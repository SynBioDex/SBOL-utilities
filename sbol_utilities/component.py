from __future__ import annotations

from typing import Dict, Iterable, List, Union, Optional, Tuple

import sbol3
import tyto

from sbol_utilities.helper_functions import id_sort, find_child, find_top_level, SBOL3PassiveVisitor, cached_references, is_plasmid, is_circular
from sbol_utilities.workarounds import get_parent

from Bio import Restriction
from pydna.dseqrecord import Dseqrecord
from itertools import product

# TODO: consider allowing return of LocalSubComponent and ExternallyDefined
def contained_components(roots: Union[sbol3.TopLevel, Iterable[sbol3.TopLevel]]) -> set[sbol3.Component]:
    """Find the set of all SBOL Components contained within the roots or their children.
    This will explore via all of the direct relations that can include a Component:
    Collection.member, CombinatorialDerivation.template, variable_features
    Component.feature:SubComponent, Implementation.built,
    VariableFeature.variant, variant_derivation, variant_collection

    :param roots: single TopLevel or iterable collection of TopLevel objects to explore
    :return: set of Components found, including roots
    :raises TopLevelNotFound: if some referenced Components are not in the document
    """
    if isinstance(roots, sbol3.TopLevel):
        roots = [roots]

    class ContainmentVisitor(SBOL3PassiveVisitor):
        def __init__(self):
            self.contained = set()  # set being built via traversal
            self.visited = set()

        def already_visited(self, obj: sbol3.Identified) -> bool:
            prior = obj in self.visited
            self.visited.add(obj)
            return prior

        def visit_collection(self, c: sbol3.Collection):
            if not self.already_visited(c):
                for m in c.members:
                    find_top_level(m).accept(self)

        def visit_combinatorial_derivation(self, c: sbol3.CombinatorialDerivation):
            if not self.already_visited(c):
                find_top_level(c.template).accept(self)
                for v in c.variable_features:
                    v.accept(self)

        def visit_variable_feature(self, v: sbol3.VariableFeature):
            if not self.already_visited(v):
                for c in v.variants:
                    find_top_level(c).accept(self)
                for c in v.variant_collections:
                    find_top_level(c).accept(self)
                for cd in v.variant_derivations:
                    find_top_level(cd).accept(self)

        def visit_component(self, c: sbol3.Component):
            if not self.already_visited(c):
                self.contained.add(c)
                for sc in (f for f in c.features if isinstance(f, sbol3.SubComponent)):
                    find_top_level(sc.instance_of).accept(self)

        def visit_implementation(self, i: sbol3.Implementation):
            if not self.already_visited(i):
                if i.built:
                    find_top_level(i.built).accept(self)

    visitor = ContainmentVisitor()
    root_list = list(roots)
    if root_list:  # can't build the cache unless there's at least one component to walk
        with cached_references(root_list[0].document):
            for r in roots:
                r.accept(visitor)
    return visitor.contained


def is_dna_part(obj: sbol3.Component) -> bool:
    """Check if an SBOL Component is a DNA Part, i.e., having type 'SBO:DNA', and exactly 1 sequence property

    :param obj: Sbol3 Document to be checked
    :return: true if dna part
    """
    # must have a type of dna
    def has_dna_type(component: sbol3.Component) -> bool:
        return any(tyto.SBO.deoxyribonucleic_acid.is_ancestor_of(type) for type in component.types)

    # there must be atleast 1 SO role, among others
    def check_roles(component: sbol3.Component) -> bool:
        return any(tyto.SO.get_term_by_uri(role) for role in component.roles)

    # check all conditions
    return isinstance(obj, sbol3.Component) and check_roles(obj) \
        and has_dna_type(obj) and len(obj.sequences) == 1


def ensure_singleton_feature(system: sbol3.Component, target: Union[sbol3.Feature, sbol3.Component]):
    """Return a feature associated with the target, i.e., the target itself if a feature, or a SubComponent.
    If the target is not already in the system, add it.
    Raises ValueError if given a Component with multiple instances.

    :return: associated feature
    """
    if isinstance(target, sbol3.Feature):  # features are returned directly
        if target not in system.features:
            system.features.append(target)
        return target
    instances = [f for f in system.features if isinstance(f, sbol3.SubComponent) and f.instance_of == target.identity]
    if len(instances) == 1:  # if there is precisely one SubComponent, return it
        return instances[0]
    elif not len(instances):  # if there are no SubComponents, add one
        return add_feature(system, target)
    else:  # if there are multiple SubComponents, raise an exception
        raise ValueError(f'Ambiguous reference: {len(instances)} instances of {target.identity} in {system.identity}')


def ensure_singleton_system(system: Optional[sbol3.Component], *features: Union[sbol3.Feature, sbol3.Component])\
        -> sbol3.Component:
    """Check that the system referred to is unambiguous. Raises ValueError if there are multiple or zero systems.

    :param system: Optional explicit specification of system
    :param features: features in the same system or components to be referenced from it
    :return: Component for the identified system
    """
    systems = set(filter(None, (get_parent(f) for f in features if isinstance(f, sbol3.Feature))))
    if system:
        systems |= {system}
    if len(systems) == 1:
        system = systems.pop()
        if not isinstance(system, sbol3.Component):
            raise ValueError(f'Could not find system, instead found {system}')
        return system
    elif not systems:
        raise ValueError(f'Could not find system: no features in {features}')
    else:
        raise ValueError(f'Multiple systems referred to: {systems}')


def add_feature(component: sbol3.Component, to_add: Union[sbol3.Feature, sbol3.Component]) -> sbol3.Feature:
    """Pass-through adder for adding a Feature to a Component for allowing slightly more compact code.
    Note that unlike ensure_singleton_feature, this allows adding multiple instances.

    :param component: Component to add the Feature to
    :param to_add: Feature or Component to be added to system. Components will be wrapped in a SubComponent Feature
    :return: feature added (SubComponent if to_add was a Component)
    """
    if isinstance(to_add, sbol3.Component):
        to_add = sbol3.SubComponent(to_add)
    component.features.append(to_add)
    return to_add


def contains(container: Union[sbol3.Feature, sbol3.Component], contained: Union[sbol3.Feature, sbol3.Component],
             system: Optional[sbol3.Component] = None) -> sbol3.Feature:
    """Assert a topological containment constraint between two features (e.g., a promoter contained in a plasmid).
    Implicitly identifies system and creates/adds features as necessary.

    :param container: containing feature
    :param contained: feature that is contained
    :param system: optional explicit statement of system
    :return: contained feature
    """
    # transform implicit arguments into explicit
    system = ensure_singleton_system(system, container, contained)
    container = ensure_singleton_feature(system, container)
    contained = ensure_singleton_feature(system, contained)
    # add a containment relation
    system.constraints.append(sbol3.Constraint(sbol3.SBOL_CONTAINS, subject=container, object=contained))
    return contained


