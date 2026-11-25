"""Whole-document rules: reference cycles and Location sequence membership."""

from __future__ import annotations

from collections.abc import Iterator
from functools import partial

from rdflib.term import Node

from sbol_utilities.validation.graphs import nodes_reaching, nodes_reaching_cycles
from sbol_utilities.validation.sbol3 import spec
from sbol_utilities.validation.sbol3.context import Sbol3Context, Sbol3Object
from sbol_utilities.validation.sbol3.registry import REGISTRY
from sbol_utilities.validation.sbol3.resolver import component_allows_sequence


def derived_from(ctx: Sbol3Context, identity: Node) -> Iterator[Node]:
    """The objects ``identity`` names with prov:wasDerivedFrom."""
    obj = ctx.get(identity)
    if obj is not None:
        yield from obj.resources(spec.PROV_WAS_DERIVED_FROM)


@REGISTRY.rule("sbol3-10203")
def derived_from_cycles(ctx: Sbol3Context) -> None:
    """prov:wasDerivedFrom chains are acyclic."""
    for identity in sorted(nodes_reaching_cycles(ctx.objects, partial(derived_from, ctx)), key=str):
        ctx.report(
            "sbol3-10203", identity, "prov:wasDerivedFrom references form a cycle", property=spec.PROV_WAS_DERIVED_FROM
        )


def generation_sources(ctx: Sbol3Context, identity: Node) -> Iterator[Node]:
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
def generation_cycles(ctx: Sbol3Context) -> None:
    """wasGeneratedBy / Usage entity chains are acyclic within the document.

    An entity that an Activity both uses and generates is tolerated on that entity itself; any other entity whose
    chain leads to it is reported.
    """
    generated_from = partial(generation_sources, ctx)

    def other_sources(identity: Node) -> list[Node]:
        """The entities ``identity`` is generated from, other than itself."""
        return [source for source in generated_from(identity) if source != identity]

    self_generated = [identity for identity in ctx.objects if identity in generated_from(identity)]
    offenders = nodes_reaching_cycles(ctx.objects, other_sources)
    offenders |= nodes_reaching(self_generated, ctx.objects, other_sources)
    for identity in sorted(offenders, key=str):
        ctx.report(
            "sbol3-10204",
            identity,
            "prov:wasGeneratedBy / prov:Usage entity references form a cycle",
            property=spec.PROV_WAS_GENERATED_BY,
        )


def instantiated_components(ctx: Sbol3Context, component: Node) -> Iterator[Node]:
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
def component_instance_cycles(ctx: Sbol3Context) -> None:
    """SubComponent instanceOf chains do not loop back to a Component."""
    components = [component.identity for component in ctx.instances(spec.COMPONENT)]
    for identity in sorted(nodes_reaching_cycles(components, partial(instantiated_components, ctx)), key=str):
        ctx.report(
            "sbol3-10804",
            identity,
            "SubComponent instanceOf references form a Component cycle",
            property=spec.INSTANCE_OF,
        )


def variant_derivations(ctx: Sbol3Context, derivation: Node) -> Iterator[Node]:
    """The CombinatorialDerivations that ``derivation``'s VariableFeatures draw variants from."""
    obj = ctx.get(derivation)
    if obj is None:
        return
    for variable_feature in obj.resources(spec.HAS_VARIABLE_FEATURE):
        variable_feature_obj = ctx.get(variable_feature)
        if variable_feature_obj is not None:
            yield from variable_feature_obj.resources(spec.VARIANT_DERIVATION)


@REGISTRY.rule("sbol3-12204")
def variant_derivation_cycles(ctx: Sbol3Context) -> None:
    """variantDerivation chains are acyclic."""
    derivations = [derivation.identity for derivation in ctx.instances(spec.COMBINATORIAL_DERIVATION)]
    for identity in sorted(nodes_reaching_cycles(derivations, partial(variant_derivations, ctx)), key=str):
        ctx.report(
            "sbol3-12204", identity, "variantDerivation references form a cycle", property=spec.VARIANT_DERIVATION
        )


def check_location_sequences(
    ctx: Sbol3Context, feature: Sbol3Object, predicate: str, component: Node, rule: str
) -> None:
    """Report each of ``feature``'s Locations under ``predicate`` whose Sequence ``component`` does not declare."""
    for location in ctx.referenced(feature, predicate):
        sequence = location.first_resource(spec.HAS_SEQUENCE)
        if sequence is None or location.has_class(spec.ENTIRE_SEQUENCE):
            continue
        if not component_allows_sequence(ctx, component, sequence):
            ctx.report(
                rule,
                location,
                "Location sequence must be declared on the relevant Component or by a sibling EntireSequence",
                property=predicate,
            )


@REGISTRY.rule("sbol3-11302", "sbol3-11303")
def location_sequence_membership(ctx: Sbol3Context) -> None:
    """A Feature's Locations refer to Sequences of its Component, and a SubComponent's source Locations to
    Sequences of the Component it instantiates."""
    for feature in ctx.instances(spec.SUB_COMPONENT, spec.SEQUENCE_FEATURE, spec.LOCAL_SUB_COMPONENT):
        component = ctx.parent(feature, spec.HAS_FEATURE)
        if component is None:
            continue
        check_location_sequences(ctx, feature, spec.HAS_LOCATION, component.identity, "sbol3-11302")
        instance_of = feature.first_resource(spec.INSTANCE_OF) if feature.has_class(spec.SUB_COMPONENT) else None
        if instance_of is not None:
            check_location_sequences(ctx, feature, spec.SOURCE_LOCATION, instance_of, "sbol3-11303")
