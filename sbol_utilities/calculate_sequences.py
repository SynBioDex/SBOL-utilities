import argparse
import logging
from typing import List, Tuple, Union, Iterable

import sbol3

from sbol_utilities.helper_functions import is_plasmid, id_sort
from sbol_utilities.workarounds import type_to_standard_extension


def resolved_dna_component(component: sbol3.Component) -> bool:
    """ Check if a DNA component still needs its sequence calculated

    :param component: SBOL Component to check
    :return: True if it has a DNa sequence; false otherwise
    """
    return sbol3.SBO_DNA in component.types and len(component.sequences) > 0


def order_subcomponents(component: sbol3.Component) -> Union[Tuple[List[sbol3.Feature], bool], None]:
    """Attempt to find a sorted order of features in an SBOL Component, so its sequence can be calculated from theirs
    Conduct the sort by walking through one meet relation at a time (excepting a circular component)

    :param component: Component whose features are to be oreered
    :return: if the features can be ordered, return a list of features in the order that they should be joined and
    a boolean indicating if it's circular. If the features cannot be ordered, return None
    """
    # first, check for circularity of the construct
    circular_components = id_sort(f for f in component.features if is_plasmid(f))
    circular = len(circular_components) > 0

    # if there are no features, then no sequence can be computed
    if not component.features:
        return None
    # if there's precisely one feature, it doesn't need ordering
    if len(component.features) == 1:
        return [component.features[0]], circular

    # otherwise, for N components, we should have a chain of N-1 meetings (possibly excepting one circular)
    order = []
    meetings = {c for c in component.constraints if c.restriction == sbol3.SBOL_MEETS}
    # given a potential loop, designate the first circular component as the loop and remove any meetings starting there
    if circular and len(meetings) == len(component.features):
        meetings -= {m for m in meetings if m.subject == circular_components[0].identity}

    unordered = list(component.features)
    while meetings:
        # Meetings that can go next are any that are a subject and not an object
        unblocked = {m.subject.lookup() for m in meetings}-{m.object.lookup() for m in meetings}
        if len(unblocked) != 1: # if it's not an unambiguous single, we're sunk
            return None
        # add to the order
        subject = unblocked.pop()
        subject_meetings = {m for m in meetings if m.subject.lookup() is subject}
        assert len(subject_meetings) == 1 # should be precisely one with the subject
        order.append(subject)
        unordered.remove(subject)
        meetings -= subject_meetings
        if len(meetings) == 0: # if we just did the final meeting, add the object on the end
            object = subject_meetings.pop().object.lookup()
            order.append(object) # add the last one
            unordered.remove(object)

    # if all components have been ordered, then return the order
    assert unordered or (len(order) == len(component.features))
    return (order if not unordered else None), circular

# assumes already ordered
def ready_to_resolve(component: sbol3.Component, resolved: Iterable[str]):
    return all(isinstance(f,sbol3.SubComponent) and str(f.instance_of) in resolved for f in component.features)

def compute_sequence(component: sbol3.Component) -> sbol3.Sequence:
    """Compute the sequence of a component and add this information into the Component in place

    :param component: Component whose sequence is to be computed
    :return: Sequence that has been computed
    """
    sorted, circular = order_subcomponents(component)
    # make the blank sequence
    sequence = sbol3.Sequence(component.display_id+"_sequence", encoding='https://identifiers.org/edam:format_1207') #   ### BUG: pySBOL #185
    sequence.elements = '' # Should be in keywords, except pySBOL3 #208
    # for each component in turn, add it and set its location
    for i in range(len(sorted)):
        subc = sorted[i].instance_of.lookup()
        assert len(subc.sequences) == 1
        subseq = subc.sequences[0].lookup()
        assert sequence.encoding==subseq.encoding
        sorted[i].locations.append(sbol3.Range(sequence, len(sequence.elements)+1, len(sequence.elements)+len(subseq.elements)))
        sequence.elements += subseq.elements
    # when all have been handled, the sequence is fully realized
    component.document.add(sequence)
    component.sequences.append(sequence)
    return sequence


###############################################################
# Entry point function

# Takes a list of targets, all of which should be in the same input document, and expands within that document
def calculate_sequences(doc: sbol3.Document) -> List[sbol3.Sequence]:
    """Attempt to calculate missing sequences of Components from their features

    :param doc: Document where sequences will be calculated
    :return: list of newly computed sequences
    """
    new_sequences = []

    # figure out which components are potential targets for expansion
    dna_components = {obj for obj in doc.objects if isinstance(obj, sbol3.Component) and sbol3.SBO_DNA in obj.types}
    resolved = {c for c in dna_components if resolved_dna_component(c)}
    pending_resolution = {c for c in (dna_components-resolved) if order_subcomponents(c) and not resolved_dna_component(c)}
    logging.info(f'Found {len(dna_components)} DNA components, {len(pending_resolution)} needing sequences computed')

    # loop through sequences, attempting to resolve each in turn
    while pending_resolution:
        resolvable = {c for c in pending_resolution if ready_to_resolve(c, {str(r.identity) for r in resolved})}
        if not resolvable:
            break
        for c in resolvable:
            new_sequences.append(compute_sequence(c))
            logging.info(f'Computed sequence for {c.display_id}')
        resolved = resolved.union(resolvable)
        pending_resolution -= resolvable

    if len(pending_resolution) == 0:
        logging.info('All sequences resolved')
    else:
        logging.info(f'Could not resolve all sequences: {len(pending_resolution)} remain without a sequence')

    # Make sure the document is still OK, then return
    report = doc.validate()
    logging.info(f'Document validation found {len(report.errors)} errors, {len(report.warnings)} warnings')
    return new_sequences


def main():
    """
    Main wrapper: read from input file, invoke calculate_sequences, then write to output file
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('sbol_file', help="SBOL file used as input")
    parser.add_argument('-o', '--output', dest='output_file', default='out',
                        help="Name of SBOL file to be written")
    parser.add_argument('-t', '--file-type', dest='file_type', default=sbol3.SORTED_NTRIPLES,
                        help="Name of SBOL file to output to (excluding type)")
    parser.add_argument('--verbose', '-v', dest='verbose', action='count', default=0,
                        help="Print running explanation of expansion process")
    args_dict = vars(parser.parse_args())

    # Extract arguments:
    verbosity = args_dict['verbose']
    log_level = logging.WARN if verbosity == 0 else logging.INFO if verbosity == 1 else logging.DEBUG
    logging.getLogger().setLevel(level=log_level)
    output_file = args_dict['output_file']
    file_type = args_dict['file_type']
    sbol_file = args_dict['sbol_file']
    extension = type_to_standard_extension[file_type]
    outfile_name = output_file if output_file.endswith(extension) else output_file+extension

    # Read file, convert, and write resulting document
    logging.info('Reading SBOL file '+sbol_file)
    doc = sbol3.Document()
    doc.read(sbol_file)
    logging.info('Calculating sequences')
    new_seqs = calculate_sequences(doc)
    logging.info(f'Calculated {len(new_seqs)} new sequences')
    doc.write(outfile_name, file_type)
    logging.info('SBOL file written to '+outfile_name)


if __name__ == '__main__':
    main()
