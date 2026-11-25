"""Constraint rules (sbol3-117xx)."""

from __future__ import annotations

from sbol_utilities.validation.sbol3 import spec
from sbol_utilities.validation.sbol3.context import SBOL3Context
from sbol_utilities.validation.sbol3.helpers import component_contains
from sbol_utilities.validation.sbol3.registry import REGISTRY
from sbol_utilities.validation.sbol3.resolver import CONTRADICTED, table8_relation, table10_relation


@REGISTRY.rule("sbol3-11701", "sbol3-11702", "sbol3-11703", "sbol3-11704", "sbol3-11705", "sbol3-11706")
def constraints(ctx: SBOL3Context) -> None:
    """Constraint containment, distinct subject/object, restriction vocabulary, and decidable contradictions."""
    for obj in ctx.instances(spec.CONSTRAINT):
        component = ctx.ownership.single_parent(obj.identity, spec.HAS_CONSTRAINT)
        if component is None:
            continue
        subject = obj.first_resource(spec.SUBJECT)
        constrained = obj.first_resource(spec.OBJECT)
        if subject is not None and not component_contains(ctx, component, spec.HAS_FEATURE, subject):
            ctx.report(
                "sbol3-11701",
                obj,
                "Constraint subject must be a Feature of the containing Component",
                property=spec.SUBJECT,
            )
        if constrained is not None and not component_contains(ctx, component, spec.HAS_FEATURE, constrained):
            ctx.report(
                "sbol3-11702",
                obj,
                "Constraint object must be a Feature of the containing Component",
                property=spec.OBJECT,
            )
        if subject == constrained:
            ctx.report(
                "sbol3-11703", obj, "Constraint subject and object must not be the same Feature", property=spec.OBJECT
            )
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
        if subject is None or constrained is None:
            continue
        table8 = table8_relation(ctx, restriction_text, subject, constrained)
        table10 = table10_relation(ctx, restriction_text, subject, constrained)
        if table8.outcome == CONTRADICTED:
            ctx.report(
                "sbol3-11705",
                obj,
                f"Constraint restriction `{restriction_text}` is contradicted by resolved Feature semantics",
                property=spec.RESTRICTION,
            )
        if table10.outcome == CONTRADICTED and table10.subject_location is not None:
            ctx.report(
                "sbol3-11706",
                obj,
                f"Constraint restriction `{restriction_text}` is contradicted by locations "
                f"`{table10.subject_location}` and `{table10.object_location}` on the same Sequence",
                property=spec.RESTRICTION,
            )
