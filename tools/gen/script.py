"""Paradox-script helpers shared by more than one AGOT runtime generator."""

from __future__ import annotations

import re
from pathlib import Path

from .text import matching_brace, read_source, replace_exact
from .text import replace_regex as shared_replace_regex


def read_text(path: Path) -> str:
    return read_source(path, normalize_newlines=True)


def write_text(
    root: Path,
    relative: str,
    text: str,
    *,
    preserve_trailing_whitespace: bool = False,
    force_newline: str | None = None,
    with_bom: bool = True,
) -> None:
    target = root / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    if force_newline is not None:
        newline = force_newline
    else:
        if not preserve_trailing_whitespace:
            text = re.sub(r"[ \t]+(?=\r?$)", "", text, flags=re.MULTILINE)
        newline = ""
    encoding = "utf-8-sig" if with_bom else "utf-8"
    target.write_text(text, encoding=encoding, newline=newline)


def normalize_rebased_source(text: str) -> str:
    """Keep full-file rebases clean without changing their script tokens."""
    text = re.sub(r" +\t", "\t", text)
    return text.rstrip() + "\n"


def replace_regex(
    text: str,
    pattern: str,
    replacement: str,
    *,
    expected: int,
    label: str,
    flags: int = 0,
) -> str:
    return shared_replace_regex(
        text, pattern, replacement, label, expected, flags, error_type=RuntimeError
    )


def balanced_brace_end(text: str, open_index: int) -> int:
    try:
        return matching_brace(text, open_index)
    except ValueError as error:
        raise RuntimeError(
            f"unbalanced block beginning at byte {open_index}"
        ) from error


def extract_top_level_block(text: str, key: str) -> str:
    match = re.search(rf"(?m)^{re.escape(key)}\s*=\s*\{{", text)
    if not match:
        raise RuntimeError(f"top-level block not found: {key}")
    opening = text.find("{", match.start(), match.end())
    try:
        end = matching_brace(text, opening)
    except ValueError as error:
        raise RuntimeError(f"unbalanced top-level block: {key}") from error
    return text[match.start() : end + 1]


def guard_event_deaths(
    text: str, event_key: str, *, expected: int, skip_tooltips: bool = False
) -> str:
    """Let AGOT: Canon Enforcement spare its protected characters in one event.

    Every `death` effect in the event is wrapped, rather than named branches,
    so an upstream release that adds or drops a lethal outcome fails the
    expected count instead of leaving the new one unguarded. Only events whose
    deaths are accidental belong here; murder, execution and poisoning are
    chosen deaths and stay reachable.

    The guard trigger is defined by the AGOT: Canon Enforcement module.
    """
    block = extract_top_level_block(text, event_key)
    return replace_exact(
        text,
        block,
        guard_deaths(
            block, label=event_key, expected=expected, skip_tooltips=skip_tooltips
        ),
        f"{event_key} canon-enforcement guard",
        expected=1,
    )


def guard_deaths(
    block: str, *, label: str, expected: int, skip_tooltips: bool = False
) -> str:
    """Wrap every `death` effect in one script block with the canon guard.

    Takes a block rather than an event key, so callers holding a sub-block can
    guard it without the surrounding event.

    `skip_tooltips` leaves deaths inside `show_as_tooltip` alone, and which way
    it should go is a per-event judgement rather than a rule. A tooltip that
    previews a death the event goes on to inflict has to be guarded too, or it
    promises an outcome the guard then withholds; a tooltip that reports a death
    already resolved elsewhere (`limit = { is_alive = no }`, as MFA's pas d'armes
    events do) must not be, because guarding it would suppress the report of a
    death that happened.
    """
    matches = list(re.finditer(r"(?m)^([ \t]*)death\s*=\s*\{", block))
    if skip_tooltips:
        tooltips = [
            (match.start(), balanced_brace_end(block, block.index("{", match.start())))
            for match in re.finditer(r"(?m)^[ \t]*show_as_tooltip\s*=\s*\{", block)
        ]
        matches = [
            match
            for match in matches
            if not any(start < match.start() < end for start, end in tooltips)
        ]
    if len(matches) != expected:
        raise RuntimeError(
            f"{label}: expected {expected} death effect(s) to guard, "
            f"found {len(matches)}"
        )

    guarded = block
    for match in reversed(matches):
        indent = match.group(1)
        opening = guarded.index("{", match.start())
        end = balanced_brace_end(guarded, opening)
        body = "\n".join(
            f"\t{line}" if line.strip() else line
            for line in guarded[match.start() : end + 1].splitlines()
        )
        guarded = (
            guarded[: match.start()]
            + f"{indent}if = {{\n"
            + f"{indent}\tlimit = {{ agot_ce_event_death_protected_trigger = no }}\n"
            + f"{body}\n"
            + f"{indent}}}"
            + guarded[end + 1 :]
        )
    return guarded