def order(five_prime: Union[sbol3.Feature, sbol3.Component], three_prime: Union[sbol3.Feature, sbol3.Component],
          system: Optional[sbol3.Component] = None) -> sbol3.Feature:
    """Assert a topological ordering constraint between two features (e.g., a CDS followed by a terminator).
    Implicitly identifies system and creates/adds features as necessary.

    :param five_prime: containing feature
    :param three_prime: feature that is contained
    :param system: optional explicit statement of system
    :return: three_prime feature
    """
    # transform implicit arguments into explicit
    system = ensure_singleton_system(system, five_prime, three_prime)
    five_prime = ensure_singleton_feature(system, five_prime)
    three_prime = ensure_singleton_feature(system, three_prime)
    # add a containment relation
    system.constraints.append(sbol3.Constraint(sbol3.SBOL_MEETS, subject=five_prime, object=three_prime))
    return three_prime


def regulate(five_prime: Union[sbol3.Feature, sbol3.Component], target: Union[sbol3.Feature, sbol3.Component],
             system: Optional[sbol3.Component] = None) -> sbol3.Feature:
    """Connect a 5' regulatory region to control the expression of a 3' target region.
    Note: this function is an alias for "order".

    :param five_prime: Regulatory region to place upstream of target
    :param target: region to be regulated (e.g., a CDS or ncRNA)
    :param system: optional explicit statement of system
    :return: target feature
    """
    return order(five_prime, target, system)


def constitutive(target: Union[sbol3.Feature, sbol3.Component], system: Optional[sbol3.Component] = None)\
        -> sbol3.Feature:
    """Add a constitutive promoter regulating the target feature.

    :param target: 5' region for promoter to regulate
    :param system: optional explicit statement of system
    :return: newly created constitutive promoter
    """
    # transform implicit arguments into explicit
    system = ensure_singleton_system(system, target)
    target = ensure_singleton_feature(system, target)

    # create a constitutive promoter and use it to regulate the target
    local = sbol3.LocalSubComponent([sbol3.SBO_DNA], roles=[tyto.SO.constitutive_promoter])
    promoter_component = add_feature(system, local)
    regulate(promoter_component, target)

    # also add the promoter into any containers that hold the target
    # TODO: add lookups for constraints like we have for interactions
    containers = [c.subject for c in system.constraints
                  if c.restriction == sbol3.SBOL_CONTAINS and c.object == target.identity]
    for c in containers:
        contains(find_child(c), promoter_component)

    return promoter_component


def add_interaction(interaction_type: str,
                    participants: Dict[Union[sbol3.Feature, sbol3.Component], str],
                    system: sbol3.Component = None,
                    name: str = None) -> sbol3.Interaction:
    """Compact function for creation of an interaction.
    Implicitly identifies system and creates/adds features as necessary.

    :param interaction_type: SBO type of interaction to be to be added
    :param participants: dictionary assigning features/components to roles for participations
    :param system: system to add interaction to
    :param name: name for the interaction
    :return: interaction
    """
    # transform implicit arguments into explicit
    system = ensure_singleton_system(system, *participants.keys())
    participations = [sbol3.Participation([r], ensure_singleton_feature(system, p)) for p, r in participants.items()]
    # make and return interaction
    interaction = sbol3.Interaction([interaction_type], participations=participations, name=name)
    system.interactions.append(interaction)
    return interaction


def in_role(interaction: sbol3.Interaction, role: str) -> sbol3.Feature:
    """Find the (precisely one) feature with a given role in the interaction.

    :param interaction: interaction to search
    :param role: role to search for
    :return: Feature playing that role
    """
    feature_participation = [p for p in interaction.participations if role in p.roles]
    if len(feature_participation) != 1:
        raise ValueError(f'Role can be in 1 participant: found {len(feature_participation)} in {interaction.identity}')
    return find_child(feature_participation[0].participant)


def all_in_role(interaction: sbol3.Interaction, role: str) -> List[sbol3.Feature]:
    """Find the features with a given role in the interaction.

    :param interaction: interaction to search
    :param role: role to search for
    :return: sorted list of Features playing that role
    """
    return id_sort([find_child(p.participant) for p in interaction.participations if role in p.roles])


def dna_component_with_sequence(identity: str, sequence: str, **kwargs) -> Tuple[sbol3.Component, sbol3.Sequence]:
    """Creates a DNA Component and its Sequence.

    :param identity: The identity of the Component. The identity of Sequence is also identity with the suffix '_seq'.
    :param sequence: The DNA sequence of the Component encoded in IUPAC.
    :param kwargs: Keyword arguments of any other Component attribute.
    :return: A tuple of Component and Sequence.
    """
    comp_seq = sbol3.Sequence(f'{identity}_seq', elements=sequence, encoding=sbol3.IUPAC_DNA_ENCODING)
    dna_comp = sbol3.Component(identity, sbol3.SBO_DNA, sequences=[comp_seq], **kwargs)
    return dna_comp, comp_seq


def rna_component_with_sequence(identity: str, sequence: str, **kwargs) -> Tuple[sbol3.Component, sbol3.Sequence]:
    """Creates a RNA Component and its Sequence.

    :param identity: The identity of the Component. The identity of Sequence is also identity with the suffix '_seq'.
    :param sequence: The RNA sequence of the Component encoded in IUPAC.
    :param kwargs: Keyword arguments of any other Component attribute.
    :return: A tuple of Component and Sequence.
    """
    comp_seq = sbol3.Sequence(f'{identity}_seq', elements=sequence, encoding=sbol3.IUPAC_RNA_ENCODING)
    rna_comp = sbol3.Component(identity, sbol3.SBO_RNA, sequences=[comp_seq], **kwargs)
    return rna_comp, comp_seq


def protein_component_with_sequence(identity: str, sequence: str, **kwargs) -> Tuple[sbol3.Component, sbol3.Sequence]:
    """Creates a Protein Component and its Sequence.

    :param identity: The identity of the Component. The identity of Sequence is also identity with the suffix '_seq'.
    :param sequence: The Protein sequence of the Component encoded in IUPAC.
    :param kwargs: Keyword arguments of any other Component attribute.
    :return: A tuple of Component and Sequence.
    """
    comp_seq = sbol3.Sequence(f'{identity}_seq',  elements=sequence,  encoding=sbol3.IUPAC_PROTEIN_ENCODING)
    pro_comp = sbol3.Component(identity, sbol3.SBO_PROTEIN, sequences=[comp_seq], **kwargs)
    return pro_comp, comp_seq


def functional_component(identity: str, **kwargs) -> sbol3.Component:
    """Creates a Component of type functional entity.

    :param identity: The identity of the Component.
    :param kwargs: Keyword arguments of any other Component attribute.
    :return: A tuple of Component and Sequence.
    """
    fun_comp = sbol3.Component(identity, sbol3.SBO_FUNCTIONAL_ENTITY, **kwargs)
    return fun_comp


