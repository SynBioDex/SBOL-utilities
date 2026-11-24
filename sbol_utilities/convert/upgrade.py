"""SBOL 2 -> SBOL 3 conversion."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

import rdflib

from sbol_utilities.convert.report import ConversionReport
from sbol_utilities.rdf_io import GraphSource


@dataclass
class UpgradeOptions:
    """Configuration for :func:`upgrade`."""

    #: hasNamespace for top-level objects whose namespace cannot be derived from the input
    default_namespace: Optional[str] = None
    #: write https://sbols.org/backport/2_3# annotations so a later downgrade can rebuild the SBOL 2 shape
    preserve_backport: bool = True


def upgrade(
    source: GraphSource, options: Optional[UpgradeOptions] = None, fmt: Optional[str] = None
) -> Tuple[rdflib.Graph, ConversionReport]:
    """Convert an SBOL 2 document to SBOL 3.

    :param source: an rdflib Graph, path, RDF text, or sbol2.Document holding SBOL 2
    :param options: conversion options
    :param fmt: RDF format of a path or text source, when it can't be inferred
    :return: the SBOL 3 graph and a report of non-fatal issues
    """
    raise NotImplementedError
