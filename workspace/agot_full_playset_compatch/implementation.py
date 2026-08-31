#!/usr/bin/env python3
"""Generate the narrow final overrides needed by the AGOT playset."""

from __future__ import annotations

import json
import re
import subprocess
import tempfile
from pathlib import Path

from gen import GenerationContext
from gen.hashing import sha256_file
from gen.sources import canonical_source_path
from gen.text import definition_span, matching_brace, read_source

WORKSHOP_IDS = {
    "AGOT": "2962333032",
    "NOW": "3664900993",
    "SEASONS_BRIDGE": "3766038754",
    "AMSB": "3319354609",
    "AMSB_LOV": "3762892081",
    "MDE_EGGS": "3388366564",
    "MDE_EVENTS": "3466228580",
    "COW_NOW": "3742055253",
    "IRON_AND_SALT": "3781577713",
    "DFP_AGOT": "3609763696",
    "LOV_BRIDGE": "3719888822",
    "GREAT_COUNCILS": "3621472324",
}
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
TITLE_LANGUAGES = ("english", "spanish")


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


def replace_once(text: str, old: str, new: str, *, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise AssertionError(f"{label}: expected one match, found {count}")
    return text.replace(old, new)


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
        text = replace_once(text, old, new, label=repair)
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
    AMSB/AGOT+/LoV compatch loads last and currently registers a superset of
    AMSB's scenes, which is the only reason this module does not have to merge
    the file itself.  Fail if that stops holding: a court scene with no entry
    never progresses a visual culture level, and nothing reports it at runtime.
    """
    covered = set(grandeur_cultures(amsb_lov))
    missing = [name for name in grandeur_cultures(amsb) if name not in covered]
    if missing:
        raise AssertionError(
            "the AMSB/AGOT+/LoV compatch no longer covers every AMSB court "
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
    text = replace_once(
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
    text = replace_once(
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
    block = replace_once(block, old, new, label=f"{block_name} member")
    return text[:start] + block + text[end + 1 :]


def generate_regions(source: str) -> str:
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


def generate_outputs(workshop: dict[str, Path]) -> dict[Path, bytes]:
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
            generate_regions(read_text(bridge / SOURCE_RELATIVES["SEASON_REGIONS"]))
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
    return outputs


def source_manifest(
    root: Path, workshop: dict[str, Path], workshop_root: Path
) -> dict[str, object]:
    sources = {
        "NOW": workshop["NOW"] / SOURCE_RELATIVES["NOW"],
        "SEASON_EVENTS": workshop["SEASONS_BRIDGE"] / SOURCE_RELATIVES["SEASON_EVENTS"],
        "SEASON_FX": workshop["SEASONS_BRIDGE"] / SOURCE_RELATIVES["SEASON_FX"],
        "SEASON_REGIONS": workshop["SEASONS_BRIDGE"]
        / SOURCE_RELATIVES["SEASON_REGIONS"],
        "NOW_DESCRIPTOR": workshop["NOW"] / "descriptor.mod",
        "SEASONS_BRIDGE_DESCRIPTOR": workshop["SEASONS_BRIDGE"] / "descriptor.mod",
        **{
            f"NOW_TITLES_{language.upper()}": workshop["NOW"]
            / SOURCE_RELATIVES[f"NOW_TITLES_{language.upper()}"]
            for language in TITLE_LANGUAGES
        },
        "AMSB_GRANDEUR": workshop["AMSB"] / GRANDEUR_RELATIVE,
        "AMSB_LOV_GRANDEUR": workshop["AMSB_LOV"] / GRANDEUR_RELATIVE,
        "AMSB_DESCRIPTOR": workshop["AMSB"] / "descriptor.mod",
        "AMSB_LOV_DESCRIPTOR": workshop["AMSB_LOV"] / "descriptor.mod",
        "AGOT_YEARLY": workshop["AGOT"] / AGOT_YEARLY_RELATIVE,
        "MDE_EGGS": workshop["MDE_EGGS"] / MDE_RELATIVE,
        "MDE_EVENTS": workshop["MDE_EVENTS"] / MDE_RELATIVE,
        "MDE_EGGS_DESCRIPTOR": workshop["MDE_EGGS"] / "descriptor.mod",
        "MDE_EVENTS_DESCRIPTOR": workshop["MDE_EVENTS"] / "descriptor.mod",
        "COW_NOW_GRAPHICS": workshop["COW_NOW"] / COW_NOW_GRAPHICS_RELATIVE,
        "COW_NOW_DESCRIPTOR": workshop["COW_NOW"] / "descriptor.mod",
        "AGOT_HUD": workshop["AGOT"] / HUD_RELATIVE,
        "AGOT_MAP_ICON": workshop["AGOT"] / MAP_ICON_RELATIVE,
        "AGOT_CHARACTER_TRIGGERS": workshop["AGOT"] / AGOT_CHARACTER_TRIGGERS,
        "IRON_AND_SALT_HUD": workshop["IRON_AND_SALT"] / HUD_RELATIVE,
        "IRON_AND_SALT_MAP_ICON": workshop["IRON_AND_SALT"] / MAP_ICON_RELATIVE,
        "IRON_AND_SALT_TRIGGERS": workshop["IRON_AND_SALT"] / KRAKEN_TRIGGERS,
        "IRON_AND_SALT_DESCRIPTOR": workshop["IRON_AND_SALT"] / "descriptor.mod",
        "DFP_AGOT_HUD": workshop["DFP_AGOT"] / HUD_RELATIVE,
        "DFP_AGOT_DESCRIPTOR": workshop["DFP_AGOT"] / "descriptor.mod",
        "LOV_BRIDGE_MAP_ICON": workshop["LOV_BRIDGE"] / MAP_ICON_RELATIVE,
        "LOV_BRIDGE_DESCRIPTOR": workshop["LOV_BRIDGE"] / "descriptor.mod",
        "GREAT_COUNCILS_TRIGGERS": workshop["GREAT_COUNCILS"] / GREAT_COUNCILS_TRIGGERS,
        "GREAT_COUNCILS_DESCRIPTOR": workshop["GREAT_COUNCILS"] / "descriptor.mod",
    }
    versions: dict[str, str] = {}
    for label, module_root in workshop.items():
        match = re.search(
            r'(?m)^\s*version\s*=\s*"([^"]+)"',
            read_text(module_root / "descriptor.mod"),
        )
        versions[label] = match.group(1) if match else "unversioned"

    return {
        "schema_version": 1,
        "workshop_ids": WORKSHOP_IDS,
        "versions": versions,
        "files": {
            label: {
                "path": canonical_source_path(
                    path, root=root, workshop_root=workshop_root
                ),
                "sha256": sha256_file(path),
                "size": path.stat().st_size,
            }
            for label, path in sources.items()
        },
        "intent": {
            "title": "repair NOW's removed d_medway reference",
            "title_localization": (
                "rebase NOW's title names and re-add the COW Sisterton/"
                "Dunstonbury barony names"
            ),
            "events": "start DoD historical starts in autumn",
            "shader": "share the AGOT skip threshold with vertex shaders",
            "regions": "rebase NOW tokens and cover LoV cleanup regions without ruins",
            "grandeur": (
                "assert the AGOT+/LoV compatch still covers every AMSB court "
                "scene, so this module needs no grandeur_levels.txt override"
            ),
            "dragon_on_actions": (
                "union the two mods that contest mde_yearly_on_actions.txt"
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
        },
    }


def generate(context: GenerationContext) -> None:
    root = context.workspace_root
    workshop_root = context.workshop_root(
        "agot",
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
    )
    workshop = {
        "AGOT": context.source("agot"),
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
    }
    missing = [
        f"{label}:{path}" for label, path in workshop.items() if not path.is_dir()
    ]
    if missing:
        raise FileNotFoundError(f"missing Workshop modules: {missing}")

    manifest_path = context.assets_dir / "source_manifest.json"
    manifest = source_manifest(root, workshop, workshop_root)
    if not manifest_path.is_file():
        raise FileNotFoundError(
            f"{manifest_path.relative_to(root)} is missing; review the upstream "
            "inputs and replace the reviewed asset deliberately"
        )
    if json.loads(manifest_path.read_text(encoding="utf-8")) != manifest:
        raise AssertionError(
            "upstream source manifest drifted; review the differences and replace "
            f"{manifest_path.relative_to(root)} deliberately"
        )

    check_grandeur_coverage(
        read_text(workshop["AMSB"] / GRANDEUR_RELATIVE),
        read_text(workshop["AMSB_LOV"] / GRANDEUR_RELATIVE),
    )
    check_cow_model_remaps(
        read_text(workshop["COW_NOW"] / COW_NOW_GRAPHICS_RELATIVE),
        read_text(root / PAYLOAD_ROOT / COW_MODEL_TRIGGER_RELATIVE),
    )

    outputs = generate_outputs(workshop)
    for relative, data in outputs.items():
        context.write_bytes(relative, data)
    print(f"Generated full-compatch overrides: {len(outputs)} files")
