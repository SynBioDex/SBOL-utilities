"""CombinatorialDerivation, VariableFeature, and ComponentReference rules (sbol3-109xx, 121xx, 122xx)."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterator
from itertools import product

from rdflib.term import Node

from sbol_utilities.validation.sbol3 import spec
from sbol_utilities.validation.sbol3.context import Sbol3Context, Sbol3Object
from sbol_utilities.validation.sbol3.registry import REGISTRY
from sbol_utilities.validation.sbol3.resolver import (
    DerivationContext,
    Outcome,
    TraceError,
    allowed_variants,
    cardinality_allows,
    collection_contains_only_components_or_collections,
    component_contains,
    derivation_context,
    derived_objects,
    feature_properties_match,
    features_derived_from,
    parent_reference,
    reference_is_child_of,
    table8_relation,
    table10_relation,
    trace_feature,
    type_properties,
)


def _iri_set(obj: Sbol3Object, predicate: str) -> set[str]:
    return {str(i) for i in obj.iris(predicate)}


@REGISTRY.rule("sbol3-12101", "sbol3-12102", "sbol3-12103")
def derivation_strategy_and_variables(ctx: Sbol3Context) -> None:
    """A derivation's strategy is an SBOL strategy, an enumerate derivation has bounded cardinalities, and no two
    VariableFeatures share a variable."""
    for obj in ctx.instances(spec.COMBINATORIAL_DERIVATION):
        variable_features = list(ctx.referenced(obj, spec.HAS_VARIABLE_FEATURE))
        strategy = obj.first_iri(spec.STRATEGY)
        if strategy is not None and str(strategy) not in spec.STRATEGY_IRIS:
            ctx.report(
                "sbol3-12101", obj, f"unsupported CombinatorialDerivation strategy `{strategy}`", property=spec.STRATEGY
            )
        if strategy is not None and str(strategy) == spec.ENUMERATE:
            for variable_feature in variable_features:
                if str(variable_feature.first_iri(spec.CARDINALITY)) in (
                    spec.ZERO_OR_MORE_VALUE,
                    spec.ONE_OR_MORE_VALUE,
                ):
                    ctx.report(
                        "sbol3-12102",
                        variable_feature,
                        "enumerate strategy cannot use zeroOrMore or oneOrMore cardinality",
                        property=spec.CARDINALITY,
                    )
        variables = Counter(
            variable
            for variable_feature in variable_features
            if (variable := variable_feature.first_resource(spec.VARIABLE)) is not None
        )
        for variable, count in variables.items():
            if count > 1:
                ctx.report(
                    "sbol3-12103",
                    obj,
                    f"duplicate VariableFeature variable `{variable}`",
                    property=spec.HAS_VARIABLE_FEATURE,
                )


def _derivations(ctx: Sbol3Context) -> Iterator[tuple[DerivationContext, Sbol3Object]]:
    """Each CombinatorialDerivation whose template is in the document, with that template."""
    for derivation in ctx.instances(spec.COMBINATORIAL_DERIVATION):
        context = derivation_context(ctx, derivation)
        template = None if context is None else ctx.get(context.template)
        if context is not None and template is not None:
            yield context, template


def _derived_components(ctx: Sbol3Context) -> Iterator[tuple[DerivationContext, Sbol3Object, Sbol3Object]]:
    """Each Component derived from a CombinatorialDerivation, with the derivation and its template."""
    for context, template in _derivations(ctx):
        for derived in derived_objects(ctx, context.derivation, spec.COMPONENT):
            yield context, template, derived


@REGISTRY.rule("sbol3-12104", "sbol3-12106")
def templates_and_collections(ctx: Sbol3Context) -> None:
    """A derivation's template has Features, and the members of a Collection derived from it derive from it too."""
    for context, _ in _derivations(ctx):
        if not context.template_features:
            ctx.report(
                "sbol3-12104",
                context.derivation,
                "CombinatorialDerivation template Component should contain at least one Feature",
                property=spec.TEMPLATE,
            )
        for collection in derived_objects(ctx, context.derivation, spec.COLLECTION):
            for member in ctx.referenced(collection, spec.MEMBER):
                if context.derivation not in member.resources(spec.PROV_WAS_DERIVED_FROM):
                    ctx.report(
                        "sbol3-12106",
                        collection,
                        f"Collection member `{member.identity}` should derive from CombinatorialDerivation "
                        f"`{context.derivation}`",
                        property=spec.MEMBER,
                    )


@REGISTRY.rule("sbol3-12105", "sbol3-12107", "sbol3-12108")
def derived_components(ctx: Sbol3Context) -> None:
    """A derived Component keeps its template's types and roles, and each of its Features derives from a Feature
    of the template."""
    for context, template, derived in _derived_components(ctx):
        for feature in derived.resources(spec.HAS_FEATURE):
            feature_obj = ctx.get(feature)
            sources = () if feature_obj is None else feature_obj.resources(spec.PROV_WAS_DERIVED_FROM)
            if context.template_features.isdisjoint(sources):
                ctx.report(
                    "sbol3-12105",
                    feature,
                    f"derived Feature should derive from a Feature in template Component `{context.template}`",
                    property=spec.PROV_WAS_DERIVED_FROM,
                )
        for predicate, rule, name in ((spec.TYPE, "sbol3-12107", "type"), (spec.ROLE, "sbol3-12108", "role")):
            if not _iri_set(template, predicate) <= _iri_set(derived, predicate):
                ctx.report(
                    rule,
                    derived,
                    f"derived Component should include all {name} values from template Component "
                    f"`{context.template}`",
                    property=predicate,
                )


