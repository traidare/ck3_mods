#!/usr/bin/env python3
"""Generate the always-enabled part of the AGOT playset compatches."""

from __future__ import annotations

from agot_playset import final_integration
from agot_playset.runtime_fixes import RunInputs
from agot_playset.runtime_fixes.artifacts import (
    generate_agot_artifact_feature_owner_guards,
    generate_agot_artifact_succession,
    generate_agot_wall_banner_capital_fallback,
    generate_artifact_manager_distribution_event,
    generate_artifact_manager_scripted_guis,
    generate_artifact_manager_upgrade_guis,
    generate_more_valyrian_steel_artifact_repairs,
)
from agot_playset.runtime_fixes.buildings import (
    generate_landmarks_building_repairs,
    generate_landmarks_compatch_building_repairs,
)
from agot_playset.runtime_fixes.court_character import (
    generate_adventurers_beneficiary,
    generate_agot_azor_tour_events,
    generate_agot_citadel,
    generate_agot_starting_legitimacy,
    generate_agot_tour_events,
    generate_all_men_must_serve,
    generate_court_events_3020_role_guard,
    generate_cow_province_setup_rebase,
    generate_expanded_court_position_hire_events,
    generate_house_founders,
    generate_house_founders_dynasty_on_action_rebase,
    generate_house_founders_dynasty_trigger,
    generate_knighting_ceremony_event,
    generate_landed_knights,
    generate_legitimacy_over_time_ai,
    generate_red_keep_castellan_guard,
    generate_red_keep_government_rebase,
    generate_suggest_dragon_bonding,
    generate_tour_general_events,
    generate_vanilla_tour_pulse,
)
from agot_playset.runtime_fixes.crash_stability import (
    generate_accolade_lifecycle_stability,
    generate_adventurer_beneficiary_cb_guard,
    generate_appointment_score_guards,
    generate_beyond_wall_queued_event_guard,
    generate_dragon_template_storage_guards,
    generate_elder_relation_stability,
    generate_kraken_creation_scope_guard,
    generate_kraken_event_parser_repair,
    generate_naval_coastal_raid_tooltip,
    generate_naval_contact_stability,
    generate_scheme_lifecycle_stability,
)
from agot_playset.runtime_fixes.integrations import (
    generate_baie_rebases,
    generate_health_event_death_guards,
)
from agot_playset.runtime_fixes.realm_succession import (
    generate_agot_title_on_action_septon_naming,
    generate_agot_war_value_guards,
    generate_chaotic_kurultai_event_guard,
    generate_dragon_wives_legitimate_house_guards,
    generate_faction_legitimate_house_guards,
    generate_great_councils,
    generate_kurultai_succession_scope_repairs,
    generate_more_interactive_vassals_bannermen_cb_guard,
    generate_more_interactive_vassals_war_join_guards,
    generate_mpo_nomad_event_guards,
    generate_succession_crisis,
    generate_title_on_action_repairs,
    generate_voluntary_laamp_repairs,
)
from agot_playset.runtime_fixes.visuals_ui import (
    generate_additional_models_decision_illustrations,
    generate_advanced_character_search,
    generate_character_ui_overhaul_hometowns,
    generate_faster_transitions_gui,
    generate_mari_agot_portraits,
    generate_more_dragon_eggs_portrait_widget,
    generate_scene_culture_owner_guards,
    generate_seasons_agot_shaders,
    generate_upgrade_house_banners_event,
)
from gen import GenerationContext
from gen.sources import WorkshopSources

REPAIRS = (
    generate_naval_contact_stability,
    generate_elder_relation_stability,
    generate_scheme_lifecycle_stability,
    generate_beyond_wall_queued_event_guard,
    generate_naval_coastal_raid_tooltip,
    generate_dragon_template_storage_guards,
    generate_adventurer_beneficiary_cb_guard,
    generate_kraken_event_parser_repair,
    generate_kraken_creation_scope_guard,
    generate_landmarks_building_repairs,
    generate_landmarks_compatch_building_repairs,
    generate_seasons_agot_shaders,
    generate_mari_agot_portraits,
    generate_faster_transitions_gui,
    generate_more_dragon_eggs_portrait_widget,
    generate_kurultai_succession_scope_repairs,
    generate_chaotic_kurultai_event_guard,
    generate_faction_legitimate_house_guards,
    generate_dragon_wives_legitimate_house_guards,
    generate_court_events_3020_role_guard,
    generate_cow_province_setup_rebase,
    generate_upgrade_house_banners_event,
    generate_landed_knights,
    generate_expanded_court_position_hire_events,
    generate_legitimacy_over_time_ai,
    generate_red_keep_castellan_guard,
    generate_red_keep_government_rebase,
    generate_knighting_ceremony_event,
    generate_house_founders,
    generate_house_founders_dynasty_on_action_rebase,
    generate_house_founders_dynasty_trigger,
    generate_artifact_manager_distribution_event,
    generate_more_valyrian_steel_artifact_repairs,
    generate_additional_models_decision_illustrations,
    generate_succession_crisis,
    generate_baie_rebases,
    generate_character_ui_overhaul_hometowns,
    generate_more_interactive_vassals_war_join_guards,
    generate_more_interactive_vassals_bannermen_cb_guard,
    generate_agot_war_value_guards,
    generate_artifact_manager_scripted_guis,
    generate_artifact_manager_upgrade_guis,
    generate_advanced_character_search,
    generate_great_councils,
    generate_suggest_dragon_bonding,
    generate_agot_tour_events,
    generate_agot_azor_tour_events,
    generate_adventurers_beneficiary,
    generate_all_men_must_serve,
    generate_agot_artifact_succession,
    generate_agot_artifact_feature_owner_guards,
    generate_agot_wall_banner_capital_fallback,
    generate_health_event_death_guards,
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
    )
    for repair in REPAIRS:
        repair(inputs)
    # The Legacy of Valyria clause of this repair belongs to the LoV compatch's
    # copy of the same output rather than to the always-on payload.
    generate_accolade_lifecycle_stability(inputs, include_lov=False)
    # Without the Additional Models/LoV compatch, Additional Models is the
    # effective writer of the generic court scenes, so guard its own copy.
    generate_scene_culture_owner_guards(inputs, generic_source="3319354609")
    # Without the LoV bridge, AGOT is the effective writer of the four paths
    # below, so this module rebases the same repairs from AGOT's own copies.
    generate_appointment_score_guards(inputs, workshop_id="2962333032")
    generate_agot_title_on_action_septon_naming(inputs, workshop_id="2962333032")
    generate_tour_general_events(inputs, workshop_id="2962333032")
    generate_title_on_action_repairs(inputs, workshop_id="2962333032")
    final_integration.generate_core(context)
