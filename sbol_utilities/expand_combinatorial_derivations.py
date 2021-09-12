import argparse
import logging
import sbol3
import itertools
from .helper_functions import flatten, copy_toplevel_and_dependencies, replace_feature, id_sort, sort_owned_objects, \
    type_to_standard_extension


def cd_assigment_to_display_id(cd: sbol3.CombinatorialDerivation, assignment: tuple) -> str:
    """Makes a unique display-id for any assignment of values

    :param cd: CombinatorialDerivation being expanded
    :param assignment: tuple of variables to expand
    :return: display ID for this combination
    """
    return cd.display_id + ''.join("_" + a.display_id for a in assignment)


def is_library(cd: sbol3.CombinatorialDerivation) -> bool:
    """Check if the CombinatorialDerivation can be collapsed into a simple Collection of values

    :param cd: CombinatorialDerivation being checked
    :return: true if it can be reduced to a Collection
    """
    c = cd.template.lookup()
    one_var = len(cd.variable_features) == 1 and len(c.features) == 1
    simple = not c.sequences and not c.interactions and not c.constraints and not c.interfaces and not c.models
    return one_var and simple


class CombinatorialDerivationExpander:
    """Class for expanding combinatorial derivations by walking their substructures"""
    def __init__(self):
        self.expanded_derivations:dict[sbol3.CombinatorialDerivation,sbol3.Collection] = {}

    def collection_values(self, c: sbol3.Collection) -> list[sbol3.Component]:
        """Pull all SBOL Components out of a possibly recursive collection

        :param c: Collection for extraction
        :return: list of Component values found
        """
        assert all(isinstance(x.lookup(), sbol3.Collection) or isinstance(x.lookup(), sbol3.Component) for x in c.members)
        values = [x.lookup() for x in id_sort(c.members) if isinstance(x.lookup(), sbol3.Component)] + \
            id_sort(flatten([self.collection_values(x) for x in c.members if isinstance(x.lookup(), sbol3.Collection)]))
        logging.debug("Found "+str(len(values))+" values in collection "+c.display_id)
        return values

    def cd_variable_values(self, v: sbol3.VariableFeature) -> list[sbol3.Component]:
        """Flatten a variable to collect all of its values

        :param v: Variable to be flattened
        :return: list of Component values found
        """
        logging.debug("Finding values for " + v.variable.lookup().name)
        sub_cd_collections = [self.derivation_to_collection(d.lookup()) for d in id_sort(v.variant_derivations)]
        values = [x.lookup() for x in id_sort(v.variants)] + \
                 id_sort(flatten([self.collection_values(c) for c in id_sort(v.variant_collections)])) + \
                 id_sort(flatten(self.collection_values(c) for c in id_sort(sub_cd_collections)))
        logging.debug("Found " + str(len(values)) + " total values for " + v.variable.lookup().name)
        return values

    # Takes a CombinatorialDerivation and list of all those previously expanded, return a Collection of all of the
    # variants generated from the CD, which have been added to its containing document
    # Method: recursively instantiate all variables of the document
    # We'll do this by a simple depth first search initially, since the numbers shouldn't be too large
    def derivation_to_collection(self, cd: sbol3.CombinatorialDerivation):
        doc = cd.document
        sbol3.set_namespace(cd.namespace) # use the namespace of the CD for all of its products
        sort_owned_objects(cd.template.lookup()) # TODO: issue #231
        # we've already converted this CombinatorialDerivation to a Collection, just return the conversion
        if cd in self.expanded_derivations.keys():
            logging.debug('Found previous expansion of ' + cd.display_id)
            return self.expanded_derivations[cd]
        # if it doesn't already exist, we'll build it
        logging.debug("Expanding combinatorial derivation " + cd.display_id)
        # first get all of the values
        values = [id_sort(self.cd_variable_values(v)) for v in id_sort(cd.variable_features)]
        # if this is de facto a collection rather than a CD, just return it directly
        if is_library(cd):
            logging.debug("Interpreting combinatorial derivation " + cd.display_id + " as library")
            derivatives = sbol3.Collection(cd.identity + "_collection")
            doc.add(derivatives)
            derivatives.members += values[0]
        else:
            derivatives = sbol3.Collection(cd.identity + "_derivatives")
            doc.add(derivatives)
            # create a product-space of all of the possible assignments, then evaluate each in a scratch document
            assignments = itertools.product(*values)
            for a in assignments:
                # scratch_doc = sbol3.Document()
                derived = cd.template.lookup().clone(cd_assigment_to_display_id(cd, a))
                logging.debug("Considering derived combination " + derived.display_id)
                # scratch_doc.add(derived) # add to the scratch document to enable manipulation of children
                doc.add(derived)  # add to the scratch document to enable manipulation of children
                # Replace variables with values
                newsubs = {
                    derived.features[cd.template.lookup().features.index(f.variable.lookup())]: sbol3.SubComponent(v)
                    for f, v in zip(id_sort(cd.variable_features), a)}
                for f in id_sort(newsubs.keys()):
                    replace_feature(derived, f, newsubs[f])
                # Need to remap everything that points to this feature as well
                # TODO: confirm that variant satisfies constraints
                # If constraints are satisfied, then copy back and add to success list
                # derived.copy(input_doc)
                derivatives.members.append(derived)
        # remember and return the collection of all successful derivatives
        self.expanded_derivations[cd] = derivatives
        return derivatives


