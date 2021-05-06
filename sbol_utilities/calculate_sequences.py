import sbol3
import tyto

FILENAME = 'iGEM_round_1_order_constructs'

###############################################################
# Load the document

print('Reading SBOL document')

doc = sbol3.Document()
doc.read(FILENAME+'.json','json-ld')
sbol3.set_namespace('https://engineering.igem.org/2021/')

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

def compute_sequence(component):
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
    doc.add(sequence)
    component.sequences.append(sequence)

# kludge: it's a plasmid if either it or its direct subcomponent is
def component_is_circular_plasmid(component):
    plasmid = tyto.SO.get_uri_by_term('plasmid')
    return plasmid in component.roles or \
           any(f for f in component.features if (isinstance(f,sbol3.SubComponent) and plasmid in f.instance_of.lookup().roles))

dna_components = {obj for obj in doc.objects if isinstance(obj,sbol3.Component) and sbol3.SBO_DNA in obj.types}
plasmids = {c for c in dna_components if component_is_circular_plasmid(c)}
pending_resolution  = {c for c in dna_components if not (c in plasmids) and (not resolved_dna_component(c))}
print('Found '+str(len(dna_components))+' DNA components, '+str(len(pending_resolution))+' needing sequences computed, '
      +str(len(plasmids))+' ignored as circular plasmids')

while pending_resolution:
    resolvable = {c for c in pending_resolution if ready_to_resolve(c)}
    if not resolvable:
        break
    for c in resolvable:
        compute_sequence(c)
        print('Computed sequence for '+c.display_id)
    pending_resolution -= resolvable

if len(pending_resolution) == 0:
    print('All sequences resolved')
else:
    print('Could not resolve all sequences: ' + str(len(pending_resolution)) + ' remain without a sequence')

###############################################################
# Validate and write

report = doc.validate()
print('Validation of document found '+str(len(report.errors))+' errors and '+str(len(report.warnings))+' warnings')

doc.write(FILENAME+'_full_sequences.json', 'json-ld')
doc.write(FILENAME+'_full_sequences.ttl', 'turtle')

print('SBOL file written with '+str(len({obj for obj in doc.objects if resolved_dna_component(obj)}))+' resolved DNA components')
