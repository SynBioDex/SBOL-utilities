"""SBOL 3 validator: the rule implementations for the SBOL 3 catalog.

Importing :mod:`sbol_utilities.validation.sbol3.rules` registers every implementation with :data:`REGISTRY`. The
validator mirrors the sbol-rs SBOL 3 validator with its command-line defaults: best-practice rules on, conservative
topology completeness, and external resolution off.
"""

from __future__ import annotations

from typing import Callable

import rdflib

from sbol_utilities.validation.catalog import Registry
from sbol_utilities.validation.config import ValidationConfig
from sbol_utilities.validation.ontology import bundled_ontology
from sbol_utilities.validation.report import ValidationReport
from sbol_utilities.validation.sbol3.context import SBOL3Context

SBOL3RuleFunction = Callable[[SBOL3Context], None]


class SBOL3Registry(Registry):
    """Registry whose rule functions receive an :class:`SBOL3Context`."""

    def rule(self, *rule_ids: str) -> Callable[[SBOL3RuleFunction], SBOL3RuleFunction]:  # type: ignore[override]
        """Decorator registering a function as the implementation of one or more SBOL 3 catalog rules."""
        return super().rule(*rule_ids)  # type: ignore[return-value]


REGISTRY = SBOL3Registry(3)

from sbol_utilities.validation.sbol3 import rules  # noqa: E402,F401  (registers rule implementations)


def validate_graph(graph: rdflib.Graph, config: ValidationConfig) -> ValidationReport:
    """Run every SBOL 3 rule implementation against a graph."""
    context = SBOL3Context(graph, config.for_version(3), REGISTRY.catalog, bundled_ontology())
    return REGISTRY.run(context)
