"""Unit tests for sbol_utilities.convert: IRI algebra and the value maps."""

from __future__ import annotations

import pytest
from rdflib import Literal

from sbol_utilities.convert import uri
from sbol_utilities.convert import values as v
from sbol_utilities.convert.identity import compare_versions
from sbol_utilities.convert.terms import S2, S3

CUSTOM = "http://example.org/custom"

# IRI algebra

ONTOLOGY_TERMS = [
    pytest.param(
        uri.convert_so_2_to_3,
        uri.convert_so_3_to_2,
        "http://identifiers.org/so/SO:0000141",
        "https://identifiers.org/SO:0000141",
        id="SO",
    ),
    pytest.param(
        uri.convert_sbo_2_to_3,
        uri.convert_sbo_3_to_2,
        "http://identifiers.org/biomodels.sbo/SBO:0000020",
        "https://identifiers.org/SBO:0000020",
        id="SBO",
    ),
    pytest.param(
        uri.convert_edam_2_to_3,
        uri.convert_edam_3_to_2,
        "http://identifiers.org/edam/format_1207",
        "https://identifiers.org/edam:format_1207",
        id="EDAM",
    ),
]

RESPELLERS = [
    uri.convert_so_2_to_3,
    uri.convert_so_3_to_2,
    uri.convert_sbo_2_to_3,
    uri.convert_sbo_3_to_2,
    uri.convert_edam_2_to_3,
    uri.convert_edam_3_to_2,
]


@pytest.mark.parametrize("to_sbol3, to_sbol2, sbol2, sbol3", ONTOLOGY_TERMS)
def test_ontology_terms_change_spelling_and_scheme(to_sbol3, to_sbol2, sbol2, sbol3):
    assert to_sbol3(sbol2) == sbol3
    assert to_sbol2(sbol3) == sbol2


@pytest.mark.parametrize("convert", RESPELLERS, ids=lambda convert: convert.__name__)
@pytest.mark.parametrize(
    "iri",
    [
        "http://parts.igem.org/cgi/pgroup.cgi",
        "http://wiki.synbiohub.org/wiki/Terms/igem#partType/Regulatory",
        "https://example.org/lab/roles/also/reporter",
        "http://example.org/also/SO:0000141",
    ],
)
def test_non_ontology_iris_pass_through_unchanged(convert, iri):
    """Only identifiers.org ontology terms are respelled; other IRIs, even ones containing ``so/``, are untouched."""
    assert convert(iri) == iri


@pytest.mark.parametrize(
    "convert, iri, expected",
    [
        (uri.component_type_2_to_3, "http://identifiers.org/so/SO:0000987", "https://identifiers.org/SO:0000987"),
        (uri.component_type_2_to_3, CUSTOM, CUSTOM),
        (uri.component_type_3_to_2, "https://identifiers.org/SO:0000987", "http://identifiers.org/so/SO:0000987"),
        (uri.component_type_3_to_2, "https://example.org/custom", "https://example.org/custom"),
    ],
)
def test_component_types_only_respell_so_terms(convert, iri, expected):
    """Component types outside SO pass through unchanged, without a scheme toggle."""
    assert convert(iri) == expected


@pytest.mark.parametrize(
    "segment, valid", [("", True), ("1", True), ("1.2.3", True), ("1a", True), ("BBa_E0040", False), ("v1", False)]
)
def test_version_validity(segment, valid):
    """A version is empty or a leading digit followed by word characters."""
    assert uri.is_version_valid(segment) is valid


@pytest.mark.parametrize(
    "iri, prefix, display_id, version",
    [
        ("https://synbiohub.org/public/igem/BBa_E0040/1", "https://synbiohub.org/public/igem", "BBa_E0040", "1"),
        ("https://example.org/lab/foo", "https://example.org/lab", "foo", ""),
    ],
    ids=["versioned", "unversioned"],
)
def test_sbol2_decomposition(iri, prefix, display_id, version):
    """``<prefix>/<displayId>[/<version>]`` splits into its parts."""
    assert uri.Sbol2Iri.parse(iri) == (prefix, display_id, version)
    assert uri.uri_prefix_sbol2(iri) == prefix
    assert uri.display_id_sbol2(iri) == display_id
    assert uri.version_sbol2(iri) == version


@pytest.mark.parametrize("iri", ["", "https://example.org/", "urn:example"])
def test_sbol2_decomposition_rejects_non_decomposable(iri):
    """Empty IRIs, IRIs ending in ``/``, and IRIs without ``/`` do not decompose."""
    assert uri.Sbol2Iri.parse(iri) is None
    assert uri.version_sbol2(iri) is None
    assert uri.display_id_sbol2(iri) is None
    assert uri.uri_prefix_sbol2(iri) is None
    assert uri.create_sbol3_uri(iri) == iri


