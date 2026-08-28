"""Paradox-script transformations shared by repair domains."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

from gen.script import balanced_brace_end, read_text
from gen.text import matching_brace, replace_exact

from .context import RunInputs


def remove_enclosing_block(
    text: str, *, marker: str, block_name: str, label: str
) -> str:
    """Remove the one named script block that contains ``marker``."""
    if text.count(marker) != 1:
        raise RuntimeError(
            f"{label}: expected one marker {marker!r}, found {text.count(marker)}"
        )
    marker_index = text.index(marker)
    candidates = list(
        re.finditer(
            rf"(?m)^[ \t]*{re.escape(block_name)}\s*=\s*\{{", text[:marker_index]
        )
    )
    if not candidates:
        raise RuntimeError(f"{label}: no enclosing {block_name} block")
    block_match = candidates[-1]
    opening = text.index("{", block_match.start())
    end = balanced_brace_end(text, opening)
    if marker_index > end:
        raise RuntimeError(f"{label}: nearest {block_name} does not contain marker")
    if end + 1 < len(text) and text[end + 1] == "\n":
        end += 1
    return text[: block_match.start()] + text[end + 1 :]


def remove_if_block_for_artifact_modifier(
    text: str, modifier: str, *, label: str
) -> str:
    marker = f"limit = {{ has_artifact_modifier = {modifier} }}"
    marker_count = text.count(marker)
    if marker_count != 1:
        raise RuntimeError(
            f"{label}: expected one {modifier} upgrade limit, found {marker_count}"
        )
    marker_index = text.index(marker)
    candidates = list(re.finditer(r"(?m)^[ \t]*if\s*=\s*\{", text[:marker_index]))
    if not candidates:
        raise RuntimeError(f"{label}: no enclosing if block for {modifier}")
    block_match = candidates[-1]
    open_index = text.index("{", block_match.start())
    end_index = balanced_brace_end(text, open_index)
    if marker_index >= end_index:
        raise RuntimeError(f"{label}: nearest if block did not contain {modifier}")
    if end_index + 1 < len(text) and text[end_index + 1] == "\n":
        end_index += 1
    return text[: block_match.start()] + text[end_index + 1 :]


def unwrap_unconditional_random_pool_ifs(
    text: str, *, expected: int, label: str
) -> str:
    """Remove invalid if wrappers whose sole child is a random-pool effect."""
    pattern = re.compile(
        r"(?m)^[ \t]*if\s*=\s*\{\n[ \t]*random_pool_character\s*=\s*\{"
    )
    replacements: list[tuple[int, int, str]] = []
    for match in pattern.finditer(text):
        if any(start <= match.start() < end for start, end, _ in replacements):
            continue
        if_open = text.find("{", match.start(), match.end())
        if_end = balanced_brace_end(text, if_open)
        child_start = text.find("random_pool_character", if_open, match.end())
        child_open = text.find("{", child_start, match.end())
        child_end = balanced_brace_end(text, child_open)
        if text[child_end + 1 : if_end].strip():
            raise RuntimeError(
                f"{label}: unconditional if contains more than its random pool"
            )
        replacement = text[if_open + 1 : child_end + 1].lstrip("\r\n")
        replacements.append((match.start(), if_end + 1, replacement))

    if len(replacements) != expected:
        raise RuntimeError(
            f"{label}: expected {expected} unconditional random-pool if "
            f"wrapper(s), found {len(replacements)}"
        )
    for start, end, replacement in reversed(replacements):
        text = f"{text[:start]}{replacement}{text[end:]}"
    return text


def game_root(inputs: RunInputs) -> Path:
    """Return the CK3 installation root declared as this mod's game source."""
    if inputs.GAME_ROOT is None:
        raise RuntimeError("game_root is only available while ck3mm runs the generator")
    return inputs.GAME_ROOT


def guard_scene_culture_triggers(text: str, *, expected: int, label: str) -> str:
    """Return scene-culture definitions guarded against a missing court owner."""
    keys = re.findall(r"(?m)^([A-Za-z0-9_]+)\s*=\s*\{", text)
    if len(keys) != expected:
        raise RuntimeError(
            f"{label}: expected {expected} scene culture(s), found {len(keys)}"
        )

    marker = "\ttrigger = {\n"
    suffix = "\t}\n}"
    for key in keys:
        block = extract_top_level_block(text, key)
        marker_index = block.find(marker)
        if marker_index < 0 or not block.endswith(suffix):
            raise RuntimeError(f"{label}: unexpected trigger structure for {key}")
        body_start = marker_index + len(marker)
        body_end = len(block) - len(suffix)
        body = block[body_start:body_end]
        indented_body = "".join(
            f"\t{line}" if line.strip() else line
            for line in body.splitlines(keepends=True)
        )
        guarded = (
            f"{block[:body_start]}"
            "\t\t# Scene selection is briefly queried without a valid court "
            "owner during cleanup.\n"
            "\t\ttrigger_if = {\n"
            "\t\t\tlimit = { exists = root }\n"
            f"{indented_body}"
            "\t\t}\n"
            "\t\ttrigger_else = { always = no }\n"
            "\t}\n"
            "}"
        )
        text = text.replace(block, guarded, 1)
    return text


