"""SubComponent rules (sbol3-10803, 10806, 10807)."""

from __future__ import annotations

from sbol_utilities.validation.sbol3 import spec
from sbol_utilities.validation.sbol3.context import SBOL3Context, SbolObject
from sbol_utilities.validation.sbol3.helpers import sum_location_lengths
from sbol_utilities.validation.sbol3.registry import REGISTRY


def _check_location_lengths(ctx: SBOL3Context, obj: SbolObject) -> None:
    locations = obj.resources(spec.HAS_LOCATION)
    source_locations = obj.resources(spec.SOURCE_LOCATION)
    if locations and source_locations:
        location_length = sum_location_lengths(ctx, locations)
        source_length = sum_location_lengths(ctx, source_locations)
        if location_length is not None and source_length is not None and location_length != source_length:
            ctx.report(
                "sbol3-10806",
                obj,
                "SubComponent hasLocation and sourceLocation lengths must match",
                property=spec.HAS_LOCATION,
            )
        return
    if not locations or source_locations:
        return
    component = ctx.get(obj.first_resource(spec.INSTANCE_OF))
    if component is None:
        return
    sequences = component.resources(spec.HAS_SEQUENCE)
    if len(sequences) != 1:
        return
    sequence = ctx.get(sequences[0])
    elements = None if sequence is None else sequence.first_literal_value(spec.ELEMENTS)
    if elements is None:
        return
    location_length = sum_location_lengths(ctx, locations)
    if location_length is not None and location_length != len(elements.encode("utf-8")):
        ctx.report(
            "sbol3-10807",
            obj,
            "SubComponent location lengths must cover its instanceOf sequence when sourceLocation is absent",
            property=spec.HAS_LOCATION,
        )


@REGISTRY.rule("sbol3-10803", "sbol3-10806", "sbol3-10807")
def sub_components(ctx: SBOL3Context) -> None:
    """SubComponents do not instantiate their parent, and their location lengths agree."""
    for obj in ctx.instances(spec.SUB_COMPONENT):
        parent = ctx.ownership.single_parent(obj.identity, spec.HAS_FEATURE)
        if parent is not None and obj.first_resource(spec.INSTANCE_OF) == parent:
            ctx.report(
                "sbol3-10803",
                obj,
                "SubComponent instanceOf must not refer to its containing Component",
                property=spec.INSTANCE_OF,
            )
        _check_location_lengths(ctx, obj)
