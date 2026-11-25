"""Lexical, ontology-table, and graph helpers shared by the SBOL 3 rules.

These mirror sbol-rs ``crates/sbol3/src/validation/helpers`` and ``tables.rs``.
"""

from __future__ import annotations

import re

from rdflib.term import Literal, Node, URIRef

from sbol_utilities.validation.ontology import NUCLEIC_ACID, Ontology
from sbol_utilities.validation.sbol3 import spec
from sbol_utilities.validation.sbol3.context import SBOL3Context, SbolObject, literal_datatype
from sbol_utilities.vocab import RDF_LANG_STRING, XSD_NS, XSD_STRING

I64_MIN = -(2**63)
I64_MAX = 2**63 - 1

_INTEGER = re.compile(r"^[+-]?[0-9]+\Z")
_FLOAT = re.compile(r"^[+-]?(?:inf|infinity|nan|(?:[0-9]+\.?[0-9]*|\.[0-9]+)(?:e[+-]?[0-9]+)?)\Z", re.IGNORECASE)
_XSD_INTEGER = re.compile(r"^[+-]?[0-9]+\Z")
_DATETIME = re.compile(
    r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]+)?(?:Z|[+-][0-9]{2}:[0-9]{2})?\Z"
)
_DISPLAY_ID = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*\Z")
_HEX = re.compile(r"^[0-9A-Fa-f]+\Z")
_HASH_TOKEN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*\Z")

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


def parse_i64(value: str | None) -> int | None:
    """Parse a signed 64-bit integer the way Rust's ``i64::from_str`` does, or None."""
    if value is None or not _INTEGER.match(value):
        return None
    number = int(value)
    return number if I64_MIN <= number <= I64_MAX else None


def integer_value(obj: SbolObject, predicate: str) -> int | None:
    """The first literal value of a predicate parsed as an i64."""
    return parse_i64(obj.first_literal_value(predicate))


def is_url(value: str) -> bool:
    """http or https IRI."""
    return value.startswith("http://") or value.startswith("https://")


def is_namespace_url(value: str) -> bool:
    """http, https, or urn IRI."""
    return is_url(value) or value.startswith("urn:")


def is_valid_display_id(value: str) -> bool:
    """displayId lexical form: letter or underscore, then letters, digits, or underscores (ASCII)."""
    return bool(_DISPLAY_ID.match(value))


def is_hex_digest(value: str) -> bool:
    """Nonempty ASCII hexadecimal string."""
    return bool(_HEX.match(value))


def is_hash_algorithm_token(value: str) -> bool:
    """Registry-style hash algorithm token."""
    return bool(_HASH_TOKEN.match(value))


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


def _is_float_lexical(value: str) -> bool:
    return value in ("INF", "+INF", "-INF", "NaN") or bool(_FLOAT.match(value))


def value_matches_kind(term: Node, value_kind: str) -> bool:
    """Table 23 value-kind check: compatible datatype and well-formed lexical value (sbol3-10111)."""
    if value_kind == spec.URI:
        return isinstance(term, URIRef)
    if value_kind == spec.URL:
        return isinstance(term, URIRef) and is_namespace_url(str(term))
    if not isinstance(term, Literal):
        return False
    datatype = literal_datatype(term)
    value = str(term)
    if value_kind == spec.STRING:
        return _is_string_datatype(datatype)
    if value_kind in (spec.INTEGER, spec.LONG):
        return (
            (datatype in _INTEGER_TYPES or _is_string_datatype(datatype))
            and bool(_XSD_INTEGER.match(value))
            and parse_i64(value) is not None
        )
    if value_kind == spec.FLOAT:
        return (datatype in _FLOAT_TYPES or _is_string_datatype(datatype)) and _is_float_lexical(value)
    if value_kind == spec.DATE_TIME:
        return (datatype == XSD_NS + "dateTime" or _is_string_datatype(datatype)) and bool(_DATETIME.match(value))
    return False


# --- class targets ---


def class_inherits(class_iri: str, target: str) -> bool:
    """Whether a class equals or inherits from ``target`` in the class tables."""
    return spec.is_a(class_iri, target)


def object_type_is_or_inherits(obj: SbolObject, target: str) -> bool:
    """Whether any rdf:type of the object is or inherits from ``target``."""
    return any(class_inherits(t, target) for t in obj.rdf_types)


_EXACT_TARGETS = {
    spec.PROV_ACTIVITY_TARGET: spec.PROV_ACTIVITY,
    spec.PROV_AGENT_TARGET: spec.PROV_AGENT,
    spec.PROV_ASSOCIATION_TARGET: spec.PROV_ASSOCIATION,
    spec.PROV_PLAN_TARGET: spec.PROV_PLAN,
    spec.PROV_USAGE_TARGET: spec.PROV_USAGE,
    spec.OM_MEASURE_TARGET: spec.OM_MEASURE,
}


def object_matches_target(obj: SbolObject, target: str) -> bool:
    """Whether a referenced object satisfies a property's reference target."""
    if target in _EXACT_TARGETS:
        return obj.has_rdf_type(_EXACT_TARGETS[target])
    if target == spec.OM_UNIT_TARGET:
        return object_type_is_or_inherits(obj, spec.OM_UNIT)
    if target == spec.OM_PREFIX_TARGET:
        return object_type_is_or_inherits(obj, spec.OM_PREFIX)
    return obj.has_class(target)


