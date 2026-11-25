"""Component, LocalSubComponent, and ExternallyDefined type/role rules (sbol3-106xx, 110xx, 111xx)."""

from __future__ import annotations

from dataclasses import astuple, dataclass
from itertools import combinations

from rdflib.term import Node

from sbol_utilities.validation.ontology import PROTEIN, SIMPLE_CHEMICAL
from sbol_utilities.validation.sbol3 import spec
from sbol_utilities.validation.sbol3.context import Sbol3Context, Sbol3Object
from sbol_utilities.validation.sbol3.helpers import (
    SO_STRAND_ATTRIBUTE,
    SO_TOPOLOGY_ATTRIBUTE,
    component_type,
    conflicting_pairs,
    exactly_one_known,
    is_nucleic_acid_component_type,
    is_sbo_physical_entity_term,
    known_external_resource,
    sequence_encoding,
)
from sbol_utilities.validation.sbol3.registry import REGISTRY


@dataclass(frozen=True)
class TypeRoleRules:
    """The rule ids one class uses for the type and role checks it shares with other classes.

    A rule that does not exist for the class is None, and its check is skipped.
    """

    table_2_count: str
    type_terms: str
    type_conflicts: str
    topology_count: str
    topology_without_na: str
    table_2_recommendation: str | None = None
    role_type: str | None = None
    role_terms: str | None = None
    sequence_feature_without_na: str | None = None
    sequence_feature_count: str | None = None

    def ids(self) -> list[str]:
        """Every rule id the class has."""
        return [rule for rule in astuple(self) if rule is not None]


COMPONENT_RULES = TypeRoleRules(
    table_2_count="sbol3-10601",
    type_terms="sbol3-10602",
    type_conflicts="sbol3-10605",
    topology_count="sbol3-10607",
    topology_without_na="sbol3-10608",
    role_type="sbol3-10609",
    role_terms="sbol3-10610",
    sequence_feature_without_na="sbol3-10612",
    sequence_feature_count="sbol3-10613",
)
LOCAL_SUB_COMPONENT_RULES = TypeRoleRules(
    table_2_count="sbol3-11001",
    type_terms="sbol3-11002",
    table_2_recommendation="sbol3-11004",
    type_conflicts="sbol3-11005",
    topology_count="sbol3-11007",
    topology_without_na="sbol3-11008",
    role_type="sbol3-11009",
    sequence_feature_without_na="sbol3-11011",
    sequence_feature_count="sbol3-11012",
)
EXTERNALLY_DEFINED_RULES = TypeRoleRules(
    table_2_count="sbol3-11101",
    type_terms="sbol3-11102",
    table_2_recommendation="sbol3-11104",
    type_conflicts="sbol3-11105",
    topology_count="sbol3-11107",
    topology_without_na="sbol3-11108",
)


def _types(obj: Sbol3Object) -> list[str]:
    return [str(i) for i in obj.iris(spec.TYPE)]


def _roles(obj: Sbol3Object) -> list[str]:
    return [str(i) for i in obj.iris(spec.ROLE)]


def _is_nucleic_acid(ctx: Sbol3Context, obj: Sbol3Object) -> bool:
    """Whether one of the object's types is a known DNA or RNA Component type."""
    return any(is_nucleic_acid_component_type(ctx.ontology, t) for t in _types(obj))


