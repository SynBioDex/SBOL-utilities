"""Schema-driven structural rules: property cardinality, value kinds, composite children, closed property sets,
enumerated vocabularies, and positional bounds. All run on every document (the libSBOLj always-on checks)."""

from __future__ import annotations

import re

from rdflib.term import URIRef

from sbol_utilities.validation.sbol2 import spec as S
from sbol_utilities.validation.sbol2.context import Lit, Obj, Sbol2Context, Term, parse_i64
from sbol_utilities.validation.sbol2.registry import REGISTRY

_FLOAT = re.compile(
    r"^[+-]?(?:[0-9]+\.?[0-9]*(?:[eE][+-]?[0-9]+)?|\.[0-9]+(?:[eE][+-]?[0-9]+)?|inf|infinity|nan)$", re.IGNORECASE
)
_DATE_TIME = re.compile(
    r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]+)?(?:Z|[+-][0-9]{2}:[0-9]{2})?$"
)


def value_matches_kind(term: Term, kind: str) -> bool:
    """Whether a value has the lexical shape a property's value kind requires."""
    if kind in (S.URI, S.URL):
        return isinstance(term, URIRef)
    if not isinstance(term, Lit):
        return False
    if kind == S.STRING:
        return True
    if kind in (S.INTEGER, S.LONG):
        return parse_i64(term.value) is not None
    if kind == S.FLOAT:
        return term.value in ("INF", "+INF", "-INF", "NaN") or bool(_FLOAT.match(term.value))
    if kind == S.DATE_TIME:
        return bool(_DATE_TIME.match(term.value))
    return False


def matches_target(obj: Obj, reference: S.Reference) -> bool:
    """Whether an object satisfies the class a reference property targets."""
    if reference.match == S.TARGET_EXACT_TYPE:
        return obj.has_type(reference.target)
    return obj.has_class(reference.target)


_CARDINALITY_MESSAGES = {
    S.EXACTLY_ONE: "must have exactly one value",
    S.ZERO_OR_ONE: "must have zero or one value",
    S.ONE_OR_MORE: "must have one or more values",
}


def _cardinality_violated(cardinality: str, count: int) -> bool:
    if cardinality == S.EXACTLY_ONE:
        return count != 1
    if cardinality == S.ZERO_OR_ONE:
        return count > 1
    if cardinality == S.ONE_OR_MORE:
        return count == 0
    return False


@REGISTRY.rule(*S.field_rules())
def property_table(ctx: Sbol2Context) -> None:
    """Cardinality, value kind, and composite-child resolution of every declared property."""
    catalog = ctx.catalog
    for obj in ctx.sbol_objects:
        for predicate, field in obj.fields.items():
            if field.rule not in catalog:
                continue
            values = obj.values(predicate)
            if _cardinality_violated(field.cardinality, len(values)):
                ctx.error(
                    field.rule,
                    obj,
                    f"property `{predicate}` {_CARDINALITY_MESSAGES[field.cardinality]}; found {len(values)}",
                    property=predicate,
                )
            for value in values:
                if not value_matches_kind(value, field.kind):
                    ctx.error(
                        field.rule,
                        obj,
                        f"property `{predicate}` value does not match expected {field.kind}",
                        property=predicate,
                    )
                    continue
                reference = field.reference
                if reference is None or not reference.local:
                    continue
                target = ctx.get(value)  # type: ignore[arg-type]
                if target is None:
                    ctx.error(
                        field.rule, obj, f"property `{predicate}` refers to missing local child `{value}`", predicate
                    )
                elif not matches_target(target, reference):
                    ctx.error(
                        field.rule,
                        obj,
                        f"property `{predicate}` refers to `{value}`, which is not the expected class",
                        predicate,
                    )


@REGISTRY.rule(*[rule for _, rule in S.CLOSED_PROPERTY_RULES])
def closed_property_sets(ctx: Sbol2Context) -> None:
    """No SBOL 2 property outside an object's class is permitted."""
    for obj in ctx.sbol_objects:
        rule = next((r for cls, r in S.CLOSED_PROPERTY_RULES if obj.has_class(cls)), None)
        if rule is None:
            continue
        allowed = obj.fields
        for predicate in sorted(obj.properties):
            if predicate.startswith(S.SBOL2_NS) and predicate not in allowed:
                ctx.error(rule, obj, f"property `{predicate}` is not permitted on this object's class")


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
                    ctx.error(rule, obj, f"value `{value}` of `{predicate}` is not an allowed term", predicate)
        if obj.has_class(S.COMPONENT) and obj.values(S.ROLE) and not obj.values(S.ROLE_INTEGRATION):
            ctx.error(
                "sbol2-10709",
                obj,
                "a Component that specifies roles must also specify a roleIntegration",
                S.ROLE_INTEGRATION,
            )
        if obj.has_class(S.GENERIC_TOP_LEVEL):
            for value in obj.iris(S.RDF_TYPE_P):
                if value.startswith(S.SBOL2_NS):
                    ctx.error(
                        "sbol2-12303",
                        obj,
                        "the rdfType of a GenericTopLevel must not be in the SBOL 2 namespace",
                        S.RDF_TYPE_P,
                    )


@REGISTRY.rule("sbol2-11102", "sbol2-11103", "sbol2-11104", "sbol2-11202")
def location_bounds(ctx: Sbol2Context) -> None:
    """Range start/end are positive and ordered; Cut positions are non-negative."""
    for obj in ctx.sbol_objects:
        if obj.has_class(S.RANGE):
            start, end = obj.integer(S.START), obj.integer(S.END)
            if start is not None and start < 1:
                ctx.error("sbol2-11102", obj, "the start of a Range must be greater than zero", S.START)
            if end is not None and end < 1:
                ctx.error("sbol2-11103", obj, "the end of a Range must be greater than zero", S.END)
            if start is not None and end is not None and end < start:
                ctx.error("sbol2-11104", obj, "the end of a Range must be greater than or equal to its start", S.END)
        if obj.has_class(S.CUT):
            at = obj.integer(S.AT)
            if at is not None and at < 0:
                ctx.error("sbol2-11202", obj, "the at position of a Cut must be greater than or equal to zero", S.AT)


def regions(ctx: Sbol2Context, obj: Obj, predicate: str = S.LOCATION_P) -> list[tuple]:
    """The ``("range", start, end)`` / ``("cut", at)`` extents of the Locations ``obj`` names under ``predicate``."""
    result: list[tuple] = []
    for location in ctx.children(obj, predicate):
        if location.has_class(S.RANGE):
            start, end = location.integer(S.START), location.integer(S.END)
            if start is not None and end is not None:
                result.append(("range", start, end))
        elif location.has_class(S.CUT):
            at = location.integer(S.AT)
            if at is not None:
                result.append(("cut", at))
    return result
