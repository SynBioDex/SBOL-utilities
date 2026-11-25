"""Feature and Location vocabulary rules (sbol3-107xx, 108xx, 11301)."""

from __future__ import annotations

from sbol_utilities.validation.sbol3 import spec
from sbol_utilities.validation.sbol3.context import Sbol3Context
from sbol_utilities.validation.sbol3.registry import REGISTRY

#: (class, property, the values it may take, rule, what an unrecognized value is called)
VOCABULARIES = (
    (spec.FEATURE, spec.ORIENTATION, spec.ORIENTATION_IRIS, "sbol3-10702", "Feature orientation"),
    (spec.LOCATION, spec.ORIENTATION, spec.ORIENTATION_IRIS, "sbol3-11301", "Location orientation"),
    (spec.SUB_COMPONENT, spec.ROLE_INTEGRATION, spec.ROLE_INTEGRATION_IRIS, "sbol3-10801", "roleIntegration"),
)


@REGISTRY.rule(*(rule for _, _, _, rule, _ in VOCABULARIES))
def controlled_values(ctx: Sbol3Context) -> None:
    """Orientations and roleIntegration take values from their SBOL vocabularies."""
    for class_iri, predicate, allowed, rule, name in VOCABULARIES:
        for obj in ctx.instances(class_iri):
            for value in obj.iris(predicate):
                if str(value) not in allowed:
                    ctx.report(rule, obj, f"unsupported {name} `{value}`", property=predicate)


@REGISTRY.rule("sbol3-10701")
def feature_roles(ctx: Sbol3Context) -> None:
    """A Feature role that the ontology snapshot knows is a Feature role term."""
    for obj in ctx.instances(spec.FEATURE):
        for role in obj.iris(spec.ROLE):
            if ctx.ontology.is_feature_role_term(str(role)) is False:
                ctx.report(
                    "sbol3-10701",
                    obj,
                    f"Feature role `{role}` is not an ontology Feature role term",
                    property=spec.ROLE,
                )


@REGISTRY.rule("sbol3-10802")
def sub_component_role_integration(ctx: Sbol3Context) -> None:
    """A SubComponent that has roles says how they combine with those of the Component it instantiates."""
    for obj in ctx.instances(spec.SUB_COMPONENT):
        if obj.values(spec.ROLE) and not obj.values(spec.ROLE_INTEGRATION):
            ctx.report(
                "sbol3-10802",
                obj,
                "SubComponent with role values must provide roleIntegration",
                property=spec.ROLE_INTEGRATION,
            )
