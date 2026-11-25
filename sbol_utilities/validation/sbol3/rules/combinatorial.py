"""CombinatorialDerivation, VariableFeature, and ComponentReference rules (sbol3-109xx, 121xx, 122xx)."""

from __future__ import annotations

from rdflib.term import Node

from sbol_utilities.validation.sbol3 import REGISTRY, spec
from sbol_utilities.validation.sbol3.context import SBOL3Context, SbolObject
from sbol_utilities.validation.sbol3.helpers import (
    collection_contains_only_components_or_collections,
    component_contains,
)
from sbol_utilities.validation.sbol3.resolver import (
    CONTRADICTED,
    allowed_variants,
    cardinality_allows,
    derivation_context,
    derived_objects,
    feature_derives_from_template,
    features_derived_from,
    parent_reference,
    reference_is_child_of,
    static_feature_properties_match,
    table8_relation,
    table10_relation,
    trace_feature,
    type_properties,
)


def _iri_set(obj: SbolObject, predicate: str) -> set[str]:
    return {str(i) for i in obj.iris(predicate)}


def _roles_of(ctx: SBOL3Context, feature: Node) -> set[str]:
    obj = ctx.get(feature)
    return set() if obj is None else _iri_set(obj, spec.ROLE)


def _derivation_semantics(ctx: SBOL3Context, derivation: SbolObject) -> None:
    context = derivation_context(ctx, derivation)
    if context is None:
        return
    template = ctx.get(context.template)
    if template is None:
        return
    if not context.template_features:
        ctx.warning(
            "sbol3-12104",
            derivation,
            spec.TEMPLATE,
            "CombinatorialDerivation template Component should contain at least one Feature",
        )
    template_types = _iri_set(template, spec.TYPE)
    template_roles = _iri_set(template, spec.ROLE)

    for collection in derived_objects(ctx, context.derivation, spec.COLLECTION):
        for member in collection.resources(spec.MEMBER):
            member_obj = ctx.get(member)
            if member_obj is not None and context.derivation not in member_obj.derived_from():
                ctx.warning(
                    "sbol3-12106",
                    collection,
                    spec.MEMBER,
                    f"Collection member `{member}` should derive from CombinatorialDerivation `{context.derivation}`",
                )

    template_constraints = [c for c in (ctx.get(i) for i in template.resources(spec.HAS_CONSTRAINT)) if c is not None]
    for derived in derived_objects(ctx, context.derivation, spec.COMPONENT):
        for feature in derived.resources(spec.HAS_FEATURE):
            if not feature_derives_from_template(ctx, feature, context.template_features):
                ctx.warning(
                    "sbol3-12105",
                    feature,
                    spec.PROV_WAS_DERIVED_FROM,
                    f"derived Feature should derive from a Feature in template Component `{context.template}`",
                )
        if not template_types <= _iri_set(derived, spec.TYPE):
            ctx.warning(
                "sbol3-12107",
                derived,
                spec.TYPE,
                f"derived Component should include all type values from template Component `{context.template}`",
            )
        if not template_roles <= _iri_set(derived, spec.ROLE):
            ctx.warning(
                "sbol3-12108",
                derived,
                spec.ROLE,
                f"derived Component should include all role values from template Component `{context.template}`",
            )
        for static_feature in context.static_features:
            matching = features_derived_from(ctx, derived, static_feature)
            if len(matching) != 1:
                ctx.warning(
                    "sbol3-12110",
                    derived,
                    spec.HAS_FEATURE,
                    f"static template Feature `{static_feature}` should have exactly one derived Feature",
                )
            for derived_feature in matching:
                if static_feature_properties_match(ctx, derived_feature, static_feature) is False:
                    ctx.error(
                        "sbol3-12109",
                        derived_feature,
                        spec.PROV_WAS_DERIVED_FROM,
                        f"Feature derived from static template Feature `{static_feature}` must preserve its local "
                        "Feature properties",
                    )
        for template_feature, variable_feature_id in context.variables.items():
            matching = features_derived_from(ctx, derived, template_feature)
            variable_feature = ctx.get(variable_feature_id)
            if variable_feature is None:
                continue
            if not cardinality_allows(variable_feature.first_iri(spec.CARDINALITY), len(matching)):
                ctx.warning(
                    "sbol3-12111",
                    derived,
                    spec.HAS_FEATURE,
                    f"derived Feature count for variable template Feature `{template_feature}` should satisfy its "
                    "VariableFeature cardinality",
                )
            allowed = allowed_variants(ctx, variable_feature)
            template_feature_roles = _roles_of(ctx, template_feature)
            template_referent_types = type_properties(ctx, template_feature)
            for derived_feature in matching:
                derived_obj = ctx.get(derived_feature)
                if derived_obj is not None and derived_obj.has_class(spec.SUB_COMPONENT):
                    instance_of = derived_obj.first_resource(spec.INSTANCE_OF)
                    if instance_of is not None and instance_of not in allowed:
                        ctx.error(
                            "sbol3-12112",
                            derived_feature,
                            spec.INSTANCE_OF,
                            f"derived SubComponent instanceOf `{instance_of}` must be a variant allowed by "
                            f"VariableFeature `{variable_feature_id}`",
                        )
                if not template_feature_roles <= _roles_of(ctx, derived_feature):
                    ctx.warning(
                        "sbol3-12114",
                        derived_feature,
                        spec.ROLE,
                        f"derived Feature should include all role values from variable template Feature "
                        f"`{template_feature}`",
                    )
                derived_types = type_properties(ctx, derived_feature)
                if (
                    template_referent_types is not None
                    and derived_types is not None
                    and not template_referent_types <= derived_types
                ):
                    ctx.warning(
                        "sbol3-12115",
                        derived_feature,
                        spec.TYPE,
                        f"derived Feature type-determining referent should include all type values from template "
                        f"Feature `{template_feature}`",
                    )
        for constraint in template_constraints:
            restriction = constraint.first_iri(spec.RESTRICTION)
            template_subject = constraint.first_resource(spec.SUBJECT)
            template_object = constraint.first_resource(spec.OBJECT)
            if restriction is None or template_subject is None or template_object is None:
                continue
            derived_subjects = features_derived_from(ctx, derived, template_subject)
            derived_objects_ = features_derived_from(ctx, derived, template_object)
            for derived_subject in derived_subjects:
                for derived_object in derived_objects_:
                    table8 = table8_relation(ctx, str(restriction), derived_subject, derived_object)
                    table10 = table10_relation(ctx, str(restriction), derived_subject, derived_object)
                    if table8.outcome == CONTRADICTED or table10.outcome == CONTRADICTED:
                        ctx.error(
                            "sbol3-12113",
                            derived,
                            spec.HAS_CONSTRAINT,
                            f"derived Features `{derived_subject}` and `{derived_object}` must satisfy template "
                            f"Constraint `{constraint.identity}`",
                        )


