#!/usr/bin/env python3
"""Generate the CK3 1.19 runtime rebase for AGOT More Personality Depth."""

from __future__ import annotations

import re
from pathlib import Path

from ck3mm.generation import GenerationContext
from ck3mm.generators.text import matching_brace

ROOT: Path | None = None
SOURCE: Path | None = None
AGOT_TRAITS: Path | None = None
OUTPUT: Path | None = None
OPINION_KEYS = (
    "same_opinion",
    "same_opinion_if_same_faith",
    "opposite_opinion",
)
EXPECTED_TRACK_FIELDS = {
    "same_opinion": 51,
    "same_opinion_if_same_faith": 3,
    "opposite_opinion": 57,
}


def direct_property(block: str, key: str, indent: str) -> str | None:
    match = re.search(
        rf"(?m)^{re.escape(indent)}{key}\s*=\s*([^#\r\n]+?)\s*$",
        block,
    )
    return match.group(1).strip() if match else None


def main() -> None:
    text = SOURCE.read_text(encoding="utf-8-sig")
    agot_traits = AGOT_TRAITS.read_text(encoding="utf-8-sig")
    compatibility_variables = re.findall(
        r"(?m)^@(pos|neg)_compat_(high|medium|low)\s*=\s*-?\d+\s*$",
        agot_traits,
    )
    if len(compatibility_variables) != 6:
        raise RuntimeError(
            "expected six AGOT personality compatibility reader variables, "
            f"found {len(compatibility_variables)}"
        )
    compatibility_header = "\n".join(
        match.group(0)
        for match in re.finditer(
            r"(?m)^@(pos|neg)_compat_(high|medium|low)\s*=\s*-?\d+\s*$",
            agot_traits,
        )
    )
    traits = list(re.finditer(r"(?m)^([A-Za-z_][A-Za-z0-9_]*)\s*=\s*\{", text))
    counts = {key: 0 for key in OPINION_KEYS}
    migrated_traits = 0

    for trait_match in reversed(traits):
        trait_name = trait_match.group(1)
        trait_open = text.index("{", trait_match.start())
        trait_end = matching_brace(text, trait_open)
        trait_block = text[trait_match.start() : trait_end + 1]

        track_match = re.search(r"(?m)^\ttrack\s*=\s*\{", trait_block)
        if not track_match:
            continue
        track_open = trait_block.index("{", track_match.start())
        track_end = matching_brace(trait_block, track_open)
        track_block = trait_block[track_match.start() : track_end + 1]

        present = {
            key: len(
                re.findall(
                    rf"(?m)^[ \t]+{key}\s*=\s*[^#\r\n]+(?:\r?\n|$)",
                    track_block,
                )
            )
            for key in OPINION_KEYS
        }
        if not any(present.values()):
            continue

        middle_match = re.search(r"(?m)^\t\t50\s*=\s*\{", track_block)
        if not middle_match:
            raise RuntimeError(
                f"{trait_name}: opinion-bearing track has no level-50 block"
            )
        middle_open = track_block.index("{", middle_match.start())
        middle_end = matching_brace(track_block, middle_open)
        middle_block = track_block[middle_match.start() : middle_end + 1]

        migrated: list[tuple[str, str]] = []
        for key, found in present.items():
            if not found:
                continue
            counts[key] += found
            value = direct_property(middle_block, key, "\t\t\t")
            if value is None:
                raise RuntimeError(
                    f"{trait_name}: {key} occurs in its track but not at level 50"
                )
            if direct_property(trait_block, key, "\t") is not None:
                raise RuntimeError(f"{trait_name}: refusing to duplicate root {key}")
            migrated.append((key, value))

        repaired_track = track_block
        for key, _value in migrated:
            repaired_track, removed = re.subn(
                rf"(?m)^[ \t]+{key}\s*=\s*[^#\r\n]+(?:\r?\n|$)",
                "",
                repaired_track,
            )
            if removed != present[key]:
                raise RuntimeError(
                    f"{trait_name}: expected to remove {present[key]} "
                    f"{key} fields, removed {removed}"
                )

        root_fields = (
            "\t# Trait opinion fields are invalid inside CK3 1.19 track "
            "modifier blocks.\n"
            + "".join(f"\t{key} = {value}\n" for key, value in migrated)
        )
        track_relative_start = track_match.start()
        track_relative_end = track_end + 1
        trait_block = (
            trait_block[:track_relative_start]
            + root_fields
            + repaired_track
            + trait_block[track_relative_end:]
        )
        text = text[: trait_match.start()] + trait_block + text[trait_end + 1 :]
        migrated_traits += 1

    if counts != EXPECTED_TRACK_FIELDS:
        raise RuntimeError(
            "MPD opinion-track fields changed upstream: "
            f"expected {EXPECTED_TRACK_FIELDS}, found {counts}"
        )
    if migrated_traits != 25:
        raise RuntimeError(
            f"expected 25 opinion-bearing traits, found {migrated_traits}"
        )

    text = (
        compatibility_header
        + "\n\n# Compatibility values copied from current AGOT by the "
        "runtime-rebase generator.\n" + text
    )
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    text = re.sub(r"[ \t]+(?=\r?$)", "", text, flags=re.MULTILINE)
    OUTPUT.write_text(text, encoding="utf-8-sig")
    print(
        "Generated MPD trait rebase: "
        f"{sum(counts.values())} invalid track fields migrated across "
        f"{migrated_traits} traits."
    )


def generate(context: GenerationContext) -> None:
    global SOURCE, AGOT_TRAITS, OUTPUT
    SOURCE = context.source("more-personality-depth")
    AGOT_TRAITS = context.source("agot-traits")
    OUTPUT = context.output_path("common/traits/01_personality_overrides.txt")
    main()