@REGISTRY.rule("sbol3-12109", "sbol3-12110")
def derived_static_features(ctx: Sbol3Context) -> None:
    """Each template Feature that is not a variable has one derived Feature, which keeps its properties."""
    for context, _, derived in _derived_components(ctx):
        for static_feature in context.static_features:
            matching = features_derived_from(ctx, derived, static_feature)
            if len(matching) != 1:
                ctx.report(
                    "sbol3-12110",
                    derived,
                    f"static template Feature `{static_feature}` should have exactly one derived Feature",
                    property=spec.HAS_FEATURE,
                )
            template_feature = ctx.get(static_feature)
            for derived_feature in matching:
                if template_feature is not None and not feature_properties_match(derived_feature, template_feature):
                    ctx.report(
                        "sbol3-12109",
                        derived_feature,
                        f"Feature derived from static template Feature `{static_feature}` must preserve its local "
                        "Feature properties",
                        property=spec.PROV_WAS_DERIVED_FROM,
                    )


@REGISTRY.rule("sbol3-12111", "sbol3-12112", "sbol3-12114", "sbol3-12115")
def derived_variable_features(ctx: Sbol3Context) -> None:
    """The Features derived from a variable template Feature are as many as its VariableFeature's cardinality
    allows, instantiate allowed variants, and keep the template Feature's roles and types."""
    for context, _, derived in _derived_components(ctx):
        for template_feature, variable_feature_id in context.variables.items():
            variable_feature = ctx.get(variable_feature_id)
            if variable_feature is None:
                continue
            matching = features_derived_from(ctx, derived, template_feature)
            if not cardinality_allows(variable_feature.first_iri(spec.CARDINALITY), len(matching)):
                ctx.report(
                    "sbol3-12111",
                    derived,
                    f"derived Feature count for variable template Feature `{template_feature}` should satisfy its "
                    "VariableFeature cardinality",
                    property=spec.HAS_FEATURE,
                )
            allowed = allowed_variants(ctx, variable_feature)
            template_feature_obj = ctx.get(template_feature)
            template_roles = set() if template_feature_obj is None else _iri_set(template_feature_obj, spec.ROLE)
            template_types = type_properties(ctx, template_feature)
            for derived_feature in matching:
                instance_of = (
                    derived_feature.first_resource(spec.INSTANCE_OF)
                    if derived_feature.has_class(spec.SUB_COMPONENT)
                    else None
                )
                if instance_of is not None and instance_of not in allowed:
                    ctx.report(
                        "sbol3-12112",
                        derived_feature,
                        f"derived SubComponent instanceOf `{instance_of}` must be a variant allowed by "
                        f"VariableFeature `{variable_feature_id}`",
                        property=spec.INSTANCE_OF,
                    )
                if not template_roles <= _iri_set(derived_feature, spec.ROLE):
                    ctx.report(
                        "sbol3-12114",
                        derived_feature,
                        f"derived Feature should include all role values from variable template Feature "
                        f"`{template_feature}`",
                        property=spec.ROLE,
                    )
                derived_types = type_properties(ctx, derived_feature.identity)
                if template_types is not None and derived_types is not None and not template_types <= derived_types:
                    ctx.report(
                        "sbol3-12115",
                        derived_feature,
                        f"derived Feature type-determining referent should include all type values from template "
                        f"Feature `{template_feature}`",
                        property=spec.TYPE,
                    )


@REGISTRY.rule("sbol3-12113")
def derived_constraints(ctx: Sbol3Context) -> None:
    """The Features derived from the subject and object of a template Constraint satisfy its restriction."""
    for context, template, derived in _derived_components(ctx):
        for constraint in ctx.referenced(template, spec.HAS_CONSTRAINT):
            restriction = constraint.first_iri(spec.RESTRICTION)
            template_subject = constraint.first_resource(spec.SUBJECT)
            template_object = constraint.first_resource(spec.OBJECT)
            if restriction is None or template_subject is None or template_object is None:
                continue
            pairs = product(
                features_derived_from(ctx, derived, template_subject),
                features_derived_from(ctx, derived, template_object),
            )
            for derived_subject, derived_object in pairs:
                relations = (
                    table8_relation(ctx, str(restriction), derived_subject.identity, derived_object.identity),
                    table10_relation(ctx, str(restriction), derived_subject.identity, derived_object.identity),
                )
                if any(relation.outcome is Outcome.CONTRADICTED for relation in relations):
                    ctx.report(
                        "sbol3-12113",
                        derived,
                        f"derived Features `{derived_subject.identity}` and `{derived_object.identity}` must satisfy "
                        f"template Constraint `{constraint.identity}`",
                        property=spec.HAS_CONSTRAINT,
                    )


