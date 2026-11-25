"""Feature and Location vocabulary rules (sbol3-107xx, 108xx, 11301)."""

from __future__ import annotations

from sbol_utilities.validation.sbol3 import spec
from sbol_utilities.validation.sbol3.context import SBOL3Context
from sbol_utilities.validation.sbol3.registry import REGISTRY


@REGISTRY.rule("sbol3-10701", "sbol3-10702", "sbol3-11301", "sbol3-10801", "sbol3-10802")
def feature_vocabularies(ctx: SBOL3Context) -> None:
    """Feature roles and orientations, Location orientations, and SubComponent roleIntegration."""
    ontology = ctx.ontology
    for obj in ctx.objects.values():
        if obj.has_class(spec.FEATURE):
            for role in obj.iris(spec.ROLE):
                if ontology.is_feature_role_term(str(role)) is False:
                    ctx.report(
                        "sbol3-10701",
                        obj,
                        f"Feature role `{role}` is not an ontology Feature role term",
                        property=spec.ROLE,
                    )
            for orientation in obj.iris(spec.ORIENTATION):
                if str(orientation) not in spec.ORIENTATION_IRIS:
                    ctx.report(
                        "sbol3-10702",
                        obj,
                        f"unsupported Feature orientation `{orientation}`",
                        property=spec.ORIENTATION,
                    )
        if obj.has_class(spec.LOCATION):
            for orientation in obj.iris(spec.ORIENTATION):
                if str(orientation) not in spec.ORIENTATION_IRIS:
                    ctx.report(
                        "sbol3-11301",
                        obj,
                        f"unsupported Location orientation `{orientation}`",
                        property=spec.ORIENTATION,
                    )
        if obj.has_class(spec.SUB_COMPONENT):
            for role_integration in obj.iris(spec.ROLE_INTEGRATION):
                if str(role_integration) not in spec.ROLE_INTEGRATION_IRIS:
                    ctx.report(
                        "sbol3-10801",
                        obj,
                        f"unsupported roleIntegration `{role_integration}`",
                        property=spec.ROLE_INTEGRATION,
                    )
            if obj.values(spec.ROLE) and not obj.values(spec.ROLE_INTEGRATION):
                ctx.report(
                    "sbol3-10802",
                    obj,
                    "SubComponent with role values must provide roleIntegration",
                    property=spec.ROLE_INTEGRATION,
                )