def _check_types(ctx: Sbol3Context, obj: Sbol3Object, rules: TypeRoleRules) -> None:
    """Check an object's types against Table 2, the ontology's Component types, and the SO topology and strand
    terms, which accompany a DNA or RNA type."""
    ontology = ctx.ontology
    types = _types(obj)
    if sum(1 for t in types if ontology.is_table_2_component_type(t)) > 1:
        ctx.report(
            rules.table_2_count,
            obj,
            "type property must not contain more than one URI from SBOL Table 2",
            property=spec.TYPE,
        )
    for t in types:
        if ontology.is_component_type_term(t) is False:
            ctx.report(rules.type_terms, obj, f"type `{t}` is not an ontology Component type term", property=spec.TYPE)
        if (
            rules.table_2_recommendation is not None
            and is_sbo_physical_entity_term(ontology, t)
            and not ontology.is_table_2_component_type(t)
        ):
            ctx.report(
                rules.table_2_recommendation,
                obj,
                f"type `{t}` should refer to a term from SBOL Table 2",
                property=spec.TYPE,
            )
    for left, right in conflicting_pairs(ontology, types):
        ctx.report(rules.type_conflicts, obj, f"type `{left}` conflicts with type `{right}`", property=spec.TYPE)
    topologies = [t for t in types if ontology.in_branch_if_known(t, SO_TOPOLOGY_ATTRIBUTE)]
    if _is_nucleic_acid(ctx, obj):
        if len(topologies) > 1:
            ctx.report(
                rules.topology_count,
                obj,
                "DNA/RNA objects should have at most one known SO topology type",
                property=spec.TYPE,
            )
        return
    for t in types:
        if t in topologies or ontology.in_branch_if_known(t, SO_STRAND_ATTRIBUTE):
            ctx.report(
                rules.topology_without_na,
                obj,
                f"type `{t}` is an SO topology or strand term but the object is not explicitly DNA or RNA",
                property=spec.TYPE,
            )


def _check_roles(ctx: Sbol3Context, obj: Sbol3Object, rules: TypeRoleRules) -> None:
    """Check an object's roles against its Table 2 types, the ontology's Component roles, and the SO sequence
    features, of which a DNA or RNA object has one."""
    ontology = ctx.ontology
    roles = _roles(obj)
    table_2_types = [t for t in _types(obj) if ontology.is_table_2_component_type(t)]
    for role in roles:
        if rules.role_terms is not None and ontology.is_component_role_term(role) is False:
            ctx.report(
                rules.role_terms, obj, f"role `{role}` is not an ontology Component role term", property=spec.ROLE
            )
        if rules.role_type is None or not ontology.is_component_role_term(role):
            continue
        answers = [ontology.component_role_compatible_with_component_type(role, t) for t in table_2_types]
        if False in answers and True not in answers:
            ctx.report(
                rules.role_type,
                obj,
                f"role `{role}` is not compatible with the object's known Table 2 type",
                property=spec.ROLE,
            )
    feature_roles = [ontology.is_sequence_feature_role_term(role) for role in roles]
    if not _is_nucleic_acid(ctx, obj):
        if rules.sequence_feature_without_na is not None:
            for role, is_feature_role in zip(roles, feature_roles):
                if is_feature_role:
                    ctx.report(
                        rules.sequence_feature_without_na,
                        obj,
                        f"role `{role}` is an SO sequence feature term but the object is not explicitly DNA or RNA",
                        property=spec.ROLE,
                    )
    elif rules.sequence_feature_count is not None and not exactly_one_known(feature_roles):
        ctx.report(
            rules.sequence_feature_count,
            obj,
            "DNA/RNA objects should have exactly one known SO sequence feature role",
            property=spec.ROLE,
        )


@dataclass(frozen=True)
class SequenceInfo:
    """A Sequence of a Component that is held in the document, with what the rules compare."""

    identity: Node
    #: the preferred IRI of the encoding, when the ontology snapshot knows it as a Sequence encoding
    encoding: str | None
    #: the preferred IRI of the encoding term, or the IRI as written when the snapshot does not know it
    encoding_iri: str | None
    elements: str | None


def _sequence_infos(ctx: Sbol3Context, component: Sbol3Object) -> list[SequenceInfo]:
    infos = []
    for sequence in ctx.referenced(component, spec.HAS_SEQUENCE):
        encoding = sequence.first_iri(spec.ENCODING)
        encoding_iri = None if encoding is None else ctx.ontology.canonicalize(str(encoding))
        infos.append(
            SequenceInfo(
                identity=sequence.identity,
                encoding=None if encoding_iri is None else sequence_encoding(ctx.ontology, encoding_iri),
                encoding_iri=encoding_iri,
                elements=sequence.first_literal(spec.ELEMENTS),
            )
        )
    return infos