@pytest.mark.parametrize("iri, version", [("https://example.org/lab/1/foo", "1"), ("https://example.org/lab/foo", "")])
def test_sbol3_decomposition(iri, version):
    """SBOL 3 places the version, when there is one, before the displayId."""
    assert uri.namespace_sbol3(iri) == "https://example.org/lab"
    assert uri.version_sbol3(iri) == version
    assert uri.display_id_sbol3(iri) == "foo"


@pytest.mark.parametrize(
    "sbol2, sbol3",
    [
        ("https://synbiohub.org/public/igem/BBa_E0040/1", "https://synbiohub.org/public/igem/1/BBa_E0040"),
        ("https://example.org/lab/foo", "https://example.org/lab/foo"),
    ],
    ids=["versioned", "unversioned"],
)
def test_identities_round_trip(sbol2, sbol3):
    """create_sbol3_uri and create_sbol2_uri invert each other."""
    assert uri.create_sbol3_uri(sbol2) == sbol3
    assert uri.create_sbol2_uri(sbol3) == sbol2


@pytest.mark.parametrize(
    "persistent_identity, version, identity",
    [
        ("https://example.org/a", "1", "https://example.org/a/1"),
        ("https://example.org/a", None, "https://example.org/a"),
    ],
)
def test_versioned_and_without_version(persistent_identity, version, identity):
    assert uri.versioned(persistent_identity, version) == identity
    assert uri.without_version(identity, version) == persistent_identity


@pytest.mark.parametrize(
    "iri, segment",
    [
        ("https://example.org/lab/promoter", "promoter"),
        ("http://example.org/a#frag", "frag"),
        ("https://example.org/lab/", "https://example.org/lab/"),
    ],
)
def test_last_segment(iri, segment):
    assert uri.last_segment(iri) == segment


@pytest.mark.parametrize(
    "iri, origin",
    [("https://example.org/lab/x", "https://example.org"), ("urn:uuid:1234", "urn:uuid"), ("relative/path", None)],
)
def test_url_origin(iri, origin):
    assert uri.url_origin(iri) == origin


def test_claim_child_skips_used_iris():
    used = {"https://example.org/c/a"}
    assert uri.claim_child("https://example.org/c", uri.numbered("a"), used) == ("a_2", "https://example.org/c/a_2")
    assert uri.claim_child("https://example.org/c/", uri.numbered("b"), used) == ("b", "https://example.org/c/b")
    assert uri.claim_child("https://example.org/c/", uri.numbered("b"), used, join=uri.slash_join) == (
        "b",
        "https://example.org/c//b",
    )
    assert "https://example.org/c/a_2" in used


@pytest.mark.parametrize("a, b, sign", [("1", "1.0", 0), ("2.10", "2.9", 1), ("1", "2", -1), ("1.a", "1.b", -1)])
def test_compare_versions(a, b, sign):
    """Dotted versions compare numerically by segment, missing segments counting as zero."""
    assert compare_versions(a, b) == sign


# Value maps

NASEQ = "http://www.chem.qmul.ac.uk/iubmb/misc/naseq.html"
AMINO_ACID = "http://www.chem.qmul.ac.uk/iupac/AminoAcid/"
EDAM_NUCLEIC = "https://identifiers.org/edam:format_1207"
EDAM_PROTEIN = "https://identifiers.org/edam:format_1208"
CARDINALITIES = ("one", "zeroOrOne", "oneOrMore", "zeroOrMore")


@pytest.mark.parametrize(
    "predicate, value, expected",
    [
        (S2.orientation, S2.inline, v.SO_INLINE),
        (S2.orientation, S2.reverseComplement, v.SO_REVERSE_COMPLEMENT),
        (S2.orientation, CUSTOM, None),
        (S2.encoding, NASEQ, EDAM_NUCLEIC),
        (S2.encoding, AMINO_ACID, EDAM_PROTEIN),
        (S2.encoding, CUSTOM, None),
        *((S2.operator, S2.base + name, S3.base + name) for name in CARDINALITIES),
        (S2.operator, CUSTOM, None),
        (S2.strategy, S2.enumerate, S3.enumerate),
        (S2.strategy, S2.sample, S3.sample),
        (S2.strategy, CUSTOM, None),
        (S2.roleIntegration, S2.mergeRoles, S3.mergeRoles),
        (S2.roleIntegration, S2.overrideRoles, S3.overrideRoles),
        (S2.roleIntegration, CUSTOM, None),
        (S2.restriction, S2.precedes, S3.precedes),
        (S2.restriction, S2.unknownRelation, None),
    ],
)
def test_upgrade_value(predicate, value, expected):
    """Enumerated SBOL 2 values take their SBOL 3 spelling; unrecognized ones have none."""
    assert v.upgrade_value(predicate, value) == expected


