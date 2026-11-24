"""SBOL 2 -> SBOL 3 conversion.

The upgrade rewrites the SBOL 2 graph triple by triple, making the same decisions as the SynBioDex/SBOL-Converter
reference and sbol-rs:

* identities move their version segment in front of the displayId (see :mod:`sbol_utilities.convert.identity`);
* classes, predicates, and enumerated values take their SBOL 3 names, and ontology terms their SBOL 3 spelling;
* a SequenceAnnotation that references a Component collapses onto the SubComponent, which takes over its Locations;
* each MapsTo becomes a ComponentReference plus a Constraint, and FunctionalComponent directions an Interface;
* a Location with no inferable Sequence gets a synthesized empty one, so every SBOL 3 Location has a Sequence;
* SBOL 2 detail with no SBOL 3 home is recorded under ``https://sbols.org/backport/2_3#`` so a later downgrade can
  rebuild the SBOL 2 shape.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple

import rdflib
from rdflib import Literal

from sbol_utilities.convert import uri
from sbol_utilities.convert.identity import IdentityMap
from sbol_utilities.convert.report import ConversionReport
from sbol_utilities.convert.terms import (
    BP,
    DCTERMS_DESCRIPTION,
    DCTERMS_TITLE,
    EDAM_IUPAC_DNA_RNA,
    OM_NS,
    PROV_ACTIVITY,
    PROV_AGENT,
    PROV_NS,
    PROV_PLAN,
    RDF_TYPE,
    S2,
    S3,
    SBO_FUNCTIONAL_ENTITY,
    XSD_BOOLEAN,
    Term,
    Triple,
    build_graph,
    graph_triples,
    is_iri,
    plain,
)
from sbol_utilities.convert.values import BIOPAX_TO_SBO, canonical_sbol2_literal, upgrade_value
from sbol_utilities.rdf_io import GraphSource, load_graph


@dataclass
class UpgradeOptions:
    """Configuration for :func:`upgrade`."""

    #: hasNamespace for top-level objects whose namespace cannot be derived from the input
    default_namespace: Optional[str] = None
    #: write https://sbols.org/backport/2_3# annotations so a later downgrade can rebuild the SBOL 2 shape
    preserve_backport: bool = True
    #: URI prefixes; a top-level whose SBOL 2 identity starts with one takes it (minus a trailing ``/``) as its
    #: hasNamespace, in preference to the derived namespace
    namespaces: Optional[List[str]] = None


def upgrade(
    source: GraphSource, options: Optional[UpgradeOptions] = None, fmt: Optional[str] = None
) -> Tuple[rdflib.Graph, ConversionReport]:
    """Convert an SBOL 2 document to SBOL 3.

    :param source: an rdflib Graph, path, RDF text, or sbol2.Document holding SBOL 2
    :param options: conversion options
    :param fmt: RDF format of a path or text source, when it can't be inferred
    :return: the SBOL 3 graph and a report of non-fatal issues
    :raises ValueError: when the input carries triples but nothing that marks it as SBOL 2
    """
    triples = [(s, p, _canonical_literal(p, o)) for s, p, o in graph_triples(load_graph(source, fmt))]
    report = ConversionReport("upgrade", input_triples=len(triples))
    output = _Upgrader(triples, options or UpgradeOptions(), report).run()
    graph = build_graph(output)
    report.output_triples = len(graph)
    return graph, report


def _canonical_literal(predicate: str, term: Term) -> Term:
    return canonical_sbol2_literal(predicate, term) if isinstance(term, Literal) else term


#: SBOL 2 class -> SBOL 3 class
CLASSES: Dict[str, str] = {
    S2.ComponentDefinition: S3.Component,
    S2.ModuleDefinition: S3.Component,
    S2.Component: S3.SubComponent,
    S2.Module: S3.SubComponent,
    S2.FunctionalComponent: S3.SubComponent,
    S2.SequenceAnnotation: S3.SequenceFeature,
    S2.SequenceConstraint: S3.Constraint,
    S2.Sequence: S3.Sequence,
    S2.Model: S3.Model,
    S2.Interaction: S3.Interaction,
    S2.Participation: S3.Participation,
    S2.Collection: S3.Collection,
    S2.Implementation: S3.Implementation,
    S2.Attachment: S3.Attachment,
    S2.Experiment: S3.Experiment,
    S2.ExperimentalData: S3.ExperimentalData,
    S2.CombinatorialDerivation: S3.CombinatorialDerivation,
    S2.VariableComponent: S3.VariableFeature,
    S2.Range: S3.Range,
    S2.Cut: S3.Cut,
    S2.GenericLocation: S3.Location,
}

#: classes the upgrade recognizes: those above plus MapsTo, which decomposes into other objects
KNOWN_CLASSES = frozenset(CLASSES) | {S2.MapsTo}

PROV_TOP_LEVELS = frozenset({PROV_ACTIVITY, PROV_AGENT, PROV_PLAN})

TOP_LEVEL_CLASSES = (
    frozenset(
        S2.base + name
        for name in (
            "ComponentDefinition ModuleDefinition Sequence Model Collection Implementation Attachment Experiment "
            "ExperimentalData CombinatorialDerivation"
        ).split()
    )
    | PROV_TOP_LEVELS
)

#: SBOL 2 predicate -> SBOL 3 predicate, for predicates that convert one-to-one
PREDICATES: Dict[str, str] = {
    S2.base + v2: S3.base + v3
    for v2, v3 in (
        ("displayId", "displayId"),
        ("built", "built"),
        ("type", "type"),
        ("role", "role"),
        ("roleIntegration", "roleIntegration"),
        ("elements", "elements"),
        ("source", "source"),
        ("format", "format"),
        ("size", "size"),
        ("hash", "hash"),
        ("hashAlgorithm", "hashAlgorithm"),
        ("language", "language"),
        ("framework", "framework"),
        ("start", "start"),
        ("end", "end"),
        ("at", "at"),
        ("sequence", "hasSequence"),
        ("sequenceAnnotation", "hasFeature"),
        ("sequenceConstraint", "hasConstraint"),
        ("component", "hasFeature"),
        ("functionalComponent", "hasFeature"),
        ("module", "hasFeature"),
        ("interaction", "hasInteraction"),
        ("participation", "hasParticipation"),
        ("location", "hasLocation"),
        ("definition", "instanceOf"),
        ("variableComponent", "hasVariableFeature"),
        ("operator", "cardinality"),
        ("variable", "variable"),
        ("variant", "variant"),
        ("variantCollection", "variantCollection"),
        ("variantDerivation", "variantDerivation"),
        ("model", "hasModel"),
        ("attachment", "hasAttachment"),
        ("restriction", "restriction"),
        ("subject", "subject"),
        ("object", "object"),
        ("participant", "participant"),
        ("strategy", "strategy"),
        ("template", "template"),
        ("member", "member"),
        ("experimentalData", "member"),
        ("encoding", "encoding"),
        ("orientation", "orientation"),
    )
}

#: SBOL 2 predicates through which a parent owns a child, as the engine tracks ownership
OWNING_PREDICATES = frozenset(
    S2.base + name
    for name in "sequenceAnnotation location component functionalComponent module interaction participation mapsTo "
    "variableComponent".split()
)

DIRECTIONS = {S2.base + "in": "input", S2.out: "output", S2.inout: "nondirectional"}


def _type_precedence(type_iri: str) -> int:
    if type_iri in KNOWN_CLASSES or type_iri in PROV_TOP_LEVELS:
        return 2
    return 1 if type_iri.startswith(S2.base) else 0


@dataclass
class _MapsTo:
    local: Optional[str] = None
    remote: Optional[str] = None
    refinement: Optional[str] = None
    display_id: Optional[str] = None


class _Upgrader:
    """One SBOL 2 -> SBOL 3 conversion run."""

    def __init__(self, triples: List[Triple], options: UpgradeOptions, report: ConversionReport):
        self.triples = triples
        self.options = options
        self.report = report
        self.identity = IdentityMap(triples)
        self.out: List[Triple] = []
        #: original subject IRI -> its SBOL 2 (or PROV top-level) class
        self.typed: Dict[str, str] = {}
        #: CD (or Location) IRI -> the Sequences it references via sbol2:sequence
        self.cd_sequences: Dict[str, List[str]] = defaultdict(list)
        self.location_to_sa: Dict[str, str] = {}
        self.sa_to_cd: Dict[str, str] = {}
        #: SequenceAnnotation -> the Component it references; such an SA collapses onto that SubComponent
        self.sa_to_subcomponent: Dict[str, str] = {}
        self.display_ids: Dict[str, str] = {}
        self.owned_by: Dict[str, str] = {}
        self.mapstos: Dict[str, _MapsTo] = {}
        #: FunctionalComponent (or public Component) -> SBOL 3 Interface slot
        self.fc_directions: Dict[str, str] = {}
        #: every SBOL 3 IRI in use, so synthesized IRIs never land on an existing subject
        self.used_iris: Set[str] = set()
        self.location_display_id_overrides: Dict[str, str] = {}
        #: canonical IRI -> original IRI of custom-typed (GenericTopLevel) subjects
        self.generic_top_levels: Dict[str, str] = {}

    def run(self) -> List[Triple]:
        """Convert the input, returning the SBOL 3 triples."""
        self._preflight()
        for triple in self.triples:
            self._handle(triple)
        self._emit_namespaces()
        self._infer_location_sequences()
        self._decompose_mapstos()
        self._synthesize_interfaces()
        return self.out

    # Preflight

    def _preflight(self) -> None:
        rewrite = self.identity.rewrite
        sources: Dict[str, List[str]] = defaultdict(list)
        for subject in sorted({s for s, _, _ in self.triples if is_iri(s)}):
            canonical = rewrite(subject)
            self.used_iris.add(canonical)
            sources[canonical].append(subject)
        for canonical in sorted(sources):
            if len(sources[canonical]) > 1:
                self.report.warn(
                    "IdentityCollision",
                    canonical,
                    f"{len(sources[canonical])} SBOL 2 subjects merge into one: {', '.join(sources[canonical])}",
                )

        saw_sbol2_predicate = False
        custom_typed: Set[str] = set()
        recognized_typed: Set[str] = set()
        sbol2_identified: Set[str] = set()
        for s, p, o in self.triples:
            if p.startswith(S2.base):
                saw_sbol2_predicate = True
                if p in (S2.persistentIdentity, S2.displayId) and is_iri(s):
                    sbol2_identified.add(s)
            if p == RDF_TYPE:
                if is_iri(o) and is_iri(s):
                    if o.startswith(S2.base) or o.startswith(PROV_NS) or o.startswith(OM_NS):
                        recognized_typed.add(s)
                    else:
                        custom_typed.add(s)
                    if o.startswith(S2.base) or o in PROV_TOP_LEVELS:
                        existing = self.typed.get(s)
                        if existing is None or _type_precedence(o) > _type_precedence(existing):
                            self.typed[s] = o
                continue
            if not is_iri(s):
                continue
            if p == S2.displayId and isinstance(o, Literal):
                self.display_ids.setdefault(s, str(o))
            if not is_iri(o):
                continue
            if p == S2.sequence:
                self.cd_sequences[s].append(o)
            elif p == S2.sequenceAnnotation:
                self.sa_to_cd[o] = s
            elif p == S2.location:
                self.location_to_sa[o] = s
            if p in OWNING_PREDICATES:
                self.owned_by[o] = s

        has_recognized_type = bool(recognized_typed) or any(
            t.startswith(S2.base) or t in PROV_TOP_LEVELS for t in self.typed.values()
        )
        if self.triples and not saw_sbol2_predicate and not has_recognized_type:
            raise ValueError("input contains no SBOL 2 typed subjects or properties; nothing to upgrade")

        # A custom-typed subject with SBOL 2 identity properties and no recognized type is a GenericTopLevel. SBOL 3
        # has no such class, so it keeps its custom type and becomes a top-level, unless it nests under another
        # identified subject.
        prefixes = [rewrite(iri) + "/" for iri in sbol2_identified]
        for subject in sorted(sbol2_identified):
            if subject not in custom_typed or subject in recognized_typed:
                continue
            canonical = rewrite(subject)
            if not any(canonical.startswith(prefix) for prefix in prefixes):
                self.generic_top_levels.setdefault(canonical, subject)

        for s, p, o in self.triples:
            if p == S2.component and is_iri(s) and is_iri(o) and self.typed.get(s) == S2.SequenceAnnotation:
                self.sa_to_subcomponent[s] = o

        # Locations of a collapsed SA move under their new SubComponent parent. The Location's own canonical IRI is
        # released first: it is being re-homed, not duplicated.
        owners = sorted(
            (loc, self.sa_to_subcomponent[sa])
            for loc, sa in self.location_to_sa.items()
            if sa in self.sa_to_subcomponent
        )
        for loc, subcomponent in owners:
            base = self.display_ids.get(loc) or uri.last_segment(rewrite(loc))
            self.used_iris.discard(rewrite(loc))
            display_id, new_iri = uri.next_available_child_iri(
                rewrite(subcomponent), base, self.used_iris, collapse_slash=False
            )
            if display_id != base:
                self.location_display_id_overrides[loc] = display_id
            self.identity.rewrites[loc] = new_iri

        # Interface membership: in/out/inout directions, public direction-none FunctionalComponents, and public
        # Components (SBOL 3.1.0 §10.2).
        direction_none: Set[str] = set()
        public_fcs: Set[str] = set()
        for s, p, o in self.triples:
            if not (is_iri(s) and is_iri(o)):
                continue
            if p == S2.direction and self.typed.get(s) == S2.FunctionalComponent:
                if o == S2.none:
                    direction_none.add(s)
                elif o in DIRECTIONS:
                    self.fc_directions[s] = DIRECTIONS[o]
        for s, p, o in self.triples:
            if p == S2.access and is_iri(s) and o == S2.public:
                if self.typed.get(s) == S2.FunctionalComponent:
                    public_fcs.add(s)
                elif self.typed.get(s) == S2.Component:
                    self.fc_directions.setdefault(s, "nondirectional")
        for fc in direction_none & public_fcs:
            self.fc_directions.setdefault(fc, "nondirectional")

        for s, p, o in self.triples:
            if not is_iri(s) or self.typed.get(s) != S2.MapsTo:
                continue
            info = self.mapstos.setdefault(s, _MapsTo())
            if p == S2.local and is_iri(o):
                info.local = o
            elif p == S2.remote and is_iri(o):
                info.remote = o
            elif p == S2.refinement and is_iri(o):
                info.refinement = o
            elif p == S2.displayId and isinstance(o, Literal):
                info.display_id = str(o)

    def _owning_top_level(self, subject: str) -> str:
        current, seen = subject, {subject}
        while current in self.owned_by and self.owned_by[current] not in seen:
            current = self.owned_by[current]
            seen.add(current)
        return current

    # Per-triple conversion

    def _handle(self, triple: Triple) -> None:
        s, p, o = triple
        if not p.startswith(S2.base) and is_iri(s) and s in self.sa_to_subcomponent:
            if not (p == RDF_TYPE and o == S2.SequenceAnnotation):
                self._move_collapsed_sa_triple(triple, self.sa_to_subcomponent[s])
                return
        if p == RDF_TYPE:
            self._handle_type(triple)
        elif p.startswith(S2.base):
            self._handle_sbol2_predicate(triple)
        elif p in (DCTERMS_TITLE, DCTERMS_DESCRIPTION):
            predicate = S3.name if p == DCTERMS_TITLE else S3.description
            self.out.append((self.identity.term(s), predicate, self.identity.term(o)))
        else:
            self.out.append((self.identity.term(s), p, self.identity.term(o)))

    def _move_collapsed_sa_triple(self, triple: Triple, subcomponent: str) -> None:
        """Carry a non-SBOL annotation of a collapsed SequenceAnnotation over to its SubComponent."""
        _, p, o = triple
        if p.startswith(S2.base) or p == RDF_TYPE:
            return
        predicate = {DCTERMS_TITLE: S3.name, DCTERMS_DESCRIPTION: S3.description}.get(p, p)
        self.out.append((self.identity.rewrite(subcomponent), predicate, self.identity.term(o)))

    def _handle_type(self, triple: Triple) -> None:
        s, p, o = triple
        if not is_iri(o):
            self.out.append((self.identity.term(s), p, o))
            return
        if o == S2.SequenceAnnotation and is_iri(s) and s in self.sa_to_subcomponent:
            self.report.warn(
                "SequenceAnnotationWithComponent", s, "collapsed onto the SubComponent of the Component it references"
            )
            return
        if o == S2.MapsTo:
            return
        subject = self.identity.term(s)
        target = CLASSES.get(o)
        if target is None:
            if o.startswith(S2.base):
                if is_iri(s):
                    self.report.warn("UnknownSbol2Type", s, f"unrecognized SBOL 2 type {o}; subject dropped")
                return
            self.out.append((subject, p, BIOPAX_TO_SBO.get(o, o)))
            return
        self.out.append((subject, p, target))
        if o == S2.ModuleDefinition:
            # an SBOL 3 Component needs a type; ModuleDefinitions have none
            self.out.append((subject, S3.type, SBO_FUNCTIONAL_ENTITY))
        if self.options.preserve_backport:
            if o == S2.Module:
                self.out.append((subject, BP.sbol2OriginatesFromModule, plain("true")))
            elif is_iri(s):
                self.out.append((subject, BP.sbol2OriginalURI, s))

    def _handle_sbol2_predicate(self, triple: Triple) -> None:
        s, p, o = triple
        if self._collapse_sa_triple(triple):
            return
        if p == S2.mapsTo and is_iri(o) and o in self.mapstos:
            return
        if is_iri(s) and s in self.mapstos:
            return
        target = PREDICATES.get(p)
        if target is None:
            # persistentIdentity and version feed identity derivation; access, direction, and any other SBOL 2-only
            # property has no SBOL 3 home
            return
        value = self._rewrite_value(s if is_iri(s) else "", p, self.identity.term(o))
        if p == S2.displayId and is_iri(s) and s in self.location_display_id_overrides:
            value = plain(self.location_display_id_overrides[s])
        if p in (S2.start, S2.end, S2.at) and isinstance(value, Literal):
            value = plain(str(value))
        self.out.append((self.identity.term(s), target, value))

    def _collapse_sa_triple(self, triple: Triple) -> bool:
        """Handle the SBOL 2 properties of a collapsed SequenceAnnotation; True when the triple was consumed."""
        s, p, o = triple
        if not is_iri(s):
            return False
        if p == S2.sequenceAnnotation and is_iri(o) and o in self.sa_to_subcomponent:
            return True
        subcomponent = self.sa_to_subcomponent.get(s)
        if subcomponent is None:
            return False
        target = self.identity.rewrite(subcomponent)
        if p == S2.location:
            self.out.append((target, S3.hasLocation, self.identity.term(o)))
        elif p == S2.displayId:
            if self.options.preserve_backport:
                self.out.append((target, BP.sbol2OriginalSequenceAnnotationURI, s))
                self.out.append((target, BP.sbol2OriginalURI, s))
        elif p != S2.component:
            self._move_collapsed_sa_triple(triple, subcomponent)
        return True

    def _rewrite_value(self, subject: str, predicate: str, value: Term) -> Term:
        """The SBOL 3 spelling of an enumerated value or ontology term."""
        if not is_iri(value):
            return value
        mapped = upgrade_value(predicate, value)
        if mapped is not None:
            return mapped
        subject_type = self.typed.get(subject)
        if predicate == S2.type:
            if subject_type == S2.Interaction:
                return uri.convert_sbo_2_to_3(value)
            return BIOPAX_TO_SBO.get(value) or uri.component_type_2_to_3(value)
        if predicate == S2.role:
            if subject_type == S2.Participation:
                return uri.convert_sbo_2_to_3(value)
            return uri.convert_so_2_to_3(value)
        if predicate == S2.framework:
            return uri.convert_sbo_2_to_3(value)
        if predicate == S2.language:
            return uri.convert_edam_2_to_3(value)
        return value

    # Synthesis

    def _namespace(self, sbol2_iri: str, canonical: str) -> Optional[str]:
        for prefix in self.options.namespaces or ():
            if sbol2_iri.startswith(prefix):
                return prefix[:-1] if prefix.endswith("/") else prefix
        return self.identity.namespace_for(canonical)

    def _emit_namespaces(self) -> None:
        # (SBOL 2 identity, SBOL 3 identity, IRI the URL-origin fallback reads) of every top-level
        top_levels = [
            (iri, self.identity.rewrite(iri), iri)
            for iri, cls in sorted(self.typed.items())
            if cls in TOP_LEVEL_CLASSES
        ]
        top_levels += [(self.generic_top_levels[c], c, c) for c in sorted(self.generic_top_levels)]
        done: Set[str] = set()
        for sbol2_iri, canonical, fallback_source in top_levels:
            if canonical in done:
                continue
            done.add(canonical)
            namespace = self._namespace(sbol2_iri, canonical)
            if namespace is None:
                namespace = self._fallback_namespace(fallback_source)
            if namespace is not None:
                self.out.append((canonical, S3.hasNamespace, namespace))

    def _fallback_namespace(self, iri: str) -> Optional[str]:
        origin = uri.url_origin(iri)
        if origin is not None:
            return origin
        if self.options.default_namespace:
            self.report.warn("NamespaceFallback", iri, "no derivable namespace; used the default namespace")
            return self.options.default_namespace
        self.report.warn("NamespaceFallback", iri, "no derivable namespace; hasNamespace omitted")
        return None

    def _infer_location_sequences(self) -> None:
        """Give every Location the ``hasSequence`` SBOL 3 requires, inferring it from the owning Component.

        A Component with exactly one Sequence lends it to its Locations; one with none gets a synthesized empty
        Sequence (as the reference does); one with several is ambiguous and left for validation to flag.
        """
        rewrite = self.identity.rewrite
        temp_sequences: Dict[str, Tuple[str, Optional[str]]] = {}
        for location, sa in sorted(self.location_to_sa.items()):
            cd = self.sa_to_cd.get(sa)
            if cd is None:
                continue
            location_v3 = rewrite(location)
            own = self.cd_sequences.get(location)
            if own:
                self.out.append((location_v3, S3.hasSequence, rewrite(own[0])))
                continue
            sequences = self.cd_sequences.get(cd, [])
            if len(sequences) == 1:
                sequence = rewrite(sequences[0])
            elif not sequences:
                cd_v3 = rewrite(cd)
                if cd_v3 not in temp_sequences:
                    temp_sequences[cd_v3] = (f"{cd_v3}_seq", self._namespace(cd, cd_v3))
                sequence = temp_sequences[cd_v3][0]
            else:
                self.report.warn(
                    "LocationWithoutSequence",
                    location,
                    f"{cd} has {len(sequences)} sequences; hasSequence not inferred",
                )
                continue
            self.out.append((location_v3, S3.hasSequence, sequence))
            if self.options.preserve_backport:
                self.out.append((location_v3, BP.sbol2LocationSequenceNull, Literal("true", datatype=XSD_BOOLEAN)))

        for cd_v3, (temp, namespace) in temp_sequences.items():
            self.out.append((temp, RDF_TYPE, S3.Sequence))
            self.out.append((temp, S3.displayId, plain(uri.last_segment(temp))))
            self.out.append((temp, S3.encoding, EDAM_IUPAC_DNA_RNA))
            if namespace is not None:
                self.out.append((temp, S3.hasNamespace, namespace))
            self.out.append((cd_v3, S3.hasSequence, temp))
            if self.options.preserve_backport:
                self.out.append((cd_v3, BP.sbol3TempSequenceURI, temp))

    def _decompose_mapstos(self) -> None:
        """Replace each MapsTo with a ComponentReference and a Constraint on the enclosing top-level Component.

        Per SBOL 3.1.0 §10.2 the Constraint's shape follows the refinement: ``useLocal`` puts the local SubComponent
        in ``subject`` and the reference in ``object`` (restriction ``replaces``); ``useRemote`` and ``merge`` swap
        them; ``verifyIdentical`` (and an absent or unknown refinement) keeps the reference in ``subject``.
        """
        rewrite = self.identity.rewrite
        for mapsto, info in sorted(self.mapstos.items()):
            carrier = self.owned_by.get(mapsto)
            if carrier is None:
                self.report.warn("UnresolvedMapsTo", mapsto, "no Module or FunctionalComponent carries it")
                continue
            if info.local is None or info.remote is None:
                side = "local" if info.local is None else "remote"
                self.report.warn("UnresolvedMapsTo", mapsto, f"the {side} side is missing")
                continue
            top_level = rewrite(self._owning_top_level(carrier))
            local, remote = rewrite(info.local), rewrite(info.remote)
            base = info.display_id if info.display_id is not None else uri.last_segment(mapsto)
            cref_id, cref = uri.next_available_child_iri(top_level, base, self.used_iris, collapse_slash=False)
            constraint_id, constraint = self._next_constraint(top_level)

            if self.options.preserve_backport:
                self.out.append((cref, BP.sbol2OriginalURI, mapsto))
            self.out += [
                (cref, RDF_TYPE, S3.ComponentReference),
                (cref, S3.displayId, plain(cref_id)),
                (cref, S3.inChildOf, rewrite(carrier)),
                (cref, S3.refersTo, remote),
                (top_level, S3.hasFeature, cref),
            ]

            refinement = info.refinement
            if refinement == S2.useLocal:
                subject, obj, restriction = local, cref, S3.replaces
            elif refinement in (S2.useRemote, S2.merge):
                subject, obj, restriction = cref, local, S3.replaces
            else:
                if refinement not in (None, S2.verifyIdentical):
                    self.report.warn(
                        "UnsupportedRefinement", mapsto, f"refinement {refinement} treated as verifyIdentical"
                    )
                subject, obj, restriction = cref, local, S3.verifyIdentical
            self.out += [
                (constraint, RDF_TYPE, S3.Constraint),
                (constraint, S3.displayId, plain(constraint_id)),
                (constraint, S3.subject, subject),
                (constraint, S3.object, obj),
                (constraint, S3.restriction, restriction),
                (top_level, S3.hasConstraint, constraint),
            ]

    def _next_constraint(self, top_level: str) -> Tuple[str, str]:
        """The next free ``Constraint<N>`` child of a Component, numbered like the reference's ``createConstraint``."""
        counter = 1
        while True:
            display_id = f"Constraint{counter}"
            iri = f"{top_level}/{display_id}"
            if iri not in self.used_iris:
                self.used_iris.add(iri)
                return display_id, iri
            counter += 1

    def _synthesize_interfaces(self) -> None:
        """Give each Component with directional or public features an Interface listing them."""
        by_top_level: Dict[str, List[Tuple[str, str]]] = defaultdict(list)
        for fc, slot in sorted(self.fc_directions.items()):
            by_top_level[self._owning_top_level(fc)].append((fc, slot))
        for top in sorted(by_top_level):
            top_v3 = self.identity.rewrite(top)
            display_id, interface = uri.next_available_child_iri(
                top_v3, "Interface1", self.used_iris, collapse_slash=False
            )
            self.out.append((interface, RDF_TYPE, S3.Interface))
            self.out.append((interface, S3.displayId, plain(display_id)))
            for fc, slot in by_top_level[top]:
                self.out.append((interface, S3.base + slot, self.identity.rewrite(fc)))
            self.out.append((top_v3, S3.hasInterface, interface))
