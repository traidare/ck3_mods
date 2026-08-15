#!/usr/bin/env python3
"""Generate the CK3 1.19 runtime rebase for AGOT More Personality Depth."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from gen import GenerationContext
from gen.text import matching_brace


@dataclass(frozen=True, slots=True)
class RunInputs:
    SOURCE: Path
    AGOT_TRAITS: Path
    OUTPUT: Path


OPINION_KEYS = ("same_opinion", "same_opinion_if_same_faith", "opposite_opinion")
EXPECTED_TRACK_FIELDS = {
    "same_opinion": 0,
    "same_opinion_if_same_faith": 0,
    "opposite_opinion": 0,
}
EXPECTED_ROOT_FIELDS = {
    "same_opinion": 17,
    "same_opinion_if_same_faith": 1,
    "opposite_opinion": 19,
}


def direct_property(block: str, key: str, indent: str) -> str | None:
    match = re.search(rf"(?m)^{re.escape(indent)}{key}\s*=\s*([^#\r\n]+?)\s*$", block)
    return match.group(1).strip() if match else None


def main(inputs: RunInputs) -> None:
    text = inputs.SOURCE.read_text(encoding="utf-8-sig")
    agot_traits = inputs.AGOT_TRAITS.read_text(encoding="utf-8-sig")
    compatibility_variables = re.findall(
        r"(?m)^@(pos|neg)_compat_(high|medium|low)\s*=\s*-?\d+\s*$", agot_traits
    )
    if len(compatibility_variables) != 6:
        raise RuntimeError(
            "expected six AGOT personality compatibility reader variables, "
            f"found {len(compatibility_variables)}"
        )
    compatibility_header = "\n".join(
        match.group(0)
        for match in re.finditer(
            r"(?m)^@(pos|neg)_compat_(high|medium|low)\s*=\s*-?\d+\s*$", agot_traits
        )
    )
    traits = list(re.finditer(r"(?m)^([A-Za-z_][A-Za-z0-9_]*)\s*=\s*\{", text))
    track_counts = {key: 0 for key in OPINION_KEYS}
    root_counts = {key: 0 for key in OPINION_KEYS}

    for trait_match in traits:
        trait_open = text.index("{", trait_match.start())
        trait_end = matching_brace(text, trait_open)
        trait_block = text[trait_match.start() : trait_end + 1]

        for key in OPINION_KEYS:
            if direct_property(trait_block, key, "\t") is not None:
                root_counts[key] += 1

        track_match = re.search(r"(?m)^\ttrack\s*=\s*\{", trait_block)
        if not track_match:
            continue
        track_open = trait_block.index("{", track_match.start())
        track_end = matching_brace(trait_block, track_open)
        track_block = trait_block[track_match.start() : track_end + 1]

        present = {
            key: len(
                re.findall(rf"(?m)^[ \t]+{key}\s*=\s*[^#\r\n]+(?:\r?\n|$)", track_block)
            )
            for key in OPINION_KEYS
        }
        for key, found in present.items():
            track_counts[key] += found

    if track_counts != EXPECTED_TRACK_FIELDS:
        raise RuntimeError(
            "MPD opinion fields must remain outside track modifiers: "
            f"expected {EXPECTED_TRACK_FIELDS}, found {track_counts}"
        )
    if root_counts != EXPECTED_ROOT_FIELDS:
        raise RuntimeError(
            "MPD trait-scope opinion fields changed upstream: "
            f"expected {EXPECTED_ROOT_FIELDS}, found {root_counts}"
        )

    text = (
        compatibility_header
        + "\n\n# Compatibility values copied from current AGOT by the "
        "runtime-rebase generator.\n" + text
    )
    inputs.OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    text = re.sub(r"[ \t]+(?=\r?$)", "", text, flags=re.MULTILINE)
    inputs.OUTPUT.write_text(text, encoding="utf-8-sig")
    print(
        "Generated MPD trait rebase: "
        f"verified {sum(root_counts.values())} trait-scope opinion fields."
    )


def generate(context: GenerationContext) -> None:

    SOURCE = context.source("more-personality-depth")
    AGOT_TRAITS = context.source("agot-traits")
    OUTPUT = context.output_path("common/traits/01_personality_overrides.txt")
    inputs = RunInputs(SOURCE=SOURCE, AGOT_TRAITS=AGOT_TRAITS, OUTPUT=OUTPUT)
    main(inputs)
