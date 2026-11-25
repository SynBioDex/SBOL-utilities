"""The registry the SBOL 2 rule implementations register with."""

from __future__ import annotations

from sbol_utilities.validation.catalog import Registry
from sbol_utilities.validation.sbol2.context import Sbol2Context

REGISTRY: Registry[Sbol2Context] = Registry(2)
