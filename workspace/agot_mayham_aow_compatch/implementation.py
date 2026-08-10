#!/usr/bin/env python3
"""Generate merged tradition overrides for the Mayham + AoW compatch."""

from __future__ import annotations

import os
import re
import subprocess
import tempfile
from pathlib import Path

from ck3mm.generation import GenerationContext
from ck3mm.generators.text import matching_brace, read_source

ROOT: Path | None = None


def required_environment_path(name: str) -> Path:
    value = os.environ.get(name)
    if not value:
        raise SystemExit(
            f"{name} is not set; load .env through direnv or run inside the dev shell"
        )
    return Path(value).expanduser().resolve()


WORKSHOP: Path | None = None
AGOT: Path | None = None
MAYHAM: Path | None = None
AOW: Path | None = None
OUT: Path | None = None
AOW_UNIQUE_RELATIVE = Path("common/culture/traditions/00_agot_unique_traditions.txt")
AOW_UNIQUE_OUT: Path | None = None

# Each entry is (field, AGOT value, Mayham value). The generator verifies that
# this manifest describes every difference between AGOT and Mayham in the three
# conflicting tradition files before applying the changes to AoW's definitions.
DELTAS: dict[str, dict[str, list[tuple[str, str, str]]]] = {
    "00_agot_realm_traditions.txt": {
        "tradition_agot_insular_marriage": [
            ("same_culture_opinion", "10", "20"),
            ("spouse_opinion", "10", "20"),
        ],
    },
    "00_agot_regional_traditions.txt": {
        "tradition_agot_rushlander": [
            ("opinion_of_liege", "10", "20"),
            ("fellow_vassal_opinion", "10", "20"),
        ],
        "tradition_agot_braavos": [("independent_ruler_opinion", "-10", "-30")],
        "tradition_agot_pentos": [("liege_opinion", "-10", "-30")],
        "tradition_agot_slavers_bay": [("different_faith_opinion", "-10", "-30")],
        "tradition_agot_ghis": [("different_faith_opinion", "-10", "-30")],
        "tradition_agot_vale": [
            ("liege_opinion", "15", "30"),
            ("councillor_opinion", "-35", "-50"),
        ],
    },
    "00_agot_unique_traditions.txt": {
        "tradition_agot_essosi_valyrian": [("different_culture_opinion", "10", "5")],
        "tradition_agot_volantene": [("different_culture_opinion", "10", "5")],
        "tradition_agot_braavosi": [("different_faith_opinion", "10", "5")],
        "tradition_agot_pentoshi": [("courtier_and_guest_opinion", "10", "20")],
        "tradition_agot_tyroshi": [("courtier_opinion", "10", "20")],
        "tradition_agot_lyseni": [("close_relative_opinion", "10", "20")],
        "tradition_agot_hartalari": [("different_culture_opinion", "10", "5")],
        "tradition_agot_lorathi": [("guest_opinion", "10", "20")],
        "tradition_agot_norvoshi": [("religious_vassal_opinion", "10", "20")],
        "tradition_agot_astapori": [("glory_hound_opinion", "10", "20")],
        "tradition_agot_yunkaii": [("parochial_opinion", "10", "20")],
        "tradition_agot_meereenese": [("courtly_opinion", "10", "20")],
        "tradition_agot_mellar": [("same_culture_opinion", "10", "20")],
        "tradition_agot_essari": [("religious_head_opinion", "10", "20")],
        "tradition_agot_noynar": [("religious_head_opinion", "10", "20")],
        "tradition_agot_valyrian_original": [
            ("religious_head_opinion", "10", "20"),
            ("different_faith_opinion", "-10", "-30"),
        ],
        "tradition_agot_sistermen": [("same_culture_opinion", "10", "20")],
        "tradition_agot_crownlander": [("fellow_vassal_opinion", "10", "20")],
        "tradition_agot_clawmen": [("liege_opinion", "10", "20")],
        "tradition_agot_high_valyrian": [("different_culture_opinion", "10", "5")],
        "tradition_agot_western_valyrian": [("different_culture_opinion", "10", "5")],
        "tradition_agot_northern_clans": [("dynasty_opinion", "10", "20")],
        "tradition_agot_crannogmen": [("opinion_of_liege", "10", "20")],
        "tradition_agot_greenblood": [("different_faith_opinion", "10", "20")],
        "tradition_agot_stone_dornish": [("same_culture_opinion", "10", "20")],
        "tradition_agot_first_clans": [("independent_ruler_opinion", "10", "20")],
        "tradition_agot_cave_dweller": [("same_faith_opinion", "10", "20")],
        "tradition_agot_forestmen": [("independent_ruler_opinion", "10", "20")],
        "tradition_agot_hornfoots": [("opinion_of_liege", "10", "20")],
        "tradition_agot_lake_folk": [("close_relative_opinion", "10", "20")],
        "tradition_agot_milkwatermen": [("same_faith_opinion", "10", "20")],
        "tradition_agot_thenns": [("religious_head_opinion", "10", "20")],
        "tradition_agot_stonemen": [("different_culture_opinion", "-150", "-300")],
        "tradition_agot_mandermen": [("courtier_and_guest_opinion", "10", "20")],
        "tradition_agot_honeywiner": [("religious_head_opinion", "10", "20")],
    },
}

