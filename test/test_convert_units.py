"""Unit tests for sbol_utilities.convert: IRI algebra, value maps, and engine options."""

from __future__ import annotations

import pytest
from rdflib import Graph, Literal, URIRef

from sbol_utilities.convert import DowngradeOptions, UpgradeOptions, downgrade, upgrade, uri
from sbol_utilities.convert import values as v
from sbol_utilities.convert.identity import compare_versions
from sbol_utilities.convert.terms import BP, S2, S3
from sbol_utilities.rdf_io import serialize
from sbol_utilities.validation import ValidationConfig, validate_sbol3

# IRI algebra


def test_ontology_round_trips():
    """SO / SBO / EDAM terms change spelling and scheme in each direction."""
    assert uri.convert_so_2_to_3("http://identifiers.org/so/SO:0000141") == "https://identifiers.org/SO:0000141"
    assert uri.convert_so_3_to_2("https://identifiers.org/SO:0000141") == "http://identifiers.org/so/SO:0000141"
    assert (
        uri.convert_sbo_2_to_3("http://identifiers.org/biomodels.sbo/SBO:0000020")
        == "https://identifiers.org/SBO:0000020"
    )
    assert (
        uri.convert_sbo_3_to_2("https://identifiers.org/SBO:0000020")
        == "http://identifiers.org/biomodels.sbo/SBO:0000020"
    )
    assert (
        uri.convert_edam_2_to_3("http://identifiers.org/edam/format_1207") == "https://identifiers.org/edam:format_1207"
    )
    assert (
        uri.convert_edam_3_to_2("https://identifiers.org/edam:format_1207") == "http://identifiers.org/edam/format_1207"
    )
    # a role that is not an identifiers.org term is kept exactly as written
    assert uri.convert_so_2_to_3("http://parts.igem.org/cgi/pgroup.cgi") == "http://parts.igem.org/cgi/pgroup.cgi"
    assert uri.convert_so_3_to_2("https://parts.igem.org/cgi/pgroup.cgi") == "https://parts.igem.org/cgi/pgroup.cgi"


def test_non_ontology_iris_pass_through_unchanged():
    """Only identifiers.org ontology terms are respelled; other IRIs, even ones containing ``so/``, are untouched."""
    for iri in (
        "http://wiki.synbiohub.org/wiki/Terms/igem#partType/Regulatory",
        "https://example.org/lab/roles/also/reporter",
        "http://example.org/also/SO:0000141",
    ):
        for convert in (
            uri.convert_so_2_to_3,
            uri.convert_so_3_to_2,
            uri.convert_sbo_2_to_3,
            uri.convert_sbo_3_to_2,
            uri.convert_edam_2_to_3,
            uri.convert_edam_3_to_2,
        ):
            assert convert(iri) == iri


def test_component_types_only_respell_so_terms():
    """Component types outside SO pass through unchanged, without a scheme toggle."""
    assert uri.component_type_2_to_3("http://identifiers.org/so/SO:0000987") == "https://identifiers.org/SO:0000987"
    assert uri.component_type_2_to_3("http://example.org/custom") == "http://example.org/custom"
    assert uri.component_type_3_to_2("https://identifiers.org/SO:0000987") == "http://identifiers.org/so/SO:0000987"
    assert uri.component_type_3_to_2("https://example.org/custom") == "https://example.org/custom"


def test_version_validity():
    """A version is empty or a leading digit followed by word characters."""
    assert uri.is_version_valid("")
    assert uri.is_version_valid("1")
    assert uri.is_version_valid("1.2.3")
    assert uri.is_version_valid("1a")
    assert not uri.is_version_valid("BBa_E0040")
    assert not uri.is_version_valid("v1")


def test_sbol2_decomposition_versioned():
    """``<prefix>/<displayId>/<version>`` splits into its three parts."""
    iri = "https://synbiohub.org/public/igem/BBa_E0040/1"
    assert uri.uri_prefix_sbol2(iri) == "https://synbiohub.org/public/igem"
    assert uri.display_id_sbol2(iri) == "BBa_E0040"
    assert uri.version_sbol2(iri) == "1"


