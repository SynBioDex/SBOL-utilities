"""Units-of-measure rules (sbol3-13401, 135xx, 142xx)."""

from __future__ import annotations

from sbol_utilities.validation.sbol3 import spec
from sbol_utilities.validation.sbol3.context import Sbol3Context
from sbol_utilities.validation.sbol3.helpers import SBO_SYSTEMS_DESCRIPTION_PARAMETER
from sbol_utilities.validation.sbol3.registry import REGISTRY


@REGISTRY.rule("sbol3-13401")
def measures(ctx: Sbol3Context) -> None:
    """om:Measure types come from the SBO systems description parameter branch."""
    for obj in ctx.instances(spec.OM_MEASURE):
        for type_iri in obj.iris(spec.TYPE):
            if ctx.ontology.in_branch_if_known(str(type_iri), SBO_SYSTEMS_DESCRIPTION_PARAMETER) is False:
                ctx.report(
                    "sbol3-13401",
                    obj,
                    f"om:Measure type `{type_iri}` should refer to a term from the SBO Systems Description Parameter "
                    "branch (SBO:0000545)",
                    property=spec.TYPE,
                )


#: (class, SBOL property, OM property holding the same text, rule, message)
_MATCHING_STRINGS = (
    (spec.OM_UNIT, spec.NAME, spec.OM_LABEL, "sbol3-13501", "om:Unit sbol:name and om:label should match"),
    (
        spec.OM_UNIT,
        spec.DESCRIPTION,
        spec.OM_COMMENT,
        "sbol3-13502",
        "om:Unit sbol:description and om:comment should match",
    ),
    (spec.OM_PREFIX, spec.NAME, spec.OM_LABEL, "sbol3-14201", "om:Prefix sbol:name and om:label should match"),
    (
        spec.OM_PREFIX,
        spec.DESCRIPTION,
        spec.OM_COMMENT,
        "sbol3-14202",
        "om:Prefix sbol:description and om:comment should match",
    ),
)


@REGISTRY.rule(*(rule for _, _, _, rule, _ in _MATCHING_STRINGS))
def unit_and_prefix_strings(ctx: Sbol3Context) -> None:
    """sbol:name / om:label and sbol:description / om:comment agree on Units and Prefixes."""
    for class_iri, sbol_property, om_property, rule, message in _MATCHING_STRINGS:
        for obj in ctx.instances(class_iri):
            sbol_text, om_text = obj.first_literal(sbol_property), obj.first_literal(om_property)
            if sbol_text is not None and om_text is not None and sbol_text != om_text:
                ctx.report(rule, obj, message, property=om_property)