# Definitions where AoW still carries an older AGOT block. Emit the current
# AGOT definition so the later-loaded compatch does not undo upstream changes.
# Exact equality checks below make this an explicit rebase, not a blanket
# preference for AGOT.
UPSTREAM_REBASES: dict[str, tuple[str, ...]] = {
    "00_agot_regional_traditions.txt": ("tradition_agot_stormlands",),
    "00_agot_unique_traditions.txt": (
        "tradition_agot_harbormen",
        "tradition_agot_frozen_shoremen",
        "tradition_agot_wolfswood_clansmen",
        "tradition_agot_stoneborn",
    ),
}

# Mayham has balance deltas on definitions that also need the current AGOT
# rebase. Apply them after the current AGOT blocks are selected.
UPSTREAM_REBASE_DELTAS: dict[str, dict[str, list[tuple[str, str, str]]]] = {
    "00_agot_unique_traditions.txt": {
        "tradition_agot_wolfswood_clansmen": [
            ("liege_opinion", "10", "20"),
        ],
        "tradition_agot_stoneborn": [
            ("different_culture_opinion", "-10", "-30"),
        ],
    },
}


def read(path: Path) -> str:
    return read_source(path, normalize_newlines=True)


def definitions(text: str) -> dict[str, str]:
    result: dict[str, str] = {}
    pattern = re.compile(r"(?m)^([A-Za-z0-9_]+)\s*=\s*\{")
    for match in pattern.finditer(text):
        name = match.group(1)
        if name in result:
            raise ValueError(f"duplicate top-level definition: {name}")
        opening = text.find("{", match.start())
        closing = matching_brace(text, opening)
        result[name] = text[match.start() : closing + 1]
    return result


def subblock_span(block: str, key: str) -> tuple[int, int]:
    match = re.search(rf"(?m)^\s*{re.escape(key)}\s*=\s*\{{", block)
    if not match:
        raise ValueError(f"missing nested block {key}")
    opening = block.find("{", match.start())
    return match.start(), matching_brace(block, opening) + 1


def replace_modifier_field(
    block: str, tradition: str, field: str, old: str, new: str
) -> str:
    start, end = subblock_span(block, "character_modifier")
    modifier = block[start:end]
    pattern = re.compile(rf"(?m)^(\s*{re.escape(field)}\s*=\s*)(-?\d+(?:\.\d+)?)(\s*)$")
    matches = list(pattern.finditer(modifier))
    if len(matches) != 1:
        raise ValueError(
            f"{tradition}.{field}: expected one character_modifier field, "
            f"found {len(matches)}"
        )
    if matches[0].group(2) != old:
        raise ValueError(
            f"{tradition}.{field}: expected {old}, found {matches[0].group(2)}"
        )
    modifier = pattern.sub(rf"\g<1>{new}\g<3>", modifier, count=1)
    return block[:start] + modifier + block[end:]


def apply_deltas(block: str, tradition: str, deltas: list[tuple[str, str, str]]) -> str:
    for field, old, new in deltas:
        block = replace_modifier_field(block, tradition, field, old, new)
    return block


def merge_definition(base: str, ours: str, theirs: str, tradition: str) -> str:
    """Three-way merge AoW and current AGOT changes from a reconstructed base."""
    with tempfile.TemporaryDirectory() as directory:
        directory = Path(directory)
        for name, text in (("base", base), ("ours", ours), ("theirs", theirs)):
            (directory / name).write_text(text + "\n", encoding="utf-8")
        result = subprocess.run(
            [
                "git",
                "merge-file",
                "-p",
                str(directory / "ours"),
                str(directory / "base"),
                str(directory / "theirs"),
            ],
            text=True,
            capture_output=True,
        )
    merged = result.stdout
    if result.returncode == 1 and tradition == "tradition_agot_essosi_valyrian":
        conflict = re.compile(
            r"(?ms)^<<<<<<< [^\n]+\n(?P<ours>.*?)"
            r"^\|\|\|\|\|\|\| [^\n]+\n(?P<base>.*?)"
            r"^=======\n(?P<theirs>.*?)^>>>>>>> [^\n]+\n?"
        )
        matches = list(conflict.finditer(merged))
        expected = {
            "ours": (
                "\t\telephant_cavalry_maintenance_mult = -0.10\n"
                "\t\tmonthly_piety_gain_per_dread_mult = 0.1\n"
            ),
            "base": (
                "\t\telephant_cavalry_maintenance_mult = -0.10\n"
                "\t\tmonthly_piety_gain_per_dread_mult = 0.0025\n"
            ),
            "theirs": (
                "\t\tchariot_cavalry_maintenance_mult = -0.10\n"
                "\t\tmonthly_piety_gain_per_dread_mult = 0.0025\n"
            ),
        }
        if len(matches) == 1 and all(
            matches[0].group(side) == value for side, value in expected.items()
        ):
            merged = conflict.sub(
                "\t\tchariot_cavalry_maintenance_mult = -0.10\n"
                "\t\tmonthly_piety_gain_per_dread_mult = 0.1\n",
                merged,
            )
    if result.returncode not in (0, 1) or "<<<<<<<" in merged:
        raise ValueError(
            f"{tradition}: AoW/current-AGOT merge conflict; review upstream changes"
        )
    return merged.rstrip("\n")


