#!/usr/bin/env python3
"""Generate the narrow final overrides needed by the AGOT playset."""

from __future__ import annotations

import json
import re
from pathlib import Path

from gen import GenerationContext
from gen.hashing import sha256_file
from gen.sources import canonical_source_path
from gen.text import matching_brace, read_source

WORKSHOP_IDS = {"NOW": "3664900993", "SEASONS_BRIDGE": "3766038754"}
SOURCE_RELATIVES = {
    "NOW": Path("common/landed_titles/01_agot_landed_titles.txt"),
    "SEASON_EVENTS": Path("events/lov_season_events.txt"),
    "SEASON_FX": Path("gfx/FX/province_effects.fxh"),
    "SEASON_REGIONS": Path("map_data/geographical_regions/north_sans_neck.txt"),
}
OUTPUT_RELATIVES = {
    "SEASON_EVENTS": SOURCE_RELATIVES["SEASON_EVENTS"],
    "SEASON_FX": SOURCE_RELATIVES["SEASON_FX"],
    "SEASON_REGIONS": SOURCE_RELATIVES["SEASON_REGIONS"],
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
    return {
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
            "events": "start DoD historical starts in autumn",
            "shader": "share the AGOT skip threshold with vertex shaders",
            "regions": "rebase NOW tokens and cover LoV cleanup regions without ruins",
        },
    }


def generate(context: GenerationContext) -> None:
    root = context.workspace_root
    workshop_root = context.workshop_root("agot-now", "seasons-bridge")
    workshop = {
        "NOW": context.source("agot-now"),
        "SEASONS_BRIDGE": context.source("seasons-bridge"),
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

    outputs = generate_outputs(workshop)
    for relative, data in outputs.items():
        context.write_bytes(relative, data)
    print(f"Generated full-compatch overrides: {len(outputs)} files")
