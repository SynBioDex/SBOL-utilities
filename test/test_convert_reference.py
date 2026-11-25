"""Differential check against the Java SynBioDex/SBOL-Converter reference.

SBOLTestSuite's ``Expected/conversion/sbolconverter/`` holds the reference converter's outputs for six of its inputs.
The Python converter must produce a logically equivalent graph from the same input. Equivalence content-addresses the
auto-generated ``Constraint<N>`` IRIs: the reference numbers them in Java HashSet iteration order, so the ordinal
carries no meaning.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

import pytest
from rdflib import Graph, URIRef

import conversion_goldens as cg
import sboltestsuite as suite
from sbol_utilities.convert import downgrade, upgrade
from sbol_utilities.rdf_io import load_graph

pytestmark = pytest.mark.sboltestsuite

#: reference output stem -> SBOLTestSuite source
UPGRADE_CASES = {
    "component_definition_output": "SBOL2/ComponentDefinitionOutput.xml",
    "module_definition_output": "SBOL2/ModuleDefinitionOutput.xml",
    "sequence_constraint_output": "SBOL2/SequenceConstraintOutput.xml",
    "repression_model": "SBOL2/RepressionModel.xml",
}
DOWNGRADE_CASES = {
    "bba_f2620": "SBOL3/BBa_F2620_PoPSReceiver/BBa_F2620_PoPSReceiver.ttl",
    "model": "SBOL3/entity/model/model.ttl",
}

GENERATED_CONSTRAINT = re.compile(r"^Constraint\d+$")
VOCABULARY_PREDICATES = (
    "http://sbols.org/v3#role",
    "http://sbols.org/v2#role",
    "http://sbols.org/v3#type",
    "http://sbols.org/v2#type",
)


def scheme_neutral_vocabulary(line: str) -> str:
    """Ignore the http/https scheme of role and type objects that are not identifiers.org terms.

    The reference converter toggles the scheme of every role and type IRI; this converter respells only
    identifiers.org ontology terms and keeps a lab's own vocabulary as written.
    """
    for predicate in VOCABULARY_PREDICATES:
        marker = f" <{predicate}> <"
        if marker in line:
            head, obj = line.split(marker, 1)
            if "://identifiers.org/" not in obj:
                obj = re.sub(r"^https?://", "//", obj)
            return f"{head}{marker}{obj}"
    return line


DISPLAY_ID_PREDICATES = {"http://sbols.org/v3#displayId", "http://sbols.org/v2#displayId"}


def logical_lines(graph: Graph) -> set[str]:
    """Canonical N-Triples with each generated Constraint<N> IRI replaced by a hash of its content."""
    renames: dict[str, str] = {}
    for subject in set(graph.subjects()):
        if isinstance(subject, URIRef) and GENERATED_CONSTRAINT.match(str(subject).rsplit("/", 1)[-1]):
            content = sorted(
                f"{p} {o.n3()}" for p, o in graph.predicate_objects(subject) if str(p) not in DISPLAY_ID_PREDICATES
            )
            digest = hashlib.sha256("\n".join(content).encode("utf-8")).hexdigest()[:16]
            renames[f"<{subject}>"] = f"<{str(subject).rsplit('/', 1)[0]}/Constraint#{digest}>"
    result = set()
    for line in map(scheme_neutral_vocabulary, cg.canonical_lines(graph)):
        for old, new in renames.items():
            line = line.replace(old, new)
        if renames and any(f" <{p}> " in line for p in DISPLAY_ID_PREDICATES) and "Constraint#" in line.split(" ")[0]:
            continue
        result.add(line)
    return result


def reference_directory(suite_root: Path) -> Path:
    """The directory of the reference converter's outputs."""
    return suite_root / suite.EXPECTED / "conversion" / "sbolconverter"


def assert_equivalent(ours: Graph, reference: Graph) -> None:
    """Assert two graphs hold the same statements, comparing generated Constraint identities by content."""
    difference = suite.set_diff(logical_lines(reference), logical_lines(ours))
    assert not difference, difference


@pytest.mark.parametrize("stem", sorted(UPGRADE_CASES))
def test_upgrade_matches_reference(stem, sbol_test_suite):
    """SBOL 2 -> 3 agrees with the reference converter."""
    source = load_graph(sbol_test_suite / UPGRADE_CASES[stem])
    reference = load_graph(reference_directory(sbol_test_suite) / f"{stem}.sbolconverter.to-sbol3.nt")
    ours, _ = upgrade(source)
    assert_equivalent(ours, reference)


@pytest.mark.parametrize("stem", sorted(DOWNGRADE_CASES))
def test_downgrade_matches_reference(stem, sbol_test_suite):
    """SBOL 3 -> 2 agrees with the reference converter."""
    source = load_graph(sbol_test_suite / DOWNGRADE_CASES[stem])
    reference = load_graph(reference_directory(sbol_test_suite) / f"{stem}.sbolconverter.to-sbol2.rdf")
    ours, _ = downgrade(source)
    assert_equivalent(ours, reference)
