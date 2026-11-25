"""ComponentDefinition, Component, SequenceAnnotation, SequenceConstraint, Location, and MapsTo rules."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from itertools import islice

from sbol_utilities.validation.sbol2 import spec as S
from sbol_utilities.validation.sbol2.context import Sbol2Context, Sbol2Object
from sbol_utilities.validation.sbol2.helpers import (
    definition_cycles,
    extents,
    extents_overlap,
    range_span,
    use_remote_collisions,
)
from sbol_utilities.validation.sbol2.registry import REGISTRY


def parent_definition(ctx: Sbol2Context, child: str) -> Sbol2Object | None:
    """The Component- or ModuleDefinition listing ``child`` as a component, functionalComponent, or module: the
    earliest in document order among the first such definition for each of those properties."""
    firsts: list[Sbol2Object] = []
    for predicate in (S.COMPONENT_P, S.FUNCTIONAL_COMPONENT_P, S.MODULE_P):
        definitions = (
            d for d in ctx.parents(child, predicate) if d.has_class(S.COMPONENT_DEFINITION, S.MODULE_DEFINITION)
        )
        firsts.extend(islice(definitions, 1))
    return min(firsts, key=lambda definition: definition.index) if firsts else None


@REGISTRY.rule("sbol2-10603", "sbol2-11704")
def self_containing_definitions(ctx: Sbol2Context) -> None:
    """A Component or Module does not instantiate the definition that contains it."""
    for obj in ctx.instances(S.COMPONENT, S.MODULE):
        definition = obj.first_iri(S.DEFINITION)
        if obj.iri is None or definition is None:
            continue
        parent = parent_definition(ctx, obj.iri)
        if parent is not None and parent.iri == definition:
            ctx.report(
                "sbol2-11704" if obj.has_class(S.MODULE) else "sbol2-10603",
                obj,
                "a component or module must not refer to its own containing definition",
                property=S.DEFINITION,
            )


@REGISTRY.rule("sbol2-10909", "sbol2-10905")
def sequence_annotation_components(ctx: Sbol2Context) -> None:
    """A SequenceAnnotation names either a Component of its own definition or roles, not both."""
    for obj in ctx.instances(S.SEQUENCE_ANNOTATION):
        if obj.values(S.COMPONENT_P) and obj.values(S.ROLE):
            ctx.report(
                "sbol2-10909",
                obj,
                "a SequenceAnnotation must not include both a component and a roles property",
                property=S.ROLE,
            )
        component = obj.first_iri(S.COMPONENT_P)
        if component is None:
            continue
        definition = ctx.parent(obj, S.SEQUENCE_ANNOTATION_P)
        if definition is not None and component not in definition.iris(S.COMPONENT_P):
            ctx.report(
                "sbol2-10905",
                obj,
                "the Component of a SequenceAnnotation must be contained by its ComponentDefinition",
                property=S.COMPONENT_P,
            )


def annotation_for(ctx: Sbol2Context, definition: Sbol2Object, component: str) -> Sbol2Object | None:
    """The first SequenceAnnotation of ``definition`` that refers to ``component``."""
    return next(
        (a for a in ctx.referenced(definition, S.SEQUENCE_ANNOTATION_P) if a.first_iri(S.COMPONENT_P) == component),
        None,
    )


def annotation_bounds(ctx: Sbol2Context, annotation: Sbol2Object) -> tuple[int, int] | None:
    """The first and last position of the SequenceAnnotation's earliest Location."""
    return min((extent.bounds for extent in extents(ctx, annotation)), default=None)


def orientations(ctx: Sbol2Context, annotation: Sbol2Object) -> list[str]:
    """The orientation of each Location of a SequenceAnnotation; a Location without one is inline."""
    return [location.first_iri(S.ORIENTATION) or S.INLINE for location in ctx.referenced(annotation, S.LOCATION_P)]


@REGISTRY.rule("sbol2-11406", "sbol2-11403", "sbol2-11405")
def sequence_constraint_components(ctx: Sbol2Context) -> None:
    """A SequenceConstraint relates two different Components of its ComponentDefinition."""
    for obj in ctx.instances(S.SEQUENCE_CONSTRAINT):
        subject, constrained = obj.first_iri(S.SUBJECT), obj.first_iri(S.OBJECT)
        if subject is not None and subject == constrained:
            ctx.report(
                "sbol2-11406",
                obj,
                "the object of a SequenceConstraint must not be the same Component as its subject",
                property=S.OBJECT,
            )
        definition = ctx.parent(obj, S.SEQUENCE_CONSTRAINT_P)
        if definition is None:
            continue
        components = definition.iris(S.COMPONENT_P)
        if subject is not None and subject not in components:
            ctx.report(
                "sbol2-11403",
                obj,
                "the subject of a SequenceConstraint must be a Component of its ComponentDefinition",
                property=S.SUBJECT,
            )
        if constrained is not None and constrained not in components:
            ctx.report(
                "sbol2-11405",
                obj,
                "the object of a SequenceConstraint must be a Component of its ComponentDefinition",
                property=S.OBJECT,
            )


