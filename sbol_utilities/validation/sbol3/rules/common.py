"""Identified / TopLevel rules (sbol3-101xx, 102xx, 103xx): vocabulary, types, structure, and URL patterns."""

from __future__ import annotations

from collections import defaultdict
from itertools import combinations

from rdflib.term import URIRef

from sbol_utilities.identifiers import is_valid_display_id
from sbol_utilities.validation.sbol3 import spec
from sbol_utilities.validation.sbol3.context import Sbol3Context, Sbol3Object
from sbol_utilities.validation.sbol3.helpers import is_url, url_matches_namespace_display_id
from sbol_utilities.validation.sbol3.registry import REGISTRY
from sbol_utilities.validation.sbol3.structural import check_object
from sbol_utilities.vocab import RDF_TYPE, SBOL3_NS


@REGISTRY.rule("sbol3-10105", "sbol3-10108", "sbol3-10109")
def sbol_vocabulary(ctx: Sbol3Context) -> None:
    """Unknown SBOL types and properties, properties not allowed for the type, and untyped SBOL subjects."""
    for obj in ctx.objects.values():
        for rdf_type in obj.rdf_types:
            if rdf_type.startswith(SBOL3_NS) and not spec.is_known_sbol_iri(rdf_type):
                ctx.report("sbol3-10105", obj, f"unknown SBOL rdf:type `{rdf_type}`", property=RDF_TYPE)
        has_sbol_property = any(p.startswith(SBOL3_NS) for p in obj.properties)
        has_sbol_type = any(t.startswith(SBOL3_NS) for t in obj.rdf_types)
        if has_sbol_property and not has_sbol_type:
            ctx.report("sbol3-10108", obj, "object has SBOL properties but no SBOL rdf:type")
        allowed = spec.SCHEMA.properties_for(obj.rdf_types)
        for predicate in sorted(obj.properties):
            if not predicate.startswith(SBOL3_NS):
                continue
            if predicate not in spec.SCHEMA.predicates:
                ctx.report("sbol3-10105", obj, f"unknown SBOL property `{predicate}`")
            elif predicate not in allowed:
                ctx.report("sbol3-10109", obj, f"property `{predicate}` is not allowed for the object's SBOL type")


@REGISTRY.rule("sbol3-10106", "sbol3-10107")
def sbol_types(ctx: Sbol3Context) -> None:
    """Disjoint SBOL class combinations and multiple concrete classes."""
    for obj in ctx.objects.values():
        classes = obj.declared_classes
        for left, right in combinations(classes, 2):
            if not spec.SCHEMA.is_a(left, right) and not spec.SCHEMA.is_a(right, left):
                ctx.report(
                    "sbol3-10106",
                    obj,
                    f"SBOL rdf:type values `{spec.local_name(left)}` and `{spec.local_name(right)}` are disjoint",
                    property=RDF_TYPE,
                )
        concrete = [c for c in classes if c not in (spec.IDENTIFIED, spec.TOP_LEVEL)]
        if len(concrete) > 1:
            ctx.report("sbol3-10107", obj, "object has more than one concrete SBOL rdf:type", property=RDF_TYPE)


@REGISTRY.rule("sbol3-10110", "sbol3-10111", "sbol3-10112", "sbol3-10113")
def table_rules(ctx: Sbol3Context) -> None:
    """Table 23 cardinality, value kinds, and reference targets."""
    for obj in ctx.objects.values():
        check_object(ctx, obj)


@REGISTRY.rule("sbol3-10201", "sbol3-10202")
def display_id(ctx: Sbol3Context) -> None:
    """displayId lexical form and self-derivation."""
    for obj in ctx.objects.values():
        if obj.display_id is None:
            continue
        if not is_valid_display_id(obj.display_id):
            ctx.report(
                "sbol3-10201",
                obj,
                f"displayId `{obj.display_id}` must start with a letter or underscore and contain only letters, "
                "digits, or underscores",
                property=spec.DISPLAY_ID,
            )
        if obj.identity in obj.resources(spec.PROV_WAS_DERIVED_FROM):
            ctx.report(
                "sbol3-10202",
                obj,
                "object must not refer to itself via prov:wasDerivedFrom",
                property=spec.PROV_WAS_DERIVED_FROM,
            )


