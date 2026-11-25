"""SBOLTestSuite conformance expectations for the SBOL 2 and SBOL 3 validators.

Each SBOL 2 corpus isolates one configuration axis:

* ``SBOL2`` is valid under every configuration (best-practice warnings only).
* ``SBOL2_ic`` (incomplete) has errors only while the completeness family is on.
* ``SBOL2_nc`` (non-compliant) has errors while the compliant-URI family is on.
* ``SBOL2_bp`` is free of errors unless best practices are enabled.

``SBOL3_InvalidFiles/sbol3-NNNNN_case.ttl`` each violate rule ``sbol3-NNNNN``, and the SBOL 3 corpus is entirely valid.

These properties hold whatever ``Expected/validation/issues.json`` says; the exact issues every file produces are
checked against that file in ``test_validation_differential.py``.
"""

from __future__ import annotations

import pytest

import sboltestsuite as suite
from sbol_utilities.validation import ValidationConfig, validate_sbol2, validate_sbol3

pytestmark = pytest.mark.sboltestsuite

ALL_ON = ValidationConfig.all_on()
INCOMPLETE = ValidationConfig(complete=False)


def error_issues(report):
    """The report's errors as strings, for readable assertion failures."""
    return [str(i) for i in report.errors]


@pytest.mark.corpus("SBOL2")
def test_sbol2_corpus_valid(path):
    """The core SBOL 2 corpus has no errors, even with every family on."""
    for config in (ValidationConfig(), ALL_ON):
        assert not error_issues(validate_sbol2(path, config))


@pytest.mark.corpus("SBOL2_ic")
def test_sbol2_incomplete_corpus(path):
    """Incomplete documents are error-free once the completeness family is off."""
    assert not error_issues(validate_sbol2(path, INCOMPLETE))


@pytest.mark.corpus("SBOL2_bp")
def test_sbol2_best_practice_corpus(path):
    """Best-practice fixtures are error-free with the default (best practice off) configuration."""
    assert not error_issues(validate_sbol2(path))


@pytest.mark.corpus("SBOL3_InvalidFiles")
def test_sbol3_invalid_files(path):
    """Each SBOL3_InvalidFiles fixture fires the rule it is named after."""
    assert suite.rule_for(path) in validate_sbol3(path, ALL_ON).rule_ids()


@pytest.mark.corpus("SBOL3")
def test_sbol3_corpus_valid(path):
    """Every SBOL 3 corpus fixture is error-free."""
    assert not error_issues(validate_sbol3(path))
