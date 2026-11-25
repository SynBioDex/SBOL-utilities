"""Validation configuration shared by the SBOL 2 and SBOL 3 validators."""

from __future__ import annotations

from dataclasses import dataclass, field, replace

SUPPRESS = "suppress"
ERROR = "Error"
WARNING = "Warning"


@dataclass
class ValidationConfig:
    """Which rule families run and how their severities are adjusted.

    The gates mirror the rule catalog's ``gate`` field: a rule with gate ``Complete`` runs only when ``complete`` is
    set, ``Compliant`` only when ``compliant`` is set, and ``BestPractice`` only when ``best_practice`` is set.
    Ungated rules always run.
    """

    #: every referenced object must be present in the document
    complete: bool = True
    #: compliant-URI structural rules
    compliant: bool = True
    #: SHOULD-level best-practice rules, emitted as warnings; ``None`` means the version default (on for SBOL 3,
    #: off for SBOL 2)
    best_practice: bool | None = None
    #: compliant URIs may carry an optional type segment (SBOL 2 only)
    types_in_uri: bool = False
    #: per-rule overrides: rule id -> "suppress", "Error", or "Warning"
    rule_overrides: dict[str, str] = field(default_factory=dict)
    #: clamp every emitted severity to at least this level ("Warning" or "Error")
    severity_floor: str | None = None
    #: clamp every emitted severity to at most this level ("Warning" or "Error")
    severity_ceiling: str | None = None

    @classmethod
    def all_on(cls) -> ValidationConfig:
        """Config with every rule family enabled."""
        return cls(complete=True, compliant=True, best_practice=True)

    def for_version(self, version: int) -> ValidationConfig:
        """A copy with version-dependent defaults filled in."""
        if self.best_practice is not None:
            return self
        return replace(self, best_practice=(version == 3))

    def gate_enabled(self, gate: str | None) -> bool:
        """Return whether a catalog gate is switched on under this configuration."""
        if gate is None:
            return True
        return {"Complete": self.complete, "Compliant": self.compliant, "BestPractice": bool(self.best_practice)}[gate]

    def effective_severity(self, rule_id: str, severity: str) -> str | None:
        """Apply overrides, floor, and ceiling; ``None`` means the issue is suppressed."""
        override = self.rule_overrides.get(rule_id)
        if override == SUPPRESS:
            return None
        if override in (ERROR, WARNING):
            severity = override
        if self.severity_floor == ERROR:
            severity = ERROR
        if self.severity_ceiling == WARNING:
            severity = WARNING
        return severity
