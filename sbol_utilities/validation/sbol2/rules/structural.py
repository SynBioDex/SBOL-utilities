"""Schema-driven structural rules: property cardinality, value kinds, composite children, closed property sets,
enumerated vocabularies, and positional bounds. All run on every document (the libSBOLj always-on checks)."""

from __future__ import annotations

from rdflib.term import URIRef

from sbol_utilities.validation.datatypes import is_date_time_lexical, is_float_lexical, parse_i64
from sbol_utilities.validation.sbol2 import spec as S
from sbol_utilities.validation.sbol2.context import Sbol2Context, Sbol2Literal, Sbol2Object, Term
from sbol_utilities.validation.sbol2.registry import REGISTRY
from sbol_utilities.validation.schema import ValueKind
from sbol_utilities.vocab import SBOL2_NS


def value_matches_kind(term: Term, kind: ValueKind) -> bool:
    """Whether a value has the lexical shape a property's value kind requires."""
    if kind in (ValueKind.URI, ValueKind.URL):
        return isinstance(term, URIRef)
    if not isinstance(term, Sbol2Literal):
        return False
    if kind is ValueKind.STRING:
        return True
    if kind in (ValueKind.INTEGER, ValueKind.LONG):
        return parse_i64(term.value) is not None
    if kind is ValueKind.FLOAT:
        return is_float_lexical(term.value)
    return is_date_time_lexical(term.value)


@REGISTRY.rule(*S.SCHEMA.rules())
def property_table(ctx: Sbol2Context) -> None:
    """Cardinality, value kind, and composite-child resolution of every declared property."""
    for obj in ctx.sbol_objects:
        for predicate, declared in obj.property_specs.items():
            rule = declared.rule
            if rule is None:
                continue
            values = obj.values(predicate)
            if not declared.cardinality.allows(len(values)):
                ctx.report(
                    rule,
                    obj,
                    f"property `{predicate}` must have {declared.cardinality.description}; found {len(values)}",
                    property=predicate,
                )
            for value in values:
                if not value_matches_kind(value, declared.kind):
                    ctx.report(
                        rule,
                        obj,
                        f"property `{predicate}` value does not match expected {declared.kind.value}",
                        property=predicate,
                    )
                    continue
                reference = declared.reference
                if reference is None or not reference.local:
                    continue
                target = ctx.get(value)  # type: ignore[arg-type]
                if target is None:
                    ctx.report(
                        rule, obj, f"property `{predicate}` refers to missing local child `{value}`", property=predicate
                    )
                elif not target.has_class(reference.target):
                    ctx.report(
                        rule,
                        obj,
                        f"property `{predicate}` refers to `{value}`, which is not the expected class",
                        property=predicate,
                    )


@REGISTRY.rule(*[rule for _, rule in S.CLOSED_PROPERTY_RULES])
def closed_property_sets(ctx: Sbol2Context) -> None:
    """No SBOL 2 property outside an object's class is permitted."""
    for obj in ctx.sbol_objects:
        rule = next((r for cls, r in S.CLOSED_PROPERTY_RULES if obj.has_class(cls)), None)
        if rule is None:
            continue
        allowed = obj.property_specs
        for predicate in sorted(obj.properties):
            if predicate.startswith(SBOL2_NS) and predicate not in allowed:
                ctx.report(rule, obj, f"property `{predicate}` is not permitted on this object's class")


_ENUMS = (
    (S.ACCESS, "sbol2-10607", (S.PUBLIC, S.PRIVATE)),
    (S.ROLE_INTEGRATION, "sbol2-10708", (S.MERGE_ROLES, S.OVERRIDE_ROLES)),
    (S.REFINEMENT, "sbol2-10810", (S.VERIFY_IDENTICAL, S.USE_LOCAL, S.USE_REMOTE, S.MERGE)),
    (S.STRATEGY, "sbol2-12902", (S.ENUMERATE, S.SAMPLE)),
    (S.OPERATOR, "sbol2-13003", (S.OP_ZERO_OR_ONE, S.OP_ONE, S.OP_ZERO_OR_MORE, S.OP_ONE_OR_MORE)),
)


@REGISTRY.rule("sbol2-10607", "sbol2-10708", "sbol2-10810", "sbol2-12902", "sbol2-13003", "sbol2-10709", "sbol2-12303")
def controlled_values(ctx: Sbol2Context) -> None:
    """Enumerated properties take values from their fixed tables; related presence and namespace constraints."""
    for obj in ctx.sbol_objects:
        for predicate, rule, allowed in _ENUMS:
            for value in obj.iris(predicate):
                if value not in allowed:
                    ctx.report(
                        rule, obj, f"value `{value}` of `{predicate}` is not an allowed term", property=predicate
                    )
        if obj.has_class(S.COMPONENT) and obj.values(S.ROLE) and not obj.values(S.ROLE_INTEGRATION):
            ctx.report(
                "sbol2-10709",
                obj,
                "a Component that specifies roles must also specify a roleIntegration",
                property=S.ROLE_INTEGRATION,
            )
        if obj.has_class(S.GENERIC_TOP_LEVEL):
            for value in obj.iris(S.RDF_TYPE_P):
                if value.startswith(SBOL2_NS):
                    ctx.report(
                        "sbol2-12303",
                        obj,
                        "the rdfType of a GenericTopLevel must not be in the SBOL 2 namespace",
                        property=S.RDF_TYPE_P,
                    )


@REGISTRY.rule("sbol2-11102", "sbol2-11103", "sbol2-11104", "sbol2-11202")
def location_bounds(ctx: Sbol2Context) -> None:
    """Range start/end are positive and ordered; Cut positions are non-negative."""
    for obj in ctx.sbol_objects:
        if obj.has_class(S.RANGE):
            start, end = obj.integer(S.START), obj.integer(S.END)
            if start is not None and start < 1:
                ctx.report("sbol2-11102", obj, "the start of a Range must be greater than zero", property=S.START)
            if end is not None and end < 1:
                ctx.report("sbol2-11103", obj, "the end of a Range must be greater than zero", property=S.END)
            if start is not None and end is not None and end < start:
                ctx.report(
                    "sbol2-11104", obj, "the end of a Range must be greater than or equal to its start", property=S.END
                )
        if obj.has_class(S.CUT):
            at = obj.integer(S.AT)
            if at is not None and at < 0:
                ctx.report(
                    "sbol2-11202", obj, "the at position of a Cut must be greater than or equal to zero", property=S.AT
                )


def regions(ctx: Sbol2Context, obj: Sbol2Object, predicate: str = S.LOCATION_P) -> list[tuple]:
    """The ``("range", start, end)`` / ``("cut", at)`` extents of the Locations ``obj`` names under ``predicate``."""
    result: list[tuple] = []
    for location in ctx.referenced(obj, predicate):
        if location.has_class(S.RANGE):
            start, end = location.integer(S.START), location.integer(S.END)
            if start is not None and end is not None:
                result.append(("range", start, end))
        elif location.has_class(S.CUT):
            at = location.integer(S.AT)
            if at is not None:
                result.append(("cut", at))
    return result
