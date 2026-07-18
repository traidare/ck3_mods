#!/usr/bin/env python3
"""Regenerate the Long Night+, Submod Core, and DFP animation compatch."""

from __future__ import annotations

import codecs
import os
import re
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def required_environment_path(name: str) -> Path:
    value = os.environ.get(name)
    if not value:
        raise SystemExit(f"{name} is not set")
    return Path(value).expanduser().resolve()


WORKSHOP = required_environment_path("CK3_WORKSHOP_DIR")
AGOT = WORKSHOP / "2962333032"
SUBMOD_CORE = WORKSHOP / "3034473189"
DFP_AGOT = WORKSHOP / "3609763696"
LONG_NIGHT = WORKSHOP / "3766462389"

RELATIVE_ANIMATIONS = Path("gfx/portraits/portrait_animations/animations.txt")
OUTPUT = ROOT / "mods" / "agot_longnight_submodcore_dfp_compatch" / RELATIVE_ANIMATIONS

EXPECTED_DFP_POSES = 197
EXPECTED_MERGED_POSES = 196
EXPECTED_WIGHT_POSES = 5


def read(path: Path) -> str:
    if not path.is_file():
        raise SystemExit(f"missing required source: {path}")
    raw = path.read_bytes()
    if not raw.startswith(codecs.BOM_UTF8):
        raise SystemExit(f"required source is missing its UTF-8 BOM: {path}")
    return raw.decode("utf-8-sig")


def newline_style(text: str) -> str:
    return "\r\n" if "\r\n" in text else "\n"


