"""Measured-object rules: the measures a Component, FunctionalComponent, Module, Interaction, or Participation
carries are om:Measure objects."""

from __future__ import annotations

from sbol_utilities.validation.sbol2 import spec as S
from sbol_utilities.validation.sbol2.context import Sbol2Context
from sbol_utilities.validation.sbol2.registry import REGISTRY

#: class -> the rule requiring its measures to be om:Measure objects; the first class an object has applies
MEASURE_RULES = (
    (S.MODULE, "sbol2-11707"),
    (S.COMPONENT, "sbol2-10608"),
    (S.FUNCTIONAL_COMPONENT, "sbol2-10608"),
    (S.PARTICIPATION, "sbol2-12008"),
    (S.INTERACTION, "sbol2-11908"),
)


@REGISTRY.rule(*dict.fromkeys(rule for _, rule in MEASURE_RULES))
def measures_are_measures(ctx: Sbol2Context) -> None:
    """Every measure an object carries resolves to an om:Measure when held in the document."""
    for obj in ctx.instances(*(cls for cls, _ in MEASURE_RULES)):
        rule = next(rule for cls, rule in MEASURE_RULES if obj.has_class(cls))
        for iri, target in ctx.resolved(obj, S.MEASURE):
            if not target.has_class(S.OM_MEASURE):
                ctx.report(rule, obj, f"measure refers to `{iri}`, which is not an om:Measure", property=S.MEASURE)
