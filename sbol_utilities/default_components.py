from typing import List, Tuple

import sbol3
import tyto

def promoter(name: str, description: str, sequence: str)-> Tuple[sbol3.Component, sbol3.Sequence]:
    """
    Creates a promoter and a sequence Components with a given name, description, and sequence.
    """
    promoter_seq = sbol3.Sequence(f'{name}_seq')
    promoter_seq.elements= sequence
    promoter_seq.encoding = 'https://identifiers.org/edam:format_1207'

    promoter = sbol3.Component(name, sbol3.SBO_DNA)
    promoter.name = name
    promoter.description = description
    promoter.roles. append(sbol3.SO_PROMOTER)
    promoter.sequences.append(promoter_seq)
    return tuple([promoter, promoter_seq])

def rbs(name: str, description: str, sequence: str)-> Tuple[sbol3.Component, sbol3.Sequence]:
    """
    Creates a Ribosome Binding Site (RBS) and a sequence Components with a given name, description, and sequence.
    """
    rbs_seq = sbol3.Sequence(f'{name}_seq')
    rbs_seq.elements= sequence
    rbs_seq.encoding = 'https://identifiers.org/edam:format_1207'

    rbs = sbol3.Component(name, sbol3.SBO_DNA)
    rbs.name = name
    rbs.description = description
    rbs.roles. append(sbol3.SO_RBS)
    rbs.sequences.append(rbs_seq)
    return tuple([rbs, rbs_seq])

def cds(name: str, description: str, sequence: str)-> Tuple[sbol3.Component, sbol3.Sequence]:
    """
    Creates a coding sequence (CDS) and a sequence Components with a given name, description, and sequence.
    """
    cds_seq = sbol3.Sequence(f'{name}_seq')
    cds_seq.elements= sequence
    cds_seq.encoding = 'https://identifiers.org/edam:format_1207'

    cds = sbol3.Component(name, sbol3.SBO_DNA)
    cds.name = name
    cds.description = description
    cds.roles. append(sbol3.SO_CDS)
    cds.sequences.append(cds_seq)
    return tuple([cds, cds_seq])

def terminator(name: str, description: str, sequence: str)-> Tuple[sbol3.Component, sbol3.Sequence]:
    """
    Creates a terminator and a sequence Components with a given name, description, and sequence.
    """
    terminator_seq = sbol3.Sequence(f'{name}_seq')
    terminator_seq.elements= sequence
    terminator_seq.encoding = 'https://identifiers.org/edam:format_1207'

    terminator = sbol3.Component(name, sbol3.SBO_DNA)
    terminator.name = name
    terminator.description = description
    terminator.roles. append(sbol3.SO_TERMINATOR)
    terminator.sequences.append(terminator_seq)
    return tuple([terminator, terminator_seq])

def deg_tag(name: str, description: str, sequence: str)-> Tuple[sbol3.Component, sbol3.Sequence]:
    """
    Creates a degradation tag and a sequence Components with a given name, description, and sequence.
    """
    deg_tag_seq = sbol3.Sequence(f'{name}_seq')
    deg_tag_seq.elements= sequence
    deg_tag_seq.encoding = 'https://identifiers.org/edam:format_1207'

    deg_tag = sbol3.Component(name, sbol3.SBO_DNA)
    deg_tag.name = name
    deg_tag.description = description
    deg_tag.roles. append(tyto.SO.protein_stability_element)
    deg_tag.sequences.append(deg_tag_seq)
    return tuple([deg_tag, deg_tag_seq])

def plasmid_vector(name: str, description: str, sequence: str)-> Tuple[sbol3.Component, sbol3.Sequence]:
    """
    Creates a plasmid vector or backbone and a sequence Components with a given name, description, and sequence.
    """
    plasmid_vector_seq = sbol3.Sequence(f'{name}_seq')
    plasmid_vector_seq.elements= sequence
    plasmid_vector_seq.encoding = 'https://identifiers.org/edam:format_1207'

    plasmid_vector = sbol3.Component(name, sbol3.SBO_DNA)
    plasmid_vector.name = name
    plasmid_vector.description = description
    plasmid_vector.roles. append(tyto.SO.plasmid_vector)
    plasmid_vector.sequences.append(plasmid_vector_seq)
    return tuple([plasmid_vector, plasmid_vector_seq])

def engineered_region(name: str, description: str, sub_components: List[sbol3.SubComponent])-> sbol3.Component:
    """
    Creates an engineered region Componentswith a given name, description, and sub components.
    """
    #sequence = blunt or assembly?
    #engineered_region_seq = sbol3.Sequence(f'{name}_seq')
    #engineered_region_seq.elements= sequence
    #engineered_region_seq.encoding = 'https://identifiers.org/edam:format_1207'

    engineered_region = sbol3.Component(name, sbol3.SBO_DNA)
    engineered_region.name = name
    engineered_region.description = description
    engineered_region.roles.append(sbol3.SO_ENGINEERED_REGION)
    #create subcomponents if Components are passed  
    for x in sub_components:
        engineered_region.features.append(x)
    #fix order
    if len(engineered_region.features) > 1:
            for i in range(len(engineered_region.features)-1):
                engineered_region.constraints = [sbol3.Constraint(sbol3.SBOL_PRECEDES, engineered_region.features[i], engineered_region.features[i+1])]
    else: pass
    #engineered_region.sequences.append(engineered_region_seq)
    return engineered_region # , engineered_region_seq

def media(name: str, description: str)-> sbol3.Component:
    """
    Creates a media Component with a given name and description.
    """
    media = sbol3.Component(name, sbol3.SBO_FUNCTIONAL_ENTITY)
    media.name = name
    media.description = description
    media.roles.append(tyto.NCIT.Media)
    return media

def strain(name: str, description: str)-> sbol3.Component:
    """
    Creates a strain Component with a given name and description.
    """
    strain = sbol3.Component(name, sbol3.SBO_FUNCTIONAL_ENTITY)
    strain.name = name
    strain.description = description
    strain.roles.append(tyto.NCIT.Strain)
    return strain

def simple_chemical(name: str, description: str, chebi: str )-> sbol3.Component:
    """
    Creates a simple chemical Component with a given name, description and CHEBI ontology URI.
    """
    simple_chemical = sbol3.Component(name, sbol3.SBO_SIMPLE_CHEMICAL)
    simple_chemical.name = name
    simple_chemical.description = description
    simple_chemical.roles.append(chebi)
    return  simple_chemical
