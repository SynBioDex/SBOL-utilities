"""SBOL 3 -> SBOL 2 conversion."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

import rdflib

from sbol_utilities.convert.report import ConversionReport
from sbol_utilities.rdf_io import GraphSource


@dataclass
class DowngradeOptions:
    """Configuration for :func:`downgrade`."""

    #: sbol2:version for top-level objects whose SBOL 3 IRI carries no version segment; None leaves them unversioned
    default_version: Optional[str] = None


def downgrade(
    source: GraphSource, options: Optional[DowngradeOptions] = None, fmt: Optional[str] = None
) -> Tuple[rdflib.Graph, ConversionReport]:
    """Convert an SBOL 3 document to SBOL 2.

    :param source: an rdflib Graph, path, RDF text, or sbol3.Document holding SBOL 3
    :param options: conversion options
    :param fmt: RDF format of a path or text source, when it can't be inferred
    :return: the SBOL 2 graph and a report of non-fatal issues
    """
    raise NotImplementedError
