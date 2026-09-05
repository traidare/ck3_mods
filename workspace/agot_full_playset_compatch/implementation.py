#!/usr/bin/env python3
"""Generate the narrow final overrides needed by the AGOT playset."""

from __future__ import annotations

import re
import subprocess
import tempfile
from collections import Counter, defaultdict
from collections.abc import Iterable
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
RULES_RELATIVE = Path("common/scripted_rules/00_rules.txt")
LONG_NIGHT_DIARCH_RULES = Path("common/scripted_rules/zz_ln_diarch_rules.txt")
LOV_DIARCH_GUARD = "limit = { exists = this }"
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
# The model trigger is hand-merged rather than generated, so it is read from the
# installed payload; the generator's staging root only holds owned outputs.
PAYLOAD_ROOT = Path("mods/agot_full_playset_compatch")
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
DRAGON_HATCHING_RELATIVE = Path(
    "common/activities/activity_types/agot_dragon_hatching.txt"
)
CORONATION_EVENTS_RELATIVE = Path(
    "events/activities/coronation_activity/coronation_events.txt"
)
CONTEST_EVENTS_RELATIVE = Path("events/activities/tournaments/contest_events.txt")
VALE_PROVINCES_RELATIVE = Path("history/provinces/replace/00_k_the_vale_prov.txt")

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

# Nobility of Westeros' own Sisterton entries, and the holdings this layer wants
# in their place.  Everything else in the file is that parent's, because the
# same path shadows it whole rather than merging.
VALE_SISTERTON_PARENT = (
    "############### b_breakwater_castle ###############\n"
    "########## c_sweetsister - d_the_sisters ##########\n"
    "2715 = {\n"
    "\tculture = sisterman\n"
    "\treligion = fots_seven\n"
    "\tholding = castle_holding\n"
    "\t7824.1.1 = {\n"
    "\t\tbuildings = { castle_03 }\n"
    "\t}\n"
    "}\n"
    "################ b_breakwater_watch ###############\n"
    "########## c_sweetsister - d_the_sisters ##########\n"
    "2716 = {\n"
    "\tholding = none\n"
    "}\n"
    "##################### b_dordon ####################\n"
    "########## c_sweetsister - d_the_sisters ##########\n"
    "2717 = {\n"
    "\tculture = sisterman\n"
    "\treligion = fots_seven\n"
    "\tholding = castle_holding\n"
    "\t7824.1.1 = {\n"
    "\t\tbuildings = { castle_03 }\n"
    "\t}\n"
    "}\n"
)
VALE_SISTERTON_OWNED = (
    "############### b_breakwater_castle ###############\n"
    "########## c_sweetsister - d_the_sisters ##########\n"
    "2715 = {\n"
    "\tholding = castle_holding\n"
    "\t7824.1.1 = {\n"
    "\t\tbuildings = { castle_01 }\n"
    "\t}\n"
    "}\n"
    "################ b_sunderland_hall ################\n"
    "########### c_sunderland - d_the_sisters ##########\n"
    "2716 = {\n"
    "\tculture = sisterman\n"
    "\treligion = fots_seven\n"
    "\tholding = castle_holding\n"
    "\t7824.1.1 = {\n"
    "\t\tbuildings = { castle_03 }\n"
    "\t}\n"
    "}\n"
    "################ b_breakwater_watch ###############\n"
    "########## c_sweetsister - d_the_sisters ##########\n"
    "2717 = {\n"
    "\tculture = sisterman\n"
    "\treligion = fots_seven\n"
    "\tholding = castle_holding\n"
    "\t7824.1.1 = {\n"
    "\t\tbuildings = { castle_03 }\n"
    "\t}\n"
    "}\n"
)
VALE_DORDON_HEADER_PARENT = "################ b_sunderland_hall ################\n"
VALE_DORDON_HEADER_OWNED = "##################### b_dordon ####################\n"


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
    "SEASON_FX": SOURCE_RELATIVES["SEASON_FX"],
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
            "the AMSB/LoV compatch no longer covers every AMSB court "
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
    "on_game_start_iterate_next_clutch",
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
            "More Dragon Events no longer copies AGOT's dragon pulse verbatim; "
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
            "AGOT on_10th_birthday no longer dispatches "
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
        raise AssertionError(f"{name} block is no longer unique")
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
            raise AssertionError(f"historical season {date} no longer starts in autumn")
    return text if text.endswith("\n") else text + "\n"


