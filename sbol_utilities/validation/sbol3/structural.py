"""Schema-driven structural checks: cardinality, value kinds, and reference targets.

Every object is checked against the properties its classes declare in :data:`spec.SCHEMA`.
"""

from __future__ import annotations

from rdflib.term import BNode, URIRef

from sbol_utilities.validation.sbol3 import spec
from sbol_utilities.validation.sbol3.context import Sbol3Context, Sbol3Object
from sbol_utilities.validation.sbol3.helpers import value_matches_kind
from sbol_utilities.validation.schema import PropertySpec


def check_property(ctx: Sbol3Context, obj: Sbol3Object, declared: PropertySpec) -> None:
    """Check one declared property against an object's values."""
    predicate = declared.predicate
    values = obj.values(predicate)
    if not declared.cardinality.allows(len(values)):
        ctx.report(
            "sbol3-10110",
            obj,
            f"property `{predicate}` must have {declared.cardinality.description}; found {len(values)}",
            property=predicate,
        )
    reference = declared.reference
    for value in values:
        if not value_matches_kind(value, declared.kind):
            ctx.report(
                "sbol3-10111",
                obj,
                f"property `{predicate}` value does not match expected {declared.kind.value}",
                property=predicate,
            )
            continue
        if reference is None or not isinstance(value, (URIRef, BNode)):
            continue
        target = ctx.get(value)
        if target is not None:
            if not target.has_class(reference.target):
                ctx.report(
                    "sbol3-10113",
                    obj,
                    f"property `{predicate}` refers to `{value}`, which does not match expected target type",
                    property=predicate,
                )
        elif reference.local:
            ctx.report(
                "sbol3-10112",
                obj,
                f"property `{predicate}` refers to missing local child `{value}`",
                property=predicate,
            )


def check_object(ctx: Sbol3Context, obj: Sbol3Object) -> None:
    """Check every property an object's classes declare."""
    for declared in spec.SCHEMA.properties_for(obj.rdf_types).values():
        check_property(ctx, obj, declared)