def promoter(identity: str, sequence: str, **kwargs) -> Tuple[sbol3.Component, sbol3.Sequence]:
    """Creates a Promoter Component and its Sequence.

    :param identity: The identity of the Component. The identity of Sequence is also identity with the suffix '_seq'.
    :param sequence: The DNA sequence of the Component encoded in IUPAC.
    :param kwargs: Keyword arguments of any other Component attribute.
    :return: A tuple of Component and Sequence.
    """
    promoter_component, promoter_seq = dna_component_with_sequence(identity, sequence, **kwargs)
    promoter_component.roles.append(sbol3.SO_PROMOTER)
    return promoter_component, promoter_seq


def rbs(identity: str, sequence: str, **kwargs) -> Tuple[sbol3.Component, sbol3.Sequence]:
    """Creates a Ribosome Entry Site (RBS) Component and its Sequence.

    :param identity: The identity of the Component. The identity of Sequence is also identity with the suffix '_seq'.
    :param sequence: The DNA sequence of the Component encoded in IUPAC.
    :param kwargs: Keyword arguments of any other Component attribute.
    :return: A tuple of Component and Sequence.
    """
    rbs_component, rbs_seq = dna_component_with_sequence(identity, sequence, **kwargs)
    rbs_component.roles.append(sbol3.SO_RBS)
    return rbs_component, rbs_seq


def cds(identity: str, sequence: str, **kwargs) -> Tuple[sbol3.Component, sbol3.Sequence]:
    """Creates a Coding Sequence (CDS) Component and its Sequence.

    :param identity: The identity of the Component. The identity of Sequence is also identity with the suffix '_seq'.
    :param sequence: The DNA sequence of the Component encoded in IUPAC.
    :param kwargs: Keyword arguments of any other Component attribute.
    :return: A tuple of Component and Sequence.
    """
    cds_component, cds_seq = dna_component_with_sequence(identity, sequence, **kwargs)
    cds_component.roles.append(sbol3.SO_CDS)
    return cds_component, cds_seq


def terminator(identity: str, sequence: str, **kwargs) -> Tuple[sbol3.Component, sbol3.Sequence]:
    """Creates a Terminator Component and its Sequence.

    :param identity: The identity of the Component. The identity of Sequence is also identity with the suffix '_seq'.
    :param sequence: The DNA sequence of the Component encoded in IUPAC.
    :param kwargs: Keyword arguments of any other Component attribute.
    :return: A tuple of Component and Sequence.
    """
    terminator_component, terminator_seq = dna_component_with_sequence(identity, sequence, **kwargs)
    terminator_component.roles.append(sbol3.SO_TERMINATOR)
    return terminator_component, terminator_seq


def protein_stability_element(identity: str, sequence: str, **kwargs) -> Tuple[sbol3.Component, sbol3.Sequence]:
    """Creates a protein stability element Component and its Sequence.

    :param identity: The identity of the Component. The identity of Sequence is also identity with the suffix '_seq'.
    :param sequence: The DNA sequence of the Component encoded in IUPAC.
    :param kwargs: Keyword arguments of any other Component attribute.
    :return: A tuple of Component and Sequence.
    """
    pse_component, protein_stability_element_seq = dna_component_with_sequence(identity, sequence, **kwargs)
    pse_component.roles.append(tyto.SO.protein_stability_element)
    return pse_component, protein_stability_element_seq


def gene(identity: str, sequence: str, **kwargs) -> Tuple[sbol3.Component, sbol3.Sequence]:
    """Creates a Gene Component and its Sequence.

    :param identity: The identity of the Component. The identity of Sequence is also identity with the suffix '_seq'.
    :param sequence: The DNA sequence of the Component encoded in IUPAC.
    :param kwargs: Keyword arguments of any other Component attribute.
    :return: A tuple of Component and Sequence.
    """
    gene_component, gene_seq = dna_component_with_sequence(identity, sequence, **kwargs)
    gene_component.roles.append(sbol3.SO_GENE)
    return gene_component, gene_seq


def operator(identity: str, sequence: str, **kwargs) -> Tuple[sbol3.Component, sbol3.Sequence]:
    """Creates an Operator Component and its Sequence.

    :param identity: The identity of the Component. The identity of Sequence is also identity with the suffix '_seq'.
    :param sequence: The DNA sequence of the Component encoded in IUPAC.
    :param kwargs: Keyword arguments of any other Component attribute.
    :return: A tuple of Component and Sequence.
    """
    operator_component, operator_seq = dna_component_with_sequence(identity, sequence, **kwargs)
    operator_component.roles.append(sbol3.SO_OPERATOR)
    return operator_component, operator_seq


def engineered_region(identity: str, features: Union[List[sbol3.SubComponent], List[sbol3.Component]], fix_order: bool=True, **kwargs) \
        -> sbol3.Component:
    """Creates an Engineered Region Component, with features assumed to be in linear order

    :param identity: The identity of the Component.
    :param features: SubComponents or Components to add as features in linear order
    :param kwargs: Keyword arguments of any other Component attribute.
    :return: A tuple of Component and Sequence.
    """
    er_component = sbol3.Component(identity, sbol3.SBO_DNA, **kwargs)
    er_component.roles.append(sbol3.SO_ENGINEERED_REGION)
    for to_add in features:
        if isinstance(to_add, sbol3.Component):
            to_add = sbol3.SubComponent(to_add)
        er_component.features.append(to_add)
    if fix_order == True:
        if len(er_component.features) > 1:
            for i in range(len(er_component.features)-1):
                constraint = sbol3.Constraint(sbol3.SBOL_PRECEDES, er_component.features[i], er_component.features[i+1])
                er_component.constraints.append(constraint)
        else:
            pass
    return er_component


def mrna(identity: str, sequence: str, **kwargs) -> Tuple[sbol3.Component, sbol3.Sequence]:
    """Creates an mRNA Component and its Sequence.

    :param identity: The identity of the Component. The identity of Sequence is also identity with the suffix '_seq'.
    :param sequence: The RNA sequence of the Component encoded in IUPAC.
    :param kwargs: Keyword arguments of any other Component attribute.
    :return: A tuple of Component and Sequence.
    """
    mrna_component, mrna_seq = rna_component_with_sequence(identity, sequence, **kwargs)
    mrna_component.roles.append(sbol3.SO_MRNA)
    return mrna_component, mrna_seq


def transcription_factor(identity: str, sequence: str, **kwargs) -> Tuple[sbol3.Component, sbol3.Sequence]:
    """Creates a Transcription Factor Component and its Sequence.

    :param identity: The identity of the Component. The identity of Sequence is also identity with the suffix '_seq'.
    :param sequence: The Protein amino acid sequence of the Component encoded in IUPAC.
    :param kwargs: Keyword arguments of any other Component attribute.
    :return: A tuple of Component and Sequence.
    """
    tf_component, transcription_factor_seq = protein_component_with_sequence(identity, sequence, **kwargs)
    tf_component.roles.append(sbol3.SO_TRANSCRIPTION_FACTOR)
    return tf_component, transcription_factor_seq