def contained_constraints(ctx: Sbol2Context) -> Iterator[tuple[Sbol2Object, Sbol2Object, str, str]]:
    """Each SequenceConstraint held by a ComponentDefinition that names a subject and an object, with that
    definition and those two Components."""
    for obj in ctx.instances(S.SEQUENCE_CONSTRAINT):
        definition = ctx.parent(obj, S.SEQUENCE_CONSTRAINT_P)
        subject, constrained = obj.first_iri(S.SUBJECT), obj.first_iri(S.OBJECT)
        if definition is not None and subject is not None and constrained is not None:
            yield obj, definition, subject, constrained


def definition_of(ctx: Sbol2Context, instance: str) -> str | None:
    """The definition a Component held in the document names."""
    obj = ctx.get(instance)
    return None if obj is None else obj.first_iri(S.DEFINITION)


@REGISTRY.rule("sbol2-11413", "sbol2-11414")
def different_from_constraints(ctx: Sbol2Context) -> None:
    """A differentFrom SequenceConstraint relates Components with different definitions."""
    for obj, _, subject, constrained in contained_constraints(ctx):
        if obj.first_iri(S.RESTRICTION) != S.DIFFERENT_FROM:
            continue
        subject_definition, object_definition = definition_of(ctx, subject), definition_of(ctx, constrained)
        if subject_definition is None or object_definition is None:
            continue
        if subject_definition == object_definition:
            ctx.report(
                "sbol2-11413",
                obj,
                "a differentFrom SequenceConstraint must relate Components with different definitions",
            )
        left, right = ctx.resolve(subject_definition), ctx.resolve(object_definition)
        if left is not None and right is not None and left.iri is not None and left.iri == right.iri:
            ctx.report(
                "sbol2-11414",
                obj,
                "a differentFrom SequenceConstraint must relate Components resolving to different ComponentDefinitions",
            )


#: (restriction, rule, whether a subject and an object orientation violate it, message)
ORIENTATION_RESTRICTIONS: tuple[tuple[str, str, Callable[[str, str], bool], str], ...] = (
    (
        S.SAME_ORIENTATION_AS,
        "sbol2-11410",
        lambda subject, constrained: subject != constrained,
        "a sameOrientationAs SequenceConstraint requires matching orientations",
    ),
    (
        S.OPPOSITE_ORIENTATION_AS,
        "sbol2-11411",
        lambda subject, constrained: subject == constrained,
        "an oppositeOrientationAs SequenceConstraint requires differing orientations",
    ),
)


@REGISTRY.rule("sbol2-11409", *(rule for _, rule, _, _ in ORIENTATION_RESTRICTIONS))
def constraint_positions(ctx: Sbol2Context) -> None:
    """A precedes or orientation SequenceConstraint agrees with the SequenceAnnotations of its Components."""
    for obj, definition, subject, constrained in contained_constraints(ctx):
        # the annotations are read from the object the definition's IRI resolves to, by identity or persistentIdentity
        annotated = ctx.resolve(definition.iri)
        if annotated is None:
            continue
        subject_annotation = annotation_for(ctx, annotated, subject)
        object_annotation = annotation_for(ctx, annotated, constrained)
        if subject_annotation is None or object_annotation is None:
            continue
        restriction = obj.first_iri(S.RESTRICTION)
        if restriction == S.PRECEDES:
            subject_position, object_position = annotation_bounds(ctx, subject_annotation), annotation_bounds(
                ctx, object_annotation
            )
            if subject_position is not None and object_position is not None and object_position < subject_position:
                ctx.report(
                    "sbol2-11409",
                    obj,
                    "a precedes SequenceConstraint requires the subject to be positioned before the object",
                    property=S.RESTRICTION,
                )
        for required, rule, violates, message in ORIENTATION_RESTRICTIONS:
            if restriction == required and any(
                violates(s, o)
                for s in orientations(ctx, subject_annotation)
                for o in orientations(ctx, object_annotation)
            ):
                ctx.report(rule, obj, message, property=S.RESTRICTION)


