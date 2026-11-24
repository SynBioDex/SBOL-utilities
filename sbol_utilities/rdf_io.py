"""RDF loading, serialization, and SBOL version detection shared by sbol_utilities.convert and .validation.

Every entry point in those packages accepts any of: an ``rdflib.Graph``, a filesystem path, RDF text, a pySBOL3
``sbol3.Document`` or a pySBOL2 ``sbol2.Document``. This module normalizes all of them to an ``rdflib.Graph``.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Optional, Union

import rdflib
import sbol2
import sbol3

SBOL2_NS = "http://sbols.org/v2#"
SBOL3_NS = "http://sbols.org/v3#"

#: rdflib format names keyed by file extension
EXTENSION_FORMATS = {
    ".ttl": "turtle",
    ".nt": "nt",
    ".nt11": "nt",
    ".xml": "xml",
    ".rdf": "xml",
    ".jsonld": "json-ld",
    ".json": "json-ld",
}

#: user-facing format aliases accepted by the public API, mapped to rdflib format names
FORMAT_ALIASES = {
    "turtle": "turtle",
    "ttl": "turtle",
    "ntriples": "nt",
    "nt": "nt",
    "n-triples": "nt",
    "sorted nt": "nt",
    "rdfxml": "xml",
    "rdf-xml": "xml",
    "xml": "xml",
    "jsonld": "json-ld",
    "json-ld": "json-ld",
}

GraphSource = Union[rdflib.Graph, str, "os.PathLike[str]", Any]


def rdflib_format(fmt: Optional[str]) -> Optional[str]:
    """Map a user-facing format name to an rdflib parser/serializer name; ``None`` passes through."""
    if fmt is None:
        return None
    try:
        return FORMAT_ALIASES[fmt.lower()]
    except KeyError:
        raise ValueError(f"Unknown RDF format {fmt!r}; expected one of {sorted(set(FORMAT_ALIASES))}") from None


def guess_format(path: Union[str, "os.PathLike[str]"]) -> str:
    """Infer an rdflib format from a file extension, defaulting to RDF/XML (the SBOL 2 exchange format)."""
    return EXTENSION_FORMATS.get(Path(path).suffix.lower(), "xml")


def _sniff_text_format(text: str) -> str:
    stripped = text.lstrip()
    if stripped.startswith("<?xml") or stripped.startswith("<rdf:RDF") or stripped.startswith("<RDF"):
        return "xml"
    if stripped.startswith("{") or stripped.startswith("["):
        return "json-ld"
    if stripped.startswith("@prefix") or stripped.startswith("PREFIX") or stripped.startswith("@base"):
        return "turtle"
    return "nt" if stripped.startswith("<") else "turtle"


def load_graph(source: GraphSource, fmt: Optional[str] = None) -> rdflib.Graph:
    """Load an SBOL document from any supported source into an rdflib Graph.

    :param source: an rdflib Graph (returned as-is), a path, RDF text, an sbol3.Document, or an sbol2.Document
    :param fmt: RDF format of a path or text source; inferred from the extension or content when omitted
    :return: the document's triples
    """
    if isinstance(source, rdflib.Graph):
        return source
    fmt = rdflib_format(fmt)
    if isinstance(source, sbol3.Document):
        return source.graph()
    if isinstance(source, sbol2.Document):
        return rdflib.Graph().parse(data=source.writeString(), format="xml")
    if isinstance(source, os.PathLike) or (isinstance(source, str) and "\n" not in source and os.path.exists(source)):
        path = Path(source)
        return rdflib.Graph().parse(str(path), format=fmt or guess_format(path))
    if isinstance(source, str):
        return rdflib.Graph().parse(data=source, format=fmt or _sniff_text_format(source))
    raise TypeError(f"Cannot load an SBOL graph from {type(source).__name__}")


def detect_sbol_version(graph: rdflib.Graph) -> Optional[int]:
    """Return 3 or 2 according to which SBOL namespace the document's rdf:type statements use, or None.

    A graph that types subjects in both namespaces is reported as SBOL 3 only when it has more SBOL 3 typed
    subjects than SBOL 2 ones.
    """
    v2 = v3 = 0
    for _, _, o in graph.triples((None, rdflib.RDF.type, None)):
        value = str(o)
        if value.startswith(SBOL3_NS):
            v3 += 1
        elif value.startswith(SBOL2_NS):
            v2 += 1
    if not v2 and not v3:
        return None
    return 3 if v3 > v2 else 2


def serialize(graph: rdflib.Graph, fmt: str = "turtle") -> str:
    """Serialize a graph to text in a user-facing or rdflib format name."""
    result = graph.serialize(format=rdflib_format(fmt) or "turtle")
    return result.decode("utf-8") if isinstance(result, bytes) else result


def to_sbol3_document(graph: rdflib.Graph) -> sbol3.Document:
    """Load a graph holding SBOL 3 triples into a pySBOL3 Document."""
    doc = sbol3.Document()
    doc.read_string(serialize(graph, "nt"), sbol3.NTRIPLES)
    return doc


def to_sbol2_document(graph: rdflib.Graph) -> sbol2.Document:
    """Load a graph holding SBOL 2 triples into a pySBOL2 Document."""
    doc = sbol2.Document()
    doc.readString(serialize(graph, "xml"))
    return doc
