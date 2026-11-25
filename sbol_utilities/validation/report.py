"""Validation results: issues, per-rule coverage, and JSON output.

The JSON form follows the sbol-rs validation report schema v1 (``docs/validation-output.md`` in sbol-rs) so reports
from either implementation can be compared directly.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from sbol_utilities.validation.config import ERROR, WARNING, ValidationConfig

SCHEMA_URL = "https://sbolstandard.org/sbol-rs/validation-report/v1.json"


@dataclass(frozen=True)
class Issue:
    """One diagnostic: a rule violation found on a subject."""

    severity: str
    rule: str
    subject: str | None
    message: str
    property: str | None = None
    hint: str | None = None

    def __str__(self) -> str:
        where = self.subject or "<document>"
        if self.property:
            where = f"{where} [{self.property}]"
        return f"{self.severity} {self.rule}: {where}: {self.message}"

    def to_dict(self) -> dict[str, Any]:
        """JSON-ready form of this issue."""
        return {
            "severity": self.severity,
            "rule": self.rule,
            "subject": self.subject,
            "property": self.property,
            "message": self.message,
            "hint": self.hint,
        }


@dataclass
class Coverage:
    """Which catalog rules were evaluated against the document, and how completely."""

    fully_applied: list[str] = field(default_factory=list)
    #: entries carry ``rule``, ``blocker``, and ``coverage_kind``
    partially_applied: list[dict[str, str]] = field(default_factory=list)
    #: entries carry ``rule`` and ``reason``
    not_applied: list[dict[str, str]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """JSON-ready form of the coverage partition."""
        return {
            "fully_applied": sorted(self.fully_applied),
            "partially_applied": sorted(self.partially_applied, key=lambda e: e["rule"]),
            "not_applied": sorted(self.not_applied, key=lambda e: e["rule"]),
        }


@dataclass
class ValidationReport:
    """The outcome of validating one document."""

    spec_version: str
    config: ValidationConfig
    issues: list[Issue] = field(default_factory=list)
    coverage: Coverage = field(default_factory=Coverage)

    @property
    def errors(self) -> list[Issue]:
        """Issues at Error severity."""
        return [i for i in self.issues if i.severity == ERROR]

    @property
    def warnings(self) -> list[Issue]:
        """Issues at Warning severity."""
        return [i for i in self.issues if i.severity == WARNING]

    @property
    def is_valid(self) -> bool:
        """True when no Error-severity issue was found."""
        return not self.errors

    def __len__(self) -> int:
        return len(self.issues)

    def __iter__(self):
        return iter(self.issues)

    def __bool__(self) -> bool:
        return True

    def __str__(self) -> str:
        if not self.issues:
            return f"Valid SBOL {self.spec_version} document."
        return "\n".join(str(i) for i in self.sorted_issues())

    def sorted_issues(self) -> list[Issue]:
        """Issues in a stable order: rule, subject, property, message."""
        return sorted(self.issues, key=lambda i: (i.rule, i.subject or "", i.property or "", i.message))

    def rule_ids(self) -> list[str]:
        """Sorted distinct rule ids that fired."""
        return sorted({i.rule for i in self.issues})

    def to_dict(self) -> dict[str, Any]:
        """JSON-ready form of the whole report."""
        cfg = self.config
        overridden = [
            {"rule": rule, "override": "Suppress" if value == "suppress" else {"Severity": value}}
            for rule, value in sorted(cfg.rule_overrides.items())
        ]
        return {
            "$schema": SCHEMA_URL,
            "schema_version": 1,
            "spec_version": self.spec_version,
            "applied_options": {
                "complete": cfg.complete,
                "compliant": cfg.compliant,
                "best_practice": cfg.best_practice,
                "types_in_uri": cfg.types_in_uri,
                "severity_floor": cfg.severity_floor,
                "severity_ceiling": cfg.severity_ceiling,
                "overridden_rules": overridden,
            },
            "coverage": self.coverage.to_dict(),
            "issues": [i.to_dict() for i in self.sorted_issues()],
        }

    def to_json(self, indent: int | None = 1) -> str:
        """Serialize the report as JSON."""
        return json.dumps(self.to_dict(), indent=indent)
