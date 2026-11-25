"""Indexed view of an SBOL 2 graph shared by the rule implementations.

The graph is read once into :class:`Sbol2Object` records: one per subject that carries at least one data-model predicate
(``rdf:type``, an SBOL 2 / PROV / OM predicate, or the mapped Dublin Core and RDFS terms). Literal values of
data-model properties are normalized to the datatype the schema assigns them, so ``sbol:start "10"`` and
``sbol:start 10`` are the same value. Property values keep the order the parser produced them in, which for
rdflib's in-memory store is document order.

Lookups the rules repeat (resolving a URI by identity or persistentIdentity, finding the object that lists a child
under a property) are served from indexes built on first use.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from typing import Union

import rdflib
from rdflib.term import BNode, Literal, URIRef

from sbol_utilities.validation.catalog import Catalog, Context
from sbol_utilities.validation.config import ValidationConfig
from sbol_utilities.validation.datatypes import parse_i64
from sbol_utilities.validation.ontology import Ontology
from sbol_utilities.validation.sbol2 import spec
from sbol_utilities.validation.schema import PropertySpec
from sbol_utilities.vocab import RDF_TYPE, SBOL2_NS, XSD_STRING


@dataclass(frozen=True)
class Sbol2Literal:
    """A literal value: its lexical form and datatype IRI (``None`` for a plain or language-tagged string)."""

    value: str
    datatype: str | None = None
    language: str | None = None


Resource = Union[URIRef, BNode]
Term = Union[URIRef, BNode, Sbol2Literal]


class Sbol2Object:
    """One subject of the document with its properties."""

    __slots__ = (
        "identity",
        "index",
        "rdf_types",
        "properties",
        "classes",
        "is_sbol",
        "is_top_level",
        "display_id",
    )

    def __init__(self, identity: Resource, properties: dict[str, list[Term]], index: int = 0):
        self.identity = identity
        #: position in the document's object order (IRIs sorted, then blank nodes)
        self.index = index
        self.properties = properties
        self.rdf_types: tuple[str, ...] = tuple(
            sorted({str(t) for t in properties.get(RDF_TYPE, ()) if isinstance(t, URIRef)})
        )
        #: every class this object is an instance of, through the class hierarchy
        self.classes: frozenset[str] = frozenset().union(*(spec.SCHEMA.ancestors(t) for t in self.rdf_types))
        self.is_sbol = bool(self.classes)
        self.is_top_level = any(t in spec.SCHEMA.top_level_classes for t in self.rdf_types)
        self.display_id = self.first_literal(spec.DISPLAY_ID)

    def __repr__(self) -> str:
        return f"Sbol2Object({self.identity!s})"

    @property
    def iri(self) -> str | None:
        """The identity as a string when it is an IRI, else None."""
        return str(self.identity) if isinstance(self.identity, URIRef) else None

    @property
    def property_specs(self) -> Mapping[str, PropertySpec]:
        """The properties this object's classes declare, by predicate, in predicate order."""
        return spec.SCHEMA.properties_for(self.rdf_types)

    def has_class(self, *class_iris: str) -> bool:
        """Whether the object is an instance of one of these classes or of a subclass."""
        return not self.classes.isdisjoint(class_iris)

    def has_rdf_type(self, iri: str) -> bool:
        """Whether the object carries exactly this rdf:type."""
        return iri in self.rdf_types

    def values(self, predicate: str) -> list[Term]:
        """Every value of ``predicate``."""
        return self.properties.get(predicate, [])

    def resources(self, predicate: str) -> list[Resource]:
        """IRI and blank-node values of ``predicate``."""
        return [v for v in self.properties.get(predicate, ()) if not isinstance(v, Sbol2Literal)]  # type: ignore[misc]

    def iris(self, predicate: str) -> list[str]:
        """IRI values of ``predicate`` as strings."""
        return [str(v) for v in self.properties.get(predicate, ()) if isinstance(v, URIRef)]

    def first_iri(self, predicate: str) -> str | None:
        """The first non-literal value of ``predicate`` as a string, or None when that value is a blank node."""
        for v in self.properties.get(predicate, ()):
            if isinstance(v, Sbol2Literal):
                continue
            return str(v) if isinstance(v, URIRef) else None
        return None

    def first_literal(self, predicate: str) -> str | None:
        """The lexical form of the first literal value of ``predicate``."""
        for v in self.properties.get(predicate, ()):
            if isinstance(v, Sbol2Literal):
                return v.value
        return None

    def integer(self, predicate: str) -> int | None:
        """The first literal value of ``predicate`` that parses as a 64-bit integer."""
        for v in self.properties.get(predicate, ()):
            if isinstance(v, Sbol2Literal):
                parsed = parse_i64(v.value)
                if parsed is not None:
                    return parsed
        return None


def _term(node: rdflib.term.Node, predicate: str) -> Term:
    """A graph value as the object model holds it.

    A literal of a property the data model declares takes the datatype the model gives that property, whatever
    datatype it was written with; any other literal keeps its own datatype or language, a plain one being a string.
    """
    if isinstance(node, Literal):
        datatype = spec.LITERAL_DATATYPES.get(predicate)
        if datatype is not None:
            return Sbol2Literal(str(node), datatype)
        if node.datatype is not None:
            return Sbol2Literal(str(node), str(node.datatype))
        if node.language:
            return Sbol2Literal(str(node), None, str(node.language))
        return Sbol2Literal(str(node), XSD_STRING)
    return node  # type: ignore[return-value]