def test_sbol2_decomposition_unversioned():
    """An unversioned SBOL 2 IRI has an empty version."""
    iri = "https://example.org/lab/foo"
    assert uri.uri_prefix_sbol2(iri) == "https://example.org/lab"
    assert uri.display_id_sbol2(iri) == "foo"
    assert uri.version_sbol2(iri) == ""


def test_sbol2_decomposition_rejects_non_decomposable():
    """Empty IRIs, IRIs ending in ``/``, and IRIs without ``/`` do not decompose."""
    for iri in ("", "https://example.org/", "urn:example"):
        assert uri.version_sbol2(iri) is None
        assert uri.display_id_sbol2(iri) is None
        assert uri.uri_prefix_sbol2(iri) is None
        assert uri.create_sbol3_uri(iri) == iri


def test_sbol3_decomposition_versioned():
    """SBOL 3 places the version before the displayId."""
    iri = "https://example.org/lab/1/foo"
    assert uri.namespace_sbol3(iri) == "https://example.org/lab"
    assert uri.version_sbol3(iri) == "1"
    assert uri.display_id_sbol3(iri) == "foo"


def test_sbol3_decomposition_unversioned():
    """An unversioned SBOL 3 IRI has an empty version."""
    iri = "https://example.org/lab/foo"
    assert uri.namespace_sbol3(iri) == "https://example.org/lab"
    assert uri.version_sbol3(iri) == ""
    assert uri.display_id_sbol3(iri) == "foo"


def test_round_trips_versioned():
    """create_sbol3_uri and create_sbol2_uri invert each other on versioned IRIs."""
    sbol2 = "https://synbiohub.org/public/igem/BBa_E0040/1"
    sbol3 = uri.create_sbol3_uri(sbol2)
    assert sbol3 == "https://synbiohub.org/public/igem/1/BBa_E0040"
    assert uri.create_sbol2_uri(sbol3) == sbol2


def test_round_trips_unversioned():
    """Unversioned IRIs are unchanged in both directions."""
    sbol2 = "https://example.org/lab/foo"
    sbol3 = uri.create_sbol3_uri(sbol2)
    assert sbol3 == "https://example.org/lab/foo"
    assert uri.create_sbol2_uri(sbol3) == sbol2


def test_iri_helpers():
    """last_segment, url_origin, and child IRI allocation."""
    assert uri.last_segment("https://example.org/lab/promoter") == "promoter"
    assert uri.last_segment("http://example.org/a#frag") == "frag"
    assert uri.last_segment("https://example.org/lab/") == "https://example.org/lab/"
    assert uri.url_origin("https://example.org/lab/x") == "https://example.org"
    assert uri.url_origin("urn:uuid:1234") == "urn:uuid"
    assert uri.url_origin("relative/path") is None
    used = {"https://example.org/c/a"}
    assert uri.next_available_child_iri("https://example.org/c", "a", used) == ("a_2", "https://example.org/c/a_2")
    assert uri.next_available_child_iri("https://example.org/c/", "b", used) == ("b", "https://example.org/c/b")
    assert "https://example.org/c/a_2" in used


def test_compare_versions():
    """Dotted versions compare numerically by segment, missing segments counting as zero."""
    assert compare_versions("1", "1.0") == 0
    assert compare_versions("2.10", "2.9") > 0
    assert compare_versions("1", "2") < 0
    assert compare_versions("1.a", "1.b") < 0


# Upgrade value maps


def test_orientation_upgrade():
    """SBOL 2 orientations become SO terms."""
    assert v.upgrade_value(S2.orientation, S2.inline) == v.SO_INLINE
    assert v.upgrade_value(S2.orientation, S2.reverseComplement) == v.SO_REVERSE_COMPLEMENT
    assert v.upgrade_value(S2.orientation, "http://example.org/custom") is None


def test_encoding_upgrade():
    """Legacy IUPAC encoding pages become EDAM formats."""
    assert v.upgrade_value(S2.encoding, "http://www.chem.qmul.ac.uk/iubmb/misc/naseq.html") == (
        "https://identifiers.org/edam:format_1207"
    )
    assert v.upgrade_value(S2.encoding, "http://www.chem.qmul.ac.uk/iupac/AminoAcid/") == (
        "https://identifiers.org/edam:format_1208"
    )
    assert v.upgrade_value(S2.encoding, "http://example.org/custom") is None


