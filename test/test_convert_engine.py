"""End-to-end behaviour of the upgrade and downgrade engines on small documents."""

from __future__ import annotations

import pytest
from rdflib import RDF, Graph, Literal, URIRef

from sbol_utilities.convert import DowngradeOptions, UpgradeOptions, WarningKind, downgrade, upgrade
from sbol_utilities.convert.terms import BP, S2, S3
from sbol_utilities.rdf_io import serialize
from sbol_utilities.validation import ValidationConfig, validate_sbol3
from sbol_utilities.vocab import DCTERMS_TITLE

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

PROMOTER_2 = URIRef("https://example.org/lab/parts/promoter/1")
PROMOTER_3 = URIRef("https://example.org/lab/parts/1/promoter")

UNVERSIONED_SBOL3 = """
@prefix sbol: <http://sbols.org/v3#> .
<https://example.org/lab/promoter> a sbol:Component ;
    sbol:displayId "promoter" ; sbol:hasNamespace <https://example.org/lab> .
"""


@pytest.fixture(scope="module")
def upgraded_promoter():
    """The upgrade of :data:`SBOL2_DOC` and its report."""
    return upgrade(SBOL2_DOC)


def test_upgrade_moves_version_and_derives_namespace(upgraded_promoter):
    """The version moves before the displayId and the SBOL 2 prefix becomes hasNamespace."""
    graph, report = upgraded_promoter
    assert (PROMOTER_3, URIRef(S3.hasNamespace), URIRef("https://example.org/lab/parts")) in graph
    assert (PROMOTER_3, URIRef(S3.name), Literal("A promoter")) in graph
    assert (PROMOTER_3, URIRef(S3.role), URIRef("https://identifiers.org/SO:0000167")) in graph
    assert (PROMOTER_3, URIRef(BP.sbol2OriginalURI), PROMOTER_2) in graph


def test_upgrade_report(upgraded_promoter):
    graph, report = upgraded_promoter
    assert report.direction == "upgrade"
    assert report.output_triples == len(graph)
    assert not report.warnings


@pytest.mark.parametrize(
    "namespaces, expected",
    [
        (["https://other.org/", "https://example.org/"], "https://example.org"),
        (None, "https://example.org/lab/parts"),
    ],
    ids=["matching-prefix", "derived"],
)
def test_upgrade_namespaces_option(namespaces, expected):
    """A matching namespaces prefix (minus its trailing slash) wins over the derived namespace."""
    graph, _ = upgrade(SBOL2_DOC, UpgradeOptions(namespaces=namespaces))
    assert set(graph.objects(PROMOTER_3, URIRef(S3.hasNamespace))) == {URIRef(expected)}


def test_upgrade_without_backport():
    """preserve_backport=False writes no backport annotations."""
    graph, _ = upgrade(SBOL2_DOC, UpgradeOptions(preserve_backport=False))
    assert not any(str(p).startswith(BP.base) for p in graph.predicates())


def test_upgrade_rejects_non_sbol2():
    """A graph with triples but no SBOL 2 marker is not upgraded."""
    graph = Graph()
    graph.add((URIRef("https://example.org/x"), URIRef(S3.displayId), Literal("x")))
    with pytest.raises(ValueError, match="no SBOL 2"):
        upgrade(graph)


def test_upgrade_of_an_empty_graph_is_empty():
    assert len(upgrade(Graph()).graph) == 0


def test_round_trip_restores_sbol2_identity(upgraded_promoter):
    """Downgrading the upgrade restores the SBOL 2 identity, class, and vocabulary."""
    sbol2, report = downgrade(upgraded_promoter.graph)
    assert (PROMOTER_2, URIRef(S2.persistentIdentity), URIRef("https://example.org/lab/parts/promoter")) in sbol2
    assert (PROMOTER_2, URIRef(S2.version), Literal("1")) in sbol2
    assert (PROMOTER_2, URIRef(DCTERMS_TITLE), Literal("A promoter")) in sbol2
    assert (PROMOTER_2, URIRef(S2.role), URIRef("http://identifiers.org/so/SO:0000167")) in sbol2
    assert not any(str(p).startswith((BP.base, S3.base)) for p in sbol2.predicates())
    assert report.direction == "downgrade"


