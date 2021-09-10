import argparse
import logging

import sbol3
import tyto

from sbol_utilities.helper_functions import type_to_standard_extension

###############################################################
# Collect all components of type DNA and resolve sequences until blocked

def resolved_dna_component(component):
    return isinstance(component,sbol3.Component) and sbol3.SBO_DNA in component.types and len(component.sequences)>0

# sort by finding one meet relation at a time
def order_subcomponents(component):
    if len(component.features)==1: # if there's precisely one component, it doesn't need ordering
        return [component.features[0]]
    # otherwise, for N components, we should have a chain of N-1 meetings
    order = []
    meetings = {c for c in component.constraints if c.restriction==sbol3.SBOL_MEETS}
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
    assert unordered or (len(order)==len(component.features))
    return (order if not unordered else None)

def ready_to_resolve(component):
    return all(isinstance(f,sbol3.SubComponent) and resolved_dna_component(f.instance_of.lookup()) for f in component.features) and order_subcomponents(component)

def compute_sequence(component: sbol3.Component) -> sbol3.Sequence:
    """Compute the sequence of a component and add this information into the Component in place

    :param component: Component whose sequence is to be computed
    :return: Sequence that has been computed
    """
    sorted = order_subcomponents(component)
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
def calculate_sequences(doc: sbol3.Document) -> list[sbol3.Sequence]:
    """Attempt to calculate missing sequences of Components from their features

    :param doc: Document where sequences will be calculated
    :return: list of newly computed sequences
    """
    new_sequences = []

    # figure out which components are potential targets for expansion
    dna_components = {obj for obj in doc.objects if isinstance(obj, sbol3.Component) and sbol3.SBO_DNA in obj.types}
    pending_resolution = {c for c in dna_components if not resolved_dna_component(c)}
    logging.info(f'Found {len(dna_components)} DNA components, {len(pending_resolution)} needing sequences computed')

    # loop through sequences, attempting to resolve each in turn
    while pending_resolution:
        resolvable = {c for c in pending_resolution if ready_to_resolve(c)}
        if not resolvable:
            break
        for c in resolvable:
            new_sequences.append(compute_sequence(c))
            logging.info('Computed sequence for ' + c.display_id)
        pending_resolution -= resolvable

    if len(pending_resolution) == 0:
        logging.info('All sequences resolved')
    else:
        logging.info('Could not resolve all sequences: ' + str(len(pending_resolution)) + ' remain without a sequence')

    # Make sure the document is still OK, then return
    report = doc.validate()
    logging.info('Document validation found '+str(len(report.errors))+' errors, '+str(len(report.warnings))+' warnings')
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
    outfile_name = output_file+type_to_standard_extension[file_type]

    # Read file, convert, and write resulting document
    logging.info('Reading SBOL file '+sbol_file)
    doc = sbol3.Document()
    doc.read(sbol_file)
    logging.info('Calculating sequences')
    new_seqs = calculate_sequences(doc)
    logging.info(f'Calculated {len(new_seqs)} new sequences')
    doc.write(outfile_name, file_type)
    logging.info('SBOL file written to '+outfile_name)