def test_biopax_to_sbo():
    """BioPAX types map to SBO terms."""
    assert v.BIOPAX_TO_SBO[v.BIOPAX + "Dna"] == "https://identifiers.org/SBO:0000251"
    assert v.BIOPAX_TO_SBO[v.BIOPAX + "Protein"] == "https://identifiers.org/SBO:0000252"
    assert "http://example.org/custom" not in v.BIOPAX_TO_SBO


def test_refinement_to_restriction():
    """MapsTo refinements map to Constraint restrictions; merge is treated as useRemote."""
    assert v.REFINEMENTS[S2.verifyIdentical] == S3.verifyIdentical
    assert v.REFINEMENTS[S2.useLocal] == S3.replaces
    assert v.REFINEMENTS[S2.useRemote] == S3.replaces
    assert v.REFINEMENTS[S2.merge] == S3.replaces
    assert "http://example.org/other" not in v.REFINEMENTS


def test_operator_to_cardinality():
    """VariableComponent operators become VariableFeature cardinalities."""
    for name in ("one", "zeroOrOne", "oneOrMore", "zeroOrMore"):
        assert v.upgrade_value(S2.operator, S2.base + name) == S3.base + name
    assert v.upgrade_value(S2.operator, "http://example.org/custom") is None


def test_strategy_and_role_integration_upgrade():
    """Strategy and roleIntegration values shift namespace."""
    assert v.upgrade_value(S2.strategy, S2.enumerate) == S3.enumerate
    assert v.upgrade_value(S2.strategy, S2.sample) == S3.sample
    assert v.upgrade_value(S2.strategy, "http://example.org/custom") is None
    assert v.upgrade_value(S2.roleIntegration, S2.mergeRoles) == S3.mergeRoles
    assert v.upgrade_value(S2.roleIntegration, S2.overrideRoles) == S3.overrideRoles
    assert v.upgrade_value(S2.roleIntegration, "http://example.org/custom") is None


def test_restriction_upgrade_only_known_values():
    """SequenceConstraint restrictions shift namespace; unknown ones pass through."""
    assert v.upgrade_value(S2.restriction, S2.precedes) == S3.precedes
    assert v.upgrade_value(S2.restriction, S2.unknownRelation) is None


# Downgrade value maps


def test_orientation_downgrade():
    """Both SBOL 3 and SO orientation spellings map back to SBOL 2."""
    assert v.downgrade_value(S3.orientation, S3.inline) == S2.inline
    assert v.downgrade_value(S3.orientation, v.SO_INLINE) == S2.inline
    assert v.downgrade_value(S3.orientation, S3.reverseComplement) == S2.reverseComplement
    assert v.downgrade_value(S3.orientation, "http://example.org/other") is None


def test_encoding_downgrade():
    """EDAM formats map back to the legacy IUPAC pages."""
    assert v.downgrade_value(S3.encoding, "https://identifiers.org/edam:format_1207") == (
        "http://www.chem.qmul.ac.uk/iubmb/misc/naseq.html"
    )
    assert v.downgrade_value(S3.encoding, "https://identifiers.org/edam:format_1208") == (
        "http://www.chem.qmul.ac.uk/iupac/AminoAcid/"
    )


def test_sbo_to_biopax_prefers_region_variant():
    """The downgrade picks the ``*Region`` BioPAX spelling."""
    assert v.SBO_TO_BIOPAX["https://identifiers.org/SBO:0000251"] == v.BIOPAX + "DnaRegion"


def test_restriction_namespace_shift():
    """Any SBOL 3 restriction keeps its local name in the SBOL 2 namespace."""
    assert v.downgrade_value(S3.restriction, S3.precedes) == S2.precedes
    assert v.downgrade_value(S3.restriction, S3.verifyIdentical) == S2.verifyIdentical
    assert v.downgrade_value(S3.restriction, "http://example.org/other") is None


def test_refinement_inference_is_position_aware():
    """``replaces`` means useRemote with the reference in subject, useLocal in object."""
    assert v.refinement_for(S3.replaces, cref_is_subject=True) == S2.useRemote
    assert v.refinement_for(S3.replaces, cref_is_subject=False) == S2.useLocal
    assert v.refinement_for(S3.verifyIdentical, cref_is_subject=True) == S2.verifyIdentical
    assert v.refinement_for(S3.verifyIdentical, cref_is_subject=False) == S2.verifyIdentical
    assert v.refinement_for("http://example.org/other", cref_is_subject=True) is None


