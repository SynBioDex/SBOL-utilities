"""Expected validation issues, from SBOLTestSuite's ``Expected/validation/issues.json``.

Each file entry lists the distinct ``[rule, severity, subject, [config names]]`` issues a conforming validator
reports for that file, and ``configs`` defines each config name as rule-family gate settings.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Set, Tuple

import pytest
import sboltestsuite

from sbol_utilities.validation import ValidationConfig, ValidationReport

IssueKey = Tuple[str, str, str]


@lru_cache(maxsize=None)
def expectations() -> dict:
    """The parsed expected-issues file."""
    path = sboltestsuite.suite_root() / sboltestsuite.EXPECTED / "validation" / "issues.json"
    return json.loads(path.read_text(encoding="utf-8"))


def name_params() -> list:
    """pytest parameters for every file with expected issues, safe to call at collection time."""
    try:
        return [pytest.param(name, id=name) for name in sorted(expectations()["files"])]
    except sboltestsuite.SuiteUnavailable:
        return [sboltestsuite.UNAVAILABLE]


def configs(version: str) -> Dict[str, ValidationConfig]:
    """Config name -> equivalent ValidationConfig, for ``sbol2`` or ``sbol3``."""
    return {name: ValidationConfig(**kwargs) for name, kwargs in expectations()["configs"][version].items()}


def expected(name: str, config: str) -> Set[IssueKey]:
    """(rule, severity, subject) issues expected for a file under a config."""
    entry = expectations()["files"][name]
    return {(rule, severity, subject) for rule, severity, subject, cfgs in entry["issues"] if config in cfgs}


def fires(name: str, rule: str) -> bool:
    """Whether ``rule`` is expected to fire on the file under any config."""
    return any(issue[0] == rule for issue in expectations()["files"].get(name, {}).get("issues", []))


def actual(report: ValidationReport) -> Set[IssueKey]:
    """(rule, severity, subject) issues of a report, normalized like the expectations."""
    result = set()
    for issue in report.issues:
        subject = issue.subject or ""
        if subject.startswith("_:"):
            subject = "_:"
        result.add((issue.rule, issue.severity, subject))
    return result


def is_parse_error(name: str) -> bool:
    """Whether the file's RDF is expected to be unreadable."""
    return any(rule == "<parse-error>" for rule, *_ in expectations()["files"][name]["issues"])


def describe(missing: Set[IssueKey], extra: Set[IssueKey], limit: int = 25) -> str:
    """Readable summary of a mismatch."""
    lines: List[str] = []
    for label, items in (("missing (expected, not reported)", missing), ("extra (reported, not expected)", extra)):
        if items:
            lines.append(f"{label}: {len(items)}")
            lines.extend(f"  {rule} {severity} {subject}" for rule, severity, subject in sorted(items)[:limit])
    return "\n".join(lines)


def suite_path(name: str) -> Path:
    """Filesystem path of a suite-relative file name."""
    return sboltestsuite.suite_root() / name
