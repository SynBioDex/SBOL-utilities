"""Best-practice ontology recommendations: the BioPAX, SO, SBO, and EDAM terms that type and role fields should
draw from (Tables 1, 2, 7, 11 and the ontology branches the specification names)."""

from __future__ import annotations

from collections.abc import Callable

from sbol_utilities.validation.sbol2 import spec as S
from sbol_utilities.validation.sbol2.context import Sbol2Context
from sbol_utilities.validation.sbol2.helpers import is_nucleic_acid_region, ontology_curie
from sbol_utilities.validation.sbol2.registry import REGISTRY


def is_edam_iri(iri: str) -> bool:
    """Whether an IRI names an EDAM term, natively or as an identifiers.org CURIE URL."""
    return (
        iri.startswith(("http://edamontology.org/", "https://edamontology.org/")) or "edam:" in iri or "/edam/" in iri
    )


def _count_in_branch(ctx: Sbol2Context, terms: list[str], root: str) -> int:
    return sum(1 for t in terms if ctx.ontology.is_in_branch(ontology_curie(t), root))


def _in_modeling_framework_branch(ctx: Sbol2Context, iri: str) -> bool:
    return ctx.ontology.is_in_branch(ontology_curie(iri), S.SBO_MODELING_FRAMEWORK)


#: (class, property, rule, whether a value is a recommended term, message): every value should be recommended
_RECOMMENDED_TERMS: tuple[tuple[str, str, str, Callable[[Sbol2Context, str], bool], str], ...] = (
    (
        S.SEQUENCE,
        S.ENCODING,
        "sbol2-10407",
        lambda ctx, iri: iri in S.TABLE_1_ENCODINGS,
        "the encoding of a Sequence should be a URI from Table 1",
    ),
    (
        S.SEQUENCE_CONSTRAINT,
        S.RESTRICTION,
        "sbol2-11412",
        lambda ctx, iri: iri in S.TABLE_7_RESTRICTIONS,
        "the restriction of a SequenceConstraint should be a URI from Table 7",
    ),
    (
        S.MODEL,
        S.LANGUAGE,
        "sbol2-11507",
        lambda ctx, iri: is_edam_iri(iri),
        "the language of a Model should refer to a term from the EDAM ontology",
    ),
    (
        S.MODEL,
        S.FRAMEWORK,
        "sbol2-11511",
        _in_modeling_framework_branch,
        "the framework of a Model should refer to a term from the SBO modeling-framework branch",
    ),
    (
        S.ATTACHMENT,
        S.FORMAT,
        "sbol2-13206",
        lambda ctx, iri: is_edam_iri(iri),
        "the format of an Attachment should refer to a term from the EDAM ontology",
    ),
)


@REGISTRY.rule(*(rule for _, _, rule, _, _ in _RECOMMENDED_TERMS))
def recommended_terms(ctx: Sbol2Context) -> None:
    """Encoding, restriction, language, framework, and format terms come from the recommended vocabularies."""
    for class_iri, predicate, rule, recommended, message in _RECOMMENDED_TERMS:
        for obj in ctx.instances(class_iri):
            if not all(recommended(ctx, iri) for iri in obj.iris(predicate)):
                ctx.report(rule, obj, message, property=predicate)


#: (class, property, ontology branch, rule, message): exactly one value should lie in the branch
_ONE_TERM_IN_BRANCH = (
    (
        S.INTERACTION,
        S.TYPE,
        S.SBO_OCCURRING_ENTITY_REPRESENTATION,
        "sbol2-11905",
        "an Interaction should contain exactly one occurring-entity SBO type",
    ),
    (
        S.PARTICIPATION,
        S.ROLE,
        S.SBO_PARTICIPANT_ROLE,
        "sbol2-12007",
        "a Participation should contain exactly one participant-role SBO term",
    ),
)


@REGISTRY.rule(*(rule for _, _, _, rule, _ in _ONE_TERM_IN_BRANCH))
def single_branch_terms(ctx: Sbol2Context) -> None:
    """An Interaction has one occurring-entity type and a Participation one participant role."""
    for class_iri, predicate, branch_root, rule, message in _ONE_TERM_IN_BRANCH:
        for obj in ctx.instances(class_iri):
            if _count_in_branch(ctx, obj.iris(predicate), branch_root) != 1:
                ctx.report(rule, obj, message, property=predicate)


