"""Lexical forms, IRI shapes, and ontology-table lookups the SBOL 3 rules share."""

from __future__ import annotations

import re
from collections.abc import Iterable

from rdflib.term import Literal, Node, URIRef

from sbol_utilities.validation.datatypes import is_date_time_lexical, is_float_lexical, literal_datatype, parse_i64
from sbol_utilities.validation.ontology import NUCLEIC_ACID, Ontology
from sbol_utilities.validation.schema import ValueKind
from sbol_utilities.vocab import RDF_LANG_STRING, XSD_NS, XSD_STRING

_HEX = re.compile(r"[0-9A-Fa-f]+")
_HASH_TOKEN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")

EDAM_IUPAC_DNA_RNA = "https://identifiers.org/edam:format_1207"
EDAM_IUPAC_PROTEIN = "https://identifiers.org/edam:format_1208"
IUPAC_NUCLEOTIDES = frozenset("ACGTURYSWKMBDHVN")
IUPAC_PROTEIN = frozenset("ACDEFGHIKLMNPQRSTVWYBZJXUO*")

EDAM_FORMAT = "EDAM:format_1915"
EDAM_TEXTUAL_FORMAT = "EDAM:format_2330"
SO_TOPOLOGY_ATTRIBUTE = "SO:0000986"
SO_STRAND_ATTRIBUTE = "SO:0000983"
SBO_MODELING_FRAMEWORK = "SBO:0000004"
SBO_SYSTEMS_DESCRIPTION_PARAMETER = "SBO:0000545"
SBO_PHYSICAL_ENTITY = "SBO:0000236"

MODEL_LANGUAGE_TABLE_15 = (
    "https://identifiers.org/edam:format_2585",
    "https://identifiers.org/edam:format_3240",
    "https://identifiers.org/edam:format_3156",
)
MODEL_FRAMEWORK_TABLE_16 = ("https://identifiers.org/SBO:0000062", "https://identifiers.org/SBO:0000063")


# --- lexical forms ---


def is_url(value: str) -> bool:
    """http or https IRI."""
    return value.startswith(("http://", "https://"))


def is_namespace_url(value: str) -> bool:
    """http, https, or urn IRI."""
    return is_url(value) or value.startswith("urn:")


def is_hex_digest(value: str) -> bool:
    """Nonempty ASCII hexadecimal string."""
    return _HEX.fullmatch(value) is not None


def is_hash_algorithm_token(value: str) -> bool:
    """Registry-style hash algorithm token."""
    return _HASH_TOKEN.fullmatch(value) is not None


def url_is_child_of(candidate: str, parent: str) -> bool:
    """Whether ``candidate`` lies strictly under ``parent`` as a path."""
    base = parent.rstrip("/")
    return candidate.startswith(base) and candidate[len(base) :].startswith("/")


def url_matches_namespace_display_id(identity: str, namespace: str, display_id: str) -> bool:
    """Whether ``identity`` is ``namespace/[local/]displayId``."""
    namespace = namespace.rstrip("/")
    if not identity.startswith(namespace):
        return False
    rest = identity[len(namespace) :]
    if not rest.startswith("/"):
        return False
    rest = rest[1:]
    segments = rest.split("/")
    return bool(rest) and all(segments) and segments[-1] == display_id


def _is_string_datatype(datatype: str) -> bool:
    return datatype in (XSD_STRING, RDF_LANG_STRING)


_INTEGER_TYPES = frozenset(
    XSD_NS + t
    for t in (
        "integer",
        "long",
        "int",
        "short",
        "byte",
        "nonNegativeInteger",
        "positiveInteger",
        "nonPositiveInteger",
        "negativeInteger",
        "unsignedLong",
        "unsignedInt",
        "unsignedShort",
        "unsignedByte",
    )
)
_FLOAT_TYPES = frozenset(XSD_NS + t for t in ("float", "double", "decimal"))


def value_matches_kind(term: Node, kind: ValueKind) -> bool:
    """Whether a value has a datatype compatible with a property's value kind and a well-formed lexical form."""
    if kind is ValueKind.URI:
        return isinstance(term, URIRef)
    if kind is ValueKind.URL:
        return isinstance(term, URIRef) and is_namespace_url(str(term))
    if not isinstance(term, Literal):
        return False
    datatype = literal_datatype(term)
    value = str(term)
    if kind is ValueKind.STRING:
        return _is_string_datatype(datatype)
    if kind in (ValueKind.INTEGER, ValueKind.LONG):
        return (datatype in _INTEGER_TYPES or _is_string_datatype(datatype)) and parse_i64(value) is not None
    if kind is ValueKind.FLOAT:
        return (datatype in _FLOAT_TYPES or _is_string_datatype(datatype)) and is_float_lexical(value)
    return (datatype == XSD_NS + "dateTime" or _is_string_datatype(datatype)) and is_date_time_lexical(value)


