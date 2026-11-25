"""Location rules (sbol3-114xx, 11501) and Feature location overlap (sbol3-10805, 11013, 11201)."""

from __future__ import annotations

from itertools import combinations

from sbol_utilities.validation.sbol3 import spec
from sbol_utilities.validation.sbol3.context import Sbol3Context
from sbol_utilities.validation.sbol3.registry import REGISTRY
from sbol_utilities.validation.sbol3.resolver import location_sequence_length


def is_beyond(position: int, length: int) -> bool:
    """Whether a position lies beyond a Sequence of ``length`` positions; a negative position always does."""
    return position < 0 or position > length


@REGISTRY.rule("sbol3-11401", "sbol3-11402", "sbol3-11403")
def ranges(ctx: Sbol3Context) -> None:
    """Range bounds are ordered, positive, and within the Sequence the Range refers to."""
    for obj in ctx.instances(spec.RANGE):
        start, end = obj.integer(spec.START), obj.integer(spec.END)
        if start is None or end is None:
            continue
        if end < start:
            ctx.report("sbol3-11403", obj, "Range end must be greater than or equal to start", property=spec.END)
        if start <= 0:
            ctx.report("sbol3-11401", obj, "Range start must be greater than zero", property=spec.START)
        length = location_sequence_length(ctx, obj)
        if length is None:
            continue
        if is_beyond(start, length):
            ctx.report("sbol3-11401", obj, "Range start exceeds referenced Sequence length", property=spec.START)
        if is_beyond(end, length):
            ctx.report("sbol3-11402", obj, "Range end exceeds referenced Sequence length", property=spec.END)


@REGISTRY.rule("sbol3-11501")
def cuts(ctx: Sbol3Context) -> None:
    """Cut positions are nonnegative and within the Sequence the Cut refers to."""
    for obj in ctx.instances(spec.CUT):
        at = obj.integer(spec.AT)
        if at is None:
            continue
        if at < 0:
            ctx.report("sbol3-11501", obj, "Cut at must be greater than or equal to zero", property=spec.AT)
        length = location_sequence_length(ctx, obj)
        if length is not None and is_beyond(at, length):
            ctx.report("sbol3-11501", obj, "Cut at exceeds referenced Sequence length", property=spec.AT)


#: Feature class -> the rule forbidding its Locations to overlap
OVERLAP_RULES = (
    (spec.SUB_COMPONENT, "sbol3-10805"),
    (spec.LOCAL_SUB_COMPONENT, "sbol3-11013"),
    (spec.SEQUENCE_FEATURE, "sbol3-11201"),
)


@REGISTRY.rule(*(rule for _, rule in OVERLAP_RULES))
def location_overlap(ctx: Sbol3Context) -> None:
    """The Locations of one Feature that have a start and an end do not overlap on a Sequence."""
    for class_iri, rule in OVERLAP_RULES:
        for obj in ctx.instances(class_iri):
            spans = [
                (location.identity, location.first_resource(spec.HAS_SEQUENCE), start, end)
                for location in ctx.referenced(obj, spec.HAS_LOCATION)
                if (start := location.integer(spec.START)) is not None
                and (end := location.integer(spec.END)) is not None
            ]
            for (left, left_sequence, left_start, left_end), (
                right,
                right_sequence,
                right_start,
                right_end,
            ) in combinations(spans, 2):
                if left_sequence == right_sequence and left_start <= right_end and right_start <= left_end:
                    ctx.report(rule, obj, f"locations `{left}` and `{right}` overlap", property=spec.HAS_LOCATION)
