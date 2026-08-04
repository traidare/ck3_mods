#!/usr/bin/env python3
"""Build the standalone, fixed AGOT: The Long Night mod from pinned sources."""

from __future__ import annotations

import argparse
import codecs
import hashlib
import importlib.util
import os
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "mods" / "agot_the_long_night"
WORKSHOP = Path(os.environ["CK3_WORKSHOP_DIR"]).expanduser().resolve()
AGOT = WORKSHOP / "2962333032"
CORE = WORKSHOP / "3034473189"
SEASONS = WORKSHOP / "3377641022"
LONG_NIGHT = WORKSHOP / "3766462389"

PINNED_HASHES = {
    CORE
    / "gfx/portraits/portrait_animations/animations.txt": "c0b7d8bf00ce21001e28a10ca76cc0c95cf850a0bf5ef3dd81d98b671b1a111a",
    SEASONS
    / "events/season_events.txt": "f5f618b90ff2f5697517310b4d3c63f95c44ecf56150a2d1ad4cb3e26b217c04",
    LONG_NIGHT
    / "gfx/portraits/portrait_animations/animations.txt": "2d8de11f686ba6772c4607f0d1a8b7938153b589a1c081d5d194dd45c06142bd",
}

SKIP = {
    "descriptor.mod",
    "common/scripted_rules/00_rules.txt",
    "common/decisions/zz_long_night_plus_native_overrides.txt",
    "common/scripted_triggers/00_long_night_plus_laamp_override.txt",
    "common/scripted_triggers/zz_long_night_plus_capture.txt",
    "common/scripted_triggers/zz_long_night_plus_commander.txt",
    "common/scripted_triggers/zz_long_night_plus_regency.txt",
    "gfx/models/portraits/decals/hair_aging_control.dds",
    "gfx/models/portraits/male_head/male_eyes_normal.dds",
    "gfx/portraits/skin_palette.dds",
}


