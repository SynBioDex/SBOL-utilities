"""Canonical graph fingerprints, and access to the sbol-rs conversion goldens.

``test/test_files/sbol_rs_golden/conversion.json`` (written by ``tools/generate_sbol_rs_goldens.py``) records, for
each corpus file, the SHA-256 of sbol-rs's conversion output as a canonical N-Triples set. Comparing fingerprints
checks that the Python converter produces the same graph as sbol-rs without redistributing converted corpus content.
"""

from __future__ import annotations

import hashlib
import json
from functools import lru_cache
from pathlib import Path
from typing import List

from rdflib import Graph
from rdflib.compare import to_canonical_graph

GOLDEN = Path(__file__).resolve().parent / "test_files" / "sbol_rs_golden" / "conversion.json"


def canonical_lines(graph: Graph) -> List[str]:
    """Sorted N-Triples lines of a graph with blank nodes canonically relabeled."""
    canonical = to_canonical_graph(graph)
    text = canonical.serialize(format="nt")
    if isinstance(text, bytes):
        text = text.decode("utf-8")
    return sorted(line for line in text.splitlines() if line.strip())


def fingerprint(graph: Graph) -> str:
    """SHA-256 over a graph's canonical N-Triples lines."""
    digest = hashlib.sha256()
    for line in canonical_lines(graph):
        digest.update(line.encode("utf-8"))
        digest.update(b"\n")
    return digest.hexdigest()


@lru_cache(maxsize=None)
def goldens() -> dict:
    """The parsed conversion golden file."""
    return json.loads(GOLDEN.read_text(encoding="utf-8"))
