"""Validation configuration shared by the SBOL 2 and SBOL 3 validators."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from enum import Enum


class StrEnum(str, Enum):
    """An enumeration whose members are, compare as, and print as their string values."""

    def __str__(self) -> str:
        return self.value


class Severity(StrEnum):
    """How serious a reported violation is."""

    ERROR = "Error"
    WARNING = "Warning"


class Gate(StrEnum):
    """A family of rules that a configuration switches on or off together."""

    COMPLETE = "Complete"
    COMPLIANT = "Compliant"
    BEST_PRACTICE = "BestPractice"


#: per-rule override value that silences a rule
SUPPRESS = "suppress"


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
    #: per-rule overrides: rule id -> :data:`SUPPRESS` or a :class:`Severity` (or its string value)
    rule_overrides: dict[str, str] = field(default_factory=dict)
    #: report nothing below this severity: ``Severity.ERROR`` turns every warning into an error
    severity_floor: str | None = None
    #: report nothing above this severity: ``Severity.WARNING`` turns every error into a warning
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
        """Whether a catalog gate is switched on under this configuration; an ungated rule is always on."""
        if gate is None:
            return True
        gate = Gate(gate)
        if gate is Gate.COMPLETE:
            return self.complete
        if gate is Gate.COMPLIANT:
            return self.compliant
        return bool(self.best_practice)

    def effective_severity(self, rule_id: str, severity: str) -> Severity | None:
        """Apply overrides, floor, and ceiling; ``None`` means the issue is suppressed."""
        override = self.rule_overrides.get(rule_id)
        if override == SUPPRESS:
            return None
        result = Severity(severity if override is None else override)
        if self.severity_floor == Severity.ERROR:
            result = Severity.ERROR
        if self.severity_ceiling == Severity.WARNING:
            result = Severity.WARNING
        return result
