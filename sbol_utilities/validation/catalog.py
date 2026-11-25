"""Rule catalogs and the registry that binds rule ids to their Python implementations.

Each SBOL version has a JSON catalog (published in SynBioDex/SBOLTestSuite's ``Rules/``) listing every rule in the
specification with its status, normative severity, optional gate, and optional coverage limits. Implementations
register against rule ids with :meth:`Registry.rule`; one function may check several related rules, and may
report only the rules it registered for.

Statuses:

* ``Error`` / ``Warning`` -- algorithm complete; violations emit at that severity.
* ``Configurable`` -- algorithm complete; MUST rules emit errors, SHOULD rules warnings. A ``coverage_kind`` marks
  rules that can only be checked against references held in the document.
* ``MachineUncheckable`` -- the specification says violations are not to be machine-reported in general. An
  implementation may still report the cases it can decide from the document, at the rule's normative level.
"""

from __future__ import annotations

import json
from collections.abc import Hashable, Iterable
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any, Callable, Generic, Protocol, TypeVar

import rdflib
from rdflib.term import BNode

from sbol_utilities.validation.config import Gate, Severity, StrEnum, ValidationConfig
from sbol_utilities.validation.ontology import Ontology
from sbol_utilities.validation.report import (
    Coverage,
    Issue,
    NotApplied,
    NotAppliedReason,
    PartiallyApplied,
    ValidationReport,
)
from sbol_utilities.validation.runtime_data import runtime_file


class Status(StrEnum):
    """How completely a rule can be checked, and at what severity (see the module docstring)."""

    ERROR = "Error"
    WARNING = "Warning"
    CONFIGURABLE = "Configurable"
    MACHINE_UNCHECKABLE = "MachineUncheckable"


class NormativeLevel(StrEnum):
    """The requirement level the specification gives a rule."""

    MUST = "MUST"
    SHOULD = "SHOULD"


@dataclass(frozen=True)
class RuleSpec:
    """One catalog entry."""

    id: str
    status: Status
    normative_severity: NormativeLevel
    spec_section: str
    note: str
    gate: Gate | None = None
    blocker: str | None = None
    coverage_kind: str | None = None

    @classmethod
    def from_entry(cls, entry: dict[str, Any]) -> RuleSpec:
        """The rule described by one entry of a catalog's ``rule`` list."""
        gate = entry.get("gate")
        return cls(
            id=entry["id"],
            status=Status(entry["status"]),
            normative_severity=NormativeLevel(entry["normative_severity"]),
            spec_section=entry["spec_section"],
            note=entry["note"],
            gate=None if gate is None else Gate(gate),
            blocker=entry.get("blocker"),
            coverage_kind=entry.get("coverage_kind"),
        )

    @property
    def machine_checkable(self) -> bool:
        """False for rules the specification marks as not to be machine-reported."""
        return self.status is not Status.MACHINE_UNCHECKABLE

    @property
    def default_severity(self) -> Severity:
        """Severity a violation of this rule is reported at, before configuration overrides.

        An ``Error`` or ``Warning`` status fixes the severity. Otherwise a best-practice rule is a warning, and any
        other rule follows its normative level: MUST is an error, SHOULD a warning.
        """
        if self.status is Status.ERROR:
            return Severity.ERROR
        if self.status is Status.WARNING or self.gate is Gate.BEST_PRACTICE:
            return Severity.WARNING
        return Severity.ERROR if self.normative_severity is NormativeLevel.MUST else Severity.WARNING


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
    rules = {entry["id"]: RuleSpec.from_entry(entry) for entry in raw["rule"]}
    return Catalog(spec_version=raw["meta"]["spec_version"], rules=rules)


class ModelObject(Protocol):
    """What the context needs of a document object: an identity and the classes it is an instance of."""

    identity: Any
    classes: frozenset[str]


ObjectT = TypeVar("ObjectT", bound=ModelObject)
T = TypeVar("T")