@REGISTRY.rule("sbol3-10101", "sbol3-10301")
def top_level_namespace(ctx: Sbol3Context) -> None:
    """TopLevel identities are IRIs prefixed by their namespace."""
    for obj in ctx.instances(spec.TOP_LEVEL):
        if not isinstance(obj.identity, URIRef):
            ctx.report("sbol3-10101", obj, "Identified object identities must be IRIs")
            continue
        namespace = obj.first_iri(spec.HAS_NAMESPACE)
        identity = str(obj.identity)
        if namespace is None or not is_url(identity):
            continue
        base = str(namespace).rstrip("/")
        if identity != base and not identity.startswith(base + "/"):
            ctx.report(
                "sbol3-10301",
                obj,
                f"TopLevel URL `{identity}` is not prefixed by namespace `{base}`",
                property=spec.HAS_NAMESPACE,
            )


def _top_level_urls(ctx: Sbol3Context) -> list[tuple[str, Sbol3Object]]:
    """Each TopLevel whose identity is a URL, with that URL."""
    return [
        (str(obj.identity), obj)
        for obj in ctx.instances(spec.TOP_LEVEL)
        if isinstance(obj.identity, URIRef) and is_url(str(obj.identity))
    ]


@REGISTRY.rule("sbol3-10102")
def top_level_url_pattern(ctx: Sbol3Context) -> None:
    """A TopLevel URL is ``[namespace]/[local]/[displayId]``."""
    for identity, obj in _top_level_urls(ctx):
        namespace = obj.first_iri(spec.HAS_NAMESPACE)
        if namespace is None:
            continue
        if obj.display_id is None:
            ctx.report(
                "sbol3-10102",
                obj,
                "TopLevel URL objects require displayId to satisfy the URL pattern",
                property=spec.DISPLAY_ID,
            )
        elif not url_matches_namespace_display_id(identity, str(namespace), obj.display_id):
            ctx.report("sbol3-10102", obj, f"TopLevel URL `{identity}` does not match [namespace]/[local]/[displayId]")


@REGISTRY.rule("sbol3-10103")
def top_level_url_prefixes(ctx: Sbol3Context) -> None:
    """No TopLevel URL lies under another TopLevel's URL."""
    top_levels = _top_level_urls(ctx)
    by_base: dict[str, list[str]] = defaultdict(list)
    for identity, _ in top_levels:
        by_base[identity.rstrip("/")].append(identity)
    for identity, obj in top_levels:
        for position, character in enumerate(identity):
            if character != "/":
                continue
            for other in by_base.get(identity[:position], ()):
                if other != identity:
                    ctx.report("sbol3-10103", obj, f"TopLevel URL `{identity}` uses TopLevel URL `{other}` as a prefix")


@REGISTRY.rule("sbol3-10104")
def child_urls(ctx: Sbol3Context) -> None:
    """Child URLs are ``[parent URL]/[displayId]``."""
    for parent in ctx.objects.values():
        if not isinstance(parent.identity, URIRef):
            continue
        for predicate in spec.COMPOSITE_PREDICATES:
            for child in parent.resources(predicate):
                child_obj = ctx.get(child)
                if child_obj is None or not isinstance(child, URIRef) or not is_url(str(child)):
                    continue
                if child_obj.display_id is None:
                    ctx.report(
                        "sbol3-10104",
                        child_obj,
                        "child URL objects require displayId to satisfy the URL pattern",
                        property=spec.DISPLAY_ID,
                    )
                    continue
                expected = f"{str(parent.identity).rstrip('/')}/{child_obj.display_id}"
                if str(child) != expected:
                    ctx.report(
                        "sbol3-10104", child_obj, f"child URL `{child}` does not match expected URL `{expected}`"
                    )