@REGISTRY.rule("sbol3-12201", "sbol3-12202", "sbol3-12203")
def variable_features(ctx: Sbol3Context) -> None:
    """VariableFeature cardinality, variable containment, and variantCollection membership."""
    for obj in ctx.instances(spec.VARIABLE_FEATURE):
        cardinality = obj.first_iri(spec.CARDINALITY)
        if cardinality is not None and str(cardinality) not in spec.CARDINALITY_IRIS:
            ctx.report(
                "sbol3-12201",
                obj,
                f"unsupported VariableFeature cardinality `{cardinality}`",
                property=spec.CARDINALITY,
            )
        derivation = ctx.parent(obj, spec.HAS_VARIABLE_FEATURE)
        template = None if derivation is None else derivation.first_resource(spec.TEMPLATE)
        variable = obj.first_resource(spec.VARIABLE)
        if template is not None and variable is not None:
            if not component_contains(ctx, template, spec.HAS_FEATURE, variable):
                ctx.report(
                    "sbol3-12202",
                    obj,
                    "VariableFeature variable must be a Feature of the template Component",
                    property=spec.VARIABLE,
                )
        for collection in obj.resources(spec.VARIANT_COLLECTION):
            if not collection_contains_only_components_or_collections(ctx, collection, set()):
                ctx.report(
                    "sbol3-12203",
                    obj,
                    f"variantCollection `{collection}` contains a member that is not a Component or Collection",
                    property=spec.VARIANT_COLLECTION,
                )


@REGISTRY.rule("sbol3-10901")
def reference_sub_components(ctx: Sbol3Context) -> None:
    """A ComponentReference's inChildOf is a SubComponent of the Component holding the reference."""
    for obj in ctx.instances(spec.COMPONENT_REFERENCE):
        component = ctx.parent(obj, spec.HAS_FEATURE)
        in_child_of = obj.first_resource(spec.IN_CHILD_OF)
        if (
            component is not None
            and in_child_of is not None
            and not ctx.ownership.contains(component.identity, spec.HAS_FEATURE, in_child_of)
        ):
            ctx.report(
                "sbol3-10901",
                obj,
                "ComponentReference inChildOf must be a SubComponent of its parent Component",
                property=spec.IN_CHILD_OF,
            )


def _instantiated_component(ctx: Sbol3Context, sub_component: Node | None) -> Node | None:
    """The Component a SubComponent held in the document instantiates."""
    obj = ctx.get(sub_component)
    return None if obj is None else obj.first_resource(spec.INSTANCE_OF)


@REGISTRY.rule("sbol3-10902", "sbol3-10903", "sbol3-10904")
def reference_targets(ctx: Sbol3Context) -> None:
    """A ComponentReference reaches into the Component its inChildOf instantiates: a nested reference's inChildOf
    and every reference's refersTo are Features of the Component reached so far, and refersTo chains end."""
    for obj in ctx.instances(spec.COMPONENT_REFERENCE):
        in_child_of = obj.first_resource(spec.IN_CHILD_OF)
        enclosing = parent_reference(ctx, obj)
        enclosing_in_child_of = None if enclosing is None else enclosing.first_resource(spec.IN_CHILD_OF)
        if enclosing_in_child_of is not None:
            reached = _instantiated_component(ctx, enclosing_in_child_of)
            if reached is None:
                # nothing is decidable below a reference whose own SubComponent or its Component is not in the document
                continue
            if in_child_of is not None and not component_contains(ctx, reached, spec.HAS_FEATURE, in_child_of):
                ctx.report(
                    "sbol3-10902",
                    obj,
                    "nested ComponentReference inChildOf must be a SubComponent of the referenced Component",
                    property=spec.IN_CHILD_OF,
                )
        referenced_component = _instantiated_component(ctx, in_child_of)
        refers_to = obj.first_resource(spec.REFERS_TO)
        target = ctx.get(refers_to)
        if referenced_component is None or refers_to is None or target is None:
            continue
        in_referenced_component = component_contains(ctx, referenced_component, spec.HAS_FEATURE, refers_to)
        if trace_feature(ctx, obj.identity).error is TraceError.CYCLE:
            ctx.report(
                "sbol3-10903", obj, "ComponentReference refersTo chain must not form a cycle", property=spec.REFERS_TO
            )
        elif not target.has_class(spec.COMPONENT_REFERENCE):
            if not in_referenced_component:
                ctx.report(
                    "sbol3-10904",
                    obj,
                    "ComponentReference refersTo target must be a Feature of the referenced Component",
                    property=spec.REFERS_TO,
                )
        elif not in_referenced_component and not reference_is_child_of(ctx, refers_to, obj.identity):
            ctx.report(
                "sbol3-10903",
                obj,
                "ComponentReference refersTo target must be a permitted ComponentReference child",
                property=spec.REFERS_TO,
            )