def generate_shader(source: str) -> str:
    skip = "static const float SKIP_VALUE = 0.001f;"
    if source.count(skip) != 1:
        raise AssertionError("Seasons shader skip threshold changed")
    struct = re.search(r"(?m)^struct\s+EffectIntensities\s*\n\{", source)
    if not struct:
        raise AssertionError("missing EffectIntensities declaration")
    struct_end = matching_brace(source, source.find("{", struct.start(), struct.end()))
    text = (
        source[: struct_end + 1]
        + (
            "\n\nCode\n[[\n"
            "\t// AGOT: this include is also consumed by vertex shaders.\n"
            "\tstatic const float SKIP_VALUE = 0.001f;\n"
            "]]\n"
        )
        + source[struct_end + 1 :]
    )
    text = replace_exact(
        text,
        "\t\tstatic const float SKIP_VALUE = 0.001f;\n",
        "",
        label="pixel-shader-local skip threshold",
    )
    if text.count(skip) != 1 or text.index(skip) > text.index("PixelShader ="):
        raise AssertionError("shared Seasons shader skip threshold placement failed")
    return text if text.endswith("\n") else text + "\n"


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
TITLE_TREE_SOURCES = ("AGOT", "NOW", "LOV", "LOV_BRIDGE", "ESSOS_EXPANDED")

MEMBERSHIP_KEYS = ("empires", "kingdoms", "duchies", "counties")

# Seasonal regions name three titles that hold no province: a titular duchy and
# a titular kingdom, plus one duchy no parent defines at all. They cover
# nothing, so they are never redundant and the coverage check has to expect
# them by name rather than treat an empty result as a resolution failure.
TITULAR_SEASON_TITLES = frozenset({"d_knellstone", "d_turnbridge", "k_the_rills"})

# Every membership entry the prune removes, by the region that listed it. A
# kingdom already contains its duchies and a duchy its counties, so re-listing
# them makes CK3 read the same province twice and log `Region 'N' has multiple
# entries for the province 'N'` once per repeat at world init. Dropping the
# narrower entry leaves the region covering exactly the same provinces.
EXPECTED_SEASON_REGION_PRUNE = {
    "world_barrowlands_seasons": 5,
    "world_westerlands_low": 6,
    "world_sheepshead_hills": 4,
    "world_upper_crown": 3,
    "world_norvos_seasons": 3,
    "world_dornish_marches_seasons": 3,
    "world_the_fingers_seasons": 3,
    "world_lonely_hills": 3,
    "world_upper_reach": 2,
    "world_dorne_north_coast": 2,
}

_TITLE_TOKEN = re.compile(r"[ekdcb]_[A-Za-z0-9_\-']+")
_TREE_TOKEN = re.compile(r"([A-Za-z0-9_\-']+)\s*=\s*\{|\{|\}|province\s*=\s*(\d+)")