def media(identity: str, recipe: dict[Union[sbol3.Component, sbol3.SubComponent], Union[sbol3.Measure, list]] = None,
          **kwargs) -> sbol3.Component:
    """Creates a media Component of type functional entity.

    :param identity: The identity of the Component.
    :param recipe: dictionary of mapping from Component/SubComponent to a quantity (either Measure or value/unit pairs)
    :param kwargs: Keyword arguments of any other Component attribute.
    :return: a new Component representing the specified media
    :raises: ValueError if there are problems with the recipe elements
    """
    media_component = functional_component(identity, **kwargs)
    media_component.roles.append(tyto.NCIT.Media)
    # If there is a recipe, add all of the element, wrapping as needed
    if recipe:
        for key, value in recipe.items():
            if isinstance(key, sbol3.Component):
                key = sbol3.SubComponent(key)
            if not isinstance(value, sbol3.Measure):
                value = sbol3.Measure(value[0], value[1])
            if len(key.measures):
                raise ValueError(f'Media recipe applied to a component that already has a quantity: {key.identity}')
            key.measures.append(value)
            media_component.features.append(key)
    return media_component


def strain(identity: str, **kwargs) -> sbol3.Component:
    """Creates a strain Component of type functional entity.

    :param identity: The identity of the Component.
    :param kwargs: Keyword arguments of any other Component attribute.
    :return: A Component object.
    """
    strain_component = functional_component(identity, **kwargs)
    strain_component.roles.append(tyto.NCIT.Strain)
    return strain_component


def ed_simple_chemical(definition: str, **kwargs) -> sbol3.ExternallyDefined:
    """Creates an ExternallyDefined Simple Chemical Component.

    :param definition: The URI that links to a canonical definition external to SBOL, recommended ChEBI and PubChem.
    :param kwargs: Keyword arguments of any other ExternallyDefined attribute.
    :return: A Component object.
    """
    return sbol3.ExternallyDefined([sbol3.SBO_SIMPLE_CHEMICAL], definition, **kwargs)


def ed_protein(definition: str, **kwargs) -> sbol3.ExternallyDefined:
    """Creates an ExternallyDefined Protein Component.

    :param definition: The URI that links to a canonical definition external to SBOL, recommended UniProt.
    :param kwargs: Keyword arguments of any other ExternallyDefined attribute.
    :return: A Component object.
    """
    return sbol3.ExternallyDefined([sbol3.SBO_PROTEIN], definition, **kwargs)

def ed_restriction_enzyme(name:str, **kwargs) -> sbol3.ExternallyDefined:
    """Creates an ExternallyDefined Restriction Enzyme Component from rebase.

    :param name: Name of the SBOL ExternallyDefined, used by PyDNA. Case sensitive, follow standard restriction enzyme nomenclature, i.e. 'BsaI'
    :param kwargs: Keyword arguments of any other ExternallyDefined attribute.
    :return: An ExternallyDefined object.
    """
    check_enzyme = Restriction.__dict__[name]
    definition=f'http://rebase.neb.com/rebase/enz/{name}.html' # TODO: replace with getting the URI from Enzyme when REBASE identifiers become available in biopython 1.8
    return sbol3.ExternallyDefined([sbol3.SBO_PROTEIN], definition=definition, name=name, **kwargs)

def backbone(identity: str, sequence: str, dropout_location: List[int], fusion_site_length:int, linear:bool, **kwargs) -> Tuple[sbol3.Component, sbol3.Sequence]:
    """Creates a Backbone Component and its Sequence.

    :param identity: The identity of the Component. The identity of Sequence is also identity with the suffix '_seq'.
    :param sequence: The DNA sequence of the Component encoded in IUPAC.
    :param dropout_location: List of 2 integers that indicates the start and the end of the dropout sequence including overhangs. Note that the index of the first location is 1, as is typical practice in biology, rather than 0, as is typical practice in computer science.
    :param fusion_site_length: Integer of the lenght of the fusion sites (eg. BsaI fusion site lenght is 4, SapI fusion site lenght is 3)
    :param linear: Boolean than indicates if the backbone is linear, by default it is seted to False which means that it has a circular topology.
    :param kwargs: Keyword arguments of any other Component attribute.
    :return: A tuple of Component and Sequence.
    """
    if len(dropout_location) != 2:
        raise ValueError('The dropout_location only accepts 2 int values in a list.')
    backbone_component, backbone_seq = dna_component_with_sequence(identity, sequence, **kwargs)
    backbone_component.roles.append(sbol3.SO_DOUBLE_STRANDED)  
    dropout_location_comp = sbol3.Range(sequence=backbone_seq, start=dropout_location[0], end=dropout_location[1])
    insertion_site_location1 = sbol3.Range(sequence=backbone_seq, start=dropout_location[0], end=dropout_location[0]+fusion_site_length, order=1)
    insertion_site_location2 = sbol3.Range(sequence=backbone_seq, start=dropout_location[1]-fusion_site_length, end=dropout_location[1], order=3)
    dropout_sequence_feature = sbol3.SequenceFeature(locations=[dropout_location_comp], roles=[tyto.SO.deletion])
    insertion_sites_feature = sbol3.SequenceFeature(locations=[insertion_site_location1, insertion_site_location2], roles=[tyto.SO.insertion_site])
    if linear:
        backbone_component.types.append(sbol3.SO_LINEAR)
        backbone_component.roles.append(sbol3.SO_ENGINEERED_REGION)
        open_backbone_location1 = sbol3.Range(sequence=backbone_seq, start=1, end=dropout_location[0]+fusion_site_length-1, order=1)
        open_backbone_location2 = sbol3.Range(sequence=backbone_seq, start=dropout_location[1]-fusion_site_length, end=len(sequence), order=3)
        open_backbone_feature = sbol3.SequenceFeature(locations=[open_backbone_location1, open_backbone_location2])
    else: 
        backbone_component.types.append(sbol3.SO_CIRCULAR)
        backbone_component.roles.append(tyto.SO.plasmid_vector)
        open_backbone_location1 = sbol3.Range(sequence=backbone_seq, start=1, end=dropout_location[0]+fusion_site_length-1, order=2)
        open_backbone_location2 = sbol3.Range(sequence=backbone_seq, start=dropout_location[1]-fusion_site_length, end=len(sequence), order=1)
        open_backbone_feature = sbol3.SequenceFeature(locations=[open_backbone_location1, open_backbone_location2])
    backbone_component.features.append(dropout_sequence_feature)
    backbone_component.features.append(insertion_sites_feature)
    backbone_component.features.append(open_backbone_feature)
    backbone_dropout_meets = sbol3.Constraint(restriction='http://sbols.org/v3#meets', subject=dropout_sequence_feature, object=open_backbone_feature)
    backbone_component.constraints.append(backbone_dropout_meets)
    return backbone_component, backbone_seq