def test_cardinality_strategy_role_integration_downgrade():
    """Cardinality, strategy, and roleIntegration map back to SBOL 2."""
    for name in ("one", "zeroOrOne", "oneOrMore", "zeroOrMore"):
        assert v.downgrade_value(S3.cardinality, S3.base + name) == S2.base + name
    assert v.downgrade_value(S3.cardinality, "http://example.org/other") is None
    assert v.downgrade_value(S3.strategy, S3.enumerate) == S2.enumerate
    assert v.downgrade_value(S3.strategy, S3.sample) == S2.sample
    assert v.downgrade_value(S3.roleIntegration, S3.mergeRoles) == S2.mergeRoles
    assert v.downgrade_value(S3.roleIntegration, S3.overrideRoles) == S2.overrideRoles
    assert v.downgrade_value(S3.roleIntegration, "http://example.org/other") is None


def test_sbol2_literal_canonicalization():
    """Literals of SBOL 2 model properties take the model's datatype; extension literals are untouched."""
    start = v.canonical_sbol2_literal(S2.start, Literal("07"))
    assert str(start) == "07" and str(start.datatype).endswith("#integer")
    assert v.canonical_sbol2_literal("http://purl.org/dc/terms/title", Literal("x", lang="en")) == Literal("x")
    assert v.canonical_sbol2_literal("http://example.org/note", Literal("x", lang="en")) == Literal("x", lang="en")


# Engine behavior

SBOL2_DOC = """<?xml version="1.0" ?>
<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#" xmlns:sbol="http://sbols.org/v2#"
         xmlns:dcterms="http://purl.org/dc/terms/">
  <sbol:ComponentDefinition rdf:about="https://example.org/lab/parts/promoter/1">
    <sbol:persistentIdentity rdf:resource="https://example.org/lab/parts/promoter"/>
    <sbol:displayId>promoter</sbol:displayId>
    <sbol:version>1</sbol:version>
    <dcterms:title>A promoter</dcterms:title>
    <sbol:type rdf:resource="http://www.biopax.org/release/biopax-level3.owl#DnaRegion"/>
    <sbol:role rdf:resource="http://identifiers.org/so/SO:0000167"/>
  </sbol:ComponentDefinition>
</rdf:RDF>
"""
PROMOTER_3 = URIRef("https://example.org/lab/parts/1/promoter")


def test_upgrade_moves_version_and_derives_namespace():
    """The version moves before the displayId and the SBOL 2 prefix becomes hasNamespace."""
    graph, report = upgrade(SBOL2_DOC)
    assert (PROMOTER_3, URIRef(S3.hasNamespace), URIRef("https://example.org/lab/parts")) in graph
    assert (PROMOTER_3, URIRef(S3.name), Literal("A promoter")) in graph
    assert (PROMOTER_3, URIRef(S3.role), URIRef("https://identifiers.org/SO:0000167")) in graph
    assert (PROMOTER_3, URIRef(BP.sbol2OriginalURI), URIRef("https://example.org/lab/parts/promoter/1")) in graph
    assert report.direction == "upgrade" and report.output_triples == len(graph)


def test_upgrade_namespaces_option_takes_priority():
    """A matching namespaces prefix (minus its trailing slash) wins over the derived namespace."""
    graph, _ = upgrade(SBOL2_DOC, UpgradeOptions(namespaces=["https://other.org/", "https://example.org/"]))
    assert set(graph.objects(PROMOTER_3, URIRef(S3.hasNamespace))) == {URIRef("https://example.org")}
    default, _ = upgrade(SBOL2_DOC, UpgradeOptions(namespaces=None))
    assert set(default.objects(PROMOTER_3, URIRef(S3.hasNamespace))) == {URIRef("https://example.org/lab/parts")}


def test_upgrade_without_backport():
    """preserve_backport=False writes no backport annotations."""
    graph, _ = upgrade(SBOL2_DOC, UpgradeOptions(preserve_backport=False))
    assert not any(str(p).startswith(BP.base) for p in graph.predicates())


