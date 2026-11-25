"""Component, LocalSubComponent, and ExternallyDefined type/role rules (sbol3-106xx, 110xx, 111xx)."""

from __future__ import annotations

from dataclasses import dataclass

from rdflib.term import Node

from sbol_utilities.validation.ontology import PROTEIN, SIMPLE_CHEMICAL
from sbol_utilities.validation.sbol3 import spec
from sbol_utilities.validation.sbol3.context import Sbol3Context, Sbol3Object
from sbol_utilities.validation.sbol3.helpers import (
    SO_STRAND_ATTRIBUTE,
    SO_TOPOLOGY_ATTRIBUTE,
    component_type,
    is_nucleic_acid_component_type,
    is_sbo_physical_entity_term,
    known_external_resource,
    sequence_encoding,
)
from sbol_utilities.validation.sbol3.registry import REGISTRY

#: rule ids by check, for Component / LocalSubComponent / ExternallyDefined
COMPONENT_RULES = {
    "table_2_count": "sbol3-10601",
    "type_terms": "sbol3-10602",
    "type_conflicts": "sbol3-10605",
    "topology_count": "sbol3-10607",
    "topology_without_na": "sbol3-10608",
    "role_type": "sbol3-10609",
    "role_terms": "sbol3-10610",
    "sequence_feature_without_na": "sbol3-10612",
    "sequence_feature_count": "sbol3-10613",
}
LOCAL_SUB_COMPONENT_RULES = {
    "table_2_count": "sbol3-11001",
    "type_terms": "sbol3-11002",
    "table_2_recommendation": "sbol3-11004",
    "type_conflicts": "sbol3-11005",
    "topology_count": "sbol3-11007",
    "topology_without_na": "sbol3-11008",
    "role_type": "sbol3-11009",
    "sequence_feature_without_na": "sbol3-11011",
    "sequence_feature_count": "sbol3-11012",
}
EXTERNALLY_DEFINED_RULES = {
    "table_2_count": "sbol3-11101",
    "type_terms": "sbol3-11102",
    "table_2_recommendation": "sbol3-11104",
    "type_conflicts": "sbol3-11105",
    "topology_count": "sbol3-11107",
    "topology_without_na": "sbol3-11108",
}


def _types(obj: Sbol3Object) -> list[str]:
    return [str(i) for i in obj.iris(spec.TYPE)]


def _roles(obj: Sbol3Object) -> list[str]:
    return [str(i) for i in obj.iris(spec.ROLE)]


def _is_nucleic_acid(ctx: Sbol3Context, obj: Sbol3Object) -> bool:
    return any(is_nucleic_acid_component_type(ctx.ontology, t) for t in _types(obj))


def _check_types(ctx: Sbol3Context, obj: Sbol3Object, rules: dict) -> None:
    ontology = ctx.ontology
    types = _types(obj)
    if sum(1 for t in types if ontology.is_table_2_component_type(t)) > 1:
        ctx.report(
            rules["table_2_count"],
            obj,
            "type property must not contain more than one URI from SBOL Table 2",
            property=spec.TYPE,
        )
    for t in types:
        if ontology.is_component_type_term(t) is False:
            ctx.report(
                rules["type_terms"], obj, f"type `{t}` is not an ontology Component type term", property=spec.TYPE
            )
    if "table_2_recommendation" in rules:
        for t in types:
            if is_sbo_physical_entity_term(ontology, t) is True and not ontology.is_table_2_component_type(t):
                ctx.report(
                    rules["table_2_recommendation"],
                    obj,
                    f"type `{t}` should refer to a term from SBOL Table 2",
                    property=spec.TYPE,
                )
    for index, left in enumerate(types):
        for right in types[index + 1 :]:
            if ontology.terms_conflict(left, right) is True:
                ctx.report(
                    rules["type_conflicts"], obj, f"type `{left}` conflicts with type `{right}`", property=spec.TYPE
                )
    nucleic_acid = _is_nucleic_acid(ctx, obj)
    if nucleic_acid:
        if sum(1 for t in types if ontology.in_branch_if_known(t, SO_TOPOLOGY_ATTRIBUTE) is True) > 1:
            ctx.report(
                rules["topology_count"],
                obj,
                "DNA/RNA objects should have at most one known SO topology type",
                property=spec.TYPE,
            )
    else:
        for t in types:
            if (
                ontology.in_branch_if_known(t, SO_TOPOLOGY_ATTRIBUTE) is True
                or ontology.in_branch_if_known(t, SO_STRAND_ATTRIBUTE) is True
            ):
                ctx.report(
                    rules["topology_without_na"],
                    obj,
                    f"type `{t}` is an SO topology or strand term but the object is not explicitly DNA or RNA",
                    property=spec.TYPE,
                )