def backbone_from_sbol(identity: Union[str,None], sbol_comp: sbol3.Component, dropout_location: List[int], fusion_site_length:int, linear:bool, **kwargs) -> Tuple[sbol3.Component, sbol3.Sequence]:
    """Creates a Backbone Component and its Sequence.

    :param identity: The identity of the Component. The identity of Sequence is also identity with the suffix '_seq'.
    :param sbol_comp: The SBOL Component containing the DNA sequence to use.
    :param dropout_location: List of 2 integers that indicates the start and the end of the dropout sequence including overhangs. Note that the index of the first location is 1, as is typical practice in biology, rather than 0, as is typical practice in computer science.
    :param fusion_site_length: Integer of the lenght of the fusion sites (eg. BsaI fusion site lenght is 4, SapI fusion site lenght is 3)
    :param linear: Boolean than indicates if the backbone is linear, by default it is seted to False which means that it has a circular topology.
    :param kwargs: Keyword arguments of any other Component attribute.
    :return: A tuple of Component and Sequence.
    """
    if len(dropout_location) != 2:
        raise ValueError('The dropout_location only accepts 2 int values in a list.')
    if len(sbol_comp.sequences)!=1:
        raise ValueError(f'The reactant needs to have precisely one sequence. The input reactant has {len(sbol_comp.sequences)} sequences')
    sequence = str(sbol_comp.sequences[0].lookup().elements)
    if identity == None:
        backbone_component = sbol_comp 
        backbone_seq = sbol_comp.sequences[0]
    else: 
        backbone_component, backbone_seq = dna_component_with_sequence(identity, sequence, **kwargs)
    backbone_component.roles.append(sbol3.SO_DOUBLE_STRANDED)  
    dropout_location_comp = sbol3.Range(sequence=backbone_seq, start=dropout_location[0], end=dropout_location[1])
    insertion_site_location1 = sbol3.Range(sequence=backbone_seq, start=dropout_location[0], end=dropout_location[0]+fusion_site_length, order=1)
    insertion_site_location2 = sbol3.Range(sequence=backbone_seq, start=dropout_location[1]-fusion_site_length, end=dropout_location[1], order=3)
    dropout_sequence_feature = sbol3.SequenceFeature(locations=[dropout_location_comp], roles=[tyto.SO.deletion])
    insertion_sites_feature = sbol3.SequenceFeature(locations=[insertion_site_location1, insertion_site_location2], roles=[tyto.SO.insertion_site])
    if linear:
        backbone_component.types.append(sbol3.SO_LINEAR)
        backbone_component.roles.append(sbol3.SO_ENGINEERED_REGION)
        open_backbone_location1 = sbol3.Range(sequence=backbone_seq, start=1, end=dropout_location[0]+fusion_site_length-1, order=1)
        open_backbone_location2 = sbol3.Range(sequence=backbone_seq, start=dropout_location[1]-fusion_site_length, end=len(sequence), order=3)
        open_backbone_feature = sbol3.SequenceFeature(locations=[open_backbone_location1, open_backbone_location2])
    else: 
        backbone_component.types.append(sbol3.SO_CIRCULAR)
        backbone_component.roles.append(tyto.SO.plasmid_vector)
        open_backbone_location1 = sbol3.Range(sequence=backbone_seq, start=1, end=dropout_location[0]+fusion_site_length-1, order=2)
        open_backbone_location2 = sbol3.Range(sequence=backbone_seq, start=dropout_location[1]-fusion_site_length, end=len(sequence), order=1)
        open_backbone_feature = sbol3.SequenceFeature(locations=[open_backbone_location1, open_backbone_location2])
    backbone_component.features.append(dropout_sequence_feature)
    backbone_component.features.append(insertion_sites_feature)
    backbone_component.features.append(open_backbone_feature)
    backbone_dropout_meets = sbol3.Constraint(restriction='http://sbols.org/v3#meets', subject=dropout_sequence_feature, object=open_backbone_feature)
    backbone_component.constraints.append(backbone_dropout_meets)
    return backbone_component, backbone_seq

def part_in_backbone(identity: str, part: sbol3.Component, backbone: sbol3.Component, linear:bool=False, **kwargs) -> Tuple[sbol3.Component, sbol3.Sequence]:
    """Creates a Part in Backbone Component and its Sequence.

    :param identity: The identity of the Component. The identity of Sequence is also identity with the suffix '_seq'.
    :param part: Part to be located in the backbone as SBOL Component.
    :param backbone: Backbone in wich the part is located as SBOL Component.
    :param linear: Boolean than indicates if the backbone is linear, by default it is seted to Flase which means that it has a circular topology.
    :param kwargs: Keyword arguments of any other Component attribute.
    :return: A tuple of Component and Sequence.
    """
    # check that backbone has a plasmid vector or child ontology term
    if is_plasmid(backbone)==False:
        raise TypeError('The backbone has no valid plasmid vector or child role')
    # check that the backbone and part has one sequence
    if len(backbone.sequences)!=1:
        raise ValueError(f'The backbone should have only one sequence, found {len(backbone.sequences)} sequences')
    if len(part.sequences)!=1:
        raise ValueError(f'The part should have only one sequence, found{len(part.sequences)} sequences')
    # check that the the last feature of backbone has 2 locations
    if len(backbone.features[-1].locations)!=2:
        raise ValueError(f'The backbone last feature should be the open backbone and should contain 2 Locations, found {len(backbone.features[-1].locations)} Locations')
    # get backbone sequence
    backbone_sequence = backbone.sequences[0].lookup().elements
    # compute open backbone sequences
    open_backbone_sequence_from_location1=backbone_sequence[backbone.features[-1].locations[0].start -1 : backbone.features[-1].locations[0].end]
    open_backbone_sequence_from_location2=backbone_sequence[backbone.features[-1].locations[1].start -1 : backbone.features[-1].locations[1].end]
    # extract part sequence
    part_sequence = part.sequences[0].lookup().elements
    covered_fusion_site_lengths = [3,4] # review can be user input
    for l in covered_fusion_site_lengths:
        if open_backbone_sequence_from_location1[-l:]==part_sequence[:l] and part_sequence[-l:]==open_backbone_sequence_from_location2[:l]:
            part_sequence = part_sequence[l:-l]
    # make new component sequence
    if linear:
        part_in_backbone_seq_str = open_backbone_sequence_from_location1 + part_sequence + open_backbone_sequence_from_location2
        topology_type = sbol3.SO_LINEAR
    else:
        part_in_backbone_seq_str = part_sequence + open_backbone_sequence_from_location2 + open_backbone_sequence_from_location1
        topology_type = sbol3.SO_CIRCULAR
    # part in backbone Component
    part_in_backbone_component, part_in_backbone_seq = dna_component_with_sequence(identity, part_in_backbone_seq_str, **kwargs)
    part_in_backbone_component.roles.append(tyto.SO.plasmid_vector) #review
    # defining Location
    part_subcomponent_location = sbol3.Range(sequence=part_in_backbone_seq, start=1, end=len(part_sequence))
    backbone_subcomponent_location = sbol3.Range(sequence=part_in_backbone_seq, start=len(part_sequence)+1, end=len(part_in_backbone_seq_str))
    source_location = sbol3.Range(sequence=backbone_sequence, start=backbone.features[-1].locations[0].start, end=backbone.features[-1].locations[0].end) # review
    # creating and adding features
    part_subcomponent = sbol3.SubComponent(part, roles=[tyto.SO.engineered_insert], locations=[part_subcomponent_location], role_integration='http://sbols.org/v3#mergeRoles')
    backbone_subcomponent = sbol3.SubComponent(backbone, locations=[backbone_subcomponent_location], source_locations=[source_location])  #[backbone.features[2].locations[0]]) #generalize source location
    part_in_backbone_component.features.append(part_subcomponent)
    part_in_backbone_component.features.append(backbone_subcomponent)
    # adding topology
    part_in_backbone_component.types.append(topology_type)
    #if len(part_in_backbone_component.name)==0: # TODO: review
    #    part_in_backbone_component.name = identity
    return part_in_backbone_component, part_in_backbone_seq

