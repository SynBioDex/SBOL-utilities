"""Model, Implementation, and Attachment rules (sbol3-123xx, 125xx, 128xx).

External content (Model and Attachment sources) is never fetched: with external validation off the availability
rules stay silent, and otherwise they report that no content resolver is configured.
"""

from __future__ import annotations

from rdflib.term import Node, URIRef

from sbol_utilities.validation.sbol3 import REGISTRY, spec
from sbol_utilities.validation.sbol3.context import (
    EXTERNAL_OFF,
    HASH_CONSERVATIVE,
    HASH_STRICT,
    SBOL3Context,
    SbolObject,
)
from sbol_utilities.validation.sbol3.helpers import (
    canonical_model_framework_iri,
    canonical_model_language_iri,
    is_edam_format_term,
    is_hash_algorithm_token,
    is_hex_digest,
    is_known_hash_algorithm,
    is_known_non_edam_namespace,
    is_sbo_modeling_framework_term,
    parse_i64,
)


def _check_external_content(ctx: SBOL3Context, obj: SbolObject, rule: str) -> None:
    source = obj.first_iri(spec.SOURCE)
    if source is None or ctx.external_mode == EXTERNAL_OFF:
        return
    ctx.warning(rule, obj, spec.SOURCE, f"source `{source}` was not checked because no content resolver was configured")


@REGISTRY.rule("sbol3-12501", "sbol3-12503", "sbol3-12504", "sbol3-12506", "sbol3-12507")
def models(ctx: SBOL3Context) -> None:
    """Model source availability, Table 15 / 16 aliases, and ontology branches of language and framework."""
    for obj in ctx.instances(spec.MODEL):
        _check_external_content(ctx, obj, "sbol3-12501")
        for language in obj.iris(spec.LANGUAGE):
            text = str(language)
            canonical = canonical_model_language_iri(text)
            if canonical is not None and canonical.lower() != text.lower():
                ctx.error(
                    "sbol3-12503",
                    obj,
                    spec.LANGUAGE,
                    f"Model language `{text}` is equivalent to Table 15 URI `{canonical}`",
                )
            if is_known_non_edam_namespace(ctx.ontology, text):
                ctx.warning(
                    "sbol3-12504", obj, spec.LANGUAGE, f"Model language `{text}` should refer to an EDAM ontology term"
                )
        for framework in obj.iris(spec.FRAMEWORK):
            text = str(framework)
            canonical = canonical_model_framework_iri(text)
            if canonical is not None and canonical.lower() != text.lower():
                ctx.error(
                    "sbol3-12506",
                    obj,
                    spec.FRAMEWORK,
                    f"Model framework `{text}` is equivalent to Table 16 URI `{canonical}`",
                )
            if is_sbo_modeling_framework_term(ctx.ontology, text) is False:
                ctx.warning(
                    "sbol3-12507",
                    obj,
                    spec.FRAMEWORK,
                    f"Model framework `{text}` should refer to a term from the SBO modeling framework branch "
                    "(SBO:0000004)",
                )


@REGISTRY.rule("sbol3-12301", "sbol3-12302")
def implementations(ctx: SBOL3Context) -> None:
    """Implementation derivations refer to Components whose types do not conflict."""
    for obj in ctx.instances(spec.IMPLEMENTATION):
        components: list[SbolObject] = []
        for derived_from in obj.derived_from():
            target = ctx.get(derived_from)
            if target is None:
                continue
            if not target.has_class(spec.COMPONENT):
                ctx.error(
                    "sbol3-12301",
                    obj,
                    spec.PROV_WAS_DERIVED_FROM,
                    f"Implementation prov:wasDerivedFrom `{derived_from}` must refer to a Component",
                )
                continue
            components.append(target)
        if len(components) < 2:
            continue
        typed: list[tuple[Node, URIRef]] = [(c.identity, t) for c in components for t in c.iris(spec.TYPE)]
        for index, (left_component, left_type) in enumerate(typed):
            for right_component, right_type in typed[index + 1 :]:
                if left_component == right_component:
                    continue
                if ctx.ontology.terms_conflict(str(left_type), str(right_type)) is True:
                    ctx.error(
                        "sbol3-12302",
                        obj,
                        spec.PROV_WAS_DERIVED_FROM,
                        f"Implementation prov:wasDerivedFrom Components have conflicting types: `{left_component}` "
                        f"has `{left_type}` while `{right_component}` has `{right_type}`",
                    )


@REGISTRY.rule("sbol3-12801", "sbol3-12803", "sbol3-12804", "sbol3-12805", "sbol3-12806", "sbol3-12807", "sbol3-12808")
def attachments(ctx: SBOL3Context) -> None:
    """Attachment size, hash, hash algorithm, format, and source availability."""
    for obj in ctx.instances(spec.ATTACHMENT):
        for size in obj.literals(spec.SIZE):
            value = parse_i64(str(size))
            if value is not None and value < 0:
                ctx.error("sbol3-12804", obj, spec.SIZE, "Attachment size must be a nonnegative byte count")
        for digest in obj.literals(spec.HASH):
            if not is_hex_digest(str(digest)):
                ctx.error("sbol3-12805", obj, spec.HASH, "Attachment hash must be a nonempty hexadecimal digest")
        for algorithm in obj.literals(spec.HASH_ALGORITHM):
            value_text = str(algorithm)
            if ctx.hash_algorithm_registry == HASH_CONSERVATIVE and not is_hash_algorithm_token(value_text):
                ctx.warning(
                    "sbol3-12806",
                    obj,
                    spec.HASH_ALGORITHM,
                    "Attachment hashAlgorithm should be a registry-style hash algorithm token",
                )
                continue
            if ctx.hash_algorithm_registry == HASH_STRICT and not is_known_hash_algorithm(value_text):
                ctx.error(
                    "sbol3-12806",
                    obj,
                    spec.HASH_ALGORITHM,
                    f"Attachment hashAlgorithm `{value_text}` is not in the known set "
                    "(sha2-256, sha3-256, blake3, sha2-512, sha3-512)",
                )
                continue
            if value_text != "sha3-256":
                ctx.warning("sbol3-12807", obj, spec.HASH_ALGORITHM, "Attachment hashAlgorithm should be sha3-256")
        for fmt in obj.iris(spec.FORMAT):
            if is_edam_format_term(ctx.ontology, str(fmt)) is False:
                ctx.warning(
                    "sbol3-12803", obj, spec.FORMAT, "Attachment format should refer to a term from the EDAM ontology"
                )
        if obj.values(spec.HASH) and not obj.values(spec.HASH_ALGORITHM):
            ctx.error("sbol3-12808", obj, spec.HASH_ALGORITHM, "Attachment hash requires hashAlgorithm")
        _check_external_content(ctx, obj, "sbol3-12801")
