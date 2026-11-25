"""Offline ontology facts used by SBOL validation.

The snapshot (``Ontology/ontology_facts.tsv`` in SynBioDex/SBOLTestSuite) covers EDAM, SBO, SO, GO, ChEBI, and the
Cell Ontology. Terms are accepted as identifiers.org IRIs, OBO PURLs, EDAM/biomodels IRIs, or compact ids, and are
normalized to compact ids (``SO:0000167``). Query methods return ``None`` when a term is absent from the snapshot,
so callers can tell "known and wrong" from "unknown".

TSV rows:

* ``term  id  iri  label  aliases  parents  ontology  role  component_family  sequence_family  table1  table2``
* ``branch  id  root`` -- ``id`` lies in the branch rooted at ``root``
* ``compat  encoding  component_type`` -- Sequence encoding compatible with Component type
* ``conflict  left  right`` -- terms that must not co-occur
* ``component_role  id`` -- additional Component role term
* ``component_role_compat  role  component_type``
* ``participation_compat  interaction_type  participation_role``
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from sbol_utilities.validation.runtime_data import runtime_file

FORMAT_VERSION = 1

SEQUENCE_ENCODING = "sequence_encoding"
COMPONENT_TYPE = "component_type"
COMPONENT_TYPE_MODIFIER = "component_type_modifier"
INTERACTION_TYPE = "interaction_type"
PARTICIPATION_ROLE = "participation_role"
FEATURE_ROLE = "feature_role"

NUCLEIC_ACID = "nucleic_acid"
PROTEIN = "protein"
SIMPLE_CHEMICAL = "simple_chemical"

SEQUENCE_FEATURE_ROOT = "SO:0000110"
MOLECULAR_FUNCTION_ROOT = "GO:0003674"
CHEBI_ROLE_ROOT = "CHEBI:50906"
CELL_ROOT = "CL:0000000"

_PREFIXES = {"EDAM": "EDAM", "SBO": "SBO", "SO": "SO", "GO": "GO", "CHEBI": "CHEBI", "CL": "CL", "NCIT": "NCIT"}


def normalize_term_id(value: str) -> str | None:
    """Return the compact ontology id for a supported IRI, PURL, or compact id, or None."""

    def prefixed(prefix: str, local: str) -> str | None:
        canonical = _PREFIXES.get(prefix.upper())
        return f"{canonical}:{local}" if canonical else None

    if ":" in value and not value.startswith(("http://", "https://")):
        prefix, local = value.split(":", 1)
        return prefixed(prefix, local)
    for base in ("https://identifiers.org/", "http://identifiers.org/"):
        if value.startswith(base):
            rest = value[len(base) :]
            if ":" not in rest:
                return None
            prefix, local = rest.split(":", 1)
            return prefixed(prefix, local)
    if value.startswith("http://edamontology.org/"):
        return "EDAM:" + value[len("http://edamontology.org/") :]
    for base in ("http://biomodels.net/SBO/SBO_", "https://biomodels.net/SBO/SBO_"):
        if value.startswith(base):
            return "SBO:" + value[len(base) :]
    if value.startswith("http://purl.obolibrary.org/obo/"):
        local = value[len("http://purl.obolibrary.org/obo/") :]
        if "_" not in local:
            return None
        prefix, suffix = local.split("_", 1)
        return prefixed(prefix, suffix)
    return None


@dataclass(frozen=True)
class TermFact:
    """Classification of one ontology term."""

    iri: str
    parents: tuple[str, ...]
    namespace: str
    role: str
    component_family: str | None
    sequence_family: str | None
    table_1_sequence_encoding: bool
    table_2_component_type: bool


def _optional(value: str) -> str | None:
    return None if value in ("", "-") else value


def _ordered(left: str, right: str) -> tuple[str, str]:
    return (left, right) if left <= right else (right, left)


class Ontology:
    """Query surface over an ontology fact snapshot."""

    def __init__(self) -> None:
        self.terms: dict[str, TermFact] = {}
        self.aliases: dict[str, str] = {}
        self.branches: set[tuple[str, str]] = set()
        self.compatibilities: set[tuple[str, str]] = set()
        self.conflicts: set[tuple[str, str]] = set()
        self.component_role_terms: set[str] = set()
        self.component_role_compatibilities: set[tuple[str, str]] = set()
        self.participation_compatibilities: set[tuple[str, str]] = set()
        self._ancestors: dict[str, frozenset] = {}

    @classmethod
    def from_tsv(cls, text: str) -> Ontology:
        """Parse an ontology facts TSV (the SBOLTestSuite ``Ontology/ontology_facts.tsv`` format)."""
        ontology = cls()
        version_seen = False
        for line in text.splitlines():
            if not line:
                continue
            if line.startswith("#"):
                if line.startswith("# format_version:"):
                    version = int(line.split(":", 1)[1])
                    if version != FORMAT_VERSION:
                        raise ValueError(f"Unsupported ontology facts format_version {version}")
                    version_seen = True
                continue
            columns = line.split("\t")
            kind = columns[0]
            if kind == "term":
                term_id, iri, _label, aliases, parents = columns[1:6]
                ontology.terms[term_id] = TermFact(
                    iri=iri,
                    parents=tuple(p for p in parents.split("|") if p and p != "-"),
                    namespace=columns[6],
                    role=columns[7],
                    component_family=_optional(columns[8]),
                    sequence_family=_optional(columns[9]),
                    table_1_sequence_encoding=columns[10] == "true",
                    table_2_component_type=columns[11] == "true",
                )
                ontology.aliases[iri] = term_id
                for alias in aliases.split("|"):
                    if alias and alias != "-":
                        ontology.aliases[alias] = term_id
            elif kind == "branch":
                ontology.branches.add((columns[1], columns[2]))
            elif kind == "compat":
                ontology.compatibilities.add((columns[1], columns[2]))
            elif kind == "conflict":
                ontology.conflicts.add(_ordered(columns[1], columns[2]))
            elif kind == "component_role":
                ontology.component_role_terms.add(columns[1])
            elif kind == "component_role_compat":
                ontology.component_role_compatibilities.add((columns[1], columns[2]))
            elif kind == "participation_compat":
                ontology.participation_compatibilities.add((columns[1], columns[2]))
            else:
                raise ValueError(f"Unknown ontology fact kind {kind!r}")
        if not version_seen:
            raise ValueError("Ontology facts TSV is missing its '# format_version:' header")
        return ontology

    # --- identity ---

    def canonical_id(self, term: str) -> str | None:
        """Compact canonical id for a known term, or None."""
        term = str(term)
        if term in self.aliases:
            return self.aliases[term]
        candidate = normalize_term_id(term)
        return candidate if candidate in self.terms else None

    def fact(self, term: str) -> TermFact | None:
        """Classification of a known term, or None."""
        canonical = self.canonical_id(term)
        return self.terms.get(canonical) if canonical else None

    def canonical_iri(self, term: str) -> str | None:
        """Preferred SBOL-facing IRI of a known term."""
        fact = self.fact(term)
        return fact.iri if fact else None

    def canonicalize(self, term: str) -> str:
        """The preferred IRI of a known term; any other term as given."""
        return self.canonical_iri(term) or str(term)

    def contains_term(self, term: str) -> bool:
        """Whether the term is in the snapshot."""
        return self.canonical_id(term) is not None

    def namespace(self, term: str) -> str | None:
        """Source ontology (EDAM, SBO, SO, GO, CHEBI, CL) of a known term."""
        fact = self.fact(term)
        return fact.namespace if fact else None

    def term_role(self, term: str) -> str | None:
        """SBOL-facing role of a known term."""
        fact = self.fact(term)
        return fact.role if fact else None

    # --- role predicates ---

    def _role_is(self, term: str, *roles: str) -> bool | None:
        role = self.term_role(term)
        return None if role is None else role in roles

    def is_sequence_encoding_term(self, term: str) -> bool | None:
        """Whether a known term is a Sequence encoding."""
        return self._role_is(term, SEQUENCE_ENCODING)

    def is_component_type_term(self, term: str) -> bool | None:
        """Whether a known term may be a Component type (including topology/strand modifiers)."""
        return self._role_is(term, COMPONENT_TYPE, COMPONENT_TYPE_MODIFIER)

    def is_feature_role_term(self, term: str) -> bool | None:
        """Whether a known term may be a Feature role."""
        return self._role_is(term, FEATURE_ROLE)

    def is_component_role_term(self, term: str) -> bool | None:
        """Whether a known term may be a Component role."""
        canonical = self.canonical_id(term)
        if canonical is None:
            return None
        if canonical in self.component_role_terms:
            return True
        return self.terms[canonical].role == FEATURE_ROLE

    def is_sequence_feature_role_term(self, term: str) -> bool | None:
        """Whether a known term lies in the SO sequence_feature branch."""
        return self.in_branch_if_known(term, SEQUENCE_FEATURE_ROOT)

    def is_cell_type_term(self, term: str) -> bool | None:
        """Whether a known term is a Cell Ontology cell type."""
        return self.in_branch_if_known(term, CELL_ROOT)

    def is_interaction_type_term(self, term: str) -> bool | None:
        """Whether a known term may be an Interaction type."""
        return self._role_is(term, INTERACTION_TYPE)

    def is_participation_role_term(self, term: str) -> bool | None:
        """Whether a known term may be a Participation role."""
        return self._role_is(term, PARTICIPATION_ROLE)

    def is_table_1_sequence_encoding(self, term: str) -> bool:
        """Whether the term is one of the encodings listed in SBOL 3 Table 1."""
        fact = self.fact(term)
        return bool(fact and fact.table_1_sequence_encoding)

    def is_table_2_component_type(self, term: str) -> bool:
        """Whether the term is one of the Component types listed in SBOL 3 Table 2."""
        fact = self.fact(term)
        return bool(fact and fact.table_2_component_type)

    # --- hierarchy ---

    def _ancestor_set(self, term_id: str) -> frozenset:
        cached = self._ancestors.get(term_id)
        if cached is not None:
            return cached
        result: set[str] = set()
        stack: list[str] = list(self.terms[term_id].parents) if term_id in self.terms else []
        while stack:
            parent = stack.pop()
            if parent in result:
                continue
            result.add(parent)
            if parent in self.terms:
                stack.extend(self.terms[parent].parents)
        frozen = frozenset(result)
        self._ancestors[term_id] = frozen
        return frozen

    def is_descendant(self, term: str, ancestor: str) -> bool:
        """Whether ``term`` strictly descends from ``ancestor``."""
        t, a = self.canonical_id(term), self.canonical_id(ancestor)
        return bool(t and a and t != a and a in self._ancestor_set(t))

    def is_equivalent_or_descendant(self, term: str, ancestor: str) -> bool:
        """Whether ``term`` equals or descends from ``ancestor``."""
        t, a = self.canonical_id(term), self.canonical_id(ancestor)
        return bool(t and a and (t == a or a in self._ancestor_set(t)))

    def is_in_branch(self, term: str, branch_root: str) -> bool:
        """Whether ``term`` lies in the branch rooted at ``branch_root`` (by hierarchy or explicit branch fact)."""
        t, r = self.canonical_id(term), self.canonical_id(branch_root)
        if not t or not r:
            return False
        return t == r or (t, r) in self.branches or r in self._ancestor_set(t)

    def in_branch_if_known(self, term: str, branch_root: str) -> bool | None:
        """Whether a known term lies in the branch rooted at ``branch_root``; None for a term not in the snapshot."""
        return self.is_in_branch(term, branch_root) if self.contains_term(term) else None

    # --- compatibility ---

    def terms_conflict(self, left: str, right: str) -> bool | None:
        """Whether two known terms conflict (explicit conflict, or different component/sequence families)."""
        lid, rid = self.canonical_id(left), self.canonical_id(right)
        if lid is None or rid is None:
            return None
        if lid == rid:
            return False
        if _ordered(lid, rid) in self.conflicts:
            return True
        lf, rf = self.terms[lid], self.terms[rid]
        if lf.component_family and rf.component_family:
            return lf.component_family != rf.component_family
        if lf.sequence_family and rf.sequence_family:
            return lf.sequence_family != rf.sequence_family
        return False

    def participation_role_compatible_with_interaction_type(self, role: str, interaction_type: str) -> bool | None:
        """Whether SBOL 3 Tables 11/12 cross-list the Participation role for the Interaction type."""
        rid, iid = self.canonical_id(role), self.canonical_id(interaction_type)
        if rid is None or iid is None:
            return None
        if self.terms[rid].role != PARTICIPATION_ROLE or self.terms[iid].role != INTERACTION_TYPE:
            return None
        return (iid, rid) in self.participation_compatibilities

    def component_role_compatible_with_component_type(self, role: str, component_type: str) -> bool | None:
        """Whether a Component role suits a Component type; None when the question doesn't apply."""
        rid, cid = self.canonical_id(role), self.canonical_id(component_type)
        if rid is None or cid is None:
            return None
        rf, cf = self.terms[rid], self.terms[cid]
        if rf.role != FEATURE_ROLE or cf.role != COMPONENT_TYPE:
            return None
        if (rid, cid) in self.component_role_compatibilities:
            return True
        family = cf.component_family
        if family is None:
            return None
        if self.is_in_branch(rid, SEQUENCE_FEATURE_ROOT):
            return family == NUCLEIC_ACID
        if self.is_in_branch(rid, MOLECULAR_FUNCTION_ROOT):
            return family == PROTEIN
        if self.is_in_branch(rid, CHEBI_ROLE_ROOT):
            return family == SIMPLE_CHEMICAL
        return None

    def encoding_compatible_with_component_type(self, encoding: str, component_type: str) -> bool | None:
        """Whether a Sequence encoding suits a Component type; None when the question doesn't apply."""
        eid, cid = self.canonical_id(encoding), self.canonical_id(component_type)
        if eid is None or cid is None:
            return None
        ef, cf = self.terms[eid], self.terms[cid]
        if ef.role != SEQUENCE_ENCODING or cf.role != COMPONENT_TYPE:
            return None
        if (eid, cid) in self.compatibilities:
            return True
        if ef.sequence_family is None or cf.component_family is None:
            return None
        return ef.sequence_family == cf.component_family and ef.sequence_family in (
            NUCLEIC_ACID,
            PROTEIN,
            SIMPLE_CHEMICAL,
        )

    def compatible_sequence_encodings_for_component_type(self, component_type: str) -> list[str]:
        """IRIs of the Table 1 encodings explicitly compatible with a Component type, sorted by compact id."""
        cid = self.canonical_id(component_type)
        if cid is None:
            return []
        return [self.terms[e].iri for e, c in sorted(self.compatibilities) if c == cid and e in self.terms]

    def recommended_sequence_encoding_for_component_type(self, component_type: str) -> str | None:
        """First compatible Table 1 encoding for a Component type."""
        encodings = self.compatible_sequence_encodings_for_component_type(component_type)
        return encodings[0] if encodings else None

    def component_type_family(self, component_type: str) -> str | None:
        """Broad family (nucleic_acid, protein, simple_chemical, complex, functional) of a Component type."""
        fact = self.fact(component_type)
        return fact.component_family if fact else None

    def sequence_encoding_family(self, encoding: str) -> str | None:
        """Broad family (nucleic_acid, protein, simple_chemical, other_textual) of a Sequence encoding."""
        fact = self.fact(encoding)
        return fact.sequence_family if fact else None


@lru_cache(maxsize=None)
def bundled_ontology() -> Ontology:
    """The ontology snapshot shipped with sbol_utilities, parsed once per process."""
    return Ontology.from_tsv(runtime_file("Ontology/ontology_facts.tsv").read_text(encoding="utf-8"))
