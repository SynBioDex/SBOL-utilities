"""Interaction, Participation, and Interface rules (sbol3-118xx, 119xx, 120xx)."""

from __future__ import annotations

from sbol_utilities.validation.sbol3 import spec
from sbol_utilities.validation.sbol3.context import Sbol3Context, Sbol3Object
from sbol_utilities.validation.sbol3.helpers import conflicting_pairs, exactly_one_known
from sbol_utilities.validation.sbol3.registry import REGISTRY


def iri_values(obj: Sbol3Object, predicate: str) -> list[str]:
    """The IRI values of ``predicate`` as strings."""
    return [str(i) for i in obj.iris(predicate)]


@REGISTRY.rule("sbol3-11904", "sbol3-11905", "sbol3-11906")
def participation_roles(ctx: Sbol3Context) -> None:
    """A Participation has one known SBO participant role, and its roles do not conflict."""
    ontology = ctx.ontology
    for obj in ctx.instances(spec.PARTICIPATION):
        roles = iri_values(obj, spec.ROLE)
        for role in roles:
            if ontology.is_participation_role_term(role) is False:
                ctx.report(
                    "sbol3-11904",
                    obj,
                    f"Participation role `{role}` is not an ontology Participation role term",
                    property=spec.ROLE,
                )
        for left, right in conflicting_pairs(ontology, roles):
            ctx.report(
                "sbol3-11905", obj, f"Participation role `{left}` conflicts with role `{right}`", property=spec.ROLE
            )
        if not exactly_one_known(ontology.is_participation_role_term(role) for role in roles):
            ctx.report(
                "sbol3-11906",
                obj,
                "Participation should have exactly one known SBO participant role",
                property=spec.ROLE,
            )


@REGISTRY.rule("sbol3-11901", "sbol3-11902", "sbol3-11903")
def participants(ctx: Sbol3Context) -> None:
    """A Participation names one participant, which belongs to the Component holding its Interaction."""
    for obj in ctx.instances(spec.PARTICIPATION):
        participant = obj.first_resource(spec.PARTICIPANT)
        higher = obj.first_resource(spec.HIGHER_ORDER_PARTICIPANT)
        if (participant is None) == (higher is None):
            ctx.report(
                "sbol3-11901", obj, "Participation must contain precisely one participant or higherOrderParticipant"
            )
        interaction = ctx.parent(obj, spec.HAS_PARTICIPATION)
        component = None if interaction is None else ctx.parent(interaction, spec.HAS_INTERACTION)
        if component is None:
            continue
        if participant is not None and participant not in component.resources(spec.HAS_FEATURE):
            ctx.report(
                "sbol3-11902",
                obj,
                "Participation participant must be a Feature of the containing Component",
                property=spec.PARTICIPANT,
            )
        if higher is not None and higher not in component.resources(spec.HAS_INTERACTION):
            ctx.report(
                "sbol3-11903",
                obj,
                "higherOrderParticipant must be an Interaction of the containing Component",
                property=spec.HIGHER_ORDER_PARTICIPANT,
            )


@REGISTRY.rule("sbol3-11801", "sbol3-11802", "sbol3-11803")
def interaction_types(ctx: Sbol3Context) -> None:
    """An Interaction has one known SBO occurring-entity type, and its types do not conflict."""
    ontology = ctx.ontology
    for obj in ctx.instances(spec.INTERACTION):
        types = iri_values(obj, spec.TYPE)
        for type_iri in types:
            if ontology.is_interaction_type_term(type_iri) is False:
                ctx.report(
                    "sbol3-11801",
                    obj,
                    f"Interaction type `{type_iri}` is not an ontology Interaction type term",
                    property=spec.TYPE,
                )
        for left, right in conflicting_pairs(ontology, types):
            ctx.report(
                "sbol3-11802", obj, f"Interaction type `{left}` conflicts with type `{right}`", property=spec.TYPE
            )
        if not exactly_one_known(ontology.is_interaction_type_term(type_iri) for type_iri in types):
            ctx.report(
                "sbol3-11803",
                obj,
                "Interaction should have exactly one known SBO occurring-entity-relationship type",
                property=spec.TYPE,
            )


@REGISTRY.rule("sbol3-11804")
def participation_roles_suit_interaction(ctx: Sbol3Context) -> None:
    """A Participation of an Interaction with a known type has a known role cross-listed with that type
    (Tables 11 and 12), unless one of its roles is unknown and so might be."""
    ontology = ctx.ontology
    for obj in ctx.instances(spec.INTERACTION):
        known_types = [t for t in iri_values(obj, spec.TYPE) if ontology.is_interaction_type_term(t) is True]
        if not known_types:
            continue
        for participation in ctx.referenced(obj, spec.HAS_PARTICIPATION):
            roles = iri_values(participation, spec.ROLE)
            answers = [ontology.is_participation_role_term(role) for role in roles]
            compatible = any(
                answer is True
                and any(ontology.participation_role_compatible_with_interaction_type(role, t) for t in known_types)
                for role, answer in zip(roles, answers)
            )
            if not compatible and (True not in answers or None not in answers):
                ctx.report(
                    "sbol3-11804",
                    participation,
                    "Participation should have a known role cross-listed with the Interaction type",
                    property=spec.ROLE,
                )


#: Interface property -> the rule requiring its values to be Features of the Component holding the Interface
INTERFACE_RULES = ((spec.INPUT, "sbol3-12001"), (spec.OUTPUT, "sbol3-12002"), (spec.NONDIRECTIONAL, "sbol3-12003"))


@REGISTRY.rule(*(rule for _, rule in INTERFACE_RULES))
def interfaces(ctx: Sbol3Context) -> None:
    """Interface inputs, outputs, and nondirectionals are Features of the containing Component."""
    for obj in ctx.instances(spec.INTERFACE):
        component = ctx.parent(obj, spec.HAS_INTERFACE)
        if component is None:
            continue
        features = component.resources(spec.HAS_FEATURE)
        for predicate, rule in INTERFACE_RULES:
            if not all(feature in features for feature in obj.resources(predicate)):
                ctx.report(
                    rule,
                    obj,
                    f"Interface property `{predicate}` must refer to a Feature of the containing Component",
                    property=predicate,
                )