def part_in_backbone_from_sbol(identity: Union[str, None],  sbol_comp: sbol3.Component, part_location: List[int], part_roles:List[str], fusion_site_length:int, linear:bool=False, **kwargs) -> Tuple[sbol3.Component, sbol3.Sequence]:
    """Restructures a non-hierarchical plasmid Component to follow the part-in-backbone pattern following BP011.
    It overwrites the SBOL3 Component provided. 
    A part inserted into a backbone is represented by a Component that includes both the part insert 
    as a feature that is a SubComponent and the backbone as another SubComponent.
    For more information about BP011 visit https://github.com/SynBioDex/SBOL-examples/tree/main/SBOL/best-practices/BP011 

    :param identity: The identity of the Component, is its a String it build a new SBOL Component, if None it adds on top of the input. The identity of Sequence is also identity with the suffix '_seq'.
    :param sbol_comp: The SBOL3 Component that will be used to create the part in backbone Component and Sequence.
    :param part_location: List of 2 integers that indicates the start and the end of the unitary part. Note that the index of the first location is 1, as is typical practice in biology, rather than 0, as is typical practice in computer science.
    :param part_roles: List of strings that indicates the roles to add on the part.
    :param fusion_site_length: Integer of the length of the fusion sites (eg. BsaI fusion site lenght is 4, SapI fusion site lenght is 3)
    :param linear: Boolean than indicates if the backbone is linear, by default it is seted to Flase which means that it has a circular topology.    
    :param kwargs: Keyword arguments of any other Component attribute.
    :return: A tuple of Component and Sequence.
    """
    if len(part_location) != 2:
        raise ValueError('The part_location only accepts 2 int values in a list.')
    if len(sbol_comp.sequences)!=1:
        raise ValueError(f'The reactant needs to have precisely one sequence. The input reactant has {len(sbol_comp.sequences)} sequences')
    sequence = sbol_comp.sequences[0].lookup().elements
    if identity == None:
        part_in_backbone_component = sbol_comp 
        part_in_backbone_seq = sbol_comp.sequences[0]
    else:
        part_in_backbone_component, part_in_backbone_seq = dna_component_with_sequence(identity, sequence, **kwargs)
    part_in_backbone_component.roles.append(sbol3.SO_DOUBLE_STRANDED)
    for part_role in part_roles:  
        part_in_backbone_component.roles.append(part_role)  
    # creating part feature    
    part_location_comp = sbol3.Range(sequence=part_in_backbone_seq, start=part_location[0], end=part_location[1])
    #TODO: add the option of fusion sites to be of different lenghts
    insertion_site_location1 = sbol3.Range(sequence=part_in_backbone_seq, start=part_location[0], end=part_location[0]+fusion_site_length, order=1)
    insertion_site_location2 = sbol3.Range(sequence=part_in_backbone_seq, start=part_location[1]-fusion_site_length, end=part_location[1], order=3)
    part_sequence_feature = sbol3.SequenceFeature(locations=[part_location_comp], roles=part_roles)
    part_sequence_feature.roles.append(tyto.SO.engineered_insert)
    insertion_sites_feature = sbol3.SequenceFeature(locations=[insertion_site_location1, insertion_site_location2], roles=[tyto.SO.insertion_site])
    #TODO: infer topology from the input
    if linear:
        part_in_backbone_component.types.append(sbol3.SO_LINEAR)
        part_in_backbone_component.roles.append(sbol3.SO_ENGINEERED_REGION)
        # creating backbone feature
        open_backbone_location1 = sbol3.Range(sequence=part_in_backbone_seq, start=1, end=part_location[0]+fusion_site_length-1, order=1)
        open_backbone_location2 = sbol3.Range(sequence=part_in_backbone_seq, start=part_location[1]-fusion_site_length, end=len(sequence), order=3)
        open_backbone_feature = sbol3.SequenceFeature(locations=[open_backbone_location1, open_backbone_location2])
    else: 
        part_in_backbone_component.types.append(sbol3.SO_CIRCULAR)
        part_in_backbone_component.roles.append(tyto.SO.plasmid_vector)
        # creating backbone feature
        open_backbone_location1 = sbol3.Range(sequence=part_in_backbone_seq, start=1, end=part_location[0]+fusion_site_length-1, order=2)
        open_backbone_location2 = sbol3.Range(sequence=part_in_backbone_seq, start=part_location[1]-fusion_site_length, end=len(sequence), order=1)
        open_backbone_feature = sbol3.SequenceFeature(locations=[open_backbone_location1, open_backbone_location2])
    part_in_backbone_component.features.append(part_sequence_feature)
    part_in_backbone_component.features.append(insertion_sites_feature)
    part_in_backbone_component.features.append(open_backbone_feature)
    backbone_dropout_meets = sbol3.Constraint(restriction='http://sbols.org/v3#meets', subject=part_sequence_feature, object=open_backbone_feature)
    part_in_backbone_component.constraints.append(backbone_dropout_meets)
    #TODO: Add a branch to create a component without overwriting the WHOLE input component
    #removing repeated types and roles
    part_in_backbone_component.types = set(part_in_backbone_component.types)
    part_in_backbone_component.roles = set(part_in_backbone_component.roles)
    return part_in_backbone_component, part_in_backbone_seq

