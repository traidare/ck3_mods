#!/usr/bin/env python3
"""Rebase CaFG cultural MAA boons onto AGOT's final MAA database.

AGOT replaces several vanilla men-at-arms files by filename. CaFG still
instantiates its generic refill effect for types removed by those overrides.
Every removal below is counted so a CaFG update fails loudly.
"""

from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

from ck3mm.generators.text import read_source, replace_exact

ROOT: Path | None = None
MOD_SOURCE: Path | None = None
SOURCE: Path | None = None
MOD_OUTPUT: Path | None = None
OUTPUT: Path | None = None

INVALID_MAA_TYPES = frozenset(
    [
        "abudrar",
        "archers_of_the_nile",
        "ayyar",
        "bondi",
        "bush_hunter",
        "cataphract",
        "druzhina",
        "emishi_horse_archers",
        "gakgung_archers",
        "garudas",
        "gendarme",
        "goedendag",
        "guinea_warrior",
        "horn_warrior",
        "huscarl",
        "hussar",
        "japanese_horse_archers",
        "khandayat",
        "mangudai",
        "maturkan_warriors",
        "metsanvartija",
        "monaspa",
        "mountaineer",
        "mubarizun",
        "mulaththamun",
        "palace_guards",
        "pesilat_warriors",
        "samurai",
        "sarawit",
        "schiltron",
        "shomer",
        "varangian_guards",
        "varangian_veterans",
        "vigmen",
        "zbrojnosh",
    ]
)

INVALID_TRADITIONS = frozenset(
    [
        "tradition_desert_nomads",
        "tradition_hidden_cities",
        "tradition_intensive_farming",
        "tradition_maritime_way_of_life",
        "tradition_saharan_nomads",
        "tradition_tgp_art_of_war",
        "tradition_tgp_barangay_confederations",
        "tradition_tgp_court_machinations",
        "tradition_tgp_fortified_strongholds",
        "tradition_tgp_hydraulic_builders",
        "tradition_tgp_mountain_island",
    ]
)

MAA_CALL = re.compile(
    r"E_kCAFG_generic_cultural_boon_MAA_gift\s*=\s*\{"
    r"[^\r\n]*\bMAA_TYPE\s*=\s*([A-Za-z0-9_]+)"
)
TRADITION_CHECK = re.compile(r"\bhas_cultural_tradition\s*=\s*([A-Za-z0-9_]+)")
WEIGHTED_BRANCH = re.compile(r"^        \d+\s*=\s*\{\s*(?:#.*)?$")
COASTAL_HELPER_CALL = "E_kCAFG_cultural_boon_tradition_fp1_coastal_warriors = yes"


def read_text(path: Path) -> str:
    return read_source(path, normalize_newlines=True)


def write_text(relative: str, text: str, *, root: Path | None = None) -> None:
    path = (OUTPUT if root is None else root) / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8-sig", newline="\n")


def maa_type(line: str) -> str | None:
    match = MAA_CALL.search(line)
    return match.group(1) if match else None


def script_brace_delta(line: str) -> int:
    """Count structural braces, excluding comments and quoted strings."""
    code = line.split("#", 1)[0]
    code = re.sub(r'"(?:\\.|[^"\\])*"', '""', code)
    return code.count("{") - code.count("}")


def weighted_branch(lines: list[str], marker: int) -> tuple[int, int]:
    start = next(
        (
            index
            for index in range(marker, -1, -1)
            if WEIGHTED_BRANCH.match(lines[index].rstrip("\r\n"))
        ),
        None,
    )
    if start is None:
        raise RuntimeError(
            f"CaFG cultural benefit at source line {marker + 1} "
            "has no enclosing weighted branch"
        )

    depth = 0
    for end in range(start, len(lines)):
        depth += script_brace_delta(lines[end])
        if depth == 0:
            if end < marker:
                break
            return start, end + 1
    raise RuntimeError(f"CaFG weighted branch at source line {start + 1} is unbalanced")


