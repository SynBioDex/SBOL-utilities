"""Queries over one SBOL 3 document that the rules share: what a ComponentReference resolves to, where Features
lie on a Sequence, whether a Constraint's restriction holds, and what a CombinatorialDerivation derives.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum

from rdflib.term import Node, URIRef

from sbol_utilities.validation.sbol3 import spec
from sbol_utilities.validation.sbol3.context import Sbol3Context, Sbol3Object
from sbol_utilities.vocab import RDF_TYPE


class Orientation(Enum):
    """The strand a Feature or Location lies on."""

    INLINE = "inline"
    REVERSE_COMPLEMENT = "reverseComplement"

    @classmethod
    def of(cls, iri: Node | None) -> Orientation | None:
        """The orientation an SBOL or SO orientation IRI names, or None for any other value."""
        return _ORIENTATIONS.get(str(iri)) if iri is not None else None


_ORIENTATIONS = {
    spec.INLINE: Orientation.INLINE,
    spec.SO_INLINE: Orientation.INLINE,
    spec.REVERSE_COMPLEMENT: Orientation.REVERSE_COMPLEMENT,
    spec.SO_REVERSE_COMPLEMENT: Orientation.REVERSE_COMPLEMENT,
}


class Outcome(Enum):
    """What the document says about a Constraint's restriction."""

    SATISFIED = "satisfied"
    CONTRADICTED = "contradicted"
    #: the document does not hold enough to decide
    UNKNOWN = "unknown"
    #: the restriction is not one this relation evaluates
    UNSUPPORTED = "unsupported"


@dataclass(frozen=True)
class Relation:
    """Outcome of evaluating a constraint relation, with the witnessing locations when contradicted."""

    outcome: Outcome
    subject_location: Node | None = None
    object_location: Node | None = None


class TraceError(Enum):
    """Why a ``refersTo`` chain did not reach a Feature."""

    #: a link names an object that is not in the document
    MISSING = "missing"
    #: a ComponentReference has no ``refersTo``
    MISSING_REFERS_TO = "missing_refers_to"
    CYCLE = "cycle"


@dataclass(frozen=True)
class FeatureTrace:
    """Result of following a ``refersTo`` chain: the target and the ComponentReferences passed through."""

    target: Node | None
    path: tuple[Node, ...]
    error: TraceError | None = None


@dataclass(frozen=True)
class FeatureIdentity:
    """What a Feature stands for, for deciding whether two Features are the same thing."""

    #: the Component a SubComponent instantiates, or the definition of an ExternallyDefined
    referent: Node
    #: whether ``referent`` is an external definition rather than an instantiated Component
    external: bool
    #: whether the Feature was reached through a ComponentReference
    through_reference: bool

    def same_as(self, other: FeatureIdentity) -> bool:
        """Whether both Features stand for the same Component or the same external definition."""
        return (self.external, self.referent) == (other.external, other.referent)


@dataclass(frozen=True)
class LinearLocation:
    """A location as a half-open span ``[start, end)`` on a Sequence."""

    identity: Node
    sequence: Node
    start: int
    end: int
    orientation: Orientation | None


#: predicates whose values a derived Feature shares with the template Feature it derives from
FEATURE_EQUIVALENCE_PREDICATES = (
    RDF_TYPE,
    spec.ROLE,
    spec.ORIENTATION,
    spec.TYPE,
    spec.INSTANCE_OF,
    spec.DEFINITION,
    spec.ROLE_INTEGRATION,
)


# --- containment and sequences ---


def component_contains(ctx: Sbol3Context, component: Node | None, predicate: str, child: Node) -> bool:
    """Whether the object ``component`` lists ``child`` under ``predicate``."""
    obj = ctx.get(component)
    return obj is not None and child in obj.resources(predicate)


def component_allows_sequence(ctx: Sbol3Context, component: Node, sequence: Node) -> bool:
    """Whether a Component declares a Sequence directly or through a Feature's EntireSequence location."""
    obj = ctx.get(component)
    if obj is None:
        return False
    if sequence in obj.resources(spec.HAS_SEQUENCE):
        return True
    return any(
        location.has_class(spec.ENTIRE_SEQUENCE) and location.first_resource(spec.HAS_SEQUENCE) == sequence
        for feature in ctx.referenced(obj, spec.HAS_FEATURE)
        for location in ctx.referenced(feature, spec.HAS_LOCATION)
    )


