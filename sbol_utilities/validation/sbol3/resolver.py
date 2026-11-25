"""Feature-reference, location, constraint, and combinatorial-derivation resolution over a single document.

Mirrors sbol-rs ``crates/sbol3/src/validation/resolver``: ComponentReference ``refersTo`` chains, linear location
spans, the Table 8 / Table 10 constraint relations, and CombinatorialDerivation context.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from rdflib.term import Node, URIRef

from sbol_utilities.validation.sbol3 import spec
from sbol_utilities.validation.sbol3.context import Sbol3Context, Sbol3Object
from sbol_utilities.vocab import RDF_TYPE

INLINE = "inline"
REVERSE_COMPLEMENT = "reverseComplement"

SATISFIED = "satisfied"
CONTRADICTED = "contradicted"
UNKNOWN = "unknown"
UNSUPPORTED = "unsupported"

FEATURE_EQUIVALENCE_PREDICATES = (
    RDF_TYPE,
    spec.ROLE,
    spec.ORIENTATION,
    spec.TYPE,
    spec.INSTANCE_OF,
    spec.DEFINITION,
    spec.ROLE_INTEGRATION,
)


@dataclass(frozen=True)
class Relation:
    """Outcome of evaluating a constraint relation, with the witnessing locations when contradicted."""

    outcome: str
    subject_location: Node | None = None
    object_location: Node | None = None


@dataclass(frozen=True)
class FeatureTrace:
    """Result of following a ``refersTo`` chain: the target and the ComponentReferences passed through."""

    target: Node | None
    path: tuple[Node, ...]
    #: "missing", "missing_refers_to", or "cycle" when the chain could not be resolved
    error: str | None = None


@dataclass(frozen=True)
class LinearLocation:
    """A location as a half-open span ``[start, end)`` on a Sequence."""

    identity: Node
    sequence: Node
    start: int
    end: int
    orientation: str | None


def directional_orientation(value: Node | None) -> str | None:
    """Normalize SBOL and SO orientation IRIs to inline / reverseComplement."""
    if value is None:
        return None
    text = str(value)
    if text in (spec.INLINE, spec.SO_INLINE):
        return INLINE
    if text in (spec.REVERSE_COMPLEMENT, spec.SO_REVERSE_COMPLEMENT):
        return REVERSE_COMPLEMENT
    return None


def parent_by_identity_prefix(ctx: Sbol3Context, obj: Sbol3Object) -> Sbol3Object | None:
    """The object whose identity is this object's identity with the last path segment removed."""
    identity = str(obj.identity) if isinstance(obj.identity, URIRef) else "_:" + str(obj.identity)
    if "/" not in identity:
        return None
    return ctx.get(URIRef(identity.rsplit("/", 1)[0]))


def trace_feature(ctx: Sbol3Context, feature: Node) -> FeatureTrace:
    """Follow ComponentReference ``refersTo`` links from ``feature`` to the first non-reference object."""
    current = feature
    path: list[Node] = []
    visited: set[Node] = set()
    while True:
        if current in visited:
            path.append(current)
            return FeatureTrace(None, tuple(path), "cycle")
        visited.add(current)
        obj = ctx.get(current)
        if obj is None:
            return FeatureTrace(None, tuple(path), "missing")
        if not obj.has_class(spec.COMPONENT_REFERENCE):
            return FeatureTrace(current, tuple(path))
        path.append(current)
        nxt = obj.first_resource(spec.REFERS_TO)
        if nxt is None:
            return FeatureTrace(None, tuple(path), "missing_refers_to")
        current = nxt


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


def linear_location(ctx: Sbol3Context, identity: Node) -> LinearLocation | None:
    """Normalize a local Range, Cut, or EntireSequence to a span."""
    location = ctx.get(identity)
    if location is None:
        return None
    sequence = location.first_resource(spec.HAS_SEQUENCE)
    if sequence is None:
        return None
    orientation = directional_orientation(location.first_iri(spec.ORIENTATION))
    if location.has_class(spec.RANGE):
        start = location.integer(spec.START)
        end = location.integer(spec.END)
        if start is None or end is None or start <= 0 or end < start:
            return None
        return LinearLocation(identity, sequence, start - 1, end, orientation)
    if location.has_class(spec.CUT):
        at = location.integer(spec.AT)
        if at is None or at < 0:
            return None
        return LinearLocation(identity, sequence, at, at, orientation)
    if location.has_class(spec.ENTIRE_SEQUENCE):
        sequence_obj = ctx.get(sequence)
        if sequence_obj is None:
            return None
        elements = sequence_obj.first_literal(spec.ELEMENTS)
        if elements is None:
            return None
        return LinearLocation(identity, sequence, 0, len(elements.encode("utf-8")), orientation)
    return None