def generate_boons() -> None:
    relative = "kei_cafg_cultural_boons_effects.txt"
    lines = read_text(SOURCE / relative).splitlines(keepends=True)
    removed = Counter()
    output: list[str] = []

    for line in lines:
        identifier = maa_type(line)
        if identifier in INVALID_MAA_TYPES:
            removed[identifier] += 1
            continue
        output.append(line)

    expected = {
        "bondi",
        "cataphract",
        "huscarl",
        "varangian_guards",
        "varangian_veterans",
        "vigmen",
    }
    if set(removed) != expected or sum(removed.values()) != 6:
        raise RuntimeError(
            "CaFG cultural-boon helpers: expected six removed MAA calls "
            f"for {sorted(expected)}, found {dict(removed)}"
        )

    text = "".join(output)
    text = replace_exact(
        text,
        """                random_list = {
                    150 = {}
                    50 = {
                        trigger = { NOT = { religion = religion:islam_religion } }
                        add_trait = pilgrim
                    }
                    50 = {
                        trigger = { religion = religion:islam_religion }
                        add_trait = hajjaj
                    }
                }""",
        "                add_trait = pilgrim",
        expected=1,
        label="CaFG AGOT pilgrimage trait",
    )
    text = replace_exact(
        text,
        """            if = {
                limit = { NOT = { knows_language_of_culture = culture:han } }
                learn_language_of_culture = culture:han
            }
            if = {
                limit = { NOT = { has_trait = confucian_education } }
                add_trait = confucian_education
            }
            add_trait_xp = {
                trait = confucian_education
                value = {
                    integer_range = {
                        min = small_lifestyle_random_xp_low
                        max = medium_lifestyle_random_xp_high
                    }
                }
            }
""",
        "",
        expected=1,
        label="CaFG AGOT scholar-official vanilla trait and language",
    )
    text = replace_exact(
        text,
        (
            'CONDITION = "OR = { terrain = plains terrain = steppe '
            'geographical_region = world_steppe }"'
        ),
        'CONDITION = "OR = { terrain = plains terrain = steppe }"',
        expected=1,
        label="CaFG AGOT pastoralist geographical region",
    )
    remaining_invalid = {
        identifier
        for identifier in MAA_CALL.findall(text)
        if identifier in INVALID_MAA_TYPES
    }
    if remaining_invalid:
        raise RuntimeError(
            "CaFG cultural-boon helpers still reference invalid MAA types: "
            f"{sorted(remaining_invalid)}"
        )
    write_text(relative, text)


def generate_benefits() -> None:
    relative = "kei_cafg_cultural_benefits_effects.txt"
    lines = read_text(SOURCE / relative).splitlines(keepends=True)
    invalid_calls = Counter()
    markers: list[int] = []

    for index, line in enumerate(lines):
        identifier = maa_type(line)
        if identifier in INVALID_MAA_TYPES:
            invalid_calls[identifier] += 1
            markers.append(index)
        if any(
            tradition in INVALID_TRADITIONS
            for tradition in TRADITION_CHECK.findall(line)
        ):
            markers.append(index)

    if set(invalid_calls) != INVALID_MAA_TYPES - {
        "bondi",
        "cataphract",
        "varangian_guards",
        "varangian_veterans",
        "vigmen",
    }:
        raise RuntimeError(
            f"CaFG cultural-benefit invalid MAA set changed: {dict(invalid_calls)}"
        )
    if sum(invalid_calls.values()) != 30:
        raise RuntimeError(
            "CaFG cultural benefits: expected 30 invalid MAA calls, "
            f"found {sum(invalid_calls.values())}"
        )

    helper_markers = [
        index for index, line in enumerate(lines) if COASTAL_HELPER_CALL in line
    ]
    if len(helper_markers) != 1:
        raise RuntimeError(
            "CaFG coastal-warriors helper: expected one caller, found "
            f"{len(helper_markers)}"
        )
    markers.extend(helper_markers)

    if len(markers) != 42:
        raise RuntimeError(
            "CaFG cultural benefits: expected 42 invalid branch markers, "
            f"found {len(markers)}"
        )
    branches = {weighted_branch(lines, marker) for marker in markers}
    if len(branches) != 41:
        raise RuntimeError(
            "CaFG cultural benefits: expected 41 removed weighted branches, "
            f"found {len(branches)}"
        )

    for start, end in sorted(branches, reverse=True):
        del lines[start:end]

    text = "".join(lines)
    text = replace_exact(
        text,
        "\t\t\t\t\t\tgeographical_region = world_steppe\n",
        "",
        expected=1,
        label="CaFG AGOT pastoralist benefit geographical region",
    )
    remaining_invalid = {
        identifier
        for identifier in MAA_CALL.findall(text)
        if identifier in INVALID_MAA_TYPES
    }
    remaining_traditions = {
        tradition
        for tradition in TRADITION_CHECK.findall(text)
        if tradition in INVALID_TRADITIONS
    }
    if remaining_invalid or remaining_traditions or COASTAL_HELPER_CALL in text:
        raise RuntimeError(
            "CaFG cultural benefits retain an invalid database branch: "
            f"MAA={sorted(remaining_invalid)}, "
            f"traditions={sorted(remaining_traditions)}"
        )
    write_text(relative, text)


