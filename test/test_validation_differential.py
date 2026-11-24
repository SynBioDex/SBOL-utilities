"""Differential conformance: the Python validators must report exactly what sbol-rs reports.

For every file in the sbol-rs goldens (the SBOLTestSuite SBOL 2 corpora, InvalidFiles, the SBOL 3 corpus, and the
per-rule cases under test/validation_cases) and every golden configuration, the set of (rule, severity, subject)
issues must match, apart from the documented divergences in :data:`KNOWN_DIVERGENCES`.
"""

from __future__ import annotations

from typing import Dict, Set, Tuple

import pytest
import validation_goldens as vg

from sbol_utilities.rdf_io import load_graph
from sbol_utilities.validation import validate_sbol2, validate_sbol3

pytestmark = pytest.mark.sboltestsuite

NAMES = sorted(vg.goldens()["files"])

_REPEATED_ROLE = (
    "The file states the same sbol:role triple three times. An RDF graph is a set, so rdflib holds it once; "
    "sbol-rs counts each repetition as another sequence-feature role."
)

#: (golden file, config) -> (sbol-rs issues the Python validators correctly do not report, reason)
KNOWN_DIVERGENCES: Dict[Tuple[str, str], Tuple[Set[vg.IssueKey], str]] = {
    ("SBOL2_bp/Provenance_SpecifyAmplifyOperation.xml", "best_practice"): (
        {("sbol2-10527", "Warning", "http://sbolstandard.org/build/dna_construct")},
        _REPEATED_ROLE,
    ),
    ("SBOL2_bp/Provenance_SpecifyCutOperation.xml", "best_practice"): (
        {("sbol2-10527", "Warning", "http://sbolstandard.org/build/linearized_vector")},
        _REPEATED_ROLE,
    ),
}


@pytest.mark.parametrize("name", NAMES)
def test_matches_sbol_rs(name, sbol_test_suite):
    """Every golden configuration yields the same issue set as sbol-rs."""
    entry = vg.goldens()["files"][name]
    path = vg.golden_path(name)
    validator = validate_sbol2 if entry["version"] == "sbol2" else validate_sbol3
    if vg.is_parse_error(name):
        # sbol-rs rejects the file while reading it; Python must either fail to read it or report an error
        try:
            report = validator(load_graph(path), vg.configs(entry["version"])["default"])
        except Exception:
            return
        assert report.errors, f"{name}: sbol-rs rejects this file at read time, but Python reports no error"
        return
    graph = load_graph(path)
    failures = []
    for config_name, config in vg.configs(entry["version"]).items():
        found = vg.actual(validator(graph, config))
        want = vg.expected(name, config_name)
        divergent, _reason = KNOWN_DIVERGENCES.get((name, config_name), (set(), ""))
        want -= divergent
        if found != want:
            failures.append(f"[{config_name}]\n{vg.describe(want - found, found - want)}")
    assert not failures, f"{name}\n" + "\n".join(failures)


@pytest.mark.parametrize("key", sorted(KNOWN_DIVERGENCES))
def test_known_divergences_are_still_in_the_goldens(key):
    """Each documented divergence still describes a golden issue, so stale entries are noticed."""
    name, config = key
    divergent, _reason = KNOWN_DIVERGENCES[key]
    assert divergent <= vg.expected(name, config)
