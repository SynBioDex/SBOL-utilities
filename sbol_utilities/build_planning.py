import sbol3
import tyto

from sbol_utilities.component import get_subcomponents, get_subcomponents_by_identity
from sbol_utilities.helper_functions import is_plasmid

# TODO: Delete SBOL_ASSEMBLY_PLAN and change its references to tyto.SBOL3.assemblyPlan once tyto supports the
# Design-Build-Test-Learn portion of the SBOL3 ontology
# See issues https://github.com/SynBioDex/tyto/issues/56 and https://github.com/SynBioDex/sbol-owl3/issues/5
SBOL_ASSEMBLY_PLAN = 'http://sbols.org/v3#assemblyPlan'
ASSEMBLY_TYPES = {sbol3.SBOL_DESIGN, SBOL_ASSEMBLY_PLAN}


def validate_part_in_backbone(pib: sbol3.Component) -> bool:
    """Check if a Component represents a part in backbone

    :param plan: Component being validated
    :return: true if it has SubComponents for one insert and one vector backbone
    """
    subcomps = get_subcomponents(pib)

    comps = [sc.instance_of.lookup() for sc in subcomps]

    # Get Components for SubComponents of part in backbone that have engineered_insert as one of their roles
    # (that is, a role of either the Component or its SubComponent instance)
    inserts = [comps[i] for i in range(0, len(comps))
               if tyto.SO.engineered_insert in subcomps[i].roles or tyto.SO.engineered_insert in comps[i].roles]
    
    # Get Components for SubComponents of part in backbone that are plasmids according to their roles
    # (that is, the roles of the Components)
    backbones = [c for c in comps if is_plasmid(c)]

    return len(inserts) == 1 and len(backbones) == 1


def validate_composite_part_assemblies(c: sbol3.Component) -> bool:
    """Check if a Component for a composite part has only valid assemblies

    :param plan: Component being validated
    :return: true if all of its assemblies are valid (see validate_assembly)
    """
    activities = [g.lookup() for g in c.generated_by]

    invalid_assemblies = [a for a in activities if is_assembly(a) and not validate_assembly(a, c)]

    return len(invalid_assemblies) == 0


def validate_assembly_component(ac: sbol3.Component, composite_part: sbol3.Component) -> bool:
    """Check if Component represents the assembly of a composite part

    :param plan: Component being validated and Component for composite part
    :return: true if it has (1) SubComponents for the composite part and its assembled parts
    (2) SubComponents for these parts in their backbones, and
    (3) a contains Constraint for each part in backbone and its insert. 
    """
    # Get identities of Components that are SubComponents of the assembly Component
    assembly_subcomps = get_subcomponents(ac)
    assembly_ids = {str(sc.instance_of) for sc in assembly_subcomps}

    # Get identities of Components for assembled parts that are SubComponents of the composite part
    assembled_subcomps = get_subcomponents(composite_part)
    assembled_ids = {str(sc.instance_of) for sc in assembled_subcomps}

    # Check whether composite part is SubComponent of the assembly Component
    has_composite = composite_part.identity in assembly_ids

    # Determine identities of Components for assembled parts that are not SubComponents of the assembly Component
    unassembled = assembled_ids.difference(assembly_ids)

    # Get identities of SubComponents for composite part and assembled parts in the assembly Component
    for assembly_subcomponent in assembly_subcomps:
        if str(assembly_subcomponent.instance_of) == composite_part.identity:
            composite_subid = assembly_subcomponent.identity

    assembled_subids = {sc.identity for sc in assembly_subcomps if str(sc.instance_of) in assembled_ids}

    # Build map from object to subject SubComponent identities for all contains Constraints in the assembly Component
    # TODO: Change sbol3.SBOL_CONTAINS to tyto.SBOL3.contains once tyto supports SBOL3 constraint restrictions
    # See issues https://github.com/SynBioDex/tyto/issues/55 and https://github.com/SynBioDex/sbol-owl3/issues/4
    contained_map = {str(co.object) : str(co.subject) for co in ac.constraints if co.restriction == sbol3.SBOL_CONTAINS}

    # Determine identities of SubComponents for assembly parts that are not the object of a contains Constraint
    uncontained = assembled_subids.difference(contained_map.keys())

    # Add identity of SubComoponent for composite part to uncontained set if it is not the object of contains Constraint
    if has_composite:
        if composite_subid not in contained_map.keys():
            uncontained.add(composite_subid)


    # Get identities of SubComponents for parts in backbones that contain an assembled part or composite part
    pib_subids = [contained_map[key] for key in contained_map.keys() 
                  if key in assembled_subids or (has_composite and key == composite_subid)]

    # Get identities of Components for parts in backbones
    parts_in_backbones = [sc.instance_of.lookup() for sc in get_subcomponents_by_identity(ac, pib_subids)]

    # Determine which part in backbone Components are invalid
    invalid_parts_in_backbones = [pib for pib in parts_in_backbones if not validate_part_in_backbone(pib)]
  
    # ligations = [i for i in assembly_comps[0].interactions if tyto.SBO.conversion in i.types]

    # digestions = [i for i in assembly_comps[0].interactions if tyto.SBO.cleavage in i.types]

    return (len(unassembled) == 0 and len(uncontained) == 0 and has_composite 
            and len(invalid_parts_in_backbones) == 0)


def is_assembly(a: sbol3.Activity) -> bool:
    """Check if Activity is an assembly

    :param plan: Activity being checked
    :return: true if it has the expected types for an assembly
    """
    return set(ASSEMBLY_TYPES).issubset(a.types)


def validate_assembly(a: sbol3.Activity, composite_part: sbol3.Component) -> bool:
    """Check if Activity represents the assembly of a composite part

    :param plan: Activity being validated and Component for composite part
    :return: true if it uses a single valid assembly Component (see validate_assembly_component)
    """
    # TODO: Change sbol3.SBOL_Design to tyto.SBOL3.design once tyto supports the
    # Design-Build-Test-Learn portion of the SBOL3 ontology
    # See issues https://github.com/SynBioDex/tyto/issues/56 and https://github.com/SynBioDex/sbol-owl3/issues/5
    assembly_comps = [a.document.find(u.entity) for u in a.usage if sbol3.SBOL_DESIGN in u.roles]

    is_assembly_comp_valid = True
    for assembly_comp in assembly_comps:
        if not validate_assembly_component(assembly_comp, composite_part):
            is_assembly_comp_valid = False
    
    return len(assembly_comps) == 1 and is_assembly_comp_valid
