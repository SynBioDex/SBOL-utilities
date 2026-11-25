"""Indexed view of an SBOL 3 graph shared by every SBOL 3 rule implementation.

The graph is indexed once: each subject that carries an rdf:type or any SBOL, PROV, or OM predicate becomes an
:class:`Sbol3Object`, objects are ordered by identity (IRIs before blank nodes), and composite parent/child edges
are recorded in an ownership index.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from typing import Any

import rdflib
from rdflib.term import BNode, Literal, Node, URIRef

from sbol_utilities.validation.catalog import Catalog, Context, NormativeLevel
from sbol_utilities.validation.config import Severity, ValidationConfig
from sbol_utilities.validation.datatypes import parse_i64
from sbol_utilities.validation.ontology import Ontology
from sbol_utilities.validation.sbol3 import spec
from sbol_utilities.vocab import OM_NS, PROV_NS, RDF_TYPE, SBOL3_NS


def term_order(node: Node) -> tuple[int, str]:
    """Sort key placing IRIs first, then blank nodes, then literals, each group in string order."""
    if isinstance(node, URIRef):
        return 0, str(node)
    if isinstance(node, BNode):
        return 1, str(node)
    return 2, str(node)


def is_extension_predicate(predicate: str) -> bool:
    """Whether a predicate is outside the SBOL 3, PROV, and OM namespaces and is not rdf:type."""
    return (
        predicate != RDF_TYPE
        and not predicate.startswith(SBOL3_NS)
        and not predicate.startswith(PROV_NS)
        and not predicate.startswith(OM_NS)
    )


class Sbol3Object:
    """One subject of the document: its identity, rdf:types, and property values."""

    __slots__ = ("identity", "rdf_types", "properties", "declared_classes", "classes", "display_id", "is_top_level")

    def __init__(self, identity: Node, properties: dict[str, list[Node]]):
        self.identity = identity
        self.properties = properties
        self.rdf_types: tuple[str, ...] = tuple(
            sorted(str(t) for t in properties.get(RDF_TYPE, ()) if isinstance(t, URIRef))
        )
        #: the rdf:types that are classes of the data model
        self.declared_classes: tuple[str, ...] = tuple(t for t in self.rdf_types if t in spec.SCHEMA)
        #: every class this object is an instance of, through the class hierarchy
        self.classes: frozenset[str] = frozenset().union(*(spec.SCHEMA.ancestors(t) for t in self.declared_classes))
        self.display_id: str | None = self.first_literal(spec.DISPLAY_ID)
        self.is_top_level = any(c in spec.SCHEMA.top_level_classes for c in self.declared_classes)

    def __repr__(self) -> str:
        return f"Sbol3Object({self.identity!s})"

    def values(self, predicate: str) -> list[Node]:
        """All values of a predicate."""
        return self.properties.get(predicate, [])

    def resources(self, predicate: str) -> list[Node]:
        """IRI and blank-node values of a predicate."""
        return [v for v in self.values(predicate) if isinstance(v, (URIRef, BNode))]

    def iris(self, predicate: str) -> list[URIRef]:
        """IRI values of a predicate."""
        return [v for v in self.values(predicate) if isinstance(v, URIRef)]

    def literals(self, predicate: str) -> list[Literal]:
        """Literal values of a predicate."""
        return [v for v in self.values(predicate) if isinstance(v, Literal)]

    def first_resource(self, predicate: str) -> Node | None:
        """First IRI or blank-node value of a predicate."""
        for v in self.values(predicate):
            if isinstance(v, (URIRef, BNode)):
                return v
        return None

    def first_iri(self, predicate: str) -> URIRef | None:
        """First IRI value of a predicate."""
        for v in self.values(predicate):
            if isinstance(v, URIRef):
                return v
        return None

    def first_literal(self, predicate: str) -> str | None:
        """Lexical form of the first literal value of a predicate."""
        for v in self.values(predicate):
            if isinstance(v, Literal):
                return str(v)
        return None

    def integer(self, predicate: str) -> int | None:
        """The first literal value of ``predicate`` as a 64-bit integer, or None when it is not one."""
        return parse_i64(self.first_literal(predicate))

    def has_class(self, *class_iris: str) -> bool:
        """Whether the object is an instance of one of these classes or of a subclass."""
        return not self.classes.isdisjoint(class_iris)

    def has_rdf_type(self, iri: str) -> bool:
        """Whether the object carries exactly this rdf:type."""
        return iri in self.rdf_types


class OwnershipIndex:
    """Composite parent/child edges of the document (``hasFeature``, ``hasLocation``, ...)."""

    def __init__(self, objects: Iterable[Sbol3Object]):
        self.parents_by_child: dict[Node, list[tuple[Node, str]]] = {}
        self.children_by_parent: dict[tuple[Node, str], list[Node]] = {}
        for obj in objects:
            for predicate in spec.COMPOSITE_PREDICATES:
                for child in obj.resources(predicate):
                    self.parents_by_child.setdefault(child, []).append((obj.identity, predicate))
                    self.children_by_parent.setdefault((obj.identity, predicate), []).append(child)

    def parents(self, child: Node, predicate: str) -> list[Node]:
        """Every parent holding ``child`` under ``predicate``."""
        return [parent for parent, p in self.parents_by_child.get(child, ()) if p == predicate]

    def single_parent(self, child: Node, predicate: str) -> Node | None:
        """The first parent holding ``child`` under ``predicate``."""
        parents = self.parents(child, predicate)
        return parents[0] if parents else None

    def children(self, parent: Node, predicate: str) -> list[Node]:
        """Children held by ``parent`` under ``predicate``."""
        return self.children_by_parent.get((parent, predicate), [])

    def contains(self, parent: Node, predicate: str, child: Node) -> bool:
        """Whether ``parent`` holds ``child`` under ``predicate``."""
        return child in self.children(parent, predicate)


def collect_objects(graph: rdflib.Graph) -> dict[Node, Sbol3Object]:
    """Index the graph's SBOL-relevant subjects, ordered by identity.

    Property values keep the graph's insertion order (document order for a parsed file), so a "first value" lookup
    returns the value written first.
    """
    objects: dict[Node, Sbol3Object] = {}
    for subject in sorted(set(graph.subjects()), key=term_order):
        properties: dict[str, list[Node]] = {}
        for p, o in graph.predicate_objects(subject):
            properties.setdefault(str(p), []).append(o)
        if any(not is_extension_predicate(p) for p in properties):
            objects[subject] = Sbol3Object(subject, properties)
    return objects


class Sbol3Context(Context[Sbol3Object]):
    """Validation state for one SBOL 3 run: the indexed document.

    While the best-practice family is off, every rule whose normative level is SHOULD is silenced.
    """

    def __init__(self, graph: rdflib.Graph, config: ValidationConfig, catalog: Catalog, ontology: Ontology):
        super().__init__(graph, config, catalog, ontology)
        self.objects: dict[Node, Sbol3Object] = collect_objects(graph)
        self.ownership = OwnershipIndex(self.objects.values())
        self.index_instances(self.objects.values())

    def get(self, identity: Node | None) -> Sbol3Object | None:
        """The object with this identity, if present in the document."""
        if identity is None:
            return None
        return self.objects.get(identity)

    def referenced(self, obj: Sbol3Object, predicate: str) -> Iterator[Sbol3Object]:
        """The objects in the document that ``obj``'s ``predicate`` values name."""
        for identity in obj.resources(predicate):
            target = self.objects.get(identity)
            if target is not None:
                yield target

    def parent(self, child: Sbol3Object, predicate: str) -> Sbol3Object | None:
        """The first object in the document holding ``child`` under the composite ``predicate``."""
        return self.get(self.ownership.single_parent(child.identity, predicate))

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
        """Record a violation; SHOULD-level rules are dropped while the best-practice family is off."""
        if not self.config.best_practice and self.catalog[rule_id].normative_severity is NormativeLevel.SHOULD:
            return
        super().report(rule_id, subject, message, property=property, hint=hint, severity=severity)
