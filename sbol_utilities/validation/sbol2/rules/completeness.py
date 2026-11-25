"""The completeness family: referenced objects are present in the document and of the class the reference
requires. References are resolved by identity or persistentIdentity, as libSBOLj does."""

from __future__ import annotations

from collections.abc import Iterable

from rdflib.term import URIRef

from sbol_utilities.validation.catalog import Context
from sbol_utilities.validation.sbol2 import REGISTRY
from sbol_utilities.validation.sbol2 import spec as S
from sbol_utilities.validation.sbol2.context import Obj, Sbol2Context

_COMPLETENESS_RULES = (
    "sbol2-10604",
    "sbol2-11703",
    "sbol2-10513",
    "sbol2-11608",
    "sbol2-12103",
    "sbol2-12905",
    "sbol2-10307",
    "sbol2-13008",
    "sbol2-13010",
    "sbol2-13012",
    "sbol2-10222",
    "sbol2-12407",
    "sbol2-12604",
    "sbol2-12606",
)


def _resolvable(ctx: Sbol2Context) -> set[str]:
    uris: set[str] = set()
    for obj in ctx.objects:
        if obj.iri is not None:
            uris.add(obj.iri)
        pid = obj.first_ref(S.PERSISTENT_IDENTITY)
        if pid is not None:
            uris.add(pid)
    return uris


@REGISTRY.rule(*_COMPLETENESS_RULES)
def referenced_objects_present(context: Context) -> None:
    """Every external reference names an object held in the document."""
    ctx: Sbol2Context = context  # type: ignore[assignment]
    if not ctx.config.complete:
        return
    resolvable = _resolvable(ctx)
    for obj in ctx.sbol_objects:
        for predicate, field in obj.fields.items():
            reference = field.reference
            if reference is None or reference.local:
                continue
            rule = S.completeness_rule(predicate, reference.target)
            if rule is None:
                continue
            for value in obj.resources(predicate):
                if not (isinstance(value, URIRef) and str(value) in resolvable):
                    ctx.error(
                        rule,
                        obj,
                        f"complete document must contain the object `{value}` referenced by `{predicate}`",
                        predicate,
                    )


def _wrong_class(ctx: Sbol2Context, obj: Obj, predicate: str, accept) -> Iterable[str]:
    for iri in obj.iris(predicate):
        target = ctx.resolve(iri)
        if target is not None and not accept(target):
            yield iri


_CLASS_CHECKS = (
    (S.WAS_GENERATED_BY, (S.ACTIVITY,), "sbol2-10222"),
    (S.WAS_INFORMED_BY, (S.ACTIVITY,), "sbol2-12407"),
    (S.AGENT_P, (S.AGENT,), "sbol2-12606"),
    (S.HAD_PLAN, (S.PLAN,), "sbol2-12604"),
    (S.MODEL_P, (S.MODEL,), "sbol2-11608"),
    (S.VARIANT_COLLECTION, (S.COLLECTION,), "sbol2-13010"),
    (S.VARIANT_DERIVATION, (S.COMBINATORIAL_DERIVATION,), "sbol2-13014"),
    (S.EXPERIMENTAL_DATA_P, (S.EXPERIMENTAL_DATA,), "sbol2-13404"),
)


@REGISTRY.rule(
    "sbol2-10604",
    "sbol2-10222",
    "sbol2-12407",
    "sbol2-12604",
    "sbol2-12606",
    "sbol2-11608",
    "sbol2-13010",
    "sbol2-13014",
    "sbol2-13404",
    "sbol2-13506",
    "sbol2-10807",
    "sbol2-13103",
)
def referenced_object_classes(context: Context) -> None:
    """References resolved in the document name objects of the class the property requires."""
    ctx: Sbol2Context = context  # type: ignore[assignment]
    for obj in ctx.sbol_objects:
        if (obj.has_class(S.COMPONENT) or obj.has_class(S.FUNCTIONAL_COMPONENT)) and not obj.has_class(S.MODULE):
            for iri in _wrong_class(ctx, obj, S.DEFINITION, lambda t: t.has_class(S.COMPONENT_DEFINITION)):
                ctx.error(
                    "sbol2-10604",
                    obj,
                    f"definition refers to `{iri}`, which is not a ComponentDefinition",
                    S.DEFINITION,
                )
        for predicate, classes, rule in _CLASS_CHECKS:
            for iri in _wrong_class(ctx, obj, predicate, lambda t, cs=classes: any(t.has_class(c) for c in cs)):
                ctx.error(rule, obj, f"`{predicate}` refers to `{iri}`, which is not the required class", predicate)
        if obj.has_class(S.OM_MEASURE):
            for iri in _wrong_class(ctx, obj, S.OM_HAS_UNIT, lambda t: any(t.has_class(c) for c in S.UNIT_CLASSES)):
                ctx.error("sbol2-13506", obj, f"the hasUnit of a Measure `{iri}` must refer to a Unit", S.OM_HAS_UNIT)
        if obj.has_class(S.MAPS_TO):
            for iri in _wrong_class(ctx, obj, S.REMOTE, lambda t: t.lists(S.ACCESS, S.PUBLIC)):
                ctx.error("sbol2-10807", obj, f"the MapsTo remote `{iri}` must have public access", S.REMOTE)
        if obj.has_class(S.IMPLEMENTATION):
            for iri in obj.iris(S.BUILT):
                target = ctx.resolve(iri)
                if target is None or not (
                    target.has_class(S.COMPONENT_DEFINITION) or target.has_class(S.MODULE_DEFINITION)
                ):
                    ctx.error(
                        "sbol2-13103",
                        obj,
                        f"built refers to `{iri}`, which is not a ComponentDefinition or ModuleDefinition",
                        S.BUILT,
                    )
