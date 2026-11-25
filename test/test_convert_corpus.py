"""SBOLTestSuite conversion conformance: conversions must produce the graphs ``Expected/conversion/`` records.

For each SBOL 2 corpus file the upgrade must match its expected SBOL 3 graph, and upgrading the downgrade of that
upgrade must reproduce it (the SBOL 2 -> 3 -> 2 -> 3 fixed point) or match the recorded round trip. For each SBOL 3
corpus file the downgrade, and the upgrade of that downgrade, must match.
"""

from __future__ import annotations

import pytest

import conversion_goldens as cg
import sboltestsuite as suite
from sbol_utilities.convert import downgrade, upgrade
from sbol_utilities.rdf_io import load_graph

pytestmark = pytest.mark.sboltestsuite


def check_against_golden(actual, relative: str, what: str) -> None:
    """Assert a converted graph equals the expected graph stored at ``relative``."""
    difference = cg.diff(actual, cg.expected_graph(relative))
    assert not difference, f"{what} differs from {relative}\n{difference}"


@pytest.mark.corpus("SBOL2-all")
def test_sbol2_upgrade_matches_expected(path):
    """Upgrade and the 3 -> 2 -> 3 round trip both match the expected graphs."""
    entry = cg.entry(suite.relative_name(path))
    upgraded, _ = upgrade(load_graph(path))
    check_against_golden(upgraded, entry["upgrade"], "upgrade")
    again, _ = upgrade(downgrade(upgraded)[0])
    if entry["roundtrip"] == "fixed-point":
        check_against_golden(again, entry["upgrade"], "round trip (expected to reproduce the upgrade)")
    else:
        check_against_golden(again, entry["roundtrip"], "round trip")


@pytest.mark.corpus("SBOL3")
def test_sbol3_downgrade_matches_expected(path):
    """Downgrade and the 2 -> 3 re-upgrade both match the expected graphs."""
    entry = cg.entry(suite.relative_name(path))
    downgraded, _ = downgrade(load_graph(path))
    check_against_golden(downgraded, entry["downgrade"], "downgrade")
    again, _ = upgrade(downgraded)
    check_against_golden(again, entry["roundtrip"], "round trip")
