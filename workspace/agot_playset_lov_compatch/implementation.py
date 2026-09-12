#!/usr/bin/env python3
"""Generate the Legacy of Valyria part of the AGOT playset compatches."""

from __future__ import annotations

from agot_playset import final_integration, lov_map
from agot_playset.compatch import RunInputs as MapInputs
from agot_playset.compatch import lov_bridge
from agot_playset.runtime_fixes import RunInputs
from agot_playset.runtime_fixes.court_character import (
    generate_aurion_title_gain_guard,
    generate_tour_general_events,
)
from agot_playset.runtime_fixes.crash_stability import (
    generate_accolade_lifecycle_stability,
    generate_appointment_score_guards,
)
from agot_playset.runtime_fixes.realm_succession import (
    generate_agot_title_on_action_septon_naming,
    generate_title_on_action_repairs,
)
from agot_playset.runtime_fixes.visuals_ui import (
    generate_additional_models_holding_art_constants,
    generate_additional_models_scripted_illustration_cultures,
    generate_scene_culture_owner_guards,
)
from gen import GenerationContext
from gen.sources import WorkshopSources


def generate(context: GenerationContext) -> None:
    workshop = WorkshopSources(context)
    runtime = RunInputs(
        WORKSHOP=workshop,
        OUTPUT=context.output_root,
        GAME_ROOT=context.source("game"),
    )
    for repair in (
        generate_appointment_score_guards,
        generate_aurion_title_gain_guard,
        generate_title_on_action_repairs,
        generate_agot_title_on_action_septon_naming,
        generate_additional_models_holding_art_constants,
        generate_additional_models_scripted_illustration_cultures,
        generate_tour_general_events,
    ):
        repair(runtime)
    generate_accolade_lifecycle_stability(runtime, include_core=False)
    generate_scene_culture_owner_guards(
        runtime, generic_source="3773616784", include_agot=False
    )

    map_inputs = MapInputs(
        context=context,
        workshop_root=context.workshop_root("agot", "lov", "lov-agot-bridge"),
        workshop={
            "AGOT": context.source("agot"),
            "NOW": context.source("agot-now"),
            "LOV": context.source("lov"),
            "RC": context.source("lov-agot-bridge"),
        },
        root=context.workspace_root,
        output=context.output_root,
        assets=context.assets_dir,
        references={},
    )
    lov_bridge.rebase(map_inputs)
    lov_map.generate(context)
    final_integration.generate_lov(context)