def normalize_newlines(text: str, newline: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n").replace("\n", newline)


def matching_brace(text: str, opening: int) -> int:
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
    raise ValueError("unclosed brace")


def definition_matches(text: str, name_pattern: str) -> list[re.Match[str]]:
    return list(
        re.finditer(
            rf"(?m)^\t\t(?P<name>{name_pattern})\s*=\s*\{{",
            text,
        )
    )


def definition_span(text: str, name: str) -> tuple[int, int]:
    matches = definition_matches(text, re.escape(name))
    if len(matches) != 1:
        raise ValueError(f"{name}: expected one definition, found {len(matches)}")
    start = matches[0].start()
    opening = text.find("{", start)
    end = matching_brace(text, opening) + 1
    while end < len(text) and text[end] in " \t":
        end += 1
    if text.startswith("\r\n", end):
        end += 2
    elif end < len(text) and text[end] == "\n":
        end += 1
    return start, end


def unique_marker(text: str, marker: str, label: str) -> int:
    count = text.count(marker)
    if count != 1:
        raise ValueError(f"{label}: expected one insertion marker, found {count}")
    return text.index(marker)


def direct_definition_names(text: str, name_pattern: str) -> list[str]:
    return [match.group("name") for match in definition_matches(text, name_pattern)]


def assert_count(text: str, name_pattern: str, expected: int, label: str) -> None:
    count = len(definition_matches(text, name_pattern))
    if count != expected:
        raise ValueError(f"{label}: expected {expected}, found {count}")


def extract_dfp_poses(dfp: str, newline: str) -> tuple[str, set[str]]:
    pose_names = direct_definition_names(dfp, r"CIP_[A-Za-z0-9_]+")
    if len(pose_names) != EXPECTED_DFP_POSES:
        raise ValueError(
            f"DFP poses: expected {EXPECTED_DFP_POSES}, found {len(pose_names)}"
        )
    if len(set(pose_names)) != len(pose_names):
        raise ValueError("DFP poses contain duplicate definition names")

    first_pose = unique_marker(dfp, "\t\tCIP_toast = {", "first DFP pose")
    dfp_newline = newline_style(dfp)
    high_septon_marker = f"\t\t#AGOT Added{dfp_newline}\t\thigh_septon = {{"
    high_septon = unique_marker(dfp, high_septon_marker, "DFP high_septon")
    if first_pose >= high_septon:
        raise ValueError("DFP pose region is not before high_septon")
    poses = dfp[first_pose:high_septon]

    obsolete_start, obsolete_end = definition_span(poses, "CIP_agressive_longsword")
    poses_newline = newline_style(poses)
    removal_start = obsolete_start
    if poses[:obsolete_start].endswith(poses_newline):
        removal_start -= len(poses_newline)
    poses = poses[:removal_start] + poses_newline + poses[obsolete_end:]

    trigger = re.compile(
        r"(?m)^[ \t]*use_longsword_default_trigger\s*=\s*no[ \t]*(?:\r?\n)"
    )
    poses, replacements = trigger.subn("", poses)
    if replacements != 1:
        raise ValueError(
            "generic DFP aggressive pose: expected one obsolete trigger, "
            f"found {replacements}"
        )

    expected_names = set(pose_names) - {"CIP_agressive_longsword"}
    actual_names = set(direct_definition_names(poses, r"CIP_[A-Za-z0-9_]+"))
    if actual_names != expected_names:
        raise ValueError(
            "DFP pose extraction did not preserve the expected definitions"
        )
    return normalize_newlines(poses, newline), expected_names


def extract_core_bow(core: str, newline: str) -> str:
    bow_start, bow_end = definition_span(core, "hold_bow_idle")
    comment = "\t\t##TGC Added"
    comment_start = core.rfind(comment, 0, bow_start)
    if comment_start < 0 or core[comment_start:bow_start].count("\n") > 2:
        raise ValueError("Submod Core bow pose is missing its expected TGC comment")
    return normalize_newlines(core[comment_start:bow_end], newline)


def generate() -> str:
    long_night = read(LONG_NIGHT / RELATIVE_ANIMATIONS)
    dfp = read(DFP_AGOT / RELATIVE_ANIMATIONS)
    core = read(SUBMOD_CORE / RELATIVE_ANIMATIONS)
    newline = newline_style(long_night)

    assert_count(
        long_night,
        r"wight_pose_[A-Za-z0-9_]+",
        EXPECTED_WIGHT_POSES,
        "Long Night+ wight poses",
    )
    assert_count(long_night, r"CIP_[A-Za-z0-9_]+", 0, "Long Night+ DFP poses")
    assert_count(long_night, "hold_long_axe_idle", 1, "AGOT long-axe pose")
    assert_count(core, "hold_bow_idle", 1, "Submod Core bow pose")

    poses, expected_pose_names = extract_dfp_poses(dfp, newline)
    bow = extract_core_bow(core, newline)

    high_septon_marker = f"\t\t#AGOT Added{newline}\t\thigh_septon = {{"
    hold_hammer_marker = f"\t\t#AGOT Added{newline}\t\thold_hammer_idle = {{"
    unique_marker(long_night, high_septon_marker, "Long Night+ high_septon")
    unique_marker(long_night, hold_hammer_marker, "Long Night+ hold_hammer_idle")

    merged = long_night.replace(high_septon_marker, poses + high_septon_marker, 1)
    merged = merged.replace(hold_hammer_marker, bow + newline + hold_hammer_marker, 1)

    merged_pose_names = set(direct_definition_names(merged, r"CIP_[A-Za-z0-9_]+"))
    if merged_pose_names != expected_pose_names:
        raise ValueError("merged file does not contain the expected DFP pose set")
    assert_count(
        merged,
        r"CIP_[A-Za-z0-9_]+",
        EXPECTED_MERGED_POSES,
        "merged DFP poses",
    )
    assert_count(
        merged,
        r"wight_pose_[A-Za-z0-9_]+",
        EXPECTED_WIGHT_POSES,
        "merged wight poses",
    )
    assert_count(merged, "hold_bow_idle", 1, "merged bow pose")
    assert_count(merged, "hold_long_axe_idle", 1, "merged long-axe pose")
    assert_count(
        merged,
        "CIP_agressive_longsword",
        0,
        "obsolete DFP longsword pose",
    )
    active_removed_trigger = re.findall(
        r"(?m)^[ \t]*use_longsword_default_trigger\s*=", merged
    )
    if active_removed_trigger:
        raise ValueError("merged file still has an active removed longsword trigger")
    return merged


def write_atomic(path: Path, content: str) -> bool:
    encoded = codecs.BOM_UTF8 + content.encode("utf-8")
    if path.is_file() and path.read_bytes() == encoded:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb", prefix=f".{path.name}.", dir=path.parent, delete=False
        ) as handle:
            handle.write(encoded)
            temporary = Path(handle.name)
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()
    return True


def main() -> None:
    # AGOT is explicit even though Long Night+ supplies the merge base.
    if not (AGOT / "descriptor.mod").is_file():
        raise SystemExit(f"missing required AGOT dependency: {AGOT}")
    merged = generate()
    changed = write_atomic(OUTPUT, merged)
    action = "wrote" if changed else "unchanged"
    print(
        f"{action}: {OUTPUT.relative_to(ROOT)} "
        f"({EXPECTED_MERGED_POSES} DFP poses, "
        f"{EXPECTED_WIGHT_POSES} wight poses, 1 Submod Core bow pose)"
    )


if __name__ == "__main__":
    try:
        main()
    except ValueError as error:
        raise SystemExit(f"cannot regenerate compatch: {error}") from error
