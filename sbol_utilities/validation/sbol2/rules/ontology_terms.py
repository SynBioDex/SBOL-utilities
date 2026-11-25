"""Best-practice ontology recommendations: the BioPAX, SO, SBO, and EDAM terms that type and role fields should
draw from (Tables 1, 2, 7, 11 and the ontology branches the specification names)."""

from __future__ import annotations

from sbol_utilities.validation.sbol2 import spec as S
from sbol_utilities.validation.sbol2.context import Obj, Sbol2Context
from sbol_utilities.validation.sbol2.registry import REGISTRY
from sbol_utilities.validation.sbol2.rules.module import ontology_curie


def is_edam_iri(iri: str) -> bool:
    """Whether an IRI names an EDAM term, natively or as an identifiers.org CURIE URL."""
    return (
        iri.startswith("http://edamontology.org/")
        or iri.startswith("https://edamontology.org/")
        or "edam:" in iri
        or "/edam/" in iri
    )


def _count_in_branch(ctx: Sbol2Context, terms: list[str], root: str) -> int:
    return sum(1 for t in terms if ctx.ontology.is_in_branch(ontology_curie(t), root))


def _definition_types(ctx: Sbol2Context, component: Obj) -> list[str] | None:
    definition = ctx.get(component.first_ref(S.DEFINITION))
    return None if definition is None else definition.iris(S.TYPE)


@REGISTRY.rule(
    "sbol2-10503",
    "sbol2-10525",
    "sbol2-10527",
    "sbol2-10528",
    "sbol2-10511",
    "sbol2-10529",
    "sbol2-10706",
    "sbol2-10707",
    "sbol2-11905",
    "sbol2-12007",
    "sbol2-10407",
    "sbol2-11412",
    "sbol2-11507",
    "sbol2-11511",
    "sbol2-13206",
    "sbol2-13505",
)
def ontology_usage(ctx: Sbol2Context) -> None:
    """Type, role, encoding, restriction, language, framework, and format terms come from the recommended
    vocabularies."""
    if not ctx.config.best_practice:
        return
    for obj in ctx.sbol_objects:
        if obj.has_class(S.COMPONENT_DEFINITION):
            _component_definition(ctx, obj)
        if obj.has_class(S.COMPONENT):
            _component(ctx, obj)
        if (
            obj.has_class(S.INTERACTION)
            and _count_in_branch(ctx, obj.iris(S.TYPE), S.SBO_OCCURRING_ENTITY_REPRESENTATION) != 1
        ):
            ctx.warning(
                "sbol2-11905", obj, "an Interaction should contain exactly one occurring-entity SBO type", S.TYPE
            )
        if obj.has_class(S.PARTICIPATION) and _count_in_branch(ctx, obj.iris(S.ROLE), S.SBO_PARTICIPANT_ROLE) != 1:
            ctx.warning(
                "sbol2-12007", obj, "a Participation should contain exactly one participant-role SBO term", S.ROLE
            )
        if obj.has_class(S.SEQUENCE):
            for encoding in obj.iris(S.ENCODING):
                if encoding not in S.TABLE_1_ENCODINGS:
                    ctx.warning(
                        "sbol2-10407", obj, "the encoding of a Sequence should be a URI from Table 1", S.ENCODING
                    )
        if obj.has_class(S.SEQUENCE_CONSTRAINT):
            for restriction in obj.iris(S.RESTRICTION):
                if restriction not in S.TABLE_7_RESTRICTIONS:
                    ctx.warning(
                        "sbol2-11412",
                        obj,
                        "the restriction of a SequenceConstraint should be a URI from Table 7",
                        S.RESTRICTION,
                    )
        if obj.has_class(S.MODEL):
            for language in obj.iris(S.LANGUAGE):
                if not is_edam_iri(language):
                    ctx.warning(
                        "sbol2-11507",
                        obj,
                        "the language of a Model should refer to a term from the EDAM ontology",
                        S.LANGUAGE,
                    )
            for framework in obj.iris(S.FRAMEWORK):
                if not ctx.ontology.is_in_branch(ontology_curie(framework), S.SBO_MODELING_FRAMEWORK):
                    ctx.warning(
                        "sbol2-11511",
                        obj,
                        "the framework of a Model should refer to a term from the SBO modeling-framework branch",
                        S.FRAMEWORK,
                    )
        if obj.has_class(S.ATTACHMENT):
            for fmt in obj.iris(S.FORMAT):
                if not is_edam_iri(fmt):
                    ctx.warning(
                        "sbol2-13206",
                        obj,
                        "the format of an Attachment should refer to a term from the EDAM ontology",
                        S.FORMAT,
                    )
        if obj.has_class(S.OM_MEASURE):
            types = obj.iris(S.TYPE)
            if types and _count_in_branch(ctx, types, S.SBO_SYSTEMS_DESCRIPTION_PARAMETER) != 1:
                ctx.warning(
                    "sbol2-13505",
                    obj,
                    "a Measure with types should carry exactly one systems-description-parameter SBO type",
                    S.TYPE,
                )


def _component_definition(ctx: Sbol2Context, obj: Obj) -> None:
    types = obj.iris(S.TYPE)
    is_region = S.BIOPAX_DNA_REGION in types or S.BIOPAX_RNA_REGION in types
    is_molecule = S.BIOPAX_DNA_MOLECULE in types or S.BIOPAX_RNA_MOLECULE in types
    num_biopax = sum(1 for t in types if t in S.BIOPAX_TYPES)
    if num_biopax == 0:
        ctx.warning("sbol2-10525", obj, "a ComponentDefinition should contain a Table 2 type", S.TYPE)
    elif num_biopax > 1:
        ctx.error("sbol2-10503", obj, "a ComponentDefinition must not contain more than one Table 2 type", S.TYPE)
    num_so = _count_in_branch(ctx, obj.iris(S.ROLE), S.SO_SEQUENCE_FEATURE)
    num_topology = _count_in_branch(ctx, types, S.SO_TOPOLOGY_ATTRIBUTE)
    num_strand = _count_in_branch(ctx, types, S.SO_STRAND_ATTRIBUTE)
    if is_region:
        if num_so != 1:
            ctx.warning(
                "sbol2-10527",
                obj,
                "a DNA/RNA ComponentDefinition should contain exactly one sequence-feature role",
                S.ROLE,
            )
        if num_topology > 1:
            ctx.warning(
                "sbol2-10528", obj, "a DNA/RNA ComponentDefinition should contain at most one topology type", S.TYPE
            )
    elif not is_molecule:
        if num_so != 0:
            ctx.warning(
                "sbol2-10511", obj, "a sequence-feature role should not appear without a DNA or RNA type", S.ROLE
            )
        if num_topology != 0 or num_strand != 0:
            ctx.warning(
                "sbol2-10529", obj, "a topology or strand type should not appear without a DNA or RNA type", S.TYPE
            )


def _component(ctx: Sbol2Context, obj: Obj) -> None:
    definition_types = _definition_types(ctx, obj)
    if definition_types is None:
        return
    is_region = S.BIOPAX_DNA_REGION in definition_types or S.BIOPAX_RNA_REGION in definition_types
    num_so = _count_in_branch(ctx, obj.iris(S.ROLE), S.SO_SEQUENCE_FEATURE)
    if not is_region:
        if num_so != 0:
            ctx.warning(
                "sbol2-10706",
                obj,
                "a Component role should be a sequence-feature term only for DNA/RNA definitions",
                S.ROLE,
            )
    elif num_so > 1:
        ctx.warning("sbol2-10707", obj, "a DNA/RNA Component should contain at most one sequence-feature role", S.ROLE)
