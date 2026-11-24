"""Graph-access helpers shared by the SBOL 2 and SBOL 3 rule implementations."""

from __future__ import annotations

import re
from typing import Iterable, Iterator, List, Optional, Set

import rdflib
from rdflib.term import BNode, Literal, Node, URIRef

from sbol_utilities.vocab import TYPE

#: Characters permitted in a displayId: alphanumerics and underscore, not starting with a digit
DISPLAY_ID_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def objects(graph: rdflib.Graph, subject: Node, predicate: Node) -> List[Node]:
    """All values of ``predicate`` on ``subject``, in a stable order."""
    return sorted(graph.objects(subject, predicate), key=str)


def value(graph: rdflib.Graph, subject: Node, predicate: Node) -> Optional[Node]:
    """One value of ``predicate`` on ``subject`` (the smallest, for determinism), or None."""
    values = objects(graph, subject, predicate)
    return values[0] if values else None


def text(graph: rdflib.Graph, subject: Node, predicate: Node) -> Optional[str]:
    """String form of one value of ``predicate`` on ``subject``, or None."""
    v = value(graph, subject, predicate)
    return None if v is None else str(v)


def types(graph: rdflib.Graph, subject: Node) -> Set[URIRef]:
    """The rdf:type values of ``subject``."""
    return {t for t in graph.objects(subject, TYPE) if isinstance(t, URIRef)}


def subjects_of_type(graph: rdflib.Graph, *classes: Node) -> List[Node]:
    """Subjects typed with any of ``classes``, sorted, without duplicates."""
    found: Set[Node] = set()
    for cls in classes:
        found.update(graph.subjects(TYPE, cls))
    return sorted(found, key=str)


def subjects_in_namespace(graph: rdflib.Graph, namespace: str) -> Iterator[Node]:
    """Subjects with at least one rdf:type in ``namespace``."""
    seen: Set[Node] = set()
    for s, _, o in graph.triples((None, TYPE, None)):
        if s not in seen and str(o).startswith(namespace):
            seen.add(s)
            yield s


def is_iri(node: Optional[Node]) -> bool:
    """Whether a node is an IRI (not a literal or blank node)."""
    return isinstance(node, URIRef)


def is_literal(node: Optional[Node]) -> bool:
    """Whether a node is a literal."""
    return isinstance(node, Literal)


def is_blank(node: Optional[Node]) -> bool:
    """Whether a node is a blank node."""
    return isinstance(node, BNode)


def is_url(iri: str) -> bool:
    """Whether an IRI uses an http(s) scheme with an authority."""
    return bool(re.match(r"^https?://[^/?#]+", iri))


def has_valid_display_id(display_id: str) -> bool:
    """Whether a displayId matches the SBOL pattern (alphanumeric or underscore, not starting with a digit)."""
    return bool(DISPLAY_ID_PATTERN.match(display_id))


def iter_references(graph: rdflib.Graph, predicates: Iterable[Node]) -> Iterator[tuple]:
    """(subject, predicate, object) triples for each listed predicate, in a stable order."""
    for predicate in predicates:
        for s, o in sorted(graph.subject_objects(predicate), key=lambda pair: (str(pair[0]), str(pair[1]))):
            yield s, predicate, o