#: IRI prefixes (lower case) of records in the external resources the rules recognize
_EXTERNAL_RESOURCE_PREFIXES: dict[str, tuple[str, ...]] = {
    "uniprot": (
        "https://identifiers.org/uniprot:",
        "http://identifiers.org/uniprot:",
        "http://purl.uniprot.org/uniprot/",
        "https://www.uniprot.org/uniprot/",
        "https://www.uniprot.org/uniprotkb/",
    ),
    "chebi": (
        "https://identifiers.org/chebi:",
        "http://identifiers.org/chebi:",
        "http://purl.obolibrary.org/obo/chebi_",
        "https://www.ebi.ac.uk/chebi/",
    ),
    "pubchem": (
        "https://identifiers.org/pubchem.compound:",
        "http://identifiers.org/pubchem.compound:",
        "https://pubchem.ncbi.nlm.nih.gov/compound/",
    ),
}


def known_external_resource(iri: str) -> str | None:
    """The resource (``uniprot``, ``chebi``, or ``pubchem``) a definition IRI names a record of, if any."""
    lowered = iri.lower()
    return next((name for name, prefixes in _EXTERNAL_RESOURCE_PREFIXES.items() if lowered.startswith(prefixes)), None)


# --- ontology tables ---


def is_sbo_physical_entity_term(ontology: Ontology, iri: str) -> bool | None:
    """For known SBO terms, whether the term lies in the physical entity representation branch."""
    if ontology.namespace(iri) != "SBO":
        return None
    return ontology.is_in_branch(iri, SBO_PHYSICAL_ENTITY)


def is_edam_format_term(ontology: Ontology, iri: str) -> bool | None:
    """For known terms, whether the term is an EDAM format."""
    if not ontology.contains_term(iri):
        return None
    return ontology.namespace(iri) == "EDAM" and ontology.is_in_branch(iri, EDAM_FORMAT)


def is_known_non_edam_namespace(ontology: Ontology, iri: str) -> bool:
    """Whether a term is known and comes from an ontology other than EDAM."""
    namespace = ontology.namespace(iri)
    return namespace is not None and namespace != "EDAM"


def is_nucleic_acid_component_type(ontology: Ontology, iri: str) -> bool:
    """Whether a known Component type is in the nucleic-acid family."""
    return ontology.component_type_family(iri) == NUCLEIC_ACID


def canonical_table_1_sequence_encoding_iri(ontology: Ontology, iri: str) -> str | None:
    """Preferred IRI of a Table 1 encoding term."""
    if not ontology.is_table_1_sequence_encoding(iri):
        return None
    return ontology.canonicalize(iri)


def sequence_encoding(ontology: Ontology, iri: str) -> str | None:
    """Canonical IRI of a known Sequence encoding term."""
    if ontology.is_sequence_encoding_term(iri) is not True:
        return None
    return ontology.canonicalize(iri)


def component_type(ontology: Ontology, iri: str) -> str | None:
    """Canonical IRI of a Table 2 Component type term."""
    if not ontology.is_table_2_component_type(iri):
        return None
    return ontology.canonicalize(iri)


def _matches_table_entry(iri: str, table: Iterable[str]) -> str | None:
    """The table entry ``iri`` spells, ignoring case and the http/https distinction."""
    lowered = iri.lower()
    for canonical in table:
        if lowered == canonical.lower() or lowered == canonical.replace("https://", "http://").lower():
            return canonical
    return None


def canonical_model_language_iri(iri: str) -> str | None:
    """Table 15 URI that ``iri`` is an alias of."""
    return _matches_table_entry(iri, MODEL_LANGUAGE_TABLE_15)


def canonical_model_framework_iri(iri: str) -> str | None:
    """Table 16 URI that ``iri`` is an alias of."""
    return _matches_table_entry(iri, MODEL_FRAMEWORK_TABLE_16)


def first_invalid_sequence_element(ontology: Ontology, elements: str, encoding: str) -> str | None:
    """First character of ``elements`` outside the IUPAC alphabet of a Table 1 IUPAC encoding."""
    canonical = ontology.canonicalize(encoding)
    if canonical == EDAM_IUPAC_DNA_RNA:
        alphabet = IUPAC_NUCLEOTIDES
    elif canonical == EDAM_IUPAC_PROTEIN:
        alphabet = IUPAC_PROTEIN
    else:
        return None
    for character in elements:
        upper = character.upper() if character.isascii() else character
        if upper not in alphabet:
            return character
    return None