def collection_contains_only_components_or_collections(ctx: Sbol3Context, collection: Node, visited: set[Node]) -> bool:
    """Whether every member of a Collection held in the document, recursively, is a Component or Collection."""
    if collection in visited:
        return True
    visited.add(collection)
    obj = ctx.get(collection)
    if obj is None:
        return True
    for member in ctx.referenced(obj, spec.MEMBER):
        if member.has_class(spec.COMPONENT):
            continue
        if not (
            member.has_class(spec.COLLECTION)
            and collection_contains_only_components_or_collections(ctx, member.identity, visited)
        ):
            return False
    return True


def elements_length(elements: str) -> int:
    """The length of a Sequence's ``elements``, counted in UTF-8 bytes as the reference validator counts it.

    IUPAC and SMILES elements are ASCII, for which this is the number of characters.
    """
    return len(elements.encode("utf-8"))


def sequence_length(ctx: Sbol3Context, sequence: Node | None) -> int | None:
    """The length of the elements of a Sequence held in the document, when it has elements."""
    obj = ctx.get(sequence)
    elements = None if obj is None else obj.first_literal(spec.ELEMENTS)
    return None if elements is None else elements_length(elements)


def location_sequence_length(ctx: Sbol3Context, location: Sbol3Object) -> int | None:
    """The length of the Sequence a Location refers to, when known."""
    return sequence_length(ctx, location.first_resource(spec.HAS_SEQUENCE))


def location_length(ctx: Sbol3Context, location: Node) -> int | None:
    """The number of positions a Location held in the document covers, when known."""
    obj = ctx.get(location)
    if obj is None:
        return None
    if obj.has_class(spec.RANGE):
        start, end = obj.integer(spec.START), obj.integer(spec.END)
        if start is None or end is None or start <= 0 or end < start:
            return None
        return end - start + 1
    if obj.has_class(spec.CUT):
        return 0
    if obj.has_class(spec.ENTIRE_SEQUENCE):
        return location_sequence_length(ctx, obj)
    return None


def sum_location_lengths(ctx: Sbol3Context, locations: list[Node]) -> int | None:
    """The total length of several Locations, or None when any of them is unknown."""
    lengths = [location_length(ctx, location) for location in locations]
    return None if None in lengths else sum(length for length in lengths if length is not None)


# --- ComponentReference chains ---


def parent_by_identity_prefix(ctx: Sbol3Context, obj: Sbol3Object) -> Sbol3Object | None:
    """The object whose identity is this object's IRI with the last path segment removed."""
    if not isinstance(obj.identity, URIRef) or "/" not in obj.identity:
        return None
    return ctx.get(URIRef(obj.identity.rsplit("/", 1)[0]))


def trace_feature(ctx: Sbol3Context, feature: Node) -> FeatureTrace:
    """Follow ComponentReference ``refersTo`` links from ``feature`` to the first object that is not a reference."""
    return ctx.memo(("feature trace", feature), lambda: _trace_feature(ctx, feature))


def _trace_feature(ctx: Sbol3Context, feature: Node) -> FeatureTrace:
    current = feature
    path: list[Node] = []
    visited: set[Node] = set()
    while True:
        if current in visited:
            path.append(current)
            return FeatureTrace(None, tuple(path), TraceError.CYCLE)
        visited.add(current)
        obj = ctx.get(current)
        if obj is None:
            return FeatureTrace(None, tuple(path), TraceError.MISSING)
        if not obj.has_class(spec.COMPONENT_REFERENCE):
            return FeatureTrace(current, tuple(path))
        path.append(current)
        following = obj.first_resource(spec.REFERS_TO)
        if following is None:
            return FeatureTrace(None, tuple(path), TraceError.MISSING_REFERS_TO)
        current = following


def _traced(ctx: Sbol3Context, feature: Node) -> tuple[FeatureTrace, Sbol3Object] | None:
    """The trace of ``feature`` and the object it reaches, when the chain resolves."""
    trace = trace_feature(ctx, feature)
    obj = ctx.get(trace.target) if trace.error is None else None
    return None if obj is None else (trace, obj)