def locations_for_feature(ctx: Sbol3Context, feature: Node) -> list[LinearLocation]:
    """Spans of the (reference-resolved) feature's local locations."""
    trace = trace_feature(ctx, feature)
    target = trace.target if trace.error is None else feature
    obj = ctx.get(target)
    if obj is None:
        return []
    spans = (linear_location(ctx, location) for location in obj.resources(spec.HAS_LOCATION))
    return [span for span in spans if span is not None]


def _sequential_relation_satisfied(restriction: str, s: LinearLocation, o: LinearLocation) -> bool:
    if restriction == spec.PRECEDES:
        return s.start < o.start
    if restriction == spec.STRICTLY_PRECEDES:
        return s.end < o.start
    if restriction == spec.MEETS:
        return s.end == o.start
    if restriction == spec.OVERLAPS:
        return s.start < o.start < s.end < o.end
    if restriction == spec.CONTAINS:
        return s.start <= o.start and s.end >= o.end
    if restriction == spec.STRICTLY_CONTAINS:
        return s.start < o.start and s.end > o.end
    if restriction == spec.EQUALS:
        return s.start == o.start and s.end == o.end
    if restriction == spec.FINISHES:
        return s.start > o.start and s.end == o.end
    if restriction == spec.STARTS:
        return s.start == o.start and s.end < o.end
    return True


def _identity_key(ctx: Sbol3Context, feature: Node) -> tuple[tuple[str, Node], bool] | None:
    trace = trace_feature(ctx, feature)
    if trace.error is not None:
        return None
    obj = ctx.get(trace.target)
    if obj is None:
        return None
    through_reference = bool(trace.path)
    if obj.has_class(spec.SUB_COMPONENT):
        instance_of = obj.first_resource(spec.INSTANCE_OF)
        return None if instance_of is None else (("instance", instance_of), through_reference)
    if obj.has_class(spec.EXTERNALLY_DEFINED):
        definition = obj.first_resource(spec.DEFINITION)
        return None if definition is None else (("definition", definition), through_reference)
    return None


def _feature_orientation(ctx: Sbol3Context, feature: Node) -> str | None:
    trace = trace_feature(ctx, feature)
    if trace.error is not None:
        return None
    obj = ctx.get(trace.target)
    return None if obj is None else directional_orientation(obj.first_iri(spec.ORIENTATION))


def table8_relation(ctx: Sbol3Context, restriction: str, subject: Node, obj: Node) -> Relation:
    """Evaluate an identity or orientation restriction (Tables 8 and 9) between two Features."""
    if restriction in (spec.VERIFY_IDENTICAL, spec.DIFFERENT_FROM):
        subject_key = _identity_key(ctx, subject)
        object_key = _identity_key(ctx, obj)
        if subject_key is None or object_key is None:
            return Relation(UNKNOWN)
        same = subject_key[0] == object_key[0]
        if restriction == spec.VERIFY_IDENTICAL:
            if same:
                return Relation(SATISFIED)
            if subject_key[1] or object_key[1]:
                return Relation(UNKNOWN)
            return Relation(CONTRADICTED)
        return Relation(CONTRADICTED) if same else Relation(SATISFIED)
    if restriction in (spec.SAME_ORIENTATION_AS, spec.OPPOSITE_ORIENTATION_AS):
        subject_orientation = _feature_orientation(ctx, subject)
        object_orientation = _feature_orientation(ctx, obj)
        if subject_orientation is None or object_orientation is None:
            return Relation(UNKNOWN)
        same = subject_orientation == object_orientation
        if (restriction == spec.SAME_ORIENTATION_AS) == same:
            return Relation(SATISFIED)
        return Relation(CONTRADICTED)
    if restriction == spec.REPLACES:
        return Relation(UNKNOWN)
    return Relation(UNSUPPORTED)


def table10_relation(ctx: Sbol3Context, restriction: str, subject: Node, obj: Node) -> Relation:
    """Evaluate a sequential restriction (Table 10) between the locations of two Features."""
    if restriction not in spec.SEQUENTIAL_RESTRICTION_IRIS:
        return Relation(UNSUPPORTED)
    subject_locations = locations_for_feature(ctx, subject)
    object_locations = locations_for_feature(ctx, obj)
    comparable: tuple[Node, Node] | None = None
    for s in subject_locations:
        for o in object_locations:
            if s.sequence != o.sequence:
                continue
            if _sequential_relation_satisfied(restriction, s, o):
                return Relation(SATISFIED)
            if comparable is None:
                comparable = (s.identity, o.identity)
    if comparable is None:
        return Relation(UNKNOWN)
    return Relation(CONTRADICTED, comparable[0], comparable[1])


def type_properties(ctx: Sbol3Context, feature: Node) -> frozenset[str] | None:
    """The ``sbol:type`` IRIs of the object that determines a Feature's type, when resolvable."""
    trace = trace_feature(ctx, feature)
    if trace.error is not None:
        return None
    obj = ctx.get(trace.target)
    if obj is None:
        return None
    referent: Node | None = None
    if obj.has_class(spec.LOCAL_SUB_COMPONENT) or obj.has_class(spec.EXTERNALLY_DEFINED):
        referent = trace.target
    elif obj.has_class(spec.SUB_COMPONENT):
        referent = obj.first_resource(spec.INSTANCE_OF)
    referent_obj = ctx.get(referent)
    if referent_obj is None:
        return None
    return frozenset(str(i) for i in referent_obj.iris(spec.TYPE))


