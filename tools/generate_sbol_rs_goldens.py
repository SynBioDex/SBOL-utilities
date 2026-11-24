"""Record sbol-rs validation verdicts and conversion fingerprints over the SBOLTestSuite corpus.

Writes two goldens under test/test_files/sbol_rs_golden/:

* ``validation.json`` -- sbol-rs validation verdicts, the reference for the Python validators.
* ``conversion.json`` -- canonical-graph fingerprints of sbol-rs conversion output, the reference for the Python
  converter: for each SBOL 2 corpus file, its upgrade and the upgrade of the downgrade of that upgrade; for each SBOL 3
  corpus file, its downgrade and the upgrade of that downgrade.

Validation:

For every corpus file and every configuration in :data:`CONFIGS`, runs ``sbol validate --format json``. Each file's
entry lists every distinct ``[rule, severity, subject, [config names]]`` reported, where the config names are those
under which sbol-rs reports that issue. No corpus content is stored: only file names,
rule ids, severities, and subject IRIs (blank-node subjects are written as ``_:``).

Usage: python tools/generate_sbol_rs_goldens.py /path/to/sbol-rs/target/release/sbol
The corpus is located the same way the tests locate it (see test/sboltestsuite.py).
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Dict, List

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "test"))

import sboltestsuite  # noqa: E402
from conversion_goldens import fingerprint  # noqa: E402
from rdflib import Graph  # noqa: E402

OUTPUT = REPO_ROOT / "test" / "test_files" / "sbol_rs_golden" / "validation.json"
CONVERSION_OUTPUT = OUTPUT.with_name("conversion.json")
LOCAL_TEST_FILES = REPO_ROOT / "test" / "test_files"
RULE_CASES = REPO_ROOT / "test" / "validation_cases"
RDF_SUFFIXES = {".ttl", ".xml", ".rdf", ".nt", ".jsonld"}

#: configuration name -> (sbol CLI flags, matching sbol_utilities ValidationConfig keyword arguments)
CONFIGS = {
    "sbol2": {
        "default": ([], {}),
        "incomplete": (["--incomplete"], {"complete": False}),
        "non_compliant": (["--non-compliant"], {"compliant": False}),
        "best_practice": (["--best-practice"], {"best_practice": True}),
    },
    "sbol3": {
        "default": ([], {}),
        "incomplete": (["--incomplete"], {"complete": False}),
        "non_compliant": (["--non-compliant"], {"compliant": False}),
        "no_best_practices": (["--no-best-practices"], {"best_practice": False}),
    },
}


def corpus_files() -> Dict[str, List[Path]]:
    """Files to record, keyed by validator version."""
    sbol2 = [p for corpus in sboltestsuite.SBOL2_CORPORA for p in sboltestsuite.sbol2_files(corpus)]
    sbol2 += sboltestsuite.sbol2_files(sboltestsuite.SBOL2_INVALID)
    sbol3 = list(sboltestsuite.sbol3_manifest())
    for version, files in (("sbol2", sbol2), ("sbol3", sbol3)):
        files.extend(sorted(p for p in (RULE_CASES / version).rglob("*") if p.suffix in RDF_SUFFIXES))
    return {"sbol2": sbol2, "sbol3": sbol3}


def golden_name(path: Path) -> str:
    """Key under which a file's verdicts are stored."""
    for base, prefix in ((LOCAL_TEST_FILES, "repo/"), (RULE_CASES, "cases/")):
        try:
            return prefix + path.relative_to(base).as_posix()
        except ValueError:
            pass
    return sboltestsuite.relative_name(path)


def run(cli: str, version: str, path: Path, flags: List[str]) -> List[List[str]]:
    """Validate one file with sbol-rs and return its normalized issues."""
    command = [cli, "validate", "--format", "json", "--sbol-version", version[-1], *flags, str(path)]
    result = subprocess.run(command, capture_output=True, text=True)
    if not result.stdout.strip():
        return [["<parse-error>", "Error", result.stderr.strip().splitlines()[-1] if result.stderr else ""]]
    report = json.loads(result.stdout)
    issues = set()
    for issue in report["issues"]:
        subject = issue.get("subject") or ""
        if subject.startswith("_:"):
            subject = "_:"
        issues.add((issue["rule"], issue["severity"], subject))
    return [list(i) for i in sorted(issues)]


def _convert(cli: str, command: str, source: Path, target: Path) -> bool:
    result = subprocess.run([cli, command, str(source), "-o", str(target)], capture_output=True, text=True)
    return result.returncode == 0 and target.exists()


