"""Measured-object rules: the measures a Component, FunctionalComponent, Module, Interaction, or Participation
carries are om:Measure objects."""

from __future__ import annotations

from sbol_utilities.validation.sbol2 import spec as S
from sbol_utilities.validation.sbol2.context import Sbol2Context, Sbol2Object
from sbol_utilities.validation.sbol2.registry import REGISTRY


def _measure_rule(obj: Sbol2Object):
    if obj.has_class(S.MODULE):
        return "sbol2-11707"
    if obj.has_class(S.COMPONENT, S.FUNCTIONAL_COMPONENT):
        return "sbol2-10608"
    if obj.has_class(S.PARTICIPATION):
        return "sbol2-12008"
    if obj.has_class(S.INTERACTION):
        return "sbol2-11908"
    return None


@REGISTRY.rule("sbol2-10608", "sbol2-11707", "sbol2-12008", "sbol2-11908")
def measures_are_measures(ctx: Sbol2Context) -> None:
    """Every measure an object carries resolves to an om:Measure when held in the document."""
    for obj in ctx.sbol_objects:
        rule = _measure_rule(obj)
        if rule is None:
            continue
        for iri in obj.iris(S.MEASURE):
            target = ctx.resolve(iri)
            if target is not None and not target.has_class(S.OM_MEASURE):
                ctx.report(rule, obj, f"measure refers to `{iri}`, which is not an om:Measure", property=S.MEASURE)
