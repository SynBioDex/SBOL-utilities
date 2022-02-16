import sbol3
import tyto

from sbol_utilities.component import get_subcomponents, get_subcomponents_by_identity

# TODO: Change SBOL_ASSEMBLY_PLAN and sbol3.SBOL_DESIGN to tyto calls after resolution of 
SBOL_ASSEMBLY_PLAN = 'http://sbols.org/v3#assemblyPlan'
ASSEMBLY_TYPES = {sbol3.SBOL_DESIGN, SBOL_ASSEMBLY_PLAN}


def validate_part_in_backbone(pib: sbol3.Component) -> bool:
    """Check if a Component represents a part in backbone

    :param plan: Component being validated
    :return: true if its structure follows the best practices for representing a part in backbone
    """
    subcomps = get_subcomponents(pib)

    has_insert = False
    has_backbone = False

    i = 0
    while (not has_insert or not has_backbone) and i < len(subcomps):
        part = subcomps[i].instance_of.lookup()
        
        if tyto.SO.engineered_insert in subcomps[i].roles or tyto.SO.engineered_insert in part.roles:
            has_insert = True
        elif is_backbone(part):
            has_backbone = True
            
        i = i + 1

    return has_insert and has_backbone


def is_backbone(b: sbol3.Component) -> bool:
    """Check if Component is a backbone

    :param plan: Component being checked
    :return: true if it has an expected role for a backbone
    """
    for role in b.roles:
        if role == tyto.SO.vector_replicon or tyto.SO.vector_replicon.is_ancestor_of(role):
            return True

    return False


def validate_composite_part_assemblies(c: sbol3.Component) -> bool:
    """Check if a Component for a composite part has valid assemblies

    :param plan: Component being validated
    :return: true if its assemblies follows the best practices for representing a composite part
    """
    activities = [g.lookup() for g in c.generated_by]

    invalid_assemblies = [a for a in activities if is_assembly(a) and not validate_assembly(a, c)]

    return len(invalid_assemblies) == 0


def validate_assembly_component(ac: sbol3.Component, composite_part: sbol3.Component) -> bool:
    """Check if Component represents the assembly of a composite part

    :param plan: Component being validated and Component for composite part
    :return: true if it follows best practices for representing assembly of composite part
    """
    assembly_subcomps = get_subcomponents(ac)
    assembly_ids = {str(sc.instance_of) for sc in assembly_subcomps}

    assembled_subcomps = get_subcomponents(composite_part)
    assembled_ids = {str(sc.instance_of) for sc in assembled_subcomps}

    has_composite = composite_part.identity in assembly_ids

    if has_composite:
        for assembly_subcomponent in assembly_subcomps:
            if str(assembly_subcomponent.instance_of) == composite_part.identity:
                composite_subid = assembly_subcomponent.identity

        unassembled = assembled_ids.difference(assembly_ids)

        assembled_subids = {sc.identity for sc in assembly_subcomps if str(sc.instance_of) in assembled_ids}

        # TODO: Change sbol3.SBOL_CONTAINS to tyto call after resolution of 
        contained_map = {str(co.object) : str(co.subject) for co in ac.constraints if co.restriction == sbol3.SBOL_CONTAINS}

        uncontained = assembled_subids.difference(contained_map.keys())
        if composite_subid not in contained_map.keys():
            uncontained.add(composite_subid)

        pib_subids = [contained_map[key] for key in contained_map.keys() 
                      if key in assembled_subids or key == composite_subid]
    else:
        unassembled = assembled_ids.difference(assembly_ids)

        assembled_subids = {sc.identity for sc in assembly_subcomps if str(sc.instance_of) in assembled_ids}

        # TODO: Change sbol3.SBOL_CONTAINS to tyto call after resolution of 
        contained_map = {str(co.object) : str(co.subject) for co in ac.constraints if co.restriction == sbol3.SBOL_CONTAINS}

        uncontained = assembled_subids.difference(contained_map.keys())

        pib_subids = [contained_map[key] for key in contained_map.keys() if key in assembled_subids]

    parts_in_backbones = [sc.instance_of.lookup() for sc in get_subcomponents_by_identity(ac, pib_subids)]

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
    :return: true if it follows best practices for representing assembly of composite part
    """
    # TODO: Change sbol3.SBOL_DESIGN to tyto call after resolution of 

    assembly_comps = [a.document.find(u.entity) for u in a.usage if sbol3.SBOL_DESIGN in u.roles]

    is_assembly_comp_valid = True
    for assembly_comp in assembly_comps:
        if not validate_assembly_component(assembly_comp, composite_part):
            is_assembly_comp_valid = False
    
    return len(assembly_comps) == 1 and is_assembly_comp_valid
