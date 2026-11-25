"""Indexed view of an SBOL 3 graph shared by every SBOL 3 rule implementation.

The graph is indexed once: each subject that carries an rdf:type or any SBOL, PROV, or OM predicate becomes an
:class:`SbolObject` (mirroring sbol-rs ``collect_objects``), objects are ordered by identity (IRIs before blank
nodes), and composite parent/child edges are recorded in an ownership index.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

import rdflib
from rdflib.term import BNode, Literal, Node, URIRef

from sbol_utilities.validation.catalog import Catalog, Context, NormativeLevel
from sbol_utilities.validation.config import Severity, ValidationConfig
from sbol_utilities.validation.ontology import Ontology
from sbol_utilities.validation.sbol3 import spec
from sbol_utilities.vocab import OM_NS, PROV_NS, RDF_LANG_STRING, RDF_TYPE, SBOL3_NS, XSD_STRING


def _term_order(node: Node) -> tuple[int, str]:
    if isinstance(node, URIRef):
        return 0, str(node)
    if isinstance(node, BNode):
        return 1, str(node)
    return 2, str(node)


def literal_datatype(literal: Literal) -> str:
    """The RDF 1.1 datatype IRI of a literal: xsd:string for plain literals, rdf:langString for tagged ones."""
    if literal.datatype is not None:
        return str(literal.datatype)
    if literal.language:
        return RDF_LANG_STRING
    return XSD_STRING


def _is_extension_predicate(predicate: str) -> bool:
    return (
        predicate != RDF_TYPE
        and not predicate.startswith(SBOL3_NS)
        and not predicate.startswith(PROV_NS)
        and not predicate.startswith(OM_NS)
    )


class SbolObject:
    """One subject of the document: its identity, rdf:types, and property values."""

    __slots__ = ("identity", "rdf_types", "properties", "classes", "ancestors", "display_id", "is_top_level")

    def __init__(self, identity: Node, properties: dict[str, list[Node]]):
        self.identity = identity
        self.properties = properties
        self.rdf_types: tuple[str, ...] = tuple(
            sorted(str(t) for t in properties.get(RDF_TYPE, ()) if isinstance(t, URIRef))
        )
        #: recognized SBOL / PROV / OM classes among the rdf:types
        self.classes: tuple[str, ...] = tuple(t for t in self.rdf_types if t in spec.CLASS_SPECS)
        ancestors: set[str] = set()
        for cls in self.classes:
            ancestors |= spec.ANCESTORS[cls]
        #: every class this object is an instance of, through the class hierarchy
        self.ancestors = frozenset(ancestors)
        self.display_id: str | None = self.first_literal_value(spec.DISPLAY_ID)
        self.is_top_level = any(c in spec.TOP_LEVEL_CLASSES for c in self.classes)

    def __repr__(self) -> str:
        return f"SbolObject({self.identity!s})"

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

    def first_literal_value(self, predicate: str) -> str | None:
        """Lexical form of the first literal value of a predicate."""
        for v in self.values(predicate):
            if isinstance(v, Literal):
                return str(v)
        return None

    def has_class(self, class_iri: str) -> bool:
        """Whether the object is an instance of a class or any of its subclasses."""
        return class_iri in self.ancestors

    def has_rdf_type(self, iri: str) -> bool:
        """Whether the object carries exactly this rdf:type."""
        return iri in self.rdf_types

    def derived_from(self) -> list[Node]:
        """The object's prov:wasDerivedFrom resources."""
        return self.resources(spec.PROV_WAS_DERIVED_FROM)


def primary_kind(obj: SbolObject) -> str | None:
    """The single typed class an object is read as (first match in sbol-rs dispatch order)."""
    for cls in spec.TYPED_DISPATCH_ORDER:
        if obj.has_class(cls):
            return cls
    if obj.has_class(spec.IDENTIFIED):
        return spec.IDENTIFIED
    return None


class OwnershipIndex:
    """Composite parent/child edges of the document (``hasFeature``, ``hasLocation``, ...)."""

    def __init__(self, objects: Iterable[SbolObject]):
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


def collect_objects(graph: rdflib.Graph) -> dict[Node, SbolObject]:
    """Index the graph's SBOL-relevant subjects, ordered by identity.

    Property values keep the graph's insertion order (document order for a parsed file), so "first value" lookups
    agree with sbol-rs, which reads values in document order.
    """
    objects: dict[Node, SbolObject] = {}
    for subject in sorted(set(graph.subjects()), key=_term_order):
        properties: dict[str, list[Node]] = {}
        for p, o in graph.predicate_objects(subject):
            properties.setdefault(str(p), []).append(o)
        if any(not _is_extension_predicate(p) for p in properties):
            objects[subject] = SbolObject(subject, properties)
    return objects


class SBOL3Context(Context):
    """Validation state for one SBOL 3 run: the indexed document.

    While the best-practice family is off, every rule whose normative level is SHOULD is silenced.
    """

    def __init__(self, graph: rdflib.Graph, config: ValidationConfig, catalog: Catalog, ontology: Ontology):
        super().__init__(graph, config, catalog, ontology)
        self.objects: dict[Node, SbolObject] = collect_objects(graph)
        self.ownership = OwnershipIndex(self.objects.values())
        self._typed: dict[str, list[SbolObject]] = {}
        self._instances: dict[str, list[SbolObject]] = {}
        for obj in self.objects.values():
            kind = primary_kind(obj)
            if kind is not None:
                self._typed.setdefault(kind, []).append(obj)

    def get(self, identity: Node | None) -> SbolObject | None:
        """The object with this identity, if present in the document."""
        if identity is None:
            return None
        return self.objects.get(identity)

    def typed(self, class_iri: str) -> list[SbolObject]:
        """Objects whose primary typed kind is ``class_iri`` (sbol-rs ``Document::components()`` and friends)."""
        return self._typed.get(class_iri, [])

    def instances(self, class_iri: str) -> list[SbolObject]:
        """Objects that are instances of ``class_iri`` or a subclass."""
        found = self._instances.get(class_iri)
        if found is None:
            found = self._instances[class_iri] = [obj for obj in self.objects.values() if obj.has_class(class_iri)]
        return found

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
