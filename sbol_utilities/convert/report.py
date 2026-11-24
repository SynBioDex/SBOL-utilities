"""Non-fatal conversion diagnostics."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass(frozen=True)
class ConversionWarning:
    """Something the conversion could not translate cleanly but chose not to fail on."""

    #: machine-readable kind, e.g. ``NamespaceFallback``, ``UnresolvedMapsTo``, ``UnsupportedRefinement``
    kind: str
    subject: Optional[str]
    message: str

    def __str__(self) -> str:
        return f"{self.kind}: {self.subject or '<document>'}: {self.message}"


@dataclass
class ConversionReport:
    """Warnings and counts produced by one upgrade or downgrade."""

    direction: str
    warnings: List[ConversionWarning] = field(default_factory=list)
    #: number of input triples consumed and output triples produced
    input_triples: int = 0
    output_triples: int = 0

    def warn(self, kind: str, subject: Optional[object], message: str) -> None:
        """Record a warning."""
        self.warnings.append(ConversionWarning(kind, None if subject is None else str(subject), message))
