"""ComponentDefinition, Component, SequenceAnnotation, SequenceConstraint, Location, and MapsTo rules."""

from __future__ import annotations

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
    """The first Component- or ModuleDefinition listing ``child`` as a component, functionalComponent, or module."""
    best: Sbol2Object | None = None
    for predicate in (S.COMPONENT_P, S.FUNCTIONAL_COMPONENT_P, S.MODULE_P):
        for candidate in ctx.parents(child, predicate):
            if candidate.has_class(S.COMPONENT_DEFINITION, S.MODULE_DEFINITION):
                if best is None or candidate.index < best.index:
                    best = candidate
                break
    return best


@REGISTRY.rule("sbol2-10603", "sbol2-11704")
def self_containing_definitions(ctx: Sbol2Context) -> None:
    """A Component or Module does not instantiate the definition that contains it."""
    for obj in ctx.sbol_objects:
        if obj.iri is None or not (obj.has_class(S.COMPONENT, S.MODULE)):
            continue
        definition = obj.first_iri(S.DEFINITION)
        if definition is None:
            continue
        parent = parent_definition(ctx, obj.iri)
        if parent is not None and parent.iri == definition:
            rule = "sbol2-11704" if obj.has_class(S.MODULE) else "sbol2-10603"
            ctx.report(
                rule,
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


def _annotation_for(ctx: Sbol2Context, definition: Sbol2Object, component: str) -> Sbol2Object | None:
    for annotation in ctx.referenced(definition, S.SEQUENCE_ANNOTATION_P):
        if annotation.first_iri(S.COMPONENT_P) == component:
            return annotation
    return None


def _position(ctx: Sbol2Context, annotation: Sbol2Object) -> tuple[int, int] | None:
    """The first and last position of the SequenceAnnotation's earliest Location."""
    return min((extent.bounds for extent in extents(ctx, annotation)), default=None)


def _orientations(ctx: Sbol2Context, annotation: Sbol2Object) -> list[str]:
    return [location.first_iri(S.ORIENTATION) or S.INLINE for location in ctx.referenced(annotation, S.LOCATION_P)]


def _definition_of(ctx: Sbol2Context, instance: str) -> str | None:
    obj = ctx.get(instance)
    return None if obj is None else obj.first_iri(S.DEFINITION)


@REGISTRY.rule(
    "sbol2-11406",
    "sbol2-11403",
    "sbol2-11405",
    "sbol2-11413",
    "sbol2-11414",
    "sbol2-11409",
    "sbol2-11410",
    "sbol2-11411",
)
def sequence_constraints(ctx: Sbol2Context) -> None:
    """SequenceConstraint subject/object membership, distinctness, and agreement with annotated positions."""
    for obj in ctx.instances(S.SEQUENCE_CONSTRAINT):
        subject, target = obj.first_iri(S.SUBJECT), obj.first_iri(S.OBJECT)
        if subject is not None and subject == target:
            ctx.report(
                "sbol2-11406",
                obj,
                "the object of a SequenceConstraint must not be the same Component as its subject",
                property=S.OBJECT,
            )
        definition = ctx.parent(obj, S.SEQUENCE_CONSTRAINT_P)
        if definition is None:
            continue
        restriction = obj.first_iri(S.RESTRICTION)
        different_from = restriction == S.DIFFERENT_FROM
        same_definition = same_resolved = False
        if different_from and subject is not None and target is not None:
            subject_def, object_def = _definition_of(ctx, subject), _definition_of(ctx, target)
            same_definition = subject_def is not None and object_def is not None and subject_def == object_def
            if subject_def is not None and object_def is not None:
                left, right = ctx.resolve(subject_def), ctx.resolve(object_def)
                same_resolved = (
                    left is not None and right is not None and left.iri is not None and left.iri == right.iri
                )
        if definition.iri is not None:
            _check_positions(ctx, obj, definition.iri, restriction, subject, target)
        if subject is not None and subject not in definition.iris(S.COMPONENT_P):
            ctx.report(
                "sbol2-11403",
                obj,
                "the subject of a SequenceConstraint must be a Component of its ComponentDefinition",
                property=S.SUBJECT,
            )
        if target is not None and target not in definition.iris(S.COMPONENT_P):
            ctx.report(
                "sbol2-11405",
                obj,
                "the object of a SequenceConstraint must be a Component of its ComponentDefinition",
                property=S.OBJECT,
            )
        if same_definition:
            ctx.report(
                "sbol2-11413",
                obj,
                "a differentFrom SequenceConstraint must relate Components with different definitions",
            )
        if same_resolved:
            ctx.report(
                "sbol2-11414",
                obj,
                "a differentFrom SequenceConstraint must relate Components resolving to different ComponentDefinitions",
            )


def _check_positions(
    ctx: Sbol2Context,
    constraint: Sbol2Object,
    definition_id: str,
    restriction: str | None,
    subject: str | None,
    target: str | None,
) -> None:
    if subject is None or target is None:
        return
    definition = ctx.resolve(definition_id)
    if definition is None:
        return
    subject_annotation = _annotation_for(ctx, definition, subject)
    object_annotation = _annotation_for(ctx, definition, target)
    if subject_annotation is None or object_annotation is None:
        return
    if restriction == S.PRECEDES:
        subject_position, object_position = _position(ctx, subject_annotation), _position(ctx, object_annotation)
        if subject_position is not None and object_position is not None and object_position < subject_position:
            ctx.report(
                "sbol2-11409",
                constraint,
                "a precedes SequenceConstraint requires the subject to be positioned before the object",
                property=S.RESTRICTION,
            )
    elif restriction == S.SAME_ORIENTATION_AS:
        subject_o, object_o = _orientations(ctx, subject_annotation), _orientations(ctx, object_annotation)
        if any(s != o for s in subject_o for o in object_o):
            ctx.report(
                "sbol2-11410",
                constraint,
                "a sameOrientationAs SequenceConstraint requires matching orientations",
                property=S.RESTRICTION,
            )
    elif restriction == S.OPPOSITE_ORIENTATION_AS:
        subject_o, object_o = _orientations(ctx, subject_annotation), _orientations(ctx, object_annotation)
        if any(s == o for s in subject_o for o in object_o):
            ctx.report(
                "sbol2-11411",
                constraint,
                "an oppositeOrientationAs SequenceConstraint requires differing orientations",
                property=S.RESTRICTION,
            )


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
    for obj in ctx.sbol_objects:
        if obj.has_class(S.SEQUENCE_ANNOTATION) and extents_overlap(extents(ctx, obj)):
            ctx.report(
                "sbol2-10903", obj, "the Locations of a SequenceAnnotation should not overlap", property=S.LOCATION_P
            )


@REGISTRY.rule("sbol2-10711", "sbol2-10712")
def component_source_locations(ctx: Sbol2Context) -> None:
    """A Component's source Locations do not overlap and span the same length as the Ranges annotating it."""
    annotation_by_component: dict[str, Sbol2Object] = {}
    for candidate in ctx.objects:
        if candidate.has_class(S.SEQUENCE_ANNOTATION):
            component = candidate.first_iri(S.COMPONENT_P)
            if component is not None:
                annotation_by_component.setdefault(component, candidate)
    for obj in ctx.instances(S.COMPONENT):
        source = extents(ctx, obj, S.SOURCE_LOCATION)
        if extents_overlap(source):
            ctx.report(
                "sbol2-10711", obj, "the source Locations of a Component should not overlap", property=S.SOURCE_LOCATION
            )
        if obj.iri is None:
            continue
        annotation = annotation_by_component.get(obj.iri)
        if annotation is None:
            continue
        source_len, target_len = range_span(source), range_span(extents(ctx, annotation))
        if source_len is not None and target_len is not None and source_len != target_len:
            ctx.report(
                "sbol2-10712",
                obj,
                "a Component's source Range length should equal its annotation Range length",
                property=S.SOURCE_LOCATION,
            )
