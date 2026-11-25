"""Expected validation issues, from SBOLTestSuite's ``Expected/validation/issues.json``.

Each file entry lists the distinct ``[rule, severity, subject, [config names]]`` issues a conforming validator
reports for that file, and ``configs`` defines each config name as rule-family gate settings.
"""

from __future__ import annotations

from pathlib import Path

import sboltestsuite

from sbol_utilities.validation import ValidationConfig, ValidationReport

IssueKey = tuple[str, str, str]


def expectations() -> dict:
    """The parsed expected-issues file."""
    return sboltestsuite.load_json(f"{sboltestsuite.EXPECTED}/validation/issues.json")


def configs(version: str) -> dict[str, ValidationConfig]:
    """Config name -> equivalent ValidationConfig, for ``sbol2`` or ``sbol3``."""
    return {name: ValidationConfig(**kwargs) for name, kwargs in expectations()["configs"][version].items()}


def expected(name: str, config: str) -> set[IssueKey]:
    """(rule, severity, subject) issues expected for a file under a config."""
    entry = expectations()["files"][name]
    return {(rule, severity, subject) for rule, severity, subject, cfgs in entry["issues"] if config in cfgs}


def fires(name: str, rule: str) -> bool:
    """Whether ``rule`` is expected to fire on the file under any config."""
    return any(issue[0] == rule for issue in expectations()["files"].get(name, {}).get("issues", []))


def actual(report: ValidationReport) -> set[IssueKey]:
    """(rule, severity, subject) issues of a report, normalized like the expectations."""
    result: set[IssueKey] = set()
    for issue in report.issues:
        subject = issue.subject or ""
        if subject.startswith("_:"):
            subject = "_:"
        result.add((issue.rule, issue.severity.value, subject))
    return result


def is_parse_error(name: str) -> bool:
    """Whether the file's RDF is expected to be unreadable."""
    return any(rule == "<parse-error>" for rule, *_ in expectations()["files"][name]["issues"])


def suite_path(name: str) -> Path:
    """Filesystem path of a suite-relative file name."""
    return sboltestsuite.suite_root() / name
