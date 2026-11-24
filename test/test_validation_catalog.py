"""Catalog completeness: every machine-checkable rule is implemented and has a firing negative case.

Per-rule cases live in ``test/validation_cases/sbol{2,3}/``. A file named ``<rule-id>[_<suffix>].<ext>`` (for example
``sbol3-10104_child_url.ttl``) must fire that rule; files under ``valid/`` must produce no issues. Every case is also
recorded in the sbol-rs goldens, so the differential test checks each case against sbol-rs.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from sbol_utilities.validation import ValidationConfig, validate_sbol2, validate_sbol3
from sbol_utilities.validation.sbol2 import REGISTRY as SBOL2
from sbol_utilities.validation.sbol3 import REGISTRY as SBOL3

CASES = Path(__file__).resolve().parent / "validation_cases"
SUFFIXES = {".ttl", ".xml", ".rdf", ".nt", ".jsonld"}
CASE_NAME = re.compile(r"^(sbol[23]-\d{5})(?:_.*)?$")
REGISTRIES = {"sbol2": SBOL2, "sbol3": SBOL3}
VALIDATORS = {"sbol2": validate_sbol2, "sbol3": validate_sbol3}


def _cases(version):
    return sorted(p for p in (CASES / version).rglob("*") if p.suffix in SUFFIXES and p.parent.name != "valid")


def _valid_cases(version):
    return sorted(p for p in (CASES / version / "valid").glob("*") if p.suffix in SUFFIXES)


@pytest.mark.parametrize("version", ["sbol2", "sbol3"])
def test_every_machine_checkable_rule_is_implemented(version):
    """No machine-checkable catalog rule lacks a registered implementation."""
    registry = REGISTRIES[version]
    implemented = registry.implemented()
    missing = sorted(r.id for r in registry.catalog.machine_checkable() if r.id not in implemented)
    assert not missing, f"{len(missing)} unimplemented {version} rules: {missing}"


@pytest.mark.parametrize("version", ["sbol2", "sbol3"])
def test_every_implemented_rule_has_a_negative_case(version):
    """Each machine-checkable rule has at least one case file named after it."""
    registry = REGISTRIES[version]
    covered = {CASE_NAME.match(p.stem).group(1) for p in _cases(version) if CASE_NAME.match(p.stem)}
    missing = sorted(r.id for r in registry.catalog.machine_checkable() if r.id not in covered)
    assert not missing, f"{len(missing)} {version} rules without a negative case: {missing}"


@pytest.mark.parametrize(
    "version,path",
    [pytest.param(v, p, id=f"{v}/{p.name}") for v in ("sbol2", "sbol3") for p in _cases(v)],
)
def test_negative_case_fires_its_rule(version, path):
    """A case file fires the rule it is named after (with every rule family enabled)."""
    match = CASE_NAME.match(path.stem)
    assert match, f"case file {path.name} is not named <rule-id>[_<suffix>]"
    report = VALIDATORS[version](path, ValidationConfig.all_on())
    assert match.group(1) in report.rule_ids(), str(report)


@pytest.mark.parametrize(
    "version,path",
    [pytest.param(v, p, id=f"{v}/valid/{p.name}") for v in ("sbol2", "sbol3") for p in _valid_cases(v)],
)
def test_valid_case_is_clean(version, path):
    """A case under valid/ produces no issues with every rule family enabled."""
    report = VALIDATORS[version](path, ValidationConfig.all_on())
    assert not report.issues, str(report)
