"""Whole-document rules: reference cycles and Location sequence membership."""

from __future__ import annotations

from typing import List, Set, Tuple

from rdflib.term import Node

from sbol_utilities.validation.sbol3 import REGISTRY, spec
from sbol_utilities.validation.sbol3.context import SBOL3Context
from sbol_utilities.validation.sbol3.helpers import component_allows_sequence


def _has_cycle_from(ctx: SBOL3Context, identity: Node, predicate: str, stack: Set[Node]) -> bool:
    if identity in stack:
        return True
    stack.add(identity)
    obj = ctx.get(identity)
    if obj is not None:
        for nxt in obj.resources(predicate):
            if _has_cycle_from(ctx, nxt, predicate, stack):
                return True
    stack.discard(identity)
    return False


@REGISTRY.rule("sbol3-10203")
def derived_from_cycles(ctx: SBOL3Context) -> None:
    """prov:wasDerivedFrom chains are acyclic."""
    for obj in ctx.objects.values():
        if _has_cycle_from(ctx, obj.identity, spec.PROV_WAS_DERIVED_FROM, set()):
            ctx.error("sbol3-10203", obj, spec.PROV_WAS_DERIVED_FROM, "prov:wasDerivedFrom references form a cycle")


def _has_generation_cycle_from(ctx: SBOL3Context, identity: Node, stack: Set[Node]) -> bool:
    # A revisit while only the starting entity is on the stack is the single-Activity self-loop, which is tolerated.
    if identity in stack:
        return len(stack) > 1
    stack.add(identity)
    obj = ctx.get(identity)
    if obj is not None:
        for activity_iri in obj.resources(spec.PROV_WAS_GENERATED_BY):
            activity = ctx.get(activity_iri)
            if activity is None:
                continue
            for usage_iri in activity.resources(spec.PROV_QUALIFIED_USAGE):
                usage = ctx.get(usage_iri)
                if usage is None:
                    continue
                for entity in usage.resources(spec.PROV_ENTITY):
                    if _has_generation_cycle_from(ctx, entity, stack):
                        return True
    stack.discard(identity)
    return False


@REGISTRY.rule("sbol3-10204")
def generation_cycles(ctx: SBOL3Context) -> None:
    """wasGeneratedBy / Usage entity chains are acyclic within the document."""
    for obj in ctx.objects.values():
        if _has_generation_cycle_from(ctx, obj.identity, set()):
            ctx.error(
                "sbol3-10204",
                obj,
                spec.PROV_WAS_GENERATED_BY,
                "prov:wasGeneratedBy / prov:Usage entity references form a cycle",
            )


def _component_instance_cycle(ctx: SBOL3Context, component: Node, stack: Set[Node]) -> bool:
    if component in stack:
        return True
    stack.add(component)
    obj = ctx.get(component)
    if obj is not None:
        for feature in obj.resources(spec.HAS_FEATURE):
            feature_obj = ctx.get(feature)
            if feature_obj is None or not feature_obj.has_class(spec.SUB_COMPONENT):
                continue
            instance_of = feature_obj.first_resource(spec.INSTANCE_OF)
            if instance_of is not None and _component_instance_cycle(ctx, instance_of, stack):
                return True
    stack.discard(component)
    return False


@REGISTRY.rule("sbol3-10804")
def component_instance_cycles(ctx: SBOL3Context) -> None:
    """SubComponent instanceOf chains do not loop back to a Component."""
    for component in ctx.typed(spec.COMPONENT):
        if _component_instance_cycle(ctx, component.identity, set()):
            ctx.error(
                "sbol3-10804",
                component,
                spec.INSTANCE_OF,
                "SubComponent instanceOf references form a Component cycle",
            )


def _variant_derivation_cycle(ctx: SBOL3Context, derivation: Node, stack: Set[Node]) -> bool:
    if derivation in stack:
        return True
    stack.add(derivation)
    obj = ctx.get(derivation)
    if obj is not None:
        for variable_feature in obj.resources(spec.HAS_VARIABLE_FEATURE):
            variable_feature_obj = ctx.get(variable_feature)
            if variable_feature_obj is None:
                continue
            for nxt in variable_feature_obj.resources(spec.VARIANT_DERIVATION):
                if _variant_derivation_cycle(ctx, nxt, stack):
                    return True
    stack.discard(derivation)
    return False


@REGISTRY.rule("sbol3-12204")
def variant_derivation_cycles(ctx: SBOL3Context) -> None:
    """variantDerivation chains are acyclic."""
    for derivation in ctx.typed(spec.COMBINATORIAL_DERIVATION):
        if _variant_derivation_cycle(ctx, derivation.identity, set()):
            ctx.error("sbol3-12204", derivation, spec.VARIANT_DERIVATION, "variantDerivation references form a cycle")


@REGISTRY.rule("sbol3-11302", "sbol3-11303")
def location_sequence_membership(ctx: SBOL3Context) -> None:
    """Feature Locations refer to Sequences of their Component; sourceLocations to the instanceOf's Sequences."""
    checks: List[Tuple[Node, Node, str, str]] = []
    for kind in (spec.SUB_COMPONENT, spec.SEQUENCE_FEATURE, spec.LOCAL_SUB_COMPONENT):
        for feature in ctx.typed(kind):
            component = ctx.ownership.single_parent(feature.identity, spec.HAS_FEATURE)
            if component is None:
                continue
            for location in feature.resources(spec.HAS_LOCATION):
                checks.append((location, component, spec.HAS_LOCATION, "sbol3-11302"))
            if kind == spec.SUB_COMPONENT:
                instance_of = feature.first_resource(spec.INSTANCE_OF)
                if instance_of is not None:
                    for location in feature.resources(spec.SOURCE_LOCATION):
                        checks.append((location, instance_of, spec.SOURCE_LOCATION, "sbol3-11303"))
    for location, component, predicate, rule in checks:
        location_obj = ctx.get(location)
        if location_obj is None or location_obj.has_class(spec.ENTIRE_SEQUENCE):
            continue
        sequence = location_obj.first_resource(spec.HAS_SEQUENCE)
        if sequence is None:
            continue
        if not component_allows_sequence(ctx, component, sequence):
            ctx.error(
                rule,
                location_obj,
                predicate,
                "Location sequence must be declared on the relevant Component or by a sibling EntireSequence",
            )
