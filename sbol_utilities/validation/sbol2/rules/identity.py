"""Identified and TopLevel rules: identity syntax, persistentIdentity classes, the document namespace,
wasDerivedFrom cycles and version order, and the compliant-URI family."""

from __future__ import annotations

from sbol_utilities.identifiers import is_valid_display_id
from sbol_utilities.validation.graphs import nodes_on_cycles
from sbol_utilities.validation.sbol2 import spec as S
from sbol_utilities.validation.sbol2.context import Sbol2Context, Sbol2Object
from sbol_utilities.validation.sbol2.registry import REGISTRY
from sbol_utilities.vocab import PROV_NS, SBOL2_NS

DELIMITERS = ("/", "#", ":")


def is_valid_version(version: str) -> bool:
    """SBOL 2 version lexical form: alphanumerics, underscore, hyphen, or period, beginning with a digit."""
    if not version or not ("0" <= version[0] <= "9"):
        return False
    return all(c.isascii() and (c.isalnum() or c in "_-.") for c in version[1:])


@REGISTRY.rule("sbol2-10201", "sbol2-10204", "sbol2-10206", "sbol2-10228")
def identity_syntax(ctx: Sbol2Context) -> None:
    """Identities are URIs; displayId and version are lexically valid; at most one SBOL and one PROV rdf:type."""
    for obj in ctx.sbol_objects:
        if obj.iri is None:
            ctx.report("sbol2-10201", obj, "the identity of an Identified object must be a URI")
        if obj.display_id is not None and not is_valid_display_id(obj.display_id):
            ctx.report(
                "sbol2-10204",
                obj,
                f"displayId `{obj.display_id}` must contain only alphanumeric or underscore characters and must "
                "not begin with a digit",
                property=S.DISPLAY_ID,
            )
        version = obj.first_literal(S.VERSION)
        if version is not None and not is_valid_version(version):
            ctx.report(
                "sbol2-10206", obj, f"version `{version}` is not a valid SBOL 2 version string", property=S.VERSION
            )
        sbol_types = sum(1 for t in obj.rdf_types if t.startswith(SBOL2_NS))
        prov_types = sum(1 for t in obj.rdf_types if t.startswith(PROV_NS))
        if sbol_types > 1 or prov_types > 1:
            ctx.report(
                "sbol2-10228",
                obj,
                "an Identified object must have no more than one rdfType in each of the SBOL 2 and PROV namespaces",
            )


@REGISTRY.rule("sbol2-10220")
def persistent_identity_classes(ctx: Sbol2Context) -> None:
    """Objects sharing a persistentIdentity are instances of the same class."""
    classes: dict[str, set[str]] = {}
    for obj in ctx.objects:
        pid = obj.first_iri(S.PERSISTENT_IDENTITY)
        if pid is not None:
            classes.setdefault(pid, set()).add(",".join(obj.rdf_types))
    for obj in ctx.objects:
        pid = obj.first_iri(S.PERSISTENT_IDENTITY)
        if pid is not None and len(classes[pid]) > 1:
            ctx.report(
                "sbol2-10220",
                obj,
                f"objects sharing persistentIdentity `{pid}` must be instances of the same class",
                property=S.PERSISTENT_IDENTITY,
            )


@REGISTRY.rule("sbol2-10101")
def document_namespace(ctx: Sbol2Context) -> None:
    """A non-empty document names SBOL 2 properties or classes (its SBOL prefix is bound to the SBOL 2 namespace)."""
    if ctx.triple_count and not ctx.uses_sbol2_namespace:
        ctx.report("sbol2-10101", SBOL2_NS, f"an SBOL document must declare and use the SBOL 2 namespace `{SBOL2_NS}`")


@REGISTRY.rule("sbol2-10303", "sbol2-10304")
def derivation_cycles(ctx: Sbol2Context) -> None:
    """A TopLevel does not derive from itself, directly or through a wasDerivedFrom chain of TopLevels."""
    graph: dict[str, list[str]] = {}
    for obj in ctx.objects:
        if not obj.is_top_level or obj.iri is None:
            continue
        successors = []
        for target in obj.iris(S.WAS_DERIVED_FROM):
            source = ctx.get(target)
            if source is not None and source.is_top_level:
                successors.append(target)
        graph[obj.iri] = successors
    cyclic = nodes_on_cycles(graph, lambda node: graph.get(node, ()))
    for obj in ctx.sbol_objects:
        if not obj.is_top_level or obj.iri is None:
            continue
        if obj.iri in obj.iris(S.WAS_DERIVED_FROM):
            ctx.report("sbol2-10303", obj, "a TopLevel must not derive from itself", property=S.WAS_DERIVED_FROM)
        if obj.iri in cyclic:
            ctx.report(
                "sbol2-10304",
                obj,
                "TopLevel objects must not form a circular wasDerivedFrom chain",
                property=S.WAS_DERIVED_FROM,
            )


def version_precedes(earlier: str, later: str) -> bool:
    """Whether ``earlier`` strictly precedes ``later``: dot-separated parts compared numerically when both are
    numeric, lexically otherwise."""
    left, right = earlier.split("."), later.split(".")
    for a, b in zip(left, right):
        if a.isascii() and a.isdigit() and b.isascii() and b.isdigit() and len(a) <= 20 and len(b) <= 20:
            x, y = int(a), int(b)
            if x < 2**64 and y < 2**64:
                if x != y:
                    return x < y
                continue
        if a != b:
            return a.encode("utf-8") < b.encode("utf-8")
    return len(left) < len(right)


