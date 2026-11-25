"""Sequence rules and the ComponentDefinition sequence best practices."""

from __future__ import annotations

from sbol_utilities.validation.sbol2 import spec as S
from sbol_utilities.validation.sbol2.context import Sbol2Context, Sbol2Object
from sbol_utilities.validation.sbol2.helpers import RangeExtent, extents
from sbol_utilities.validation.sbol2.registry import REGISTRY


@REGISTRY.rule("sbol2-10405")
def elements_match_encoding(ctx: Sbol2Context) -> None:
    """A Sequence's elements use the IUPAC nucleic-acid or protein alphabet its encoding names."""
    for obj in ctx.sbol_objects:
        if not obj.has_class(S.SEQUENCE):
            continue
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


def _nucleic_length(ctx: Sbol2Context, definition: Sbol2Object) -> int | None:
    for iri in definition.iris(S.SEQUENCE_P):
        sequence = ctx.resolve(iri)
        if sequence is None or sequence.first_iri(S.ENCODING) != S.IUPAC_NUCLEIC_ENCODING:
            continue
        elements = sequence.first_literal(S.ELEMENTS)
        if elements is not None:
            return len(elements)
    return None


@REGISTRY.rule("sbol2-10516", "sbol2-10518", "sbol2-10520", "sbol2-10523")
def definition_sequences(ctx: Sbol2Context) -> None:
    """A ComponentDefinition carries sequences matching its type, of consistent lengths, covering its annotations."""
    for obj in ctx.sbol_objects:
        if obj.has_class(S.COMPONENT_DEFINITION):
            _check_definition(ctx, obj)


def _check_definition(ctx: Sbol2Context, obj: Sbol2Object) -> None:
    sequences: list[tuple[str, int]] = []
    for iri in obj.iris(S.SEQUENCE_P):
        sequence = ctx.resolve(iri)
        if sequence is None:
            continue
        encoding = sequence.first_iri(S.ENCODING)
        if encoding is None:
            continue
        elements = sequence.first_literal(S.ELEMENTS)
        sequences.append((encoding, len(elements) if elements is not None else 0))
    if not sequences:
        return
    lengths: dict[str, int] = {}
    length_mismatch = False
    for encoding, length in sequences:
        if encoding not in S.TABLE_1_ENCODINGS:
            continue
        if encoding in lengths:
            if lengths[encoding] != length:
                length_mismatch = True
        else:
            lengths[encoding] = length
    nucleic = lengths.get(S.IUPAC_NUCLEIC_ENCODING)

    types = obj.iris(S.TYPE)
    wants_nucleic = S.BIOPAX_DNA_REGION in types or S.BIOPAX_RNA_REGION in types
    missing_category = (
        (wants_nucleic and nucleic is None)
        or (S.BIOPAX_PROTEIN in types and S.IUPAC_PROTEIN_ENCODING not in lengths)
        or (S.BIOPAX_SMALL_MOLECULE in types and S.SMILES_ENCODING not in lengths)
    )

    out_of_bounds = False
    hierarchy_inconsistent = False
    if nucleic is not None:
        for annotation in ctx.referenced(obj, S.SEQUENCE_ANNOTATION_P):
            for location in ctx.referenced(annotation, S.LOCATION_P):
                if location.has_class(S.RANGE):
                    start = location.integer(S.START)
                    end = location.integer(S.END)
                    start = 1 if start is None else start
                    end = 0 if end is None else end
                    if start <= 0 or end > nucleic:
                        out_of_bounds = True
                elif location.has_class(S.CUT):
                    at = location.integer(S.AT)
                    at = 0 if at is None else at
                    if at < 0 or at > nucleic:
                        out_of_bounds = True
        for annotation in ctx.referenced(obj, S.SEQUENCE_ANNOTATION_P):
            component_iri = annotation.first_iri(S.COMPONENT_P)
            if component_iri is None:
                continue
            span = next((e.length for e in extents(ctx, annotation) if isinstance(e, RangeExtent)), None)
            if span is None:
                continue
            component = ctx.resolve(component_iri)
            definition_iri = None if component is None else component.first_iri(S.DEFINITION)
            if definition_iri is None:
                continue
            definition = ctx.resolve(definition_iri)
            child_length = None if definition is None else _nucleic_length(ctx, definition)
            if child_length is not None and child_length != span:
                hierarchy_inconsistent = True

    if missing_category:
        ctx.report(
            "sbol2-10516",
            obj,
            "a ComponentDefinition must carry a Sequence whose encoding matches its type",
            property=S.SEQUENCE_P,
        )
    if length_mismatch:
        ctx.report(
            "sbol2-10518",
            obj,
            "a ComponentDefinition's Sequences of one encoding should share a length",
            property=S.SEQUENCE_P,
        )
    if out_of_bounds:
        ctx.report(
            "sbol2-10523",
            obj,
            "a SequenceAnnotation position should lie within the ComponentDefinition's sequence",
            property=S.SEQUENCE_ANNOTATION_P,
        )
    if hierarchy_inconsistent:
        ctx.report(
            "sbol2-10520",
            obj,
            "Sequences across a ComponentDefinition-Component hierarchy should be consistent",
            property=S.SEQUENCE_P,
        )