def conversion_entry(cli: str, path: Path, version: str) -> Dict[str, str]:
    """Fingerprints of sbol-rs's conversion chain for one corpus file ('error' where a step fails)."""
    first, second = ("upgrade", "downgrade") if version == "sbol2" else ("downgrade", "upgrade")
    with tempfile.TemporaryDirectory() as tmp:
        step1 = Path(tmp) / ("step1.ttl" if first == "upgrade" else "step1.xml")
        step2 = Path(tmp) / ("step2.xml" if second == "downgrade" else "step2.ttl")
        entry = {first: "error"}
        if not _convert(cli, first, path, step1):
            return entry
        entry[first] = fingerprint(Graph().parse(str(step1), format="turtle" if step1.suffix == ".ttl" else "xml"))
        if version == "sbol2":
            # SBOL 2 -> 3 -> 2 -> 3: the second upgrade must land on the first (the representational fixed point)
            step3 = Path(tmp) / "step3.ttl"
            ok = _convert(cli, "downgrade", step1, step2) and _convert(cli, "upgrade", step2, step3)
            entry["roundtrip_upgrade"] = fingerprint(Graph().parse(str(step3), format="turtle")) if ok else "error"
        else:
            ok = _convert(cli, "upgrade", step1, step2)
            entry["roundtrip_upgrade"] = fingerprint(Graph().parse(str(step2), format="turtle")) if ok else "error"
        return entry


def write_conversion_goldens(cli: str, version_line: str) -> None:
    """Record conversion fingerprints for the SBOL 2 corpora and the SBOL 3 manifest."""
    jobs = [(p, "sbol2") for corpus in sboltestsuite.SBOL2_CORPORA for p in sboltestsuite.sbol2_files(corpus)]
    jobs += [(p, "sbol3") for p in sboltestsuite.sbol3_manifest()]
    with ThreadPoolExecutor(max_workers=8) as pool:
        entries = list(pool.map(lambda job: conversion_entry(cli, job[0], job[1]), jobs))
    files = {golden_name(p): {"version": v, **e} for (p, v), e in zip(jobs, entries)}
    header = {
        "generator": "tools/generate_sbol_rs_goldens.py",
        "sbol_rs": version_line,
        "sboltestsuite_commit": sboltestsuite.COMMIT,
    }
    lines = ["{"] + [f" {json.dumps(k)}: {json.dumps(v)}," for k, v in sorted(header.items())] + [' "files": {']
    lines.append(",\n".join(f"  {json.dumps(k)}: {json.dumps(v, sort_keys=True)}" for k, v in sorted(files.items())))
    lines += [" }", "}"]
    CONVERSION_OUTPUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"{len(files)} files -> {CONVERSION_OUTPUT.relative_to(REPO_ROOT)}")


def main() -> None:
    """Command-line entry point."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("cli", help="path to the sbol-rs `sbol` binary")
    args = parser.parse_args()
    version_line = subprocess.run([args.cli, "--version"], capture_output=True, text=True).stdout.strip()

    golden: Dict[str, object] = {
        "generator": "tools/generate_sbol_rs_goldens.py",
        "sbol_rs": version_line,
        "sboltestsuite_commit": sboltestsuite.COMMIT,
        "configs": {v: {name: cfg[1] for name, cfg in configs.items()} for v, configs in CONFIGS.items()},
        "files": {},
    }
    jobs = []
    for version, paths in corpus_files().items():
        for path in paths:
            for name, (flags, _) in CONFIGS[version].items():
                jobs.append((version, path, name, flags))
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda job: run(args.cli, job[0], job[1], job[3]), jobs))
    merged: Dict[str, Dict[tuple, List[str]]] = {}
    versions: Dict[str, str] = {}
    for (version, path, name, _), issues in zip(jobs, results):
        key = golden_name(path)
        versions[key] = version
        per_file = merged.setdefault(key, {})
        for issue in issues:
            per_file.setdefault(tuple(issue), []).append(name)
    golden["files"] = {
        key: {"version": versions[key], "issues": [[*issue, sorted(cfgs)] for issue, cfgs in sorted(issues.items())]}
        for key, issues in sorted(merged.items())
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    lines = ["{"]
    header = {k: v for k, v in golden.items() if k != "files"}
    for k, v in sorted(header.items()):
        lines.append(f" {json.dumps(k)}: {json.dumps(v, sort_keys=True)},")
    lines.append(' "files": {')
    file_entries: Dict[str, object] = golden["files"]  # type: ignore[assignment]
    entries = [f"  {json.dumps(k)}: {json.dumps(v)}" for k, v in file_entries.items()]
    lines.append(",\n".join(entries))
    lines.append(" }")
    lines.append("}")
    OUTPUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"{len(golden['files'])} files -> {OUTPUT.relative_to(REPO_ROOT)}")  # type: ignore[arg-type]
    write_conversion_goldens(args.cli, version_line)


if __name__ == "__main__":
    main()