class Context(Generic[ObjectT]):
    """State shared by every rule implementation during one validation run.

    Version-specific validators subclass this to read the graph into their object model. Rule functions find
    objects with :meth:`instances` and report violations with :meth:`report`; the context applies gating, the
    rule's catalog severity, and configuration overrides.
    """

    def __init__(self, graph: rdflib.Graph, config: ValidationConfig, catalog: Catalog, ontology: Ontology):
        self.graph = graph
        self.config = config
        self.catalog = catalog
        self.ontology = ontology
        self.issues: list[Issue] = []
        self.indexed: list[ObjectT] = []
        self.instances_by_class: dict[str, list[ObjectT]] = {}
        self.memoized_values: dict[Hashable, Any] = {}
        self.seen: set[tuple[str, str | None, str | None, str]] = set()
        #: rule ids the running rule function declared, or None outside :meth:`Registry.run`
        self.declared_rules: frozenset[str] | None = None

    def index_instances(self, objects: Iterable[ObjectT]) -> None:
        """Record the document's objects, in document order, for :meth:`instances`."""
        self.indexed = list(objects)
        for obj in self.indexed:
            for class_iri in obj.classes:
                self.instances_by_class.setdefault(class_iri, []).append(obj)

    def instances(self, *class_iris: str) -> list[ObjectT]:
        """The objects that are instances of one of these classes or of a subclass, in document order."""
        if len(class_iris) == 1:
            return self.instances_by_class.get(class_iris[0], [])
        return [obj for obj in self.indexed if not obj.classes.isdisjoint(class_iris)]

    def memo(self, key: Hashable, compute: Callable[[], T]) -> T:
        """The value ``compute`` returns, computed once per validation run for each ``key``.

        Rule helpers use this for indexes and derived facts that several rules, or several objects, need.
        """
        if key not in self.memoized_values:
            self.memoized_values[key] = compute()
        return self.memoized_values[key]

    def enabled(self, rule_id: str) -> bool:
        """Whether the rule's gate is on; rule functions may skip expensive work for disabled rules."""
        return self.config.gate_enabled(self.catalog[rule_id].gate)

    def report(
        self,
        rule_id: str,
        subject: Any,
        message: str,
        *,
        property: str | None = None,
        hint: str | None = None,
        severity: Severity | None = None,
    ) -> None:
        """Record a violation of ``rule_id`` on ``subject``.

        :param subject: the offending object (anything with an ``identity``), its identity node, or None for the
            document as a whole
        :param property: the predicate the violation concerns, when there is one
        :param severity: overrides the rule's catalog severity; for the few cases an implementation reports a rule
            at another level than the catalog assigns it

        A rule whose gate is off is not recorded, and neither is a repeat of the same (rule, subject, property,
        message).
        """
        if self.declared_rules is not None and rule_id not in self.declared_rules:
            raise ValueError(f"{rule_id} was reported by a rule function that does not declare it")
        spec = self.catalog[rule_id]
        if not self.config.gate_enabled(spec.gate):
            return
        final = self.config.effective_severity(rule_id, severity or spec.default_severity)
        if final is None:
            return
        identity = getattr(subject, "identity", subject)
        issue = Issue(
            severity=final,
            rule=rule_id,
            subject=None if identity is None else (identity.n3() if isinstance(identity, BNode) else str(identity)),
            message=message,
            property=None if property is None else str(property),
            hint=hint,
        )
        key = (issue.rule, issue.subject, issue.property, issue.message)
        if key not in self.seen:
            self.seen.add(key)
            self.issues.append(issue)


ContextT = TypeVar("ContextT", bound="Context[Any]")


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
            """Record the decorated function as the implementation of the rule ids."""
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
                context.declared_rules = frozenset(rule_ids)
                function(context)
        context.declared_rules = None
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
                coverage.not_applied.append(NotApplied(spec.id, NotAppliedReason.MACHINE_UNCHECKABLE))
            elif not config.gate_enabled(spec.gate):
                coverage.not_applied.append(NotApplied(spec.id, NotAppliedReason.GATED_OFF, spec.gate))
            elif spec.id not in implemented:
                coverage.not_applied.append(NotApplied(spec.id, NotAppliedReason.UNIMPLEMENTED))
            elif spec.coverage_kind:
                coverage.partially_applied.append(PartiallyApplied(spec.id, spec.blocker or "", spec.coverage_kind))
            else:
                coverage.fully_applied.append(spec.id)
        return coverage


def iter_rule_ids(registries: Iterable[Registry]) -> Iterable[str]:
    """All rule ids implemented across registries."""
    for registry in registries:
        yield from registry.implemented()