def test_downgrade_default_version():
    """default_version versions unversioned top-levels and reports the synthesis."""
    sbol2, report = downgrade(UNVERSIONED_SBOL3, DowngradeOptions(default_version="1"), fmt="turtle")
    assert (URIRef("https://example.org/lab/promoter/1"), URIRef(S2.version), Literal("1")) in sbol2
    assert [warning.kind for warning in report.warnings] == [WarningKind.SYNTHESIZED_VERSION]


def test_downgrade_rejects_an_empty_default_version():
    with pytest.raises(ValueError, match="default_version"):
        downgrade(UNVERSIONED_SBOL3, DowngradeOptions(default_version=""), fmt="turtle")


def test_versioned_prov_and_measure_children_nest_under_their_parent():
    """Usage, Association, and Measure children of versioned objects nest under the parent's SBOL 3 identity."""
    upgraded, _ = upgrade(VERSIONED_PROV_AND_MEASURE, fmt="turtle")
    assert {str(s) for s in upgraded.subjects()} >= {
        "https://example.org/lab/1/act/use",
        "https://example.org/lab/1/act/assoc",
        "https://example.org/lab/1/cd/mass",
    }
    assert not validate_sbol3(upgraded, ValidationConfig(complete=False)).errors
    downgraded, _ = downgrade(upgraded)
    assert {str(s) for s in downgraded.subjects()} >= {
        "https://example.org/lab/act/use/1",
        "https://example.org/lab/act/assoc/1",
        "https://example.org/lab/cd/mass/1",
    }


def test_fragment_style_sequence_annotation_downgrades_to_valid_iris():
    """A `#`-fragment SequenceAnnotation identity yields no displayId, so the rebuilt annotation is named instead."""
    upgraded, _ = upgrade(FRAGMENT_SEQUENCE_ANNOTATION, fmt="xml")
    downgraded, _ = downgrade(upgraded)
    assert all(str(s).count("#") <= 1 for s in downgraded.subjects())
    assert "SequenceAnnotation" in serialize(downgraded, "xml")


@pytest.fixture(scope="module")
def upgraded_extension_objects():
    """The upgrade of :data:`EXTENSION_OBJECTS_SBOL2`."""
    return upgrade(EXTENSION_OBJECTS_SBOL2, fmt="turtle").graph


@pytest.mark.parametrize(
    "iri, marker",
    [
        ("https://example.org/lab/act", S3.TopLevel),
        ("https://example.org/lab/sheet", S3.TopLevel),
        ("https://example.org/lab/act/use", S3.Identified),
        ("https://example.org/lab/cd/mass", S3.Identified),
    ],
)
def test_extension_objects_gain_sbol_marker_types(upgraded_extension_objects, iri, marker):
    """PROV, OM, and custom-class objects with SBOL identity are typed TopLevel or Identified (SBOL 3.1.0 §6.11)."""
    assert (URIRef(iri), RDF.type, URIRef(marker)) in upgraded_extension_objects


def test_plain_annotations_gain_no_marker_type(upgraded_extension_objects):
    note_types = set(upgraded_extension_objects.objects(URIRef("https://example.org/lab/cd/info"), RDF.type))
    assert note_types == {URIRef("http://myapp.org/Information")}


def test_upgraded_extension_objects_are_valid(upgraded_extension_objects):
    assert not validate_sbol3(upgraded_extension_objects, ValidationConfig(complete=False)).errors


def test_marked_extension_objects_survive_downgrade():
    """The downgrade keeps PROV and custom-class objects, dropping only their SBOL 3 marker types."""
    downgraded, report = downgrade(EXTENSION_OBJECTS_SBOL3, fmt="turtle")
    for iri, cls in (
        ("https://example.org/lab/act", "http://www.w3.org/ns/prov#Activity"),
        ("https://example.org/lab/act/use", "http://www.w3.org/ns/prov#Usage"),
        ("https://example.org/lab/repository", "http://example.org/vocab/Repository"),
    ):
        assert (URIRef(iri), RDF.type, URIRef(cls)) in downgraded, iri
    assert not any(str(term).startswith(S3.base) for triple in downgraded for term in triple)
    assert (URIRef("https://example.org/lab/part/note"), URIRef(S2.persistentIdentity), None) not in downgraded
    assert not report.warnings
