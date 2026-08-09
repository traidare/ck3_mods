"""Shared text-rewriting helpers for CK3 source generators."""

from __future__ import annotations

import re
from codecs import BOM_UTF8
from pathlib import Path


def read_source(
    path: Path,
    *,
    require_bom: bool = False,
    normalize_newlines: bool = False,
) -> str:
    """Read a UTF-8 source file with optional BOM and newline requirements."""
    if not path.is_file():
        raise ValueError(f"missing required source: {path}")
    raw = path.read_bytes()
    if require_bom and not raw.startswith(BOM_UTF8):
        raise ValueError(f"required source is missing its UTF-8 BOM: {path}")
    text = raw.decode("utf-8-sig")
    if normalize_newlines:
        return text.replace("\r\n", "\n").replace("\r", "\n")
    return text


def replace_exact(
    text: str,
    old: str,
    new: str,
    label: str,
    expected: int = 1,
) -> str:
    """Replace an exact source fragment only when its count is deliberate."""
    count = text.count(old)
    if count != expected:
        raise ValueError(
            f"{label}: expected {expected} exact occurrence(s), found {count}"
        )
    return text.replace(old, new)


def replace_regex(
    text: str,
    pattern: str,
    replacement: str,
    label: str,
    expected: int = 1,
    flags: int = 0,
    error_type: type[Exception] = ValueError,
) -> str:
    """Replace a regex fragment only when its match count is deliberate."""
    result, count = re.subn(pattern, replacement, text, flags=flags)
    if count != expected:
        raise error_type(f"{label}: expected {expected} regex match(es), found {count}")
    return result


def matching_brace(text: str, opening: int) -> int:
    """Find a Paradox-script block end while ignoring comments and strings."""
    if not 0 <= opening < len(text) or text[opening] != "{":
        raise ValueError(f"expected opening brace at offset {opening}")

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
    raise ValueError(f"unterminated block starting at offset {opening}")


def definition_span(
    text: str,
    name: str,
    *,
    indent: str = r"[ \t]*",
    consume_line_end: bool = False,
) -> tuple[int, int]:
    """Return the source span of one named top-level-style definition."""
    matches = list(
        re.finditer(
            rf"(?m)^{indent}{re.escape(name)}\s*=\s*\{{",
            text,
        )
    )
    if len(matches) != 1:
        raise ValueError(f"{name}: expected one definition, found {len(matches)}")

    start = matches[0].start()
    opening = text.find("{", start)
    end = matching_brace(text, opening) + 1
    if consume_line_end:
        while end < len(text) and text[end] in " \t":
            end += 1
        if text.startswith("\r\n", end):
            end += 2
        elif end < len(text) and text[end] == "\n":
            end += 1
    return start, end


def unique_marker(text: str, marker: str, label: str) -> int:
    """Return the only insertion marker occurrence."""
    count = text.count(marker)
    if count != 1:
        raise ValueError(f"{label}: expected one insertion marker, found {count}")
    return text.index(marker)
