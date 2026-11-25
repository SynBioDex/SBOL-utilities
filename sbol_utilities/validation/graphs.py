"""Directed-graph queries used by the reference-cycle rules.

A graph is given as a ``successors`` function from a node to the nodes it points at, so callers describe edges in
terms of the document (an object's ``prov:wasDerivedFrom`` values, say) without building an adjacency table. Every
traversal is iterative and visits each node once, so reference chains of any length and shape are handled in time
linear in the number of edges.
"""

from __future__ import annotations

from collections.abc import Hashable, Iterable, Iterator
from typing import Callable, TypeVar

N = TypeVar("N", bound=Hashable)

Successors = Callable[[N], Iterable[N]]


def memoized(successors: Successors[N]) -> Callable[[N], tuple[N, ...]]:
    """``successors`` evaluated at most once per node."""
    edges: dict[N, tuple[N, ...]] = {}

    def lookup(node: N) -> tuple[N, ...]:
        """The successors of ``node``, computed on first use."""
        if node not in edges:
            edges[node] = tuple(successors(node))
        return edges[node]

    return lookup


def nodes_reaching_cycles(starts: Iterable[N], successors: Successors[N]) -> set[N]:
    """The nodes of ``starts`` from which a directed walk reaches a cycle (self-loops included)."""
    starts = list(starts)
    edges = memoized(successors)
    on_path: set[N] = set()
    reaches: dict[N, bool] = {}  # set for every node visited; final once the node leaves the path
    for start in starts:
        if start in reaches:
            continue
        path: list[tuple[N, Iterator[N]]] = [(start, iter(edges(start)))]
        on_path.add(start)
        reaches[start] = False
        while path:
            node, remaining = path[-1]
            for successor in remaining:
                if successor in on_path:
                    reaches[node] = True
                elif successor in reaches:
                    reaches[node] = reaches[node] or reaches[successor]
                else:
                    on_path.add(successor)
                    reaches[successor] = False
                    path.append((successor, iter(edges(successor))))
                    break
            else:
                path.pop()
                on_path.discard(node)
                if path and reaches[node]:
                    reaches[path[-1][0]] = True
    return {node for node in starts if reaches[node]}


def nodes_on_cycles(nodes: Iterable[N], successors: Successors[N]) -> set[N]:
    """The nodes reachable from ``nodes`` that lie on a directed cycle.

    These are the members of every strongly connected component with more than one node, plus every node with a
    self-loop.
    """
    edges = memoized(successors)
    index_of: dict[N, int] = {}
    low: dict[N, int] = {}
    component_stack: list[N] = []
    in_component_stack: set[N] = set()
    result: set[N] = set()

    def enter(node: N) -> tuple[N, Iterator[N]]:
        """Number ``node``, push it on the component stack, and start iterating its successors."""
        index_of[node] = low[node] = len(index_of)
        component_stack.append(node)
        in_component_stack.add(node)
        return node, iter(edges(node))

    for root in nodes:
        if root in index_of:
            continue
        path = [enter(root)]
        while path:
            node, remaining = path[-1]
            for successor in remaining:
                if successor not in index_of:
                    path.append(enter(successor))
                    break
                if successor in in_component_stack:
                    low[node] = min(low[node], index_of[successor])
            else:
                path.pop()
                if path:
                    parent = path[-1][0]
                    low[parent] = min(low[parent], low[node])
                if low[node] == index_of[node]:
                    component = []
                    while True:
                        member = component_stack.pop()
                        in_component_stack.discard(member)
                        component.append(member)
                        if member == node:
                            break
                    if len(component) > 1 or node in edges(node):
                        result.update(component)
    return result


def nodes_reaching(targets: Iterable[N], nodes: Iterable[N], successors: Successors[N]) -> set[N]:
    """The nodes of ``nodes`` with a walk of at least one edge to a node of ``targets``."""
    nodes = list(nodes)
    edges = memoized(successors)
    predecessors: dict[N, list[N]] = {}
    pending = list(nodes)
    seen: set[N] = set(pending)
    while pending:
        node = pending.pop()
        for successor in edges(node):
            predecessors.setdefault(successor, []).append(node)
            if successor not in seen:
                seen.add(successor)
                pending.append(successor)
    found: set[N] = set()
    frontier = list(targets)
    while frontier:
        for predecessor in predecessors.get(frontier.pop(), ()):
            if predecessor not in found:
                found.add(predecessor)
                frontier.append(predecessor)
    return found.intersection(nodes)
