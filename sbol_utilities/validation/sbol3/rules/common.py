"""Identified / TopLevel rules (sbol3-101xx, 102xx, 103xx): vocabulary, types, structure, and URL patterns."""

from __future__ import annotations

from rdflib.term import URIRef

from sbol_utilities.identifiers import is_valid_display_id
from sbol_utilities.validation.sbol3 import spec
from sbol_utilities.validation.sbol3.context import SBOL3Context
from sbol_utilities.validation.sbol3.helpers import is_url, url_is_child_of, url_matches_namespace_display_id
from sbol_utilities.validation.sbol3.registry import REGISTRY
from sbol_utilities.validation.sbol3.structural import check_object
from sbol_utilities.vocab import RDF_TYPE, SBOL3_NS


@REGISTRY.rule("sbol3-10105", "sbol3-10108", "sbol3-10109")
def sbol_vocabulary(ctx: SBOL3Context) -> None:
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
def sbol_types(ctx: SBOL3Context) -> None:
    """Disjoint SBOL class combinations and multiple concrete classes."""
    for obj in ctx.objects.values():
        classes = obj.classes
        for index, left in enumerate(classes):
            for right in classes[index + 1 :]:
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
def table_rules(ctx: SBOL3Context) -> None:
    """Table 23 cardinality, value kinds, and reference targets."""
    for obj in ctx.objects.values():
        check_object(ctx, obj)


@REGISTRY.rule("sbol3-10201", "sbol3-10202")
def display_id(ctx: SBOL3Context) -> None:
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
        if obj.identity in obj.derived_from():
            ctx.report(
                "sbol3-10202",
                obj,
                "object must not refer to itself via prov:wasDerivedFrom",
                property=spec.PROV_WAS_DERIVED_FROM,
            )


@REGISTRY.rule("sbol3-10101", "sbol3-10301")
def top_level_namespace(ctx: SBOL3Context) -> None:
    """TopLevel identities are IRIs prefixed by their namespace."""
    for obj in ctx.objects.values():
        if not obj.is_top_level:
            continue
        if not isinstance(obj.identity, URIRef):
            ctx.report("sbol3-10101", obj, "Identified object identities must be IRIs")
            continue
        namespace = obj.first_iri(spec.HAS_NAMESPACE)
        if namespace is None:
            continue
        identity = str(obj.identity)
        if is_url(identity):
            base = str(namespace).rstrip("/")
            if identity != base and not identity.startswith(base + "/"):
                ctx.report(
                    "sbol3-10301",
                    obj,
                    f"TopLevel URL `{identity}` is not prefixed by namespace `{base}`",
                    property=spec.HAS_NAMESPACE,
                )


@REGISTRY.rule("sbol3-10102", "sbol3-10103")
def top_level_urls(ctx: SBOL3Context) -> None:
    """TopLevel URL pattern and URL prefix collisions between TopLevels."""
    top_levels = [
        (str(o.identity), o)
        for o in ctx.objects.values()
        if o.is_top_level and isinstance(o.identity, URIRef) and is_url(str(o.identity))
    ]
    for index, (left_identity, left) in enumerate(top_levels):
        namespace = left.first_iri(spec.HAS_NAMESPACE)
        if namespace is not None:
            if left.display_id is None:
                ctx.report(
                    "sbol3-10102",
                    left,
                    "TopLevel URL objects require displayId to satisfy the URL pattern",
                    property=spec.DISPLAY_ID,
                )
            elif not url_matches_namespace_display_id(left_identity, str(namespace), left.display_id):
                ctx.report(
                    "sbol3-10102",
                    left,
                    f"TopLevel URL `{left_identity}` does not match [namespace]/[local]/[displayId]",
                )
        for right_identity, right in top_levels[index + 1 :]:
            if url_is_child_of(right_identity, left_identity):
                ctx.report(
                    "sbol3-10103",
                    right,
                    f"TopLevel URL `{right_identity}` uses TopLevel URL `{left_identity}` as a prefix",
                )
            if url_is_child_of(left_identity, right_identity):
                ctx.report(
                    "sbol3-10103",
                    left,
                    f"TopLevel URL `{left_identity}` uses TopLevel URL `{right_identity}` as a prefix",
                )


@REGISTRY.rule("sbol3-10104")
def child_urls(ctx: SBOL3Context) -> None:
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
