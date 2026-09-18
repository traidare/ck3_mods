#!/usr/bin/env python3
"""Generate the narrow final overrides needed by the AGOT playset."""

from __future__ import annotations

import re
import subprocess
import tempfile
from collections import Counter, defaultdict
from collections.abc import Iterable, Iterator
from pathlib import Path

from gen import GenerationContext
from gen.text import (
    definition_span,
    matching_brace,
    read_source,
    replace_exact,
    replace_regex,
)

HUD_RELATIVE = Path("gui/hud.gui")
MAP_ICON_RELATIVE = Path("gui/map_icon_layer.gui")
IS_HUMAN_RELATIVE = Path("common/scripted_triggers/zzz_agot_playset_is_human.txt")
AGOT_CHARACTER_TRIGGERS = Path(
    "common/scripted_triggers/00_agot_character_triggers.txt"
)
KRAKEN_TRIGGERS = Path("common/scripted_triggers/zz_kraken_character_triggers.txt")
GREAT_COUNCILS_TRIGGERS = Path(
    "common/scripted_triggers/zzz_Great_Councils_replaced_triggers.txt"
)
IS_DIARCH_VALID_RELATIVE = Path(
    "common/scripted_rules/zzz_agot_playset_is_diarch_valid.txt"
)
CAN_BE_ACTIVITY_GUEST_RELATIVE = Path(
    "common/scripted_rules/zzz_agot_playset_can_be_activity_guest.txt"
)
RULES_RELATIVE = Path("common/scripted_rules/00_rules.txt")
LONG_NIGHT_DIARCH_RULES = Path("common/scripted_rules/zz_ln_diarch_rules.txt")
LONG_NIGHT_ACTIVITY_RULES = Path("common/scripted_rules/zz_ln_activity_rules.txt")
LIVING_WESTEROS_RULES = Path("common/scripted_rules/zz_guest_right_rules.txt")
LOV_DIARCH_GUARD = "this ?="
CHAPLAIN_SUMMON_GUARD = (
    "\t\t\t\t\tcp:councillor_court_chaplain ?= {\n"
    "\t\t\t\t\t\tif = {\n"
    "\t\t\t\t\t\t\tlimit = {\n"
    "\t\t\t\t\t\t\t\texists = root.location\n"
    "\t\t\t\t\t\t\t\texists = root.involved_activity\n"
    "\t\t\t\t\t\t\t}\n"
    "\t\t\t\t\t\t\tset_location = root.location\n"
    "\t\t\t\t\t\t\tadd_to_activity_without_travel = root.involved_activity\n"
    "\t\t\t\t\t\t}\n"
    "\t\t\t\t\t}\n"
)
KRAKEN_CLAUSE = "NOT = { has_trait = kraken }"
GREAT_COUNCILS_CLAUSE = (
    "NOT = { has_character_flag = zzz_great_councils_disable } #AGC Added"
)
FIND_ELDER_DATACONTEXT = (
    "datacontext = \"[GetDecisionWithKey('find_elder_interaction')]\""
)
GRANDEUR_RELATIVE = Path(
    "gfx/court_scene/scene_settings/grandeur_levels/grandeur_levels.txt"
)
COW_MODEL_TRIGGER_RELATIVE = Path(
    "common/scripted_triggers/zzz_agot_cow_building_model_trigger.txt"
)
COW_NOW_GRAPHICS_RELATIVE = Path(
    "common/buildings/replace/99_background_graphics_buildings.txt"
)
# Hand-merged repairs the always-on compatch ships verbatim rather than
# deriving.  Each one's parents — AGOT, COW-AGOT, Additional Models, and base
# Seasons — load ahead of every optional module and none of them re-opens the
# same definitions, so that copy is the effective one in all three profiles.
COW_MODEL_TRIGGER_ASSET = "cow_building_model_trigger.txt"
CORE_VERBATIM_ASSETS = {
    COW_MODEL_TRIGGER_ASSET: COW_MODEL_TRIGGER_RELATIVE,
    "agot_runtime_rules.txt": Path("common/scripted_rules/zzz_agot_runtime_rules.txt"),
    "seasons_runtime_weather_triggers.txt": Path(
        "common/scripted_triggers/zz_agot_seasons_runtime_weather_triggers.txt"
    ),
}
MDE_RELATIVE = Path("common/on_action/agot_on_actions/mde_yearly_on_actions.txt")
AGOT_YEARLY_RELATIVE = Path(
    "common/on_action/agot_on_actions/agot_yearly_on_actions.txt"
)
CHILDHOOD_ON_ACTIONS_RELATIVE = Path("common/on_action/childhood_on_actions.txt")
AGOT_CHILDHOOD_ON_ACTIONS_RELATIVE = Path(
    "common/on_action/agot_on_actions/agot_childhood_on_actions.txt"
)
CANON_DRAGON_BIRTHDAY_RELATIVE = Path(
    "common/on_action/agot_on_actions/"
    "zzz_agot_playset_canon_dragon_birthday_on_actions.txt"
)
CANON_DRAGON_BIRTHDAY_ACTION = "on_10th_birthday_tame_canon_dragon"
TITLE_LANGUAGES = ("english", "spanish")

TOURNAMENT_RELATIVE = Path("common/activities/activity_types/tournament.txt")
CORONATION_RELATIVE = Path("common/activities/activity_types/coronation.txt")
WEDDING_RELATIVE = Path("common/activities/activity_types/wedding.txt")
DRAGON_HATCHING_RELATIVE = Path(
    "common/activities/activity_types/agot_dragon_hatching.txt"
)
DRAGON_CRADLING_RELATIVE = Path(
    "common/on_action/agot_on_actions/agot_dragon_cradling_on_action.txt"
)
DRAGON_HATCHING_EVENTS_RELATIVE = Path(
    "events/activities/agot_hatching_activity/agot_dragon_hatching_activity_events.txt"
)
RUINS_EVENTS_RELATIVE = Path("events/agot_events/agot_ruins_events.txt")
DRAGONPIT_EFFECTS_RELATIVE = Path(
    "common/scripted_effects/00_agot_dragonpit_effects.txt"
)
LOV_DRAGONPIT_EFFECTS_RELATIVE = Path(
    "common/scripted_effects/zzzz_lv_lov_scripted_effect_delta_overrides_v0_2_2.txt"
)
MDE_LOV_DRAGONPIT_OUTPUT = Path(
    "common/scripted_effects/zzzzz_agot_playset_mde_lov_dragonpit_effects.txt"
)
MDE_HUD_RELATIVE = Path("gui/custom_gui/mde_gui/mde_hud.gui")
TRAVEL_ON_ACTIONS_RELATIVE = Path("common/on_action/travel_on_actions.txt")
TRAVEL_OPTIONS_RELATIVE = Path("common/travel/travel_options/travel_options.txt")
AGOT_TRAVEL_OPTIONS_RELATIVE = Path(
    "common/travel/travel_options/agot_travel_options.txt"
)
CORONATION_EVENTS_RELATIVE = Path(
    "events/activities/coronation_activity/coronation_events.txt"
)
CONTEST_EVENTS_RELATIVE = Path("events/activities/tournaments/contest_events.txt")
EP3_SCRIPTED_EFFECTS_RELATIVE = Path(
    "common/scripted_effects/07_dlc_ep3_scripted_effects.txt"
)

# Much Faster Activities regenerates its overrides from vanilla, so its files
# carry vanilla lines AGOT had already replaced alongside the timing edits that
# are the mod's actual purpose.  Restoring AGOT's text for each of those before
# the merge keeps MFA's delta to the timings, which is the only part the playset
# wants and the only part that merges without a conflict.
MFA_VANILLA_REGRESSIONS = (
    (
        "tournament jungle terrain",
        "\t\t\t\t\tterrain = jungle\n",
        "\t\t\t\t\t#AGOT Modified\n"
        "\t\t\t\t\t# terrain = jungle\n"
        "\t\t\t\t\tagot_is_jungle_terrain = yes\n",
    ),
    (
        "tournament land-of-the-bow archery bonus",
        "\t\t\t\tif = {\n"
        "\t\t\t\t\tlimit = {\n"
        "\t\t\t\t\t\tculture = { has_cultural_tradition = tradition_land_of_the_bow }\n"
        "\t\t\t\t\t}\n"
        "\t\t\t\t\tadd = {\n"
        "\t\t\t\t\t\tvalue = 50\n"
        "\t\t\t\t\t\tdesc = tradition_land_of_the_bow_name\n"
        "\t\t\t\t\t}\n"
        "\t\t\t\t}\n",
        "\t\t\t\t#AGOT Disabled\n"
        "\t\t\t\t# if = {\n"
        "\t\t\t\t# \tlimit = {\n"
        "\t\t\t\t# \t\tculture = { has_cultural_tradition = tradition_land_of_the_bow }\n"
        "\t\t\t\t# \t}\n"
        "\t\t\t\t# \tadd = {\n"
        "\t\t\t\t# \t\tvalue = 50\n"
        "\t\t\t\t# \t\tdesc = tradition_land_of_the_bow_name\n"
        "\t\t\t\t# \t}\n"
        "\t\t\t\t# }\n",
    ),
)

MFA_WEDDING_FARMLANDS = "\t\t\t\tterrain = farmlands\n"
AGOT_WEDDING_FARMLANDS = (
    "\t\t\t\t#AGOT Modified\n"
    "\t\t\t\t# terrain = farmlands\n"
    "\t\t\t\tagot_is_farmlands_terrain = yes\n"
)

TRAVELERS_SCOPE_COMMENT = "current_travel_plan ?= { # Travelers: Fix scope errors"
TRAVELERS_SCOPE_NORMALIZED = "current_travel_plan ?= {"
TRAVELERS_ON_ACTION_MARKERS = (
    "is_imprisoned = no # Travelers",
    "# Travelers-FF",
    "is_at_same_location = root # Travelers",
    "travl_travel.0002 # Travelers: Add missing entourage members",
    "add_character_modifier = unop_prepare_travels_character_modifier",
    "remove_character_modifier = unop_prepare_travels_character_modifier",
)
TRAVELERS_WRAPPED_ON_ACTIONS = (
    "on_travel_plan_movement",
    "on_travel_plan_arrival",
    "on_travel_plan_start",
    "on_travel_plan_complete",
    "on_travel_plan_abort",
    "on_travel_plan_cancel",
    "on_travel_leader_removed",
)
LOV_TRAVEL_MARKERS = (
    "lv_valyria_subregion_restored = yes",
    "save_temporary_scope_as = temp_travel_current_location",
    "target = scope:temp_travel_current_location",
    "province = scope:temp_travel_current_location",
)
TRAVELERS_OPTION_AVAILABILITY = "is_available_at_peace_ai_adult = yes # Travelers"
LIVING_WESTEROS_GUEST_MARKERS = (
    "guest_right_denied_houses",
    "guest_right_breaker_modifier",
    "guest_right_captor_modifier",
    "guest_right_breaker_lenient_modifier",
    "guest_right_captor_lenient_modifier",
)

HOLY_SITE_HOLDER_GUARD = (
    "exists = barony.holder "
    "# A holy site's barony can be unheld, and CK3 drops the whole clause "
    "when its holder does not resolve.\n"
)
DRAGON_HATCHING_DEATH_LIMIT = (
    "\t\t\t\tthis = scope:host\n"
    "\t\t\t\thas_character_flag = agot_dead_in_dragon_hatching\n"
)
CANON_DEATH_GUARD = (
    "\t\t\t\t# The host survives their own hatching accident while AGOT:\n"
    "\t\t\t\t# Canon Continuity protects them.\n"
    "\t\t\t\tagot_cc_event_death_protected_trigger = no\n"
)

# Culture and Faith Granularity's contest_events delta, counted the same way its
# own compatch counts it, so a CaFG or AGOT release that moves either number
# fails here instead of shipping a half-merged file.
CAFG_CALL = re.compile(r"\bE_kCAFG_[A-Za-z0-9_]+")
AGOT_MARKER = re.compile(r"(?i)#\s*AGOT\b")
CONTEST_EVENTS_CAFG_CALLS = 1
CONTEST_EVENTS_AGOT_MARKERS = 24


def title_localization_relative(language: str) -> Path:
    return Path(
        f"localization/replace/{language}/agot/replace/00_agot_titles_l_{language}.yml"
    )


SOURCE_RELATIVES = {
    "NOW": Path("common/landed_titles/01_agot_landed_titles.txt"),
    "SEASON_EVENTS": Path("events/lov_season_events.txt"),
    "SEASON_FX": Path("gfx/FX/province_effects.fxh"),
    "SEASON_REGIONS": Path("map_data/geographical_regions/north_sans_neck.txt"),
    **{
        f"NOW_TITLES_{language.upper()}": title_localization_relative(language)
        for language in TITLE_LANGUAGES
    },
}
OUTPUT_RELATIVES = {
    "SEASON_EVENTS": SOURCE_RELATIVES["SEASON_EVENTS"],
    "SEASON_REGIONS": SOURCE_RELATIVES["SEASON_REGIONS"],
    **{
        f"NOW_TITLES_{language.upper()}": title_localization_relative(language)
        for language in TITLE_LANGUAGES
    },
}

# The NOW-COW compatch remaps Sisterton's and Dunstonbury's provinces, and
# `zzz_agot_cow_building_model_trigger.txt` keys its models to that remap.  NOW
# names none of these baronies, so its title file would leave AGOT's originals.
COW_TITLE_NAMES = {
    "english": (
        ("b_breakwater_castle", "Breakwater Castle"),
        ("b_breakwater_watch", "Breakwaterwatch"),
        ("b_dordon", "Castle Sunderland"),
    ),
    "spanish": (
        ("b_breakwater_castle", "Castillo Rompeolas"),
        ("b_breakwater_watch", "Atalaya del Este"),
        ("b_dordon", "Castillo Sunderland"),
    ),
}
COW_TITLE_HEADER = (
    "# COW Sisterton/Dunstonbury barony names "
    "(see zzz_agot_cow_building_model_trigger.txt)"
)

# Localization defects NOW ships that this module repairs because it is the
# file's effective last writer.  Each is keyed to the exact upstream line, so a
# fix upstream fails the build instead of being applied twice.
NOW_TITLE_REPAIRS = {
    "spanish": (
        (
            ' d_crackclaw_point: "$c_dyre_den$\n',
            ' d_crackclaw_point: "$c_dyre_den$"\n',
            "NOW Spanish d_crackclaw_point closing quote",
        ),
    ),
}


