"""SBOL 2 validator: the rule implementations for the SBOL 2 catalog.

Importing :mod:`sbol_utilities.validation.sbol2.rules` registers every implementation with :data:`REGISTRY`.
"""

from __future__ import annotations

import rdflib

from sbol_utilities.validation.catalog import Context, Registry
from sbol_utilities.validation.config import ValidationConfig
from sbol_utilities.validation.ontology import bundled_ontology
from sbol_utilities.validation.report import ValidationReport

REGISTRY = Registry(2)

from sbol_utilities.validation.sbol2 import rules  # noqa: E402,F401  (registers rule implementations)


def validate_graph(graph: rdflib.Graph, config: ValidationConfig) -> ValidationReport:
    """Run every SBOL 2 rule implementation against a graph."""
    context = Context(graph, config.for_version(2), REGISTRY.catalog, bundled_ontology())
    return REGISTRY.run(context)
