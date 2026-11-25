"""Unit tests for the validation building blocks that the corpus does not exercise at scale."""

from __future__ import annotations

import pytest
from rdflib import Graph, URIRef

from sbol_utilities.identifiers import is_valid_display_id
from sbol_utilities.validation import ValidationConfig, validate_sbol3
from sbol_utilities.validation.datatypes import I64_MAX, I64_MIN, is_date_time_lexical, is_float_lexical, parse_i64
from sbol_utilities.validation.graphs import nodes_on_cycles, nodes_reaching, nodes_reaching_cycles
from sbol_utilities.vocab import PROV, SBOL3, TYPE

EX = "https://example.org/"


def successors_in(edges: dict[str, list[str]]):
    """A successors function over an adjacency table."""
    return lambda node: edges.get(node, ())


CYCLE_CASES = [
    pytest.param({"a": ["b"], "b": ["c"], "c": []}, set(), set(), id="chain"),
    pytest.param({"a": ["a"]}, {"a"}, {"a"}, id="self-loop"),
    pytest.param({"a": ["b"], "b": ["a"], "c": ["a"], "d": []}, {"a", "b", "c"}, {"a", "b"}, id="cycle-with-tail"),
    pytest.param({"a": ["b", "c"], "b": ["d"], "c": ["d"], "d": []}, set(), set(), id="diamond"),
    pytest.param({"a": ["b"], "b": ["c"], "c": ["b"], "d": ["a"]}, {"a", "b", "c", "d"}, {"b", "c"}, id="late-cycle"),
]


@pytest.mark.parametrize("edges, reaching, on_cycle", CYCLE_CASES)
def test_nodes_reaching_cycles(edges, reaching, on_cycle):
    assert nodes_reaching_cycles(edges, successors_in(edges)) == reaching


@pytest.mark.parametrize("edges, reaching, on_cycle", CYCLE_CASES)
def test_nodes_on_cycles(edges, reaching, on_cycle):
    assert nodes_on_cycles(edges, successors_in(edges)) == on_cycle


def test_nodes_reaching_cycles_reports_only_starts():
    edges = {"a": ["b"], "b": ["b"]}
    assert nodes_reaching_cycles(["a"], successors_in(edges)) == {"a"}


def test_nodes_reaching_needs_at_least_one_edge():
    edges = {"a": ["b"], "b": ["c"], "c": [], "d": []}
    assert nodes_reaching(["c"], edges, successors_in(edges)) == {"a", "b"}
    assert nodes_reaching(["a"], edges, successors_in(edges)) == set()


def test_cycle_queries_handle_long_chains():
    edges = {n: [n + 1] for n in range(50_000)}
    assert nodes_reaching_cycles(edges, successors_in(edges)) == set()
    assert nodes_on_cycles(edges, successors_in(edges)) == set()
    edges[50_000] = [0]
    assert len(nodes_on_cycles(edges, successors_in(edges))) == 50_001


def test_cycle_queries_are_linear_on_ladders():
    """Each rung doubles the number of distinct walks; every node is still visited once."""
    edges = {(side, rung): [("l", rung + 1), ("r", rung + 1)] for rung in range(2_000) for side in "lr"}
    assert nodes_reaching_cycles(edges, successors_in(edges)) == set()


def derivation_graph(edges: dict[str, list[str]]) -> Graph:
    """An SBOL 3 document of Collections linked by prov:wasDerivedFrom."""
    graph = Graph()
    for name, sources in edges.items():
        subject = URIRef(EX + name)
        graph.add((subject, TYPE, SBOL3.Collection))
        graph.add((subject, SBOL3.hasNamespace, URIRef(EX.rstrip("/"))))
        for source in sources:
            graph.add((subject, PROV.wasDerivedFrom, URIRef(EX + source)))
    return graph


def derivation_cycle_subjects(edges: dict[str, list[str]]) -> set:
    report = validate_sbol3(derivation_graph(edges), ValidationConfig(complete=False, best_practice=False))
    return {issue.subject for issue in report.issues if issue.rule == "sbol3-10203"}


def test_derivation_cycle_is_reported_on_every_object_leading_to_it():
    assert derivation_cycle_subjects({"a": ["b"], "b": ["c"], "c": ["b"], "d": []}) == {EX + "a", EX + "b", EX + "c"}


def test_long_derivation_chain_validates():
    assert derivation_cycle_subjects({f"n{i}": [f"n{i + 1}"] for i in range(1_500)}) == set()


def test_derivation_ladder_validates():
    edges = {f"{side}{rung}": [f"l{rung + 1}", f"r{rung + 1}"] for rung in range(40) for side in "lr"}
    assert derivation_cycle_subjects(edges) == set()


@pytest.mark.parametrize(
    "text, valid",
    [
        ("promoter", True),
        ("_x1", True),
        ("BBa_J23101", True),
        ("1x", False),
        ("a-b", False),
        ("", False),
        ("a\n", False),
    ],
)
def test_display_id_syntax(text, valid):
    assert is_valid_display_id(text) is valid


@pytest.mark.parametrize(
    "text, value",
    [
        ("0", 0),
        ("+7", 7),
        ("-12", -12),
        (str(I64_MAX), I64_MAX),
        (str(I64_MIN), I64_MIN),
        (str(I64_MAX + 1), None),
        (str(I64_MIN - 1), None),
        ("1.0", None),
        ("", None),
        ("١٢", None),
        ("12\n", None),
        (None, None),
    ],
)
def test_parse_i64(text, value):
    assert parse_i64(text) == value


@pytest.mark.parametrize(
    "text, valid",
    [("1", True), ("-1.5e3", True), (".5", True), ("5.", True), ("INF", True), ("-inf", True), ("NaN", True)]
    + [("", False), ("e3", False), ("1e", False), ("1.5\n", False)],
)
def test_float_lexical_form(text, valid):
    assert is_float_lexical(text) is valid


@pytest.mark.parametrize(
    "text, valid",
    [("2024-01-02T03:04:05", True), ("2024-01-02T03:04:05.250Z", True), ("2024-01-02T03:04:05+01:00", True)]
    + [("2024-01-02", False), ("2024-01-02 03:04:05", False), ("2024-01-02T03:04:05Z\n", False)],
)
def test_date_time_lexical_form(text, valid):
    assert is_date_time_lexical(text) is valid