def parent_reference(ctx: Sbol3Context, reference: Sbol3Object) -> Sbol3Object | None:
    """The ComponentReference whose identity prefixes this reference's identity."""
    parent = parent_by_identity_prefix(ctx, reference)
    return parent if parent is not None and parent.has_class(spec.COMPONENT_REFERENCE) else None


def reference_is_child_of(ctx: Sbol3Context, reference: Node, parent: Node) -> bool:
    """Whether ``reference`` is nested under ComponentReference ``parent`` by identity."""
    obj = ctx.get(reference)
    if obj is None:
        return False
    found = parent_reference(ctx, obj)
    return found is not None and found.identity == parent


# --- locations and constraint relations ---


def linear_location(ctx: Sbol3Context, identity: Node) -> LinearLocation | None:
    """The span of a Range, Cut, or EntireSequence held in the document, when its positions are well formed."""
    location = ctx.get(identity)
    if location is None:
        return None
    sequence = location.first_resource(spec.HAS_SEQUENCE)
    if sequence is None:
        return None
    orientation = Orientation.of(location.first_iri(spec.ORIENTATION))
    if location.has_class(spec.RANGE):
        start, end = location.integer(spec.START), location.integer(spec.END)
        if start is None or end is None or start <= 0 or end < start:
            return None
        return LinearLocation(identity, sequence, start - 1, end, orientation)
    if location.has_class(spec.CUT):
        at = location.integer(spec.AT)
        if at is None or at < 0:
            return None
        return LinearLocation(identity, sequence, at, at, orientation)
    if location.has_class(spec.ENTIRE_SEQUENCE):
        length = sequence_length(ctx, sequence)
        return None if length is None else LinearLocation(identity, sequence, 0, length, orientation)
    return None


def locations_for_feature(ctx: Sbol3Context, feature: Node) -> list[LinearLocation]:
    """The spans of the Locations of ``feature``, or of the Feature it refers to when that resolves."""
    trace = trace_feature(ctx, feature)
    obj = ctx.get(trace.target if trace.error is None else feature)
    if obj is None:
        return []
    spans = (linear_location(ctx, location) for location in obj.resources(spec.HAS_LOCATION))
    return [span for span in spans if span is not None]


#: sequential restriction -> whether it holds between a subject span and an object span on the same Sequence
_SEQUENTIAL_RELATIONS: dict[str, Callable[[LinearLocation, LinearLocation], bool]] = {
    spec.PRECEDES: lambda s, o: s.start < o.start,
    spec.STRICTLY_PRECEDES: lambda s, o: s.end < o.start,
    spec.MEETS: lambda s, o: s.end == o.start,
    spec.OVERLAPS: lambda s, o: s.start < o.start < s.end < o.end,
    spec.CONTAINS: lambda s, o: s.start <= o.start and s.end >= o.end,
    spec.STRICTLY_CONTAINS: lambda s, o: s.start < o.start and s.end > o.end,
    spec.EQUALS: lambda s, o: s.start == o.start and s.end == o.end,
    spec.FINISHES: lambda s, o: s.start > o.start and s.end == o.end,
    spec.STARTS: lambda s, o: s.start == o.start and s.end < o.end,
}


def _feature_identity(ctx: Sbol3Context, feature: Node) -> FeatureIdentity | None:
    traced = _traced(ctx, feature)
    if traced is None:
        return None
    trace, obj = traced
    if obj.has_class(spec.SUB_COMPONENT):
        referent, external = obj.first_resource(spec.INSTANCE_OF), False
    elif obj.has_class(spec.EXTERNALLY_DEFINED):
        referent, external = obj.first_resource(spec.DEFINITION), True
    else:
        return None
    return None if referent is None else FeatureIdentity(referent, external, through_reference=bool(trace.path))


def _feature_orientation(ctx: Sbol3Context, feature: Node) -> Orientation | None:
    traced = _traced(ctx, feature)
    return None if traced is None else Orientation.of(traced[1].first_iri(spec.ORIENTATION))


