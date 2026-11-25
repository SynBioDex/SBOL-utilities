"""Document queries that several SBOL 2 rule modules share."""

from __future__ import annotations

import re
from dataclasses import dataclass
from itertools import combinations
from typing import Union

from sbol_utilities.validation.graphs import nodes_reaching_cycles
from sbol_utilities.validation.sbol2 import spec as S
from sbol_utilities.validation.sbol2.context import Sbol2Context, Sbol2Object

_SEGMENT = re.compile(r"[/#]")


def ontology_curie(iri: str) -> str:
    """The compact ontology id an SBOL 2 term IRI ends with: its last path or fragment segment."""
    return _SEGMENT.split(iri)[-1]


@dataclass(frozen=True)
class RangeExtent:
    """The positions a Range covers, both ends included."""

    start: int
    end: int

    @property
    def bounds(self) -> tuple[int, int]:
        """First and last position."""
        return self.start, self.end

    @property
    def length(self) -> int:
        """Number of positions covered."""
        return self.end - self.start + 1


@dataclass(frozen=True)
class CutExtent:
    """The position a Cut follows."""

    at: int

    @property
    def bounds(self) -> tuple[int, int]:
        """The cut position, as both first and last position."""
        return self.at, self.at


Extent = Union[RangeExtent, CutExtent]


def extents(ctx: Sbol2Context, obj: Sbol2Object, predicate: str = S.LOCATION_P) -> list[Extent]:
    """The extents of the Ranges and Cuts ``obj`` names under ``predicate``, skipping any without integer positions."""
    result: list[Extent] = []
    for location in ctx.referenced(obj, predicate):
        if location.has_class(S.RANGE):
            start, end = location.integer(S.START), location.integer(S.END)
            if start is not None and end is not None:
                result.append(RangeExtent(start, end))
        elif location.has_class(S.CUT):
            at = location.integer(S.AT)
            if at is not None:
                result.append(CutExtent(at))
    return result


def _overlap(a: Extent, b: Extent) -> bool:
    if isinstance(a, RangeExtent) and isinstance(b, RangeExtent):
        return b.start <= a.start <= b.end or a.start <= b.start <= a.end
    if isinstance(a, CutExtent) and isinstance(b, CutExtent):
        return a.at == b.at
    covered, cut = (a, b) if isinstance(a, RangeExtent) else (b, a)
    assert isinstance(covered, RangeExtent) and isinstance(cut, CutExtent)
    return covered.start <= cut.at < covered.end


def extents_overlap(found: list[Extent]) -> bool:
    """Whether any two extents overlap: two Ranges sharing a position, two Cuts at the same position, or a Cut
    falling inside a Range."""
    return any(_overlap(a, b) for a, b in combinations(found, 2))


def range_span(found: list[Extent]) -> int | None:
    """The summed length of the Range extents, or None when there are none."""
    lengths = [extent.length for extent in found if isinstance(extent, RangeExtent)]
    return sum(lengths) if lengths else None


def definition_cycles(
    ctx: Sbol2Context, class_iri: str, instance_predicate: str, link_predicate: str
) -> list[Sbol2Object]:
    """Definitions of ``class_iri`` from which following instances to their definitions reaches a cycle."""
    graph: dict[str, list[str]] = {}
    members: list[Sbol2Object] = []
    for obj in ctx.instances(class_iri):
        if obj.iri is None:
            continue
        members.append(obj)
        graph[obj.iri] = []
        for instance in ctx.referenced(obj, instance_predicate):
            target = ctx.resolve(instance.first_iri(link_predicate))
            if target is not None and target.iri is not None:
                graph[obj.iri].append(target.iri)
    offenders = nodes_reaching_cycles(graph, lambda node: graph.get(node, ()))
    return [obj for obj in members if obj.iri in offenders]


def use_remote_collisions(ctx: Sbol2Context, class_iri: str, instance_predicates: tuple[str, ...]) -> list[Sbol2Object]:
    """Definitions of ``class_iri`` in which two useRemote MapsTos of their instances share a local."""
    offenders = []
    for obj in ctx.instances(class_iri):
        locals_ = [
            local
            for predicate in instance_predicates
            for instance in ctx.referenced(obj, predicate)
            for maps_to in ctx.referenced(instance, S.MAPS_TO_P)
            if maps_to.first_iri(S.REFINEMENT) == S.USE_REMOTE and (local := maps_to.first_iri(S.LOCAL)) is not None
        ]
        if len(set(locals_)) < len(locals_):
            offenders.append(obj)
    return offenders