def assert_source_block_hash(
    text: str, key: str, expected_hash: str, *, label: str
) -> str:
    """Return a pinned top-level block, failing closed on upstream drift."""
    block = extract_top_level_block(text, key)
    actual_hash = hashlib.sha256(block.encode()).hexdigest()
    if actual_hash != expected_hash:
        raise RuntimeError(
            f"{label} changed: expected {expected_hash}, found {actual_hash}"
        )
    return block


def assert_source_file_hash(path: Path, expected_hash: str, *, label: str) -> None:
    """Fail closed when a whole-file rebase parent changes."""
    actual_hash = hashlib.sha256(path.read_bytes()).hexdigest()
    if actual_hash != expected_hash:
        raise RuntimeError(
            f"{label} changed: expected {expected_hash}, found {actual_hash}"
        )


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


def replace_numbered_branch_with_constant(
    text: str, number: int, value: bool, *, label: str
) -> str:
    pattern = re.compile(rf"(?m)^([ \t]*){number}\s*=\s*\{{")
    matches = list(pattern.finditer(text))
    if len(matches) != 1:
        raise RuntimeError(
            f"{label}: expected one switch branch {number}, found {len(matches)}"
        )
    match = matches[0]
    open_index = text.index("{", match.start())
    end_index = balanced_brace_end(text, open_index)
    replacement = (
        f"{match.group(1)}{number} = {{ always = {'yes' if value else 'no'} }}"
    )
    return text[: match.start()] + replacement + text[end_index + 1 :]


def top_level_block_keys(text: str) -> list[str]:
    return [
        match.group(1) for match in re.finditer(r"(?m)^([A-Za-z_]\w*)\s*=\s*\{", text)
    ]


def rebase_additional_models_scene_guards(inputs: RunInputs, text: str) -> str:
    """Carry current Additional Models exclusions into the later LoV compatch.

    The compatch replaces Additional Models' whole scene-culture file, so every
    generic scene Additional Models keeps out of its own throne rooms has to be
    kept out again here. The guarded set is read from Additional Models rather
    than listed, so an upstream scene gaining or losing its exclusion follows
    automatically.
    """
    relative = "gfx/court_scene/scene_cultures/00_default_cultures.txt"
    additional_models = read_text(inputs.WORKSHOP / "3319354609" / relative)
    guarded = [
        key
        for key in top_level_block_keys(additional_models)
        if "amsb_has_throne_room = no"
        in extract_top_level_block(additional_models, key)
    ]
    if not guarded:
        raise RuntimeError(
            "Additional Models no longer excludes any generic scene; re-audit "
            "whether this rebase is still needed"
        )
    for key in guarded:
        if key not in top_level_block_keys(text):
            raise RuntimeError(
                f"Additional Models/AGOT+/LoV compatch drops guarded scene {key}"
            )
        compatch_block = extract_top_level_block(text, key)
        amsb_guard_count = compatch_block.count("amsb_has_throne_room = no")
        if amsb_guard_count > 1:
            raise RuntimeError(
                f"Additional Models/AGOT+/LoV compatch duplicates its AMSB "
                f"guard for {key}"
            )
        if amsb_guard_count == 1:
            # The compatch can carry the exclusion itself; keep its version.
            continue
        guarded_block = replace_exact(
            compatch_block,
            "\t\tagot_has_throne_room = no\n",
            "\t\tagot_has_throne_room = no\n\t\tamsb_has_throne_room = no\n",
            expected=1,
            label=f"Additional Models scene exclusion for {key}",
        )
        text = text.replace(compatch_block, guarded_block, 1)
    for key in guarded:
        if extract_top_level_block(text, key).count("amsb_has_throne_room = no") != 1:
            raise RuntimeError(
                f"Additional Models/AGOT+/LoV scene {key}: AMSB exclusion not "
                "active after rebase"
            )
    return text