@dataclass
class DerivationContext:
    """A CombinatorialDerivation with its template's features split into static and variable ones."""

    derivation: Node
    template: Node
    template_features: frozenset[Node]
    variables: dict[Node, Node] = field(default_factory=dict)
    static_features: list[Node] = field(default_factory=list)


def derivation_context(ctx: Sbol3Context, derivation: Sbol3Object) -> DerivationContext | None:
    """Resolve a derivation's local template and variable features."""
    template = derivation.first_resource(spec.TEMPLATE)
    template_obj = ctx.get(template)
    if template is None or template_obj is None:
        return None
    template_features = list(dict.fromkeys(template_obj.resources(spec.HAS_FEATURE)))
    variables: dict[Node, Node] = {}
    for variable_feature in derivation.resources(spec.HAS_VARIABLE_FEATURE):
        variable_feature_obj = ctx.get(variable_feature)
        if variable_feature_obj is None:
            continue
        variable = variable_feature_obj.first_resource(spec.VARIABLE)
        if variable is None:
            continue
        variables[variable] = variable_feature
    static = [f for f in template_features if f not in variables]
    return DerivationContext(derivation.identity, template, frozenset(template_features), variables, static)


def derived_objects(ctx: Sbol3Context, derivation: Node, class_iri: str) -> list[Sbol3Object]:
    """Objects of a class whose ``prov:wasDerivedFrom`` names the derivation."""
    return [
        o
        for o in ctx.objects.values()
        if o.has_class(class_iri) and derivation in o.resources(spec.PROV_WAS_DERIVED_FROM)
    ]


def features_derived_from(ctx: Sbol3Context, component: Sbol3Object, template_feature: Node) -> list[Node]:
    """Features of a derived Component that derive from a template Feature."""
    result = []
    for feature in component.resources(spec.HAS_FEATURE):
        obj = ctx.get(feature)
        if obj is not None and template_feature in obj.resources(spec.PROV_WAS_DERIVED_FROM):
            result.append(feature)
    return result


def feature_derives_from_template(ctx: Sbol3Context, feature: Node, template_features: frozenset[Node]) -> bool:
    """Whether a Feature derives from any of the template's Features."""
    obj = ctx.get(feature)
    return obj is not None and any(c in template_features for c in obj.resources(spec.PROV_WAS_DERIVED_FROM))


def static_feature_properties_match(ctx: Sbol3Context, derived: Node, template: Node) -> bool | None:
    """Whether a derived Feature preserves the template Feature's core properties."""
    derived_obj = ctx.get(derived)
    template_obj = ctx.get(template)
    if derived_obj is None or template_obj is None:
        return None
    return all(set(derived_obj.values(p)) == set(template_obj.values(p)) for p in FEATURE_EQUIVALENCE_PREDICATES)


def cardinality_allows(cardinality: Node | None, count: int) -> bool:
    """Whether a derived Feature count satisfies a VariableFeature cardinality."""
    value = None if cardinality is None else str(cardinality)
    if value == spec.ONE:
        return count == 1
    if value == spec.ZERO_OR_ONE_VALUE:
        return count <= 1
    if value == spec.ONE_OR_MORE_VALUE:
        return count >= 1
    return True


def _collect_collection_components(ctx: Sbol3Context, collection: Node, visited: set[Node], out: set[Node]) -> None:
    if collection in visited:
        return
    visited.add(collection)
    obj = ctx.get(collection)
    if obj is None or not obj.has_class(spec.COLLECTION):
        return
    for member in obj.resources(spec.MEMBER):
        member_obj = ctx.get(member)
        if member_obj is None:
            continue
        if member_obj.has_class(spec.COMPONENT):
            out.add(member)
        elif member_obj.has_class(spec.COLLECTION):
            _collect_collection_components(ctx, member, visited, out)


def allowed_variants(ctx: Sbol3Context, variable_feature: Sbol3Object) -> set[Node]:
    """Components a VariableFeature allows through variant, variantCollection, and variantDerivation."""
    allowed: set[Node] = set()
    for variant in variable_feature.resources(spec.VARIANT):
        obj = ctx.get(variant)
        if obj is not None and obj.has_class(spec.COMPONENT):
            allowed.add(variant)
    for collection in variable_feature.resources(spec.VARIANT_COLLECTION):
        _collect_collection_components(ctx, collection, set(), allowed)
    derivations = set(variable_feature.resources(spec.VARIANT_DERIVATION))
    if derivations:
        for component in ctx.instances(spec.COMPONENT):
            if any(c in derivations for c in component.resources(spec.PROV_WAS_DERIVED_FROM)):
                allowed.add(component.identity)
    return allowed