def generate_traditions() -> str:
    generated: list[str] = []
    definition_count = 0
    delta_count = 0

    for filename, expected in DELTAS.items():
        relative = Path("common/culture/traditions") / filename
        agot = definitions(read(AGOT / relative))
        mayham = definitions(read(MAYHAM / relative))
        aow = definitions(read(AOW / relative))

        if agot.keys() != mayham.keys():
            raise ValueError(f"{filename}: AGOT and Mayham definition sets differ")
        upstream_rebases = UPSTREAM_REBASES.get(filename, ())
        upstream_rebase_set = set(upstream_rebases)
        changed = {
            name
            for name in agot
            if agot[name] != mayham[name] and name not in upstream_rebase_set
        }
        if changed != set(expected):
            missing = sorted(changed - set(expected))
            stale = sorted(set(expected) - changed)
            raise ValueError(
                f"{filename}: delta manifest drift; unlisted={missing}, unchanged={stale}"
            )

        for tradition in upstream_rebases:
            if tradition not in aow:
                raise ValueError(f"{filename}: AoW is missing {tradition}")
            rebase_deltas = UPSTREAM_REBASE_DELTAS.get(filename, {}).get(tradition, [])
            expected_mayham = apply_deltas(agot[tradition], tradition, rebase_deltas)
            if expected_mayham != mayham[tradition]:
                raise ValueError(
                    f"{filename}: upstream rebase delta drift for {tradition}"
                )
            if agot[tradition] == aow[tradition]:
                raise ValueError(
                    f"{filename}: upstream rebase for {tradition} is no longer needed"
                )
            generated.append(apply_deltas(agot[tradition], tradition, rebase_deltas))
            definition_count += 1
            delta_count += len(rebase_deltas)

        for tradition, deltas in expected.items():
            if tradition not in aow:
                raise ValueError(f"{filename}: AoW is missing {tradition}")
            aow_deltas = [
                (
                    field,
                    agot_value,
                    mayham_value,
                )
                for field, agot_value, mayham_value in deltas
            ]
            reverse_deltas = [
                (field, mayham_value, aow_value)
                for (field, _, mayham_value), (_, aow_value, _) in zip(
                    deltas, aow_deltas, strict=True
                )
            ]
            reconstructed_base = apply_deltas(
                mayham[tradition], tradition, reverse_deltas
            )
            merged = merge_definition(
                reconstructed_base,
                aow[tradition],
                agot[tradition],
                tradition,
            )
            generated.append(apply_deltas(merged, tradition, deltas))
            definition_count += 1
            delta_count += len(deltas)

    if definition_count != 47 or delta_count != 48:
        raise ValueError(
            f"unexpected manifest size: {definition_count} definitions, {delta_count} deltas"
        )

    header = (
        "# Generated by ck3mm from the mod's workspace implementation.\n"
        "# AoW definitions with Mayham's verified balance deltas applied, plus\n"
        "# explicit current-AGOT rebases where both parents retain stale data.\n\n"
    )
    return header + "\n\n".join(generated) + "\n"


def generate_aow_unique_syntax_repair() -> str:
    text = read(AOW / AOW_UNIQUE_RELATIVE)
    old = "\t\treveler_traits_more_valued \n"
    found = text.count(old)
    if found != 1:
        raise ValueError(
            "AoW Arbor tradition syntax repair: expected one malformed "
            f"parameter, found {found}"
        )
    return text.replace(old, "\t\treveler_traits_more_valued = yes\n")


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(generate_traditions(), encoding="utf-8-sig")
    AOW_UNIQUE_OUT.parent.mkdir(parents=True, exist_ok=True)
    AOW_UNIQUE_OUT.write_text(generate_aow_unique_syntax_repair(), encoding="utf-8-sig")
    print(
        f"Generated {OUT.relative_to(ROOT)} "
        "(47 definitions, 48 deltas, 5 upstream rebases)"
    )


def generate(context: GenerationContext) -> None:
    global ROOT, AGOT, MAYHAM, AOW, OUT, AOW_UNIQUE_OUT
    ROOT = context.workspace.root
    AGOT = context.source("agot")
    MAYHAM = context.source("mayham")
    AOW = context.source("armies-of-westeros")
    OUT = context.output_path(
        "common/culture/traditions/zzz_agot_mayham_aow_compatch_traditions.txt"
    )
    AOW_UNIQUE_OUT = context.output_path(
        "common/culture/traditions/00_agot_unique_traditions.txt"
    )
    main()
