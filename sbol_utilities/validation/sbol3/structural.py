"""Table-driven structural checks: allowed properties, cardinality, value kinds, and reference targets.

Every object is checked against the property rows of its classes (:data:`spec.CLASS_SPECS`), mirroring sbol-rs
``validate_table_rules`` / ``validate_property_spec``.
"""

from __future__ import annotations

from rdflib.term import BNode, URIRef

from sbol_utilities.validation.sbol3 import spec
from sbol_utilities.validation.sbol3.context import SBOL3Context, SbolObject
from sbol_utilities.validation.sbol3.helpers import object_matches_target, value_matches_kind


def check_property(ctx: SBOL3Context, obj: SbolObject, prop: spec.PropertySpec) -> None:
    """Check one property row against an object's values."""
    values = obj.values(prop.predicate)
    count = len(values)
    if prop.cardinality == spec.EXACTLY_ONE and count != 1:
        ctx.report(
            prop.rule,
            obj,
            f"property `{prop.predicate}` must have exactly one value; found {count}",
            property=prop.predicate,
        )
    elif prop.cardinality == spec.ZERO_OR_ONE and count > 1:
        ctx.report(
            prop.rule,
            obj,
            f"property `{prop.predicate}` must have zero or one value; found {count}",
            property=prop.predicate,
        )
    elif prop.cardinality == spec.ONE_OR_MORE and count == 0:
        ctx.report(prop.rule, obj, f"property `{prop.predicate}` must have one or more values", property=prop.predicate)

    for value in values:
        if not value_matches_kind(value, prop.value_kind):
            ctx.report(
                "sbol3-10111",
                obj,
                f"property `{prop.predicate}` value does not match expected {prop.value_kind}",
                property=prop.predicate,
            )
            continue
        if prop.target is None or not isinstance(value, (URIRef, BNode)):
            continue
        target = ctx.get(value)
        if target is not None:
            if not object_matches_target(target, prop.target):
                ctx.report(
                    "sbol3-10113",
                    obj,
                    f"property `{prop.predicate}` refers to `{value}`, which does not match expected target type",
                    property=prop.predicate,
                )
        elif prop.require_local:
            ctx.report(
                "sbol3-10112",
                obj,
                f"property `{prop.predicate}` refers to missing local child `{value}`",
                property=prop.predicate,
            )


def check_object(ctx: SBOL3Context, obj: SbolObject) -> None:
    """Check every property row that applies to an object."""
    for prop in spec.property_specs_for(obj.rdf_types).values():
        check_property(ctx, obj, prop)
