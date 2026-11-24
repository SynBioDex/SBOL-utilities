"""CombinatorialDerivation and VariableComponent rules, and the best practices relating derived designs and
Collections to the derivation they come from."""

from __future__ import annotations

from typing import List, Optional, Set, Tuple

from sbol_utilities.validation.catalog import Context
from sbol_utilities.validation.sbol2 import REGISTRY
from sbol_utilities.validation.sbol2 import spec as S
from sbol_utilities.validation.sbol2.context import Obj, Sbol2Context
from sbol_utilities.validation.sbol2.rules.component import definition_cycles


@REGISTRY.rule("sbol2-12903", "sbol2-12907")
def variable_components(context: Context) -> None:
    """An enumerate derivation uses bounded operators, and no two VariableComponents share a variable."""
    ctx: Sbol2Context = context  # type: ignore[assignment]
    for obj in ctx.sbol_objects:
        if not obj.has_class(S.COMBINATORIAL_DERIVATION):
            continue
        variable_components = list(ctx.children(obj, S.VARIABLE_COMPONENT_P))
        if S.ENUMERATE in obj.iris(S.STRATEGY) and any(
            op in (S.OP_ZERO_OR_MORE, S.OP_ONE_OR_MORE) for vc in variable_components for op in vc.iris(S.OPERATOR)
        ):
            ctx.error(
                "sbol2-12903",
                obj,
                "an enumerate CombinatorialDerivation must not use a zeroOrMore or oneOrMore operator",
                S.STRATEGY,
            )
        variables: Set[str] = set()
        duplicate = False
        for vc in variable_components:
            variable = vc.first_ref(S.VARIABLE)
            if variable is not None:
                if variable in variables:
                    duplicate = True
                variables.add(variable)
        if duplicate:
            ctx.error(
                "sbol2-12907",
                obj,
                "two VariableComponents of a CombinatorialDerivation must not share a variable",
                S.VARIABLE_COMPONENT_P,
            )


@REGISTRY.rule("sbol2-13015")
def variant_derivation_cycles(context: Context) -> None:
    """CombinatorialDerivations do not form a cycle through their VariableComponents' variantDerivations."""
    ctx: Sbol2Context = context  # type: ignore[assignment]
    for obj in definition_cycles(ctx, S.COMBINATORIAL_DERIVATION, S.VARIABLE_COMPONENT_P, S.VARIANT_DERIVATION):
        ctx.error(
            "sbol2-13015",
            obj,
            "a CombinatorialDerivation must not form a cycle through its variantDerivations",
            S.VARIABLE_COMPONENT_P,
        )


_MESSAGES = {
    "sbol2-12909": "a CombinatorialDerivation template should contain Components",
    "sbol2-13006": "a VariableComponent should specify at least one variant source",
    "sbol2-12910": "a derived ComponentDefinition should keep its template's types",
    "sbol2-12911": "a derived ComponentDefinition should keep its template's roles",
    "sbol2-13018": "a derived Component should keep its template Component's roles",
    "sbol2-13019": "a zeroOrOne VariableComponent should be realized at most once",
    "sbol2-13020": "a one VariableComponent should be realized exactly once",
    "sbol2-13021": "a oneOrMore VariableComponent should be realized at least once",
    "sbol2-13022": "a non-replaced template Component should be realized exactly once",
    "sbol2-12912": "a Collection should record the CombinatorialDerivation its members derive from",
    "sbol2-12913": "a Collection's members should derive from the same CombinatorialDerivation",
}

Finding = Tuple[str, Obj, str]


@REGISTRY.rule(*_MESSAGES)
def combinatorial_best_practices(context: Context) -> None:
    """Templates have Components, variables have variants, and derived designs and Collections follow their
    CombinatorialDerivation."""
    ctx: Sbol2Context = context  # type: ignore[assignment]
    if not ctx.config.best_practice:
        return
    for obj in ctx.sbol_objects:
        findings: List[Finding] = []
        if obj.has_class(S.COMBINATORIAL_DERIVATION):
            template = ctx.resolve(obj.first_ref(S.TEMPLATE))
            if template is not None and not template.resources(S.COMPONENT_P):
                findings.append(("sbol2-12909", obj, S.TEMPLATE))
            for vc in ctx.children(obj, S.VARIABLE_COMPONENT_P):
                if not (
                    vc.resources(S.VARIANT) or vc.resources(S.VARIANT_COLLECTION) or vc.resources(S.VARIANT_DERIVATION)
                ):
                    findings.append(("sbol2-13006", vc, S.VARIANT))
        if obj.has_class(S.COMPONENT_DEFINITION):
            _derived_definition_findings(ctx, obj, findings)
        if obj.has_class(S.COLLECTION):
            _collection_findings(ctx, obj, findings)
        for rule, subject, prop in findings:
            ctx.warning(rule, subject, _MESSAGES[rule], prop)