@pytest.mark.parametrize(
    "predicate, value, expected",
    [
        (S3.orientation, S3.inline, S2.inline),
        (S3.orientation, v.SO_INLINE, S2.inline),
        (S3.orientation, S3.reverseComplement, S2.reverseComplement),
        (S3.orientation, CUSTOM, None),
        (S3.encoding, EDAM_NUCLEIC, NASEQ),
        (S3.encoding, EDAM_PROTEIN, AMINO_ACID),
        (S3.restriction, S3.precedes, S2.precedes),
        (S3.restriction, S3.verifyIdentical, S2.verifyIdentical),
        (S3.restriction, CUSTOM, None),
        *((S3.cardinality, S3.base + name, S2.base + name) for name in CARDINALITIES),
        (S3.cardinality, CUSTOM, None),
        (S3.strategy, S3.enumerate, S2.enumerate),
        (S3.strategy, S3.sample, S2.sample),
        (S3.roleIntegration, S3.mergeRoles, S2.mergeRoles),
        (S3.roleIntegration, S3.overrideRoles, S2.overrideRoles),
        (S3.roleIntegration, CUSTOM, None),
    ],
)
def test_downgrade_value(predicate, value, expected):
    """Enumerated SBOL 3 values take their SBOL 2 spelling; both orientation spellings map back."""
    assert v.downgrade_value(predicate, value) == expected


def test_biopax_and_sbo_types():
    """BioPAX types map to SBO terms, and back to the ``*Region`` BioPAX spelling."""
    assert v.BIOPAX_TO_SBO[v.BIOPAX + "Dna"] == "https://identifiers.org/SBO:0000251"
    assert v.BIOPAX_TO_SBO[v.BIOPAX + "Protein"] == "https://identifiers.org/SBO:0000252"
    assert CUSTOM not in v.BIOPAX_TO_SBO
    assert v.SBO_TO_BIOPAX["https://identifiers.org/SBO:0000251"] == v.BIOPAX + "DnaRegion"


@pytest.mark.parametrize(
    "refinement, restriction",
    [
        (S2.verifyIdentical, S3.verifyIdentical),
        (S2.useLocal, S3.replaces),
        (S2.useRemote, S3.replaces),
        (S2.merge, S3.replaces),
    ],
)
def test_refinement_to_restriction(refinement, restriction):
    """MapsTo refinements map to Constraint restrictions; merge is treated as useRemote."""
    assert v.REFINEMENTS[refinement] == restriction


@pytest.mark.parametrize(
    "restriction, cref_is_subject, refinement",
    [
        (S3.replaces, True, S2.useRemote),
        (S3.replaces, False, S2.useLocal),
        (S3.verifyIdentical, True, S2.verifyIdentical),
        (S3.verifyIdentical, False, S2.verifyIdentical),
        (CUSTOM, True, None),
    ],
)
def test_refinement_inference_is_position_aware(restriction, cref_is_subject, refinement):
    """``replaces`` means useRemote with the reference in subject, useLocal in object."""
    assert v.refinement_for(restriction, cref_is_subject=cref_is_subject) == refinement


def test_class_and_predicate_tables_invert():
    """Each SBOL 3 class and predicate a downgrade maps comes back to itself through the upgrade tables."""
    assert all(v.UPGRADE_CLASSES[sbol2] == sbol3 for sbol3, sbol2 in v.DOWNGRADE_CLASSES.items())
    sbol_predicates = {p3: p2 for p3, p2 in v.DOWNGRADE_PREDICATES.items() if p2.startswith(S2.base)}
    assert all(v.UPGRADE_PREDICATES[p2] == p3 for p3, p2 in sbol_predicates.items())
    assert {v.DOWNGRADE_PREDICATES[p3] for p3 in v.DCTERMS_TO_SBOL3.values()} == set(v.DCTERMS_TO_SBOL3)


def test_sbol2_literal_canonicalization():
    """Literals of SBOL 2 model properties take the model's datatype; extension literals are untouched."""
    start = v.canonical_sbol2_literal(S2.start, Literal("07"))
    assert str(start) == "07" and str(start.datatype).endswith("#integer")
    assert v.canonical_sbol2_literal("http://purl.org/dc/terms/title", Literal("x", lang="en")) == Literal("x")
    assert v.canonical_sbol2_literal("http://example.org/note", Literal("x", lang="en")) == Literal("x", lang="en")
