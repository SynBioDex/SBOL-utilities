"""Expected SBOL 2 <-> SBOL 3 conversions, from SBOLTestSuite's ``Expected/conversion/``.

``index.json`` maps each corpus file to its expected outputs (suite-relative paths, or ``fixed-point`` for a round
trip that reproduces the upgrade). Graphs are compared as canonical N-Triples sets, which treats blank nodes up to
isomorphism.
"""

from __future__ import annotations

import json
from functools import lru_cache
from typing import List, Set

import sboltestsuite
from rdflib import Graph
from rdflib.compare import to_canonical_graph

from sbol_utilities.rdf_io import load_graph


def canonical_lines(graph: Graph) -> List[str]:
    """Sorted N-Triples lines of a graph with blank nodes canonically relabeled."""
    text = to_canonical_graph(graph).serialize(format="nt")
    if isinstance(text, bytes):
        text = text.decode("utf-8")
    return sorted(line for line in text.splitlines() if line.strip())


@lru_cache(maxsize=None)
def index() -> dict:
    """The parsed conversion index."""
    path = sboltestsuite.suite_root() / sboltestsuite.EXPECTED / "conversion" / "index.json"
    return json.loads(path.read_text(encoding="utf-8"))


def entry(name: str) -> dict:
    """Expected outputs of one suite-relative corpus file."""
    return index()["files"][name]


def expected_graph(relative: str) -> Graph:
    """Parse one expected output file."""
    return load_graph(sboltestsuite.suite_root() / relative)


def diff(actual: Graph, expected: Graph, limit: int = 40) -> str:
    """Triple-level description of how two graphs differ ('' when they are equivalent)."""
    mine: Set[str] = set(canonical_lines(actual))
    want: Set[str] = set(canonical_lines(expected))
    if mine == want:
        return ""
    lines = [f"expected only ({len(want - mine)}):", *sorted(want - mine)[:limit]]
    lines += [f"actual only ({len(mine - want)}):", *sorted(mine - want)[:limit]]
    return "\n".join(lines)
