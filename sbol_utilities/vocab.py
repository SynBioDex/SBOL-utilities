"""Namespace IRIs shared by sbol_utilities.convert and sbol_utilities.validation.

Class- and predicate-level constants live with the code that uses them; this module holds only the namespaces and
the handful of terms both packages need.
"""

from __future__ import annotations

from rdflib import Namespace
from rdflib.namespace import RDF

SBOL2 = Namespace("http://sbols.org/v2#")
SBOL3 = Namespace("http://sbols.org/v3#")
PROV = Namespace("http://www.w3.org/ns/prov#")
OM = Namespace("http://www.ontology-of-units-of-measure.org/resource/om-2/")
DCTERMS = Namespace("http://purl.org/dc/terms/")
#: Conversion-provenance namespace of the SynBioDex/SBOL-Converter reference, also used by sbol-rs
BACKPORT = Namespace("https://sbols.org/backport/2_3#")
#: Backport namespace written by the sbolgraph converter
LEGACY_BACKPORT = Namespace("http://sboltools.org/backport#")

XSD_NS = "http://www.w3.org/2001/XMLSchema#"

TYPE = RDF.type

__all__ = ["SBOL2", "SBOL3", "PROV", "OM", "DCTERMS", "BACKPORT", "LEGACY_BACKPORT", "XSD_NS", "TYPE", "RDF"]
