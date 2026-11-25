"""Whole-document rules: reference cycles and Location sequence membership."""

from __future__ import annotations

from collections.abc import Iterator
from functools import partial

from rdflib.term import Node

from sbol_utilities.validation.graphs import nodes_reaching, nodes_reaching_cycles
from sbol_utilities.validation.sbol3 import spec
from sbol_utilities.validation.sbol3.context import SBOL3Context
from sbol_utilities.validation.sbol3.helpers import component_allows_sequence
from sbol_utilities.validation.sbol3.registry import REGISTRY


def _derived_from(ctx: SBOL3Context, identity: Node) -> Iterator[Node]:
    """The objects ``identity`` names with prov:wasDerivedFrom."""
    obj = ctx.get(identity)
    if obj is not None:
        yield from obj.resources(spec.PROV_WAS_DERIVED_FROM)


@REGISTRY.rule("sbol3-10203")
def derived_from_cycles(ctx: SBOL3Context) -> None:
    """prov:wasDerivedFrom chains are acyclic."""
    for identity in sorted(nodes_reaching_cycles(ctx.objects, partial(_derived_from, ctx)), key=str):
        ctx.error("sbol3-10203", identity, spec.PROV_WAS_DERIVED_FROM, "prov:wasDerivedFrom references form a cycle")


def _generated_from(ctx: SBOL3Context, identity: Node) -> Iterator[Node]:
    """The entities used by the Activities that generated ``identity``."""
    obj = ctx.get(identity)
    if obj is None:
        return
    for activity_iri in obj.resources(spec.PROV_WAS_GENERATED_BY):
        activity = ctx.get(activity_iri)
        if activity is None:
            continue
        for usage_iri in activity.resources(spec.PROV_QUALIFIED_USAGE):
            usage = ctx.get(usage_iri)
            if usage is not None:
                yield from usage.resources(spec.PROV_ENTITY)


@REGISTRY.rule("sbol3-10204")
def generation_cycles(ctx: SBOL3Context) -> None:
    """wasGeneratedBy / Usage entity chains are acyclic within the document.

    An entity that an Activity both uses and generates is tolerated on that entity itself; any other entity whose
    chain leads to it is reported.
    """
    generated_from = partial(_generated_from, ctx)

    def other_sources(identity: Node) -> list[Node]:
        return [source for source in generated_from(identity) if source != identity]

    self_generated = [identity for identity in ctx.objects if identity in generated_from(identity)]
    offenders = nodes_reaching_cycles(ctx.objects, other_sources)
    offenders |= nodes_reaching(self_generated, ctx.objects, other_sources)
    for identity in sorted(offenders, key=str):
        ctx.error(
            "sbol3-10204",
            identity,
            spec.PROV_WAS_GENERATED_BY,
            "prov:wasGeneratedBy / prov:Usage entity references form a cycle",
        )


def _instantiated_components(ctx: SBOL3Context, component: Node) -> Iterator[Node]:
    """The Components that ``component``'s SubComponents are instances of."""
    obj = ctx.get(component)
    if obj is None:
        return
    for feature in obj.resources(spec.HAS_FEATURE):
        feature_obj = ctx.get(feature)
        if feature_obj is None or not feature_obj.has_class(spec.SUB_COMPONENT):
            continue
        instance_of = feature_obj.first_resource(spec.INSTANCE_OF)
        if instance_of is not None:
            yield instance_of


@REGISTRY.rule("sbol3-10804")
def component_instance_cycles(ctx: SBOL3Context) -> None:
    """SubComponent instanceOf chains do not loop back to a Component."""
    components = [component.identity for component in ctx.typed(spec.COMPONENT)]
    for identity in sorted(nodes_reaching_cycles(components, partial(_instantiated_components, ctx)), key=str):
        ctx.error(
            "sbol3-10804",
            identity,
            spec.INSTANCE_OF,
            "SubComponent instanceOf references form a Component cycle",
        )


def _variant_derivations(ctx: SBOL3Context, derivation: Node) -> Iterator[Node]:
    """The CombinatorialDerivations that ``derivation``'s VariableFeatures draw variants from."""
    obj = ctx.get(derivation)
    if obj is None:
        return
    for variable_feature in obj.resources(spec.HAS_VARIABLE_FEATURE):
        variable_feature_obj = ctx.get(variable_feature)
        if variable_feature_obj is not None:
            yield from variable_feature_obj.resources(spec.VARIANT_DERIVATION)


@REGISTRY.rule("sbol3-12204")
def variant_derivation_cycles(ctx: SBOL3Context) -> None:
    """variantDerivation chains are acyclic."""
    derivations = [derivation.identity for derivation in ctx.typed(spec.COMBINATORIAL_DERIVATION)]
    for identity in sorted(nodes_reaching_cycles(derivations, partial(_variant_derivations, ctx)), key=str):
        ctx.error("sbol3-12204", identity, spec.VARIANT_DERIVATION, "variantDerivation references form a cycle")


@REGISTRY.rule("sbol3-11302", "sbol3-11303")
def location_sequence_membership(ctx: SBOL3Context) -> None:
    """Feature Locations refer to Sequences of their Component; sourceLocations to the instanceOf's Sequences."""
    checks: list[tuple[Node, Node, str, str]] = []
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