def _check_roles(ctx: Sbol3Context, obj: Sbol3Object, rules: dict) -> None:
    ontology = ctx.ontology
    types = _types(obj)
    roles = _roles(obj)
    table_2_types = [t for t in types if ontology.is_table_2_component_type(t)]
    if table_2_types:
        for role in roles:
            if ontology.is_component_role_term(role) is not True:
                continue
            decidable = compatible = False
            for t in table_2_types:
                answer = ontology.component_role_compatible_with_component_type(role, t)
                if answer is True:
                    decidable = compatible = True
                elif answer is False:
                    decidable = True
            if decidable and not compatible:
                ctx.report(
                    rules["role_type"],
                    obj,
                    f"role `{role}` is not compatible with the object's known Table 2 type",
                    property=spec.ROLE,
                )
    if "role_terms" in rules:
        for role in roles:
            if ontology.is_component_role_term(role) is False:
                ctx.report(
                    rules["role_terms"],
                    obj,
                    f"role `{role}` is not an ontology Component role term",
                    property=spec.ROLE,
                )
    if not _is_nucleic_acid(ctx, obj):
        for role in roles:
            if ontology.is_sequence_feature_role_term(role) is True:
                ctx.report(
                    rules["sequence_feature_without_na"],
                    obj,
                    f"role `{role}` is an SO sequence feature term but the object is not explicitly DNA or RNA",
                    property=spec.ROLE,
                )
    else:
        count = 0
        unknown = False
        for role in roles:
            answer = ontology.is_sequence_feature_role_term(role)
            if answer is True:
                count += 1
            elif answer is None:
                unknown = True
        if count > 1 or (count == 0 and not unknown):
            ctx.report(
                rules["sequence_feature_count"],
                obj,
                "DNA/RNA objects should have exactly one known SO sequence feature role",
                property=spec.ROLE,
            )


@dataclass
class SequenceInfo:
    """A Component's local Sequence with its canonical encoding."""

    identity: Node
    encoding: str | None
    encoding_iri: str | None
    elements: str | None


def _sequence_infos(ctx: Sbol3Context, component: Sbol3Object) -> list[SequenceInfo]:
    infos = []
    for identity in component.resources(spec.HAS_SEQUENCE):
        sequence = ctx.get(identity)
        if sequence is None:
            continue
        encoding = sequence.first_iri(spec.ENCODING)
        encoding_iri = None
        if encoding is not None:
            encoding_iri = ctx.ontology.canonicalize(str(encoding))
        infos.append(
            SequenceInfo(
                identity=identity,
                encoding=None if encoding_iri is None else sequence_encoding(ctx.ontology, encoding_iri),
                encoding_iri=encoding_iri,
                elements=sequence.first_literal(spec.ELEMENTS),
            )
        )
    return infos