def _object_order(node: Resource) -> tuple[int, str]:
    return (0 if isinstance(node, URIRef) else 1, str(node))


def _properties(graph: rdflib.Graph, subject: Resource) -> dict[str, list[Term]]:
    """A subject's distinct values by predicate, each list in the order the graph holds them.

    rdflib keeps a subject's values in document order, which "first value" lookups rely on.
    """
    values: dict[str, dict[Term, None]] = {}
    for p, o in graph.predicate_objects(subject):
        predicate = str(p)
        values.setdefault(predicate, {})[_term(o, predicate)] = None
    return {predicate: list(distinct) for predicate, distinct in values.items()}


class Sbol2Context(Context[Sbol2Object]):
    """Validation context holding the SBOL 2 object model and lookup indexes."""

    def __init__(self, graph: rdflib.Graph, config: ValidationConfig, catalog: Catalog, ontology: Ontology):
        super().__init__(graph, config, catalog, ontology)
        # subjects are visited in a fixed order, as whole-graph iteration order varies with the process hash seed
        properties = {s: _properties(graph, s) for s in sorted(set(graph.subjects()), key=_object_order)}
        self.triple_count = len(graph)
        #: every object of the document, IRIs before blank nodes, each group sorted
        self.objects: list[Sbol2Object] = []
        self.by_identity: dict[Resource, Sbol2Object] = {}
        for subject, props in properties.items():
            if not _is_model_relevant(props):
                continue
            obj = Sbol2Object(subject, props, len(self.objects))
            self.objects.append(obj)
            self.by_identity[subject] = obj
        #: objects whose rdf:types include an SBOL 2, PROV, or OM schema class
        self.sbol_objects: list[Sbol2Object] = [o for o in self.objects if o.is_sbol]
        self._index_instances(self.objects)
        self._resolve_index: dict[str, Sbol2Object] | None = None
        self._parents: dict[str, dict[str, list[Sbol2Object]]] = {}
        #: whether any triple has an SBOL 2 predicate or an SBOL 2 rdf:type
        self.uses_sbol2_namespace: bool = any(
            p.startswith(SBOL2_NS) or (p == RDF_TYPE and _sbol2_type(props))
            for props in properties.values()
            for p in props
        )

    # --- lookups -------------------------------------------------------------------------------------------------

    def get(self, node: Resource | str | None) -> Sbol2Object | None:
        """The object whose identity is exactly ``node`` (an rdflib node or IRI string)."""
        if node is None or isinstance(node, Sbol2Literal):
            return None
        if isinstance(node, str) and not isinstance(node, (URIRef, BNode)):
            node = URIRef(node)
        return self.by_identity.get(node)

    def resolve(self, uri: str | None) -> Sbol2Object | None:
        """The first object whose identity or persistentIdentity is ``uri``."""
        if uri is None:
            return None
        if self._resolve_index is None:
            index: dict[str, Sbol2Object] = {}
            for obj in self.objects:
                for key in (obj.iri, obj.first_iri(spec.PERSISTENT_IDENTITY)):
                    if key is not None and key not in index:
                        index[key] = obj
            self._resolve_index = index
        return self._resolve_index.get(uri)

    def resolved(self, obj: Sbol2Object, predicate: str) -> Iterator[tuple[str, Sbol2Object]]:
        """Each IRI value of ``obj``'s ``predicate`` that resolves in the document, with the object it names."""
        for iri in obj.iris(predicate):
            target = self.resolve(iri)
            if target is not None:
                yield iri, target

    def parents(self, child: Sbol2Object | str | None, predicate: str) -> list[Sbol2Object]:
        """Every object whose ``predicate`` property lists ``child`` (an object or its IRI), in object order."""
        iri = child.iri if isinstance(child, Sbol2Object) else child
        if iri is None:
            return []
        index = self._parents.get(predicate)
        if index is None:
            index = {}
            for obj in self.objects:
                for v in obj.properties.get(predicate, ()):
                    if isinstance(v, URIRef):
                        holders = index.setdefault(str(v), [])
                        if not holders or holders[-1] is not obj:
                            holders.append(obj)
            self._parents[predicate] = index
        return index.get(iri, [])

    def parent(self, child: Sbol2Object | str | None, predicate: str) -> Sbol2Object | None:
        """The first object whose ``predicate`` property lists ``child`` (an object or its IRI)."""
        holders = self.parents(child, predicate)
        return holders[0] if holders else None

    def referenced(self, obj: Sbol2Object, predicate: str) -> Iterator[Sbol2Object]:
        """The objects in the document that ``obj``'s ``predicate`` values name."""
        for ref in obj.resources(predicate):
            target = self.by_identity.get(ref)
            if target is not None:
                yield target


def _sbol2_type(props: dict[str, list[Term]]) -> bool:
    return any(isinstance(t, URIRef) and str(t).startswith(SBOL2_NS) for t in props.get(RDF_TYPE, ()))


def _is_model_relevant(props: dict[str, list[Term]]) -> bool:
    if any(not spec.is_extension_predicate(p) for p in props):
        return True
    return any(isinstance(t, URIRef) and str(t) in spec.SCHEMA for t in props.get(RDF_TYPE, ()))
