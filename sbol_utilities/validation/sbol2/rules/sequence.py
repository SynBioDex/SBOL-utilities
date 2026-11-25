"""Sequence rules and the ComponentDefinition sequence best practices."""

from __future__ import annotations

from sbol_utilities.validation.sbol2 import spec as S
from sbol_utilities.validation.sbol2.context import Sbol2Context, Sbol2Object
from sbol_utilities.validation.sbol2.helpers import RangeExtent, extents, is_nucleic_acid_region
from sbol_utilities.validation.sbol2.registry import REGISTRY


@REGISTRY.rule("sbol2-10405")
def elements_match_encoding(ctx: Sbol2Context) -> None:
    """A Sequence's elements use the IUPAC nucleic-acid or protein alphabet its encoding names."""
    for obj in ctx.instances(S.SEQUENCE):
        encoding = obj.first_iri(S.ENCODING)
        elements = obj.first_literal(S.ELEMENTS)
        if encoding is None or elements is None:
            continue
        if encoding == S.IUPAC_NUCLEIC_ENCODING:
            consistent = all(c in S.IUPAC_NUCLEIC_ALPHABET for c in _ascii_upper(elements))
        elif encoding == S.IUPAC_PROTEIN_ENCODING:
            consistent = all(c.isascii() and c.isalpha() for c in elements)
        else:
            consistent = True
        if not consistent:
            ctx.report(
                "sbol2-10405",
                obj,
                "the elements of a Sequence must be consistent with its encoding",
                property=S.ELEMENTS,
            )


def _ascii_upper(text: str) -> str:
    return "".join(c.upper() if c.isascii() else c for c in text)


def _sequences(ctx: Sbol2Context, definition: Sbol2Object) -> list[tuple[str, int]]:
    """The (encoding, elements length) of each Sequence of a ComponentDefinition that is held in the document and has
    an encoding; a Sequence without elements has length 0."""
    return [
        (encoding, len(sequence.first_literal(S.ELEMENTS) or ""))
        for _, sequence in ctx.resolved(definition, S.SEQUENCE_P)
        if (encoding := sequence.first_iri(S.ENCODING)) is not None
    ]


def _table_1_lengths(sequences: list[tuple[str, int]]) -> dict[str, int]:
    """Table 1 encoding -> the length of the first Sequence with that encoding."""
    lengths: dict[str, int] = {}
    for encoding, length in sequences:
        if encoding in S.TABLE_1_ENCODINGS:
            lengths.setdefault(encoding, length)
    return lengths


def _nucleic_length(ctx: Sbol2Context, definition: Sbol2Object) -> int | None:
    """The length of a ComponentDefinition's first IUPAC nucleic-acid Sequence that has elements."""
    for _, sequence in ctx.resolved(definition, S.SEQUENCE_P):
        elements = sequence.first_literal(S.ELEMENTS)
        if sequence.first_iri(S.ENCODING) == S.IUPAC_NUCLEIC_ENCODING and elements is not None:
            return len(elements)
    return None


@REGISTRY.rule("sbol2-10516")
def definition_sequence_categories(ctx: Sbol2Context) -> None:
    """A ComponentDefinition with Sequences has one whose encoding matches its DNA/RNA, protein, or small-molecule
    type."""
    for obj in ctx.instances(S.COMPONENT_DEFINITION):
        sequences = _sequences(ctx, obj)
        if not sequences:
            continue
        encodings = _table_1_lengths(sequences)
        types = obj.iris(S.TYPE)
        if (
            (is_nucleic_acid_region(types) and S.IUPAC_NUCLEIC_ENCODING not in encodings)
            or (S.BIOPAX_PROTEIN in types and S.IUPAC_PROTEIN_ENCODING not in encodings)
            or (S.BIOPAX_SMALL_MOLECULE in types and S.SMILES_ENCODING not in encodings)
        ):
            ctx.report(
                "sbol2-10516",
                obj,
                "a ComponentDefinition must carry a Sequence whose encoding matches its type",
                property=S.SEQUENCE_P,
            )


@REGISTRY.rule("sbol2-10518")
def definition_sequence_lengths(ctx: Sbol2Context) -> None:
    """A ComponentDefinition's Sequences of one Table 1 encoding share a length."""
    for obj in ctx.instances(S.COMPONENT_DEFINITION):
        sequences = _sequences(ctx, obj)
        first = _table_1_lengths(sequences)
        if any(first.get(encoding, length) != length for encoding, length in sequences):
            ctx.report(
                "sbol2-10518",
                obj,
                "a ComponentDefinition's Sequences of one encoding should share a length",
                property=S.SEQUENCE_P,
            )


def _outside(location: Sbol2Object, length: int) -> bool:
    """Whether a Range or Cut lies outside a sequence of ``length`` positions.

    A Range without a start is read as starting at 1 and one without an end as ending at 0; a Cut without a
    position is read as at 0.
    """
    if location.has_class(S.RANGE):
        start, end = location.integer(S.START), location.integer(S.END)
        return (1 if start is None else start) <= 0 or (0 if end is None else end) > length
    if location.has_class(S.CUT):
        at = location.integer(S.AT) or 0
        return at < 0 or at > length
    return False


@REGISTRY.rule("sbol2-10523")
def annotation_positions(ctx: Sbol2Context) -> None:
    """The Locations of a ComponentDefinition's SequenceAnnotations lie within its nucleic-acid Sequence."""
    for obj in ctx.instances(S.COMPONENT_DEFINITION):
        length = _table_1_lengths(_sequences(ctx, obj)).get(S.IUPAC_NUCLEIC_ENCODING)
        if length is None:
            continue
        locations = (
            location
            for annotation in ctx.referenced(obj, S.SEQUENCE_ANNOTATION_P)
            for location in ctx.referenced(annotation, S.LOCATION_P)
        )
        if any(_outside(location, length) for location in locations):
            ctx.report(
                "sbol2-10523",
                obj,
                "a SequenceAnnotation position should lie within the ComponentDefinition's sequence",
                property=S.SEQUENCE_ANNOTATION_P,
            )


def _annotated_definition_length(ctx: Sbol2Context, annotation: Sbol2Object) -> int | None:
    """The nucleic-acid Sequence length of the definition of the Component a SequenceAnnotation refers to."""
    component = ctx.resolve(annotation.first_iri(S.COMPONENT_P))
    definition = None if component is None else ctx.resolve(component.first_iri(S.DEFINITION))
    return None if definition is None else _nucleic_length(ctx, definition)


@REGISTRY.rule("sbol2-10520")
def hierarchy_sequence_lengths(ctx: Sbol2Context) -> None:
    """A SequenceAnnotation's first Range is as long as the Sequence of the Component it annotates."""
    for obj in ctx.instances(S.COMPONENT_DEFINITION):
        if S.IUPAC_NUCLEIC_ENCODING not in _table_1_lengths(_sequences(ctx, obj)):
            continue
        for annotation in ctx.referenced(obj, S.SEQUENCE_ANNOTATION_P):
            span = next((e.length for e in extents(ctx, annotation) if isinstance(e, RangeExtent)), None)
            child_length = None if span is None else _annotated_definition_length(ctx, annotation)
            if child_length is not None and child_length != span:
                ctx.report(
                    "sbol2-10520",
                    obj,
                    "Sequences across a ComponentDefinition-Component hierarchy should be consistent",
                    property=S.SEQUENCE_P,
                )
                break
