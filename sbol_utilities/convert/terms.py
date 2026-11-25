"""Vocabulary and triple plumbing shared by the upgrade and downgrade engines.

The engines work on plain tuples: an IRI is a Python ``str``, a blank node an ``rdflib.BNode``, a literal an
``rdflib.Literal``. (rdflib's ``URIRef`` never compares equal to a ``str``, so IRIs are unwrapped on the way in and
wrapped again on the way out.)
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Union

import rdflib
from rdflib import BNode, Literal, URIRef

from sbol_utilities.vocab import (
    BACKPORT_NS,
    DCTERMS_DESCRIPTION,
    DCTERMS_TITLE,
    OM_NS,
    PROV_NS,
    RDF_TYPE,
    SBOL2_NS,
    SBOL3_NS,
    XSD_BOOLEAN,
    XSD_STRING,
)

__all__ = [
    "BP",
    "DCTERMS_DESCRIPTION",
    "DCTERMS_TITLE",
    "EDAM_IUPAC_DNA_RNA",
    "EDAM_IUPAC_PROTEIN",
    "EXTENSION_MARKERS",
    "OM_NS",
    "OM_TOP_LEVELS",
    "PROV_ACTIVITY",
    "PROV_AGENT",
    "PROV_NS",
    "PROV_PLAN",
    "RDF_TYPE",
    "S2",
    "S3",
    "SBO_FUNCTIONAL_ENTITY",
    "XSD_BOOLEAN",
    "XSD_STRING",
    "Node",
    "Term",
    "Triple",
    "build_graph",
    "graph_triples",
    "is_iri",
    "plain",
]


class Namespace:
    """Attribute access to the plain-string IRIs of one namespace: ``S3.hasFeature``."""

    def __init__(self, base: str):
        self.base = base

    def __getattr__(self, name: str) -> str:
        return self.base + name


S2 = Namespace(SBOL2_NS)
S3 = Namespace(SBOL3_NS)
BP = Namespace(BACKPORT_NS)

PROV_ACTIVITY = PROV_NS + "Activity"
PROV_AGENT = PROV_NS + "Agent"
PROV_PLAN = PROV_NS + "Plan"

#: OM classes whose instances are top-level objects (SBOL 3.1.0 Appendix A.2); om:Measure is a child object
OM_TOP_LEVELS = frozenset(
    OM_NS + name
    for name in (
        "Unit SingularUnit CompoundUnit UnitMultiplication UnitDivision UnitExponentiation PrefixedUnit Prefix "
        "SIPrefix BinaryPrefix"
    ).split()
)

#: SBOL 3 types that place an object of another vocabulary's class in the SBOL data model (SBOL 3.1.0 §6.11)
EXTENSION_MARKERS = frozenset({S3.TopLevel, S3.Identified})

#: SBO "functional entity": the type the upgrade gives every ModuleDefinition-derived Component
SBO_FUNCTIONAL_ENTITY = "https://identifiers.org/SBO:0000241"
EDAM_IUPAC_DNA_RNA = "https://identifiers.org/edam:format_1207"
EDAM_IUPAC_PROTEIN = "https://identifiers.org/edam:format_1208"

Node = Union[str, BNode]
Term = Union[str, BNode, Literal]
Triple = tuple[Node, str, Term]


def is_iri(term: object) -> bool:
    """Whether an engine term is an IRI (a plain ``str``, not a blank node or literal)."""
    return type(term) is str


def plain(value: str) -> Literal:
    """A simple (``xsd:string``) literal, spelled the way rdflib parses an untyped literal."""
    return Literal(value)


def from_rdflib(term) -> Term:
    """An rdflib node as an engine term: an IRI as ``str``, an ``xsd:string`` literal as a plain one."""
    if isinstance(term, URIRef):
        return str(term)
    if isinstance(term, Literal) and term.datatype is not None and str(term.datatype) == XSD_STRING:
        return Literal(str(term))
    return term


def graph_triples(graph: rdflib.Graph) -> list[Triple]:
    """The graph's triples as engine tuples, in a stable (sorted) order.

    ``xsd:string`` literals become simple literals: RDF 1.1 treats the two as the same term.
    """
    triples = [(from_rdflib(s), str(p), from_rdflib(o)) for s, p, o in graph]
    triples.sort(key=sort_key)
    return triples  # type: ignore[return-value]


def sort_key(triple) -> tuple:
    """A total order over triples whose terms are IRIs, blank nodes, and literals."""
    return tuple((type(t).__name__, str(t), literal_tag(t)) for t in triple)


def literal_tag(term) -> str:
    """A literal's language and datatype as one string; empty for any other term."""
    if isinstance(term, Literal):
        return f"{term.language or ''}^{term.datatype or ''}"
    return ""


def to_rdflib(term: Term):
    """An engine term as an rdflib node, with literals built the way a parser reads them."""
    if type(term) is str:
        return URIRef(term)
    if isinstance(term, Literal):
        # rebuild typed literals the way a parser would read them, so lexical forms are normalized identically
        if term.language:
            return Literal(str(term), lang=term.language)
        if term.datatype is None or str(term.datatype) == XSD_STRING:
            return Literal(str(term))
        return Literal(str(term), datatype=term.datatype)
    return term


def build_graph(triples: Iterable[Triple]) -> rdflib.Graph:
    """An rdflib Graph holding the engine's output triples."""
    graph = rdflib.Graph()
    for s, p, o in triples:
        graph.add((to_rdflib(s), URIRef(p), to_rdflib(o)))
    return graph