def build_title_provinces(roots: Iterable[Path]) -> dict[str, set[int]]:
    """Return the provinces each landed title covers, resolved by load order."""
    parent: dict[str, str] = {}
    barony_province: dict[str, int] = {}
    for root in roots:
        directory = root / "common/landed_titles"
        if not directory.is_dir():
            continue
        for path in sorted(directory.rglob("*.txt")):
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
                    enclosing = next(
                        (entry for entry in reversed(stack) if entry), None
                    )
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

    for title in (*parent, *children):
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
                covers = coverage.get(name, set())
                if not covers and name not in TITULAR_SEASON_TITLES:
                    raise AssertionError(
                        f"{region} names {name}, which no declared landed-titles "
                        "source gives a province; re-audit the seasonal membership"
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


def generate_regions(source: str, coverage: dict[str, set[int]]) -> str:
    text = replace_block_member(
        source, "world_westeros_rest_of_dorne", "\t\td_yronwood\n", "\t\td_greenbelt\n"
    )
    if "d_yronwood" in text:
        raise AssertionError("NOW d_greenbelt seasonal-region membership changed")
    if "c_sunvane" in text:
        raise AssertionError("NOW Sunvane seasonal-region membership returned")
    if text.count("\t\tc_brittlebush\n") != 1:
        raise AssertionError("NOW Brittlebush seasonal-region membership changed")

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

    for group, regions in {
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
    }.items():
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
        raise AssertionError(f"{label}: parent no longer differs from AGOT")
    if delta != changed_lines(ours, merged):
        raise AssertionError(f"{label}: merge did not reproduce the parent's delta")


def generate_hud(agot: str, iron_and_salt: str, dfp: str) -> str:
    """Keep the naval and kraken HUD together with the family portrait stack."""
    label = "hud.gui"
    merged = merge_onto_agot(ours=iron_and_salt, base=agot, theirs=dfp, label=label)
    require_delta_preserved(
        base=agot, parent=dfp, merged=merged, ours=iron_and_salt, label=label
    )
    for needle in (
        "type bottom_left_dragon_portrait = container {",
        "type bottom_left_portrait = container {",
        "mde_dragon_portrait_zeroth_size",
        "mde_dragon_portrait_third_size",
    ):
        if needle not in merged:
            raise AssertionError(f"{label}: merged output lost {needle!r}")
    if merged.count("naval") < 1000:
        raise AssertionError(
            f"{label}: Iron and Salt's naval interface did not survive"
        )
    return merged


def generate_map_icon_layer(agot: str, iron_and_salt: str, lov: str) -> str:
    """Keep the kraken map icon without restoring LoV's removed datacontext."""
    label = "map_icon_layer.gui"
    # LoV expresses the same human-portrait gate through AGOT's shared template,
    # while AGOT's source spells it inline. Normalising the equivalent forms
    # leaves LoV's find-elder datacontext removal as its only merge delta.
    lov = replace_exact(
        lov,
        "\t\t\t\tusing = visible_if_not_dragon\n",
        '\t\t\t\tvisible = "[Not(IsCharacterDragon)]"\n',
        label=f"{label} LoV dragon gate",
    )
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
            raise AssertionError(f"{label}: {owner} no longer adds {clause!r}")
        if script_tokens(derived.replace(clause, "", 1)) != script_tokens(parent):
            raise AssertionError(
                f"{label}: {owner}'s definition is no longer AGOT's plus one clause"
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


def generate_is_diarch_valid(agot: str, lov: str, long_night: str) -> str:
    """Combine the Long Night's diarch clause with the LoV bridge's null guard."""
    label = "is_diarch_valid"
    parent = scripted_trigger(agot, label)
    if script_tokens(parent) != f"{label} = {{ {label}_trigger = yes }}":
        raise AssertionError(
            f"{label}: AGOT no longer defines the rule as a bare {label}_trigger call"
        )

    guarded = scripted_trigger(lov, label)
    if script_tokens(guarded) != (
        f"{label} = {{ trigger_if = {{ {LOV_DIARCH_GUARD} {label}_trigger = yes }} "
        "trigger_else = { always = no } }"
    ):
        raise AssertionError(
            f"{label}: the LoV bridge no longer wraps AGOT's call in exactly its "
            f"{LOV_DIARCH_GUARD!r} guard"
        )

    extended = scripted_trigger(long_night, label)
    clause = indented_block(extended, "trigger_if", label=label)
    if "government_is_nw" not in clause:
        raise AssertionError(
            f"{label}: the Long Night's added clause no longer tests the "
            "Night's Watch government flag"
        )
    if script_tokens(extended.replace(clause, "", 1)) != script_tokens(parent):
        raise AssertionError(
            f"{label}: the Long Night's definition is no longer AGOT's plus one "
            "trigger_if clause"
        )

    nested = "\n".join(f"\t{line}" if line else line for line in clause.splitlines())
    inner = indented_block(guarded, "trigger_if", label=label)
    closing = inner.rfind("\n\t}")
    if closing < 0:
        raise AssertionError(
            f"{label}: the LoV bridge's guarded branch lost its indent"
        )
    body = replace_exact(
        guarded,
        inner,
        f"{inner[:closing]}\n{nested}\n\t}}",
        label=f"{label} guarded branch",
    )
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
    text = replace_regex(
        text,
        r"(?m)^([ \t]*)barony\.holder = \{",
        lambda match: (
            f"{match.group(1)}{HOLY_SITE_HOLDER_GUARD}"
            f"{match.group(1)}barony.holder = {{"
        ),
        f"{label} holy-site holder guard",
        expected=4,
    )
    # AGOT writes one of the five tests through optional scopes instead, which
    # suppresses the missing holder without ever failing the test.
    return replace_exact(
        text,
        "\t\t\t\t\t\tbarony ?= {\n"
        "\t\t\t\t\t\t\tholder ?= {\n"
        "\t\t\t\t\t\t\t\tOR = {\n"
        "\t\t\t\t\t\t\t\t\tthis = scope:host\n"
        "\t\t\t\t\t\t\t\t\tany_liege_or_above = { this = scope:host }\n"
        "\t\t\t\t\t\t\t\t}\n"
        "\t\t\t\t\t\t\t}\n"
        "\t\t\t\t\t\t}\n",
        f"\t\t\t\t\t\t{HOLY_SITE_HOLDER_GUARD}"
        "\t\t\t\t\t\tbarony.holder = {\n"
        "\t\t\t\t\t\t\tOR = {\n"
        "\t\t\t\t\t\t\t\tthis = scope:host\n"
        "\t\t\t\t\t\t\t\tany_liege_or_above = { this = scope:host }\n"
        "\t\t\t\t\t\t\t}\n"
        "\t\t\t\t\t\t}\n",
        label=f"{label} optional-scope holy-site test",
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
    # be tested before the move rather than assumed.
    return replace_exact(
        merged,
        "\t\t\t\t\tcp:councillor_court_chaplain = {\n"
        "\t\t\t\t\t\tset_location = root.location\n"
        "\t\t\t\t\t\tadd_to_activity_without_travel = root.involved_activity\n"
        "\t\t\t\t\t}\n",
        "\t\t\t\t\tcp:councillor_court_chaplain ?= {\n"
        "\t\t\t\t\t\tif = {\n"
        "\t\t\t\t\t\t\tlimit = {\n"
        "\t\t\t\t\t\t\t\texists = root.location\n"
        "\t\t\t\t\t\t\t\texists = root.involved_activity\n"
        "\t\t\t\t\t\t\t}\n"
        "\t\t\t\t\t\t\tset_location = root.location\n"
        "\t\t\t\t\t\t\tadd_to_activity_without_travel = root.involved_activity\n"
        "\t\t\t\t\t\t}\n"
        "\t\t\t\t\t}\n",
        label=f"{label} court chaplain summon",
    )


def generate_dragon_hatching(agot: str, mde_lov: str, mfa: str) -> str:
    """Run hatching ceremonies at MFA's pace, sparing canon-protected hosts."""
    label = "agot_dragon_hatching.txt"
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


def generate_vale_provinces(now: str) -> str:
    """Give Sisterton its held baronies without dropping the rest of the Vale.

    This path shadows Nobility of Westeros' file whole rather than merging with
    it, so every province entry the parent ships has to be carried through or it
    falls back to AGOT's.  Deriving the file from the parent is what keeps that
    true as the parent gains, drops, or re-numbers entries.
    """
    label = "00_k_the_vale_prov.txt"
    text = replace_exact(
        now,
        VALE_DORDON_HEADER_PARENT,
        VALE_DORDON_HEADER_OWNED,
        label=f"{label} b_dordon header",
    )
    return replace_exact(
        text,
        VALE_SISTERTON_PARENT,
        VALE_SISTERTON_OWNED,
        label=f"{label} Sisterton holdings",
    )


def generate_outputs(workshop: dict[str, Path], vanilla: Path) -> dict[Path, bytes]:
    # NOW 1.2.5 corrected the `d_lychester` creation requirement upstream (it
    # previously required `d_medway`'s capital county), which was this override's
    # only delta.  Assert the fix is still present instead of shipping a
    # no-delta whole-file copy of the parent's landed titles.
    now_title = read_text(workshop["NOW"] / SOURCE_RELATIVES["NOW"])
    if "title:d_medway.title_capital_county" in now_title:
        raise AssertionError("NOW d_medway creation requirement returned")
    if now_title.count("has_title = title:d_lychester.title_capital_county") != 1:
        raise AssertionError("NOW d_lychester creation requirement changed")

    bridge = workshop["SEASONS_BRIDGE"]
    outputs = {
        OUTPUT_RELATIVES["SEASON_EVENTS"]: normalize_output(
            generate_events(read_text(bridge / SOURCE_RELATIVES["SEASON_EVENTS"]))
        ).encode("utf-8-sig"),
        OUTPUT_RELATIVES["SEASON_FX"]: normalize_output(
            generate_shader(read_text(bridge / SOURCE_RELATIVES["SEASON_FX"]))
        ).encode("utf-8"),
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
            read_text(workshop["MDE_LOV"] / DRAGON_HATCHING_RELATIVE),
            read_text(mfa / DRAGON_HATCHING_RELATIVE),
        )
    ).encode("utf-8-sig")
    outputs[CONTEST_EVENTS_RELATIVE] = normalize_output(
        generate_contest_events(
            read_text(agot / CONTEST_EVENTS_RELATIVE),
            read_text(workshop["LOV_COMPATCH"] / CONTEST_EVENTS_RELATIVE),
            read_text(mfa / CONTEST_EVENTS_RELATIVE),
            read_text(workshop["CAFG"] / CONTEST_EVENTS_RELATIVE),
            read_text(vanilla / CONTEST_EVENTS_RELATIVE),
        )
    ).encode("utf-8-sig")
    outputs[VALE_PROVINCES_RELATIVE] = normalize_output(
        generate_vale_provinces(read_text(workshop["NOW"] / VALE_PROVINCES_RELATIVE))
    ).encode("utf-8-sig")
    return outputs


# One line per merge decision, kept beside the code that implements it. The
# upstream inputs behind them are pinned by sources.lock.json.
INTENT = {
    "title": "repair NOW's removed d_medway reference",
    "title_localization": (
        "rebase NOW's title names and re-add the COW Sisterton/Dunstonbury barony names"
    ),
    "events": "start DoD historical starts in autumn",
    "shader": "share the AGOT skip threshold with vertex shaders",
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
        "keep the kraken map icon without restoring the LoV bridge's "
        "removed find_elder datacontext"
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
        "run hatching ceremonies at MFA's pace on the More Dragon "
        "Eggs/LoV activity, sparing canon-protected hosts"
    ),
    "contest_events": (
        "combine the LoV compatch's tournament summary guards, MFA's "
        "contest cooldown, and CaFG's granular county conversion"
    ),
    "vale_provinces": (
        "give Sisterton its held baronies on top of every province entry "
        "NOW ships, because this path shadows that file whole"
    ),
    "is_diarch_valid": (
        "keep the LoV bridge's missing-character guard under the Long "
        "Night's later-sorting Night's Watch clause"
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


def generate(context: GenerationContext) -> None:
    root = context.workspace_root
    # Called for the check, not the value: every parent must sit under one
    # Workshop root, or the source names below are resolving somewhere unexpected.
    context.workshop_root(
        "agot",
        "new-personality-events",
        "agot-now",
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
        "mde-lov-hatching",
        "lov-agot-compatch",
        "culture-faith-granularity",
        "lov",
        "essos-expanded",
    )
    workshop = {
        "AGOT": context.source("agot"),
        "NEW_PERSONALITY_EVENTS": context.source("new-personality-events"),
        "NOW": context.source("agot-now"),
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
        "MDE_LOV": context.source("mde-lov-hatching"),
        "LOV_COMPATCH": context.source("lov-agot-compatch"),
        "CAFG": context.source("culture-faith-granularity"),
        "LOV": context.source("lov"),
        "ESSOS_EXPANDED": context.source("essos-expanded"),
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
    check_cow_model_remaps(
        read_text(workshop["COW_NOW"] / COW_NOW_GRAPHICS_RELATIVE),
        read_text(root / PAYLOAD_ROOT / COW_MODEL_TRIGGER_RELATIVE),
    )

    outputs = generate_outputs(workshop, vanilla)
    for relative, data in outputs.items():
        context.write_bytes(relative, data)
    print(f"Generated full-compatch overrides: {len(outputs)} files")