def read_text(path: Path) -> str:
    return read_source(path, normalize_newlines=True)


def normalize_output(text: str) -> str:
    """Keep generated whole-file overrides reviewable without changing tokens."""
    return re.sub(r"[ \t]+(?=\n)", "", text).rstrip() + "\n"


def require_balanced_quotes(text: str, *, label: str) -> None:
    """Reject an unterminated localization value.

    CK3 swallows the rest of the entry when a value loses its closing quote, so
    this is worth catching before the file reaches the Launcher.
    """
    for number, line in enumerate(text.split("\n"), start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if line.count('"') % 2:
            raise AssertionError(f"{label}: unterminated value on line {number}")


def generate_title_localization(text: str, language: str) -> str:
    """Rebase NOW's title names, keeping only this module's COW barony delta."""
    label = f"NOW {language} title localization"
    for old, new, repair in NOW_TITLE_REPAIRS.get(language, ()):
        text = replace_exact(text, old, new, label=repair)
    require_balanced_quotes(text, label=label)

    lines = [text.rstrip("\n"), "", COW_TITLE_HEADER]
    for key, value in COW_TITLE_NAMES[language]:
        if re.search(rf"(?m)^\s*{re.escape(key)}\s*:", text):
            raise AssertionError(f"{label}: NOW now names {key} itself")
        lines.append(f' {key}: "{value}"')
    return "\n".join(lines) + "\n"


def grandeur_cultures(text: str) -> list[str]:
    """List the court-scene cultures a `grandeur_levels.txt` registers."""
    return re.findall(r'culture\s*=\s*"([^"]+)"', text)


def check_grandeur_coverage(amsb: str, amsb_lov: str) -> None:
    """Confirm no override of this file is needed.

    Every playset parent owns `grandeur_levels.txt` whole, so the last of them
    silently drops the court scenes the others registered.  The temporary
    AMSB/LoV compatch loads last and currently registers a superset of
    AMSB's scenes, which is the only reason this module does not have to merge
    the file itself.  Fail if that stops holding: a court scene with no entry
    never progresses a visual culture level, and nothing reports it at runtime.
    """
    covered = set(grandeur_cultures(amsb_lov))
    missing = [name for name in grandeur_cultures(amsb) if name not in covered]
    if missing:
        raise AssertionError(
            "the AMSB/LoV compatch must cover every AMSB court "
            f"scene ({missing}); this module must merge {GRANDEUR_RELATIVE} again"
        )


def province_building_pairs(text: str) -> set[tuple[str, str]]:
    return set(
        re.findall(
            r"this\s*=\s*province:(\d+)\s*\n\s*has_building_or_higher\s*=\s*(\w+)",
            text,
        )
    )


def check_cow_model_remaps(cow_now: str, owned_trigger: str) -> None:
    """Confirm the hand-merged model trigger still matches the NOW-COW compatch.

    That compatch is not enabled — its `map_object_data` would shadow the map
    compatch — so its province remaps are carried by hand in
    `zzz_agot_cow_building_model_trigger.txt`.  Pinning it as a source turns a
    silent remap into a generation failure.
    """
    missing = province_building_pairs(cow_now) - province_building_pairs(owned_trigger)
    if missing:
        raise AssertionError(
            "NOW-COW special-building model pairs are absent from "
            f"{COW_MODEL_TRIGGER_RELATIVE}: {sorted(missing)}"
        )


MDE_PULSE = "agot_yearly_owned_dragon_pulse"
MDE_EGGS_DEFINITIONS = (
    "yearly_global_pulse",
    "on_dragon_lay_canon_clutch_on_action",
    "clean_lists_yearly_on_action",
)
EXPECTED_MDE_FILLER_EVENTS = 14
MDE_HEADER = """# Final integration owner of mde_yearly_on_actions.txt.
#
# AGOT More Dragon Eggs and AGOT - More Dragon Events both ship this path, so
# the later of them drops the other's file entirely.  Their definitions are
# disjoint, and CK3 merges on_action declarations across files, so More Dragon
# Events' pulse is re-emitted below as its delta over AGOT's own declaration
# rather than as its full copy -- re-emitting the copy would merge AGOT's 38
# entries a second time and halve the chance of no event firing.
"""


def top_level_definitions(text: str) -> list[str]:
    return re.findall(r"(?m)^([a-z_0-9]+)\s*=\s*\{", text)


def block_of(text: str, name: str) -> str:
    start, end = named_block(text, name)
    return text[start : end + 1]


def weighted_events(block: str, prefix: str) -> list[str]:
    return re.findall(rf"(?m)^\s*(\d+\s*=\s*{prefix}\.\d+.*?)\s*$", block)


def generate_mde_on_actions(eggs: str, events: str, agot: str) -> str:
    """Union the two contested dragon on_action files.

    More Dragon Events' pulse is a copy of AGOT's plus its own entries, so only
    the additions are emitted; the copied part is asserted identical to AGOT's
    so an upstream rebalance fails here instead of being silently discarded.
    """
    if tuple(top_level_definitions(eggs)) != MDE_EGGS_DEFINITIONS:
        raise AssertionError(
            f"More Dragon Eggs definitions changed: {top_level_definitions(eggs)}"
        )
    if top_level_definitions(events) != [MDE_PULSE]:
        raise AssertionError(
            f"More Dragon Events definitions changed: {top_level_definitions(events)}"
        )

    events_block = block_of(events, MDE_PULSE)
    agot_block = block_of(agot, MDE_PULSE)
    if weighted_events(events_block, "agot_filler_dragon") != weighted_events(
        agot_block, "agot_filler_dragon"
    ):
        raise AssertionError(
            "More Dragon Events must copy AGOT's dragon pulse verbatim; "
            "re-derive the delta before re-emitting it"
        )
    additions = weighted_events(events_block, "mde_filler_dragon")
    if len(additions) != EXPECTED_MDE_FILLER_EVENTS:
        raise AssertionError(
            f"More Dragon Events pulse additions changed: {len(additions)} entries"
        )

    trigger = block_of(agot_block, "trigger")
    body = "\n".join(f"\t\t{entry}" for entry in additions)
    return (
        f"{MDE_HEADER}{eggs.rstrip()}\n\n"
        f"{MDE_PULSE} = {{\n"
        f"{trigger}\n"
        f"\trandom_events = {{\n{body}\n\t}}\n"
        "}\n"
    )


def generate_canon_dragon_birthday_on_action(
    agot_childhood: str, agot_childhood_actions: str, personality_childhood: str
) -> str:
    """Restore AGOT's canon-dragon birthday dispatch beside the personality mod."""
    agot_birthday = block_of(agot_childhood, "on_10th_birthday")
    personality_birthday = block_of(personality_childhood, "on_10th_birthday")
    if agot_birthday.count(CANON_DRAGON_BIRTHDAY_ACTION) != 1:
        raise AssertionError(
            "AGOT on_10th_birthday must dispatch "
            f"{CANON_DRAGON_BIRTHDAY_ACTION} exactly once"
        )
    if CANON_DRAGON_BIRTHDAY_ACTION in personality_birthday:
        raise AssertionError(
            "New Personality Events already dispatches AGOT's canon-dragon "
            "birthday action; remove this bridge to avoid firing it twice"
        )

    action = block_of(agot_childhood_actions, CANON_DRAGON_BIRTHDAY_ACTION)
    required_fragments = (
        "agot_canon_dragons_enabled = yes",
        "is_ai = yes",
        "agot_is_canon_rider = yes",
        "type = agot_dragon",
        "count = 0",
        "scheme_type = bond_with_dragon_scheme",
        "flag = attempting_canon_bond",
        "dragon_taming_events.9000",
    )
    missing = [fragment for fragment in required_fragments if fragment not in action]
    if missing:
        raise AssertionError(
            "AGOT canon-dragon birthday action changed; re-audit the bridge "
            f"before generation (missing {missing})"
        )

    return f"""# Restore AGOT's canon-rider birthday dispatch alongside New Personality Events.
# The parents contest childhood_on_actions.txt, while on_action declarations in
# uniquely named files merge. Remove this bridge if the later parent adds the
# dispatch itself.
on_10th_birthday = {{
\ton_actions = {{
\t\t{CANON_DRAGON_BIRTHDAY_ACTION}
\t}}
}}
"""


def named_block(text: str, name: str) -> tuple[int, int]:
    pattern = rf"(?m)^[ \t]*{re.escape(name)}\s*=\s*\{{"
    match = re.search(pattern, text)
    if not match:
        raise AssertionError(f"missing {name} block")
    if len(re.findall(pattern, text)) != 1:
        raise AssertionError(f"{name} block must be unique")
    opening = text.find("{", match.start(), match.end())
    return match.start(), matching_brace(text, opening)


def replace_named_block(text: str, name: str, replacement: str) -> str:
    start, end = named_block(text, name)
    return text[:start] + replacement + text[end + 1 :]


def historical_season_block(date: str, delay: int) -> str:
    return f"""\t\tif = {{
\t\t\tlimit = {{
\t\t\t\tAND = {{
\t\t\t\t\thas_game_rule = agot_historical_seasons
\t\t\t\t\tgame_start_date = {date} # MODDED DoD
\t\t\t\t}}
\t\t\t}}
\t\t\tevery_ruler = {{
\t\t\t\ttrigger_event = season_events.008 # Start in autumn
\t\t\t}}
\t\t\tset_AGOT_season_autumn_start = yes
\t\t\ttrigger_event = {{
\t\t\t\tid = season_events.044
\t\t\t\tdays = {delay} # Continue toward winter 8131
\t\t\t}}
\t\t}}"""


def replace_historical_season_block(text: str, date: str, delay: int) -> str:
    needle = f"game_start_date = {date}"
    matches = list(re.finditer(rf"{re.escape(needle)}(?![0-9.])", text))
    if len(matches) != 1:
        raise AssertionError(f"historical season {date}: expected one source block")
    date_offset = matches[0].start()
    start = text.rfind("\t\tif = {", 0, date_offset)
    if start < 0:
        raise AssertionError(f"historical season {date}: outer if block not found")
    opening = text.find("{", start, date_offset)
    end = matching_brace(text, opening)
    return text[:start] + historical_season_block(date, delay) + text[end + 1 :]


def generate_events(source: str) -> str:
    if "game_start_date = 8129.4.1" in source:
        raise AssertionError("upstream added the 8129.4.1 historical-season start")
    text = replace_historical_season_block(source, "8129.4.2", 705)
    first = historical_season_block("8129.4.2", 705)
    text = replace_exact(
        text,
        first,
        first + "\n" + historical_season_block("8129.4.1", 705),
        label="8129.4.1 historical-season insertion",
    )
    text = replace_historical_season_block(text, "8129.4.28", 769)
    for date in ("8129.4.1", "8129.4.2", "8129.4.28"):
        needle = f"game_start_date = {date}"
        offset = text.index(needle)
        start = text.rfind("\t\tif = {", 0, offset)
        end = matching_brace(text, text.find("{", start, offset))
        block = text[start : end + 1]
        if "season_events.007" in block or "set_AGOT_season_summer_start" in block:
            raise AssertionError(f"historical season {date} still starts in summer")
        if (
            "season_events.008" not in block
            or "set_AGOT_season_autumn_start" not in block
        ):
            raise AssertionError(f"historical season {date} must start in autumn")
    return text if text.endswith("\n") else text + "\n"


def check_shader(source: str) -> None:
    """Assert the Seasons bridge retains its upstream global threshold fix."""
    skip = "static const float SKIP_VALUE = 0.001f;"
    active = list(re.finditer(rf"(?m)^[ \t]*{re.escape(skip)}[ \t]*$", source))
    if len(active) != 1:
        raise AssertionError("Seasons shader skip threshold changed")
    struct = re.search(r"(?m)^struct\s+EffectIntensities\s*\n\{", source)
    if not struct:
        raise AssertionError("missing EffectIntensities declaration")
    struct_end = matching_brace(source, source.find("{", struct.start(), struct.end()))
    if source[struct_end : struct_end + 2] != "};":
        raise AssertionError("EffectIntensities declaration is not terminated")
    pixel = source.find("PixelShader =")
    if pixel < 0 or active[0].start() <= struct_end or active[0].start() >= pixel:
        raise AssertionError("shared Seasons shader threshold is not global")
    if source.count("//static const float SKIP_VALUE = 0.001f;") != 1:
        raise AssertionError("pixel-shader-local skip threshold marker changed")


def add_group_regions(text: str, group: str, regions: tuple[str, ...]) -> str:
    group_start, group_end = named_block(text, group)
    group_text = text[group_start : group_end + 1]
    region_start, region_end = named_block(group_text, "regions")
    region_text = group_text[region_start : region_end + 1]
    for region in regions:
        if re.search(rf"(?m)^\s*{re.escape(region)}\s*$", region_text):
            raise AssertionError(f"{region} already assigned in {group}")
    additions = "\n\t\t# LoV/Seasons compatch cleanup coverage.\n" + "".join(
        f"\t\t{region}\n" for region in regions
    )
    region_text = region_text[:-1] + additions + "\t}"
    group_text = group_text[:region_start] + region_text + group_text[region_end + 1 :]
    return text[:group_start] + group_text + text[group_end + 1 :]


def replace_block_member(text: str, block_name: str, old: str, new: str) -> str:
    start, end = named_block(text, block_name)
    block = text[start : end + 1]
    block = replace_exact(block, old, new, label=f"{block_name} member")
    return text[:start] + block + text[end + 1 :]


# Landed titles merge by key across the load order, and a title has one parent,
# so the last file that nests a title decides where it sits. These are the mods
# that place every title the seasonal regions name, in load order.
TITLE_TREE_SOURCES = ("AGOT", "NOW", "LOV", "LOV_BRIDGE")
# The same tree for the profile that enables neither optional family.
CORE_TITLE_TREE_SOURCES = ("AGOT", "NOW")

# The Seasons of Valyria compatch defines `world_lov_*` regions but lists none
# of them in a seasonal group, so nothing ever rolls weather for them. Spread
# them over the ten groups here. Only that compatch defines these regions, so
# the profile that enables neither it nor Legacy of Valyria must name none of
# them: a group that lists an undefined region crashes world init.
LOV_SEASON_GROUPS: dict[str, tuple[str, ...]] = {
    "world_group_three": ("world_lov_upper_rhoyne",),
    "world_group_four": ("world_lov_middle_rhoyne",),
    "world_group_seven": (
        "world_lov_mantarys",
        "world_lov_lower_rhoyne",
        "world_lov_volantene_steppe",
    ),
    "world_group_nine": (
        "world_lov_south_ghiscar",
        "world_lov_western_sothoryos",
        "world_lov_eastern_sothoryos",
        "world_lov_marahai",
        "world_lov_asshai",
    ),
    "world_group_ten": ("world_lov_volantene_coast", "world_lov_north_ghiscar"),
}

LOV_OUTPUTS = {
    SOURCE_RELATIVES["SEASON_EVENTS"],
    SOURCE_RELATIVES["SEASON_REGIONS"],
    MAP_ICON_RELATIVE,
    IS_DIARCH_VALID_RELATIVE,
    CAN_BE_ACTIVITY_GUEST_RELATIVE,
    TRAVEL_ON_ACTIONS_RELATIVE,
    TRAVEL_OPTIONS_RELATIVE,
    TOURNAMENT_RELATIVE,
    CORONATION_RELATIVE,
    CORONATION_EVENTS_RELATIVE,
    DRAGON_HATCHING_RELATIVE,
    DRAGON_CRADLING_RELATIVE,
    DRAGON_HATCHING_EVENTS_RELATIVE,
    RUINS_EVENTS_RELATIVE,
    MDE_LOV_DRAGONPIT_OUTPUT,
    CONTEST_EVENTS_RELATIVE,
}

MEMBERSHIP_KEYS = ("empires", "kingdoms", "duchies", "counties")

# Seasonal regions name two titles a parent declares but gives no province: a
# titular duchy and a titular kingdom. They cover nothing, so they are never
# redundant and the coverage check has to expect them by name rather than treat
# an empty result as a resolution failure.
TITULAR_SEASON_TITLES = frozenset({"d_knellstone", "k_the_rills"})

# Membership entries no declared landed-titles source defines. The seasons
# bridge builds its regions from the NOW-Seasons compatch, which names titles at
# tiers the current stack does not have: NOW demoted each of these to a barony
# or a county, or never had it. CK3 resolves a region entry by title key, so an
# undefined key contributes no province and only logs at world init - dropping
# the line leaves every region covering exactly what it covered.
EXPECTED_UNDEFINED_SEASON_MEMBERS = {
    "world_westeros_the_reach_without_south_or_marches": ("d_whitehand",),
    "world_westeros_the_stormlands_sans_marches": ("d_morne",),
    "world_westeros_rest_of_dorne": ("d_the_northblood",),
    "world_tarth_and_estermont": ("d_morne",),
    "world_central_stormlands": ("d_kings_mountain",),
    "world_gods_eye_region": ("c_hoarespring", "c_droven"),
    "world_upper_reach": ("d_whitehand",),
    "world_dorne_north_coast": ("c_hall_of_the_dead",),
    "world_dorne_south_coast": ("c_sunvane",),
    "world_dornish_marches_seasons": ("d_the_vultures_gorge", "c_hillguard"),
    "world_westerlands_low": ("c_bonetree", "c_silvermere", "c_longdowns"),
    "world_upper_vale_seasons": ("c_riving",),
    "world_barrowlands_seasons": ("d_steelwater", "d_witheredheath"),
    "world_wolfswood_seasons": ("d_mullroot", "d_ironrath", "d_torrhens_square"),
    "world_whiteknife_seasons": ("c_whittarkeep", "c_seal_rock", "c_wolfs_den"),
    "world_winterfell_seasons": ("c_greyward_tower",),
    "world_lonely_hills": ("d_seals_edge",),
    "world_sheepshead_hills": ("d_sheepshead_hills", "d_wraithmarch"),
}

# The Legacy of Valyria profile builds its regions from the Seasons of Valyria
# compatch, which adds the `world_lov_*` regions the always-enabled profile's
# source does not carry, so it expects two entries more.
#
# The Legacy of Valyria bridge ships an empty
# `common/landed_titles/lv_rhoyne_titles.txt`, deferring the Rhoyne to AGOT,
# which lays the same river out as `d_ar_noy`, `d_ny_sar`, and `d_ghoyan_drohe`
# under three ruin kingdoms. The four duchies below are the Legacy of Valyria
# keys that layout has no counterpart for. Both regions keep their coverage
# through AGOT's duchies, so these lines only name titles the stack never
# defines.
EXPECTED_UNDEFINED_LOV_SEASON_MEMBERS = EXPECTED_UNDEFINED_SEASON_MEMBERS | {
    "world_lov_middle_rhoyne": ("d_the_sorrows", "d_golden_bridge", "d_dagger_lake"),
    "world_lov_upper_rhoyne": ("d_velvet_peak",),
}

# Every membership entry the prune removes, by the region that listed it. A
# kingdom already contains its duchies and a duchy its counties, so re-listing
# them makes CK3 read the same province twice and log `Region 'N' has multiple
# entries for the province 'N'` once per repeat at world init. Dropping the
# narrower entry leaves the region covering exactly the same provinces.
EXPECTED_SEASON_REGION_PRUNE = {
    "world_upper_vale_seasons": 11,
    "world_westerlands_low": 6,
    "world_barrowlands_seasons": 5,
    "world_dornish_marches_seasons": 4,
    "world_the_fingers_seasons": 4,
    "world_norvos_seasons": 3,
    "world_lonely_hills": 3,
    "world_sheepshead_hills": 3,
    "world_upper_reach": 2,
    "world_dorne_north_coast": 2,
}

_TITLE_TOKEN = re.compile(r"[ekdcb]_[A-Za-z0-9_\-']+")
_TREE_TOKEN = re.compile(r"([A-Za-z0-9_\-']+)\s*=\s*\{|\{|\}|province\s*=\s*(\d+)")


def build_title_provinces(roots: Iterable[Path]) -> dict[str, set[int]]:
    """Return the provinces each landed title covers, resolved by load order.

    Sources are resolved per relative path, the way CK3 loads them: when a later
    root ships `common/landed_titles/<name>`, only that copy is read. A parent
    that blanks an earlier parent's file therefore removes its declarations,
    rather than leaving them declared by the shadowed copy.

    Every title a source declares gets an entry, so a title that is absent from
    the result is one no parent defines at all, and one that maps to an empty
    set is declared but holds no province.
    """
    winning: dict[str, Path] = {}
    for root in roots:
        directory = root / "common/landed_titles"
        if not directory.is_dir():
            continue
        for path in directory.rglob("*.txt"):
            winning[path.relative_to(directory).as_posix()] = path

    parent: dict[str, str] = {}
    declared: set[str] = set()
    barony_province: dict[str, int] = {}
    for _, path in sorted(winning.items()):
        stack: list[str | None] = []
        text = re.sub(r"#[^\n]*", "", read_text(path))
        for match in _TREE_TOKEN.finditer(text):
            if match.group(2) is not None:
                for entry in reversed(stack):
                    if entry and entry.startswith("b_"):
                        barony_province[entry] = int(match.group(2))
                        break
                continue
            token = match.group(0)
            if token == "}":
                if stack:
                    stack.pop()
            elif token == "{":
                stack.append(None)
            elif _TITLE_TOKEN.fullmatch(match.group(1)):
                declared.add(match.group(1))
                enclosing = next((entry for entry in reversed(stack) if entry), None)
                if enclosing:
                    parent[match.group(1)] = enclosing
                stack.append(match.group(1))
            else:
                stack.append(None)
    children: dict[str, list[str]] = defaultdict(list)
    for title, holder in parent.items():
        children[holder].append(title)
    resolved: dict[str, set[int]] = {}

    def resolve(title: str, pending: frozenset[str]) -> set[int]:
        if title in resolved:
            return resolved[title]
        if title in pending:
            raise AssertionError(f"landed title {title} contains itself")
        if title.startswith("b_"):
            province = barony_province.get(title)
            covered = set() if province is None else {province}
        else:
            covered = set()
            for child in children.get(title, ()):
                covered |= resolve(child, pending | {title})
        resolved[title] = covered
        return covered

    for title in (*declared, *parent, *children):
        resolve(title, frozenset())
    return resolved


def membership_lists(block: str) -> list[tuple[str, int, int]]:
    """Return each membership list in a region block as (key, start, end)."""
    found = []
    for key in MEMBERSHIP_KEYS:
        for match in re.finditer(rf"(?m)^[ \t]*{key}\s*=\s*\{{", block):
            opening = block.find("{", match.start(), match.end())
            found.append((key, opening + 1, matching_brace(block, opening)))
    return found


def region_blocks(text: str) -> Iterator[tuple[str, int, int]]:
    """Yield each top-level region as (name, start, end-exclusive)."""
    position = 0
    for match in re.finditer(r"(?m)^([a-zA-Z_0-9]+)\s*=\s*\{", text):
        if match.start() < position:
            continue
        opening = text.find("{", match.start(), match.end())
        position = matching_brace(text, opening) + 1
        yield match.group(1), match.start(), position


def drop_undefined_members(
    text: str,
    coverage: dict[str, set[int]],
    expected: dict[str, tuple[str, ...]],
) -> str:
    """Remove membership entries naming a title no parent declares."""
    dropped: dict[str, tuple[str, ...]] = {}
    position = 0
    pieces: list[str] = []
    for region, start, end in region_blocks(text):
        block = text[start:end]
        names: list[str] = []
        for _, body_start, body_end in membership_lists(block):
            for name in re.sub(r"#.*", "", block[body_start:body_end]).split():
                if name not in coverage:
                    names.append(name)
        for name in names:
            block, count = re.subn(rf"(?m)^[ \t]*{name}[ \t]*\r?\n", "", block, count=1)
            if count != 1:
                raise AssertionError(f"{region} entry {name} is not on its own line")
        if names:
            dropped[region] = tuple(names)
        pieces.append(text[position:start])
        pieces.append(block)
        position = end
    pieces.append(text[position:])
    if dropped != expected:
        raise AssertionError(
            f"undefined seasonal-region membership changed: {dropped} is not {expected}"
        )
    return "".join(pieces)


def prune_covered_members(text: str, coverage: dict[str, set[int]]) -> str:
    """Drop membership entries a broader entry of the same region already covers.

    This is subtractive only: an entry goes only when every province it holds is
    also held by an entry that stays, so each region keeps exactly the provinces
    it had. Entries that cover nothing are always kept, which is what stops an
    unresolvable or titular name from being read as redundant.
    """
    pruned: dict[str, int] = {}
    position = 0
    pieces: list[str] = []
    for match in re.finditer(r"(?m)^([a-zA-Z_0-9]+)\s*=\s*\{", text):
        if match.start() < position:
            continue
        opening = text.find("{", match.start(), match.end())
        end = matching_brace(text, opening) + 1
        region = match.group(1)
        block = text[match.start() : end]
        entries: list[tuple[str, set[int]]] = []
        for _, body_start, body_end in membership_lists(block):
            for name in re.sub(r"#.*", "", block[body_start:body_end]).split():
                if not _TITLE_TOKEN.fullmatch(name):
                    raise AssertionError(
                        f"{region} membership entry {name!r} is not a title key"
                    )
                covers = coverage[name]
                if not covers and name not in TITULAR_SEASON_TITLES:
                    raise AssertionError(
                        f"{region} names {name}, which is declared but holds no "
                        "province; re-audit the seasonal membership"
                    )
                entries.append((name, covers))
        covered: set[int] = set()
        drops: list[str] = []
        for name, provinces in sorted(entries, key=lambda entry: -len(entry[1])):
            if provinces and provinces <= covered:
                drops.append(name)
            else:
                covered |= provinces
        for name in drops:
            block = replace_exact(
                block,
                f"\t\t{name}\n",
                "",
                expected=1,
                label=f"{region} redundant membership entry {name}",
            )
        if drops:
            pruned[region] = len(drops)
            # A region whose overlap was pure containment must come out clean.
            # Anything left is a partial overlap the prune cannot express, and
            # dropping an entry beside one would have cost real coverage.
            retained: Counter[int] = Counter()
            for name, provinces in entries:
                if name not in drops:
                    retained.update(provinces)
            repeated = sum(1 for count in retained.values() if count > 1)
            if repeated:
                raise AssertionError(
                    f"{region} still lists {repeated} province(s) twice after "
                    "the prune; its membership entries only partly overlap"
                )
            # A list the prune empties carries no members and no commented-out
            # ones either, so drop the declaration with it.
            for key, body_start, body_end in reversed(membership_lists(block)):
                body = block[body_start:body_end]
                if body.strip():
                    continue
                opening = block.rindex(key, 0, body_start)
                closing = body_end + 1
                while closing < len(block) and block[closing] in " \t":
                    closing += 1
                if closing < len(block) and block[closing] == "\n":
                    closing += 1
                start = block.rindex("\n", 0, opening) + 1
                block = block[:start] + block[closing:]
        pieces.append(text[position : match.start()])
        pieces.append(block)
        position = end
    pieces.append(text[position:])
    if pruned != EXPECTED_SEASON_REGION_PRUNE:
        raise AssertionError(
            "seasonal-region membership overlap changed: "
            f"{pruned} is not {EXPECTED_SEASON_REGION_PRUNE}"
        )
    return "".join(pieces)


def generate_regions(
    source: str,
    coverage: dict[str, set[int]],
    groups: dict[str, tuple[str, ...]] = LOV_SEASON_GROUPS,
    undefined: dict[str, tuple[str, ...]] = EXPECTED_UNDEFINED_LOV_SEASON_MEMBERS,
) -> str:
    text = replace_block_member(
        source, "world_westeros_rest_of_dorne", "\t\td_yronwood\n", "\t\td_greenbelt\n"
    )
    if "d_yronwood" in text:
        raise AssertionError("NOW d_greenbelt seasonal-region membership changed")
    if text.count("\t\tc_brittlebush\n") != 1:
        raise AssertionError("NOW Brittlebush seasonal-region membership changed")

    # `c_heapsdown` is named by two sub-regions of the same seasonal group, so
    # `world_group_one` reads its provinces twice and the seasons situation has
    # two claims on them. `world_barrowlands_seasons` keeps the county; the
    # prune below only sees one region at a time and cannot resolve this.
    text = replace_block_member(
        text, "world_whiteknife_seasons", "\t\tc_heapsdown\n", ""
    )
    if text.count("\t\tc_heapsdown\n") != 1:
        raise AssertionError("Heapsdown seasonal-region membership changed")

    text = replace_named_block(
        text,
        "world_iron_isles",
        """world_iron_isles = {
\tduchies = {
\t\td_pyke
\t\td_east_wyk
\t\td_saltcliffe
\t\td_hardstone_hills
\t\td_old_wyk
\t\td_harlaw
\t\td_orkmont
\t\td_blacktyde
\t\td_lonely_light
\t}
}""",
    )
    crossing_start, crossing_end = named_block(text, "world_crossing_flood")
    crossing = text[crossing_start : crossing_end + 1]
    if "\t\tc_ironwater\n" not in crossing or "d_ironwater" in crossing:
        raise AssertionError("Ironwater flood membership changed upstream")
    text = replace_block_member(
        text, "world_riverrun_flood", "\t\t#c_sally_dance\n", "\t\tc_sallydance\n"
    )
    rest_start, rest_end = named_block(text, "world_rest_of_essos_valyria_LOV")
    rest = text[rest_start : rest_end + 1]
    if not re.search(r"(?m)^\s*d_ruins\s*$", rest) or re.search(
        r"(?m)^\s*regions\s*=", rest
    ):
        raise AssertionError("ruins seasonal-region exclusion changed upstream")
    text = replace_named_block(
        text,
        "world_rest_of_essos_valyria_LOV",
        """world_rest_of_essos_valyria_LOV = {
\t# LoV & Seasons compatch: was duchies = { d_ruins }, which is EVERY wasteland on the map.
\t# AGOT 0.4.40 stubbed the real Essos regions, so upstream's essos_dothraki rolls were
\t# carpet-painting all ruins provinces with one season. Emptied on purpose.
}""",
    )

    for group, regions in groups.items():
        text = add_group_regions(text, group, regions)

    iron_start, iron_end = named_block(text, "world_iron_isles")
    iron = text[iron_start : iron_end + 1]
    if "empires" in iron or iron.count("\t\td_") != 9:
        raise AssertionError("Iron Islands seasonal-region narrowing failed")
    crossing_start, crossing_end = named_block(text, "world_crossing_flood")
    if "d_ironwater" in text[crossing_start : crossing_end + 1]:
        raise AssertionError("Ironwater flood region still uses a duchy token")
    river_start, river_end = named_block(text, "world_riverrun_flood")
    river = text[river_start : river_end + 1]
    if "c_sallydance" not in river or "c_sally_dance" in river:
        raise AssertionError("Sallydance flood region did not rebase to NOW")
    text = drop_undefined_members(text, coverage, undefined)
    text = prune_covered_members(text, coverage)
    return text if text.endswith("\n") else text + "\n"


def script_tokens(block: str) -> str:
    """Normalise a script block to the tokens CK3 actually parses."""
    return " ".join(
        re.sub(r"\s+", " ", line.split("#", 1)[0].strip())
        for line in block.splitlines()
        if line.split("#", 1)[0].strip()
    )


def merge_onto_agot(*, ours: str, base: str, theirs: str, label: str) -> str:
    """Three-way merge two AGOT-derived overrides of one interface file."""
    with tempfile.TemporaryDirectory(prefix="agot-full-compatch-") as directory:
        root = Path(directory)
        paths = []
        for name, text in (("ours", ours), ("base", base), ("theirs", theirs)):
            path = root / f"{name}.gui"
            path.write_text(text, encoding="utf-8", newline="\n")
            paths.append(str(path))
        completed = subprocess.run(
            ["git", "merge-file", "-p", *paths], capture_output=True, check=False
        )
    if completed.returncode not in (0, 1):
        raise AssertionError(
            f"{label}: git merge-file failed: {completed.stderr.decode().strip()}"
        )
    merged = completed.stdout.decode("utf-8")
    if "<<<<<<<" in merged or ">>>>>>>" in merged:
        raise AssertionError(f"{label}: unresolved three-way merge")
    return merged


def changed_lines(before: str, after: str) -> list[str]:
    """Return both sides of a zero-context diff without line-number noise."""
    import difflib

    return [
        line[1:]
        for line in difflib.unified_diff(
            before.splitlines(), after.splitlines(), n=0, lineterm=""
        )
        if line.startswith(("+", "-")) and not line.startswith(("+++", "---"))
    ]


def require_delta_preserved(
    *, base: str, parent: str, merged: str, ours: str, label: str
) -> None:
    """Assert the merge applies exactly the other parent's textual delta."""
    delta = changed_lines(base, parent)
    if not delta:
        raise AssertionError(f"{label}: parent must differ from AGOT")
    if delta != changed_lines(ours, merged):
        raise AssertionError(f"{label}: merge did not reproduce the parent's delta")


def generate_hud(agot: str, iron_and_salt: str, dfp: str, mde_hud: str) -> str:
    """Keep the naval and kraken HUD together with the family portrait stack."""
    label = "hud.gui"
    merged = merge_onto_agot(ours=iron_and_salt, base=agot, theirs=dfp, label=label)
    require_delta_preserved(
        base=agot, parent=dfp, merged=merged, ours=iron_and_salt, label=label
    )
    for needle in ("bottom_left_dragon_portrait = {}", "type bottom_left_portrait"):
        if needle not in merged:
            raise AssertionError(f"{label}: merged output lost {needle!r}")
    if "type bottom_left_dragon_portrait" in merged:
        raise AssertionError(
            f"{label}: hud.gui must not declare bottom_left_dragon_portrait inline"
        )
    for needle in (
        "type bottom_left_dragon_portrait = container",
        "mde_dragon_portrait_size_baby",
        "mde_dragon_portrait_size_normal",
        "mde_dragon_portrait_size_giant",
    ):
        if needle not in mde_hud:
            raise AssertionError(f"mde_hud.gui: source lost {needle!r}")
    if merged.count("naval") < 1000:
        raise AssertionError(
            f"{label}: Iron and Salt's naval interface did not survive"
        )
    return merged


def generate_map_icon_layer(agot: str, iron_and_salt: str, lov: str) -> str:
    """Keep the kraken map icon without adding LoV's absent datacontext."""
    label = "map_icon_layer.gui"
    # LoV spells the human-portrait gate the same way AGOT does. Its only merge
    # delta is the absent find-elder datacontext; the shared template is the
    # equivalent active form.
    if "using = visible_if_not_dragon" in lov:
        raise AssertionError(f"{label}: LoV moved the dragon gate to the template")
    merged = merge_onto_agot(ours=iron_and_salt, base=agot, theirs=lov, label=label)
    require_delta_preserved(
        base=agot, parent=lov, merged=merged, ours=iron_and_salt, label=label
    )
    for needle in ("agot_kraken_portrait_map_icon = {}", "kraken_character_window"):
        if needle not in merged:
            raise AssertionError(f"{label}: merged output lost {needle!r}")
    if FIND_ELDER_DATACONTEXT in merged:
        raise AssertionError(f"{label}: LoV's removed find_elder datacontext came back")
    return merged


def scripted_trigger(text: str, name: str) -> str:
    start, end = definition_span(text, name)
    return text[start:end]


def generate_is_human(agot: str, iron_and_salt: str, great_councils: str) -> str:
    """Combine AGOT, Iron and Salt, and Great Councils under one last writer."""
    label = "is_human"
    parent = scripted_trigger(agot, "is_human")
    for source, clause, owner in (
        (iron_and_salt, KRAKEN_CLAUSE, "Iron and Salt"),
        (great_councils, GREAT_COUNCILS_CLAUSE, "Great Councils"),
    ):
        derived = scripted_trigger(source, "is_human")
        if clause not in derived:
            raise AssertionError(f"{label}: {owner} must add {clause!r}")
        if script_tokens(derived.replace(clause, "", 1)) != script_tokens(parent):
            raise AssertionError(
                f"{label}: {owner}'s definition must equal AGOT plus one clause"
            )
    body = parent.replace(
        "NOT = { has_trait = dragon }",
        f"NOT = {{ has_trait = dragon }}\n\t{KRAKEN_CLAUSE}",
        1,
    )
    closing = body.rfind("}")
    body = f"{body[:closing]}\t{GREAT_COUNCILS_CLAUSE}\n{body[closing:]}"
    return (
        "# The AGOT playset's single last writer for `is_human`.\n"
        "#\n"
        "# AGOT excludes dragons and dummy characters, Iron and Salt excludes\n"
        "# krakens, and Great Councils excludes flagged characters.  CK3 resolves\n"
        "# scripted triggers by filename across the merged file system, not by mod\n"
        "# position, so only one of those three files can win and the other two\n"
        "# clauses are lost.  This name sorts after all of them; re-audit whenever\n"
        "# a later-sorting writer of `is_human` joins the playset.\n"
        f"{body}\n"
    )


def indented_block(text: str, name: str, *, label: str) -> str:
    """Return one nested `name = { ... }` block from inside a definition body."""
    matches = list(re.finditer(rf"(?m)^\t{re.escape(name)}\s*=\s*\{{", text))
    if len(matches) != 1:
        raise AssertionError(
            f"{label}: expected one nested {name} block, found {len(matches)}"
        )
    start = matches[0].start()
    end = matching_brace(text, text.find("{", start)) + 1
    return text[start:end]


def indented_blocks(text: str, name: str) -> list[str]:
    """Return every top-level nested block with `name` from one definition."""
    blocks = []
    for match in re.finditer(rf"(?m)^\t{re.escape(name)}\s*=\s*\{{", text):
        start = match.start()
        end = matching_brace(text, text.find("{", start)) + 1
        blocks.append(text[start:end])
    return blocks


def block_after_marker(text: str, marker: str, *, label: str) -> str:
    """Return the first script block after a unique comment or marker line."""
    if text.count(marker) != 1:
        raise AssertionError(
            f"{label}: expected one {marker!r} marker, found {text.count(marker)}"
        )
    marker_at = text.index(marker) + len(marker)
    match = re.search(r"(?m)^[ \t]*if\s*=\s*\{", text[marker_at:])
    if match is None:
        raise AssertionError(f"{label}: no if block follows {marker!r}")
    start = marker_at + match.start()
    end = matching_brace(text, text.find("{", start)) + 1
    return text[start:end]


def generate_core_travel_on_actions(travelers: str) -> str:
    """Restate the Travelers AGOT compatch so it outranks later parents.

    Without the LoV bridge, the Travelers AGOT compatch is already the complete
    AGOT + Travelers resolution and nothing here has to be merged. It still has
    to be restated, because More Dragon Eggs ships its own whole-file copy of
    AGOT's version further down the load order and would otherwise drop every
    Travelers wrapper and guard below.
    """
    label = "travel_on_actions.txt"
    scope_comments = travelers.count(TRAVELERS_SCOPE_COMMENT)
    if scope_comments != 8:
        raise AssertionError(
            f"{label}: expected eight Travelers scope-fix comments, found "
            f"{scope_comments}"
        )
    restated = travelers.replace(TRAVELERS_SCOPE_COMMENT, TRAVELERS_SCOPE_NORMALIZED)
    for name in TRAVELERS_WRAPPED_ON_ACTIONS:
        wrapper = f"{name} = {{\n\ton_actions = {{\n\t\tvanilla_{name}\n\t}}"
        if restated.count(wrapper) != 1:
            raise AssertionError(f"{label}: Travelers wrapper for {name} changed")
    for needle in TRAVELERS_ON_ACTION_MARKERS:
        if not restated.count(needle):
            raise AssertionError(f"{label}: Travelers marker {needle!r} changed")
    return restated


def generate_travel_on_actions(agot: str, travelers: str, lov: str) -> str:
    """Keep Travelers' wrappers and guards together with LoV's safe scopes."""
    label = "travel_on_actions.txt"
    scope_comments = travelers.count(TRAVELERS_SCOPE_COMMENT)
    if scope_comments != 8:
        raise AssertionError(
            f"{label}: expected eight Travelers scope-fix comments, found "
            f"{scope_comments}"
        )
    travelers = travelers.replace(TRAVELERS_SCOPE_COMMENT, TRAVELERS_SCOPE_NORMALIZED)

    # Both parents make the same seven current-travel-plan scopes optional but
    # spell the line differently.  Travelers also replaces the eighth, the
    # caravan-master task, with a character modifier.  Give LoV that complete
    # replacement before the three-way merge so identical safety edits do not
    # become textual conflicts and the superseded travel-plan modifier is not
    # revived.
    marker = "# Caravan Master Task"
    agot_task = block_after_marker(agot, marker, label=f"{label} AGOT")
    travelers_task = block_after_marker(travelers, marker, label=f"{label} Travelers")
    lov_task = block_after_marker(lov, marker, label=f"{label} LoV")
    if "add_travel_plan_modifier = prepare_travels_modifier" not in agot_task:
        raise AssertionError(f"{label}: AGOT caravan-master task changed")
    if "current_travel_plan ?=" not in lov_task:
        raise AssertionError(f"{label}: LoV caravan-master scope guard changed")
    if (
        "add_character_modifier = unop_prepare_travels_character_modifier"
        not in travelers_task
        or "add_travel_plan_modifier = prepare_travels_modifier"
        in script_tokens(travelers_task)
    ):
        raise AssertionError(f"{label}: Travelers caravan-master repair changed")
    aligned_lov = replace_exact(
        lov,
        lov_task,
        travelers_task,
        label=f"{label} shared caravan-master resolution",
    )

    merged = merge_onto_agot(ours=travelers, base=agot, theirs=aligned_lov, label=label)
    if top_level_definitions(merged) != top_level_definitions(travelers):
        raise AssertionError(f"{label}: Travelers' on-action definitions changed")
    for name in TRAVELERS_WRAPPED_ON_ACTIONS:
        wrapper = f"{name} = {{\n\ton_actions = {{\n\t\tvanilla_{name}\n\t}}"
        if merged.count(wrapper) != 1:
            raise AssertionError(f"{label}: Travelers wrapper for {name} changed")
    for needle in TRAVELERS_ON_ACTION_MARKERS:
        if not travelers.count(needle) or merged.count(needle) != travelers.count(
            needle
        ):
            raise AssertionError(f"{label}: Travelers marker {needle!r} changed")
    for needle in LOV_TRAVEL_MARKERS:
        if not lov.count(needle) or merged.count(needle) != lov.count(needle):
            raise AssertionError(f"{label}: LoV marker {needle!r} changed")
    for needle in ("current_travel_plan ?= {", "root.current_travel_plan ?= {"):
        if merged.count(needle) < max(travelers.count(needle), lov.count(needle)):
            raise AssertionError(f"{label}: optional scope {needle!r} was lost")
    return merged


def generate_travel_options(agot: str, travelers: str, lov: str) -> str:
    """Add Travelers' availability checks to LoV's guarded mercenary option."""
    label = "travel_options.txt"
    option = "hire_experienced_mercenaries_option"
    agot_option = scripted_trigger(agot, option)
    travelers_option = scripted_trigger(travelers, option)
    lov_option = scripted_trigger(lov, option)

    travelers_base = replace_exact(
        travelers_option,
        "\t\tis_imprisoned = no # Travelers\n",
        "",
        label=f"{label} Travelers imprisonment delta",
    )
    travelers_base = replace_regex(
        travelers_base,
        r"(?m)^[ \t]*is_available_at_peace_ai_adult = yes # Travelers\n",
        "",
        f"{label} Travelers leader availability delta",
        expected=2,
    )
    if script_tokens(travelers_base) != script_tokens(agot_option):
        raise AssertionError(
            f"{label}: Travelers' mercenary option must equal AGOT plus its "
            "three availability checks"
        )

    combined = replace_exact(
        lov_option,
        "\t\tis_ruler = yes\n",
        "\t\tis_ruler = yes\n\t\tis_imprisoned = no # Travelers\n",
        label=f"{label} imprisoned mercenary option",
    )
    combined = replace_regex(
        combined,
        r"(?m)^([ \t]*)mercenary_company_leader = \{\n(?=[ \t]*is_travelling = no$)",
        lambda match: (
            match.group(0)
            + match.group(1)
            + "\t"
            + TRAVELERS_OPTION_AVAILABILITY
            + "\n"
        ),
        f"{label} available mercenary leaders",
        expected=2,
    )
    if combined.count(TRAVELERS_OPTION_AVAILABILITY) != 2:
        raise AssertionError(f"{label}: Travelers mercenary guards changed")
    for needle in (
        "limit = { mercenary_company_leader ?= { always = yes } }",
        "limit = { exists = scope:mercenary_leader }",
    ):
        if combined.count(needle) != lov_option.count(needle) or not lov_option.count(
            needle
        ):
            raise AssertionError(f"{label}: LoV mercenary guard {needle!r} changed")

    merged = replace_exact(
        travelers,
        travelers_option,
        combined,
        label=f"{label} merged mercenary option",
    )
    for needle in (
        "is_imprisoned = no # Travelers",
        TRAVELERS_OPTION_AVAILABILITY,
        "limit = { mercenary_company_leader ?= { always = yes } }",
        "limit = { exists = scope:mercenary_leader }",
    ):
        if needle not in merged:
            raise AssertionError(f"{label}: merged output lost {needle!r}")
    return merged


def generate_agot_travel_options(agot: str, travelers: str) -> str:
    """Keep AGOT's sailing exclusion while adding Travelers' prison guard."""
    label = "agot_travel_options.txt"
    option = "dragon_flight_option"
    agot_option = scripted_trigger(agot, option)
    travelers_option = scripted_trigger(travelers, option)
    agot_shown = indented_block(agot_option, "is_shown", label=label)
    travelers_shown = indented_block(
        travelers_option, "is_shown", label=f"{label} Travelers"
    )
    if (
        "activity_agot_sailing" not in agot_shown
        or "activity_agot_sailing" in travelers_shown
    ):
        raise AssertionError(
            f"{label}: expected stale Travelers sailing override changed"
        )
    if travelers_shown.count("is_imprisoned = no # Travelers") != 1:
        raise AssertionError(f"{label}: Travelers imprisonment guard changed")
    if script_tokens(agot_option.replace(agot_shown, "", 1)) != script_tokens(
        travelers_option.replace(travelers_shown, "", 1)
    ):
        raise AssertionError(f"{label}: Travelers changes more than is_shown")

    merged_shown = replace_exact(
        agot_shown,
        "\t\thas_trait = dragonrider\n",
        "\t\thas_trait = dragonrider\n\t\tis_imprisoned = no # Travelers\n",
        label=f"{label} imprisonment guard",
    )
    merged_option = replace_exact(
        agot_option, agot_shown, merged_shown, label=f"{label} is_shown merge"
    )
    merged = replace_exact(
        agot, agot_option, merged_option, label=f"{label} dragon flight option"
    )
    if merged.count("activity_agot_sailing") != agot.count("activity_agot_sailing"):
        raise AssertionError(f"{label}: AGOT sailing exclusion was lost")
    return merged


def generate_can_be_activity_guest(
    agot: str, lov: str, long_night: str, living_westeros: str
) -> str:
    """Combine every playset extension of the activity-guest rule."""
    label = "can_be_activity_guest"
    parent = scripted_trigger(agot, label)
    guarded = scripted_trigger(lov, label)
    long_night_rule = scripted_trigger(long_night, label)
    living_rule = scripted_trigger(living_westeros, label)

    dead_clause = "\tln_is_one_of_them_trigger = no\n"
    without_dead = replace_exact(
        long_night_rule,
        dead_clause,
        "",
        label=f"{label} Long Night dead-character clause",
    )
    parent_with_host_guard = replace_exact(
        parent,
        "\t\t\tscope:host = {\n\t\t\t\thas_character_flag = exiled_from_iron_throne\n",
        "\t\t\tscope:host ?= {\n\t\t\t\thas_character_flag = exiled_from_iron_throne\n",
        label=f"{label} Long Night host guard",
    )
    if script_tokens(without_dead) != script_tokens(parent_with_host_guard):
        raise AssertionError(
            f"{label}: Long Night must equal AGOT plus its two guarded changes"
        )

    living_trigger_ifs = indented_blocks(living_rule, "trigger_if")
    if len(living_trigger_ifs) != 5:
        raise AssertionError(
            f"{label}: expected five Living Westeros trigger_if blocks, found "
            f"{len(living_trigger_ifs)}"
        )
    additions = living_trigger_ifs[-2:]
    living_base = living_rule
    for addition in additions:
        living_base = replace_exact(
            living_base,
            addition,
            "",
            label=f"{label} Living Westeros extension",
        )
    if script_tokens(living_base) != script_tokens(parent):
        raise AssertionError(
            f"{label}: Living Westeros must equal AGOT plus two guest-right clauses"
        )
    extension = "\n".join(additions)
    for needle in LIVING_WESTEROS_GUEST_MARKERS:
        if needle not in extension:
            raise AssertionError(f"{label}: Living Westeros marker {needle!r} changed")

    closing = guarded.rfind("}")
    if closing < 0:
        raise AssertionError(f"{label}: LoV guarded definition lost its closing brace")
    body = (
        guarded[: guarded.find("\n") + 1]
        + dead_clause
        + guarded[guarded.find("\n") + 1 : closing].rstrip()
        + "\n"
        + extension
        + "\n"
        + guarded[closing:]
    )
    for needle in (
        "scope:host.involved_activity ?= {",
        "scope:host ?= {",
        "ln_is_one_of_them_trigger = no",
        *LIVING_WESTEROS_GUEST_MARKERS,
    ):
        if needle not in body:
            raise AssertionError(f"{label}: merged rule lost {needle!r}")
    return (
        "# The AGOT playset's single last writer for `can_be_activity_guest`.\n"
        "#\n"
        "# The Legacy of Valyria bridge guards optional activity and host scopes,\n"
        "# the Long Night excludes dead characters, and A Living Westeros enforces\n"
        "# denied houses and guest-right breaker restrictions. Scripted-rule keys\n"
        "# resolve by filename parse order, so this later-sorting file keeps all\n"
        "# three extensions effective. Re-audit when another definition joins the\n"
        "# playset or any parent changes this rule.\n"
        f"{body}\n"
    )


def generate_is_diarch_valid(agot: str, lov: str, long_night: str) -> str:
    """Combine the Long Night's diarch clause with the LoV bridge's null guard."""
    label = "is_diarch_valid"
    parent = scripted_trigger(agot, label)
    if script_tokens(parent) != f"{label} = {{ {label}_trigger = yes }}":
        raise AssertionError(
            f"{label}: AGOT must define the rule as a bare {label}_trigger call"
        )

    guarded = scripted_trigger(lov, label)
    if script_tokens(guarded) != (
        f"{label} = {{ {LOV_DIARCH_GUARD} {{ {label}_trigger = yes }} }}"
    ):
        raise AssertionError(
            f"{label}: the LoV bridge must wrap AGOT's call in exactly its "
            f"{LOV_DIARCH_GUARD!r} guard"
        )

    extended = scripted_trigger(long_night, label)
    clause = indented_block(extended, "trigger_if", label=label)
    if "government_is_nw" not in clause:
        raise AssertionError(
            f"{label}: the Long Night's added clause must test the "
            "Night's Watch government flag"
        )
    if script_tokens(extended.replace(clause, "", 1)) != script_tokens(parent):
        raise AssertionError(
            f"{label}: the Long Night's definition must equal AGOT plus one "
            "trigger_if clause"
        )

    nested = "\n".join(f"\t{line}" if line else line for line in clause.splitlines())
    closing = guarded.rfind("\n\t}")
    if closing < 0:
        raise AssertionError(
            f"{label}: the LoV bridge's guarded branch lost its indent"
        )
    body = f"{guarded[:closing]}\n{nested}\n\t}}\n}}"
    return (
        "# The AGOT playset's single last writer for `is_diarch_valid`.\n"
        "#\n"
        "# The Legacy of Valyria bridge guards AGOT's call against a missing\n"
        "# character, and AGOT: The Long Night & Azor Ahai adds the clause that\n"
        "# keeps a sworn brother of the Night's Watch from serving as diarch\n"
        "# outside the Watch's own chain of command.  Only one definition of a\n"
        "# rule key survives, and the winner is the file parsed last: across the\n"
        "# merged file system CK3 walks every top-level file in the directory in\n"
        "# name order, then its subdirectories, without regard to mod position.\n"
        "# The Long Night's `zz_ln_diarch_rules.txt` therefore wins and the\n"
        "# bridge's guard is lost.  This name sorts after both, and no mod in the\n"
        "# playset puts a rule file in a `common/scripted_rules/` subdirectory,\n"
        "# which would parse later still.  Re-audit when either stops holding.\n"
        "#\n"
        "# `is_diarch_able` needs no entry here: only the bridge and AGOT define\n"
        "# it, both in `00_rules.txt`, so load order already keeps the guard.\n"
        f"{body}\n"
    )


def mfa_timing_delta(text: str) -> str:
    """Return Much Faster Activities' file with only its timing edits left."""
    for label, vanilla, agot in MFA_VANILLA_REGRESSIONS:
        text = replace_exact(text, vanilla, agot, label=f"MFA {label}")
    return text


def generate_wedding(agot: str, living_westeros: str, mfa: str) -> str:
    """Run weddings at MFA's pace with Living Westeros' AGOT backgrounds."""
    label = "wedding.txt"
    trimmed = replace_exact(
        mfa,
        MFA_WEDDING_FARMLANDS,
        AGOT_WEDDING_FARMLANDS,
        label=f"{label} MFA farmlands regression",
        expected=2,
    )
    merged = merge_onto_agot(
        ours=living_westeros, base=agot, theirs=trimmed, label=label
    )
    require_delta_preserved(
        base=agot,
        parent=trimmed,
        merged=merged,
        ours=living_westeros,
        label=label,
    )
    for needle in (
        "MFA_wedding_guest_arrival_delay_days",
        "MFA_option_wait_time",
        "MFA_wedding_1_relay",
        "MFA_wedding_2_relay",
        "MFA_wedding_3_relay",
        "MFA_wedding_pulse_relay",
    ):
        if needle not in merged:
            raise AssertionError(f"{label}: MFA marker {needle!r} changed")
    for needle in (
        "wedding_rites_weirwood.dds",
        "fp1_beached_longship_no_longship.dds",
        "wedding_rites_sept.dds",
    ):
        if merged.count(needle) != living_westeros.count(
            needle
        ) or not living_westeros.count(needle):
            raise AssertionError(
                f"{label}: Living Westeros background {needle!r} changed"
            )
    if merged.count("agot_is_farmlands_terrain = yes") != agot.count(
        "agot_is_farmlands_terrain = yes"
    ):
        raise AssertionError(f"{label}: AGOT farmlands abstraction was lost")
    return merged


def generate_tournament(agot: str, lov: str, mfa: str) -> str:
    """Run tournaments at MFA's pace on AGOT's map and cultures."""
    label = "tournament.txt"
    trimmed = mfa_timing_delta(mfa)
    merged = merge_onto_agot(ours=lov, base=agot, theirs=trimmed, label=label)
    require_delta_preserved(
        base=agot, parent=trimmed, merged=merged, ours=lov, label=label
    )
    for needle in ("MFA_tournament_cooldown", "agot_is_jungle_terrain = yes"):
        if needle not in merged:
            raise AssertionError(f"{label}: merged output lost {needle!r}")
    return merged


def guard_holy_site_holders(text: str, *, label: str) -> str:
    """Keep coronation holy-site tests from resolving through an unheld barony.

    CK3 discards the enclosing clause when `barony.holder` finds no character,
    so a restored or ruined holy site silently makes the location unusable
    rather than merely unqualified.
    """
    return replace_regex(
        text,
        r"(?m)^([ \t]*)barony\.holder = \{",
        lambda match: (
            f"{match.group(1)}{HOLY_SITE_HOLDER_GUARD}"
            f"{match.group(1)}barony.holder = {{"
        ),
        f"{label} holy-site holder guard",
        expected=5,
    )


def generate_coronation(agot: str, lov: str, mfa: str) -> str:
    """Run coronations at MFA's pace without failing on an unheld holy site."""
    label = "coronation.txt"
    merged = merge_onto_agot(ours=lov, base=agot, theirs=mfa, label=label)
    require_delta_preserved(base=agot, parent=mfa, merged=merged, ours=lov, label=label)
    return guard_holy_site_holders(merged, label=label)


def generate_coronation_events(agot: str, lov: str, mfa: str) -> str:
    """Run the coronation chain at MFA's pace without a stale chaplain scope."""
    label = "coronation_events.txt"
    merged = merge_onto_agot(ours=lov, base=agot, theirs=mfa, label=label)
    require_delta_preserved(base=agot, parent=mfa, merged=merged, ours=lov, label=label)
    # The court chaplain is summoned outside the effect that established the
    # activity, so both the councillor and the scopes it is moved into have to
    # be tested before the move rather than assumed. The LoV bridge already
    # spells it that way, so this only pins the guard the merge must keep.
    if CHAPLAIN_SUMMON_GUARD not in merged:
        raise AssertionError(f"{label}: the guarded court chaplain summon is gone")
    if (
        "\t\t\t\t\tcp:councillor_court_chaplain = {\n"
        "\t\t\t\t\t\tset_location = root.location\n"
    ) in merged:
        raise AssertionError(f"{label}: the court chaplain summon lost its guard")
    return merged


def generate_mde_lov_parent_merge(agot: str, mde: str, lov: str, *, label: str) -> str:
    """Merge current MDE and the current LoV bridge from their shared AGOT base."""
    merged = merge_onto_agot(ours=mde, base=agot, theirs=lov, label=label)
    require_delta_preserved(base=agot, parent=lov, merged=merged, ours=mde, label=label)
    require_delta_preserved(
        base=agot, parent=mde, merged=merged, ours=lov, label=f"{label} MDE delta"
    )
    return merged


def generate_dragon_hatching(agot: str, mde: str, lov: str, mfa: str) -> str:
    """Run hatching ceremonies at MFA's pace, sparing canon-protected hosts."""
    label = "agot_dragon_hatching.txt"
    mde_lov = generate_mde_lov_parent_merge(agot, mde, lov, label=label)
    merged = merge_onto_agot(ours=mde_lov, base=agot, theirs=mfa, label=label)
    require_delta_preserved(
        base=agot, parent=mfa, merged=merged, ours=mde_lov, label=label
    )
    # A hatching death is an accident, so it is one of the deaths AGOT: Canon
    # Continuity withholds.  Both activity variants kill the host the same way.
    return replace_exact(
        merged,
        DRAGON_HATCHING_DEATH_LIMIT,
        DRAGON_HATCHING_DEATH_LIMIT + CANON_DEATH_GUARD,
        f"{label} canon-continuity guard",
        expected=2,
    )


def generate_ep3_scripted_effects(agot: str, mde: str, seasons: str) -> str:
    """Keep More Dragon Eggs' landing hooks with Seasons' weather logic."""
    label = "07_dlc_ep3_scripted_effects.txt"
    merged = merge_onto_agot(ours=seasons, base=agot, theirs=mde, label=label)
    require_delta_preserved(
        base=agot, parent=mde, merged=merged, ours=seasons, label=label
    )
    require_delta_preserved(
        base=agot,
        parent=seasons,
        merged=merged,
        ours=mde,
        label=f"{label} Seasons delta",
    )
    if "more_dragon_eggs_events.0013" in merged:
        raise AssertionError(
            f"{label}: undefined More Dragon Eggs event .0013 is present"
        )
    for modifier in (
        "winter_north_modifier",
        "winter_normal_modifier_1",
        "winter_harsh_modifier",
        "winter_cold_modifier",
        "winter_light_modifier",
    ):
        if merged.count(f"has_province_modifier = {modifier}") != 2:
            raise AssertionError(
                f"{label}: Seasons weather modifier {modifier} changed"
            )
    return merged


def generate_mde_lov_cradling(agot: str, mde: str, lov: str) -> str:
    merged = generate_mde_lov_parent_merge(
        agot, mde, lov, label="agot_dragon_cradling_on_action.txt"
    )
    for needle in (
        "mde_cradle_hatch_likelihood_factor",
        "mde_pit_hatch_likelihood_factor",
        "geographical_region = world_valyria",
    ):
        if needle not in merged:
            raise AssertionError(f"dragon cradling merge lost {needle!r}")
    return merged


def generate_mde_lov_hatching_events(agot: str, mde: str, lov: str) -> str:
    merged = generate_mde_lov_parent_merge(
        agot, mde, lov, label="agot_dragon_hatching_activity_events.txt"
    )
    for needle in (
        "lv_agot_dragon_hatching.0014.opt.e_volcano",
        "valyria_volcano_05",
    ):
        if needle not in merged:
            raise AssertionError(f"dragon hatching event merge lost {needle!r}")
    return merged


def add_lov_ruins_delta(text: str) -> str:
    """Apply the LoV bridge's six semantic additions to the current ruins file."""
    text = replace_exact(
        text,
        "\t\t\tbarony = { set_coa = holder.house }\n",
        "\t\t\tbarony = { set_coa = holder.house }\n"
        "\t\t\tlv_agot_ruin_remember_developed_mines_effect = yes\n",
        label="LoV remember developed ruin mines",
    )
    text = replace_exact(
        text,
        "\t\t\t\thas_game_rule = agot_hv_conversion_offshoots\n",
        "\t\t\t\thas_game_rule = agot_hv_conversion_offshoots\n"
        "\t\t\t\tNOT = { scope:completed_ruin = { "
        "lv_agot_hv_conversion_exempt_province_trigger = yes } }\n",
        expected=2,
        label="LoV high-Valyrian ruin conversion exemptions",
    )
    for building in ("castle_02", "city_02", "temple_02", "tribe_02"):
        text = replace_exact(
            text,
            f"\t\t\tadd_building = {building}\n",
            f"\t\t\tadd_building = {building}\n"
            "\t\t\tlv_agot_ruin_restore_developed_mines_effect = yes\n",
            label=f"LoV restore developed mines after {building}",
        )
    return text


def generate_mde_lov_ruins(agot: str, mde: str, lov: str) -> str:
    expected_lov = add_lov_ruins_delta(agot)
    if script_tokens(expected_lov) != script_tokens(lov):
        raise AssertionError(
            "agot_ruins_events.txt: LoV bridge must equal AGOT plus six pinned additions"
        )
    merged = add_lov_ruins_delta(mde)
    for needle, expected in (
        ("lv_agot_ruin_remember_developed_mines_effect", 1),
        ("lv_agot_hv_conversion_exempt_province_trigger", 2),
        ("lv_agot_ruin_restore_developed_mines_effect", 4),
        ("mde_start_egg_source_effect", 2),
    ):
        if merged.count(needle) != expected:
            raise AssertionError(
                f"agot_ruins_events.txt: expected {expected} {needle!r} markers"
            )
    return merged


def generate_mde_lov_dragonpit_effects(agot: str, mde: str, lov: str) -> str:
    """Retain MDE's landless branch and LoV's dragonpit building abstraction."""
    status = block_of(mde, "agot_change_dragonpit_status")
    ai_status = block_of(mde, "agot_change_dragonpit_status_ai")
    if script_tokens(ai_status) != script_tokens(
        block_of(agot, "agot_change_dragonpit_status_ai")
    ):
        raise AssertionError("MDE AI dragonpit status must match AGOT")
    for name in ("agot_change_dragonpit_status", "agot_change_dragonpit_status_ai"):
        lov_block = block_of(lov, name)
        for marker in ("valyria_volcano_01", "procrazion_01", "last_dragon_tower_01"):
            if marker not in lov_block:
                raise AssertionError(f"LoV {name} lost {marker!r}")

    insertion = (
        "\t\t\t\t\t\t\tany_county_province = { "
        "lv_has_dragon_pit_building = yes } # Legacy of Valyria\n"
    )
    anchor = "\t\t\t\t\t\t}\n\t\t\t\t\t\thas_variable = has_dragonkeeper_order\n"
    status = replace_exact(
        status,
        anchor,
        insertion + anchor,
        label="player dragonpit LoV building detection",
    )
    ai_anchor = "\t\t\t\t}\n\t\t\t\thas_variable = has_dragonkeeper_order\n"
    ai_insertion = (
        "\t\t\t\t\tany_county_province = { "
        "lv_has_dragon_pit_building = yes } # Legacy of Valyria\n"
    )
    ai_status = replace_exact(
        ai_status,
        ai_anchor,
        ai_insertion + ai_anchor,
        label="AI dragonpit LoV building detection",
    )
    merged = (
        "# Final owner of the two dragonpit status effects contested by MDE and LoV.\n"
        f"{status}\n\n{ai_status}\n"
    )
    if merged.count("lv_has_dragon_pit_building = yes") != 2:
        raise AssertionError("dragonpit merge lost LoV detection")
    if merged.count("is_landless_adventurer = yes") != 1:
        raise AssertionError("dragonpit merge lost MDE landless handling")
    if "more_dragon_eggs_events.0008" in merged:
        raise AssertionError("dragonpit merge calls undefined MDE mover event .0008")
    return merged


def assert_mde_parent_invariants(agot: Path, mde: Path) -> None:
    """Pin MDE behavior that remains parent-owned in the effective playset."""
    gene_values = read_text(
        agot / "common/script_values/00_agot_dragon_gene_values.txt"
    )
    for name, variable in (
        ("gene_dragon_fire_color_template_svalue", "gene_dragon_fire_color_template"),
        ("gene_dragon_fire_smoke_template_svalue", "gene_dragon_fire_smoke_template"),
    ):
        block = block_of(gene_values, name)
        for marker in (
            f"is_alive = yes has_variable = {variable}",
            "agot_has_dragon_storage_system_global_list = yes",
            "exists = scope:dragon_var_story_val",
        ):
            if marker not in block:
                raise AssertionError(
                    f"AGOT {name} must contain storage guard {marker!r}"
                )

    event = block_of(
        read_text(mde / "events/dlc/ep3/ep3_laamp_events.txt"), "ep3_laamps.0030"
    )
    if "trigger = { exists = scope:laamp_inheritor }" not in event:
        raise AssertionError("MDE voluntary-adventurer event trigger changed")
    if "can_children_be_landless_" in event:
        raise AssertionError(
            "MDE voluntary-adventurer event contains the decision-only rule gate"
        )

    portraits = mde / "gui/shared/mde_portraits.gui"
    if portraits.exists():
        text = read_text(portraits)
        if (
            "IsCharacterFakeDead" in text
            or "agot_fake_death_portrait_status_icons_small" in text
        ):
            raise AssertionError(
                "MDE portrait source references unavailable fake-death GUI symbols"
            )


def generate_contest_events(
    agot: str, lov: str, mfa: str, cafg: str, vanilla: str
) -> str:
    """Run tournament contests with LoV's guards, MFA's pace, and CaFG's faiths.

    Two merges over two different ancestors, because the parents are two
    generations apart: LoV and MFA both edit AGOT's file, while CaFG edits
    vanilla's and never saw AGOT at all.
    """
    label = "contest_events.txt"
    merged = merge_onto_agot(ours=lov, base=agot, theirs=mfa, label=label)
    require_delta_preserved(base=agot, parent=mfa, merged=merged, ours=lov, label=label)
    merged = merge_onto_agot(
        ours=cafg, base=vanilla, theirs=merged, label=f"{label} (CaFG)"
    )
    calls = len(CAFG_CALL.findall(merged))
    markers = len(AGOT_MARKER.findall(merged))
    if (calls, markers) != (CONTEST_EVENTS_CAFG_CALLS, CONTEST_EVENTS_AGOT_MARKERS):
        raise AssertionError(
            f"{label}: expected {CONTEST_EVENTS_CAFG_CALLS} CaFG call(s) and "
            f"{CONTEST_EVENTS_AGOT_MARKERS} AGOT marker(s), found {calls} and "
            f"{markers}"
        )
    return merged


def generate_core_can_be_activity_guest(
    agot: str, long_night: str, living_westeros: str
) -> str:
    """Combine the two non-LoV extensions of AGOT's activity-guest rule."""
    label = "can_be_activity_guest"
    parent = scripted_trigger(agot, label)
    extended = scripted_trigger(long_night, label)
    living = scripted_trigger(living_westeros, label)
    additions = indented_blocks(living, "trigger_if")[-2:]
    if len(additions) != 2:
        raise AssertionError(f"{label}: Living Westeros guest-right clauses changed")
    closing = extended.rfind("}")
    body = extended[:closing].rstrip() + "\n" + "\n".join(additions) + "\n}"
    for needle in ("ln_is_one_of_them_trigger = no", *LIVING_WESTEROS_GUEST_MARKERS):
        if needle not in body:
            raise AssertionError(f"{label}: core merge lost {needle!r}")
    if script_tokens(parent) == script_tokens(body):
        raise AssertionError(f"{label}: core merge has no parent delta")
    return "# Core AGOT playset activity-guest rule.\n" + body + "\n"


def generate_core_dragon_hatching(agot: str, mde: str, mfa: str) -> str:
    """Merge the non-LoV More Dragon Eggs activity with MFA and canon guards."""
    label = "agot_dragon_hatching.txt"
    merged = merge_onto_agot(ours=mde, base=agot, theirs=mfa, label=label)
    require_delta_preserved(base=agot, parent=mfa, merged=merged, ours=mde, label=label)
    return replace_exact(
        merged,
        DRAGON_HATCHING_DEATH_LIMIT,
        DRAGON_HATCHING_DEATH_LIMIT + CANON_DEATH_GUARD,
        f"{label} canon-continuity guard",
        expected=2,
    )


def generate_core_coronation_events(agot: str, mfa: str) -> str:
    """Apply MFA timing and the profile-independent coronation scope guards."""
    label = "coronation_events.txt"
    merged = merge_onto_agot(ours=agot, base=agot, theirs=mfa, label=label)
    unsafe = (
        "\t\t\t\t\tcp:councillor_court_chaplain = {\n"
        "\t\t\t\t\t\tset_location = root.location\n"
        "\t\t\t\t\t\tadd_to_activity_without_travel = root.involved_activity\n"
        "\t\t\t\t\t}\n"
    )
    return replace_exact(
        merged,
        unsafe,
        CHAPLAIN_SUMMON_GUARD,
        label=f"{label} guarded court chaplain summon",
        expected=1,
    )


def generate_core_outputs(
    workshop: dict[str, Path], vanilla: Path
) -> dict[Path, bytes]:
    """Build overrides valid when neither LoV nor the eastern expansion is loaded."""
    outputs: dict[Path, bytes] = {}
    for language in TITLE_LANGUAGES:
        key = f"NOW_TITLES_{language.upper()}"
        outputs[OUTPUT_RELATIVES[key]] = generate_title_localization(
            read_text(workshop["NOW"] / SOURCE_RELATIVES[key]), language
        ).encode("utf-8-sig")
    outputs[MDE_RELATIVE] = normalize_output(
        generate_mde_on_actions(
            read_text(workshop["MDE_EGGS"] / MDE_RELATIVE),
            read_text(workshop["MDE_EVENTS"] / MDE_RELATIVE),
            read_text(workshop["AGOT"] / AGOT_YEARLY_RELATIVE),
        )
    ).encode("utf-8-sig")
    outputs[CANON_DRAGON_BIRTHDAY_RELATIVE] = normalize_output(
        generate_canon_dragon_birthday_on_action(
            read_text(workshop["AGOT"] / CHILDHOOD_ON_ACTIONS_RELATIVE),
            read_text(workshop["AGOT"] / AGOT_CHILDHOOD_ON_ACTIONS_RELATIVE),
            read_text(
                workshop["NEW_PERSONALITY_EVENTS"] / CHILDHOOD_ON_ACTIONS_RELATIVE
            ),
        )
    ).encode("utf-8-sig")
    outputs[HUD_RELATIVE] = normalize_output(
        generate_hud(
            read_text(workshop["AGOT"] / HUD_RELATIVE),
            read_text(workshop["IRON_AND_SALT"] / HUD_RELATIVE),
            read_text(workshop["DFP_AGOT"] / HUD_RELATIVE),
            read_text(workshop["MDE_EGGS"] / MDE_HUD_RELATIVE),
        )
    ).encode("utf-8-sig")
    # Without LoV, Iron and Salt is already the desired AGOT-derived last writer.
    outputs[MAP_ICON_RELATIVE] = normalize_output(
        read_text(workshop["IRON_AND_SALT"] / MAP_ICON_RELATIVE)
    ).encode("utf-8-sig")
    outputs[IS_HUMAN_RELATIVE] = normalize_output(
        generate_is_human(
            read_text(workshop["AGOT"] / AGOT_CHARACTER_TRIGGERS),
            read_text(workshop["IRON_AND_SALT"] / KRAKEN_TRIGGERS),
            read_text(workshop["GREAT_COUNCILS"] / GREAT_COUNCILS_TRIGGERS),
        )
    ).encode("utf-8-sig")
    outputs[CAN_BE_ACTIVITY_GUEST_RELATIVE] = normalize_output(
        generate_core_can_be_activity_guest(
            read_text(workshop["AGOT"] / RULES_RELATIVE),
            read_text(workshop["LONG_NIGHT"] / LONG_NIGHT_ACTIVITY_RULES),
            read_text(workshop["LIVING_WESTEROS"] / LIVING_WESTEROS_RULES),
        )
    ).encode("utf-8-sig")
    outputs[AGOT_TRAVEL_OPTIONS_RELATIVE] = normalize_output(
        generate_agot_travel_options(
            read_text(workshop["AGOT"] / AGOT_TRAVEL_OPTIONS_RELATIVE),
            read_text(workshop["TRAVELERS_AGOT"] / AGOT_TRAVEL_OPTIONS_RELATIVE),
        )
    ).encode("utf-8-sig")
    # `travel_options.txt` needs no copy here: the Travelers AGOT compatch is
    # already its last writer in this profile. `travel_on_actions.txt` does,
    # because More Dragon Eggs writes it later.
    outputs[TRAVEL_ON_ACTIONS_RELATIVE] = normalize_output(
        generate_core_travel_on_actions(
            read_text(workshop["TRAVELERS_AGOT"] / TRAVEL_ON_ACTIONS_RELATIVE)
        )
    ).encode("utf-8-sig")
    agot = workshop["AGOT"]
    mfa = workshop["MFA"]
    outputs[TOURNAMENT_RELATIVE] = normalize_output(
        generate_tournament(
            read_text(agot / TOURNAMENT_RELATIVE),
            read_text(agot / TOURNAMENT_RELATIVE),
            read_text(mfa / TOURNAMENT_RELATIVE),
        )
    ).encode("utf-8-sig")
    outputs[CORONATION_RELATIVE] = normalize_output(
        guard_holy_site_holders(
            merge_onto_agot(
                ours=read_text(agot / CORONATION_RELATIVE),
                base=read_text(agot / CORONATION_RELATIVE),
                theirs=read_text(mfa / CORONATION_RELATIVE),
                label="coronation.txt core",
            ),
            label="coronation.txt core",
        )
    ).encode("utf-8-sig")
    outputs[WEDDING_RELATIVE] = normalize_output(
        generate_wedding(
            read_text(agot / WEDDING_RELATIVE),
            read_text(workshop["LIVING_WESTEROS"] / WEDDING_RELATIVE),
            read_text(mfa / WEDDING_RELATIVE),
        )
    ).encode("utf-8-sig")
    outputs[CORONATION_EVENTS_RELATIVE] = normalize_output(
        generate_core_coronation_events(
            read_text(agot / CORONATION_EVENTS_RELATIVE),
            read_text(mfa / CORONATION_EVENTS_RELATIVE),
        )
    ).encode("utf-8-sig")
    outputs[DRAGON_HATCHING_RELATIVE] = normalize_output(
        generate_core_dragon_hatching(
            read_text(agot / DRAGON_HATCHING_RELATIVE),
            read_text(workshop["MDE_EGGS"] / DRAGON_HATCHING_RELATIVE),
            read_text(mfa / DRAGON_HATCHING_RELATIVE),
        )
    ).encode("utf-8-sig")
    outputs[EP3_SCRIPTED_EFFECTS_RELATIVE] = normalize_output(
        generate_ep3_scripted_effects(
            read_text(agot / EP3_SCRIPTED_EFFECTS_RELATIVE),
            read_text(workshop["MDE_EGGS"] / EP3_SCRIPTED_EFFECTS_RELATIVE),
            read_text(workshop["SEASONS"] / EP3_SCRIPTED_EFFECTS_RELATIVE),
        )
    ).encode("utf-8-sig")
    outputs[CONTEST_EVENTS_RELATIVE] = normalize_output(
        generate_contest_events(
            read_text(agot / CONTEST_EVENTS_RELATIVE),
            read_text(agot / CONTEST_EVENTS_RELATIVE),
            read_text(mfa / CONTEST_EVENTS_RELATIVE),
            read_text(workshop["CAFG"] / CONTEST_EVENTS_RELATIVE),
            read_text(vanilla / CONTEST_EVENTS_RELATIVE),
        )
    ).encode("utf-8-sig")
    # NOW-Seasons writes under replace/. Restate it at the root and suppress the
    # earlier duplicate so the same region key never has two active definitions.
    #
    # The restated copy is pruned against the titles this profile actually
    # defines, exactly as the Legacy of Valyria compatch prunes its own source.
    # NOW-Seasons names duchy keys such as `d_ironrath` that no parent declares
    # at county level, so shipping it verbatim would resolve the region file
    # against titles that do not exist without Legacy of Valyria.  The seasonal
    # group assignment is skipped for the same reason: the regions it would name
    # come from the Seasons of Valyria compatch, which this profile omits.
    season_relative = Path("map_data/geographical_regions/north_sans_neck.txt")
    outputs[season_relative] = normalize_output(
        generate_regions(
            read_text(
                workshop["NOW_SEASONS"]
                / "map_data/geographical_regions/replace/north_sans_neck.txt"
            ),
            build_title_provinces(workshop[key] for key in CORE_TITLE_TREE_SOURCES),
            groups={},
            undefined=EXPECTED_UNDEFINED_SEASON_MEMBERS,
        )
    ).encode("utf-8-sig")
    outputs[Path("map_data/geographical_regions/replace/north_sans_neck.txt")] = (
        b"\xef\xbb\xbf"
    )
    return outputs


def generate_outputs(workshop: dict[str, Path], vanilla: Path) -> dict[Path, bytes]:
    # NOW owns the `d_lychester` creation requirement. Pin its current capital
    # county and avoid a no-delta whole-file landed-title override.
    now_title = read_text(workshop["NOW"] / SOURCE_RELATIVES["NOW"])
    if "title:d_medway.title_capital_county" in now_title:
        raise AssertionError("NOW d_lychester requirement references d_medway")
    if now_title.count("has_title = title:d_lychester.title_capital_county") != 1:
        raise AssertionError("NOW d_lychester creation requirement changed")

    bridge = workshop["SEASONS_BRIDGE"]
    check_shader(read_text(bridge / SOURCE_RELATIVES["SEASON_FX"]))
    outputs = {
        OUTPUT_RELATIVES["SEASON_EVENTS"]: normalize_output(
            generate_events(read_text(bridge / SOURCE_RELATIVES["SEASON_EVENTS"]))
        ).encode("utf-8-sig"),
        OUTPUT_RELATIVES["SEASON_REGIONS"]: normalize_output(
            generate_regions(
                read_text(bridge / SOURCE_RELATIVES["SEASON_REGIONS"]),
                build_title_provinces(workshop[key] for key in TITLE_TREE_SOURCES),
            )
        ).encode("utf-8-sig"),
    }
    for language in TITLE_LANGUAGES:
        key = f"NOW_TITLES_{language.upper()}"
        outputs[OUTPUT_RELATIVES[key]] = generate_title_localization(
            read_text(workshop["NOW"] / SOURCE_RELATIVES[key]), language
        ).encode("utf-8-sig")
    outputs[MDE_RELATIVE] = normalize_output(
        generate_mde_on_actions(
            read_text(workshop["MDE_EGGS"] / MDE_RELATIVE),
            read_text(workshop["MDE_EVENTS"] / MDE_RELATIVE),
            read_text(workshop["AGOT"] / AGOT_YEARLY_RELATIVE),
        )
    ).encode("utf-8-sig")
    outputs[CANON_DRAGON_BIRTHDAY_RELATIVE] = normalize_output(
        generate_canon_dragon_birthday_on_action(
            read_text(workshop["AGOT"] / CHILDHOOD_ON_ACTIONS_RELATIVE),
            read_text(workshop["AGOT"] / AGOT_CHILDHOOD_ON_ACTIONS_RELATIVE),
            read_text(
                workshop["NEW_PERSONALITY_EVENTS"] / CHILDHOOD_ON_ACTIONS_RELATIVE
            ),
        )
    ).encode("utf-8-sig")
    outputs[HUD_RELATIVE] = normalize_output(
        generate_hud(
            read_text(workshop["AGOT"] / HUD_RELATIVE),
            read_text(workshop["IRON_AND_SALT"] / HUD_RELATIVE),
            read_text(workshop["DFP_AGOT"] / HUD_RELATIVE),
            read_text(workshop["MDE_EGGS"] / MDE_HUD_RELATIVE),
        )
    ).encode("utf-8-sig")
    outputs[MAP_ICON_RELATIVE] = normalize_output(
        generate_map_icon_layer(
            read_text(workshop["AGOT"] / MAP_ICON_RELATIVE),
            read_text(workshop["IRON_AND_SALT"] / MAP_ICON_RELATIVE),
            read_text(workshop["LOV_BRIDGE"] / MAP_ICON_RELATIVE),
        )
    ).encode("utf-8-sig")
    outputs[IS_HUMAN_RELATIVE] = normalize_output(
        generate_is_human(
            read_text(workshop["AGOT"] / AGOT_CHARACTER_TRIGGERS),
            read_text(workshop["IRON_AND_SALT"] / KRAKEN_TRIGGERS),
            read_text(workshop["GREAT_COUNCILS"] / GREAT_COUNCILS_TRIGGERS),
        )
    ).encode("utf-8-sig")
    outputs[IS_DIARCH_VALID_RELATIVE] = normalize_output(
        generate_is_diarch_valid(
            read_text(workshop["AGOT"] / RULES_RELATIVE),
            read_text(workshop["LOV_BRIDGE"] / RULES_RELATIVE),
            read_text(workshop["LONG_NIGHT"] / LONG_NIGHT_DIARCH_RULES),
        )
    ).encode("utf-8-sig")
    outputs[CAN_BE_ACTIVITY_GUEST_RELATIVE] = normalize_output(
        generate_can_be_activity_guest(
            read_text(workshop["AGOT"] / RULES_RELATIVE),
            read_text(workshop["LOV_BRIDGE"] / RULES_RELATIVE),
            read_text(workshop["LONG_NIGHT"] / LONG_NIGHT_ACTIVITY_RULES),
            read_text(workshop["LIVING_WESTEROS"] / LIVING_WESTEROS_RULES),
        )
    ).encode("utf-8-sig")
    outputs[TRAVEL_ON_ACTIONS_RELATIVE] = normalize_output(
        generate_travel_on_actions(
            read_text(workshop["AGOT"] / TRAVEL_ON_ACTIONS_RELATIVE),
            read_text(workshop["TRAVELERS_AGOT"] / TRAVEL_ON_ACTIONS_RELATIVE),
            read_text(workshop["LOV_BRIDGE"] / TRAVEL_ON_ACTIONS_RELATIVE),
        )
    ).encode("utf-8-sig")
    outputs[TRAVEL_OPTIONS_RELATIVE] = normalize_output(
        generate_travel_options(
            read_text(workshop["AGOT"] / TRAVEL_OPTIONS_RELATIVE),
            read_text(workshop["TRAVELERS_AGOT"] / TRAVEL_OPTIONS_RELATIVE),
            read_text(workshop["LOV_BRIDGE"] / TRAVEL_OPTIONS_RELATIVE),
        )
    ).encode("utf-8-sig")
    outputs[AGOT_TRAVEL_OPTIONS_RELATIVE] = normalize_output(
        generate_agot_travel_options(
            read_text(workshop["AGOT"] / AGOT_TRAVEL_OPTIONS_RELATIVE),
            read_text(workshop["TRAVELERS_AGOT"] / AGOT_TRAVEL_OPTIONS_RELATIVE),
        )
    ).encode("utf-8-sig")
    agot = workshop["AGOT"]
    lov = workshop["LOV_BRIDGE"]
    mfa = workshop["MFA"]
    outputs[TOURNAMENT_RELATIVE] = normalize_output(
        generate_tournament(
            read_text(agot / TOURNAMENT_RELATIVE),
            read_text(lov / TOURNAMENT_RELATIVE),
            read_text(mfa / TOURNAMENT_RELATIVE),
        )
    ).encode("utf-8-sig")
    outputs[CORONATION_RELATIVE] = normalize_output(
        generate_coronation(
            read_text(agot / CORONATION_RELATIVE),
            read_text(lov / CORONATION_RELATIVE),
            read_text(mfa / CORONATION_RELATIVE),
        )
    ).encode("utf-8-sig")
    outputs[WEDDING_RELATIVE] = normalize_output(
        generate_wedding(
            read_text(agot / WEDDING_RELATIVE),
            read_text(workshop["LIVING_WESTEROS"] / WEDDING_RELATIVE),
            read_text(mfa / WEDDING_RELATIVE),
        )
    ).encode("utf-8-sig")
    outputs[CORONATION_EVENTS_RELATIVE] = normalize_output(
        generate_coronation_events(
            read_text(agot / CORONATION_EVENTS_RELATIVE),
            read_text(lov / CORONATION_EVENTS_RELATIVE),
            read_text(mfa / CORONATION_EVENTS_RELATIVE),
        )
    ).encode("utf-8-sig")
    outputs[DRAGON_HATCHING_RELATIVE] = normalize_output(
        generate_dragon_hatching(
            read_text(agot / DRAGON_HATCHING_RELATIVE),
            read_text(workshop["MDE_EGGS"] / DRAGON_HATCHING_RELATIVE),
            read_text(lov / DRAGON_HATCHING_RELATIVE),
            read_text(mfa / DRAGON_HATCHING_RELATIVE),
        )
    ).encode("utf-8-sig")
    outputs[DRAGON_CRADLING_RELATIVE] = normalize_output(
        generate_mde_lov_cradling(
            read_text(agot / DRAGON_CRADLING_RELATIVE),
            read_text(workshop["MDE_EGGS"] / DRAGON_CRADLING_RELATIVE),
            read_text(lov / DRAGON_CRADLING_RELATIVE),
        )
    ).encode("utf-8-sig")
    outputs[DRAGON_HATCHING_EVENTS_RELATIVE] = normalize_output(
        generate_mde_lov_hatching_events(
            read_text(agot / DRAGON_HATCHING_EVENTS_RELATIVE),
            read_text(workshop["MDE_EGGS"] / DRAGON_HATCHING_EVENTS_RELATIVE),
            read_text(lov / DRAGON_HATCHING_EVENTS_RELATIVE),
        )
    ).encode("utf-8-sig")
    outputs[RUINS_EVENTS_RELATIVE] = normalize_output(
        generate_mde_lov_ruins(
            read_text(agot / RUINS_EVENTS_RELATIVE),
            read_text(workshop["MDE_EGGS"] / RUINS_EVENTS_RELATIVE),
            read_text(lov / RUINS_EVENTS_RELATIVE),
        )
    ).encode("utf-8-sig")
    outputs[MDE_LOV_DRAGONPIT_OUTPUT] = normalize_output(
        generate_mde_lov_dragonpit_effects(
            read_text(agot / DRAGONPIT_EFFECTS_RELATIVE),
            read_text(workshop["MDE_EGGS"] / DRAGONPIT_EFFECTS_RELATIVE),
            read_text(workshop["LOV_BRIDGE"] / LOV_DRAGONPIT_EFFECTS_RELATIVE),
        )
    ).encode("utf-8-sig")
    outputs[EP3_SCRIPTED_EFFECTS_RELATIVE] = normalize_output(
        generate_ep3_scripted_effects(
            read_text(agot / EP3_SCRIPTED_EFFECTS_RELATIVE),
            read_text(workshop["MDE_EGGS"] / EP3_SCRIPTED_EFFECTS_RELATIVE),
            read_text(workshop["SEASONS"] / EP3_SCRIPTED_EFFECTS_RELATIVE),
        )
    ).encode("utf-8-sig")
    outputs[CONTEST_EVENTS_RELATIVE] = normalize_output(
        generate_contest_events(
            read_text(agot / CONTEST_EVENTS_RELATIVE),
            read_text(lov / CONTEST_EVENTS_RELATIVE),
            read_text(mfa / CONTEST_EVENTS_RELATIVE),
            read_text(workshop["CAFG"] / CONTEST_EVENTS_RELATIVE),
            read_text(vanilla / CONTEST_EVENTS_RELATIVE),
        )
    ).encode("utf-8-sig")
    return outputs


# One line per merge decision, kept beside the code that implements it. The
# upstream inputs behind them are pinned by sources.lock.json.
INTENT = {
    "title": "keep NOW's d_lychester requirement parent-owned",
    "title_localization": (
        "rebase NOW's title names and re-add the COW Sisterton/Dunstonbury barony names"
    ),
    "events": "start DoD historical starts in autumn",
    "shader": "assert the Seasons bridge keeps its global AGOT skip threshold",
    "regions": "rebase NOW tokens and cover LoV cleanup regions without ruins",
    "grandeur": (
        "assert the AMSB/LoV compatch still covers every AMSB court "
        "scene, so this module needs no grandeur_levels.txt override"
    ),
    "dragon_on_actions": ("union the two mods that contest mde_yearly_on_actions.txt"),
    "canon_dragon_birthday": (
        "restore AGOT's AI canon-rider tenth-birthday dispatch beside "
        "New Personality Events for Children"
    ),
    "cow_models": (
        "assert the unenabled NOW-COW compatch's special-building model "
        "remaps are still carried by the hand-merged trigger"
    ),
    "iron_and_salt_hud": (
        "merge Iron and Salt's naval and kraken HUD with Dynamic Family "
        "Portrait's AGOT stack and More Dragon Eggs portrait sizes"
    ),
    "iron_and_salt_map_icon": (
        "keep the kraken map icon without the LoV bridge's absent "
        "find-elder datacontext"
    ),
    "iron_and_salt_is_human": (
        "combine AGOT's body with the Iron and Salt and Great Councils "
        "extensions under one later-sorting writer"
    ),
    "tournament": (
        "run tournaments at MFA's pace while keeping AGOT's terrain "
        "abstraction and disabled archery tradition"
    ),
    "coronation": (
        "run coronations at MFA's pace and test holy-site holders that may not exist"
    ),
    "coronation_events": (
        "run the coronation chain at MFA's pace and summon the court "
        "chaplain only into scopes that still resolve"
    ),
    "dragon_hatching": (
        "merge More Dragon Eggs' variable-driven ceremonies with LoV volcano "
        "locations, run them at MFA's pace, and spare canon-protected hosts"
    ),
    "ep3_scripted_effects": (
        "combine the More Dragon Eggs landing hooks with Seasons weather modifiers"
    ),
    "contest_events": (
        "combine the LoV compatch's tournament summary guards, MFA's "
        "contest cooldown, and CaFG's granular county conversion"
    ),
    "is_diarch_valid": (
        "keep the LoV bridge's missing-character guard under the Long "
        "Night's later-sorting Night's Watch clause"
    ),
    "travel_on_actions": (
        "combine Travelers' AGOT wrappers and imprisonment behavior with "
        "the LoV bridge's optional scopes and restored-Valyria travel gate"
    ),
    "travel_options": (
        "keep Travelers' imprisonment and leader-availability checks with "
        "the LoV bridge's guarded mercenary leader"
    ),
    "agot_travel_options": (
        "add Travelers' imprisonment guard without dropping AGOT's sailing exclusion"
    ),
    "wedding": (
        "run weddings at MFA's pace with Living Westeros' ceremony backgrounds "
        "and AGOT's terrain abstraction"
    ),
    "can_be_activity_guest": (
        "combine LoV's optional scopes, the Long Night's dead exclusion, and "
        "Living Westeros' guest-right restrictions under one final rule writer"
    ),
}


def parent_versions(workshop: dict[str, Path]) -> dict[str, str]:
    """Read each parent's declared version, for the generation report.

    Reading every descriptor.mod also keeps them in sources.lock.json, which
    makes a parent bump visible to `ck3mm upstream` even when the module's
    own output does not move.
    """
    versions: dict[str, str] = {}
    for label, module_root in workshop.items():
        match = re.search(
            r'(?m)^\s*version\s*=\s*"([^"]+)"',
            read_text(module_root / "descriptor.mod"),
        )
        versions[label] = match.group(1) if match else "unversioned"
    return versions


def generate_lov(context: GenerationContext) -> None:
    """Generate the final integrations whose winning source is Legacy of Valyria."""
    # Called for the check, not the value: every parent must sit under one
    # Workshop root, or the source names below are resolving somewhere unexpected.
    context.workshop_root(
        "agot",
        "new-personality-events",
        "agot-now",
        "seasons",
        "seasons-bridge",
        "amsb",
        "amsb-lov-compatch",
        "mde-eggs",
        "mde-events",
        "cow-now-compatch",
        "iron-and-salt",
        "dfp-agot",
        "lov-agot-bridge",
        "great-councils",
        "long-night-azor-ahai",
        "much-faster-activities",
        "culture-faith-granularity",
        "lov",
        "travelers",
        "travelers-agot-compatibility",
        "living-westeros",
    )
    workshop = {
        "AGOT": context.source("agot"),
        "NEW_PERSONALITY_EVENTS": context.source("new-personality-events"),
        "NOW": context.source("agot-now"),
        "SEASONS": context.source("seasons"),
        "SEASONS_BRIDGE": context.source("seasons-bridge"),
        "AMSB": context.source("amsb"),
        "AMSB_LOV": context.source("amsb-lov-compatch"),
        "MDE_EGGS": context.source("mde-eggs"),
        "MDE_EVENTS": context.source("mde-events"),
        "COW_NOW": context.source("cow-now-compatch"),
        "IRON_AND_SALT": context.source("iron-and-salt"),
        "DFP_AGOT": context.source("dfp-agot"),
        "LOV_BRIDGE": context.source("lov-agot-bridge"),
        "GREAT_COUNCILS": context.source("great-councils"),
        "LONG_NIGHT": context.source("long-night-azor-ahai"),
        "MFA": context.source("much-faster-activities"),
        "CAFG": context.source("culture-faith-granularity"),
        "LOV": context.source("lov"),
        "TRAVELERS": context.source("travelers"),
        "TRAVELERS_AGOT": context.source("travelers-agot-compatibility"),
        "LIVING_WESTEROS": context.source("living-westeros"),
    }
    vanilla = context.source("vanilla")
    missing = [
        f"{label}:{path}" for label, path in workshop.items() if not path.is_dir()
    ]
    if missing:
        raise FileNotFoundError(f"missing Workshop modules: {missing}")

    versions = parent_versions(workshop)
    print(
        "Parents: " + ", ".join(f"{label} {v}" for label, v in sorted(versions.items()))
    )

    check_grandeur_coverage(
        read_text(workshop["AMSB"] / GRANDEUR_RELATIVE),
        read_text(workshop["AMSB_LOV"] / GRANDEUR_RELATIVE),
    )
    assert_mde_parent_invariants(workshop["AGOT"], workshop["MDE_EGGS"])

    outputs = {
        relative: data
        for relative, data in generate_outputs(workshop, vanilla).items()
        if relative in LOV_OUTPUTS
    }
    for relative, data in outputs.items():
        context.write_bytes(relative, data)
    print(f"Generated Legacy of Valyria integration overrides: {len(outputs)} files")


def generate_core(context: GenerationContext) -> None:
    """Generate the final integrations that do not depend on LoV or Further East."""
    names = (
        "agot",
        "new-personality-events",
        "agot-now",
        "seasons",
        "now-seasons",
        "mde-eggs",
        "mde-events",
        "cow-now-compatch",
        "iron-and-salt",
        "dfp-agot",
        "great-councils",
        "long-night-azor-ahai",
        "much-faster-activities",
        "culture-faith-granularity",
        "travelers-agot-compatibility",
        "living-westeros",
    )
    context.workshop_root(*names)
    workshop = {
        "AGOT": context.source("agot"),
        "NEW_PERSONALITY_EVENTS": context.source("new-personality-events"),
        "NOW": context.source("agot-now"),
        "SEASONS": context.source("seasons"),
        "NOW_SEASONS": context.source("now-seasons"),
        "MDE_EGGS": context.source("mde-eggs"),
        "MDE_EVENTS": context.source("mde-events"),
        "COW_NOW": context.source("cow-now-compatch"),
        "IRON_AND_SALT": context.source("iron-and-salt"),
        "DFP_AGOT": context.source("dfp-agot"),
        "GREAT_COUNCILS": context.source("great-councils"),
        "LONG_NIGHT": context.source("long-night-azor-ahai"),
        "MFA": context.source("much-faster-activities"),
        "CAFG": context.source("culture-faith-granularity"),
        "TRAVELERS_AGOT": context.source("travelers-agot-compatibility"),
        "LIVING_WESTEROS": context.source("living-westeros"),
    }
    missing = [
        f"{label}:{path}" for label, path in workshop.items() if not path.is_dir()
    ]
    if missing:
        raise FileNotFoundError(f"missing Workshop modules: {missing}")
    verbatim = {
        relative: read_text(context.assets_dir / asset)
        for asset, relative in CORE_VERBATIM_ASSETS.items()
    }
    check_cow_model_remaps(
        read_text(workshop["COW_NOW"] / COW_NOW_GRAPHICS_RELATIVE),
        verbatim[COW_MODEL_TRIGGER_RELATIVE],
    )
    assert_mde_parent_invariants(workshop["AGOT"], workshop["MDE_EGGS"])
    outputs = generate_core_outputs(workshop, context.source("vanilla"))
    for relative, text in verbatim.items():
        outputs[relative] = text.encode("utf-8-sig")
    for relative, data in outputs.items():
        context.write_bytes(relative, data)
    print(f"Generated core integration overrides: {len(outputs)} files")
