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


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / ".ignored/CK3_workshop/3206891770/common/scripted_effects"
OUTPUT = ROOT / "mods/cafg_agot_compatch/common/scripted_effects"

INVALID_MAA_TYPES = frozenset(
    """
    abudrar
    archers_of_the_nile
    ayyar
    bondi
    bush_hunter
    cataphract
    druzhina
    emishi_horse_archers
    gakgung_archers
    garudas
    gendarme
    goedendag
    guinea_warrior
    horn_warrior
    huscarl
    hussar
    japanese_horse_archers
    khandayat
    mangudai
    maturkan_warriors
    metsanvartija
    monaspa
    mountaineer
    mubarizun
    mulaththamun
    palace_guards
    pesilat_warriors
    samurai
    sarawit
    schiltron
    shomer
    varangian_guards
    varangian_veterans
    vigmen
    zbrojnosh
    """.split()
)

INVALID_TRADITIONS = frozenset(
    """
    tradition_desert_nomads
    tradition_hidden_cities
    tradition_intensive_farming
    tradition_maritime_way_of_life
    tradition_saharan_nomads
    tradition_tgp_art_of_war
    tradition_tgp_barangay_confederations
    tradition_tgp_court_machinations
    tradition_tgp_fortified_strongholds
    tradition_tgp_hydraulic_builders
    tradition_tgp_mountain_island
    """.split()
)

MAA_CALL = re.compile(
    r"E_kCAFG_generic_cultural_boon_MAA_gift\s*=\s*\{"
    r"[^\r\n]*\bMAA_TYPE\s*=\s*([A-Za-z0-9_]+)"
)
TRADITION_CHECK = re.compile(
    r"\bhas_cultural_tradition\s*=\s*([A-Za-z0-9_]+)"
)
WEIGHTED_BRANCH = re.compile(r"^        \d+\s*=\s*\{\s*(?:#.*)?$")
COASTAL_HELPER_CALL = (
    "E_kCAFG_cultural_boon_tradition_fp1_coastal_warriors = yes"
)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def write_text(relative: str, text: str) -> None:
    path = OUTPUT / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8-sig", newline="\n")


def maa_type(line: str) -> str | None:
    match = MAA_CALL.search(line)
    return match.group(1) if match else None


def replace_exact(
    text: str,
    old: str,
    new: str,
    *,
    expected: int,
    label: str,
) -> str:
    found = text.count(old)
    if found != expected:
        raise RuntimeError(
            f"{label}: expected {expected} exact source match(es), "
            f"found {found}"
        )
    return text.replace(old, new)


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
    raise RuntimeError(
        f"CaFG weighted branch at source line {start + 1} is unbalanced"
    )


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
            "CaFG cultural-benefit invalid MAA set changed: "
            f"{dict(invalid_calls)}"
        )
    if sum(invalid_calls.values()) != 30:
        raise RuntimeError(
            "CaFG cultural benefits: expected 30 invalid MAA calls, "
            f"found {sum(invalid_calls.values())}"
        )

    helper_markers = [
        index
        for index, line in enumerate(lines)
        if COASTAL_HELPER_CALL in line
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
    if (
        remaining_invalid
        or remaining_traditions
        or COASTAL_HELPER_CALL in text
    ):
        raise RuntimeError(
            "CaFG cultural benefits retain an invalid database branch: "
            f"MAA={sorted(remaining_invalid)}, "
            f"traditions={sorted(remaining_traditions)}"
        )
    write_text(relative, text)


def main() -> None:
    generate_boons()
    generate_benefits()
    print(
        "Generated CaFG/AGOT cultural-boon rebase "
        "(35 removed MAA types, 11 removed traditions)."
    )


if __name__ == "__main__":
    main()
