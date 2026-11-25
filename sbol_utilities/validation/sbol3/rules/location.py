"""Location rules (sbol3-114xx, 11501) and Feature location overlap (sbol3-10805, 11013, 11201)."""

from __future__ import annotations

from sbol_utilities.validation.sbol3 import spec
from sbol_utilities.validation.sbol3.context import Sbol3Context, Sbol3Object
from sbol_utilities.validation.sbol3.registry import REGISTRY
from sbol_utilities.validation.sbol3.resolver import location_sequence_length


@REGISTRY.rule("sbol3-11401", "sbol3-11402", "sbol3-11403")
def ranges(ctx: Sbol3Context) -> None:
    """Range bounds are ordered, positive, and within the local Sequence."""
    for obj in ctx.instances(spec.RANGE):
        start = obj.integer(spec.START)
        end = obj.integer(spec.END)
        if start is None or end is None:
            continue
        if end < start:
            ctx.report("sbol3-11403", obj, "Range end must be greater than or equal to start", property=spec.END)
        if start <= 0:
            ctx.report("sbol3-11401", obj, "Range start must be greater than zero", property=spec.START)
        length = location_sequence_length(ctx, obj)
        if length is not None:
            # Bounds are compared as unsigned values, as in sbol-rs, so a negative bound exceeds any length.
            if (start if start >= 0 else start + 2**64) > length:
                ctx.report("sbol3-11401", obj, "Range start exceeds referenced Sequence length", property=spec.START)
            if (end if end >= 0 else end + 2**64) > length:
                ctx.report("sbol3-11402", obj, "Range end exceeds referenced Sequence length", property=spec.END)


@REGISTRY.rule("sbol3-11501")
def cuts(ctx: Sbol3Context) -> None:
    """Cut positions are nonnegative and within the local Sequence."""
    for obj in ctx.instances(spec.CUT):
        at = obj.integer(spec.AT)
        if at is None:
            continue
        if at < 0:
            ctx.report("sbol3-11501", obj, "Cut at must be greater than or equal to zero", property=spec.AT)
        length = location_sequence_length(ctx, obj)
        if length is not None and (at if at >= 0 else at + 2**64) > length:
            ctx.report("sbol3-11501", obj, "Cut at exceeds referenced Sequence length", property=spec.AT)


def _check_overlap(ctx: Sbol3Context, obj: Sbol3Object, rule: str) -> None:
    spans = []
    for location in obj.resources(spec.HAS_LOCATION):
        location_obj = ctx.get(location)
        if location_obj is None:
            continue
        start = location_obj.integer(spec.START)
        end = location_obj.integer(spec.END)
        if start is None or end is None:
            continue
        spans.append((location, location_obj.first_resource(spec.HAS_SEQUENCE), start, end))
    for index, (left, left_sequence, left_start, left_end) in enumerate(spans):
        for right, right_sequence, right_start, right_end in spans[index + 1 :]:
            if left_sequence == right_sequence and left_start <= right_end and right_start <= left_end:
                ctx.report(rule, obj, f"locations `{left}` and `{right}` overlap", property=spec.HAS_LOCATION)


@REGISTRY.rule("sbol3-10805", "sbol3-11013", "sbol3-11201")
def location_overlap(ctx: Sbol3Context) -> None:
    """Range locations of one Feature do not overlap."""
    for class_iri, rule in (
        (spec.SUB_COMPONENT, "sbol3-10805"),
        (spec.LOCAL_SUB_COMPONENT, "sbol3-11013"),
        (spec.SEQUENCE_FEATURE, "sbol3-11201"),
    ):
        for obj in ctx.instances(class_iri):
            _check_overlap(ctx, obj, rule)
