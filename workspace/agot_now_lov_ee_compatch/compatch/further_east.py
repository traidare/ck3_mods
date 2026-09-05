#!/usr/bin/env python3
"""Rebase the two Further East EEP history repairs onto the v4 map.

The repaired texts are returned rather than written: the lore-government stage
layers its own edits onto exactly these files, so they reach the payload once,
as that stage's output.
"""

from __future__ import annotations

import re

from gen.script import read_text
from gen.text import matching_brace

from .context import RunInputs

TITLE_HISTORY = "history/titles/hist_titles.txt"
PROVINCE_HISTORY = "history/provinces/k_generated.txt"
TARGET_FAITHS = frozenset(("song_nefer", "dothraki_faith", "sarnori_faith"))
EXPECTED_DATED_CAPITALS = 46
EXPECTED_CHURCH_HOLDINGS = 1180
EXPECTED_CONVERSIONS = 410


def remove_dated_capitals(text: str) -> str:
    """Remove capitals only from dated title-history blocks.

    EEP's landed-title files remain the authoritative capital declarations.
    Keeping the date blocks otherwise byte-for-byte intact avoids changing
    holders or government transitions.
    """
    dated = re.compile(r"(?m)^[ \t]*\d{3,5}\.\d+\.\d+\s*=\s*\{")
    capitals = 0
    pieces: list[str] = []
    cursor = 0
    for match in dated.finditer(text):
        opening = text.index("{", match.start())
        end = matching_brace(text, opening) + 1
        pieces.append(text[cursor : match.start()])
        block = text[match.start() : end]
        block, removed = re.subn(r"(?m)^[ \t]*capital\s*=\s*[^\n]+\n", "", block)
        capitals += removed
        pieces.append(block)
        cursor = end
    pieces.append(text[cursor:])
    if capitals != EXPECTED_DATED_CAPITALS:
        raise RuntimeError(
            f"Further East dated-capital count changed: {capitals} != "
            f"{EXPECTED_DATED_CAPITALS}"
        )
    return "".join(pieces)


def rewrite_lay_clergy_temples(text: str) -> str:
    """Use city holdings for targeted-faith generated secondary temples."""
    starts = list(re.finditer(r"(?m)^\d+\s*=\s*\{", text))
    if not starts:
        raise RuntimeError(
            "Further East generated province history has no province blocks"
        )
    church_holding_count = text.count("holding = church_holding")
    if church_holding_count != EXPECTED_CHURCH_HOLDINGS:
        raise RuntimeError(
            "Further East church-holding count changed: "
            f"{church_holding_count} != {EXPECTED_CHURCH_HOLDINGS}"
        )

    output: list[str] = []
    cursor = 0
    conversions = 0
    for match in starts:
        opening = text.index("{", match.start())
        end = matching_brace(text, opening) + 1
        output.append(text[cursor : match.start()])
        block = text[match.start() : end]
        faiths = set(re.findall(r"(?m)^\s*religion\s*=\s*([A-Za-z0-9_]+)\s*$", block))
        if faiths & TARGET_FAITHS and "holding = church_holding" in block:
            block, changed = re.subn(
                r"(?m)^(\s*holding\s*=\s*)church_holding\s*$",
                r"\1city_holding",
                block,
            )
            if changed != 1:
                raise RuntimeError(
                    f"{match.group().strip()}: expected one church holding, found {changed}"
                )
            conversions += 1
        output.append(block)
        cursor = end
    output.append(text[cursor:])
    if conversions != EXPECTED_CONVERSIONS:
        raise RuntimeError(
            f"Further East lay-clergy conversions changed: {conversions} != "
            f"{EXPECTED_CONVERSIONS}"
        )
    return "".join(output)


def rebase(inputs: RunInputs) -> dict[str, str]:
    """Return the repaired Further East history files, keyed by payload path."""
    source = inputs["EEP"]
    return {
        TITLE_HISTORY: remove_dated_capitals(read_text(source / TITLE_HISTORY)),
        PROVINCE_HISTORY: rewrite_lay_clergy_temples(
            read_text(source / PROVINCE_HISTORY)
        ),
    }
