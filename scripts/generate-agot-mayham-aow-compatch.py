#!/usr/bin/env python3
"""Generate merged tradition overrides for the Mayham + AoW compatch."""

from __future__ import annotations

import os
import re
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def required_environment_path(name: str) -> Path:
    value = os.environ.get(name)
    if not value:
        raise SystemExit(
            f"{name} is not set; load .env through direnv or run inside the dev shell"
        )
    return Path(value).expanduser().resolve()


WORKSHOP = required_environment_path("CK3_WORKSHOP_DIR")
AGOT = WORKSHOP / "2962333032"
MAYHAM = WORKSHOP / "3352171144"
AOW = WORKSHOP / "2966543745"
OUT = (
    ROOT
    / "mods"
    / "agot_mayham_aow_compatch"
    / "common"
    / "culture"
    / "traditions"
    / "zzz_agot_mayham_aow_compatch_traditions.txt"
)

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
        "tradition_agot_andalos": [("different_faith_opinion", "-35", "-30")],
        "tradition_agot_braavos": [("independent_ruler_opinion", "-10", "-30")],
        "tradition_agot_religious_fc": [("different_faith_opinion", "-35", "-30")],
        "tradition_agot_pentos": [("liege_opinion", "-10", "-30")],
        "tradition_agot_doom": [("religious_vassal_opinion", "-35", "-30")],
        "tradition_agot_slavers_bay": [("different_faith_opinion", "-10", "-30")],
        "tradition_agot_ghis": [("different_faith_opinion", "-10", "-30")],
        "tradition_agot_vale": [
            ("liege_opinion", "15", "30"),
            ("councillor_opinion", "-35", "-50"),
        ],
        "tradition_agot_blackwater_bay": [("zealot_opinion", "-35", "-50")],
        "tradition_agot_ironmen": [("different_faith_opinion", "-35", "-50")],
        "tradition_agot_westerlands": [("general_opinion", "-35", "-50")],
        "tradition_agot_dorne": [("different_culture_opinion", "-35", "-50")],
        "tradition_agot_reach": [("different_faith_opinion", "-35", "-50")],
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
        "tradition_agot_stoneborn": [("different_culture_opinion", "-10", "-50")],
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

# Definitions where Mayham and AoW still carry an older, identical AGOT block.
# Emit the current AGOT definition so the later-loaded compatch does not undo
# upstream changes. Exact equality checks below make this an explicit rebase,
# not a blanket preference for AGOT.
UPSTREAM_REBASES: dict[str, tuple[str, ...]] = {
    "00_agot_regional_traditions.txt": ("tradition_agot_stormlands",),
    "00_agot_unique_traditions.txt": (
        "tradition_agot_frozen_shoremen",
        "tradition_agot_harbormen",
        "tradition_agot_wolfswood_clansmen",
    ),
}

# AGOT 0.4.40 changed four fields that Mayham deliberately overrides. AoW
# still has the older AGOT values, so record those separate source values when
# applying Mayham's final value to AoW's otherwise richer definitions.
AOW_BASE_VALUES: dict[tuple[str, str], str] = {
    ("tradition_agot_andalos", "different_faith_opinion"): "-10",
    ("tradition_agot_religious_fc", "different_faith_opinion"): "-10",
    ("tradition_agot_doom", "religious_vassal_opinion"): "-10",
    ("tradition_agot_stoneborn", "different_culture_opinion"): "-35",
}


def read(path: Path) -> str:
    if not path.is_file():
        raise SystemExit(f"missing required source: {path}")
    return path.read_text(encoding="utf-8-sig")


def matching_brace(text: str, opening: int) -> int:
    depth = 0
    quoted = False
    escaped = False
    comment = False
    for index in range(opening, len(text)):
        char = text[index]
        if comment:
            if char == "\n":
                comment = False
            continue
        if quoted:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                quoted = False
            continue
        if char == "#":
            comment = True
        elif char == '"':
            quoted = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return index
    raise ValueError("unclosed brace")


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


def generate() -> str:
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
        upstream_rebases = set(UPSTREAM_REBASES.get(filename, ()))
        changed = {
            name
            for name in agot
            if agot[name] != mayham[name] and name not in upstream_rebases
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
            if mayham[tradition] != aow[tradition]:
                raise ValueError(
                    f"{filename}: Mayham and AoW no longer agree on {tradition}"
                )
            if agot[tradition] == mayham[tradition]:
                raise ValueError(
                    f"{filename}: upstream rebase for {tradition} is no longer needed"
                )
            generated.append(agot[tradition])
            definition_count += 1

        for tradition, deltas in expected.items():
            if tradition not in aow:
                raise ValueError(f"{filename}: AoW is missing {tradition}")
            aow_deltas = [
                (
                    field,
                    AOW_BASE_VALUES.get((tradition, field), agot_value),
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

    if definition_count != 55 or delta_count != 55:
        raise ValueError(
            f"unexpected manifest size: {definition_count} definitions, {delta_count} deltas"
        )

    header = (
        "# Generated by scripts/generate-agot-mayham-aow-compatch.py\n"
        "# AoW definitions with Mayham's verified balance deltas applied, plus\n"
        "# explicit current-AGOT rebases where both parents retain stale data.\n\n"
    )
    return header + "\n\n".join(generated) + "\n"


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(generate(), encoding="utf-8-sig")
    print(
        f"Generated {OUT.relative_to(ROOT)} "
        "(55 definitions, 55 deltas, 4 upstream rebases)"
    )


if __name__ == "__main__":
    main()
