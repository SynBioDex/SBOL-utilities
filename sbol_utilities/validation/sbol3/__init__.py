"""SBOL 3 validator: every rule implementation for the SBOL 3.1.0 catalog, run against one graph.

Importing :mod:`sbol_utilities.validation.sbol3.rules` registers the implementations with
:data:`sbol_utilities.validation.sbol3.registry.REGISTRY`. Best-practice rules are on unless the configuration
turns them off.
"""

from __future__ import annotations

import rdflib

from sbol_utilities.validation.config import ValidationConfig
from sbol_utilities.validation.ontology import bundled_ontology
from sbol_utilities.validation.report import ValidationReport
from sbol_utilities.validation.sbol3 import rules  # noqa: F401  (registers rule implementations)
from sbol_utilities.validation.sbol3.context import Sbol3Context
from sbol_utilities.validation.sbol3.registry import REGISTRY


def validate_graph(graph: rdflib.Graph, config: ValidationConfig) -> ValidationReport:
    """Run every SBOL 3 rule implementation against a graph."""
    context = Sbol3Context(graph, config.for_version(3), REGISTRY.catalog, bundled_ontology())
    return REGISTRY.run(context)
