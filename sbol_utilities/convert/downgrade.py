"""SBOL 3 -> SBOL 2 conversion.

The downgrade is the inverse of :mod:`sbol_utilities.convert.upgrade` and makes the same decisions as the
SynBioDex/SBOL-Converter reference and sbol-rs:

* each Component becomes exactly one SBOL 2 class: a ModuleDefinition when it has interactions, the SBO functional
  entity type, or a SubComponent instantiating a ModuleDefinition (recursively), otherwise a ComponentDefinition;
* identities move their version segment back to the end (``<ns>/<version>/<id>`` -> ``<ns>/<id>/<version>``) and
  every object regains ``persistentIdentity`` and ``version``;
* ComponentReference + Constraint pairs fold back into MapsTo, Interfaces into ``direction``/``access``, located
  SubComponents into SequenceAnnotation wrappers;
* the ``https://sbols.org/backport/2_3#`` hints an upgrade recorded restore the original SBOL 2 shape, and are not
  themselves emitted.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

import rdflib
from rdflib import Literal

from sbol_utilities.convert import uri
from sbol_utilities.convert.report import ConversionReport
from sbol_utilities.convert.terms import (
    BP,
    DCTERMS_DESCRIPTION,
    DCTERMS_TITLE,
    PROV_ACTIVITY,
    PROV_AGENT,
    PROV_NS,
    PROV_PLAN,
    RDF_TYPE,
    S2,
    S3,
    SBO_FUNCTIONAL_ENTITY,
    Term,
    Triple,
    build_graph,
    graph_triples,
    is_iri,
    plain,
)
from sbol_utilities.convert.values import SBO_TO_BIOPAX, downgrade_value, refinement_for
from sbol_utilities.rdf_io import GraphSource, load_graph
from sbol_utilities.validation.rdf import DISPLAY_ID_PATTERN


@dataclass
class DowngradeOptions:
    """Configuration for :func:`downgrade`."""

    #: sbol2:version for top-level objects whose SBOL 3 IRI carries no version segment; None leaves them unversioned
    default_version: Optional[str] = None


def downgrade(
    source: GraphSource, options: Optional[DowngradeOptions] = None, fmt: Optional[str] = None
) -> Tuple[rdflib.Graph, ConversionReport]:
    """Convert an SBOL 3 document to SBOL 2.

    :param source: an rdflib Graph, path, RDF text, or sbol3.Document holding SBOL 3
    :param options: conversion options
    :param fmt: RDF format of a path or text source, when it can't be inferred
    :return: the SBOL 2 graph and a report of non-fatal issues
    :raises ValueError: when ``default_version`` is the empty string
    """
    options = options or DowngradeOptions()
    if options.default_version == "":
        raise ValueError("default_version must be non-empty when set; use None to leave objects unversioned")
    triples = graph_triples(load_graph(source, fmt))
    report = ConversionReport("downgrade", input_triples=len(triples))
    output = _Downgrader(triples, options, report).run()
    graph = build_graph(output)
    report.output_triples = len(graph)
    return graph, report


#: SBOL 3 class -> SBOL 2 class; Component and SubComponent depend on context and are resolved separately
CLASSES: Dict[str, str] = {
    S3.Component: S2.ComponentDefinition,
    S3.SubComponent: S2.Component,
    S3.SequenceFeature: S2.SequenceAnnotation,
    S3.Constraint: S2.SequenceConstraint,
    S3.Sequence: S2.Sequence,
    S3.Model: S2.Model,
    S3.Interaction: S2.Interaction,
    S3.Participation: S2.Participation,
    S3.Collection: S2.Collection,
    S3.Implementation: S2.Implementation,
    S3.Attachment: S2.Attachment,
    S3.Experiment: S2.Experiment,
    S3.ExperimentalData: S2.ExperimentalData,
    S3.CombinatorialDerivation: S2.CombinatorialDerivation,
    S3.VariableFeature: S2.VariableComponent,
    S3.Range: S2.Range,
    S3.Cut: S2.Cut,
    S3.Location: S2.GenericLocation,
}

#: SBOL 3 predicate -> SBOL 2 predicate, for predicates that convert one-to-one
PREDICATES: Dict[str, str] = {
    S3.base + v3: v2
    for v3, v2 in (
        ("displayId", S2.displayId),
        ("name", DCTERMS_TITLE),
        ("description", DCTERMS_DESCRIPTION),
        ("type", S2.type),
        ("role", S2.role),
        ("roleIntegration", S2.roleIntegration),
        ("elements", S2.elements),
        ("encoding", S2.encoding),
        ("source", S2.source),
        ("format", S2.format),
        ("size", S2.size),
        ("hash", S2.hash),
        ("hashAlgorithm", S2.hashAlgorithm),
        ("language", S2.language),
        ("framework", S2.framework),
        ("start", S2.start),
        ("end", S2.end),
        ("at", S2.at),
        ("built", S2.built),
        ("orientation", S2.orientation),
        ("hasSequence", S2.sequence),
        ("hasConstraint", S2.sequenceConstraint),
        ("hasInteraction", S2.interaction),
        ("hasParticipation", S2.participation),
        ("hasLocation", S2.location),
        ("hasModel", S2.model),
        ("hasAttachment", S2.attachment),
        ("instanceOf", S2.definition),
        ("hasVariableFeature", S2.variableComponent),
        ("cardinality", S2.operator),
        ("variable", S2.variable),
        ("variant", S2.variant),
        ("variantCollection", S2.variantCollection),
        ("variantDerivation", S2.variantDerivation),
        ("restriction", S2.restriction),
        ("subject", S2.subject),
        ("object", S2.object),
        ("participant", S2.participant),
        ("strategy", S2.strategy),
        ("template", S2.template),
        ("member", S2.member),
    )
}

#: the order in which sbol-rs's typed document model picks the class of a multiply-typed subject
DISPATCH_ORDER = [
    S3.base + name
    for name in (
        "Attachment Experiment Collection CombinatorialDerivation Component ComponentReference Constraint Cut "
        "EntireSequence ExperimentalData ExternallyDefined Implementation Interaction Interface LocalSubComponent "
        "Model Participation Range Sequence SequenceFeature SubComponent VariableFeature"
    ).split()
] + [PROV_ACTIVITY, PROV_AGENT, PROV_NS + "Association", PROV_PLAN, PROV_NS + "Usage"]

TOP_LEVEL_CLASSES = frozenset(
    [
        S3.base + name
        for name in (
            "Attachment Experiment Collection CombinatorialDerivation Component ExperimentalData Implementation Model "
            "Sequence"
        ).split()
    ]
    + [PROV_ACTIVITY, PROV_AGENT, PROV_PLAN]
)

LOCATION_TYPES = frozenset({S2.Range, S2.Cut, S2.GenericLocation})

DIRECTION_SLOTS = {S3.input: "in", S3.output: "out", S3.nondirectional: "inout"}


@dataclass
class _MapsTo:
    carrier: str
    display_id: str
    local: str
    remote: str
    refinement: Optional[str]


@dataclass
class _SaWrapper:
    """A SequenceAnnotation to emit around a located SubComponent."""

    display_id: str
    iri_unversioned: str
    parent_component: str
    locations: List[str] = field(default_factory=list)


class _Downgrader:
    """One SBOL 3 -> SBOL 2 conversion run."""

    def __init__(self, triples: List[Triple], options: DowngradeOptions, report: ConversionReport):
        self.triples = triples
        self.options = options
        self.report = report
        self.out: List[Triple] = []
        self.types: Dict[str, Set[str]] = defaultdict(set)
        for s, p, o in triples:
            if p == RDF_TYPE and is_iri(s) and is_iri(o):
                self.types[s].add(o)
        #: every IRI in use, so synthesized SBOL 2 IRIs never land on an existing subject
        self.used_iris: Set[str] = {s for s, _, _ in triples if is_iri(s)}
        self.top_levels: Set[str] = set()
        self.versions: Dict[str, str] = {}
        self.preserved_versions: Set[str] = set()
        self.persistent_identities: Dict[str, str] = {}
        self.rewrites: Dict[str, str] = {}
        #: Component -> True when it downgrades to a ModuleDefinition
        self.is_md: Dict[str, bool] = {}
        self.feature_parent: Dict[str, str] = {}
        self.subcomponent_targets: Dict[str, str] = {}
        self.module_origin: Set[str] = set()
        self.null_sequence_locations: Set[str] = set()
        self.namespaces: Dict[str, str] = {}
        self.dcterms: Set[Tuple[str, str, Term]] = set()
        self.mapstos: Dict[str, _MapsTo] = {}
        self.mapsto_constraints: Set[str] = set()
        self.interfaces: Set[str] = set()
        self.discarded: Set[str] = set()
        self.fc_directions: Dict[str, str] = {}
        self.sa_wrappers: Dict[str, _SaWrapper] = {}
        self.resolved_types: Dict[str, str] = {}
        self.resolved_type_sets: Dict[str, Set[str]] = defaultdict(set)

    def run(self) -> List[Triple]:
        """Convert the input, returning the SBOL 2 triples."""
        self._preflight()
        for triple in self.triples:
            self._handle(triple)
        self._emit_sa_wrappers()
        self._emit_mapstos()
        self._emit_directions()
        self._emit_identity_metadata()
        self._emit_instance_defaults()
        return self.out

    # Preflight

    def _preflight(self) -> None:
        for s, p, o in self.triples:
            if not is_iri(s):
                continue
            if p == BP.sbol2OriginatesFromModule:
                self.module_origin.add(s)
            elif p == BP.sbol3TempSequenceURI:
                # the upgrade synthesized this empty Sequence; SBOL 2 does not need it
                if is_iri(o):
                    self.discarded.add(o)
            elif p == BP.sbol2LocationSequenceNull:
                self.null_sequence_locations.add(s)
            elif p == S3.hasNamespace:
                if is_iri(o):
                    self.namespaces[s] = o
            elif p in (DCTERMS_TITLE, DCTERMS_DESCRIPTION):
                self.dcterms.add((s, p, o))

        for subject, types in self.types.items():
            primary = next((cls for cls in DISPATCH_ORDER if cls in types), None)
            if primary in TOP_LEVEL_CLASSES:
                self.top_levels.add(subject)
        # hasNamespace marks every SBOL 3 top-level, including custom-typed ones
        self.top_levels.update(self.namespaces)

        self._discover_mapstos_and_interfaces()
        self._classify_components()
        self._discover_sa_wrappers()
        self._discover_unsupported()
        self._build_rewrites()

        sources: Dict[str, List[str]] = defaultdict(list)
        for sbol3, sbol2 in self.rewrites.items():
            sources[sbol2].append(sbol3)
        for sbol2 in sorted(sources):
            if len(sources[sbol2]) > 1:
                names = ", ".join(sorted(sources[sbol2]))
                self.report.warn("IdentityCollision", sbol2, f"{len(sources[sbol2])} SBOL 3 subjects merge: {names}")

        for s, p, o in self.triples:
            if p == S3.instanceOf and is_iri(s) and is_iri(o):
                self.subcomponent_targets[s] = o
        for s, p, o in self.triples:
            if p == RDF_TYPE and is_iri(s) and is_iri(o):
                resolved = self._sbol2_type(s, o)
                if resolved is not None:
                    self.resolved_type_sets[s].add(resolved)
                    self.resolved_types.setdefault(s, resolved)

    def _has_type(self, subject: str, cls: str) -> bool:
        return cls in self.types.get(subject, ())

    def _discover_mapstos_and_interfaces(self) -> None:
        """Pair each ComponentReference with the Constraint naming it, and index Interface membership.

        Only a Constraint whose restriction is ``verifyIdentical`` or ``replaces`` (the two the upgrade writes) is a
        MapsTo back-half; any other Constraint touching a ComponentReference is a genuine SBOL 3 Constraint.
        """
        crefs: Dict[str, Dict[str, str]] = defaultdict(dict)
        constraints: Dict[str, Dict[str, str]] = defaultdict(dict)
        interface_members: Dict[str, List[Tuple[str, str]]] = defaultdict(list)
        for s, p, o in self.triples:
            if not is_iri(s):
                continue
            if p == RDF_TYPE:
                if o == S3.Interface:
                    self.interfaces.add(s)
            elif p in (S3.inChildOf, S3.refersTo):
                if is_iri(o):
                    crefs[s][p] = o
            elif p == S3.displayId:
                if isinstance(o, Literal):
                    crefs[s][p] = str(o)
            elif p in (S3.subject, S3.object, S3.restriction):
                if is_iri(o):
                    constraints[s][p] = o
            elif p in DIRECTION_SLOTS:
                if is_iri(o):
                    interface_members[s].append((o, DIRECTION_SLOTS[p]))

        cref_to_constraint: Dict[str, Tuple[str, bool]] = {}
        for constraint in sorted(constraints):
            attrs = constraints[constraint]
            if not self._has_type(constraint, S3.Constraint):
                continue
            subject, obj = attrs.get(S3.subject), attrs.get(S3.object)
            if subject is not None and self._has_type(subject, S3.ComponentReference):
                cref, cref_is_subject = subject, True
            elif obj is not None and self._has_type(obj, S3.ComponentReference):
                cref, cref_is_subject = obj, False
            else:
                continue
            if attrs.get(S3.restriction) not in (S3.verifyIdentical, S3.replaces):
                continue
            cref_to_constraint[cref] = (constraint, cref_is_subject)

        for cref in sorted(crefs):
            attrs = crefs[cref]
            if not self._has_type(cref, S3.ComponentReference):
                continue
            if cref not in cref_to_constraint:
                self.report.warn("OrphanComponentReference", cref, "no matching Constraint; dropped")
                self.discarded.add(cref)
                continue
            constraint, cref_is_subject = cref_to_constraint[cref]
            constraint_attrs = constraints[constraint]
            local = constraint_attrs.get(S3.object if cref_is_subject else S3.subject)
            restriction = constraint_attrs.get(S3.restriction)
            carrier, remote, display_id = attrs.get(S3.inChildOf), attrs.get(S3.refersTo), attrs.get(S3.displayId)
            if carrier is None or remote is None or display_id is None or local is None:
                self.report.warn(
                    "UnresolvableConstraintToMapsTo",
                    constraint,
                    "ComponentReference+Constraint pair is missing inChildOf, refersTo, displayId, or its local side",
                )
                self.discarded.update((cref, constraint))
                continue
            refinement = refinement_for(restriction, cref_is_subject) if restriction else None
            self.mapstos[cref] = _MapsTo(carrier, display_id, local, remote, refinement)
            self.mapsto_constraints.add(constraint)

        for interface, members in interface_members.items():
            if interface not in self.interfaces:
                continue
            for feature, direction in members:
                existing = self.fc_directions.get(feature)
                if existing is None or existing == direction:
                    self.fc_directions[feature] = direction
                elif existing == "inout" or direction == "inout" or {existing, direction} == {"in", "out"}:
                    self.fc_directions[feature] = "inout"

    def _classify_components(self) -> None:
        """Decide whether each Component downgrades to a ModuleDefinition or a ComponentDefinition.

        A Component is a ModuleDefinition when it has interactions or the SBO functional entity type, or contains a
        SubComponent whose ``instanceOf`` is (recursively) a ModuleDefinition.
        """
        instance_of: Dict[str, str] = {}
        for s, p, o in self.triples:
            if is_iri(s) and is_iri(o):
                if p == S3.hasFeature:
                    self.feature_parent[o] = s
                elif p == S3.instanceOf:
                    instance_of[s] = o
        components = {s for s, types in self.types.items() if S3.Component in types}
        functional: Set[str] = set()
        for s, p, o in self.triples:
            if s in components and (p == S3.hasInteraction or (p == S3.type and o == SBO_FUNCTIONAL_ENTITY)):
                functional.add(s)
        child_targets: Dict[str, List[str]] = defaultdict(list)
        for child, parent in self.feature_parent.items():
            if self._has_type(child, S3.SubComponent) and child in instance_of:
                child_targets[parent].append(instance_of[child])
        module_definitions = set(functional)
        changed = True
        while changed:
            changed = False
            for component in components - module_definitions:
                if any(target in module_definitions for target in child_targets.get(component, ())):
                    module_definitions.add(component)
                    changed = True
        self.is_md = {component: component in module_definitions for component in components}

    def _discover_sa_wrappers(self) -> None:
        """Find every SubComponent that needs an SBOL 2 SequenceAnnotation wrapper.

        A SubComponent the upgrade collapsed an SBOL 2 SequenceAnnotation onto carries that annotation's identity;
        any other located SubComponent needs a wrapper too, since an SBOL 2 Component cannot carry Locations. The
        wrapper restores the recorded displayId, or is named ``{subComponent}_{firstLocation}`` like the reference.
        """
        locations_of: Dict[str, List[str]] = defaultdict(list)
        display_ids: Dict[str, str] = {}
        recorded: Dict[str, str] = {}
        for s, p, o in self.triples:
            if not is_iri(s):
                continue
            if p == S3.displayId and isinstance(o, Literal):
                display_ids.setdefault(s, str(o))
            elif p == S3.hasLocation and is_iri(o):
                locations_of[s].append(o)
            elif p == BP.sbol2OriginalSequenceAnnotationURI and is_iri(o):
                # The recorded original identity names the rebuilt SequenceAnnotation. A non-compliant identity
                # (e.g. a `#` fragment) has no displayId-shaped segment, and the SA is then named like a native one.
                sa_display_id = uri.display_id_sbol2(o)
                if sa_display_id is not None and DISPLAY_ID_PATTERN.match(sa_display_id):
                    recorded.setdefault(s, sa_display_id)

        candidates = set(recorded) | {s for s in locations_of if self._has_type(s, S3.SubComponent)}
        for subcomponent in sorted(candidates):
            parent = self.feature_parent.get(subcomponent)
            if parent is None:
                continue
            if self.is_md.get(parent):
                # a FunctionalComponent cannot own a SequenceAnnotation; its locations are dropped, as in the reference
                self.discarded.update(locations_of.get(subcomponent, ()))
                continue
            locations = sorted(locations_of.get(subcomponent, ()))
            base = recorded.get(subcomponent)
            if base is None:
                sub_display_id = display_ids.get(subcomponent) or uri.last_segment(subcomponent)
                first = display_ids.get(locations[0]) if locations else None
                base = f"{sub_display_id}_{first}" if first is not None else f"{sub_display_id}_annotation"
            display_id, iri = uri.next_available_child_iri(parent, base, self.used_iris)
            self.sa_wrappers[subcomponent] = _SaWrapper(display_id, iri, parent, locations)

    def _discover_unsupported(self) -> None:
        """Drop subjects whose only SBOL 3 classes have no SBOL 2 equivalent."""
        for subject in sorted(self.types):
            sbol_types = sorted(t for t in self.types[subject] if t.startswith(S3.base))
            if not sbol_types or any(self._sbol2_type(subject, t) is not None for t in sbol_types):
                continue
            if (
                subject in self.mapstos
                or subject in self.mapsto_constraints
                or subject in self.interfaces
                or subject in self.discarded
            ):
                continue
            self.discarded.add(subject)
            self.report.warn("UnsupportedSbol3Type", subject, f"{sbol_types[0]} has no SBOL 2 equivalent; dropped")

    def _build_rewrites(self) -> None:
        """Compute the SBOL 2 identity of every subject.

        A top-level ``<ns>/<version>/<id>`` becomes ``<ns>/<id>/<version>``; a child ``<topSbol3>/<relative>``
        becomes ``<topPersistentId>/<relative>[/<version>]``; a SequenceAnnotation wrapper and its Locations nest
        under the parent's persistent identity.
        """
        subjects = sorted({s for s, _, _ in self.triples if is_iri(s) and s not in self.discarded})
        tops: List[Tuple[str, str, Optional[str]]] = []
        for iri in subjects:
            if iri not in self.top_levels:
                continue
            sbol2 = uri.create_sbol2_uri(iri)
            version: Optional[str] = uri.version_sbol3(iri) or None
            if version is not None:
                pid = sbol2[: -len(version) - 1] if sbol2.endswith("/" + version) else sbol2
                self.versions[iri] = version
                self.preserved_versions.add(iri)
                effective: Optional[str] = version
            else:
                pid = sbol2
                effective = self.options.default_version
                if effective is not None:
                    self.versions[iri] = effective
                    self.report.warn("SynthesizedVersion", iri, f"no version in the IRI; synthesized {effective!r}")
                    sbol2 = f"{pid}/{effective}"
            self.persistent_identities[iri] = pid
            self.rewrites[iri] = sbol2
            tops.append((iri, pid, effective))
        tops.sort(key=lambda top: (-len(top[0]), top[0]))

        for iri in subjects:
            if iri in self.rewrites:
                continue
            for top, pid, version in tops:
                if iri.startswith(top + "/"):
                    child_pid = f"{pid}/{iri[len(top) + 1:]}"
                    self.persistent_identities[iri] = child_pid
                    self.rewrites[iri] = f"{child_pid}/{version}" if version is not None else child_pid
                    break

        for wrapper in self.sa_wrappers.values():
            parent = wrapper.parent_component
            parent_pid = self.persistent_identities.get(parent) or self.rewrites.get(parent, parent)
            wrapper.iri_unversioned = f"{parent_pid}/{wrapper.display_id}"
            version = self._top_level_version(parent)
            for loc in wrapper.locations:
                loc_pid = f"{wrapper.iri_unversioned}/{uri.last_segment(loc)}"
                self.persistent_identities[loc] = loc_pid
                self.rewrites[loc] = f"{loc_pid}/{version}" if version is not None else loc_pid

    def _top_level_version(self, iri: str) -> Optional[str]:
        if iri in self.preserved_versions:
            return self.versions.get(iri)
        return self.options.default_version

    def _owning_top_level(self, iri: str) -> Optional[str]:
        if iri in self.top_levels:
            return iri
        owners = [top for top in self.top_levels if iri.startswith(top + "/")]
        return min(owners, key=lambda top: (-len(top), top)) if owners else None

    def _version_for(self, iri: str) -> Optional[str]:
        top = self._owning_top_level(iri)
        version = self._top_level_version(top) if top is not None else None
        return version if version is not None else self.options.default_version

    # Type resolution

    def _component_type(self, component: str) -> Optional[str]:
        if component not in self.is_md:
            return None
        return S2.ModuleDefinition if self.is_md[component] else S2.ComponentDefinition

    def _sbol2_type(self, subject: str, sbol3_type: str) -> Optional[str]:
        if sbol3_type == S3.SubComponent:
            return self._subcomponent_type(subject)
        if sbol3_type == S3.Component:
            return S2.ModuleDefinition if self.is_md.get(subject) else S2.ComponentDefinition
        return CLASSES.get(sbol3_type)

    def _subcomponent_type(self, subject: str) -> str:
        parent = self.feature_parent.get(subject)
        if parent is None or self._component_type(parent) != S2.ModuleDefinition:
            return S2.Component
        if subject in self.module_origin:
            return S2.Module
        target = self.subcomponent_targets.get(subject)
        if target is not None and self._component_type(target) == S2.ModuleDefinition:
            return S2.Module
        return S2.FunctionalComponent

    # Per-triple conversion

    def _rewrite(self, term):
        return self.rewrites.get(term, term) if is_iri(term) else term

    def _passthrough(self, triple: Triple) -> None:
        s, p, o = triple
        self.out.append((self._rewrite(s), p, self._rewrite(o)))

    def _handle(self, triple: Triple) -> None:
        s, p, o = triple
        if is_iri(s) and (
            s in self.mapstos or s in self.mapsto_constraints or s in self.interfaces or s in self.discarded
        ):
            return
        if is_iri(o) and (
            (p.startswith(S3.base) and o in self.discarded)
            or (p == S3.hasFeature and o in self.mapstos)
            or (p == S3.hasConstraint and o in self.mapsto_constraints)
            or (p == S3.hasInterface and o in self.interfaces)
        ):
            return
        if p.startswith(BP.base):
            return
        if p in (DCTERMS_TITLE, DCTERMS_DESCRIPTION):
            self._passthrough(triple)
        elif p == RDF_TYPE:
            self._handle_type(triple)
        elif p.startswith(S3.base):
            self._handle_sbol3_predicate(triple)
        else:
            self._passthrough(triple)

    def _handle_type(self, triple: Triple) -> None:
        s, p, o = triple
        if not is_iri(s) or not is_iri(o) or not o.startswith(S3.base):
            self._passthrough(triple)
            return
        target = self._sbol2_type(s, o)
        if target is None:
            self.report.warn("UnsupportedSbol3Type", s, f"{o} has no SBOL 2 equivalent; dropped")
            return
        subject = self._rewrite(s)
        self.out.append((subject, RDF_TYPE, target))
        if target == S2.Component:
            self.out.append((subject, S2.access, S2.public))
        elif target == S2.FunctionalComponent:
            # public when the FunctionalComponent belongs to its Component's Interface
            self.out.append((subject, S2.access, S2.public if s in self.fc_directions else S2.private))

    def _handle_sbol3_predicate(self, triple: Triple) -> None:
        s, p, o = triple
        if p == S3.hasNamespace:
            return  # implicit in the SBOL 2 persistentIdentity
        if p == S3.hasFeature:
            self._handle_has_feature(triple)
            return
        if is_iri(s):
            if p == S3.hasLocation and s in self.sa_wrappers:
                return  # the SequenceAnnotation wrapper carries the location
            if p in (S3.type, S3.hasSequence) and self.is_md.get(s):
                return  # ComponentDefinition-only properties
            is_location = self.resolved_types.get(s) in LOCATION_TYPES
            if p == S3.hasSequence and is_location and s in self.null_sequence_locations:
                return  # inferred or synthesized by the upgrade
            if p == S3.orientation and not is_location:
                return  # SBOL 2 carries orientation only on Locations
            if p in (S3.name, S3.description):
                dcterms = DCTERMS_TITLE if p == S3.name else DCTERMS_DESCRIPTION
                if (s, dcterms, o) in self.dcterms:
                    return
        target = PREDICATES.get(p)
        if p == S3.member and is_iri(s) and S2.Experiment in self.resolved_type_sets.get(s, ()):
            target = S2.experimentalData
        if target is None:
            return  # SBOL 3-only data has no SBOL 2 home
        self.out.append((self._rewrite(s), target, self._reverse_value(s, p, self._rewrite(o))))

    def _handle_has_feature(self, triple: Triple) -> None:
        s, _, o = triple
        parent_type = self.resolved_types.get(s) if is_iri(s) else None
        feature_type = self.resolved_types.get(o) if is_iri(o) else None
        if parent_type == S2.ModuleDefinition and feature_type in (S2.Component, S2.FunctionalComponent, S2.Module):
            target = self.subcomponent_targets.get(o)
            target_type = self.resolved_types.get(target) if target is not None else None
            predicate = S2.module if target_type == S2.ModuleDefinition else S2.functionalComponent
        elif feature_type == S2.SequenceAnnotation:
            predicate = S2.sequenceAnnotation
        else:
            predicate = S2.component
        self.out.append((self._rewrite(s), predicate, self._rewrite(o)))

    def _reverse_value(self, subject, predicate: str, value: Term) -> Term:
        """The SBOL 2 spelling of an enumerated value or ontology term."""
        if not is_iri(value):
            return value
        resolved = self.resolved_type_sets.get(subject, set()) if is_iri(subject) else set()
        if predicate == S3.type:
            if S2.Interaction in resolved:
                return uri.convert_sbo_3_to_2(value)
            return SBO_TO_BIOPAX.get(value) or uri.component_type_3_to_2(value)
        if predicate == S3.role:
            if S2.Participation in resolved:
                return uri.convert_sbo_3_to_2(value)
            return uri.convert_so_3_to_2(value)
        if predicate == S3.framework:
            return uri.convert_sbo_3_to_2(value)
        if predicate == S3.language:
            return uri.convert_edam_3_to_2(value)
        mapped = downgrade_value(predicate, value)
        return mapped if mapped is not None else value

    # Synthesis

    def _emit_sa_wrappers(self) -> None:
        for subcomponent in sorted(self.sa_wrappers):
            wrapper = self.sa_wrappers[subcomponent]
            version = self._top_level_version(wrapper.parent_component)
            sa = (
                uri.append_segment(wrapper.iri_unversioned, version) if version is not None else wrapper.iri_unversioned
            )
            self.out += [
                (self._rewrite(wrapper.parent_component), S2.sequenceAnnotation, sa),
                (sa, RDF_TYPE, S2.SequenceAnnotation),
                (sa, S2.displayId, plain(wrapper.display_id)),
                (sa, S2.component, self._rewrite(subcomponent)),
            ]
            self.out += [(sa, S2.location, self._rewrite(loc)) for loc in wrapper.locations]
            self.out.append((sa, S2.persistentIdentity, wrapper.iri_unversioned))
            if version is not None:
                self.out.append((sa, S2.version, plain(version)))

    def _emit_mapstos(self) -> None:
        """Rebuild each SBOL 2 MapsTo under its carrier's SBOL 2 identity."""
        for cref in sorted(self.mapstos):
            info = self.mapstos[cref]
            top = self._owning_top_level(info.carrier)
            version = self._top_level_version(top) if top is not None else self.options.default_version
            carrier = self._rewrite(info.carrier)
            carrier_version = uri.version_sbol2(carrier)
            carrier_base = carrier
            if carrier_version and carrier.endswith("/" + carrier_version):
                carrier_base = carrier[: -len(carrier_version) - 1]
            display_id, unversioned = uri.next_available_child_iri(carrier_base, info.display_id, self.used_iris)
            mapsto = uri.append_segment(unversioned, version) if version is not None else unversioned
            self.out += [
                (carrier, S2.mapsTo, mapsto),
                (mapsto, RDF_TYPE, S2.MapsTo),
                (mapsto, S2.displayId, plain(display_id)),
                (mapsto, S2.local, self._rewrite(info.local)),
                (mapsto, S2.remote, self._rewrite(info.remote)),
                (mapsto, S2.refinement, info.refinement or S2.useLocal),
                (mapsto, S2.persistentIdentity, unversioned),
            ]
            if version is not None:
                self.out.append((mapsto, S2.version, plain(version)))

    def _emit_directions(self) -> None:
        """Flatten Interface membership into ``access`` (and, for FunctionalComponents, ``direction``)."""
        existing = {(s, p) for s, p, _ in self.out if is_iri(s)}
        for feature in sorted(self.fc_directions):
            subject = self._rewrite(feature)
            parent_type = self.resolved_types.get(self.feature_parent.get(feature, ""))
            target = self.subcomponent_targets.get(feature)
            target_type = self.resolved_types.get(target) if target is not None else None
            if parent_type == S2.ComponentDefinition:
                kind = S2.Component
            elif parent_type == S2.ModuleDefinition:
                kind = S2.Module if target_type == S2.ModuleDefinition else S2.FunctionalComponent
            else:
                own = self.resolved_types.get(feature)
                kind = own if own in (S2.Component, S2.Module) else S2.FunctionalComponent
            if kind == S2.Module:
                continue
            self._emit_default(existing, subject, S2.access, S2.public)
            if kind == S2.FunctionalComponent:
                self._emit_default(existing, subject, S2.direction, S2.base + self.fc_directions[feature])

    def _emit_default(self, existing: Set[Tuple[str, str]], subject: str, predicate: str, value: str) -> None:
        if (subject, predicate) not in existing:
            self.out.append((subject, predicate, value))
            existing.add((subject, predicate))

    def _emit_identity_metadata(self) -> None:
        """Give every rewritten object its ``persistentIdentity`` and (when it has one) ``version``."""
        for sbol3 in sorted(self.rewrites):
            if sbol3 in self.mapstos or sbol3 in self.mapsto_constraints or sbol3 in self.interfaces:
                continue
            if sbol3 in self.discarded:
                continue
            sbol2 = self.rewrites[sbol3]
            self.out.append((sbol2, S2.persistentIdentity, self.persistent_identities.get(sbol3, sbol3)))
            version = self._version_for(sbol3)
            if version is not None:
                self.out.append((sbol2, S2.version, plain(version)))

    def _emit_instance_defaults(self) -> None:
        """Every SBOL 2 Component needs an ``access``, every FunctionalComponent an ``access`` and a ``direction``."""
        components, functional_components = set(), set()
        for s, p, o in self.out:
            if p == RDF_TYPE and is_iri(s):
                if o == S2.Component:
                    components.add(s)
                elif o == S2.FunctionalComponent:
                    functional_components.add(s)
        existing = {(s, p) for s, p, _ in self.out if is_iri(s)}
        for subject in sorted(components):
            self._emit_default(existing, subject, S2.access, S2.private)
        for subject in sorted(functional_components):
            self._emit_default(existing, subject, S2.access, S2.private)
            self._emit_default(existing, subject, S2.direction, S2.none)
