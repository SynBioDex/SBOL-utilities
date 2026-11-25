"""Interaction, Participation, and Interface rules (sbol3-118xx, 119xx, 120xx)."""

from __future__ import annotations

from sbol_utilities.validation.sbol3 import spec
from sbol_utilities.validation.sbol3.context import Sbol3Context, Sbol3Object
from sbol_utilities.validation.sbol3.registry import REGISTRY
from sbol_utilities.validation.sbol3.resolver import component_contains


def _iris(obj: Sbol3Object, predicate: str) -> list[str]:
    return [str(i) for i in obj.iris(predicate)]


@REGISTRY.rule("sbol3-11901", "sbol3-11902", "sbol3-11903", "sbol3-11904", "sbol3-11905", "sbol3-11906")
def participations(ctx: Sbol3Context) -> None:
    """Participation roles, participant kind, and participant containment."""
    ontology = ctx.ontology
    for obj in ctx.instances(spec.PARTICIPATION):
        roles = _iris(obj, spec.ROLE)
        for role in roles:
            if ontology.is_participation_role_term(role) is False:
                ctx.report(
                    "sbol3-11904",
                    obj,
                    f"Participation role `{role}` is not an ontology Participation role term",
                    property=spec.ROLE,
                )
        for index, left in enumerate(roles):
            for right in roles[index + 1 :]:
                if ontology.terms_conflict(left, right) is True:
                    ctx.report(
                        "sbol3-11905",
                        obj,
                        f"Participation role `{left}` conflicts with role `{right}`",
                        property=spec.ROLE,
                    )
        known = 0
        unknown = False
        for role in roles:
            answer = ontology.is_participation_role_term(role)
            if answer is True:
                known += 1
            elif answer is None:
                unknown = True
        if known > 1 or (known == 0 and not unknown):
            ctx.report(
                "sbol3-11906",
                obj,
                "Participation should have exactly one known SBO participant role",
                property=spec.ROLE,
            )

        participant = obj.first_resource(spec.PARTICIPANT)
        higher = obj.first_resource(spec.HIGHER_ORDER_PARTICIPANT)
        if (participant is not None) + (higher is not None) != 1:
            ctx.report(
                "sbol3-11901", obj, "Participation must contain precisely one participant or higherOrderParticipant"
            )
        interaction = ctx.ownership.single_parent(obj.identity, spec.HAS_PARTICIPATION)
        if interaction is None:
            continue
        component = ctx.ownership.single_parent(interaction, spec.HAS_INTERACTION)
        if component is None:
            continue
        if participant is not None and not component_contains(ctx, component, spec.HAS_FEATURE, participant):
            ctx.report(
                "sbol3-11902",
                obj,
                "Participation participant must be a Feature of the containing Component",
                property=spec.PARTICIPANT,
            )
        if higher is not None and not component_contains(ctx, component, spec.HAS_INTERACTION, higher):
            ctx.report(
                "sbol3-11903",
                obj,
                "higherOrderParticipant must be an Interaction of the containing Component",
                property=spec.HIGHER_ORDER_PARTICIPANT,
            )


@REGISTRY.rule("sbol3-11801", "sbol3-11802", "sbol3-11803", "sbol3-11804")
def interactions(ctx: Sbol3Context) -> None:
    """Interaction types and their Participation roles (Tables 11 and 12)."""
    ontology = ctx.ontology
    for obj in ctx.instances(spec.INTERACTION):
        types = _iris(obj, spec.TYPE)
        for t in types:
            if ontology.is_interaction_type_term(t) is False:
                ctx.report(
                    "sbol3-11801",
                    obj,
                    f"Interaction type `{t}` is not an ontology Interaction type term",
                    property=spec.TYPE,
                )
        for index, left in enumerate(types):
            for right in types[index + 1 :]:
                if ontology.terms_conflict(left, right) is True:
                    ctx.report(
                        "sbol3-11802",
                        obj,
                        f"Interaction type `{left}` conflicts with type `{right}`",
                        property=spec.TYPE,
                    )
        known = 0
        unknown = False
        for t in types:
            answer = ontology.is_interaction_type_term(t)
            if answer is True:
                known += 1
            elif answer is None:
                unknown = True
        if known > 1 or (known == 0 and not unknown):
            ctx.report(
                "sbol3-11803",
                obj,
                "Interaction should have exactly one known SBO occurring-entity-relationship type",
                property=spec.TYPE,
            )

        known_types = [t for t in types if ontology.is_interaction_type_term(t) is True]
        if not known_types:
            continue
        for participation in obj.resources(spec.HAS_PARTICIPATION):
            participation_obj = ctx.get(participation)
            if participation_obj is None:
                continue
            known_roles = 0
            unknown_role = False
            compatible = False
            for role in _iris(participation_obj, spec.ROLE):
                answer = ontology.is_participation_role_term(role)
                if answer is True:
                    known_roles += 1
                    compatible = compatible or any(
                        ontology.participation_role_compatible_with_interaction_type(role, t) is True
                        for t in known_types
                    )
                elif answer is None:
                    unknown_role = True
            if not compatible and (known_roles == 0 or not unknown_role):
                ctx.report(
                    "sbol3-11804",
                    participation_obj,
                    "Participation should have a known role cross-listed with the Interaction type",
                    property=spec.ROLE,
                )


@REGISTRY.rule("sbol3-12001", "sbol3-12002", "sbol3-12003")
def interfaces(ctx: Sbol3Context) -> None:
    """Interface inputs, outputs, and nondirectionals are Features of the containing Component."""
    for obj in ctx.instances(spec.INTERFACE):
        component = ctx.ownership.single_parent(obj.identity, spec.HAS_INTERFACE)
        if component is None:
            continue
        for predicate, rule in (
            (spec.INPUT, "sbol3-12001"),
            (spec.OUTPUT, "sbol3-12002"),
            (spec.NONDIRECTIONAL, "sbol3-12003"),
        ):
            for feature in obj.resources(predicate):
                if not component_contains(ctx, component, spec.HAS_FEATURE, feature):
                    ctx.report(
                        rule,
                        obj,
                        f"Interface property `{predicate}` must refer to a Feature of the containing Component",
                        property=predicate,
                    )
