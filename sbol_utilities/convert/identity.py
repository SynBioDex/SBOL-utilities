"""SBOL 2 -> SBOL 3 identity mapping.

A top-level SBOL 2 object maps to ``<namespace>[/<version>]/<displayId>`` (:func:`uri.create_sbol3_uri`) and its
``hasNamespace`` is its SBOL 2 prefix. A child nests directly under its owning top-level's SBOL 3 identity as
``<topLevelSbol3>/<relativePath>``, so the version appears once, on the top-level, as in the reference converter's
object model. A reference to a bare ``persistentIdentity`` resolves to the highest-version object carrying it (the
reference's ``getLatestUri``). References to objects outside the document fall back to structural decomposition.
"""

from __future__ import annotations

from rdflib import Literal

from sbol_utilities.convert import uri
from sbol_utilities.convert.terms import RDF_TYPE, S2, Triple, is_iri
from sbol_utilities.vocab import PROV_NS

#: SBOL 2 predicates by which a parent owns a child object, including the PROV qualified-usage/association children
#: of an Activity and the measure children of any Identified object
CONTAINMENT_PREDICATES = frozenset(
    [
        *(
            S2.base + name
            for name in (
                "sequenceAnnotation sequenceConstraint location component functionalComponent module interaction "
                "participation mapsTo variableComponent measure"
            ).split()
        ),
        PROV_NS + "qualifiedUsage",
        PROV_NS + "qualifiedAssociation",
    ]
)

#: SBOL 2 predicates whose IRI objects are identities to rewrite
REFERENCE_PREDICATES = frozenset(
    S2.base + name
    for name in (
        "built sequence sequenceAnnotation sequenceConstraint component functionalComponent module interaction "
        "participation location definition variableComponent variable variant variantCollection variantDerivation "
        "model attachment subject object participant local remote mapsTo template member experimentalData"
    ).split()
)


def compare_versions(a: str, b: str) -> int:
    """Compare dotted versions segment by segment, numerically where both parse; missing segments count as ``0``."""
    a_parts, b_parts = a.strip().split("."), b.strip().split(".")
    for i in range(max(len(a_parts), len(b_parts))):
        sa = a_parts[i] if i < len(a_parts) else "0"
        sb = b_parts[i] if i < len(b_parts) else "0"
        ia, ib = _as_int(sa), _as_int(sb)
        if ia is not None and ib is not None:
            if ia != ib:
                return -1 if ia < ib else 1
        elif sa != sb:
            return -1 if sa.encode() < sb.encode() else 1
    return 0


def _as_int(text: str) -> int | None:
    body = text[1:] if text[:1] in "+-" else text
    if not body or not body.isascii() or not body.isdigit():
        return None
    value = int(text)
    return value if -(2**63) <= value < 2**63 else None


class IdentityMap:
    """SBOL 2 IRI -> SBOL 3 IRI rewrites and derived namespaces for one document."""

    def __init__(self, triples: list[Triple]):
        identified: set[str] = set()
        candidates: set[str] = set()
        owned_by: dict[str, str] = {}
        persistent_identity_of: dict[str, str] = {}
        version_of: dict[str, str] = {}

        for s, p, o in triples:
            if not is_iri(s):
                continue
            if p == RDF_TYPE:
                if is_iri(o) and o.startswith(S2.base):
                    candidates.add(s)
            elif p == S2.persistentIdentity:
                candidates.add(s)
                if is_iri(o):
                    persistent_identity_of[s] = o
            elif p == S2.version:
                if isinstance(o, Literal):
                    version_of[s] = str(o)
            elif p == S2.displayId:
                candidates.add(s)
                identified.add(s)
            if p in CONTAINMENT_PREDICATES and is_iri(o):
                owned_by[o] = s
            if p in REFERENCE_PREDICATES and is_iri(o):
                candidates.add(o)

        latest: dict[str, str] = {}
        for subject in sorted(persistent_identity_of):
            pid = persistent_identity_of[subject]
            best = latest.setdefault(pid, subject)
            if compare_versions(version_of.get(subject, ""), version_of.get(best, "")) > 0:
                latest[pid] = subject

        # a top-level is an identified subject that nothing owns
        tops: dict[str, tuple] = {}
        for subject in identified:
            if subject in owned_by:
                continue
            namespace = uri.uri_prefix_sbol2(subject)
            if namespace is None:
                continue
            display_id = uri.display_id_sbol2(subject) or ""
            tops[subject] = (namespace, f"{namespace}/{display_id}", uri.create_sbol3_uri(subject))

        self.rewrites: dict[str, str] = {}
        for iri in candidates:
            resolved = latest.get(iri, iri)
            top = _owning_top_level(resolved, owned_by, tops)
            if top is None:
                sbol3 = uri.create_sbol3_uri(resolved)
            else:
                _, persistent_identity, top_sbol3 = tops[top]
                relative = None if resolved == top else _child_relative_path(resolved, persistent_identity)
                if resolved == top:
                    sbol3 = top_sbol3
                elif relative is not None:
                    sbol3 = f"{top_sbol3}/{relative}"
                else:
                    sbol3 = uri.create_sbol3_uri(resolved)
            if sbol3 != iri:
                self.rewrites[iri] = sbol3

        #: derived hasNamespace, keyed by SBOL 3 identity (the engine emits it only for top-levels)
        self.namespaces: dict[str, str] = {self.rewrite(top): info[0] for top, info in tops.items()}

    def rewrite(self, iri: str) -> str:
        """The SBOL 3 form of an SBOL 2 IRI (unchanged when it needs no rewrite)."""
        return self.rewrites.get(iri, iri)

    def term(self, term):
        """Rewrite a term when it is an IRI."""
        return self.rewrites.get(term, term) if is_iri(term) else term

    def namespace_for(self, sbol3_iri: str) -> str | None:
        """The derived ``hasNamespace`` of a top-level, by its SBOL 3 identity."""
        return self.namespaces.get(sbol3_iri)


def _owning_top_level(iri: str, owned_by: dict[str, str], tops: dict[str, tuple]) -> str | None:
    if iri in tops:
        return iri
    current = iri
    for _ in range(64):
        parent = owned_by.get(current)
        if parent is None:
            return None
        if parent in tops:
            return parent
        current = parent
    return None


def _child_relative_path(iri: str, persistent_identity: str) -> str | None:
    """The path of a child below ``persistent_identity``, minus any trailing version segment."""
    prefix = persistent_identity + "/"
    if not iri.startswith(prefix):
        return None
    rest = iri[len(prefix) :]
    version = uri.version_sbol2(iri)
    if version and rest.endswith("/" + version):
        return rest[: -len(version) - 1]
    return rest
