"""SubComponent rules (sbol3-10803, 10806, 10807)."""

from __future__ import annotations

from sbol_utilities.validation.sbol3 import spec
from sbol_utilities.validation.sbol3.context import Sbol3Context
from sbol_utilities.validation.sbol3.registry import REGISTRY
from sbol_utilities.validation.sbol3.resolver import sequence_length, sum_location_lengths


@REGISTRY.rule("sbol3-10803")
def self_instantiation(ctx: Sbol3Context) -> None:
    """A SubComponent does not instantiate the Component that holds it."""
    for obj in ctx.instances(spec.SUB_COMPONENT):
        parent = ctx.parent(obj, spec.HAS_FEATURE)
        if parent is not None and obj.first_resource(spec.INSTANCE_OF) == parent.identity:
            ctx.report(
                "sbol3-10803",
                obj,
                "SubComponent instanceOf must not refer to its containing Component",
                property=spec.INSTANCE_OF,
            )


@REGISTRY.rule("sbol3-10806")
def source_location_lengths(ctx: Sbol3Context) -> None:
    """A SubComponent's Locations cover as many positions as its source Locations."""
    for obj in ctx.instances(spec.SUB_COMPONENT):
        locations, source_locations = obj.resources(spec.HAS_LOCATION), obj.resources(spec.SOURCE_LOCATION)
        if not locations or not source_locations:
            continue
        length, source_length = sum_location_lengths(ctx, locations), sum_location_lengths(ctx, source_locations)
        if length is not None and source_length is not None and length != source_length:
            ctx.report(
                "sbol3-10806",
                obj,
                "SubComponent hasLocation and sourceLocation lengths must match",
                property=spec.HAS_LOCATION,
            )


@REGISTRY.rule("sbol3-10807")
def whole_sequence_lengths(ctx: Sbol3Context) -> None:
    """Without source Locations, a SubComponent's Locations cover the whole Sequence of the Component it
    instantiates, when that Component has exactly one."""
    for obj in ctx.instances(spec.SUB_COMPONENT):
        locations = obj.resources(spec.HAS_LOCATION)
        component = ctx.get(obj.first_resource(spec.INSTANCE_OF))
        if not locations or obj.resources(spec.SOURCE_LOCATION) or component is None:
            continue
        sequences = component.resources(spec.HAS_SEQUENCE)
        expected = sequence_length(ctx, sequences[0]) if len(sequences) == 1 else None
        length = None if expected is None else sum_location_lengths(ctx, locations)
        if length is not None and length != expected:
            ctx.report(
                "sbol3-10807",
                obj,
                "SubComponent location lengths must cover its instanceOf sequence when sourceLocation is absent",
                property=spec.HAS_LOCATION,
            )
