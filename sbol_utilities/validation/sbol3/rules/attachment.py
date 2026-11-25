"""Model, Implementation, and Attachment rules (sbol3-123xx, 125xx, 128xx).

External content (Model and Attachment sources) is never fetched, so the source-availability rules are not checked.
"""

from __future__ import annotations

from itertools import combinations

from sbol_utilities.validation.config import Severity
from sbol_utilities.validation.datatypes import parse_i64
from sbol_utilities.validation.sbol3 import spec
from sbol_utilities.validation.sbol3.context import Sbol3Context, Sbol3Object
from sbol_utilities.validation.sbol3.helpers import (
    SBO_MODELING_FRAMEWORK,
    canonical_model_framework_iri,
    canonical_model_language_iri,
    is_edam_format_term,
    is_hash_algorithm_token,
    is_hex_digest,
    is_known_non_edam_namespace,
)
from sbol_utilities.validation.sbol3.registry import REGISTRY


@REGISTRY.rule("sbol3-12503", "sbol3-12504", "sbol3-12506", "sbol3-12507")
def models(ctx: Sbol3Context) -> None:
    """Model Table 15 / 16 aliases and the ontology branches of language and framework."""
    for obj in ctx.instances(spec.MODEL):
        for language in obj.iris(spec.LANGUAGE):
            text = str(language)
            canonical = canonical_model_language_iri(text)
            if canonical is not None and canonical.lower() != text.lower():
                ctx.report(
                    "sbol3-12503",
                    obj,
                    f"Model language `{text}` is equivalent to Table 15 URI `{canonical}`",
                    property=spec.LANGUAGE,
                )
            if is_known_non_edam_namespace(ctx.ontology, text):
                ctx.report(
                    "sbol3-12504",
                    obj,
                    f"Model language `{text}` should refer to an EDAM ontology term",
                    property=spec.LANGUAGE,
                )
        for framework in obj.iris(spec.FRAMEWORK):
            text = str(framework)
            canonical = canonical_model_framework_iri(text)
            if canonical is not None and canonical.lower() != text.lower():
                ctx.report(
                    "sbol3-12506",
                    obj,
                    f"Model framework `{text}` is equivalent to Table 16 URI `{canonical}`",
                    property=spec.FRAMEWORK,
                )
            if ctx.ontology.in_branch_if_known(text, SBO_MODELING_FRAMEWORK) is False:
                ctx.report(
                    "sbol3-12507",
                    obj,
                    f"Model framework `{text}` should refer to a term from the SBO modeling framework branch "
                    "(SBO:0000004)",
                    property=spec.FRAMEWORK,
                )


@REGISTRY.rule("sbol3-12301", "sbol3-12302")
def implementations(ctx: Sbol3Context) -> None:
    """An Implementation derives from Components, and those Components' types do not conflict."""
    for obj in ctx.instances(spec.IMPLEMENTATION):
        components: list[Sbol3Object] = []
        for source in ctx.referenced(obj, spec.PROV_WAS_DERIVED_FROM):
            if source.has_class(spec.COMPONENT):
                components.append(source)
            else:
                ctx.report(
                    "sbol3-12301",
                    obj,
                    f"Implementation prov:wasDerivedFrom `{source.identity}` must refer to a Component",
                    property=spec.PROV_WAS_DERIVED_FROM,
                )
        typed = [(component.identity, type_iri) for component in components for type_iri in component.iris(spec.TYPE)]
        for (left_component, left_type), (right_component, right_type) in combinations(typed, 2):
            if left_component != right_component and ctx.ontology.terms_conflict(str(left_type), str(right_type)):
                ctx.report(
                    "sbol3-12302",
                    obj,
                    f"Implementation prov:wasDerivedFrom Components have conflicting types: `{left_component}` "
                    f"has `{left_type}` while `{right_component}` has `{right_type}`",
                    property=spec.PROV_WAS_DERIVED_FROM,
                )


@REGISTRY.rule("sbol3-12803", "sbol3-12804", "sbol3-12805", "sbol3-12806", "sbol3-12807", "sbol3-12808")
def attachments(ctx: Sbol3Context) -> None:
    """Attachment size, hash, hash algorithm, and format."""
    for obj in ctx.instances(spec.ATTACHMENT):
        for size in obj.literals(spec.SIZE):
            value = parse_i64(str(size))
            if value is not None and value < 0:
                ctx.report("sbol3-12804", obj, "Attachment size must be a nonnegative byte count", property=spec.SIZE)
        for digest in obj.literals(spec.HASH):
            if not is_hex_digest(str(digest)):
                ctx.report(
                    "sbol3-12805", obj, "Attachment hash must be a nonempty hexadecimal digest", property=spec.HASH
                )
        for algorithm in obj.literals(spec.HASH_ALGORITHM):
            value_text = str(algorithm)
            if not is_hash_algorithm_token(value_text):
                ctx.report(
                    "sbol3-12806",
                    obj,
                    "Attachment hashAlgorithm should be a registry-style hash algorithm token",
                    property=spec.HASH_ALGORITHM,
                    severity=Severity.WARNING,
                )
                continue
            if value_text != "sha3-256":
                ctx.report(
                    "sbol3-12807", obj, "Attachment hashAlgorithm should be sha3-256", property=spec.HASH_ALGORITHM
                )
        for fmt in obj.iris(spec.FORMAT):
            if is_edam_format_term(ctx.ontology, str(fmt)) is False:
                ctx.report(
                    "sbol3-12803",
                    obj,
                    "Attachment format should refer to a term from the EDAM ontology",
                    property=spec.FORMAT,
                )
        if obj.values(spec.HASH) and not obj.values(spec.HASH_ALGORITHM):
            ctx.report("sbol3-12808", obj, "Attachment hash requires hashAlgorithm", property=spec.HASH_ALGORITHM)
