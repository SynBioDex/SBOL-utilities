"""Pure-Python validation of SBOL 2.3.0 and SBOL 3.1.0 documents.

Every machine-checkable rule of each specification's validation-rule catalog has an implementation here. Rules are
evaluated offline against the document's triples: rules that need other documents or the web run their local subset
and are reported as partially applied in the report's coverage.

    >>> from sbol_utilities.validation import validate
    >>> report = validate("design.ttl")
    >>> report.is_valid, report.errors
"""

from __future__ import annotations

from sbol_utilities.rdf_io import GraphSource, detect_sbol_version, load_graph
from sbol_utilities.validation import sbol2 as _sbol2
from sbol_utilities.validation import sbol3 as _sbol3
from sbol_utilities.validation.catalog import Catalog, RuleSpec, load_catalog
from sbol_utilities.validation.config import Gate, Severity, ValidationConfig
from sbol_utilities.validation.report import Coverage, Issue, ValidationReport

__all__ = [
    "validate",
    "validate_sbol2",
    "validate_sbol3",
    "ValidationConfig",
    "Severity",
    "Gate",
    "ValidationReport",
    "Issue",
    "Coverage",
    "Catalog",
    "RuleSpec",
    "load_catalog",
]


def validate_sbol3(
    source: GraphSource, config: ValidationConfig | None = None, fmt: str | None = None
) -> ValidationReport:
    """Validate a document against the SBOL 3.1.0 rule catalog.

    :param source: an rdflib Graph, path, RDF text, or sbol3.Document
    :param config: rule gates and severity overrides; defaults to :class:`ValidationConfig()`
    :param fmt: RDF format of a path or text source, when it can't be inferred
    """
    return _sbol3.validate_graph(load_graph(source, fmt), config or ValidationConfig())


def validate_sbol2(
    source: GraphSource, config: ValidationConfig | None = None, fmt: str | None = None
) -> ValidationReport:
    """Validate a document against the SBOL 2.3.0 rule catalog.

    :param source: an rdflib Graph, path, RDF text, or sbol2.Document
    :param config: rule gates and severity overrides; defaults to :class:`ValidationConfig()`
    :param fmt: RDF format of a path or text source, when it can't be inferred
    """
    return _sbol2.validate_graph(load_graph(source, fmt), config or ValidationConfig())


def validate(
    source: GraphSource,
    version: int | None = None,
    config: ValidationConfig | None = None,
    fmt: str | None = None,
) -> ValidationReport:
    """Validate an SBOL 2 or SBOL 3 document.

    :param source: an rdflib Graph, path, RDF text, sbol2.Document, or sbol3.Document
    :param version: 2 or 3; when omitted, the version is detected from the document's rdf:type namespaces
    :param config: rule gates and severity overrides
    :param fmt: RDF format of a path or text source, when it can't be inferred
    :raises ValueError: when ``version`` is neither 2 nor 3, or is omitted and cannot be detected
    """
    graph = load_graph(source, fmt)
    if version is None:
        version = detect_sbol_version(graph)
        if version is None:
            raise ValueError("Cannot detect the SBOL version: the document types no subject in an SBOL namespace")
    validators = {2: validate_sbol2, 3: validate_sbol3}
    if version not in validators:
        raise ValueError(f"Unknown SBOL version {version!r}; expected 2 or 3")
    return validators[version](graph, config)