@REGISTRY.rule("sbol2-13505")
def measure_types(ctx: Sbol2Context) -> None:
    """A Measure that has types has exactly one from the SBO systems-description-parameter branch."""
    for obj in ctx.instances(S.OM_MEASURE):
        types = obj.iris(S.TYPE)
        if types and _count_in_branch(ctx, types, S.SBO_SYSTEMS_DESCRIPTION_PARAMETER) != 1:
            ctx.report(
                "sbol2-13505",
                obj,
                "a Measure with types should carry exactly one systems-description-parameter SBO type",
                property=S.TYPE,
            )


@REGISTRY.rule("sbol2-10503", "sbol2-10525")
def component_definition_table_2_types(ctx: Sbol2Context) -> None:
    """A ComponentDefinition has exactly one Table 2 (BioPAX) type."""
    for obj in ctx.instances(S.COMPONENT_DEFINITION):
        count = sum(1 for t in obj.iris(S.TYPE) if t in S.BIOPAX_TYPES)
        if count == 0:
            ctx.report("sbol2-10525", obj, "a ComponentDefinition should contain a Table 2 type", property=S.TYPE)
        elif count > 1:
            ctx.report(
                "sbol2-10503", obj, "a ComponentDefinition must not contain more than one Table 2 type", property=S.TYPE
            )


@REGISTRY.rule("sbol2-10527", "sbol2-10528", "sbol2-10511", "sbol2-10529")
def component_definition_sequence_terms(ctx: Sbol2Context) -> None:
    """Sequence-feature roles and topology or strand types accompany a DNA or RNA type, in the expected numbers."""
    for obj in ctx.instances(S.COMPONENT_DEFINITION):
        types = obj.iris(S.TYPE)
        feature_roles = _count_in_branch(ctx, obj.iris(S.ROLE), S.SO_SEQUENCE_FEATURE)
        topologies = _count_in_branch(ctx, types, S.SO_TOPOLOGY_ATTRIBUTE)
        if is_nucleic_acid_region(types):
            if feature_roles != 1:
                ctx.report(
                    "sbol2-10527",
                    obj,
                    "a DNA/RNA ComponentDefinition should contain exactly one sequence-feature role",
                    property=S.ROLE,
                )
            if topologies > 1:
                ctx.report(
                    "sbol2-10528",
                    obj,
                    "a DNA/RNA ComponentDefinition should contain at most one topology type",
                    property=S.TYPE,
                )
        elif S.BIOPAX_DNA_MOLECULE not in types and S.BIOPAX_RNA_MOLECULE not in types:
            if feature_roles:
                ctx.report(
                    "sbol2-10511",
                    obj,
                    "a sequence-feature role should not appear without a DNA or RNA type",
                    property=S.ROLE,
                )
            if topologies or _count_in_branch(ctx, types, S.SO_STRAND_ATTRIBUTE):
                ctx.report(
                    "sbol2-10529",
                    obj,
                    "a topology or strand type should not appear without a DNA or RNA type",
                    property=S.TYPE,
                )


@REGISTRY.rule("sbol2-10706", "sbol2-10707")
def component_sequence_feature_roles(ctx: Sbol2Context) -> None:
    """A Component has a sequence-feature role only when its definition is DNA or RNA, and then at most one."""
    for obj in ctx.instances(S.COMPONENT):
        definition = ctx.get(obj.first_iri(S.DEFINITION))
        if definition is None:
            continue
        feature_roles = _count_in_branch(ctx, obj.iris(S.ROLE), S.SO_SEQUENCE_FEATURE)
        if not is_nucleic_acid_region(definition.iris(S.TYPE)):
            if feature_roles:
                ctx.report(
                    "sbol2-10706",
                    obj,
                    "a Component role should be a sequence-feature term only for DNA/RNA definitions",
                    property=S.ROLE,
                )
        elif feature_roles > 1:
            ctx.report(
                "sbol2-10707",
                obj,
                "a DNA/RNA Component should contain at most one sequence-feature role",
                property=S.ROLE,
            )
