"""Enumerated-value maps between the SBOL 2 and SBOL 3 vocabularies, in both directions.

Each lookup returns None for a value it does not recognize; callers pass such values through unchanged.
"""

from __future__ import annotations

from rdflib import Literal

from sbol_utilities.convert.terms import EDAM_IUPAC_DNA_RNA, EDAM_IUPAC_PROTEIN, OM_NS, PROV_NS, S2, S3, XSD_STRING
from sbol_utilities.vocab import DCTERMS_DESCRIPTION, DCTERMS_TITLE, RDFS_COMMENT, RDFS_LABEL, XSD_NS

SO_INLINE = "https://identifiers.org/SO:0001030"
SO_REVERSE_COMPLEMENT = "https://identifiers.org/SO:0001031"

BIOPAX = "http://www.biopax.org/release/biopax-level3.owl#"

ENCODINGS: dict[str, str] = {
    "http://www.chem.qmul.ac.uk/iubmb/misc/naseq.html": EDAM_IUPAC_DNA_RNA,
    "http://www.chem.qmul.ac.uk/iupac/AminoAcid/": EDAM_IUPAC_PROTEIN,
    "http://www.opensmiles.org/opensmiles.html": "https://identifiers.org/edam:format_1196",
    "http://www.chem.qmul.ac.uk/iupac/bibliog/whitebook.html": "https://identifiers.org/edam:format_1197",
}

#: BioPAX ComponentDefinition types and their SBO equivalents; both ``Dna`` and ``DnaRegion`` occur in the wild
BIOPAX_TO_SBO: dict[str, str] = {
    BIOPAX + "Dna": "https://identifiers.org/SBO:0000251",
    BIOPAX + "DnaRegion": "https://identifiers.org/SBO:0000251",
    BIOPAX + "Rna": "https://identifiers.org/SBO:0000250",
    BIOPAX + "RnaRegion": "https://identifiers.org/SBO:0000250",
    BIOPAX + "Protein": "https://identifiers.org/SBO:0000252",
    BIOPAX + "SmallMolecule": "https://identifiers.org/SBO:0000247",
    BIOPAX + "Complex": "https://identifiers.org/SBO:0000253",
}

#: the downgrade emits the ``*Region`` BioPAX spelling, the modern norm
SBO_TO_BIOPAX: dict[str, str] = {
    "https://identifiers.org/SBO:0000251": BIOPAX + "DnaRegion",
    "https://identifiers.org/SBO:0000250": BIOPAX + "RnaRegion",
    "https://identifiers.org/SBO:0000252": BIOPAX + "Protein",
    "https://identifiers.org/SBO:0000247": BIOPAX + "SmallMolecule",
    "https://identifiers.org/SBO:0000253": BIOPAX + "Complex",
}

_RESTRICTIONS = (
    "precedes strictlyPrecedes meets isDisjointFrom contains strictlyContains equals covers overlaps finishes starts "
    "sameOrientationAs oppositeOrientationAs differentFrom verifyIdentical replaces"
).split()

#: SBOL 2 value -> SBOL 3 value, keyed by the SBOL 2 predicate the value appears under
UPGRADE_VALUES: dict[str, dict[str, str]] = {
    S2.orientation: {S2.inline: SO_INLINE, S2.reverseComplement: SO_REVERSE_COMPLEMENT},
    S2.encoding: ENCODINGS,
    S2.restriction: {S2.base + r: S3.base + r for r in _RESTRICTIONS},
    S2.operator: {S2.base + v: S3.base + v for v in ("one", "zeroOrOne", "oneOrMore", "zeroOrMore")},
    S2.strategy: {S2.enumerate: S3.enumerate, S2.sample: S3.sample},
    S2.roleIntegration: {S2.mergeRoles: S3.mergeRoles, S2.overrideRoles: S3.overrideRoles},
}

#: SBOL 3 value -> SBOL 2 value, keyed by the SBOL 3 predicate the value appears under
DOWNGRADE_VALUES: dict[str, dict[str, str]] = {
    S3.orientation: {
        S3.inline: S2.inline,
        SO_INLINE: S2.inline,
        S3.reverseComplement: S2.reverseComplement,
        SO_REVERSE_COMPLEMENT: S2.reverseComplement,
    },
    S3.encoding: {v: k for k, v in ENCODINGS.items()},
    S3.cardinality: {v: k for k, v in UPGRADE_VALUES[S2.operator].items()},
    S3.strategy: {v: k for k, v in UPGRADE_VALUES[S2.strategy].items()},
    S3.roleIntegration: {v: k for k, v in UPGRADE_VALUES[S2.roleIntegration].items()},
}

