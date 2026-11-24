"""Catalog completeness: every machine-checkable rule is implemented and fires on an SBOLTestSuite invalid file.

SBOLTestSuite names each invalid file after the rule it violates: ``InvalidFiles/sbol-NNNNN[_case].xml`` for rule
``sbol2-NNNNN`` and ``SBOL3_InvalidFiles/sbol3-NNNNN_case.ttl`` for rule ``sbol3-NNNNN``. A rule counts as covered
when such a file is expected to fire it (``Expected/validation/issues.json``). ``SBOL3/validation_examples/`` holds
documents that must be clean.
"""

from __future__ import annotations

import re

import pytest
import sboltestsuite as suite
import validation_goldens as vg

from sbol_utilities.validation import ValidationConfig, validate_sbol3
from sbol_utilities.validation.sbol2 import REGISTRY as SBOL2
from sbol_utilities.validation.sbol3 import REGISTRY as SBOL3

REGISTRIES = {"sbol2": SBOL2, "sbol3": SBOL3}
CASE_NAMES = {
    "sbol2": (suite.SBOL2_INVALID, re.compile(r"^sbol-(\d{5})(?:_.*)?\.xml$"), "sbol2-"),
    "sbol3": (suite.SBOL3_INVALID, re.compile(r"^sbol3-(\d{5})(?:_.*)?\.ttl$"), "sbol3-"),
}

#: Rules that act only when references are resolved against other documents. Offline validation evaluates nothing
#: for them, so no single-document case can fire them.
RESOLVER_ONLY = {
    "sbol3-10114": "warns on unresolved external TopLevel references only in resolver-aware validation",
}


def _covered(version: str) -> set:
    directory, pattern, prefix = CASE_NAMES[version]
    covered = set()
    for path in sorted((suite.suite_root() / directory).iterdir()):
        match = pattern.match(path.name)
        if match and vg.fires(suite.relative_name(path), prefix + match.group(1)):
            covered.add(prefix + match.group(1))
    return covered


@pytest.mark.parametrize("version", ["sbol2", "sbol3"])
def test_every_machine_checkable_rule_is_implemented(version):
    """No machine-checkable catalog rule lacks a registered implementation."""
    registry = REGISTRIES[version]
    implemented = registry.implemented()
    missing = sorted(r.id for r in registry.catalog.machine_checkable() if r.id not in implemented)
    assert not missing, f"{len(missing)} unimplemented {version} rules: {missing}"


@pytest.mark.sboltestsuite
@pytest.mark.parametrize("version", ["sbol2", "sbol3"])
def test_every_rule_has_an_invalid_file(version, sbol_test_suite):
    """Each machine-checkable rule has an SBOLTestSuite invalid file that is expected to fire it."""
    covered = _covered(version)
    missing = sorted(
        r.id
        for r in REGISTRIES[version].catalog.machine_checkable()
        if r.id not in covered and r.id not in RESOLVER_ONLY
    )
    assert not missing, f"{len(missing)} {version} rules without an invalid file in SBOLTestSuite: {missing}"


@pytest.mark.sboltestsuite
@pytest.mark.parametrize(
    "path", suite.corpus_params(lambda: sorted((suite.suite_root() / "SBOL3" / "validation_examples").glob("*.ttl")))
)
def test_validation_example_is_clean(path, sbol_test_suite):
    """A validation example produces no issues with every rule family enabled."""
    report = validate_sbol3(path, ValidationConfig.all_on())
    assert not report.issues, str(report)
