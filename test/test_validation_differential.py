"""Validation conformance: the validators must report exactly the issues SBOLTestSuite expects.

For every file with expected issues in SBOLTestSuite's ``Expected/validation/issues.json`` (the SBOL 2 corpora,
InvalidFiles, the SBOL 3 corpus, and SBOL3_InvalidFiles) and every configuration, the set of (rule, severity,
subject) issues must match.
"""

from __future__ import annotations

from xml.sax import SAXException

import pytest
import validation_goldens as vg
from rdflib.exceptions import ParserError
from rdflib.plugins.parsers.notation3 import BadSyntax

from sbol_utilities.rdf_io import load_graph
from sbol_utilities.validation import validate_sbol2, validate_sbol3

pytestmark = pytest.mark.sboltestsuite

NAMES = vg.name_params()

#: What reading a file raises when its RDF is malformed, across the RDF/XML and Turtle parsers
PARSE_ERRORS = (SAXException, ParserError, BadSyntax)


@pytest.mark.parametrize("name", NAMES)
def test_reports_expected_issues(name, sbol_test_suite):
    """Every configuration yields exactly the expected issue set."""
    entry = vg.expectations()["files"][name]
    path = vg.suite_path(name)
    validator = validate_sbol2 if entry["version"] == "sbol2" else validate_sbol3
    if vg.is_parse_error(name):
        with pytest.raises(PARSE_ERRORS):
            load_graph(path)
        return
    graph = load_graph(path)
    failures = []
    for config_name, config in vg.configs(entry["version"]).items():
        found = vg.actual(validator(graph, config))
        want = vg.expected(name, config_name)
        if found != want:
            failures.append(f"[{config_name}]\n{vg.describe(want - found, found - want)}")
    assert not failures, f"{name}\n" + "\n".join(failures)