def generate_benefit_values() -> None:
    relative = "common/script_values/kei_cafg_cultural_benefits_values.txt"
    text = read_text(MOD_SOURCE / relative)
    for tradition in (
        "tradition_cultural_primacy",
        "tradition_tgp_inward_perfection",
    ):
        text = replace_exact(
            text,
            f"                has_cultural_tradition = {tradition}\n",
            "",
            expected=1,
            label=f"CaFG AGOT cultural benefit {tradition}",
        )
    text = replace_exact(
        text,
        """    if = {
        limit = {
            has_cultural_tradition = tradition_sinophilic
            scope:char.culture = { has_cultural_pillar = heritage_chinese }
        }
        multiply = 1.5
    }
""",
        "",
        expected=1,
        label="CaFG AGOT Sinophilic cultural benefit",
    )
    invalid = {
        "tradition_cultural_primacy",
        "tradition_tgp_inward_perfection",
        "tradition_sinophilic",
        "heritage_chinese",
    }
    remaining = sorted(identifier for identifier in invalid if identifier in text)
    if remaining:
        raise RuntimeError(
            f"CaFG cultural-benefit values retain AGOT-invalid identifiers: {remaining}"
        )
    write_text(relative, text, root=MOD_OUTPUT)


def generate_disabled_vanilla_overrides() -> None:
    vanilla_definitions = {
        "common/casus_belli_types/99_kei_cafg_replaced_fp3_wars.txt": (
            "fp3_zanj_rebellion_war",
        ),
        "common/scripted_effects/99_kei_cafg_replaced_decisions_effects.txt": (
            "reclaim_britannia_decision_effect",
            "embrace_english_culture_effect",
            "form_portugal_decision_effects",
            "unite_africa_decision_effects",
            "avenge_the_battle_of_tours_decision_effects",
            "become_saoshyant_decision_effect",
            "launch_hungarian_migration_scripted_effect",
        ),
        ("common/scripted_effects/99_kei_cafg_replaced_dlc_fp3_scripted_effects.txt"): (
            "avenge_the_battle_of_nahrawan_scripted_effect",
            "fp3_ending_effects_assertion",
            "fp3_struggle_ending_shia_caliphate_effects",
            "fp3_struggle_ending_vassalize_caliph_effects",
            "fp3_struggle_rekindle_iran_effects",
        ),
    }
    for relative, definitions in vanilla_definitions.items():
        source = read_text(MOD_SOURCE / relative)
        for definition in definitions:
            found = source.count(f"{definition} = {{")
            if found != 1:
                raise RuntimeError(
                    f"CaFG vanilla-only override {relative}: expected one "
                    f"{definition} definition, found {found}"
                )
        write_text(
            relative,
            (
                "# Intentionally empty for AGOT. CaFG copies vanilla-only "
                "definitions that AGOT disables.\n"
            ),
            root=MOD_OUTPUT,
        )


def main() -> None:
    generate_boons()
    generate_benefits()
    generate_benefit_values()
    generate_disabled_vanilla_overrides()
    print(
        "Generated CaFG/AGOT cultural-boon rebase "
        "(35 removed MAA types, 11 removed traditions, 4 runtime identifiers, "
        "3 vanilla-only files disabled)."
    )


if __name__ == "__main__":
    main()
