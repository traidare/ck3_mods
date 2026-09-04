#!/usr/bin/env python3
"""Generate the CK3 1.19 runtime rebase for AGOT More Personality Depth."""

from __future__ import annotations

import re

from gen import GenerationContext
from gen.text import matching_brace, read_source, replace_exact, replace_regex

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

COMPATIBILITY_VARIABLE = re.compile(
    r"(?m)^@(?:pos|neg)_compat_(?:high|medium|low)\s*=\s*-?\d+\s*$"
)

XP_CALCULATOR_RELATIVE = "common/scripted_effects/mpd_xp_calculator.txt"
REPLACED_TRAITS_RELATIVE = "common/traits/99_replaced_traits.txt"
PERSONALITY_OVERRIDES_RELATIVE = "common/traits/01_personality_overrides.txt"

CALCULATOR_ANCHOR = "\nmpd_calculate_trait_xp = {"
CALCULATOR_NOTE = """
# Local repairs applied by the runtime-rebase generator:
#
# - The generic culture weighting is dropped. It reads
#   `$TRAIT$_trait_more_common` / `$TRAIT$_trait_less_common` cultural
#   parameters that AGOT defines for only part of the personality set, and CK3
#   rejects every instantiated call that names a parameter no culture declares.
# - The wet-nurse checks scope through `court_owner ?=` and defer the variable
#   comparison behind `trigger_if`, because a courtless character or an unset
#   task variable is an ordinary state, not an error.
# - Every XP operation names the trait as its track. CK3's shorthand
#   `track = { ... }` form creates one track named after the trait, and an
#   unnamed operation resolves against no track at all.

"""

# The `has_variable` test alone does not keep CK3 from fetching the variable in
# the same block, so the comparison moves inside a `trigger_if` that only runs
# once the variable exists.
COURT_OWNER_GUARD = re.compile(
    r"\t{5}court_owner = \{\n"
    r"\t{6}# Guard: unset variable comparison logs 'Failed to fetch variable' "
    r"errors\n"
    r"\t{6}has_variable = mpd_wn_active_task\n"
    r"\t{6}var:mpd_wn_active_task = (flag:\w+)\n"
)
COURT_OWNER_REPAIR = (
    "\t\t\t\t\tcourt_owner ?= {\n"
    "\t\t\t\t\t\thas_variable = mpd_wn_active_task\n"
    "\t\t\t\t\t\ttrigger_if = {\n"
    "\t\t\t\t\t\t\tlimit = { has_variable = mpd_wn_active_task }\n"
    "\t\t\t\t\t\t\tvar:mpd_wn_active_task = %s\n"
    "\t\t\t\t\t\t}\n"
)
CULTURE_WEIGHT = (
    r"(?m)^\t{4}modifier = \{ add = -?\d+ +"
    r"culture = \{ has_cultural_parameter = \$TRAIT\$_trait_(?:more|less)_common"
    r" \} \}\n"
)
TRAIT_XP_CALL = r"((?:has|add)_trait_xp = \{ trait = \$TRAIT\$) "

REPLACED_TRAITS = """\
# Intentionally replaces Immersive Personalities' same-path paranoid override.
#
# AGOT - More Personality Depth's earlier 01_personality_overrides.txt remains
# the sole paranoid definition and therefore contributes exactly one shorthand
# trait track. Re-declaring that track in a later zzz file makes CK3 accumulate
# two tracks and reject MPD's add_trait_xp calls.
"""
REPLACED_TRAITS_UPSTREAM = ("paranoid",)


def direct_property(block: str, key: str, indent: str) -> str | None:
    match = re.search(rf"(?m)^{re.escape(indent)}{key}\s*=\s*([^#\r\n]+?)\s*$", block)
    return match.group(1).strip() if match else None


def strip_trailing_whitespace(text: str) -> str:
    return re.sub(r"[ \t]+(?=\r?$)", "", text, flags=re.MULTILINE)


