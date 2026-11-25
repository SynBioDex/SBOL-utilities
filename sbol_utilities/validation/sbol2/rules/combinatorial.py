"""CombinatorialDerivation and VariableComponent rules, and the best practices relating derived designs and
Collections to the derivation they come from."""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable, Iterator

from sbol_utilities.validation.sbol2 import spec as S
from sbol_utilities.validation.sbol2.context import Sbol2Context, Sbol2Object
from sbol_utilities.validation.sbol2.helpers import definition_cycles
from sbol_utilities.validation.sbol2.registry import REGISTRY


@REGISTRY.rule("sbol2-12903", "sbol2-12907")
def variable_components(ctx: Sbol2Context) -> None:
    """An enumerate derivation uses bounded operators, and no two VariableComponents share a variable."""
    for obj in ctx.instances(S.COMBINATORIAL_DERIVATION):
        variable_components = list(ctx.referenced(obj, S.VARIABLE_COMPONENT_P))
        if S.ENUMERATE in obj.iris(S.STRATEGY) and any(
            op in (S.OP_ZERO_OR_MORE, S.OP_ONE_OR_MORE) for vc in variable_components for op in vc.iris(S.OPERATOR)
        ):
            ctx.report(
                "sbol2-12903",
                obj,
                "an enumerate CombinatorialDerivation must not use a zeroOrMore or oneOrMore operator",
                property=S.STRATEGY,
            )
        variables = [v for vc in variable_components if (v := vc.first_iri(S.VARIABLE)) is not None]
        if len(set(variables)) < len(variables):
            ctx.report(
                "sbol2-12907",
                obj,
                "two VariableComponents of a CombinatorialDerivation must not share a variable",
                property=S.VARIABLE_COMPONENT_P,
            )


@REGISTRY.rule("sbol2-13015")
def variant_derivation_cycles(ctx: Sbol2Context) -> None:
    """CombinatorialDerivations do not form a cycle through their VariableComponents' variantDerivations."""
    for obj in definition_cycles(ctx, S.COMBINATORIAL_DERIVATION, S.VARIABLE_COMPONENT_P, S.VARIANT_DERIVATION):
        ctx.report(
            "sbol2-13015",
            obj,
            "a CombinatorialDerivation must not form a cycle through its variantDerivations",
            property=S.VARIABLE_COMPONENT_P,
        )


@REGISTRY.rule("sbol2-12909", "sbol2-13006")
def derivation_contents(ctx: Sbol2Context) -> None:
    """A derivation's template has Components, and each of its VariableComponents names a source of variants."""
    for obj in ctx.instances(S.COMBINATORIAL_DERIVATION):
        template = ctx.resolve(obj.first_iri(S.TEMPLATE))
        if template is not None and not template.resources(S.COMPONENT_P):
            ctx.report(
                "sbol2-12909", obj, "a CombinatorialDerivation template should contain Components", property=S.TEMPLATE
            )
        for vc in ctx.referenced(obj, S.VARIABLE_COMPONENT_P):
            if not any(vc.resources(p) for p in (S.VARIANT, S.VARIANT_COLLECTION, S.VARIANT_DERIVATION)):
                ctx.report(
                    "sbol2-13006",
                    vc,
                    "a VariableComponent should specify at least one variant source",
                    property=S.VARIANT,
                )


def template_derivations(ctx: Sbol2Context, definition: Sbol2Object) -> Iterator[tuple[Sbol2Object, Sbol2Object]]:
    """Each CombinatorialDerivation a ComponentDefinition derives from, with that derivation's template."""
    for _, derivation in ctx.resolved(definition, S.WAS_DERIVED_FROM):
        if derivation.has_class(S.COMBINATORIAL_DERIVATION):
            template = ctx.resolve(derivation.first_iri(S.TEMPLATE))
            if template is not None:
                yield derivation, template


