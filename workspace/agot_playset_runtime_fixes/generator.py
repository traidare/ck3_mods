"""Staged destination-specific AGOT playset runtime-fix generator."""

from __future__ import annotations

import ast
import inspect
import textwrap
from types import ModuleType

from ck3mm.generation import GenerationContext
from ck3mm.generators import agot_runtime as implementation
from ck3mm.generators.sources import WorkshopSources

EXPECTED_MAIN_CALLS = (
    "generate_seasons_agot_shaders",
    "generate_mari_agot_portraits",
    "generate_faster_transitions_gui",
    "generate_additional_models_on_action_deduplication",
    "generate_kurultai_succession_scope_repairs",
    "generate_essos_disabled_realm_cleanup",
    "generate_nomad_yurt_guards",
    "generate_pirate_succession_guards",
    "generate_faction_legitimate_house_guards",
    "generate_dragon_wives_legitimate_house_guards",
    "generate_court_events_3020_role_guard",
    "generate_aurion_title_gain_guard",
    "generate_cow_province_setup_rebase",
    "generate_upgrade_house_banners_event",
    "generate_scene_culture_owner_guards",
    "generate_now_core_rebase",
    "generate_now_summerhall_candidate_guards",
    "generate_mfa_delayed_pulse_scopes",
    "generate_grand_remembrance_agot_obituary",
    "generate_landed_knights",
    "generate_expanded_court_position_hire_events",
    "generate_legitimacy_over_time_ai",
    "generate_red_keep_castellan_guard",
    "generate_automated_squire_training_events",
    "generate_knighting_ceremony_event",
    "generate_house_founders",
    "generate_artifact_manager_distribution_event",
    "generate_additional_models_decision_illustrations",
    "generate_succession_crisis",
    "generate_more_interactive_vassals_war_join_guards",
    "generate_agot_war_value_guards",
    "generate_artifact_manager_scripted_guis",
    "generate_artifact_manager_upgrade_guis",
    "generate_advanced_character_search",
    "generate_any_new_traditions",
    "generate_great_councils",
    "generate_suggest_dragon_bonding",
    "generate_agot_tour_events",
    "generate_adventurers_beneficiary",
    "generate_all_men_must_serve",
    "generate_agot_artifact_succession",
    "generate_agot_artifact_feature_owner_guards",
    "generate_agot_wall_banner_capital_fallback",
    "generate_deadly_ck3_health_location_guards",
    "generate_deadly_ck3_infirm_track",
    "generate_agot_citadel",
    "generate_agot_starting_legitimacy",
    "generate_vanilla_tour_pulse",
    "generate_mpo_nomad_event_guards",
    "generate_voluntary_laamp_repairs",
    "generate_agot_plus",
)
OTHER_OWNERS = frozenset(
    {
        "generate_now_core_rebase",
        "generate_now_summerhall_candidate_guards",
        "generate_mfa_delayed_pulse_scopes",
        "generate_grand_remembrance_agot_obituary",
        "generate_agot_plus",
    }
)


def _main_calls(module: ModuleType) -> tuple[str, ...]:
    tree = ast.parse(textwrap.dedent(inspect.getsource(module.main)))
    function = tree.body[0]
    if not isinstance(function, ast.FunctionDef):
        raise RuntimeError("colocated main is no longer a function definition")
    return tuple(
        statement.value.func.id
        for statement in function.body
        if isinstance(statement, ast.Expr)
        and isinstance(statement.value, ast.Call)
        and isinstance(statement.value.func, ast.Name)
        and statement.value.func.id.startswith("generate_")
    )


def generate(context: GenerationContext) -> None:
    if _main_calls(implementation) != EXPECTED_MAIN_CALLS:
        raise RuntimeError(
            "colocated runtime implementation changed; review destination ownership"
        )
    implementation.ROOT = context.workspace.root
    implementation.WORKSHOP = WorkshopSources(context)
    implementation.OUTPUT = context.output_root
    implementation.game_root = lambda: context.source("game")
    for function_name in EXPECTED_MAIN_CALLS:
        if function_name not in OTHER_OWNERS:
            getattr(implementation, function_name)()