def _child_by_identity(ctx: Sbol2Context, parent: Obj, predicate: str, identity: str) -> Optional[Obj]:
    return ctx.get(identity) if identity in parent.iris(predicate) else None


def _count_derived_from(ctx: Sbol2Context, obj: Obj, source: str) -> int:
    return sum(1 for component in ctx.children(obj, S.COMPONENT_P) if component.lists(S.WAS_DERIVED_FROM, source))


def _derived_definition_findings(ctx: Sbol2Context, obj: Obj, findings: List[Finding]) -> None:
    for iri in obj.iris(S.WAS_DERIVED_FROM):
        derivation = ctx.resolve(iri)
        if derivation is None or not derivation.has_class(S.COMBINATORIAL_DERIVATION):
            continue
        template = ctx.resolve(derivation.first_ref(S.TEMPLATE))
        if template is None:
            continue
        if set(obj.iris(S.TYPE)) != set(template.iris(S.TYPE)):
            findings.append(("sbol2-12910", obj, S.TYPE))
        if set(obj.iris(S.ROLE)) != set(template.iris(S.ROLE)):
            findings.append(("sbol2-12911", obj, S.ROLE))
        for component in ctx.children(obj, S.COMPONENT_P):
            for source in component.iris(S.WAS_DERIVED_FROM):
                template_component = _child_by_identity(ctx, template, S.COMPONENT_P, source)
                if template_component is not None and set(component.iris(S.ROLE)) != set(
                    template_component.iris(S.ROLE)
                ):
                    findings.append(("sbol2-13018", obj, S.ROLE))
        variable_components = list(ctx.children(derivation, S.VARIABLE_COMPONENT_P))
        replaced = {v for v in (vc.first_ref(S.VARIABLE) for vc in variable_components) if v is not None}
        for template_component_id in template.iris(S.COMPONENT_P):
            if template_component_id in replaced:
                continue
            if _count_derived_from(ctx, obj, template_component_id) != 1:
                findings.append(("sbol2-13022", obj, S.COMPONENT_P))
        for vc in variable_components:
            variable = vc.first_ref(S.VARIABLE)
            if variable is None:
                continue
            operator = vc.first_ref(S.OPERATOR)
            count = _count_derived_from(ctx, obj, variable)
            if operator == S.OP_ZERO_OR_ONE and count > 1:
                findings.append(("sbol2-13019", obj, S.COMPONENT_P))
            elif operator == S.OP_ONE and count != 1:
                findings.append(("sbol2-13020", obj, S.COMPONENT_P))
            elif operator == S.OP_ONE_OR_MORE and count == 0:
                findings.append(("sbol2-13021", obj, S.COMPONENT_P))


def _is_combinatorial(ctx: Sbol2Context, iri: str) -> bool:
    target = ctx.resolve(iri)
    return target is not None and target.has_class(S.COMBINATORIAL_DERIVATION)


def _collection_findings(ctx: Sbol2Context, obj: Obj, findings: List[Finding]) -> None:
    members = [m for m in (ctx.resolve(iri) for iri in obj.iris(S.MEMBER)) if m is not None]
    for iri in obj.iris(S.WAS_DERIVED_FROM):
        if not _is_combinatorial(ctx, iri):
            continue
        for member in members:
            if not member.lists(S.WAS_DERIVED_FROM, iri):
                findings.append(("sbol2-12913", obj, S.MEMBER))
    for member in members:
        for iri in member.iris(S.WAS_DERIVED_FROM):
            if _is_combinatorial(ctx, iri) and not obj.lists(S.WAS_DERIVED_FROM, iri):
                findings.append(("sbol2-12912", obj, S.MEMBER))