@REGISTRY.rule("sbol2-10302")
def derivation_version_order(ctx: Sbol2Context) -> None:
    """A TopLevel deriving from a same-persistentIdentity TopLevel carries a later version."""
    for obj in ctx.sbol_objects:
        if not obj.is_top_level:
            continue
        pid = obj.first_iri(S.PERSISTENT_IDENTITY)
        version = obj.first_literal(S.VERSION)
        if pid is None or version is None:
            continue
        for target in obj.iris(S.WAS_DERIVED_FROM):
            source = ctx.resolve(target)
            if source is None or not source.is_top_level or source.first_iri(S.PERSISTENT_IDENTITY) != pid:
                continue
            source_version = source.first_literal(S.VERSION)
            if source_version is not None and not version_precedes(source_version, version):
                ctx.report(
                    "sbol2-10302",
                    obj,
                    "a derived TopLevel's source version should precede its own version",
                    property=S.VERSION,
                )


def ends_with_delimited(uri: str, tail: str) -> bool:
    """Whether ``uri`` ends with a delimiter immediately followed by ``tail``."""
    return uri.endswith(tail) and uri[: len(uri) - len(tail)].endswith(DELIMITERS)


def is_delimited_suffix(full: str, base: str, suffix: str) -> bool:
    """Whether ``full`` is ``base`` + a delimiter + ``suffix``."""
    if not full.startswith(base):
        return False
    rest = full[len(base) :]
    if not rest.endswith(suffix):
        return False
    return rest[: len(rest) - len(suffix)] in DELIMITERS


@REGISTRY.rule("sbol2-10215", "sbol2-10216", "sbol2-10218")
def compliant_identities(ctx: Sbol2Context) -> None:
    """Compliant objects carry a displayId, and their identity derives from persistentIdentity and version."""
    for obj in ctx.sbol_objects:
        display_id = obj.display_id
        if display_id is None:
            ctx.report("sbol2-10215", obj, "a compliant Identified object requires a displayId", property=S.DISPLAY_ID)
            continue
        pid = obj.first_iri(S.PERSISTENT_IDENTITY)
        identity = obj.iri
        version = obj.first_literal(S.VERSION)
        if obj.is_top_level:
            if pid is None:
                ctx.report(
                    "sbol2-10216",
                    obj,
                    "a compliant TopLevel requires a persistentIdentity",
                    property=S.PERSISTENT_IDENTITY,
                )
            elif not ends_with_delimited(pid, display_id):
                ctx.report(
                    "sbol2-10216",
                    obj,
                    f"compliant TopLevel persistentIdentity `{pid}` must end with a delimiter followed by displayId "
                    f"`{display_id}`",
                    property=S.PERSISTENT_IDENTITY,
                )
        if pid is not None and identity is not None:
            ok = identity == pid or (version is not None and is_delimited_suffix(identity, pid, version))
            if not ok:
                ctx.report(
                    "sbol2-10218",
                    obj,
                    f"compliant identity `{identity}` must equal persistentIdentity `{pid}` (optionally followed by "
                    "a delimiter and version)",
                )


def parent_map(ctx: Sbol2Context) -> dict[str, str]:
    """Composite child identity -> identity of the object holding it through a local-reference property."""
    parents: dict[str, str] = {}
    for obj in ctx.objects:
        if obj.iri is None:
            continue
        for predicate, declared in obj.property_specs.items():
            if declared.reference is None or not declared.reference.local:
                continue
            for child in obj.iris(predicate):
                parents[child] = obj.iri
    return parents


@REGISTRY.rule("sbol2-10217", "sbol2-10219")
def compliant_children(ctx: Sbol2Context) -> None:
    """A compliant child's persistentIdentity extends its parent's, and the two share a version."""
    parents = parent_map(ctx)
    for obj in ctx.sbol_objects:
        if obj.is_top_level or obj.iri is None:
            continue
        parent_id = parents.get(obj.iri)
        display_id = obj.display_id
        if parent_id is None or display_id is None:
            continue
        parent: Sbol2Object | None = ctx.resolve(parent_id)
        if parent is None:
            continue
        child_pid = obj.first_iri(S.PERSISTENT_IDENTITY)
        parent_pid = parent.first_iri(S.PERSISTENT_IDENTITY)
        if child_pid is None:
            ctx.report(
                "sbol2-10217",
                obj,
                "a compliant child object requires a persistentIdentity",
                property=S.PERSISTENT_IDENTITY,
            )
        elif parent_pid is not None and child_pid not in [f"{parent_pid}{d}{display_id}" for d in DELIMITERS]:
            ctx.report(
                "sbol2-10217",
                obj,
                f"compliant child persistentIdentity `{child_pid}` must extend parent persistentIdentity "
                f"`{parent_pid}` with displayId `{display_id}`",
                property=S.PERSISTENT_IDENTITY,
            )
        if parent.first_literal(S.VERSION) != obj.first_literal(S.VERSION):
            ctx.report(
                "sbol2-10219",
                obj,
                "a compliant child object must have the same version as its parent",
                property=S.VERSION,
            )