def _check_component_sequences(ctx: Sbol3Context, component: Sbol3Object) -> None:
    ontology = ctx.ontology
    types = [c for c in (component_type(ontology, t) for t in _types(component)) if c is not None]
    sequences = _sequence_infos(ctx, component)
    cross_listed = [t for t in types if ontology.compatible_sequence_encodings_for_component_type(t)]

    def compatible(encoding: str, component_type_iri: str) -> bool:
        return ontology.encoding_compatible_with_component_type(encoding, component_type_iri) is True

    for t in cross_listed:
        for sequence in sequences:
            if sequence.encoding is not None and not compatible(sequence.encoding, t):
                ctx.report(
                    "sbol3-10614",
                    component,
                    f"Component type `{t}` is not compatible with Sequence `{sequence.identity}` encoding "
                    f"`{sequence.encoding}`",
                    property=spec.HAS_SEQUENCE,
                )
    for index, left in enumerate(sequences):
        if left.encoding is None:
            continue
        for right in sequences[index + 1 :]:
            if right.encoding is None:
                continue
            if ontology.terms_conflict(left.encoding, right.encoding) is True:
                ctx.report(
                    "sbol3-10615",
                    component,
                    f"Sequence `{left.identity}` encoding `{left.encoding}` conflicts with Sequence "
                    f"`{right.identity}` encoding `{right.encoding}`",
                    property=spec.HAS_SEQUENCE,
                )
    if sequences and all(s.encoding is not None for s in sequences):
        for t in cross_listed:
            if not any(compatible(s.encoding, t) for s in sequences if s.encoding is not None):
                ctx.report(
                    "sbol3-10616",
                    component,
                    f"Component type `{t}` requires at least one compatible Table 1 Sequence encoding",
                    property=spec.HAS_SEQUENCE,
                )
    for index, left in enumerate(sequences):
        if left.encoding_iri is None or left.elements is None:
            continue
        for right in sequences[index + 1 :]:
            if right.encoding_iri is None or right.elements is None:
                continue
            if left.encoding_iri == right.encoding_iri and left.elements != right.elements:
                ctx.report(
                    "sbol3-10617",
                    component,
                    f"Sequences `{left.identity}` and `{right.identity}` use the same encoding but have different "
                    "elements",
                    property=spec.HAS_SEQUENCE,
                )


@REGISTRY.rule(
    "sbol3-10601",
    "sbol3-10602",
    "sbol3-10604",
    "sbol3-10605",
    "sbol3-10607",
    "sbol3-10608",
    "sbol3-10609",
    "sbol3-10610",
    "sbol3-10612",
    "sbol3-10613",
    "sbol3-10614",
    "sbol3-10615",
    "sbol3-10616",
    "sbol3-10617",
)
def components(ctx: Sbol3Context) -> None:
    """Component types, roles, and Sequence compatibility."""
    for obj in ctx.instances(spec.COMPONENT):
        _check_types(ctx, obj, COMPONENT_RULES)
        for t in _types(obj):
            if is_sbo_physical_entity_term(ctx.ontology, t) is False:
                ctx.report(
                    "sbol3-10604",
                    obj,
                    f"Component type `{t}` should refer to a term from the SBO physical entity representation "
                    "branch (SBO:0000236)",
                    property=spec.TYPE,
                )
        _check_roles(ctx, obj, COMPONENT_RULES)
        _check_component_sequences(ctx, obj)


@REGISTRY.rule(
    "sbol3-11001",
    "sbol3-11002",
    "sbol3-11004",
    "sbol3-11005",
    "sbol3-11007",
    "sbol3-11008",
    "sbol3-11009",
    "sbol3-11011",
    "sbol3-11012",
)
def local_sub_components(ctx: Sbol3Context) -> None:
    """LocalSubComponent types and roles."""
    for obj in ctx.instances(spec.LOCAL_SUB_COMPONENT):
        _check_types(ctx, obj, LOCAL_SUB_COMPONENT_RULES)
        _check_roles(ctx, obj, LOCAL_SUB_COMPONENT_RULES)


@REGISTRY.rule(
    "sbol3-11101",
    "sbol3-11102",
    "sbol3-11104",
    "sbol3-11105",
    "sbol3-11107",
    "sbol3-11108",
    "sbol3-11109",
)
def externally_defined(ctx: Sbol3Context) -> None:
    """ExternallyDefined types and recommended definition resources."""
    for obj in ctx.instances(spec.EXTERNALLY_DEFINED):
        _check_types(ctx, obj, EXTERNALLY_DEFINED_RULES)
        definition = obj.first_iri(spec.DEFINITION)
        if definition is None:
            continue
        resource = known_external_resource(str(definition))
        if resource is None:
            continue
        for t in _types(obj):
            family = ctx.ontology.component_type_family(t)
            mismatch = (family == PROTEIN and resource != "uniprot") or (
                family == SIMPLE_CHEMICAL and resource not in ("chebi", "pubchem")
            )
            if mismatch:
                ctx.report(
                    "sbol3-11109",
                    obj,
                    f"ExternallyDefined definition `{definition}` uses a resource not recommended for type `{t}`",
                    property=spec.DEFINITION,
                )
