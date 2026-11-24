"""Units-of-measure rules (sbol3-13401, 135xx, 142xx)."""

from __future__ import annotations

from sbol_utilities.validation.sbol3 import REGISTRY, spec
from sbol_utilities.validation.sbol3.context import SBOL3Context, SbolObject
from sbol_utilities.validation.sbol3.helpers import (
    is_sbo_systems_description_parameter_term,
    object_type_is_or_inherits,
)


def _matching_literals(ctx: SBOL3Context, obj: SbolObject, rule: str, left: str, right: str, message: str) -> None:
    left_value = obj.first_literal_value(left)
    right_value = obj.first_literal_value(right)
    if left_value is not None and right_value is not None and left_value != right_value:
        ctx.warning(rule, obj, right, message)


@REGISTRY.rule("sbol3-13401")
def measures(ctx: SBOL3Context) -> None:
    """om:Measure types come from the SBO systems description parameter branch."""
    for obj in ctx.objects.values():
        if not object_type_is_or_inherits(obj, spec.OM_MEASURE):
            continue
        for type_iri in obj.iris(spec.TYPE):
            if is_sbo_systems_description_parameter_term(ctx.ontology, str(type_iri)) is False:
                ctx.warning(
                    "sbol3-13401",
                    obj,
                    spec.TYPE,
                    f"om:Measure type `{type_iri}` should refer to a term from the SBO Systems Description Parameter "
                    "branch (SBO:0000545)",
                )


@REGISTRY.rule("sbol3-13501", "sbol3-13502", "sbol3-14201", "sbol3-14202")
def unit_and_prefix_strings(ctx: SBOL3Context) -> None:
    """sbol:name / om:label and sbol:description / om:comment agree on Units and Prefixes."""
    for obj in ctx.objects.values():
        if object_type_is_or_inherits(obj, spec.OM_UNIT):
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
        if object_type_is_or_inherits(obj, spec.OM_PREFIX):
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
