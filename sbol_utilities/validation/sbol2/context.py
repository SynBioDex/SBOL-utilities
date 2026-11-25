"""Indexed view of an SBOL 2 graph shared by the rule implementations.

The graph is read once into :class:`Obj` records: one per subject that carries at least one data-model predicate
(``rdf:type``, an SBOL 2 / PROV / OM predicate, or the mapped Dublin Core and RDFS terms). Literal values of
data-model properties are normalized to the datatype the schema assigns them, so ``sbol:start "10"`` and
``sbol:start 10`` are the same value. Property values keep the order the parser produced them in, which for
rdflib's in-memory store is document order.

Lookups the rules repeat (resolving a URI by identity or persistentIdentity, finding the object that lists a child
under a property) are served from indexes built on first use.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from typing import Union

import rdflib
from rdflib.term import BNode, Literal, URIRef

from sbol_utilities.validation.catalog import Catalog, Context
from sbol_utilities.validation.config import ValidationConfig
from sbol_utilities.validation.ontology import Ontology
from sbol_utilities.validation.sbol2 import spec
from sbol_utilities.vocab import RDF_TYPE, SBOL2_NS, XSD_STRING


@dataclass(frozen=True)
class Lit:
    """A literal value: its lexical form and datatype IRI (``None`` for a plain or language-tagged string)."""

    value: str
    datatype: str | None = None
    language: str | None = None


Resource = Union[URIRef, BNode]
Term = Union[URIRef, BNode, Lit]


def is_resource(term: Term) -> bool:
    """Whether a value is an IRI or blank node."""
    return isinstance(term, (URIRef, BNode))


class Obj:
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
        "_fields",
    )

    def __init__(self, identity: Resource, properties: dict[str, list[Term]], index: int = 0):
        self.identity = identity
        #: position in the document's object order (IRIs sorted, then blank nodes)
        self.index = index
        self.properties = properties
        self.rdf_types: tuple[str, ...] = tuple(
            sorted({str(t) for t in properties.get(RDF_TYPE, ()) if isinstance(t, URIRef)})
        )
        self.classes: set[str] = set()
        for rdf_type in self.rdf_types:
            self.classes |= spec.ancestors(rdf_type)
        self.is_sbol = any(t in spec.CLASSES for t in self.rdf_types)
        self.is_top_level = any(t in spec.TOP_LEVEL_CLASSES for t in self.rdf_types)
        self.display_id = self.literal(spec.DISPLAY_ID)
        self._fields: dict[str, spec.Field] | None = None

    def __repr__(self) -> str:
        return f"Obj({self.identity!s})"

    @property
    def iri(self) -> str | None:
        """The identity as a string when it is an IRI, else None."""
        return str(self.identity) if isinstance(self.identity, URIRef) else None

    @property
    def fields(self) -> dict[str, spec.Field]:
        """Schema fields of this object's classes, keyed by predicate (sorted)."""
        if self._fields is None:
            self._fields = spec.fields_for_types(self.rdf_types)
        return self._fields

    def has_class(self, class_iri: str) -> bool:
        """Whether one of the object's types is ``class_iri`` or a subclass of it."""
        return class_iri in self.classes

    def has_type(self, class_iri: str) -> bool:
        """Whether the object carries exactly this rdf:type."""
        return class_iri in self.rdf_types

    def values(self, predicate: str) -> list[Term]:
        """Every value of ``predicate``."""
        return self.properties.get(predicate, [])

    def resources(self, predicate: str) -> list[Resource]:
        """IRI and blank-node values of ``predicate``."""
        return [v for v in self.properties.get(predicate, ()) if not isinstance(v, Lit)]  # type: ignore[misc]

    def iris(self, predicate: str) -> list[str]:
        """IRI values of ``predicate`` as strings."""
        return [str(v) for v in self.properties.get(predicate, ()) if isinstance(v, URIRef)]

    def first_ref(self, predicate: str) -> str | None:
        """The first IRI-or-blank value of ``predicate`` as a string when it is an IRI (None for a blank node)."""
        for v in self.properties.get(predicate, ()):
            if isinstance(v, Lit):
                continue
            return str(v) if isinstance(v, URIRef) else None
        return None

    def literal(self, predicate: str) -> str | None:
        """The lexical form of the first literal value of ``predicate``."""
        for v in self.properties.get(predicate, ()):
            if isinstance(v, Lit):
                return v.value
        return None

    def integer(self, predicate: str) -> int | None:
        """The first literal value of ``predicate`` that parses as a 64-bit integer."""
        for v in self.properties.get(predicate, ()):
            if isinstance(v, Lit):
                parsed = parse_i64(v.value)
                if parsed is not None:
                    return parsed
        return None

    def lists(self, predicate: str, target: str) -> bool:
        """Whether ``predicate`` has the IRI ``target`` among its values."""
        return any(isinstance(v, URIRef) and str(v) == target for v in self.properties.get(predicate, ()))


I64_MIN = -(2**63)
I64_MAX = 2**63 - 1


def parse_i64(text: str) -> int | None:
    """Parse a decimal integer with an optional sign, as Rust's ``i64::from_str`` does."""
    body = text[1:] if text[:1] in ("+", "-") else text
    if not body or not body.isascii() or not body.isdigit():
        return None
    value = int(text)
    return value if I64_MIN <= value <= I64_MAX else None