def digestion(reactant:sbol3.Component, restriction_enzymes:List[sbol3.ExternallyDefined], assembly_plan:sbol3.Component, **kwargs)-> Tuple[sbol3.Component, sbol3.Sequence]:
    """Digests a Component using the provided restriction enzymes and creates a product Component and a digestion Interaction.
    The product Component is assumed to be the insert for parts in backbone and the backbone for backbones.

    :param reactant: DNA to be digested as SBOL Component, usually a part_in_backbone. 
    :param restriction_enzymes: Restriction enzymes used  Externally Defined.
    :return: A tuple of Component and Interaction.
    """
    if sbol3.SBO_DNA not in reactant.types:
        raise TypeError(f'The reactant should has a DNA type. Types founded {reactant.types}.')
    if len(reactant.sequences)!=1:
        raise ValueError(f'The reactant needs to have precisely one sequence. The input reactant has {len(reactant.sequences)} sequences')
    participations=[]
    restriction_enzymes_pydna=[] 
    for re in restriction_enzymes:
        enzyme = Restriction.__dict__[re.name]
        restriction_enzymes_pydna.append(enzyme)
        modifier_participation = sbol3.Participation(roles=[sbol3.SBO_MODIFIER], participant=re)
        participations.append(modifier_participation)

    # Inform topology to PyDNA, if not found assuming linear. 
    if is_circular(reactant):
        circular=True
        linear=False
    else: 
        circular=False
        linear=True
        
    reactant_seq = reactant.sequences[0].lookup().elements
    # Dseqrecord is from PyDNA package with reactant sequence
    ds_reactant = Dseqrecord(reactant_seq, linear=linear, circular=circular)
    digested_reactant = ds_reactant.cut(restriction_enzymes_pydna)

    if len(digested_reactant)<2 or len(digested_reactant)>3:
        raise NotImplementedError(f'Not supported number of products. Found{len(digested_reactant)}')
    #TODO select them based on content rather than size.
    elif circular and len(digested_reactant)==2:
        part_extract, backbone = sorted(digested_reactant, key=len)
    elif linear and len(digested_reactant)==3:
        prefix, part_extract, suffix = digested_reactant
    else: raise NotImplementedError('The reactant has no valid topology type')
    
    # Extracting roles from features
    reactant_features_roles = []
    for f in reactant.features:
        for r in f.roles:
             reactant_features_roles.append(r)
    # if part
    if any(n==tyto.SO.engineered_insert for n in reactant_features_roles):
        # Compute the length of single strand sticky ends or fusion sites
        product_5_prime_ss_strand, product_5_prime_ss_end = part_extract.seq.five_prime_end()
        product_3_prime_ss_strand, product_3_prime_ss_end = part_extract.seq.three_prime_end()
    
        product_sequence = str(part_extract.seq)
        prod_comp, prod_seq = dna_component_with_sequence(identity=f'{reactant.name}_part_extract', sequence=product_sequence, **kwargs) #str(product_sequence))
        # add sticky ends features
        five_prime_fusion_site_location = sbol3.Range(sequence=product_sequence, start=1, end=len(product_5_prime_ss_end), order=1)
        three_prime_fusion_site_location = sbol3.Range(sequence=product_sequence, start=len(product_sequence)-len(product_3_prime_ss_end)+1, end=len(product_sequence), order=3)
        fusion_sites_feature = sbol3.SequenceFeature(locations=[five_prime_fusion_site_location, three_prime_fusion_site_location], roles=[tyto.SO.insertion_site])
        prod_comp.roles.append(tyto.SO.engineered_insert) 
        prod_comp.features.append(fusion_sites_feature)

    # if backbone
    elif any(n==tyto.SO.deletion for n in reactant_features_roles):
        # Compute the length of single strand sticky ends or fusion sites
        product_5_prime_ss_strand, product_5_prime_ss_end = backbone.seq.five_prime_end()
        product_3_prime_ss_strand, product_3_prime_ss_end = backbone.seq.three_prime_end()
        product_sequence = str(backbone.seq)
        prod_comp, prod_seq = dna_component_with_sequence(identity=f'{reactant.name}_backbone', sequence=product_sequence, **kwargs) #str(product_sequence))
        # add sticky ends features
        five_prime_fusion_site_location = sbol3.Range(sequence=product_sequence, start=1, end=len(product_5_prime_ss_end), order=1)
        three_prime_fusion_site_location = sbol3.Range(sequence=product_sequence, start=len(product_sequence)-len(product_3_prime_ss_end)+1, end=len(product_sequence), order=3)
        fusion_sites_feature = sbol3.SequenceFeature(locations=[five_prime_fusion_site_location, three_prime_fusion_site_location], roles=[tyto.SO.insertion_site])
        prod_comp.roles.append(tyto.SO.plasmid_vector)
        prod_comp.features.append(fusion_sites_feature)

    else: raise NotImplementedError('The reactant has no valid roles')

    #Add reference to part in backbone
    reactant_subcomponent = sbol3.SubComponent(reactant)
    prod_comp.features.append(reactant_subcomponent)
    # Create reactant Participation.
    react_subcomp = sbol3.SubComponent(reactant)
    assembly_plan.features.append(react_subcomp)
    reactant_participation = sbol3.Participation(roles=[sbol3.SBO_REACTANT], participant=react_subcomp)
    participations.append(reactant_participation)
    
    prod_subcomp = sbol3.SubComponent(prod_comp)
    assembly_plan.features.append(prod_subcomp)
    product_participation = sbol3.Participation(roles=[sbol3.SBO_PRODUCT], participant=prod_subcomp)
    participations.append(product_participation)
   
    # Make Interaction
    interaction = sbol3.Interaction(types=[tyto.SBO.cleavage], participations=participations)
    assembly_plan.interactions.append(interaction)
                    
    return prod_comp, prod_seq

