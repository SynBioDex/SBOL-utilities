"""Vendor the rule catalogs and ontology facts from an sbol-rs checkout into sbol_utilities.

sbol-rs (https://github.com/SynBioDex/sbol-rs) maintains the machine-readable SBOL 2.3.0 and SBOL 3.1.0 validation
rule catalogs and a compact ontology fact snapshot. This script converts the TOML catalogs to JSON (so the runtime
package needs no TOML parser on Python < 3.11) and copies the ontology facts with the label column blanked, since the
validators only need term identity, hierarchy, and classification.

Usage: python tools/sync_sbol_rs_data.py ~/git/SynBioDex/sbol-rs
Requires Python 3.11+ (tomllib).
"""

from __future__ import annotations

import argparse
import json
import subprocess
import tomllib
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "sbol_utilities" / "validation" / "data"
LABEL_COLUMN = 3


def _git_revision(repo: Path) -> str:
    result = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], capture_output=True, text=True, check=True)
    return result.stdout.strip()


def sync_catalog(repo: Path, version: str, revision: str) -> int:
    """Convert crates/sbol{version}/rules.toml into validation/data/sbol{version}_rules.json."""
    with open(repo / "crates" / f"sbol{version}" / "rules.toml", "rb") as handle:
        catalog = tomllib.load(handle)
    catalog["meta"]["source"] = f"sbol-rs@{revision}"
    out = DATA_DIR / f"sbol{version}_rules.json"
    out.write_text(json.dumps(catalog, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    return len(catalog["rule"])


def sync_ontology(repo: Path) -> int:
    """Copy the ontology facts TSV with term labels removed, plus the provenance table."""
    source_dir = repo / "crates" / "sbol-ontology" / "data"
    lines_out = []
    for line in (source_dir / "sbol3_ontology_facts.tsv").read_text(encoding="utf-8").splitlines():
        if line.startswith("term\t"):
            columns = line.split("\t")
            columns[LABEL_COLUMN] = "-"
            line = "\t".join(columns)
        lines_out.append(line)
    (DATA_DIR / "ontology_facts.tsv").write_text("\n".join(lines_out) + "\n", encoding="utf-8")
    (DATA_DIR / "ontology_sources.tsv").write_text(
        (source_dir / "ontology_sources.tsv").read_text(encoding="utf-8"), encoding="utf-8"
    )
    return sum(1 for line in lines_out if line.startswith("term\t"))


def main() -> None:
    """Command-line entry point."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("sbol_rs", type=Path, help="path to an sbol-rs checkout")
    args = parser.parse_args()
    repo = args.sbol_rs.expanduser().resolve()
    revision = _git_revision(repo)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    for version in ("2", "3"):
        print(f"SBOL {version}: {sync_catalog(repo, version, revision)} rules")
    print(f"ontology: {sync_ontology(repo)} terms")


if __name__ == "__main__":
    main()