###############################################################
# Entry point function

def expand_derivations(targets: list[sbol3.CombinatorialDerivation]) -> list[sbol3.Collection]:
    """Given a list of CombinatorialDerivations, expand each to make all of the variants that instantiate the
    specification for each CombinatorialDerivation. All of the expansions are stored in the document.
    Note: assumes exhaustive sampling strategy

    :param targets: list of CombinatorialDerivations to expand, all of which should be in the same SBOL document
    :return: list of SBOL Collections, one for each target (in same order as targets)
    """
    # Make sure input is a unique set of CombinatorialDerivation objects
    assert all(isinstance(t, sbol3.CombinatorialDerivation) for t in targets), \
        'Some expansion targets are not SBOL CombinatorialDerivation objects: ' + \
        str(t for t in targets if not isinstance(t, sbol3.CombinatorialDerivation))
    assert len(set(targets)) == len(targets), \
        'All expansion targets must be unique; found '+str(len(targets)-len(set(targets)))+' duplicates'
    assert len({t.document for t in targets}) == 1 and targets[0].document is not None, \
        'All expansion targets must be located in a single SBOL Document'
    input_doc = targets[0].document

    # Output document will contain the derivative collections for each target
    expander = CombinatorialDerivationExpander()
    for cd in targets:
        logging.info('Expanding derivation '+cd.display_id)
        expander.derivation_to_collection(cd)
        logging.info("Expansion finished, producing "+str(len(expander.expanded_derivations[cd].members))+" designs")

    # Make sure the document is still OK, then return
    report = input_doc.validate()
    logging.info('Document validation found '+str(len(report.errors))+' errors, '+str(len(report.warnings))+' warnings')
    return [expander.expanded_derivations[t] for t in targets]


def root_combinatorial_derivations(doc: sbol3.Document) -> set[sbol3.CombinatorialDerivation]:
    """ Find all of the root CombinatorialDerivations in a document (i.e., those not referred to be another CD)

    :param doc: Document to search
    :return: set of root CDs
    """
    cds = {o for o in doc.objects if isinstance(o, sbol3.CombinatorialDerivation)}
    children = set(flatten([[d.lookup() for d in v.variant_derivations] for cd in cds for v in cd.variable_features]))
    return cds - children  # Roots are those CDs that are not a child of any other CD


def main():
    """Main wrapper: read from input file, invoke expand_derivations, then write to output file

    :return: None
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('input_file', help="SBOL file used as input")
    parser.add_argument('-x', '--expansion-target', dest='targets', action='append', default=None,
                        help="Name of object to be expanded; can be used multiple times. "
                             "If not listed, will attempt to expand all root derivations")
    parser.add_argument('-o', '--output', dest='output_file', default='out',
                        help="Name of SBOL file to be written")
    parser.add_argument('-t', '--file-type', dest='file_type', default=sbol3.SORTED_NTRIPLES,
                        help="Name of SBOL file to output to (excluding type)")
    parser.add_argument('--verbose', '-v', dest='verbose', action='count', default=0,
                        help="Print running explanation of conversion process")
    args_dict = vars(parser.parse_args())

    # Extract arguments:
    verbosity = args_dict['verbose']
    logging.getLogger().setLevel(level=(logging.WARN if verbosity == 0 else
                                        logging.INFO if verbosity == 1 else logging.DEBUG))
    output_file = args_dict['output_file']
    file_type = args_dict['file_type']
    input_file = args_dict['input_file']
    extension = type_to_standard_extension[file_type]
    outfile_name = output_file if output_file.endswith(extension) else output_file+extension
    targets = args_dict['targets']

    # Read file and find the target CombinatorialDerivation objects
    logging.info('Accessing input SBOL file '+input_file)
    input_doc = sbol3.Document()
    input_doc.read(input_file)
    if targets:
        targets = id_sort([input_doc.find(cd) for cd in targets])
    else:
        targets = id_sort(root_combinatorial_derivations(input_doc))
    # Expand CDs
    derivative_collections = expand_derivations(targets)
    # Write a document containing only the expansions
    output_doc = sbol3.Document()
    for c in derivative_collections:
        copy_toplevel_and_dependencies(output_doc, c)  # TODO: adjust after resolution of pySBOL issue #235
    report = output_doc.validate()
    logging.info('Document validation found '+str(len(report.errors))+' errors, '+str(len(report.warnings))+' warnings')
    output_doc.write(outfile_name, file_type)
    logging.info('Expansions SBOL file written to '+outfile_name)