def _check_component_sequences(ctx: Sbol3Context, component: Sbol3Object) -> None:
    """Check that a Component's Sequences suit its Table 2 types and agree with one another."""
    ontology = ctx.ontology
    types = [c for c in (component_type(ontology, t) for t in _types(component)) if c is not None]
    cross_listed = [t for t in types if ontology.compatible_sequence_encodings_for_component_type(t)]
    sequences = _sequence_infos(ctx, component)
    encoded = [sequence for sequence in sequences if sequence.encoding is not None]

    def compatible(sequence: SequenceInfo, component_type_iri: str) -> bool:
        return bool(ontology.encoding_compatible_with_component_type(sequence.encoding or "", component_type_iri))

    for t in cross_listed:
        for sequence in encoded:
            if not compatible(sequence, t):
                ctx.report(
                    "sbol3-10614",
                    component,
                    f"Component type `{t}` is not compatible with Sequence `{sequence.identity}` encoding "
                    f"`{sequence.encoding}`",
                    property=spec.HAS_SEQUENCE,
                )
        if sequences and len(encoded) == len(sequences) and not any(compatible(s, t) for s in sequences):
            ctx.report(
                "sbol3-10616",
                component,
                f"Component type `{t}` requires at least one compatible Table 1 Sequence encoding",
                property=spec.HAS_SEQUENCE,
            )
    for left, right in combinations(encoded, 2):
        if ontology.terms_conflict(left.encoding or "", right.encoding or ""):
            ctx.report(
                "sbol3-10615",
                component,
                f"Sequence `{left.identity}` encoding `{left.encoding}` conflicts with Sequence "
                f"`{right.identity}` encoding `{right.encoding}`",
                property=spec.HAS_SEQUENCE,
            )
    with_elements = [s for s in sequences if s.encoding_iri is not None and s.elements is not None]
    for left, right in combinations(with_elements, 2):
        if left.encoding_iri == right.encoding_iri and left.elements != right.elements:
            ctx.report(
                "sbol3-10617",
                component,
                f"Sequences `{left.identity}` and `{right.identity}` use the same encoding but have different "
                "elements",
                property=spec.HAS_SEQUENCE,
            )


@REGISTRY.rule(*COMPONENT_RULES.ids(), "sbol3-10604", "sbol3-10614", "sbol3-10615", "sbol3-10616", "sbol3-10617")
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


@REGISTRY.rule(*LOCAL_SUB_COMPONENT_RULES.ids())
def local_sub_components(ctx: Sbol3Context) -> None:
    """LocalSubComponent types and roles."""
    for obj in ctx.instances(spec.LOCAL_SUB_COMPONENT):
        _check_types(ctx, obj, LOCAL_SUB_COMPONENT_RULES)
        _check_roles(ctx, obj, LOCAL_SUB_COMPONENT_RULES)


#: Component type family -> the external resources recommended for the definition of such an ExternallyDefined
_RECOMMENDED_RESOURCES = {PROTEIN: ("uniprot",), SIMPLE_CHEMICAL: ("chebi", "pubchem")}


@REGISTRY.rule(*EXTERNALLY_DEFINED_RULES.ids(), "sbol3-11109")
def externally_defined(ctx: Sbol3Context) -> None:
    """ExternallyDefined types and recommended definition resources."""
    for obj in ctx.instances(spec.EXTERNALLY_DEFINED):
        _check_types(ctx, obj, EXTERNALLY_DEFINED_RULES)
        definition = obj.first_iri(spec.DEFINITION)
        resource = None if definition is None else known_external_resource(str(definition))
        if resource is None:
            continue
        for t in _types(obj):
            recommended = _RECOMMENDED_RESOURCES.get(ctx.ontology.component_type_family(t) or "")
            if recommended is not None and resource not in recommended:
                ctx.report(
                    "sbol3-11109",
                    obj,
                    f"ExternallyDefined definition `{definition}` uses a resource not recommended for type `{t}`",
                    property=spec.DEFINITION,
                )