#: SBOL 2 MapsTo refinement -> SBOL 3 Constraint restriction; ``merge`` is treated as ``useRemote`` (SBOL 3.1.0 §10.2)
REFINEMENTS: dict[str, str] = {
    S2.verifyIdentical: S3.verifyIdentical,
    S2.useLocal: S3.replaces,
    S2.useRemote: S3.replaces,
    S2.merge: S3.replaces,
}


def upgrade_value(predicate: str, value: str) -> str | None:
    """The SBOL 3 spelling of an enumerated SBOL 2 value under ``predicate``."""
    return UPGRADE_VALUES.get(predicate, {}).get(value)


def downgrade_value(predicate: str, value: str) -> str | None:
    """The SBOL 2 spelling of an enumerated SBOL 3 value under ``predicate``.

    Constraint restrictions keep their local name and move from the SBOL 3 to the SBOL 2 namespace.
    """
    if predicate == S3.restriction:
        return S2.base + value[len(S3.base) :] if value.startswith(S3.base) else None
    return DOWNGRADE_VALUES.get(predicate, {}).get(value)


def refinement_for(restriction: str, cref_is_subject: bool) -> str | None:
    """The SBOL 2 MapsTo refinement for a MapsTo-shaped Constraint.

    The ComponentReference's position carries the useLocal/useRemote distinction: ``replaces`` with the reference in
    ``subject`` is ``useRemote``, in ``object`` ``useLocal``; ``verifyIdentical`` is position-insensitive.
    """
    if restriction == S3.verifyIdentical:
        return S2.verifyIdentical
    if restriction == S3.replaces:
        return S2.useRemote if cref_is_subject else S2.useLocal
    return None


# Literal datatypes the SBOL 2 data model assigns, by predicate. SBOL 2 files differ in how they type literals (RDF/XML
# leaves ``sbol:start`` untyped where Turtle writes an integer), so sbol-rs normalizes every literal of a recognized
# property to its model datatype before converting; extension properties keep their literals verbatim.
SBOL2_LITERAL_DATATYPES: dict[str, str] = {
    S2.displayId: XSD_STRING,
    S2.version: XSD_STRING,
    S2.elements: XSD_STRING,
    S2.hash: XSD_STRING,
    DCTERMS_TITLE: XSD_STRING,
    DCTERMS_DESCRIPTION: XSD_STRING,
    RDFS_LABEL: XSD_STRING,
    RDFS_COMMENT: XSD_STRING,
    OM_NS + "symbol": XSD_STRING,
    OM_NS + "alternativeSymbol": XSD_STRING,
    OM_NS + "alternativeLabel": XSD_STRING,
    OM_NS + "longcomment": XSD_STRING,
    S2.start: XSD_NS + "integer",
    S2.end: XSD_NS + "integer",
    S2.at: XSD_NS + "integer",
    OM_NS + "hasExponent": XSD_NS + "integer",
    S2.size: XSD_NS + "long",
    OM_NS + "hasNumericalValue": XSD_NS + "decimal",
    OM_NS + "hasFactor": XSD_NS + "decimal",
    PROV_NS + "startedAtTime": XSD_NS + "dateTime",
    PROV_NS + "endedAtTime": XSD_NS + "dateTime",
}


def canonical_sbol2_literal(predicate: str, literal: Literal) -> Literal:
    """A literal of a recognized SBOL 2 property, retyped to the datatype the SBOL 2 model assigns it.

    The lexical form is kept as written; language tags are dropped.
    """
    datatype = SBOL2_LITERAL_DATATYPES.get(predicate)
    if datatype is None:
        return literal
    current = str(literal.datatype) if literal.datatype is not None else XSD_STRING
    if current == datatype and not literal.language:
        return literal
    if datatype == XSD_STRING:
        return Literal(str(literal))
    return Literal(str(literal), datatype=datatype, normalize=False)
