"""Rule catalogs and the registry that binds rule ids to their Python implementations.

Each SBOL version has a JSON catalog (published in SynBioDex/SBOLTestSuite's ``Rules/``) listing every rule in the
specification with its status, normative severity, optional gate, and optional coverage limits. Implementations
register against rule ids with :meth:`Registry.rule`; one function may check several related rules.

Statuses:

* ``Error`` / ``Warning`` -- algorithm complete; violations emit at that severity.
* ``Configurable`` -- algorithm complete; MUST rules emit errors, SHOULD rules warnings. A ``coverage_kind`` marks
  rules that can only be checked against references held in the document.
* ``MachineUncheckable`` -- the specification says violations are not to be machine-reported. An implementation may
  still emit warnings for positively decidable cases.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any, Callable, Generic, TypeVar

import rdflib
from rdflib.term import BNode

from sbol_utilities.validation.config import ERROR, WARNING, ValidationConfig
from sbol_utilities.validation.ontology import Ontology
from sbol_utilities.validation.report import Coverage, Issue, ValidationReport
from sbol_utilities.validation.runtime_data import runtime_file

MACHINE_UNCHECKABLE = "MachineUncheckable"


@dataclass(frozen=True)
class RuleSpec:
    """One catalog entry."""

    id: str
    status: str
    normative_severity: str
    spec_section: str
    note: str
    gate: str | None = None
    blocker: str | None = None
    coverage_kind: str | None = None

    @property
    def machine_checkable(self) -> bool:
        """False for rules the specification marks as not to be machine-reported."""
        return self.status != MACHINE_UNCHECKABLE

    @property
    def default_severity(self) -> str:
        """Severity a violation of this rule is emitted at, before configuration overrides."""
        if self.status == ERROR:
            return ERROR
        if self.status in (WARNING, MACHINE_UNCHECKABLE) or self.gate == "BestPractice":
            return WARNING
        return ERROR if self.normative_severity == "MUST" else WARNING


@dataclass(frozen=True)
class Catalog:
    """All rules of one SBOL specification version."""

    spec_version: str
    rules: dict[str, RuleSpec]

    def __getitem__(self, rule_id: str) -> RuleSpec:
        return self.rules[rule_id]

    def __contains__(self, rule_id: object) -> bool:
        return rule_id in self.rules

    def machine_checkable(self) -> list[RuleSpec]:
        """Rules whose violations are to be machine-reported."""
        return [r for r in self.rules.values() if r.machine_checkable]


@lru_cache(maxsize=None)
def load_catalog(version: int) -> Catalog:
    """Load the vendored catalog for SBOL version 2 or 3."""
    raw = json.loads(runtime_file(f"Rules/sbol{version}-rules.json").read_text(encoding="utf-8"))
    rules = {}
    for entry in raw["rule"]:
        rules[entry["id"]] = RuleSpec(
            id=entry["id"],
            status=entry["status"],
            normative_severity=entry["normative_severity"],
            spec_section=entry["spec_section"],
            note=entry["note"],
            gate=entry.get("gate"),
            blocker=entry.get("blocker"),
            coverage_kind=entry.get("coverage_kind"),
        )
    return Catalog(spec_version=raw["meta"]["spec_version"], rules=rules)


class Context:
    """State shared by every rule implementation during one validation run.

    Version-specific validators subclass this to add indexes over the graph. Rule functions report violations with
    :meth:`emit`; the context applies gating, severity defaults, and configuration overrides.
    """

    def __init__(self, graph: rdflib.Graph, config: ValidationConfig, catalog: Catalog, ontology: Ontology):
        self.graph = graph
        self.config = config
        self.catalog = catalog
        self.ontology = ontology
        self.issues: list[Issue] = []
        self._seen: set = set()

    def enabled(self, rule_id: str) -> bool:
        """Whether the rule's gate is on; rule functions may skip expensive work for disabled rules."""
        return self.config.gate_enabled(self.catalog[rule_id].gate)

    def emit(
        self,
        rule_id: str,
        subject: Any,
        message: str,
        property: Any = None,
        hint: str | None = None,
        severity: str | None = None,
    ) -> None:
        """Record a violation of ``rule_id``; duplicate (rule, subject, property, message) records are dropped."""
        spec = self.catalog[rule_id]
        if not self.config.gate_enabled(spec.gate):
            return
        final = self.config.effective_severity(rule_id, severity or spec.default_severity)
        if final is None:
            return
        issue = Issue(
            severity=final,
            rule=rule_id,
            subject=None if subject is None else (subject.n3() if isinstance(subject, BNode) else str(subject)),
            message=message,
            property=None if property is None else str(property),
            hint=hint,
        )
        key = (issue.rule, issue.subject, issue.property, issue.message)
        if key not in self._seen:
            self._seen.add(key)
            self.issues.append(issue)


ContextT = TypeVar("ContextT", bound=Context)


@dataclass
class Registry(Generic[ContextT]):
    """Rule implementations for one SBOL version, in registration order.

    A registry is parameterized by the context class its rule functions receive.
    """

    version: int
    functions: list[tuple[tuple[str, ...], Callable[[ContextT], None]]] = field(default_factory=list)

    @property
    def catalog(self) -> Catalog:
        """The catalog this registry implements."""
        return load_catalog(self.version)

    def rule(self, *rule_ids: str) -> Callable[[Callable[[ContextT], None]], Callable[[ContextT], None]]:
        """Decorator registering a function as the implementation of one or more catalog rules."""
        for rule_id in rule_ids:
            if rule_id not in self.catalog:
                raise KeyError(f"{rule_id} is not in the SBOL {self.version} rule catalog")

        def register(function: Callable[[ContextT], None]) -> Callable[[ContextT], None]:
            self.functions.append((tuple(rule_ids), function))
            return function

        return register

    def implemented(self) -> dict[str, list[str]]:
        """Rule id -> names of the functions implementing it."""
        result: dict[str, list[str]] = {}
        for rule_ids, function in self.functions:
            for rule_id in rule_ids:
                result.setdefault(rule_id, []).append(f"{function.__module__}.{function.__qualname__}")
        return result

    def run(self, context: ContextT) -> ValidationReport:
        """Run every registered function whose rules are enabled, and build the report."""
        for rule_ids, function in self.functions:
            if any(context.enabled(r) for r in rule_ids):
                function(context)
        return ValidationReport(
            spec_version=self.catalog.spec_version,
            config=context.config,
            issues=context.issues,
            coverage=self.coverage(context.config),
        )

    def coverage(self, config: ValidationConfig) -> Coverage:
        """Partition the catalog by how completely each rule was evaluated under ``config``."""
        implemented = self.implemented()
        coverage = Coverage()
        for spec in self.catalog.rules.values():
            if not spec.machine_checkable:
                coverage.not_applied.append({"rule": spec.id, "reason": MACHINE_UNCHECKABLE})
            elif not config.gate_enabled(spec.gate):
                coverage.not_applied.append({"rule": spec.id, "reason": {"GatedOff": spec.gate}})  # type: ignore
            elif spec.id not in implemented:
                coverage.not_applied.append({"rule": spec.id, "reason": "Unimplemented"})
            elif spec.coverage_kind:
                coverage.partially_applied.append(
                    {"rule": spec.id, "blocker": spec.blocker or "", "coverage_kind": spec.coverage_kind}
                )
            else:
                coverage.fully_applied.append(spec.id)
        return coverage


def iter_rule_ids(registries: Iterable[Registry]) -> Iterable[str]:
    """All rule ids implemented across registries."""
    for registry in registries:
        yield from registry.implemented()
