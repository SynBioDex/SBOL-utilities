"""SBOLTestSuite conversion conformance: the Python converter must produce sbol-rs's graphs.

For each SBOL 2 corpus file the upgrade, and the upgrade of the downgrade of that upgrade, must match sbol-rs's output
(compared by canonical-graph fingerprint; see test/conversion_goldens.py). For compliant inputs that second upgrade
is the first one again: the SBOL 2 -> 3 -> 2 -> 3 fixed point. For each SBOL 3 corpus file the downgrade, and the
upgrade of that downgrade, must match.

Set ``SBOL_RS_CLI`` to an sbol-rs ``sbol`` binary to get a triple-level diff against sbol-rs on mismatch.
"""

from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path

import conversion_goldens as cg
import pytest
import sboltestsuite as suite
from rdflib import Graph

from sbol_utilities.rdf_io import load_graph
from sbol_utilities.convert import downgrade, upgrade

pytestmark = pytest.mark.sboltestsuite


def _sbol2_files():
    return [p for corpus in suite.SBOL2_CORPORA for p in suite.sbol2_files(corpus)]


def _golden(path):
    return cg.goldens()["files"][suite.relative_name(path)]


def _sbol_rs_graph(command: str, source: Graph, out_suffix: str) -> Graph:
    """Run one sbol-rs conversion step on a graph (only used to explain a mismatch)."""
    cli = os.environ["SBOL_RS_CLI"]
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / ("in.ttl" if command == "downgrade" else "in.xml")
        source.serialize(str(src), format="turtle" if src.suffix == ".ttl" else "xml")
        out = Path(tmp) / f"out{out_suffix}"
        subprocess.run([cli, command, str(src), "-o", str(out)], check=True, capture_output=True)
        return load_graph(out)


def _explain(ours: Graph, step, limit: int = 40) -> str:
    if not os.environ.get("SBOL_RS_CLI"):
        return "set SBOL_RS_CLI to an sbol-rs `sbol` binary for a triple-level diff"
    theirs = step()
    mine, ref = set(cg.canonical_lines(ours)), set(cg.canonical_lines(theirs))
    lines = [f"sbol-rs only ({len(ref - mine)}):"] + sorted(ref - mine)[:limit]
    lines += [f"python only ({len(mine - ref)}):"] + sorted(mine - ref)[:limit]
    return "\n".join(lines)


@pytest.mark.parametrize("path", suite.corpus_params(_sbol2_files))
def test_sbol2_upgrade_matches_sbol_rs(path, sbol_test_suite):
    """Upgrade and the 3 -> 2 -> 3 round trip both match sbol-rs."""
    golden = _golden(path)
    source = load_graph(path)
    if golden["upgrade"] == "error":
        with pytest.raises(Exception):
            upgrade(source)
        return
    upgraded, _ = upgrade(source)
    assert cg.fingerprint(upgraded) == golden["upgrade"], _explain(
        upgraded, lambda: _sbol_rs_graph("upgrade", source, ".ttl")
    )
    if golden["roundtrip_upgrade"] == "error":
        pytest.skip("sbol-rs cannot complete this round trip, so there is no reference graph to compare against")
    downgraded, _ = downgrade(upgraded)
    again, _ = upgrade(downgraded)
    assert cg.fingerprint(again) == golden["roundtrip_upgrade"], _explain(
        again, lambda: _sbol_rs_graph("upgrade", _sbol_rs_graph("downgrade", upgraded, ".xml"), ".ttl")
    )


@pytest.mark.parametrize("path", suite.corpus_params(suite.sbol3_manifest))
def test_sbol3_downgrade_matches_sbol_rs(path, sbol_test_suite):
    """Downgrade and the 2 -> 3 re-upgrade both match sbol-rs."""
    golden = _golden(path)
    source = load_graph(path)
    downgraded, _ = downgrade(source)
    assert cg.fingerprint(downgraded) == golden["downgrade"], _explain(
        downgraded, lambda: _sbol_rs_graph("downgrade", source, ".xml")
    )
    again, _ = upgrade(downgraded)
    assert cg.fingerprint(again) == golden["roundtrip_upgrade"], _explain(
        again, lambda: _sbol_rs_graph("upgrade", downgraded, ".ttl")
    )
