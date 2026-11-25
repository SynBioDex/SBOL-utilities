"""Catalog completeness: every machine-checkable rule is implemented and fires on an SBOLTestSuite invalid file.

SBOLTestSuite names each invalid file after the rule it violates: ``InvalidFiles/sbol-NNNNN[_case].xml`` for rule
``sbol2-NNNNN`` and ``SBOL3_InvalidFiles/sbol3-NNNNN_case.ttl`` for rule ``sbol3-NNNNN``. A rule counts as covered
when such a file is expected to fire it (``Expected/validation/issues.json``). ``SBOL3/validation_examples/`` holds
documents that must be clean.
"""

from __future__ import annotations

import pytest
import sboltestsuite as suite
import validation_goldens as vg

from sbol_utilities.validation import ValidationConfig, validate_sbol3
from sbol_utilities.validation.sbol2 import REGISTRY as SBOL2
from sbol_utilities.validation.sbol3 import REGISTRY as SBOL3

REGISTRIES = {"sbol2": SBOL2, "sbol3": SBOL3}
INVALID_FILES = {"sbol2": suite.SBOL2_INVALID, "sbol3": suite.SBOL3_INVALID}

#: Rules that act only when references are resolved against other documents. Validation of a single document has
#: no implementation for them, and no single-document case can fire them.
RESOLVER_ONLY = {
    "sbol3-10114": "warns on unresolved external TopLevel references only in resolver-aware validation",
}


def _covered(version: str) -> set[str]:
    """The rules that an invalid file named after them is expected to fire."""
    files = suite.CORPORA[INVALID_FILES[version]]()
    return {rule for path in files if vg.fires(suite.relative_name(path), rule := suite.rule_for(path))}


@pytest.mark.parametrize("version", ["sbol2", "sbol3"])
def test_every_machine_checkable_rule_is_implemented(version):
    """No machine-checkable catalog rule lacks a registered implementation."""
    registry = REGISTRIES[version]
    implemented = registry.implemented()
    missing = sorted(
        r.id for r in registry.catalog.machine_checkable() if r.id not in implemented and r.id not in RESOLVER_ONLY
    )
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
@pytest.mark.corpus("SBOL3/validation_examples")
def test_validation_example_is_clean(path):
    """A validation example produces no issues with every rule family enabled."""
    report = validate_sbol3(path, ValidationConfig.all_on())
    assert not report.issues, str(report)
