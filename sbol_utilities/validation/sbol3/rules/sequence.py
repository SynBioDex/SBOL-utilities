"""Sequence rules (sbol3-105xx): encodings and element alphabets."""

from __future__ import annotations

from sbol_utilities.validation.sbol3 import spec
from sbol_utilities.validation.sbol3.context import Sbol3Context
from sbol_utilities.validation.sbol3.helpers import (
    EDAM_TEXTUAL_FORMAT,
    canonical_table_1_sequence_encoding_iri,
    first_invalid_sequence_element,
)
from sbol_utilities.validation.sbol3.registry import REGISTRY


@REGISTRY.rule("sbol3-10501", "sbol3-10502", "sbol3-10503", "sbol3-10504", "sbol3-10505")
def sequences(ctx: Sbol3Context) -> None:
    """Encoding presence, ontology classification, Table 1 aliases, and IUPAC alphabets."""
    ontology = ctx.ontology
    for obj in ctx.instances(spec.SEQUENCE):
        if len(obj.values(spec.ELEMENTS)) == 1 and not obj.values(spec.ENCODING):
            ctx.report(
                "sbol3-10501", obj, "Sequence objects with elements must provide an encoding", property=spec.ENCODING
            )
        elements = obj.first_literal(spec.ELEMENTS)
        first_encoding = obj.first_iri(spec.ENCODING)
        if elements is not None and first_encoding is not None:
            invalid = first_invalid_sequence_element(ontology, elements, str(first_encoding))
            if invalid is not None:
                ctx.report(
                    "sbol3-10503",
                    obj,
                    f"Sequence elements contain `{invalid}`, which is inconsistent with encoding `{first_encoding}`",
                    property=spec.ELEMENTS,
                )
        for encoding in obj.iris(spec.ENCODING):
            text = str(encoding)
            if ontology.is_sequence_encoding_term(text) is False:
                ctx.report(
                    "sbol3-10502",
                    obj,
                    f"Sequence encoding `{text}` is not an ontology Sequence encoding term",
                    property=spec.ENCODING,
                )
            canonical = canonical_table_1_sequence_encoding_iri(ontology, text)
            if canonical is not None and canonical != text:
                ctx.report(
                    "sbol3-10504",
                    obj,
                    f"Sequence encoding `{text}` is equivalent to Table 1 URI `{canonical}`",
                    property=spec.ENCODING,
                )
            if ontology.in_branch_if_known(text, EDAM_TEXTUAL_FORMAT) is False:
                ctx.report(
                    "sbol3-10505",
                    obj,
                    f"Sequence encoding `{text}` is not in the EDAM textual format branch",
                    property=spec.ENCODING,
                )