@REGISTRY.rule(
    "sbol3-12101",
    "sbol3-12102",
    "sbol3-12103",
    "sbol3-12104",
    "sbol3-12105",
    "sbol3-12106",
    "sbol3-12107",
    "sbol3-12108",
    "sbol3-12109",
    "sbol3-12110",
    "sbol3-12111",
    "sbol3-12112",
    "sbol3-12113",
    "sbol3-12114",
    "sbol3-12115",
)
def combinatorial_derivations(ctx: SBOL3Context) -> None:
    """Strategy, cardinalities, unique variables, and local derivation semantics."""
    for obj in ctx.instances(spec.COMBINATORIAL_DERIVATION):
        strategy = obj.first_iri(spec.STRATEGY)
        if strategy is not None and str(strategy) not in spec.STRATEGY_IRIS:
            ctx.error("sbol3-12101", obj, spec.STRATEGY, f"unsupported CombinatorialDerivation strategy `{strategy}`")
        if strategy is not None and str(strategy) == spec.ENUMERATE:
            for variable_feature in obj.resources(spec.HAS_VARIABLE_FEATURE):
                variable_feature_obj = ctx.get(variable_feature)
                if variable_feature_obj is None:
                    continue
                cardinality = variable_feature_obj.first_iri(spec.CARDINALITY)
                if cardinality is not None and str(cardinality) in (spec.ZERO_OR_MORE_VALUE, spec.ONE_OR_MORE_VALUE):
                    ctx.error(
                        "sbol3-12102",
                        variable_feature_obj,
                        spec.CARDINALITY,
                        "enumerate strategy cannot use zeroOrMore or oneOrMore cardinality",
                    )
        variables: set[Node] = set()
        for variable_feature in obj.resources(spec.HAS_VARIABLE_FEATURE):
            variable_feature_obj = ctx.get(variable_feature)
            if variable_feature_obj is None:
                continue
            variable = variable_feature_obj.first_resource(spec.VARIABLE)
            if variable is None:
                continue
            if variable in variables:
                ctx.error(
                    "sbol3-12103", obj, spec.HAS_VARIABLE_FEATURE, f"duplicate VariableFeature variable `{variable}`"
                )
            variables.add(variable)
        _derivation_semantics(ctx, obj)