def ligation(reactants:List[sbol3.Component], assembly_plan:sbol3.Component)-> List[Tuple[sbol3.Component, sbol3.Sequence]]:
    """Ligates Components using base complementarity and creates a product Component and a ligation Interaction.

    :param reactant: DNA to be ligated as SBOL Component. 
    :return: A tuple of Component and Interaction.
    """
    # Create a dictionary that maps each first and last 4 letters to a list of strings that have those letters.
    reactant_parts = []
    fusion_sites_set = set()
    for reactant in reactants:
        fusion_site_3prime_length = reactant.features[0].locations[0].end - reactant.features[0].locations[0].start
        fusion_site_5prime_length = reactant.features[0].locations[1].end - reactant.features[0].locations[1].start
        if fusion_site_3prime_length == fusion_site_5prime_length:
            fusion_site_length = fusion_site_3prime_length + 1 # if the fusion site is 4 bp long, the start will be 1 and end 4, 4-1 = 3, so we add 1 to get 4.
            fusion_sites_set.add(fusion_site_length)
            if len(fusion_sites_set) > 1:
                raise ValueError(f'Fusion sites of different length within different parts. Check {reactant.identity} ')
        else:
            raise ValueError(f'Fusion sites of different length within the same part. Check {reactant.identity}')
        if tyto.SO.plasmid_vector in reactant.roles:
            reactant_parts.append(reactant)
        elif tyto.SO.engineered_insert in reactant.roles:
            reactant_parts.append(reactant)
        else:
            raise ValueError(f'Part {reactant.identity} does not have a valid role')
    # remove the backbones if any from the reactants, to create the composite
    groups = {}
    for reactant in reactant_parts:
        first_four_letters = reactant.sequences[0].lookup().elements[:fusion_site_length].lower()
        last_four_letters = reactant.sequences[0].lookup().elements[-fusion_site_length:].lower()
        part_syntax = f'{first_four_letters}_{last_four_letters}'
        if part_syntax not in groups:
            groups[part_syntax] = []
            groups[part_syntax].append(reactant)
        else: groups[part_syntax].append(reactant)
    # groups is a dictionary of lists of parts that have the same first and last 4 letters
    # list_of_combinations_per_assembly is a list of tuples of parts that can be ligated together
    list_of_parts_per_combination = list(product(*groups.values())) #cartesian product
    # create list_of_composites_per_assembly from list_of_combinations_per_assembly
    list_of_composites_per_assembly = []
    for combination in list_of_parts_per_combination:
        list_of_parts_per_composite = [combination[0]] 
        insert_sequence = combination[0].sequences[0].lookup().elements
        remaining_parts = list(combination[1:])
        it = 1
        while remaining_parts:   
            remaining_parts_before = len(remaining_parts) 
            for part in remaining_parts:
                # match insert sequence 5' to part 3'
                if part.sequences[0].lookup().elements[:fusion_site_length].lower() == insert_sequence[-fusion_site_length:].lower():
                    insert_sequence = insert_sequence[:-fusion_site_length] + part.sequences[0].lookup().elements
                    list_of_parts_per_composite.append(part)
                    remaining_parts.remove(part)
                # match insert sequence 3' to part 5'
                elif part.sequences[0].lookup().elements[-fusion_site_length:].lower() == insert_sequence[:fusion_site_length].lower():
                    insert_sequence =  part.sequences[0].lookup().elements + insert_sequence[fusion_site_length:]
                    list_of_parts_per_composite.insert(0, part)
                    remaining_parts.remove(part)
                remaining_parts_after = len(remaining_parts)
            
            if remaining_parts_before == remaining_parts_after:
                it += 1
            if it > 5: #5 was chosen arbitrarily to avoid infinite loops
                print(groups)
                raise ValueError('No match found, check the parts and their fusion sites')
        list_of_composites_per_assembly.append(list_of_parts_per_composite)

    # transform list_of_parts_per_assembly into list of composites
    products_list = []
    participations = []
    composite_number = 1
    for composite in list_of_composites_per_assembly: # a composite of the form [A,B,C]
        # calculate sequence
        composite_sequence_str = ""
        composite_name = ""
        #part_subcomponents = []
        part_extract_subcomponents = []
        for part_extract in composite:
            composite_sequence_str = composite_sequence_str + part_extract.sequences[0].lookup().elements[:-fusion_site_length] #needs a version for linear
            # create participations
            part_extract_subcomponent = sbol3.SubComponent(part_extract) # LocalSubComponent??
            part_extract_subcomponents.append(part_extract_subcomponent)
            composite_name = composite_name +'_'+ part_extract.name
        # create dna componente and sequence
        composite_component, composite_seq = dna_component_with_sequence(f'composite_{composite_number}{composite_name}', composite_sequence_str) # **kwarads use in future?
        composite_component.name = f'composite_{composite_number}{composite_name}'
        composite_component.roles.append(sbol3.SO_ENGINEERED_REGION)
        composite_component.features = part_extract_subcomponents
        for i in range(len(composite_component.features )-1):
            composite_component.constraints = [sbol3.Constraint(restriction='http://sbols.org/v3#meets', subject=composite_component.features[i], object=composite_component.features[i+1])]
        products_list.append([composite_component, composite_seq])
        composite_number += 1
    return products_list


class Assembly_plan_composite_in_backbone_single_enzyme():
    """Creates a Assembly Plan.
    :param name: Name of the assembly plan Component.
    :param parts_in_backbone: Parts in backbone to be assembled. 
    :param acceptor_backbone:  Backbone in which parts are inserted on the assembly. 
    :param restriction_enzymes: Restriction enzyme with correct name from Bio.Restriction as Externally Defined.
    :param document: SBOL Document where the assembly plan will be created.
    :param linear: Boolean to inform if the reactant is linear.
    :param circular: Boolean to inform if the reactant is circular.
    :param **kwargs: Keyword arguments of any other Component attribute for the assembled part.
    """

    def __init__(self, name: str, parts_in_backbone: List[sbol3.Component], acceptor_backbone: sbol3.Component, restriction_enzyme: Union[str,sbol3.ExternallyDefined], document:sbol3.Document):
        self.name = name
        self.parts_in_backbone = parts_in_backbone
        self.acceptor_backbone = acceptor_backbone
        self.restriction_enzyme = restriction_enzyme
        self.products = []
        self.extracted_parts = []
        self.document = document

        #create assembly plan
        self.assembly_plan_component = sbol3.Component(identity=f'{self.name}_assembly_plan', types=sbol3.SBO_FUNCTIONAL_ENTITY)
        self.document.add(self.assembly_plan_component)
        self.composites = []

    def run(self):
        self.assembly_plan_component.features.append(self.restriction_enzyme)
        #extract parts
        part_number = 1
        for part_in_backbone in self.parts_in_backbone:
            part_comp, part_seq = digestion(reactant=part_in_backbone,restriction_enzymes=[self.restriction_enzyme], assembly_plan=self.assembly_plan_component, name=f'part_{part_number}_{part_in_backbone.display_id}')
            self.document.add([part_comp, part_seq])
            self.extracted_parts.append(part_comp)
            part_number += 1
        #extract backbone (should be the same?)
        backbone_comp, backbone_seq = digestion(reactant=self.acceptor_backbone,restriction_enzymes=[self.restriction_enzyme], assembly_plan=self.assembly_plan_component,  name=f'part_{part_number}')
        self.document.add([backbone_comp, backbone_seq])
        self.extracted_parts.append(backbone_comp)
        
        #create composite part from extracted parts
        composites_list = ligation(reactants=self.extracted_parts, assembly_plan=self.assembly_plan_component)
        for composite in composites_list:
            composite[0].generated_by.append(self.assembly_plan_component) #
            self.composites.append(composite)
            self.products.append(composite)
            self.document.add(composite)
