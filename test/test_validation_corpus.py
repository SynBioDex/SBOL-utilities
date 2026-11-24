"""SBOLTestSuite conformance expectations for the SBOL 2 and SBOL 3 validators.

Each SBOL 2 corpus isolates one configuration axis:

* ``SBOL2`` is valid under every configuration (best-practice warnings only).
* ``SBOL2_ic`` (incomplete) has errors only while the completeness family is on.
* ``SBOL2_nc`` (non-compliant) has errors while the compliant-URI family is on.
* ``SBOL2_bp`` is free of errors unless best practices are enabled.

``InvalidFiles/sbol-NNNNN.xml`` each violate rule ``sbol2-NNNNN``. The SBOL 3 corpus is entirely valid.
"""

from __future__ import annotations

import re

import pytest
import sboltestsuite as suite
import validation_goldens as vg

from sbol_utilities.validation import ValidationConfig, validate_sbol2, validate_sbol3

pytestmark = pytest.mark.sboltestsuite

ALL_ON = ValidationConfig.all_on()
INCOMPLETE = ValidationConfig(complete=False)
NON_COMPLIANT = ValidationConfig(compliant=False)


def _errors(report):
    return [str(i) for i in report.errors]


@pytest.mark.parametrize("path", suite.corpus_params(lambda: suite.sbol2_files("SBOL2")))
def test_sbol2_corpus_valid(path, sbol_test_suite):
    """The core SBOL 2 corpus has no errors, even with every family on."""
    for config in (ValidationConfig(), ALL_ON):
        assert not _errors(validate_sbol2(path, config))


@pytest.mark.parametrize("path", suite.corpus_params(lambda: suite.sbol2_files("SBOL2_ic")))
def test_sbol2_incomplete_corpus(path, sbol_test_suite):
    """Incomplete documents are error-free once the completeness family is off."""
    assert not _errors(validate_sbol2(path, INCOMPLETE))


@pytest.mark.parametrize("path", suite.corpus_params(lambda: suite.sbol2_files("SBOL2_bp")))
def test_sbol2_best_practice_corpus(path, sbol_test_suite):
    """Best-practice fixtures are error-free with the default (best practice off) configuration."""
    assert not _errors(validate_sbol2(path))


@pytest.mark.parametrize("path", suite.corpus_params(lambda: suite.sbol2_files("SBOL2_nc")))
def test_sbol2_non_compliant_corpus(path, sbol_test_suite):
    """Non-compliant fixtures fail the compliant-URI family exactly when sbol-rs says they do."""
    name = suite.relative_name(path)
    report = validate_sbol2(path, ValidationConfig())
    assert {i.rule for i in report.errors} == {r for r, s, _ in vg.expected(name, "default") if s == "Error"}


@pytest.mark.parametrize("path", suite.corpus_params(lambda: suite.sbol2_files(suite.SBOL2_INVALID)))
def test_sbol2_invalid_files(path, sbol_test_suite):
    """Each InvalidFiles fixture fires its own rule wherever sbol-rs strictly fires it."""
    name = suite.relative_name(path)
    if vg.is_parse_error(name):
        pytest.skip("sbol-rs rejects this file at parse time")
    rule = re.sub(r"^sbol-(\d+)\.xml$", r"sbol2-\1", path.name)
    golden_rules = {r for r, s, _ in vg.expected(name, "best_practice") if s == "Error"}
    if rule not in golden_rules:
        pytest.skip(f"sbol-rs defers {rule} for this fixture (see sbol-rs invalid_files_deferred.in)")
    assert rule in {i.rule for i in validate_sbol2(path, ALL_ON).errors}


@pytest.mark.parametrize("path", suite.corpus_params(suite.sbol3_manifest))
def test_sbol3_corpus_valid(path, sbol_test_suite):
    """Every SBOL 3 corpus fixture is error-free."""
    assert not _errors(validate_sbol3(path))
