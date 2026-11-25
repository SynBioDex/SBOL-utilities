"""Constraint rules (sbol3-117xx)."""

from __future__ import annotations

from collections.abc import Iterator

from sbol_utilities.validation.sbol3 import spec
from sbol_utilities.validation.sbol3.context import Sbol3Context, Sbol3Object
from sbol_utilities.validation.sbol3.registry import REGISTRY
from sbol_utilities.validation.sbol3.resolver import Outcome, table8_relation, table10_relation


def _contained_constraints(ctx: Sbol3Context) -> Iterator[tuple[Sbol3Object, Sbol3Object]]:
    """Each Constraint held by a Component, with that Component."""
    for obj in ctx.instances(spec.CONSTRAINT):
        component = ctx.parent(obj, spec.HAS_CONSTRAINT)
        if component is not None:
            yield obj, component


@REGISTRY.rule("sbol3-11701", "sbol3-11702", "sbol3-11703")
def constraint_features(ctx: Sbol3Context) -> None:
    """A Constraint relates two different Features of the Component that holds it."""
    for obj, component in _contained_constraints(ctx):
        features = component.resources(spec.HAS_FEATURE)
        subject, constrained = obj.first_resource(spec.SUBJECT), obj.first_resource(spec.OBJECT)
        if subject is not None and subject not in features:
            ctx.report(
                "sbol3-11701",
                obj,
                "Constraint subject must be a Feature of the containing Component",
                property=spec.SUBJECT,
            )
        if constrained is not None and constrained not in features:
            ctx.report(
                "sbol3-11702",
                obj,
                "Constraint object must be a Feature of the containing Component",
                property=spec.OBJECT,
            )
        # a Constraint with neither a subject nor an object is reported here as well as for the missing properties
        if subject == constrained:
            ctx.report(
                "sbol3-11703", obj, "Constraint subject and object must not be the same Feature", property=spec.OBJECT
            )


@REGISTRY.rule("sbol3-11704", "sbol3-11705", "sbol3-11706")
def constraint_restrictions(ctx: Sbol3Context) -> None:
    """A Constraint's restriction is an SBOL relation that the document's Features and Locations do not contradict."""
    for obj, _ in _contained_constraints(ctx):
        restriction = obj.first_iri(spec.RESTRICTION)
        if restriction is None:
            continue
        restriction_text = str(restriction)
        if restriction_text not in spec.RESTRICTION_IRIS:
            ctx.report(
                "sbol3-11704",
                obj,
                f"Constraint restriction `{restriction_text}` is not a recommended SBOL relation",
                property=spec.RESTRICTION,
            )
        subject, constrained = obj.first_resource(spec.SUBJECT), obj.first_resource(spec.OBJECT)
        if subject is None or constrained is None:
            continue
        if table8_relation(ctx, restriction_text, subject, constrained).outcome is Outcome.CONTRADICTED:
            ctx.report(
                "sbol3-11705",
                obj,
                f"Constraint restriction `{restriction_text}` is contradicted by resolved Feature semantics",
                property=spec.RESTRICTION,
            )
        sequential = table10_relation(ctx, restriction_text, subject, constrained)
        if sequential.outcome is Outcome.CONTRADICTED:
            ctx.report(
                "sbol3-11706",
                obj,
                f"Constraint restriction `{restriction_text}` is contradicted by locations "
                f"`{sequential.subject_location}` and `{sequential.object_location}` on the same Sequence",
                property=spec.RESTRICTION,
            )
