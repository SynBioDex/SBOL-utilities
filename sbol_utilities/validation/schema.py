"""The shape of a data-model schema: classes, the properties they declare, and what those properties may hold.

The SBOL 2 and SBOL 3 validators each describe their data model as a :class:`Schema` built from these types
(``sbol2/spec.py`` and ``sbol3/spec.py``), and their structural rules read it through the same interface.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType

from sbol_utilities.vocab import XSD_NS


class Cardinality(Enum):
    """How many values a property may have."""

    EXACTLY_ONE = ("exactly one value", 1, 1)
    ZERO_OR_ONE = ("zero or one value", 0, 1)
    ONE_OR_MORE = ("one or more values", 1, None)
    ZERO_OR_MORE = ("any number of values", 0, None)

    def __init__(self, description: str, minimum: int, maximum: int | None):
        #: the requirement in words, to complete "must have ..."
        self.description = description
        self.minimum = minimum
        self.maximum = maximum

    def allows(self, count: int) -> bool:
        """Whether a property with this cardinality may have ``count`` values."""
        return count >= self.minimum and (self.maximum is None or count <= self.maximum)


class ValueKind(Enum):
    """The kind of value a property holds."""

    URI = "Uri"
    URL = "Url"
    STRING = "String"
    INTEGER = "Integer"
    LONG = "Long"
    FLOAT = "Float"
    DATE_TIME = "DateTime"

    @property
    def datatype(self) -> str | None:
        """The XSD datatype the data model gives a literal of this kind; None for IRI-valued kinds."""
        return DATATYPES.get(self)


DATATYPES = {
    ValueKind.STRING: XSD_NS + "string",
    ValueKind.INTEGER: XSD_NS + "integer",
    ValueKind.LONG: XSD_NS + "long",
    ValueKind.FLOAT: XSD_NS + "decimal",
    ValueKind.DATE_TIME: XSD_NS + "dateTime",
}


@dataclass(frozen=True)
class Reference:
    """The class of object a reference property points at."""

    #: the referenced object is an instance of this class or of a subclass
    target: str
    #: the referenced object is a child held in the same document, rather than an object that may live elsewhere
    local: bool


@dataclass(frozen=True)
class PropertySpec:
    """One property a class declares."""

    predicate: str
    cardinality: Cardinality
    kind: ValueKind
    reference: Reference | None = None
    #: the catalog rule governing this property, when one rule does
    rule: str | None = None


@dataclass(frozen=True)
class ClassSpec:
    """A class's direct parents and the properties it declares itself."""

    parents: tuple[str, ...]
    properties: tuple[PropertySpec, ...] = ()


class Schema:
    """The classes of one data model, with the inheritance-derived views the validators query."""

    def __init__(self, classes: Mapping[str, ClassSpec], top_level: str):
        """
        :param classes: every class of the model, by IRI
        :param top_level: IRI of the class whose instances are top-level objects
        """
        self.classes: Mapping[str, ClassSpec] = MappingProxyType(dict(classes))
        self.ancestors_by_class: dict[str, frozenset[str]] = {}
        for class_iri in self.classes:
            self.add_ancestors(class_iri)
        self.properties_by_types: dict[tuple[str, ...], Mapping[str, PropertySpec]] = {}
        #: every predicate some class declares
        self.predicates: frozenset[str] = frozenset(p.predicate for c in classes.values() for p in c.properties)
        #: every class whose instances are top-level objects
        self.top_level_classes: frozenset[str] = frozenset(
            c for c in classes if top_level in self.ancestors_by_class[c]
        )

    def add_ancestors(self, class_iri: str) -> frozenset[str]:
        """Compute and record ``class_iri``'s ancestors, and those of every class it inherits from."""
        known = self.ancestors_by_class.get(class_iri)
        if known is None:
            parents = self.classes[class_iri].parents
            known = frozenset({class_iri}).union(*(self.add_ancestors(parent) for parent in parents))
            self.ancestors_by_class[class_iri] = known
        return known

    def __contains__(self, class_iri: object) -> bool:
        return class_iri in self.classes

    def ancestors(self, class_iri: str) -> frozenset[str]:
        """``class_iri`` and every class it inherits from; empty for an IRI that is not a class of the model."""
        return self.ancestors_by_class.get(class_iri, frozenset())

    def is_a(self, class_iri: str, target: str) -> bool:
        """Whether ``class_iri`` is ``target`` or one of its subclasses."""
        return target in self.ancestors(class_iri)

    def properties_for(self, rdf_types: Iterable[str]) -> Mapping[str, PropertySpec]:
        """The properties an object with these rdf:types may carry, by predicate, in predicate order.

        A class's own declaration of a predicate replaces an inherited one, and when several of the types declare
        the same predicate the declaration of the type that sorts last applies.
        """
        key = tuple(sorted(rdf_types))
        found = self.properties_by_types.get(key)
        if found is None:
            collected: dict[str, PropertySpec] = {}
            for rdf_type in key:
                self.collect(rdf_type, collected)
            found = self.properties_by_types[key] = MappingProxyType(dict(sorted(collected.items())))
        return found

    def collect(self, class_iri: str, into: dict[str, PropertySpec]) -> None:
        """Add the properties ``class_iri`` inherits and declares to ``into``, nearest declaration last."""
        spec = self.classes.get(class_iri)
        if spec is None:
            return
        for parent in spec.parents:
            self.collect(parent, into)
        for declared in spec.properties:
            into[declared.predicate] = declared

    def rules(self) -> list[str]:
        """Every catalog rule a property of the model carries, sorted."""
        return sorted({p.rule for c in self.classes.values() for p in c.properties if p.rule is not None})

    def literal_datatypes(self) -> dict[str, str]:
        """Predicate -> the XSD datatype the model gives that property's literals."""
        return {
            p.predicate: p.kind.datatype
            for c in self.classes.values()
            for p in c.properties
            if p.kind.datatype is not None
        }
