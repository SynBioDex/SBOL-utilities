"""SBOL 2 rule implementations, grouped by specification area. Each module registers with the SBOL 2 REGISTRY.

The always-on structural and whole-document checks run on every document; the compliant-URI, completeness, and
best-practice families run only when their configuration flag is on, as in libSBOLj's SBOLValidate.
"""

from sbol_utilities.validation.sbol2.rules import (  # noqa: F401
    combinatorial,
    completeness,
    component,
    identity,
    measure,
    module,
    ontology_terms,
    provenance,
    sequence,
    structural,
)