def test_upgrade_rejects_non_sbol2():
    """A graph with triples but no SBOL 2 marker is not upgraded."""
    graph = Graph()
    graph.add((URIRef("https://example.org/x"), URIRef(S3.displayId), Literal("x")))
    with pytest.raises(ValueError):
        upgrade(graph)
    assert len(upgrade(Graph())[0]) == 0


def test_round_trip_restores_sbol2_identity():
    """Downgrading the upgrade restores the SBOL 2 identity, class, and vocabulary."""
    upgraded, _ = upgrade(SBOL2_DOC)
    sbol2, report = downgrade(upgraded)
    original = URIRef("https://example.org/lab/parts/promoter/1")
    assert (original, URIRef(S2.persistentIdentity), URIRef("https://example.org/lab/parts/promoter")) in sbol2
    assert (original, URIRef(S2.version), Literal("1")) in sbol2
    assert (original, URIRef("http://purl.org/dc/terms/title"), Literal("A promoter")) in sbol2
    assert (original, URIRef(S2.role), URIRef("http://identifiers.org/so/SO:0000167")) in sbol2
    assert not any(str(p).startswith(BP.base) or str(p).startswith(S3.base) for p in sbol2.predicates())
    assert report.direction == "downgrade"


def test_downgrade_default_version():
    """default_version versions unversioned top-levels and reports the synthesis."""
    sbol3 = Graph()
    component = URIRef("https://example.org/lab/promoter")
    sbol3.add((component, URIRef("http://www.w3.org/1999/02/22-rdf-syntax-ns#type"), URIRef(S3.Component)))
    sbol3.add((component, URIRef(S3.displayId), Literal("promoter")))
    sbol3.add((component, URIRef(S3.hasNamespace), URIRef("https://example.org/lab")))
    sbol2, report = downgrade(sbol3, DowngradeOptions(default_version="1"))
    versioned = URIRef("https://example.org/lab/promoter/1")
    assert (versioned, URIRef(S2.version), Literal("1")) in sbol2
    assert [w.kind for w in report.warnings] == ["SynthesizedVersion"]
    with pytest.raises(ValueError):
        downgrade(sbol3, DowngradeOptions(default_version=""))


VERSIONED_PROV_AND_MEASURE = """
@prefix sbol: <http://sbols.org/v2#> .
@prefix prov: <http://www.w3.org/ns/prov#> .
@prefix om: <http://www.ontology-of-units-of-measure.org/resource/om-2/> .
@prefix biopax: <http://www.biopax.org/release/biopax-level3.owl#> .

<https://example.org/lab/act/1> a prov:Activity ; sbol:displayId "act" ;
    sbol:persistentIdentity <https://example.org/lab/act> ; sbol:version "1" ;
    prov:qualifiedUsage <https://example.org/lab/act/use/1> ;
    prov:qualifiedAssociation <https://example.org/lab/act/assoc/1> .
<https://example.org/lab/act/use/1> a prov:Usage ; sbol:displayId "use" ;
    sbol:persistentIdentity <https://example.org/lab/act/use> ; sbol:version "1" ;
    prov:entity <https://example.org/lab/cd/1> ; prov:hadRole <http://sbols.org/v2#design> .
<https://example.org/lab/act/assoc/1> a prov:Association ; sbol:displayId "assoc" ;
    sbol:persistentIdentity <https://example.org/lab/act/assoc> ; sbol:version "1" ;
    prov:agent <https://example.org/lab/agent/1> .
<https://example.org/lab/agent/1> a prov:Agent ; sbol:displayId "agent" ;
    sbol:persistentIdentity <https://example.org/lab/agent> ; sbol:version "1" .
<https://example.org/lab/cd/1> a sbol:ComponentDefinition ; sbol:displayId "cd" ;
    sbol:persistentIdentity <https://example.org/lab/cd> ; sbol:version "1" ; sbol:type biopax:DnaRegion ;
    sbol:measure <https://example.org/lab/cd/mass/1> .
<https://example.org/lab/cd/mass/1> a om:Measure ; sbol:displayId "mass" ;
    sbol:persistentIdentity <https://example.org/lab/cd/mass> ; sbol:version "1" ;
    om:hasNumericalValue "1.5"^^<http://www.w3.org/2001/XMLSchema#float> ; om:hasUnit om:gram .
"""

