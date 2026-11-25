"""ModuleDefinition, Module, Interaction, and Participation rules."""

from __future__ import annotations

from sbol_utilities.validation.sbol2 import spec as S
from sbol_utilities.validation.sbol2.context import Sbol2Context
from sbol_utilities.validation.sbol2.helpers import definition_cycles, ontology_curie, use_remote_collisions
from sbol_utilities.validation.sbol2.registry import REGISTRY


@REGISTRY.rule("sbol2-11705")
def module_definition_cycles(ctx: Sbol2Context) -> None:
    """ModuleDefinitions do not form a cycle through their Modules' definitions."""
    for obj in definition_cycles(ctx, S.MODULE_DEFINITION, S.MODULE_P, S.DEFINITION):
        ctx.report(
            "sbol2-11705",
            obj,
            "a ModuleDefinition must not form a cycle through its Modules' definitions",
            property=S.MODULE_P,
        )


@REGISTRY.rule("sbol2-11609")
def module_definition_use_remote(ctx: Sbol2Context) -> None:
    """Two useRemote MapsTos of a ModuleDefinition's Modules and FunctionalComponents do not share a local."""
    for obj in use_remote_collisions(ctx, S.MODULE_DEFINITION, (S.MODULE_P, S.FUNCTIONAL_COMPONENT_P)):
        ctx.report(
            "sbol2-11609",
            obj,
            "two useRemote MapsTos of a ModuleDefinition must not share a local",
            property=S.MAPS_TO_P,
        )


@REGISTRY.rule("sbol2-12003")
def participants_in_module_definition(ctx: Sbol2Context) -> None:
    """A Participation's participant is a FunctionalComponent of the ModuleDefinition holding its Interaction."""
    for obj in ctx.instances(S.PARTICIPATION):
        participant = obj.first_iri(S.PARTICIPANT)
        if participant is None:
            continue
        interaction = ctx.parent(obj, S.PARTICIPATION_P)
        if interaction is None:
            continue
        module_definition = ctx.parent(interaction, S.INTERACTION_P)
        if module_definition is not None and participant not in module_definition.iris(S.FUNCTIONAL_COMPONENT_P):
            ctx.report(
                "sbol2-12003",
                obj,
                "the participant of a Participation must be a FunctionalComponent of the ModuleDefinition",
                property=S.PARTICIPANT,
            )


def _only_term_in_branch(ctx: Sbol2Context, iris: list[str], branch_root: str) -> str | None:
    """The compact id of the one term among ``iris`` lying in an ontology branch; None when there is not exactly one."""
    found = [curie for curie in map(ontology_curie, iris) if ctx.ontology.is_in_branch(curie, branch_root)]
    return found[0] if len(found) == 1 else None


@REGISTRY.rule("sbol2-11907")
def interaction_participation_roles(ctx: Sbol2Context) -> None:
    """An Interaction's participant roles are compatible with its SBO type (Table 11)."""
    for obj in ctx.instances(S.INTERACTION):
        interaction_type = _only_term_in_branch(ctx, obj.iris(S.TYPE), S.SBO_OCCURRING_ENTITY_REPRESENTATION)
        allowed = S.PARTICIPANT_ROLES_FOR_INTERACTION.get(interaction_type or "")
        if allowed is None:
            continue
        roles = (
            _only_term_in_branch(ctx, participation.iris(S.ROLE), S.SBO_PARTICIPANT_ROLE)
            for participation in ctx.referenced(obj, S.PARTICIPATION_P)
        )
        if any(role is not None and role not in allowed for role in roles):
            ctx.report(
                "sbol2-11907",
                obj,
                "an Interaction's participant roles should be compatible with its SBO type",
                property=S.TYPE,
            )
