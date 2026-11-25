"""Non-fatal conversion diagnostics."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import NamedTuple

import rdflib


class WarningKind(str, Enum):
    """What a conversion could not translate cleanly."""

    #: several source subjects map to one target identity
    IDENTITY_COLLISION = "IdentityCollision"
    #: a Location's Sequence could not be inferred from its Component
    LOCATION_WITHOUT_SEQUENCE = "LocationWithoutSequence"
    #: a top-level's namespace could not be derived from its identity
    NAMESPACE_FALLBACK = "NamespaceFallback"
    #: a ComponentReference no Constraint names
    ORPHAN_COMPONENT_REFERENCE = "OrphanComponentReference"
    #: an SBOL 2 SequenceAnnotation folded onto the SubComponent of the Component it refers to
    SEQUENCE_ANNOTATION_WITH_COMPONENT = "SequenceAnnotationWithComponent"
    #: an object without a version given the default one
    SYNTHESIZED_VERSION = "SynthesizedVersion"
    UNKNOWN_SBOL2_TYPE = "UnknownSbol2Type"
    #: a ComponentReference and Constraint pair lacking what a MapsTo needs
    UNRESOLVABLE_CONSTRAINT_TO_MAPS_TO = "UnresolvableConstraintToMapsTo"
    #: a MapsTo without a carrier, a local, or a remote
    UNRESOLVED_MAPS_TO = "UnresolvedMapsTo"
    UNSUPPORTED_REFINEMENT = "UnsupportedRefinement"
    #: an SBOL 3 class with no SBOL 2 equivalent
    UNSUPPORTED_SBOL3_TYPE = "UnsupportedSbol3Type"

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class ConversionWarning:
    """Something the conversion could not translate cleanly but chose not to fail on."""

    kind: WarningKind
    subject: str | None
    message: str

    def __str__(self) -> str:
        return f"{self.kind}: {self.subject or '<document>'}: {self.message}"


@dataclass
class ConversionReport:
    """Warnings and counts produced by one upgrade or downgrade."""

    #: ``"upgrade"`` or ``"downgrade"``
    direction: str
    warnings: list[ConversionWarning] = field(default_factory=list)
    #: number of input triples consumed and output triples produced
    input_triples: int = 0
    output_triples: int = 0

    def warn(self, kind: WarningKind, subject: object | None, message: str) -> None:
        """Record a warning."""
        self.warnings.append(ConversionWarning(kind, None if subject is None else str(subject), message))


class ConversionResult(NamedTuple):
    """What a conversion returns: the converted graph and the report of what it could not translate cleanly."""

    graph: rdflib.Graph
    report: ConversionReport
