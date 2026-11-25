"""ModuleDefinition, Module, Interaction, and Participation rules."""

from __future__ import annotations

import re

from sbol_utilities.validation.sbol2 import spec as S
from sbol_utilities.validation.sbol2.context import Sbol2Context
from sbol_utilities.validation.sbol2.registry import REGISTRY
from sbol_utilities.validation.sbol2.rules.component import definition_cycles, use_remote_collisions

_SEGMENT = re.compile(r"[/#]")


def ontology_curie(iri: str) -> str:
    """The compact ontology id an SBOL 2 term IRI ends with: its last path or fragment segment."""
    return _SEGMENT.split(iri)[-1]


@REGISTRY.rule("sbol2-11705")
def module_definition_cycles(ctx: Sbol2Context) -> None:
    """ModuleDefinitions do not form a cycle through their Modules' definitions."""
    for obj in definition_cycles(ctx, S.MODULE_DEFINITION, S.MODULE_P, S.DEFINITION):
        ctx.error(
            "sbol2-11705", obj, "a ModuleDefinition must not form a cycle through its Modules' definitions", S.MODULE_P
        )


@REGISTRY.rule("sbol2-11609")
def module_definition_use_remote(ctx: Sbol2Context) -> None:
    """Two useRemote MapsTos of a ModuleDefinition's Modules and FunctionalComponents do not share a local."""
    for obj in use_remote_collisions(ctx, S.MODULE_DEFINITION, (S.MODULE_P, S.FUNCTIONAL_COMPONENT_P)):
        ctx.error("sbol2-11609", obj, "two useRemote MapsTos of a ModuleDefinition must not share a local", S.MAPS_TO_P)


@REGISTRY.rule("sbol2-12003")
def participants_in_module_definition(ctx: Sbol2Context) -> None:
    """A Participation's participant is a FunctionalComponent of the ModuleDefinition holding its Interaction."""
    for obj in ctx.sbol_objects:
        if not obj.has_class(S.PARTICIPATION):
            continue
        participant = obj.first_ref(S.PARTICIPANT)
        if participant is None:
            continue
        interaction = ctx.container_of(obj, S.PARTICIPATION_P)
        if interaction is None:
            continue
        module_definition = ctx.container_of(interaction, S.INTERACTION_P)
        if module_definition is not None and not module_definition.lists(S.FUNCTIONAL_COMPONENT_P, participant):
            ctx.error(
                "sbol2-12003",
                obj,
                "the participant of a Participation must be a FunctionalComponent of the ModuleDefinition",
                S.PARTICIPANT,
            )


@REGISTRY.rule("sbol2-11907")
def interaction_participation_roles(ctx: Sbol2Context) -> None:
    """An Interaction's participant roles are compatible with its SBO type (Table 11)."""
    if not ctx.config.best_practice:
        return
    ontology = ctx.ontology
    for obj in ctx.sbol_objects:
        if not obj.has_class(S.INTERACTION):
            continue
        types = [
            ontology_curie(t)
            for t in obj.iris(S.TYPE)
            if ontology.is_in_branch(ontology_curie(t), S.SBO_OCCURRING_ENTITY_REPRESENTATION)
        ]
        if len(types) != 1:
            continue
        allowed = S.PARTICIPANT_ROLES_FOR_INTERACTION.get(types[0])
        if allowed is None:
            continue
        offending = False
        for participation in ctx.children(obj, S.PARTICIPATION_P):
            roles = [
                ontology_curie(r)
                for r in participation.iris(S.ROLE)
                if ontology.is_in_branch(ontology_curie(r), S.SBO_PARTICIPANT_ROLE)
            ]
            if len(roles) == 1 and roles[0] not in allowed:
                offending = True
        if offending:
            ctx.warning(
                "sbol2-11907",
                obj,
                "an Interaction's participant roles should be compatible with its SBO type",
                S.TYPE,
            )