@REGISTRY.rule("sbol3-12201", "sbol3-12202", "sbol3-12203")
def variable_features(ctx: SBOL3Context) -> None:
    """VariableFeature cardinality, variable containment, and variantCollection membership."""
    for obj in ctx.instances(spec.VARIABLE_FEATURE):
        cardinality = obj.first_iri(spec.CARDINALITY)
        if cardinality is not None and str(cardinality) not in spec.CARDINALITY_IRIS:
            ctx.error("sbol3-12201", obj, spec.CARDINALITY, f"unsupported VariableFeature cardinality `{cardinality}`")
        derivation = ctx.get(ctx.ownership.single_parent(obj.identity, spec.HAS_VARIABLE_FEATURE))
        template = None if derivation is None else derivation.first_resource(spec.TEMPLATE)
        variable = obj.first_resource(spec.VARIABLE)
        if template is not None and variable is not None:
            if not component_contains(ctx, template, spec.HAS_FEATURE, variable):
                ctx.error(
                    "sbol3-12202",
                    obj,
                    spec.VARIABLE,
                    "VariableFeature variable must be a Feature of the template Component",
                )
        for collection in obj.resources(spec.VARIANT_COLLECTION):
            if not collection_contains_only_components_or_collections(ctx, collection, set()):
                ctx.error(
                    "sbol3-12203",
                    obj,
                    spec.VARIANT_COLLECTION,
                    f"variantCollection `{collection}` contains a member that is not a Component or Collection",
                )


@REGISTRY.rule("sbol3-10901", "sbol3-10902", "sbol3-10903", "sbol3-10904")
def component_references(ctx: SBOL3Context) -> None:
    """ComponentReference inChildOf and refersTo containment."""
    for obj in ctx.instances(spec.COMPONENT_REFERENCE):
        parent_component = ctx.ownership.single_parent(obj.identity, spec.HAS_FEATURE)
        parent_ref = parent_reference(ctx, obj)
        parent_in_child_of = None if parent_ref is None else parent_ref.first_resource(spec.IN_CHILD_OF)
        in_child_of = obj.first_resource(spec.IN_CHILD_OF)

        if (
            parent_component is not None
            and in_child_of is not None
            and not ctx.ownership.contains(parent_component, spec.HAS_FEATURE, in_child_of)
        ):
            ctx.error(
                "sbol3-10901",
                obj,
                spec.IN_CHILD_OF,
                "ComponentReference inChildOf must be a SubComponent of its parent Component",
            )

        if parent_in_child_of is not None:
            parent_sub_component = ctx.get(parent_in_child_of)
            if parent_sub_component is None:
                continue
            referenced = parent_sub_component.first_resource(spec.INSTANCE_OF)
            if referenced is None:
                continue
            if in_child_of is not None and not component_contains(ctx, referenced, spec.HAS_FEATURE, in_child_of):
                ctx.error(
                    "sbol3-10902",
                    obj,
                    spec.IN_CHILD_OF,
                    "nested ComponentReference inChildOf must be a SubComponent of the referenced Component",
                )

        sub_component = ctx.get(in_child_of)
        if sub_component is None:
            continue
        referenced_component = sub_component.first_resource(spec.INSTANCE_OF)
        refers_to = obj.first_resource(spec.REFERS_TO)
        if referenced_component is None or refers_to is None:
            continue
        refers_to_obj = ctx.get(refers_to)
        if refers_to_obj is None:
            continue
        if trace_feature(ctx, obj.identity).error == "cycle":
            ctx.error("sbol3-10903", obj, spec.REFERS_TO, "ComponentReference refersTo chain must not form a cycle")
            continue
        if refers_to_obj.has_class(spec.COMPONENT_REFERENCE):
            if not reference_is_child_of(ctx, refers_to, obj.identity) and not component_contains(
                ctx, referenced_component, spec.HAS_FEATURE, refers_to
            ):
                ctx.error(
                    "sbol3-10903",
                    obj,
                    spec.REFERS_TO,
                    "ComponentReference refersTo target must be a permitted ComponentReference child",
                )
        elif not component_contains(ctx, referenced_component, spec.HAS_FEATURE, refers_to):
            ctx.error(
                "sbol3-10904",
                obj,
                spec.REFERS_TO,
                "ComponentReference refersTo target must be a Feature of the referenced Component",
            )