def table8_relation(ctx: Sbol3Context, restriction: str, subject: Node, obj: Node) -> Relation:
    """Evaluate an identity or orientation restriction (Tables 8 and 9) between two Features."""
    if restriction in (spec.VERIFY_IDENTICAL, spec.DIFFERENT_FROM):
        subject_identity = _feature_identity(ctx, subject)
        object_identity = _feature_identity(ctx, obj)
        if subject_identity is None or object_identity is None:
            return Relation(Outcome.UNKNOWN)
        same = subject_identity.same_as(object_identity)
        if restriction == spec.DIFFERENT_FROM:
            return Relation(Outcome.CONTRADICTED if same else Outcome.SATISFIED)
        if same:
            return Relation(Outcome.SATISFIED)
        # Features reached through a reference may still be unified by a Constraint in another Component
        if subject_identity.through_reference or object_identity.through_reference:
            return Relation(Outcome.UNKNOWN)
        return Relation(Outcome.CONTRADICTED)
    if restriction in (spec.SAME_ORIENTATION_AS, spec.OPPOSITE_ORIENTATION_AS):
        subject_orientation = _feature_orientation(ctx, subject)
        object_orientation = _feature_orientation(ctx, obj)
        if subject_orientation is None or object_orientation is None:
            return Relation(Outcome.UNKNOWN)
        same = subject_orientation is object_orientation
        return Relation(
            Outcome.SATISFIED if (restriction == spec.SAME_ORIENTATION_AS) == same else Outcome.CONTRADICTED
        )
    if restriction == spec.REPLACES:
        return Relation(Outcome.UNKNOWN)
    return Relation(Outcome.UNSUPPORTED)


def table10_relation(ctx: Sbol3Context, restriction: str, subject: Node, obj: Node) -> Relation:
    """Evaluate a sequential restriction (Table 10) between the locations of two Features.

    The restriction is satisfied when it holds for some pair of locations on the same Sequence, contradicted when
    such pairs exist and it holds for none, and unknown when the Features share no Sequence.
    """
    holds = _SEQUENTIAL_RELATIONS.get(restriction)
    if holds is None:
        return Relation(Outcome.UNSUPPORTED)
    comparable: tuple[Node, Node] | None = None
    for s in locations_for_feature(ctx, subject):
        for o in locations_for_feature(ctx, obj):
            if s.sequence != o.sequence:
                continue
            if holds(s, o):
                return Relation(Outcome.SATISFIED)
            if comparable is None:
                comparable = (s.identity, o.identity)
    if comparable is None:
        return Relation(Outcome.UNKNOWN)
    return Relation(Outcome.CONTRADICTED, *comparable)


def type_properties(ctx: Sbol3Context, feature: Node) -> frozenset[str] | None:
    """The ``sbol:type`` IRIs of the object that determines a Feature's type, when resolvable."""
    traced = _traced(ctx, feature)
    if traced is None:
        return None
    trace, obj = traced
    referent: Node | None = None
    if obj.has_class(spec.LOCAL_SUB_COMPONENT, spec.EXTERNALLY_DEFINED):
        referent = trace.target
    elif obj.has_class(spec.SUB_COMPONENT):
        referent = obj.first_resource(spec.INSTANCE_OF)
    referent_obj = ctx.get(referent)
    return None if referent_obj is None else frozenset(str(i) for i in referent_obj.iris(spec.TYPE))


@dataclass
class DerivationContext:
    """A CombinatorialDerivation with its template's features split into static and variable ones."""

    derivation: Node
    template: Node
    template_features: frozenset[Node]
    variables: dict[Node, Node] = field(default_factory=dict)
    static_features: list[Node] = field(default_factory=list)


def derivation_context(ctx: Sbol3Context, derivation: Sbol3Object) -> DerivationContext | None:
    """A derivation with its template's Features split into static and variable ones, when the template is in the
    document."""
    return ctx.memo(("derivation context", derivation.identity), lambda: _derivation_context(ctx, derivation))


