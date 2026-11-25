"""The registry the SBOL 3 rule implementations register with."""

from __future__ import annotations

from sbol_utilities.validation.catalog import Registry
from sbol_utilities.validation.sbol3.context import Sbol3Context

REGISTRY: Registry[Sbol3Context] = Registry(3)