FRAGMENT_SEQUENCE_ANNOTATION = """\
<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#" xmlns:sbol="http://sbols.org/v2#">
  <sbol:ComponentDefinition rdf:about="http://example.org#cd">
    <sbol:persistentIdentity rdf:resource="http://example.org#cd"/>
    <sbol:displayId>cd</sbol:displayId>
    <sbol:type rdf:resource="http://www.biopax.org/release/biopax-level3.owl#DnaRegion"/>
    <sbol:component>
      <sbol:Component rdf:about="http://example.org#cd/part">
        <sbol:persistentIdentity rdf:resource="http://example.org#cd/part"/>
        <sbol:displayId>part</sbol:displayId>
        <sbol:definition rdf:resource="http://example.org#part"/>
        <sbol:access rdf:resource="http://sbols.org/v2#public"/>
      </sbol:Component>
    </sbol:component>
    <sbol:sequenceAnnotation>
      <sbol:SequenceAnnotation rdf:about="http://example.org#anno">
        <sbol:persistentIdentity rdf:resource="http://example.org#anno"/>
        <sbol:displayId>anno</sbol:displayId>
        <sbol:component rdf:resource="http://example.org#cd/part"/>
        <sbol:location>
          <sbol:Range rdf:about="http://example.org#anno/range">
            <sbol:persistentIdentity rdf:resource="http://example.org#anno/range"/>
            <sbol:displayId>range</sbol:displayId>
            <sbol:start>1</sbol:start>
            <sbol:end>10</sbol:end>
          </sbol:Range>
        </sbol:location>
      </sbol:SequenceAnnotation>
    </sbol:sequenceAnnotation>
  </sbol:ComponentDefinition>
</rdf:RDF>"""


def test_versioned_prov_and_measure_children_nest_under_their_parent():
    """Usage, Association, and Measure children of versioned objects nest under the parent's SBOL 3 identity."""
    upgraded, _ = upgrade(VERSIONED_PROV_AND_MEASURE, fmt="turtle")
    subjects = {str(s) for s in upgraded.subjects()}
    for child in (
        "https://example.org/lab/1/act/use",
        "https://example.org/lab/1/act/assoc",
        "https://example.org/lab/1/cd/mass",
    ):
        assert child in subjects
    assert not validate_sbol3(upgraded, ValidationConfig(complete=False)).errors
    downgraded, _ = downgrade(upgraded)
    sbol2_subjects = {str(s) for s in downgraded.subjects()}
    for child in (
        "https://example.org/lab/act/use/1",
        "https://example.org/lab/act/assoc/1",
        "https://example.org/lab/cd/mass/1",
    ):
        assert child in sbol2_subjects


def test_fragment_style_sequence_annotation_downgrades_to_valid_iris():
    """A `#`-fragment SequenceAnnotation identity yields no displayId, so the rebuilt annotation is named instead."""
    upgraded, _ = upgrade(FRAGMENT_SEQUENCE_ANNOTATION, fmt="xml")
    downgraded, _ = downgrade(upgraded)
    assert all(str(s).count("#") <= 1 for s in downgraded.subjects())
    assert "SequenceAnnotation" in serialize(downgraded, "xml")


EXTENSION_OBJECTS_SBOL2 = """
@prefix sbol: <http://sbols.org/v2#> .
@prefix prov: <http://www.w3.org/ns/prov#> .
@prefix om: <http://www.ontology-of-units-of-measure.org/resource/om-2/> .
@prefix biopax: <http://www.biopax.org/release/biopax-level3.owl#> .
@prefix myapp: <http://myapp.org/> .

<https://example.org/lab/act> a prov:Activity ;
    sbol:displayId "act" ; sbol:persistentIdentity <https://example.org/lab/act> ;
    prov:qualifiedUsage <https://example.org/lab/act/use> .
<https://example.org/lab/act/use> a prov:Usage ;
    sbol:displayId "use" ; sbol:persistentIdentity <https://example.org/lab/act/use> ;
    prov:entity <https://example.org/lab/cd> .
<https://example.org/lab/sheet> a myapp:Datasheet ;
    sbol:displayId "sheet" ; sbol:persistentIdentity <https://example.org/lab/sheet> .
<https://example.org/lab/cd> a sbol:ComponentDefinition ;
    sbol:displayId "cd" ; sbol:persistentIdentity <https://example.org/lab/cd> ; sbol:type biopax:DnaRegion ;
    prov:wasGeneratedBy <https://example.org/lab/act> ;
    sbol:measure <https://example.org/lab/cd/mass> ;
    myapp:information <https://example.org/lab/cd/info> .
<https://example.org/lab/cd/mass> a om:Measure ;
    sbol:displayId "mass" ; sbol:persistentIdentity <https://example.org/lab/cd/mass> ;
    om:hasNumericalValue "1.5"^^<http://www.w3.org/2001/XMLSchema#float> ; om:hasUnit om:gram .
<https://example.org/lab/cd/info> a myapp:Information ; myapp:note "plain annotation" .
"""

