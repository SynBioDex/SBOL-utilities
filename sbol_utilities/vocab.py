"""Namespace IRIs and RDF terms shared by sbol_utilities.convert and sbol_utilities.validation.

Each namespace is available as a plain string (``SBOL2_NS``), for code that works with IRIs as text, and as an rdflib
``Namespace`` (``SBOL2``), for code that works with graph terms. Class- and predicate-level constants live with the
code that uses them.
"""

from __future__ import annotations

from rdflib import Namespace
from rdflib.namespace import RDF

SBOL2_NS = "http://sbols.org/v2#"
SBOL3_NS = "http://sbols.org/v3#"
PROV_NS = "http://www.w3.org/ns/prov#"
OM_NS = "http://www.ontology-of-units-of-measure.org/resource/om-2/"
DCTERMS_NS = "http://purl.org/dc/terms/"
RDFS_NS = "http://www.w3.org/2000/01/rdf-schema#"
XSD_NS = "http://www.w3.org/2001/XMLSchema#"
#: Conversion-provenance namespace of the SynBioDex/SBOL-Converter reference, also used by sbol-rs
BACKPORT_NS = "https://sbols.org/backport/2_3#"
#: Backport namespace written by the sbolgraph converter
LEGACY_BACKPORT_NS = "http://sboltools.org/backport#"

SBOL2 = Namespace(SBOL2_NS)
SBOL3 = Namespace(SBOL3_NS)
PROV = Namespace(PROV_NS)
OM = Namespace(OM_NS)
DCTERMS = Namespace(DCTERMS_NS)
BACKPORT = Namespace(BACKPORT_NS)
LEGACY_BACKPORT = Namespace(LEGACY_BACKPORT_NS)

#: rdf:type as a graph term and as text
TYPE = RDF.type
RDF_TYPE = str(RDF.type)

DCTERMS_TITLE = DCTERMS_NS + "title"
DCTERMS_DESCRIPTION = DCTERMS_NS + "description"
RDFS_LABEL = RDFS_NS + "label"
RDFS_COMMENT = RDFS_NS + "comment"

XSD_STRING = XSD_NS + "string"
XSD_BOOLEAN = XSD_NS + "boolean"
#: datatype of every language-tagged literal (RDF 1.1)
RDF_LANG_STRING = str(RDF.langString)
