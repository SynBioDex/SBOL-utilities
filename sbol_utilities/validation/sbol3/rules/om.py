"""Units-of-measure rules (sbol3-13401, 135xx, 142xx)."""

from __future__ import annotations

from sbol_utilities.validation.sbol3 import spec
from sbol_utilities.validation.sbol3.context import Sbol3Context, Sbol3Object
from sbol_utilities.validation.sbol3.helpers import SBO_SYSTEMS_DESCRIPTION_PARAMETER
from sbol_utilities.validation.sbol3.registry import REGISTRY


def _matching_literals(ctx: Sbol3Context, obj: Sbol3Object, rule: str, left: str, right: str, message: str) -> None:
    left_value = obj.first_literal(left)
    right_value = obj.first_literal(right)
    if left_value is not None and right_value is not None and left_value != right_value:
        ctx.report(rule, obj, message, property=right)


@REGISTRY.rule("sbol3-13401")
def measures(ctx: Sbol3Context) -> None:
    """om:Measure types come from the SBO systems description parameter branch."""
    for obj in ctx.objects.values():
        if not obj.has_class(spec.OM_MEASURE):
            continue
        for type_iri in obj.iris(spec.TYPE):
            if ctx.ontology.in_branch_if_known(str(type_iri), SBO_SYSTEMS_DESCRIPTION_PARAMETER) is False:
                ctx.report(
                    "sbol3-13401",
                    obj,
                    f"om:Measure type `{type_iri}` should refer to a term from the SBO Systems Description Parameter "
                    "branch (SBO:0000545)",
                    property=spec.TYPE,
                )


@REGISTRY.rule("sbol3-13501", "sbol3-13502", "sbol3-14201", "sbol3-14202")
def unit_and_prefix_strings(ctx: Sbol3Context) -> None:
    """sbol:name / om:label and sbol:description / om:comment agree on Units and Prefixes."""
    for obj in ctx.objects.values():
        if obj.has_class(spec.OM_UNIT):
            _matching_literals(
                ctx, obj, "sbol3-13501", spec.NAME, spec.OM_LABEL, "om:Unit sbol:name and om:label should match"
            )
            _matching_literals(
                ctx,
                obj,
                "sbol3-13502",
                spec.DESCRIPTION,
                spec.OM_COMMENT,
                "om:Unit sbol:description and om:comment should match",
            )
        if obj.has_class(spec.OM_PREFIX):
            _matching_literals(
                ctx, obj, "sbol3-14201", spec.NAME, spec.OM_LABEL, "om:Prefix sbol:name and om:label should match"
            )
            _matching_literals(
                ctx,
                obj,
                "sbol3-14202",
                spec.DESCRIPTION,
                spec.OM_COMMENT,
                "om:Prefix sbol:description and om:comment should match",
            )
