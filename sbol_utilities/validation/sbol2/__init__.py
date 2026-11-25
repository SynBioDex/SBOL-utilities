"""SBOL 2 validator: every rule implementation for the SBOL 2.3.0 catalog, run against one graph.

Importing :mod:`sbol_utilities.validation.sbol2.rules` registers the implementations with
:data:`sbol_utilities.validation.sbol2.registry.REGISTRY`.
"""

from __future__ import annotations

import rdflib

from sbol_utilities.validation.config import ValidationConfig
from sbol_utilities.validation.ontology import bundled_ontology
from sbol_utilities.validation.report import ValidationReport
from sbol_utilities.validation.sbol2 import rules  # noqa: F401  (registers rule implementations)
from sbol_utilities.validation.sbol2.context import Sbol2Context
from sbol_utilities.validation.sbol2.registry import REGISTRY


def validate_graph(graph: rdflib.Graph, config: ValidationConfig) -> ValidationReport:
    """Run every SBOL 2 rule implementation against a graph."""
    context = Sbol2Context(graph, config.for_version(2), REGISTRY.catalog, bundled_ontology())
    return REGISTRY.run(context)