@REGISTRY.rule("sbol2-12910", "sbol2-12911", "sbol2-13018")
def derived_types_and_roles(ctx: Sbol2Context) -> None:
    """A derived ComponentDefinition keeps its template's types and roles, and its Components the roles of the
    template Components they derive from."""
    for obj in ctx.instances(S.COMPONENT_DEFINITION):
        for _, template in template_derivations(ctx, obj):
            if set(obj.iris(S.TYPE)) != set(template.iris(S.TYPE)):
                ctx.report(
                    "sbol2-12910",
                    obj,
                    "a derived ComponentDefinition should keep its template's types",
                    property=S.TYPE,
                )
            if set(obj.iris(S.ROLE)) != set(template.iris(S.ROLE)):
                ctx.report(
                    "sbol2-12911",
                    obj,
                    "a derived ComponentDefinition should keep its template's roles",
                    property=S.ROLE,
                )
            template_components = set(template.iris(S.COMPONENT_P))
            for component in ctx.referenced(obj, S.COMPONENT_P):
                for source in component.iris(S.WAS_DERIVED_FROM):
                    template_component = ctx.get(source) if source in template_components else None
                    if template_component is not None and set(component.iris(S.ROLE)) != set(
                        template_component.iris(S.ROLE)
                    ):
                        ctx.report(
                            "sbol2-13018",
                            obj,
                            "a derived Component should keep its template Component's roles",
                            property=S.ROLE,
                        )


#: (VariableComponent operator, rule, whether a number of realizations satisfies it, message)
OPERATOR_COUNTS: tuple[tuple[str, str, Callable[[int], bool], str], ...] = (
    (
        S.OP_ZERO_OR_ONE,
        "sbol2-13019",
        lambda n: n <= 1,
        "a zeroOrOne VariableComponent should be realized at most once",
    ),
    (S.OP_ONE, "sbol2-13020", lambda n: n == 1, "a one VariableComponent should be realized exactly once"),
    (
        S.OP_ONE_OR_MORE,
        "sbol2-13021",
        lambda n: n >= 1,
        "a oneOrMore VariableComponent should be realized at least once",
    ),
)


@REGISTRY.rule("sbol2-13022", *(rule for _, rule, _, _ in OPERATOR_COUNTS))
def derived_component_counts(ctx: Sbol2Context) -> None:
    """A derived ComponentDefinition realizes each template Component once, and each variable as often as its
    operator allows."""
    for obj in ctx.instances(S.COMPONENT_DEFINITION):
        realized = Counter(
            source
            for component in ctx.referenced(obj, S.COMPONENT_P)
            for source in set(component.iris(S.WAS_DERIVED_FROM))
        )
        for derivation, template in template_derivations(ctx, obj):
            variable_components = list(ctx.referenced(derivation, S.VARIABLE_COMPONENT_P))
            variables = {v for vc in variable_components if (v := vc.first_iri(S.VARIABLE)) is not None}
            if any(realized[c] != 1 for c in template.iris(S.COMPONENT_P) if c not in variables):
                ctx.report(
                    "sbol2-13022",
                    obj,
                    "a non-replaced template Component should be realized exactly once",
                    property=S.COMPONENT_P,
                )
            for vc in variable_components:
                variable, operator = vc.first_iri(S.VARIABLE), vc.first_iri(S.OPERATOR)
                if variable is None:
                    continue
                for required, rule, satisfied, message in OPERATOR_COUNTS:
                    if operator == required and not satisfied(realized[variable]):
                        ctx.report(rule, obj, message, property=S.COMPONENT_P)


def combinatorial_sources(ctx: Sbol2Context, obj: Sbol2Object) -> set[str]:
    """The CombinatorialDerivations, held in the document, that ``obj`` records deriving from."""
    return {
        iri for iri, source in ctx.resolved(obj, S.WAS_DERIVED_FROM) if source.has_class(S.COMBINATORIAL_DERIVATION)
    }


@REGISTRY.rule("sbol2-12912", "sbol2-12913")
def derived_collections(ctx: Sbol2Context) -> None:
    """A Collection and its members record deriving from the same CombinatorialDerivations."""
    for obj in ctx.instances(S.COLLECTION):
        members = [member for _, member in ctx.resolved(obj, S.MEMBER)]
        own = set(obj.iris(S.WAS_DERIVED_FROM))
        derivations = combinatorial_sources(ctx, obj)
        if any(not derivations <= set(member.iris(S.WAS_DERIVED_FROM)) for member in members):
            ctx.report(
                "sbol2-12913",
                obj,
                "a Collection's members should derive from the same CombinatorialDerivation",
                property=S.MEMBER,
            )
        if any(not combinatorial_sources(ctx, member) <= own for member in members):
            ctx.report(
                "sbol2-12912",
                obj,
                "a Collection should record the CombinatorialDerivation its members derive from",
                property=S.MEMBER,
            )
