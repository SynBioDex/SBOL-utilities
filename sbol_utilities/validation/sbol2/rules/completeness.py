"""The completeness family: referenced objects are present in the document and of the class the reference
requires. A reference resolves to the object with that identity or that persistentIdentity."""

from __future__ import annotations

from rdflib.term import URIRef

from sbol_utilities.validation.sbol2 import spec as S
from sbol_utilities.validation.sbol2.context import Sbol2Context
from sbol_utilities.validation.sbol2.registry import REGISTRY

PRESENCE_RULES = tuple(dict.fromkeys([*S.COMPLETENESS_RULES.values(), *S.DEFINITION_COMPLETENESS_RULES.values()]))


@REGISTRY.rule(*PRESENCE_RULES)
def referenced_objects_present(ctx: Sbol2Context) -> None:
    """Every reference to an object that may live elsewhere names an object held in the document."""
    for obj in ctx.sbol_objects:
        for predicate, declared in obj.property_specs.items():
            reference = declared.reference
            if reference is None or reference.local:
                continue
            rule = S.completeness_rule(predicate, reference.target)
            if rule is None:
                continue
            for value in obj.resources(predicate):
                if not isinstance(value, URIRef) or ctx.resolve(str(value)) is None:
                    ctx.report(
                        rule,
                        obj,
                        f"complete document must contain the object `{value}` referenced by `{predicate}`",
                        property=predicate,
                    )


#: (reference predicate, class the referenced object must have, rule)
CLASS_CHECKS = (
    (S.WAS_GENERATED_BY, S.ACTIVITY, "sbol2-10222"),
    (S.WAS_INFORMED_BY, S.ACTIVITY, "sbol2-12407"),
    (S.AGENT_P, S.AGENT, "sbol2-12606"),
    (S.HAD_PLAN, S.PLAN, "sbol2-12604"),
    (S.MODEL_P, S.MODEL, "sbol2-11608"),
    (S.VARIANT_COLLECTION, S.COLLECTION, "sbol2-13010"),
    (S.VARIANT_DERIVATION, S.COMBINATORIAL_DERIVATION, "sbol2-13014"),
    (S.EXPERIMENTAL_DATA_P, S.EXPERIMENTAL_DATA, "sbol2-13404"),
)


@REGISTRY.rule(*(rule for _, _, rule in CLASS_CHECKS))
def referenced_object_classes(ctx: Sbol2Context) -> None:
    """A reference that resolves in the document names an object of the class the property requires."""
    for obj in ctx.sbol_objects:
        for predicate, required, rule in CLASS_CHECKS:
            for iri, target in ctx.resolved(obj, predicate):
                if not target.has_class(required):
                    ctx.report(
                        rule,
                        obj,
                        f"`{predicate}` refers to `{iri}`, which is not the required class",
                        property=predicate,
                    )


@REGISTRY.rule("sbol2-10604")
def component_definitions(ctx: Sbol2Context) -> None:
    """The definition of a Component or FunctionalComponent is a ComponentDefinition."""
    for obj in ctx.instances(S.COMPONENT, S.FUNCTIONAL_COMPONENT):
        if obj.has_class(S.MODULE):
            continue
        for iri, target in ctx.resolved(obj, S.DEFINITION):
            if not target.has_class(S.COMPONENT_DEFINITION):
                ctx.report(
                    "sbol2-10604",
                    obj,
                    f"definition refers to `{iri}`, which is not a ComponentDefinition",
                    property=S.DEFINITION,
                )


@REGISTRY.rule("sbol2-13506")
def measure_units(ctx: Sbol2Context) -> None:
    """The hasUnit of a Measure is an om:Unit."""
    for obj in ctx.instances(S.OM_MEASURE):
        for iri, target in ctx.resolved(obj, S.OM_HAS_UNIT):
            if not target.has_class(S.OM_UNIT):
                ctx.report(
                    "sbol2-13506", obj, f"the hasUnit of a Measure `{iri}` must refer to a Unit", property=S.OM_HAS_UNIT
                )


@REGISTRY.rule("sbol2-10807")
def maps_to_remote_access(ctx: Sbol2Context) -> None:
    """The remote of a MapsTo is a ComponentInstance with public access."""
    for obj in ctx.instances(S.MAPS_TO):
        for iri, target in ctx.resolved(obj, S.REMOTE):
            if S.PUBLIC not in target.iris(S.ACCESS):
                ctx.report("sbol2-10807", obj, f"the MapsTo remote `{iri}` must have public access", property=S.REMOTE)


@REGISTRY.rule("sbol2-13103")
def implementation_built(ctx: Sbol2Context) -> None:
    """What an Implementation was built from is a ComponentDefinition or ModuleDefinition held in the document."""
    for obj in ctx.instances(S.IMPLEMENTATION):
        for iri in obj.iris(S.BUILT):
            target = ctx.resolve(iri)
            if target is None or not target.has_class(S.COMPONENT_DEFINITION, S.MODULE_DEFINITION):
                ctx.report(
                    "sbol2-13103",
                    obj,
                    f"built refers to `{iri}`, which is not a ComponentDefinition or ModuleDefinition",
                    property=S.BUILT,
                )