@REGISTRY.rule("sbol2-10803", "sbol2-10804")
def maps_to_locals(ctx: Sbol2Context) -> None:
    """A MapsTo local names an instance held by the same definition as the MapsTo's owner."""
    for obj in ctx.instances(S.MAPS_TO):
        local = obj.first_iri(S.LOCAL)
        if local is None:
            continue
        owner = ctx.parent(obj, S.MAPS_TO_P)
        if owner is None or owner.iri is None:
            continue
        definition = ctx.parent(owner.iri, S.COMPONENT_P)
        if definition is not None:
            if local not in definition.iris(S.COMPONENT_P):
                ctx.report(
                    "sbol2-10803",
                    obj,
                    "the local of a MapsTo must refer to a Component in the same ComponentDefinition",
                    property=S.LOCAL,
                )
            continue
        module_definition = ctx.parent(owner.iri, S.FUNCTIONAL_COMPONENT_P) or ctx.parent(owner.iri, S.MODULE_P)
        if module_definition is not None and local not in module_definition.iris(S.FUNCTIONAL_COMPONENT_P):
            ctx.report(
                "sbol2-10804",
                obj,
                "the local of a MapsTo must refer to a FunctionalComponent in the same ModuleDefinition",
                property=S.LOCAL,
            )


@REGISTRY.rule("sbol2-10522")
def unique_annotated_components(ctx: Sbol2Context) -> None:
    """No two SequenceAnnotations of a ComponentDefinition refer to the same Component."""
    for obj in ctx.instances(S.COMPONENT_DEFINITION):
        by_annotation: dict[str, str] = {}
        for annotation in ctx.referenced(obj, S.SEQUENCE_ANNOTATION_P):
            component = annotation.first_iri(S.COMPONENT_P)
            if annotation.iri is not None and component is not None:
                by_annotation[annotation.iri] = component
        if len(set(by_annotation.values())) < len(by_annotation):
            ctx.report(
                "sbol2-10522",
                obj,
                "no two SequenceAnnotations may refer to the same Component",
                property=S.SEQUENCE_ANNOTATION_P,
            )


@REGISTRY.rule("sbol2-10605")
def component_definition_cycles(ctx: Sbol2Context) -> None:
    """ComponentDefinitions do not form a cycle through their Components' definitions."""
    for obj in definition_cycles(ctx, S.COMPONENT_DEFINITION, S.COMPONENT_P, S.DEFINITION):
        ctx.report(
            "sbol2-10605",
            obj,
            "a ComponentDefinition must not form a cycle through its Components' definitions",
            property=S.COMPONENT_P,
        )


@REGISTRY.rule("sbol2-10526")
def component_definition_use_remote(ctx: Sbol2Context) -> None:
    """Two useRemote MapsTos of a ComponentDefinition's Components do not share a local."""
    for obj in use_remote_collisions(ctx, S.COMPONENT_DEFINITION, (S.COMPONENT_P,)):
        ctx.report(
            "sbol2-10526",
            obj,
            "two useRemote MapsTos of a ComponentDefinition must not share a local",
            property=S.MAPS_TO_P,
        )


@REGISTRY.rule("sbol2-10903")
def annotation_location_overlaps(ctx: Sbol2Context) -> None:
    """The Locations of one SequenceAnnotation do not overlap."""
    for obj in ctx.instances(S.SEQUENCE_ANNOTATION):
        if extents_overlap(extents(ctx, obj)):
            ctx.report(
                "sbol2-10903", obj, "the Locations of a SequenceAnnotation should not overlap", property=S.LOCATION_P
            )


@REGISTRY.rule("sbol2-10711", "sbol2-10712")
def component_source_locations(ctx: Sbol2Context) -> None:
    """A Component's source Locations do not overlap and span the same length as the Ranges annotating it."""
    annotation_of: dict[str, Sbol2Object] = {}
    for annotation in ctx.instances(S.SEQUENCE_ANNOTATION):
        component = annotation.first_iri(S.COMPONENT_P)
        if component is not None:
            annotation_of.setdefault(component, annotation)
    for obj in ctx.instances(S.COMPONENT):
        source = extents(ctx, obj, S.SOURCE_LOCATION)
        if extents_overlap(source):
            ctx.report(
                "sbol2-10711", obj, "the source Locations of a Component should not overlap", property=S.SOURCE_LOCATION
            )
        annotating = annotation_of.get(obj.iri or "")
        if annotating is None:
            continue
        source_length, annotated_length = range_span(source), range_span(extents(ctx, annotating))
        if source_length is not None and annotated_length is not None and source_length != annotated_length:
            ctx.report(
                "sbol2-10712",
                obj,
                "a Component's source Range length should equal its annotation Range length",
                property=S.SOURCE_LOCATION,
            )