EXTENSION_OBJECTS_SBOL3 = """
@prefix sbol: <http://sbols.org/v3#> .
@prefix prov: <http://www.w3.org/ns/prov#> .
@prefix ex: <http://example.org/vocab/> .

<https://example.org/lab/act> a sbol:TopLevel , prov:Activity ;
    sbol:displayId "act" ; sbol:hasNamespace <https://example.org/lab> ;
    prov:qualifiedUsage <https://example.org/lab/act/use> .
<https://example.org/lab/act/use> a sbol:Identified , prov:Usage ;
    sbol:displayId "use" ; prov:entity <https://example.org/lab/part> .
<https://example.org/lab/repository> a sbol:TopLevel , ex:Repository ;
    sbol:displayId "repository" ; sbol:hasNamespace <https://example.org/lab> .
<https://example.org/lab/part> a sbol:Component ;
    sbol:displayId "part" ; sbol:hasNamespace <https://example.org/lab> ;
    sbol:type <https://identifiers.org/SBO:0000251> ;
    prov:wasGeneratedBy <https://example.org/lab/act> ;
    ex:storedIn <https://example.org/lab/repository> ;
    ex:note <https://example.org/lab/part/note> .
<https://example.org/lab/part/note> a ex:Note ; ex:text "plain annotation" .
"""


def test_extension_objects_gain_sbol_marker_types():
    """PROV, OM, and custom-class objects with SBOL identity are typed TopLevel or Identified (SBOL 3.1.0 §6.11)."""
    upgraded, _ = upgrade(EXTENSION_OBJECTS_SBOL2, fmt="turtle")
    rdf_type = URIRef("http://www.w3.org/1999/02/22-rdf-syntax-ns#type")
    for iri, marker in (
        ("https://example.org/lab/act", S3.TopLevel),
        ("https://example.org/lab/sheet", S3.TopLevel),
        ("https://example.org/lab/act/use", S3.Identified),
        ("https://example.org/lab/cd/mass", S3.Identified),
    ):
        assert (URIRef(iri), rdf_type, URIRef(marker)) in upgraded, iri
    note_types = set(upgraded.objects(URIRef("https://example.org/lab/cd/info"), rdf_type))
    assert note_types == {URIRef("http://myapp.org/Information")}
    assert not validate_sbol3(upgraded, ValidationConfig(complete=False)).errors


def test_marked_extension_objects_survive_downgrade():
    """The downgrade keeps PROV and custom-class objects, dropping only their SBOL 3 marker types."""
    downgraded, report = downgrade(EXTENSION_OBJECTS_SBOL3, fmt="turtle")
    rdf_type = URIRef("http://www.w3.org/1999/02/22-rdf-syntax-ns#type")
    for iri, cls in (
        ("https://example.org/lab/act", "http://www.w3.org/ns/prov#Activity"),
        ("https://example.org/lab/act/use", "http://www.w3.org/ns/prov#Usage"),
        ("https://example.org/lab/repository", "http://example.org/vocab/Repository"),
    ):
        assert (URIRef(iri), rdf_type, URIRef(cls)) in downgraded, iri
    assert not any(str(term).startswith(S3.base) for triple in downgraded for term in triple)
    note = URIRef("https://example.org/lab/part/note")
    assert (note, URIRef(S2.persistentIdentity), None) not in downgraded
    assert not report.warnings