def load_legacy_generator():
    path = ROOT / "scripts" / "generate-agot-longnight-submodcore-dfp-compatch.py"
    spec = importlib.util.spec_from_file_location("longnight_legacy_generator", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


legacy = load_legacy_generator()


def text(path: Path) -> str:
    return path.read_bytes().decode("utf-8-sig")


def encoded(value: str) -> bytes:
    return codecs.BOM_UTF8 + value.encode("utf-8")


def definition_span(value: str, name: str) -> tuple[int, int]:
    match = re.search(rf"(?m)^[ \t]*{re.escape(name)}\s*=\s*\{{", value)
    if match is None:
        raise ValueError(f"definition not found: {name}")
    opening = value.find("{", match.start())
    return match.start(), legacy.matching_brace(value, opening) + 1


def replace_definition(value: str, name: str, replacement: str) -> str:
    start, end = definition_span(value, name)
    return value[:start] + replacement + value[end:]


def core_animation() -> str:
    core = text(CORE / legacy.RELATIVE_ANIMATIONS)
    source = text(LONG_NIGHT / legacy.RELATIVE_ANIMATIONS)
    newline = legacy.newline_style(core)
    names = legacy.direct_definition_names(source, r"wight_pose_[A-Za-z0-9_]+")
    if len(names) != 5:
        raise ValueError(f"expected five Long Night poses, found {len(names)}")
    poses = "".join(
        source[s:e] for s, e in (legacy.definition_span(source, n) for n in names)
    )
    poses = legacy.normalize_newlines(poses, newline)
    marker = f"\t\t#AGOT Added{newline}\t\thigh_septon = {{"
    legacy.unique_marker(core, marker, "Core high_septon pose")
    merged = core.replace(marker, poses + newline + marker, 1)
    legacy.assert_count(merged, r"wight_pose_[A-Za-z0-9_]+", 5, "Core/Long Night poses")
    legacy.assert_count(merged, "hold_bow_idle", 1, "Core bow pose")
    legacy.assert_count(merged, "hold_long_axe_idle", 1, "AGOT long-axe pose")
    return legacy.strip_trailing_whitespace(legacy.normalize_newlines(merged, "\n"))


def patch_seasons() -> str:
    value = text(SEASONS / "events/season_events.txt")
    start, end = definition_span(value, "season_events.002")
    block = value[start:end]
    immediate = re.search(r"(?m)^\s*immediate\s*=\s*\{", block)
    if immediate is None:
        raise ValueError("Seasons spring event has no immediate block")
    opening = block.find("{", immediate.start())
    closing = legacy.matching_brace(block, opening)
    original = block[opening + 1 : closing]
    replacement = (
        "immediate = {\n"
        "\t\tif = {\n"
        "\t\t\tlimit = { is_agot_long_night_active_trigger = yes }\n"
        "\t\t\ttrigger_event = { id = season_events.002 days = 90 }\n"
        "\t\t}\n"
        "\t\telse = {" + original + "\n\t\t}\n\t}"
    )
    block = block[: immediate.start()] + replacement + block[closing + 1 :]
    return value[:start] + block + value[end:]


def game_rules() -> str:
    return """agot_others_invasion_chance = {
\tcategories = { agot }
\tdefault = others_certain_invasion_chance
\tothers_certain_invasion_chance = { }
\tothers_near_certain_invasion_chance = { }
\tothers_even_odds_invasion_chance = { }
\tothers_remote_odds_invasion_chance = { }
\tothers_invasion_wont_happen = { }
}

agot_others_invasion_moment = {
\tcategories = { agot }
\tdefault = others_historical_invasion
\tothers_immediate_invasion = { }
\tothers_invasion_in_50_years = { }
\tothers_invasion_in_100_years = { }
\tothers_invasion_in_150_years = { }
\tothers_historical_invasion = { }
\tothers_full_random_invasion = { }
\tothers_manual_invasion = { }
}

agot_others_invasion_strength = {
\tcategories = { agot }
\tdefault = others_standard_invasion
\tothers_weak_invasion = { }
\tothers_standard_invasion = { }
\tothers_strong_invasion = { }
\tothers_insane_invasion = { }
}

agot_others_resolution = {
\tcategories = { agot }
\tdefault = others_war_resolution
\tothers_war_resolution = { }
}

agot_longnight_iron_throne_reformation = {
\tcategories = { agot }
\tdefault = longnight_iron_throne_reformation_on
\tlongnight_iron_throne_reformation_on = { }
\tlongnight_iron_throne_reformation_off = { }
}

agot_long_night_dragon = {
\tcategories = { agot }
\tdefault = agot_long_night_dragon_off
\tagot_long_night_dragon_off = { }
\tagot_long_night_dragon_on = { }
}

agot_others_cb_tier = {
\tcategories = { agot }
\tdefault = others_cb_kingdom
\tothers_cb_kingdom = { }
\tothers_cb_empire = { }
}
"""


def patch_maintenance() -> str:
    value = legacy.patch_maintenance_events()
    event = """others_maintenance.1 = {
\tscope = none
\thidden = yes
\timmediate = {
\t\tset_global_variable = { name = agot_long_night_enabled value = yes }
\t\tset_global_variable = { name = agot_long_night_eligible_year value = current_year }
\t\tif = {
\t\t\tlimit = { NOT = { has_dlc_feature = roads_to_power } }
\t\t\tset_global_variable = { name = agot_long_night_dependency_blocked value = yes }
\t\t\tevery_player = { trigger_event = agot_ln.1 }
\t\t}
\t\telse_if = { limit = { has_game_rule = others_invasion_in_50_years } change_global_variable = { name = agot_long_night_eligible_year add = 50 } }
\t\telse_if = { limit = { has_game_rule = others_invasion_in_100_years } change_global_variable = { name = agot_long_night_eligible_year add = 100 } }
\t\telse_if = { limit = { has_game_rule = others_invasion_in_150_years } change_global_variable = { name = agot_long_night_eligible_year add = 150 } }
\t\telse_if = {
\t\t\tlimit = { has_game_rule = others_historical_invasion current_year < 8298 }
\t\t\tset_global_variable = { name = agot_long_night_eligible_year value = 8298 }
\t\t}
\t\telse_if = {
\t\t\tlimit = { has_game_rule = others_full_random_invasion }
\t\t\trandom_list = {
\t\t\t\t20 = { }
\t\t\t\t20 = { change_global_variable = { name = agot_long_night_eligible_year add = 25 } }
\t\t\t\t20 = { change_global_variable = { name = agot_long_night_eligible_year add = 50 } }
\t\t\t\t20 = { change_global_variable = { name = agot_long_night_eligible_year add = 100 } }
\t\t\t\t20 = { change_global_variable = { name = agot_long_night_eligible_year add = 150 } }
\t\t\t}
\t\t}
\t\tif = {
\t\t\tlimit = {
\t\t\t\tNOT = { has_global_variable = agot_long_night_dependency_blocked }
\t\t\t\tNOT = { has_game_rule = others_invasion_wont_happen }
\t\t\t\tNOT = { has_game_rule = others_manual_invasion }
\t\t\t}
\t\t\ttrigger_event = { id = agot_ln.10 days = 1 }
\t\t}
\t}
}"""
    return replace_definition(value, "others_maintenance.1", event)


def army_block(stacks: int) -> str:
    return f"""spawn_army = {{
\t\t\tmen_at_arms = {{ type = other_maa stacks = {stacks} }}
\t\t\tname = wights
\t\t\tuses_supply = no
\t\t\tlocation = capital_province
\t\t}}"""


def patch_effects() -> str:
    value = legacy.patch_scripted_effects()
    first = value.find("spawn_army = {")
    if first < 0:
        raise ValueError("initial horde army not found")
    end = legacy.matching_brace(value, value.find("{", first)) + 1
    replacement = """if = { limit = { has_game_rule = others_weak_invasion } %s }
\t\telse_if = { limit = { has_game_rule = others_strong_invasion } %s }
\t\telse_if = { limit = { has_game_rule = others_insane_invasion } %s }
\t\telse = { %s }""" % (
        army_block(100),
        army_block(350),
        army_block(500),
        army_block(200),
    )
    value = value[:first] + replacement + value[end:]
    marker = "mutate_into_other_effect = {"
    insertion = """
\tsave_scope_as = host
\t# Centralized horde: conquered rulers do not remain landed undead vassals.
\tif = {
\t\tlimit = { is_landed = yes NOT = { has_trait = other_trait } }
\t\tif = {
\t\t\tlimit = { is_ai = no has_dlc_feature = roads_to_power }
\t\t\tflee_noble_south_effect = yes
\t\t}
\t\telse = {
\t\t\tcreate_title_and_vassal_change = { type = conquest save_scope_as = ln_horde_change }
\t\t\tevery_held_title = {
\t\t\t\tchange_title_holder = { holder = title:h_the_others.holder change = scope:ln_horde_change }
\t\t\t}
\t\t\tresolve_title_and_vassal_change = scope:ln_horde_change
\t\t}
\t}
"""
    value = legacy.replace_exact(
        value, marker, marker + insertion, "central horde conversion"
    )
    value = re.sub(
        r"(?m)^\s*change_government\s*=\s*wight_government\s*\r?\n", "", value
    )
    value = legacy.replace_regex(
        value,
        r"(\t\tevery_player\s*=\s*\{\s*trigger_event\s*=\s*\{\s*id\s*=\s*long_night_plus_wall\.1\s*\}\s*\})",
        r"\1\r\n\t\ttrigger_event = { id = agot_ln.39 days = 3 }",
        "coalition call after Wall breach",
    )
    return value


def patch_maa() -> str:
    value = legacy.patch_maa()
    for old, new in {
        "damage = 38": "damage = 40",
        "toughness = 120": "toughness = 40",
        "pursuit = 70": "pursuit = 15",
        "screen = 0": "screen = 20",
        "stack = 500": "stack = 100",
        "siege_tier = 4": "siege_tier = 1",
        "siege_value = 0.9": "siege_value = 0.15",
    }.items():
        value = legacy.replace_exact(value, old, new, f"balanced MAA: {old}")
    value = legacy.replace_exact(
        value,
        "type = heavy_infantry",
        "type = heavy_infantry\n\tspecial_recruit_only = yes",
        "event-only MAA",
    )
    return value


def patch_story() -> str:
    value = legacy.patch_story()
    value = legacy.replace_exact(
        value,
        "on_end = {",
        "on_end = {\n\tremove_global_variable = agot_long_night_active\n\tset_global_variable = { name = agot_long_night_completed value = yes }",
        "crisis cleanup state",
    )
    death = """on_owner_death = {
\t\tif = {
\t\t\tlimit = { has_global_variable = war_for_dawn_victory }
\t\t\tend_story = yes
\t\t}
\t\telse = {
\t\t\tchange_global_variable = { name = agot_long_night_threat add = -10 }
\t\t\tif = { limit = { global_var:agot_long_night_threat < 0 } set_global_variable = { name = agot_long_night_threat value = 0 } }
\t\t\tif = {
\t\t\t\tlimit = { exists = title:h_the_others.holder title:h_the_others.holder = { is_alive = yes } }
\t\t\t\tmake_story_owner = title:h_the_others.holder
\t\t\t\tstory_owner = {
\t\t\t\t\tadd_trait = nightking
\t\t\t\t\tadd_character_modifier = { modifier = agot_ln_leaderless_modifier years = 2 }
\t\t\t\t}
\t\t\t}
\t\t}
\t}"""
    value = replace_definition(value, "on_owner_death", death)
    value = legacy.replace_regex(
        value,
        r"(exists\s*=\s*title:h_the_others\.holder\s*)(title:c_castle_black\.holder)",
        r"\1has_global_variable = agot_ln_horn_ritual_ready\r\n\t\t\t\t\2",
        "Horn-gated Wall breach",
    )
    return value


def patch_decisions() -> str:
    value = legacy.patch_decisions()
    start, end = definition_span(value, "others_trigger_invasion")
    block = value[start:end]
    block = legacy.replace_regex(
        block,
        r"effect\s*=\s*\{\s*trigger_event\s*=\s*others\.1\s*\}",
        "is_valid = {\n\t\tglobal_var:what_season_is_it = 3\n\t\thas_dlc_feature = roads_to_power\n\t}\n\n\teffect = {\n\t\ttrigger_event = agot_ln.12\n\t}",
        "manual winter gate",
    )
    return value[:start] + block + value[end:]


def patch_other_events() -> str:
    relative = "events/others_events/others_events.txt"
    value = legacy.patch_simple_files()[relative]
    marker = "\t\tthe_long_night_setup_effect = yes"
    addition = (
        marker
        + "\n\t\tset_global_variable = { name = agot_long_night_active value = yes }\n\t\tset_global_variable = { name = agot_long_night_threat value = 0 }"
    )
    return legacy.replace_exact(value, marker, addition, "activate crisis state")


def patch_cb() -> str:
    value = legacy.patch_cb()
    return legacy.replace_regex(
        value,
        r"(war_for_the_dawn_cb\s*=\s*\{.*?on_victory\s*=\s*\{)",
        r"\1\r\n\tagot_war_victory_effects = yes",
        "AGOT war victory hook",
        flags=re.DOTALL,
    )


def api_triggers() -> str:
    return """is_agot_long_night_loaded_trigger = {
\thas_global_variable = agot_long_night_enabled
}

is_agot_long_night_active_trigger = {
\thas_global_variable = agot_long_night_active
\tNOT = { has_global_variable = agot_long_night_completed }
}

is_agot_long_night_start_eligible_trigger = {
\tNOT = { has_global_variable = others_invasion_has_arrived }
\tNOT = { has_global_variable = agot_long_night_dependency_blocked }
\tNOT = { has_game_rule = others_invasion_wont_happen }
\tcurrent_year >= global_var:agot_long_night_eligible_year
\tglobal_var:what_season_is_it = 3
}
"""


def rework_effects() -> str:
    return """agot_ln_spawn_reinforcement_effect = {
\tif = { limit = { has_game_rule = others_weak_invasion } spawn_army = { men_at_arms = { type = other_maa stacks = 25 } name = wights uses_supply = no location = capital_province } }
\telse_if = { limit = { has_game_rule = others_strong_invasion } spawn_army = { men_at_arms = { type = other_maa stacks = 87 } name = wights uses_supply = no location = capital_province } }
\telse_if = { limit = { has_game_rule = others_insane_invasion } spawn_army = { men_at_arms = { type = other_maa stacks = 125 } name = wights uses_supply = no location = capital_province } }
\telse = { spawn_army = { men_at_arms = { type = other_maa stacks = 50 } name = wights uses_supply = no location = capital_province } }
}

agot_ln_add_threat_effect = {
\tchange_global_variable = { name = agot_long_night_threat add = $AMOUNT$ }
\tif = {
\t\tlimit = { global_var:agot_long_night_threat >= 25 NOT = { has_global_variable = agot_ln_threat_25 } }
\t\tset_global_variable = { name = agot_ln_threat_25 value = yes }
\t\tif = { limit = { has_game_rule = agot_long_night_dragon_on } set_global_variable = { name = agot_ln_horn_ritual_ready value = yes } }
\t\telse = { trigger_event = { id = agot_ln.30 days = 30 } }
\t\tagot_ln_spawn_reinforcement_effect = yes
\t}
\tif = { limit = { global_var:agot_long_night_threat >= 50 NOT = { has_global_variable = agot_ln_threat_50 } } set_global_variable = { name = agot_ln_threat_50 value = yes } agot_ln_spawn_reinforcement_effect = yes add_character_modifier = agot_ln_threat_50_modifier }
\tif = { limit = { global_var:agot_long_night_threat >= 75 NOT = { has_global_variable = agot_ln_threat_75 } } set_global_variable = { name = agot_ln_threat_75 value = yes } agot_ln_spawn_reinforcement_effect = yes add_character_modifier = agot_ln_threat_75_modifier }
}

agot_ln_join_war_for_dawn_effect = {
\tif = {
\t\tlimit = { title:h_the_others.holder = { any_character_war = { is_defender = title:h_the_others.holder using_cb = war_for_the_dawn_cb } } }
\t\ttitle:h_the_others.holder = {
\t\t\trandom_character_war = { limit = { is_defender = title:h_the_others.holder using_cb = war_for_the_dawn_cb } add_attacker = root }
\t\t}
\t}
}
"""


def on_actions() -> str:
    return """on_combat_end_winner = { on_actions = { agot_ln_combat_growth } }

agot_ln_combat_growth = {
\ttrigger = { is_agot_long_night_active_trigger = yes side_primary_participant = { has_trait = other_trait } }
\teffect = {
\t\tside_primary_participant = { agot_ln_add_threat_effect = { AMOUNT = 2 } }
\t\tif = { limit = { scope:wipe = yes } side_primary_participant = { agot_ln_add_threat_effect = { AMOUNT = 3 } } }
\t}
}
"""


def rework_events() -> str:
    return """namespace = agot_ln

agot_ln.1 = {
\ttype = character_event
\ttitle = agot_ln.1.t
\tdesc = agot_ln.1.desc
\ttheme = realm
\toption = { name = agot_ln.1.a }
}

agot_ln.10 = {
\tscope = none
\thidden = yes
\timmediate = {
\t\tif = {
\t\t\tlimit = { is_agot_long_night_start_eligible_trigger = yes }
\t\t\tset_global_variable = { name = others_invasion_triggered value = yes }
\t\t\tevery_player = { trigger_event = agot_ln.11 }
\t\t\ttrigger_event = { id = others.1 days = 90 }
\t\t}
\t\telse = { trigger_event = { id = agot_ln.10 days = 90 } }
\t}
}

agot_ln.11 = {
\ttype = character_event
\ttitle = agot_ln.11.t
\tdesc = agot_ln.11.desc
\ttheme = realm
\toption = { name = agot_ln.11.a }
}

agot_ln.12 = {
\tscope = none
\thidden = yes
\ttrigger = { global_var:what_season_is_it = 3 has_dlc_feature = roads_to_power }
\timmediate = {
\t\tset_global_variable = { name = others_invasion_triggered value = yes }
\t\tevery_player = { trigger_event = agot_ln.11 }
\t\ttrigger_event = { id = others.1 days = 90 }
\t}
}

agot_ln.20 = {
\thidden = yes
\ttrigger = { is_agot_long_night_active_trigger = yes has_trait = other_trait }
\timmediate = {
\t\tif = { limit = { scope:county = title:c_castle_black } agot_ln_add_threat_effect = { AMOUNT = 10 } }
\t\telse = { agot_ln_add_threat_effect = { AMOUNT = 5 } }
\t}
}

agot_ln.30 = {
\thidden = yes
\tscope = none
\timmediate = {
\t\tset_global_variable = { name = agot_ln_horn_ritual_ready value = yes }
\t\tevery_player = { trigger_event = agot_ln.31 }
\t}
}

agot_ln.31 = {
\ttype = character_event
\ttitle = agot_ln.31.t
\tdesc = agot_ln.31.desc
\ttheme = realm
\toption = { name = agot_ln.31.a }
}

agot_ln.39 = {
\ttype = character_event
\thidden = yes
\timmediate = {
\t\tif = { limit = { exists = title:h_the_iron_throne.holder title:h_the_iron_throne.holder = { is_alive = yes NOT = { has_faith = faith:cold_gods } } } title:h_the_iron_throne.holder = { save_scope_as = agot_ln_leader } }
\t\telse_if = { limit = { exists = title:e_the_north.holder title:e_the_north.holder = { is_alive = yes NOT = { has_faith = faith:cold_gods } } } title:e_the_north.holder = { save_scope_as = agot_ln_leader } }
\t\telse = { ordered_independent_ruler = { limit = { capital_county.title_province = { geographical_region = world_westeros_seven_kingdoms } NOT = { has_faith = faith:cold_gods } } order_by = max_military_strength position = 0 save_scope_as = agot_ln_leader } }
\t\tif = { limit = { exists = scope:agot_ln_leader } set_global_variable = { name = agot_ln_coalition_leader value = scope:agot_ln_leader } scope:agot_ln_leader = { start_war = { cb = war_for_the_dawn_cb target = title:h_the_others.holder claimant = this } } }
\t\tevery_independent_ruler = { limit = { capital_county.title_province = { geographical_region = world_westeros_seven_kingdoms } NOT = { has_faith = faith:cold_gods } } trigger_event = agot_ln.40 }
\t}
}

agot_ln.40 = {
\ttype = character_event
\ttitle = agot_ln.40.t
\tdesc = agot_ln.40.desc
\ttheme = war
\toption = { name = agot_ln.40.a agot_ln_join_war_for_dawn_effect = yes ai_chance = { base = 40 modifier = { add = 40 capital_county.title_province = { geographical_region = world_westeros_the_north } } modifier = { add = 20 faith.religion = religion:the_pact_religion } } }
\toption = { name = agot_ln.40.b if = { limit = { gold >= 100 } remove_short_term_gold = 100 global_var:agot_ln_coalition_leader = { add_gold = 100 } } ai_chance = { base = 30 } }
\toption = { name = agot_ln.40.c ai_chance = { base = 20 } }
\toption = { name = agot_ln.40.d add_prestige = -100 ai_chance = { base = 10 modifier = { add = 30 has_trait = craven } } }
}
"""


def modifiers() -> str:
    return """agot_ln_leaderless_modifier = {
\tadvantage = -10
\tmonthly_prestige = -1
}
agot_ln_threat_50_modifier = { advantage = 5 siege_phase_time = -0.05 }
agot_ln_threat_75_modifier = { advantage = 10 siege_phase_time = -0.10 }
"""


def localization() -> str:
    return """l_english:
 agot_ln.1.t:0 "Roads to Power Required"
 agot_ln.1.desc:0 "AGOT: The Long Night requires the Roads to Power expansion. The crisis has been disabled for this campaign."
 agot_ln.1.a:0 "The road is closed."
 agot_ln.11.t:0 "The Cold Winds Are Rising"
 agot_ln.11.desc:0 "In the dead of winter, ravens carry impossible reports from beyond the Wall. Pale shapes move beneath the aurora, and the oldest tales are spoken aloud once more."
 agot_ln.11.a:0 "The night gathers."
 agot_ln.31.t:0 "The Horn of Winter"
 agot_ln.31.desc:0 "A terrible note rolls out of the far north. Whether the horn is Joramun's or some older instrument, the wards upon the Wall have begun to crack."
 agot_ln.31.a:0 "The Wall will not hold forever."
 agot_ln.40.t:0 "A War for the Dawn"
 agot_ln.40.desc:0 "The Wall is broken. The chosen leader of the living calls every realm of Westeros to stand against the dead."
 agot_ln.40.a:0 "Join the War for the Dawn."
 agot_ln.40.b:0 "Send gold and supplies."
 agot_ln.40.c:0 "Remain neutral."
 agot_ln.40.d:0 "Refuse the call."
 agot_ln_leaderless_modifier:0 "A Herald Fallen"
 agot_ln_leaderless_modifier_desc:0 "The destruction of the Great Other's herald has temporarily disordered the dead."
 agot_ln_threat_50_modifier:0 "The Dead Gather"
 agot_ln_threat_50_modifier_desc:0 "Every conquest adds fresh bodies to the host."
 agot_ln_threat_75_modifier:0 "The Endless Night"
 agot_ln_threat_75_modifier_desc:0 "The Army of the Dead advances beneath an ever-deepening winter."
 others_standard_invasion:0 "Escalating Crisis"
 others_standard_invasion_desc:0 "The dead begin as a grave regional threat and gain bounded reinforcements through conquest and decisive victories."
 others_weak_invasion:0 "Restrained Crisis"
 others_strong_invasion:0 "Great Winter"
 others_insane_invasion:0 "Apocalyptic Winter"
 others_historical_invasion:0 "Canon Threshold (298 AC)"
 others_immediate_invasion:0 "Next Eligible Winter"
 agot_long_night_dragon_off:0 "Ice Dragon Disabled"
 agot_long_night_dragon_on:0 "Ice Dragon Enabled"
"""


def expected_files() -> dict[str, bytes]:
    for path, digest in PINNED_HASHES.items():
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != digest:
            raise ValueError(f"pinned dependency changed: {path} ({actual})")

    files: dict[str, bytes] = {}
    for source in sorted(p for p in LONG_NIGHT.rglob("*") if p.is_file()):
        relative = source.relative_to(LONG_NIGHT).as_posix()
        if relative not in SKIP:
            files[relative] = source.read_bytes()

    patched = legacy.patch_simple_files()
    patched.pop("common/scripted_rules/00_rules.txt", None)
    fixed_loc = patched["localization/english/agot_long_night_compatch_l_english.yml"]
    fixed_loc = re.sub(r"(?m)^\s*GAME_OVER_CANNOT_PLAY_WIGHT:.*\n", "", fixed_loc)
    patched["localization/english/agot_long_night_compatch_l_english.yml"] = fixed_loc
    trait_loc = patched["localization/english/theothers_l_english.yml"]
    trait_loc = re.sub(
        r"(?m)^\s*trait_nightking:.*$",
        ' trait_nightking:0 "Herald of the Great Other"',
        trait_loc,
    )
    trait_loc = re.sub(
        r"(?m)^\s*trait_nightking_desc:.*$",
        ' trait_nightking_desc:0 "The transferable war-leader and voice of the power behind the Long Night."',
        trait_loc,
    )
    patched["localization/english/theothers_l_english.yml"] = trait_loc
    patched["common/game_rules/long_night_game_rules.txt"] = game_rules()
    patched["common/men_at_arms_types/long_night_maa_types.txt"] = patch_maa()
    patched["common/scripted_effects/agot_long_night_scripted_effects.txt"] = (
        patch_effects()
    )
    patched["common/casus_belli_types/00_long_night_cbs.txt"] = patch_cb()
    patched["common/decisions/00_agot_long_night_decisions.txt"] = patch_decisions()
    patched["common/story_cycles/the_long_night.txt"] = patch_story()
    patched["events/others_events/others_maintenance_events.txt"] = patch_maintenance()
    patched["events/others_events/others_events.txt"] = patch_other_events()
    patched[str(legacy.RELATIVE_ANIMATIONS)] = core_animation()
    patched["events/season_events.txt"] = patch_seasons()
    patched["common/scripted_triggers/agot_long_night_public_triggers.txt"] = (
        api_triggers()
    )
    patched["common/scripted_effects/agot_long_night_rework_effects.txt"] = (
        rework_effects()
    )
    patched["common/on_action/agot_long_night_rework_on_actions.txt"] = on_actions()
    patched["common/modifiers/agot_long_night_rework_modifiers.txt"] = modifiers()
    patched["events/agot_long_night_rework_events.txt"] = rework_events()
    patched["localization/english/zz_agot_long_night_rework_l_english.yml"] = (
        localization()
    )

    siege_events = text(LONG_NIGHT / "events/others_events/others_siege_events.txt")
    siege_events = legacy.replace_exact(
        siege_events,
        "\t\tsave_scope_as = occupant",
        "\t\tsave_scope_as = occupant\n\t\tsave_scope_as = occupier",
        "siege occupier scope",
    )
    patched["events/others_events/others_siege_events.txt"] = siege_events

    aftermath_effects = text(
        LONG_NIGHT / "common/scripted_effects/zz_long_night_plus_aftermath_effects.txt"
    )
    aftermath_effects = legacy.replace_regex(
        aftermath_effects,
        r"(?m)^\s*NOT\s*=\s*\{\s*this\s*\?=\s*scope:ln_unleash_chooser\s*\}\s*\r?\n",
        "",
        "optional aftermath chooser scope",
    )
    patched["common/scripted_effects/zz_long_night_plus_aftermath_effects.txt"] = (
        aftermath_effects
    )

    for relative in (
        "common/on_action/00_others_on_actions.txt",
        "gfx/portraits/trait_portrait_modifiers/whitewalker_trait_modifiers.txt",
    ):
        patched[relative] = text(LONG_NIGHT / relative)

    siege_path = "common/on_action/AGOT Invasions/invasions_siege.txt"
    siege = text(LONG_NIGHT / siege_path)
    siege = legacy.replace_exact(
        siege,
        "others_siege.0001",
        "others_siege.0001\n        agot_ln.20",
        "threat siege event",
    )
    patched[siege_path] = siege

    for relative, value in patched.items():
        if relative not in SKIP:
            files[relative] = encoded(value)
    return files


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    files = expected_files()
    changed: list[str] = []
    for relative, content in sorted(files.items()):
        destination = OUTPUT / relative
        if not destination.is_file() or destination.read_bytes() != content:
            changed.append(relative)
            if not args.check:
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(content)
    if args.check and changed:
        raise SystemExit(
            "generated Long Night files are stale:\n" + "\n".join(changed[:30])
        )
    action = "checked" if args.check else "generated"
    print(f"{action} {len(files)} standalone files; {len(changed)} changed")


if __name__ == "__main__":
    try:
        main()
    except (KeyError, ValueError) as error:
        raise SystemExit(f"cannot generate standalone Long Night: {error}") from error