def _derivation_context(ctx: Sbol3Context, derivation: Sbol3Object) -> DerivationContext | None:
    template = derivation.first_resource(spec.TEMPLATE)
    template_obj = ctx.get(template)
    if template is None or template_obj is None:
        return None
    template_features = list(dict.fromkeys(template_obj.resources(spec.HAS_FEATURE)))
    variables: dict[Node, Node] = {}
    for variable_feature in ctx.referenced(derivation, spec.HAS_VARIABLE_FEATURE):
        variable = variable_feature.first_resource(spec.VARIABLE)
        if variable is not None:
            variables[variable] = variable_feature.identity
    static = [feature for feature in template_features if feature not in variables]
    return DerivationContext(derivation.identity, template, frozenset(template_features), variables, static)


def _derived_from_index(ctx: Sbol3Context) -> dict[Node, list[Sbol3Object]]:
    """Source -> the objects recording ``prov:wasDerivedFrom`` it, in document order."""

    def build() -> dict[Node, list[Sbol3Object]]:
        index: dict[Node, list[Sbol3Object]] = {}
        for obj in ctx.objects.values():
            for source in dict.fromkeys(obj.resources(spec.PROV_WAS_DERIVED_FROM)):
                index.setdefault(source, []).append(obj)
        return index

    return ctx.memo("derived from index", build)


def derived_objects(ctx: Sbol3Context, source: Node, class_iri: str) -> list[Sbol3Object]:
    """Objects of a class whose ``prov:wasDerivedFrom`` names ``source``, in document order."""
    return [obj for obj in _derived_from_index(ctx).get(source, ()) if obj.has_class(class_iri)]


def features_derived_from(ctx: Sbol3Context, component: Sbol3Object, template_feature: Node) -> list[Sbol3Object]:
    """The Features of a derived Component that derive from a template Feature."""
    return [
        feature
        for feature in ctx.referenced(component, spec.HAS_FEATURE)
        if template_feature in feature.resources(spec.PROV_WAS_DERIVED_FROM)
    ]


def feature_properties_match(derived: Sbol3Object, template: Sbol3Object) -> bool:
    """Whether a derived Feature has the template Feature's values for the properties derivation preserves."""
    return all(set(derived.values(p)) == set(template.values(p)) for p in FEATURE_EQUIVALENCE_PREDICATES)


#: VariableFeature cardinality -> whether it permits a number of derived Features
_CARDINALITY_ALLOWS: dict[str, Callable[[int], bool]] = {
    spec.ONE: lambda count: count == 1,
    spec.ZERO_OR_ONE_VALUE: lambda count: count <= 1,
    spec.ONE_OR_MORE_VALUE: lambda count: count >= 1,
}


def cardinality_allows(cardinality: Node | None, count: int) -> bool:
    """Whether a derived Feature count satisfies a VariableFeature cardinality; any other cardinality allows all."""
    allows = _CARDINALITY_ALLOWS.get(str(cardinality))
    return allows is None or allows(count)


def _collect_collection_components(ctx: Sbol3Context, collection: Node, visited: set[Node], out: set[Node]) -> None:
    """Add to ``out`` the Components a Collection holds, directly or through member Collections."""
    if collection in visited:
        return
    visited.add(collection)
    obj = ctx.get(collection)
    if obj is None or not obj.has_class(spec.COLLECTION):
        return
    for member in ctx.referenced(obj, spec.MEMBER):
        if member.has_class(spec.COMPONENT):
            out.add(member.identity)
        elif member.has_class(spec.COLLECTION):
            _collect_collection_components(ctx, member.identity, visited, out)


def allowed_variants(ctx: Sbol3Context, variable_feature: Sbol3Object) -> set[Node]:
    """Components a VariableFeature allows through variant, variantCollection, and variantDerivation."""
    return ctx.memo(("allowed variants", variable_feature.identity), lambda: _allowed_variants(ctx, variable_feature))


def _allowed_variants(ctx: Sbol3Context, variable_feature: Sbol3Object) -> set[Node]:
    allowed = {v.identity for v in ctx.referenced(variable_feature, spec.VARIANT) if v.has_class(spec.COMPONENT)}
    for collection in variable_feature.resources(spec.VARIANT_COLLECTION):
        _collect_collection_components(ctx, collection, set(), allowed)
    for derivation in variable_feature.resources(spec.VARIANT_DERIVATION):
        allowed.update(component.identity for component in derived_objects(ctx, derivation, spec.COMPONENT))
    return allowed
