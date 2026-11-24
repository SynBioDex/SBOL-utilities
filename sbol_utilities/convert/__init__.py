"""Pure-Python SBOL 2 ⇄ SBOL 3 conversion.

Conversion works directly on RDF triples and makes the same decisions as the SynBioDex/SBOL-Converter reference
(and sbol-rs): the same identities, class choices, vocabulary, and ``https://sbols.org/backport/2_3#`` round-trip
annotations.

    >>> from sbol_utilities.convert import upgrade, downgrade
    >>> sbol3_graph, report = upgrade("design_sbol2.xml")
    >>> sbol2_graph, report = downgrade(sbol3_graph)
"""

from __future__ import annotations

from sbol_utilities.convert.downgrade import DowngradeOptions, downgrade
from sbol_utilities.convert.report import ConversionReport, ConversionWarning
from sbol_utilities.convert.upgrade import UpgradeOptions, upgrade

__all__ = [
    "upgrade",
    "downgrade",
    "UpgradeOptions",
    "DowngradeOptions",
    "ConversionReport",
    "ConversionWarning",
]
