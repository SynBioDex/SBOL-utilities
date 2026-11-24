"""Differential conformance: the Python validators must report exactly what sbol-rs reports.

For every file in the sbol-rs goldens (the SBOLTestSuite SBOL 2 corpora, InvalidFiles, the SBOL 3 corpus, and the
per-rule cases under test/validation_cases) and every golden configuration, the set of (rule, severity, subject)
issues must match.
"""

from __future__ import annotations

import pytest
import validation_goldens as vg
from rdflib import Graph

from sbol_utilities.rdf_io import guess_format
from sbol_utilities.validation import validate_sbol2, validate_sbol3

pytestmark = pytest.mark.sboltestsuite

NAMES = sorted(vg.goldens()["files"])


@pytest.mark.parametrize("name", NAMES)
def test_matches_sbol_rs(name, sbol_test_suite):
    """Every golden configuration yields the same issue set as sbol-rs."""
    entry = vg.goldens()["files"][name]
    path = vg.golden_path(name)
    validator = validate_sbol2 if entry["version"] == "sbol2" else validate_sbol3
    if vg.is_parse_error(name):
        # sbol-rs rejects the file while reading it; Python must either fail to read it or report an error
        try:
            report = validator(
                Graph().parse(str(path), format=guess_format(path)), vg.configs(entry["version"])["default"]
            )
        except Exception:
            return
        assert report.errors, f"{name}: sbol-rs rejects this file at read time, but Python reports no error"
        return
    graph = Graph().parse(str(path), format=guess_format(path))
    failures = []
    for config_name, config in vg.configs(entry["version"]).items():
        found = vg.actual(validator(graph, config))
        want = vg.expected(name, config_name)
        if found != want:
            failures.append(f"[{config_name}]\n{vg.describe(want - found, found - want)}")
    assert not failures, f"{name}\n" + "\n".join(failures)
