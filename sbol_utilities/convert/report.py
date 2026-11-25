"""Non-fatal conversion diagnostics."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ConversionWarning:
    """Something the conversion could not translate cleanly but chose not to fail on."""

    #: machine-readable kind, e.g. ``NamespaceFallback``, ``UnresolvedMapsTo``, ``UnsupportedRefinement``
    kind: str
    subject: str | None
    message: str

    def __str__(self) -> str:
        return f"{self.kind}: {self.subject or '<document>'}: {self.message}"


@dataclass
class ConversionReport:
    """Warnings and counts produced by one upgrade or downgrade."""

    direction: str
    warnings: list[ConversionWarning] = field(default_factory=list)
    #: number of input triples consumed and output triples produced
    input_triples: int = 0
    output_triples: int = 0

    def warn(self, kind: str, subject: object | None, message: str) -> None:
        """Record a warning."""
        self.warnings.append(ConversionWarning(kind, None if subject is None else str(subject), message))
