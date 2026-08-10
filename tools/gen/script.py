"""Paradox-script helpers shared by more than one AGOT runtime generator."""

from __future__ import annotations

import re
from pathlib import Path

from .text import matching_brace, read_source
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
        text,
        pattern,
        replacement,
        label,
        expected,
        flags,
        error_type=RuntimeError,
    )


def balanced_brace_end(text: str, open_index: int) -> int:
    try:
        return matching_brace(text, open_index)
    except ValueError as error:
        raise RuntimeError(
            f"unbalanced block beginning at byte {open_index}"
        ) from error
