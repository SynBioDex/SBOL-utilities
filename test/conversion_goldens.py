"""Expected SBOL 2 <-> SBOL 3 conversions, from SBOLTestSuite's ``Expected/conversion/``.

``index.json`` maps each corpus file to its expected outputs (suite-relative paths, or ``fixed-point`` for a round
trip that reproduces the upgrade). Graphs are compared as canonical N-Triples sets, which treats blank nodes up to
isomorphism.
"""

from __future__ import annotations

import sboltestsuite
from rdflib import Graph
from rdflib.compare import to_canonical_graph

from sbol_utilities.rdf_io import load_graph


def canonical_lines(graph: Graph) -> list[str]:
    """Sorted N-Triples lines of a graph with blank nodes canonically relabeled."""
    text = to_canonical_graph(graph).serialize(format="nt")
    return sorted(line for line in text.splitlines() if line.strip())


def entry(name: str) -> dict:
    """Expected outputs of one suite-relative corpus file."""
    index = sboltestsuite.load_json(f"{sboltestsuite.EXPECTED}/conversion/index.json")["files"]
    assert name in index, f"{name} has no entry in Expected/conversion/index.json"
    return index[name]


def expected_graph(relative: str) -> Graph:
    """Parse one expected output file."""
    return load_graph(sboltestsuite.suite_root() / relative)


def diff(actual: Graph, expected: Graph) -> str:
    """Triple-level description of how two graphs differ ('' when they are equivalent)."""
    return sboltestsuite.set_diff(set(canonical_lines(expected)), set(canonical_lines(actual)))