def _term(node: rdflib.term.Node, predicate: str) -> Term:
    if isinstance(node, Literal):
        datatype = spec.LITERAL_DATATYPES.get(predicate)
        if datatype is not None:
            return Lit(str(node), datatype)
        if node.datatype is not None:
            return Lit(str(node), str(node.datatype))
        if node.language:
            return Lit(str(node), None, str(node.language))
        return Lit(str(node), XSD_STRING)
    return node  # type: ignore[return-value]


def _object_order(node: Resource) -> tuple[int, str]:
    return (0 if isinstance(node, URIRef) else 1, str(node))


class Sbol2Context(Context):
    """Validation context holding the SBOL 2 object model and lookup indexes."""

    def __init__(self, graph: rdflib.Graph, config: ValidationConfig, catalog: Catalog, ontology: Ontology):
        super().__init__(graph, config, catalog, ontology)
        properties: dict[Resource, dict[str, list[Term]]] = {}
        seen: set[tuple[Resource, str, Term]] = set()
        # Values are read per subject: rdflib keeps a subject's values in document order, which "first value"
        # lookups rely on, while whole-graph iteration order varies with the process hash seed.
        for s in sorted(set(graph.subjects()), key=_object_order):
            if isinstance(s, Literal):
                continue
            for p, o in graph.predicate_objects(s):
                predicate = str(p)
                term = _term(o, predicate)
                key = (s, predicate, term)
                if key in seen:
                    continue
                seen.add(key)
                properties.setdefault(s, {}).setdefault(predicate, []).append(term)
        self.triple_count = len(graph)
        #: every object of the document, IRIs before blank nodes, each group sorted
        self.objects: list[Obj] = []
        self.by_identity: dict[Resource, Obj] = {}
        for subject in sorted(properties, key=_object_order):
            props = properties[subject]
            if not _is_model_relevant(props):
                continue
            obj = Obj(subject, props, len(self.objects))
            self.objects.append(obj)
            self.by_identity[subject] = obj
        #: objects whose rdf:types include an SBOL 2, PROV, or OM schema class
        self.sbol_objects: list[Obj] = [o for o in self.objects if o.is_sbol]
        self._resolve_index: dict[str, Obj] | None = None
        self._containers: dict[str, dict[str, list[Obj]]] = {}
        self._uses_predicate = any(
            p.startswith(SBOL2_NS) or (p == RDF_TYPE and _sbol2_type(props))
            for props in properties.values()
            for p in props
        )

    # --- lookups -------------------------------------------------------------------------------------------------

    def get(self, node: Resource | str | None) -> Obj | None:
        """The object whose identity is exactly ``node`` (an rdflib node or IRI string)."""
        if node is None or isinstance(node, Lit):
            return None
        if isinstance(node, str) and not isinstance(node, (URIRef, BNode)):
            node = URIRef(node)
        return self.by_identity.get(node)

    def resolve(self, uri: str | None) -> Obj | None:
        """The first object whose identity or persistentIdentity is ``uri``."""
        if uri is None:
            return None
        if self._resolve_index is None:
            index: dict[str, Obj] = {}
            for obj in self.objects:
                for key in (obj.iri, obj.first_ref(spec.PERSISTENT_IDENTITY)):
                    if key is not None and key not in index:
                        index[key] = obj
            self._resolve_index = index
        return self._resolve_index.get(uri)

    def containers(self, child: str | None, predicate: str) -> list[Obj]:
        """Every object whose ``predicate`` property lists the IRI ``child``, in object order."""
        if child is None:
            return []
        index = self._containers.get(predicate)
        if index is None:
            index = {}
            for obj in self.objects:
                for v in obj.properties.get(predicate, ()):
                    if isinstance(v, URIRef):
                        holders = index.setdefault(str(v), [])
                        if not holders or holders[-1] is not obj:
                            holders.append(obj)
            self._containers[predicate] = index
        return index.get(child, [])

    def container(self, child: str | None, predicate: str) -> Obj | None:
        """The first object whose ``predicate`` property lists the IRI ``child``."""
        holders = self.containers(child, predicate)
        return holders[0] if holders else None

    def container_of(self, child: Obj, predicate: str) -> Obj | None:
        """The first object listing ``child``'s identity under ``predicate``."""
        return self.container(child.iri, predicate)

    def children(self, obj: Obj, predicate: str) -> Iterator[Obj]:
        """The in-document objects named by ``obj``'s ``predicate`` values."""
        for ref in obj.resources(predicate):
            child = self.by_identity.get(ref)
            if child is not None:
                yield child

    def uses_sbol2_namespace(self) -> bool:
        """Whether any triple has an SBOL 2 predicate or an SBOL 2 rdf:type."""
        return self._uses_predicate


def _sbol2_type(props: dict[str, list[Term]]) -> bool:
    return any(isinstance(t, URIRef) and str(t).startswith(SBOL2_NS) for t in props.get(RDF_TYPE, ()))


def _is_model_relevant(props: dict[str, list[Term]]) -> bool:
    if any(not spec.is_extension_predicate(p) for p in props):
        return True
    return any(isinstance(t, URIRef) and str(t) in spec.CLASSES for t in props.get(RDF_TYPE, ()))