def generate_personality_overrides(source: str, agot_traits: str) -> str:
    """Carry MPD's trait overrides across with AGOT's compatibility values."""
    variables = COMPATIBILITY_VARIABLE.findall(agot_traits)
    if len(variables) != 6:
        raise RuntimeError(
            "expected six AGOT personality compatibility reader variables, "
            f"found {len(variables)}"
        )
    header = "\n".join(
        match.group(0) for match in COMPATIBILITY_VARIABLE.finditer(agot_traits)
    )

    track_counts = {key: 0 for key in OPINION_KEYS}
    root_counts = {key: 0 for key in OPINION_KEYS}
    for trait_match in re.finditer(r"(?m)^([A-Za-z_][A-Za-z0-9_]*)\s*=\s*\{", source):
        trait_open = source.index("{", trait_match.start())
        trait_end = matching_brace(source, trait_open)
        trait_block = source[trait_match.start() : trait_end + 1]

        for key in OPINION_KEYS:
            if direct_property(trait_block, key, "\t") is not None:
                root_counts[key] += 1

        track_match = re.search(r"(?m)^\ttrack\s*=\s*\{", trait_block)
        if not track_match:
            continue
        track_open = trait_block.index("{", track_match.start())
        track_end = matching_brace(trait_block, track_open)
        track_block = trait_block[track_match.start() : track_end + 1]
        for key in OPINION_KEYS:
            track_counts[key] += len(
                re.findall(rf"(?m)^[ \t]+{key}\s*=\s*[^#\r\n]+(?:\r?\n|$)", track_block)
            )

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

    return (
        header + "\n\n# Compatibility values copied from current AGOT by the "
        "runtime-rebase generator.\n" + source
    )


def generate_xp_calculator(source: str) -> str:
    """Keep MPD's XP roll callable under AGOT's cultures and CK3 1.19 tracks."""
    label = "mpd_xp_calculator.txt"
    text = replace_exact(
        source,
        CALCULATOR_ANCHOR,
        CALCULATOR_NOTE + CALCULATOR_ANCHOR.lstrip("\n"),
        f"{label} rebase note",
    )
    text = replace_regex(
        text,
        COURT_OWNER_GUARD.pattern,
        lambda match: COURT_OWNER_REPAIR % match.group(1),
        f"{label} wet-nurse task guard",
        expected=7,
    )
    text = replace_regex(
        text, CULTURE_WEIGHT, "", f"{label} culture weights", expected=4
    )
    # The comment headed the pair of lines the culture weighting just lost.
    text = replace_exact(text, "\t\t\t\t# Culture\n", "", f"{label} culture comment")
    return replace_regex(
        text, TRAIT_XP_CALL, r"\1 track = $TRAIT$ ", f"{label} track keys", expected=4
    )


def generate_replaced_traits(upstream: str) -> str:
    """Blank the one Immersive Personalities trait that duplicates MPD's."""
    defined = tuple(
        match.group(1)
        for match in re.finditer(r"(?m)^([A-Za-z_][A-Za-z0-9_]*)\s*=\s*\{", upstream)
    )
    if defined != REPLACED_TRAITS_UPSTREAM:
        raise RuntimeError(
            "Immersive Personalities' replaced-traits file defines "
            f"{defined}, not {REPLACED_TRAITS_UPSTREAM}; blanking it whole would "
            "now drop definitions this playset wants"
        )
    return REPLACED_TRAITS


def generate(context: GenerationContext) -> None:
    source = read_source(
        context.source("more-personality-depth"), normalize_newlines=True
    )
    context.write_text(
        PERSONALITY_OVERRIDES_RELATIVE,
        strip_trailing_whitespace(
            generate_personality_overrides(
                source,
                read_source(context.source("agot-traits"), normalize_newlines=True),
            )
        ),
        encoding="utf-8-sig",
    )
    context.write_text(
        XP_CALCULATOR_RELATIVE,
        strip_trailing_whitespace(
            generate_xp_calculator(
                read_source(
                    context.source("more-personality-depth-calculator"),
                    normalize_newlines=True,
                )
            )
        ),
        encoding="utf-8-sig",
    )
    context.write_text(
        REPLACED_TRAITS_RELATIVE,
        generate_replaced_traits(
            read_source(
                context.source("immersive-personalities-traits"),
                normalize_newlines=True,
            )
        ),
        encoding="utf-8-sig",
    )
