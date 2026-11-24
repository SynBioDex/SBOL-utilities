"""Vocabulary and triple plumbing shared by the upgrade and downgrade engines.

The engines work on plain tuples: an IRI is a Python ``str``, a blank node an ``rdflib.BNode``, a literal an
``rdflib.Literal``. (rdflib's ``URIRef`` never compares equal to a ``str``, so IRIs are unwrapped on the way in and
wrapped again on the way out.)
"""

from __future__ import annotations

from typing import Iterable, List, Tuple, Union

import rdflib
from rdflib import BNode, Literal, URIRef

from sbol_utilities.vocab import BACKPORT, OM, PROV, SBOL2, SBOL3, XSD_NS


class _Namespace:
    """Attribute access to the plain-string IRIs of one namespace: ``S3.hasFeature``."""

    def __init__(self, base: str):
        self.base = base

    def __getattr__(self, name: str) -> str:
        return self.base + name


S2 = _Namespace(str(SBOL2))
S3 = _Namespace(str(SBOL3))
BP = _Namespace(str(BACKPORT))
PROV_NS = str(PROV)
OM_NS = str(OM)

RDF_TYPE = str(rdflib.RDF.type)
DCTERMS_TITLE = "http://purl.org/dc/terms/title"
DCTERMS_DESCRIPTION = "http://purl.org/dc/terms/description"
XSD_STRING = XSD_NS + "string"
XSD_BOOLEAN = XSD_NS + "boolean"

PROV_ACTIVITY = PROV_NS + "Activity"
PROV_AGENT = PROV_NS + "Agent"
PROV_PLAN = PROV_NS + "Plan"

#: SBO "functional entity": the type the upgrade gives every ModuleDefinition-derived Component
SBO_FUNCTIONAL_ENTITY = "https://identifiers.org/SBO:0000241"
EDAM_IUPAC_DNA_RNA = "https://identifiers.org/edam:format_1207"
EDAM_IUPAC_PROTEIN = "https://identifiers.org/edam:format_1208"

Node = Union[str, BNode]
Term = Union[str, BNode, Literal]
Triple = Tuple[Node, str, Term]


def is_iri(term: object) -> bool:
    """Whether an engine term is an IRI (a plain ``str``, not a blank node or literal)."""
    return type(term) is str


def plain(value: str) -> Literal:
    """A simple (``xsd:string``) literal, spelled the way rdflib parses an untyped literal."""
    return Literal(value)


def _unwrap(term) -> Term:
    if isinstance(term, URIRef):
        return str(term)
    if isinstance(term, Literal) and term.datatype is not None and str(term.datatype) == XSD_STRING:
        return Literal(str(term))
    return term


def graph_triples(graph: rdflib.Graph) -> List[Triple]:
    """The graph's triples as engine tuples, in a stable (sorted) order.

    ``xsd:string`` literals become simple literals: RDF 1.1 treats the two as the same term, and sbol-rs never
    distinguishes them.
    """
    triples = [(_unwrap(s), str(p), _unwrap(o)) for s, p, o in graph]
    triples.sort(key=_sort_key)
    return triples  # type: ignore[return-value]


def _sort_key(triple) -> tuple:
    return tuple((type(t).__name__, str(t), _literal_tag(t)) for t in triple)


def _literal_tag(term) -> str:
    if isinstance(term, Literal):
        return f"{term.language or ''}^{term.datatype or ''}"
    return ""


def _wrap(term: Term):
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
        graph.add((_wrap(s), URIRef(p), _wrap(o)))
    return graph