def known_external_resource(iri: str) -> str | None:
    """Classify a definition IRI as a UniProt, ChEBI, or PubChem record."""
    iri = iri.lower()
    if iri.startswith(
        (
            "https://identifiers.org/uniprot:",
            "http://identifiers.org/uniprot:",
            "http://purl.uniprot.org/uniprot/",
            "https://www.uniprot.org/uniprot/",
            "https://www.uniprot.org/uniprotkb/",
        )
    ):
        return "uniprot"
    if iri.startswith(
        (
            "https://identifiers.org/chebi:",
            "http://identifiers.org/chebi:",
            "http://purl.obolibrary.org/obo/chebi_",
            "https://www.ebi.ac.uk/chebi/",
        )
    ):
        return "chebi"
    if iri.startswith(
        (
            "https://identifiers.org/pubchem.compound:",
            "http://identifiers.org/pubchem.compound:",
            "https://pubchem.ncbi.nlm.nih.gov/compound/",
        )
    ):
        return "pubchem"
    return None


# --- ontology tables ---


def _branch_if_known(ontology: Ontology, iri: str, root: str) -> bool | None:
    return ontology.is_in_branch(iri, root) if ontology.contains_term(iri) else None


def is_topology_type_term(ontology: Ontology, iri: str) -> bool | None:
    """Known term in the SO topology attribute branch."""
    return _branch_if_known(ontology, iri, SO_TOPOLOGY_ATTRIBUTE)


def is_strand_type_term(ontology: Ontology, iri: str) -> bool | None:
    """Known term in the SO strand attribute branch."""
    return _branch_if_known(ontology, iri, SO_STRAND_ATTRIBUTE)


def is_edam_textual_format(ontology: Ontology, iri: str) -> bool | None:
    """Known term in the EDAM textual format branch."""
    return _branch_if_known(ontology, iri, EDAM_TEXTUAL_FORMAT)


def is_sbo_modeling_framework_term(ontology: Ontology, iri: str) -> bool | None:
    """Known term in the SBO modelling framework branch."""
    return _branch_if_known(ontology, iri, SBO_MODELING_FRAMEWORK)


def is_sbo_systems_description_parameter_term(ontology: Ontology, iri: str) -> bool | None:
    """Known term in the SBO systems description parameter branch."""
    return _branch_if_known(ontology, iri, SBO_SYSTEMS_DESCRIPTION_PARAMETER)


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
    return ontology.canonical_iri(iri) or iri


def sequence_encoding(ontology: Ontology, iri: str) -> str | None:
    """Canonical IRI of a known Sequence encoding term."""
    if ontology.is_sequence_encoding_term(iri) is not True:
        return None
    return ontology.canonical_iri(iri) or iri


def component_type(ontology: Ontology, iri: str) -> str | None:
    """Canonical IRI of a Table 2 Component type term."""
    if not ontology.is_table_2_component_type(iri):
        return None
    return ontology.canonical_iri(iri) or iri


def _matches_table_entry(iri: str, table) -> str | None:
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
    canonical = ontology.canonical_iri(encoding) or encoding
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


# --- document queries ---


def component_contains(ctx: SBOL3Context, component: Node | None, predicate: str, child: Node) -> bool:
    """Whether the object ``component`` lists ``child`` under ``predicate``."""
    obj = ctx.get(component)
    return obj is not None and child in obj.resources(predicate)


def component_allows_sequence(ctx: SBOL3Context, component: Node, sequence: Node) -> bool:
    """Whether a Component declares a Sequence directly or through a Feature's EntireSequence location."""
    obj = ctx.get(component)
    if obj is None:
        return False
    if sequence in obj.resources(spec.HAS_SEQUENCE):
        return True
    for feature in obj.resources(spec.HAS_FEATURE):
        feature_obj = ctx.get(feature)
        if feature_obj is None:
            continue
        for location in feature_obj.resources(spec.HAS_LOCATION):
            location_obj = ctx.get(location)
            if (
                location_obj is not None
                and location_obj.has_class(spec.ENTIRE_SEQUENCE)
                and location_obj.first_resource(spec.HAS_SEQUENCE) == sequence
            ):
                return True
    return False


def collection_contains_only_components_or_collections(ctx: SBOL3Context, collection: Node, visited: set[Node]) -> bool:
    """Whether every local member of a Collection, recursively, is a Component or Collection."""
    if collection in visited:
        return True
    visited.add(collection)
    obj = ctx.get(collection)
    if obj is None:
        return True
    for member in obj.resources(spec.MEMBER):
        member_obj = ctx.get(member)
        if member_obj is None or member_obj.has_class(spec.COMPONENT):
            continue
        if not (
            member_obj.has_class(spec.COLLECTION)
            and collection_contains_only_components_or_collections(ctx, member, visited)
        ):
            return False
    return True


def location_sequence_length(ctx: SBOL3Context, location: SbolObject) -> int | None:
    """Length of the elements of a Location's local Sequence."""
    sequence = ctx.get(location.first_resource(spec.HAS_SEQUENCE))
    if sequence is None:
        return None
    elements = sequence.first_literal_value(spec.ELEMENTS)
    return None if elements is None else len(elements.encode("utf-8"))


def location_length(ctx: SBOL3Context, location: Node) -> int | None:
    """Length covered by a local Location, when known."""
    obj = ctx.get(location)
    if obj is None:
        return None
    if obj.has_class(spec.RANGE):
        start = integer_value(obj, spec.START)
        end = integer_value(obj, spec.END)
        if start is None or end is None or start <= 0 or end < start:
            return None
        return end - start + 1
    if obj.has_class(spec.CUT):
        return 0
    if obj.has_class(spec.ENTIRE_SEQUENCE):
        return location_sequence_length(ctx, obj)
    return None


def sum_location_lengths(ctx: SBOL3Context, locations: list[Node]) -> int | None:
    """Total length of several Locations, or None when any is unknown."""
    total = 0
    for location in locations:
        length = location_length(ctx, location)
        if length is None:
            return None
        total += length
    return total
