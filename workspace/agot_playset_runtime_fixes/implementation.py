#!/usr/bin/env python3
"""Generate narrow runtime repairs for the current AGOT playset."""

from __future__ import annotations

from gen import GenerationContext
from gen.sources import WorkshopSources

from .runtime_fixes import RunInputs
from .runtime_fixes.artifacts import (
    generate_agot_artifact_feature_owner_guards,
    generate_agot_artifact_succession,
    generate_agot_wall_banner_capital_fallback,
    generate_artifact_manager_distribution_event,
    generate_artifact_manager_scripted_guis,
    generate_artifact_manager_upgrade_guis,
)
from .runtime_fixes.court_character import (
    generate_adventurers_beneficiary,
    generate_agot_citadel,
    generate_agot_starting_legitimacy,
    generate_agot_tour_events,
    generate_all_men_must_serve,
    generate_aurion_title_gain_guard,
    generate_automated_squire_training_events,
    generate_court_events_3020_role_guard,
    generate_cow_province_setup_rebase,
    generate_expanded_court_position_hire_events,
    generate_further_east_startup_government_quarantine,
    generate_house_founders,
    generate_house_founders_dynasty_on_action_rebase,
    generate_house_founders_title_gain_capital_guards,
    generate_knighting_ceremony_event,
    generate_landed_knights,
    generate_legitimacy_over_time_ai,
    generate_red_keep_castellan_guard,
    generate_red_keep_government_rebase,
    generate_suggest_dragon_bonding,
    generate_vanilla_tour_pulse,
)
from .runtime_fixes.integrations import (
    generate_any_new_traditions,
    generate_baie_rebases,
    generate_deadly_ck3_health_location_guards,
    generate_deadly_ck3_infirm_track,
)
from .runtime_fixes.realm_succession import (
    generate_agot_war_value_guards,
    generate_chaotic_kurultai_event_guard,
    generate_dragon_wives_legitimate_house_guards,
    generate_essos_disabled_realm_cleanup,
    generate_faction_legitimate_house_guards,
    generate_great_councils,
    generate_kurultai_succession_scope_repairs,
    generate_more_interactive_vassals_war_join_guards,
    generate_mpo_nomad_event_guards,
    generate_nomad_yurt_guards,
    generate_pirate_succession_guards,
    generate_succession_crisis,
    generate_voluntary_laamp_repairs,
)
from .runtime_fixes.visuals_ui import (
    generate_additional_models_decision_illustrations,
    generate_additional_models_on_action_deduplication,
    generate_advanced_character_search,
    generate_character_ui_overhaul_hometowns,
    generate_faster_transitions_gui,
    generate_mari_agot_portraits,
    generate_scene_culture_owner_guards,
    generate_seasons_agot_shaders,
    generate_upgrade_house_banners_event,
)

REPAIRS = (
    generate_seasons_agot_shaders,
    generate_mari_agot_portraits,
    generate_faster_transitions_gui,
    generate_additional_models_on_action_deduplication,
    generate_kurultai_succession_scope_repairs,
    generate_chaotic_kurultai_event_guard,
    generate_essos_disabled_realm_cleanup,
    generate_nomad_yurt_guards,
    generate_pirate_succession_guards,
    generate_faction_legitimate_house_guards,
    generate_dragon_wives_legitimate_house_guards,
    generate_court_events_3020_role_guard,
    generate_aurion_title_gain_guard,
    generate_cow_province_setup_rebase,
    generate_upgrade_house_banners_event,
    generate_scene_culture_owner_guards,
    generate_landed_knights,
    generate_expanded_court_position_hire_events,
    generate_legitimacy_over_time_ai,
    generate_red_keep_castellan_guard,
    generate_red_keep_government_rebase,
    generate_further_east_startup_government_quarantine,
    generate_automated_squire_training_events,
    generate_knighting_ceremony_event,
    generate_house_founders,
    generate_house_founders_title_gain_capital_guards,
    generate_house_founders_dynasty_on_action_rebase,
    generate_artifact_manager_distribution_event,
    generate_additional_models_decision_illustrations,
    generate_succession_crisis,
    generate_baie_rebases,
    generate_character_ui_overhaul_hometowns,
    generate_more_interactive_vassals_war_join_guards,
    generate_agot_war_value_guards,
    generate_artifact_manager_scripted_guis,
    generate_artifact_manager_upgrade_guis,
    generate_advanced_character_search,
    generate_any_new_traditions,
    generate_great_councils,
    generate_suggest_dragon_bonding,
    generate_agot_tour_events,
    generate_adventurers_beneficiary,
    generate_all_men_must_serve,
    generate_agot_artifact_succession,
    generate_agot_artifact_feature_owner_guards,
    generate_agot_wall_banner_capital_fallback,
    generate_deadly_ck3_health_location_guards,
    generate_deadly_ck3_infirm_track,
    generate_agot_citadel,
    generate_agot_starting_legitimacy,
    generate_vanilla_tour_pulse,
    generate_mpo_nomad_event_guards,
    generate_voluntary_laamp_repairs,
)


def generate(context: GenerationContext) -> None:
    inputs = RunInputs(
        WORKSHOP=WorkshopSources(context),
        OUTPUT=context.output_root,
        GAME_ROOT=context.source("game"),
        LORE_GOVERNMENTS=context.source("lore-governments"),
        LOV_REBASE=context.source("lov-rebase"),
    )
    for repair in REPAIRS:
        repair(inputs)
