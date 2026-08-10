#!/usr/bin/env python3
"""Merge the DFP AGOT portrait poses into Long Night+'s animation file.

The payload is one file, so an upstream change to either parent has to fail
loudly rather than silently produce a stale whole-file override.
"""

from __future__ import annotations

import codecs
import hashlib
import re
from pathlib import Path

from ck3mm.generation import GenerationContext
from ck3mm.generators.text import (
    assert_count,
    direct_definition_names,
    nested_definition_span,
    newline_style,
    normalize_newlines,
    read_source,
    strip_trailing_whitespace,
    unique_marker,
)

DFP_AGOT: Path | None = None
STANDALONE_LONG_NIGHT: Path | None = None

RELATIVE_ANIMATIONS = Path("gfx/portraits/portrait_animations/animations.txt")

EXPECTED_DFP_POSES = 197
EXPECTED_MERGED_POSES = 196
EXPECTED_WIGHT_POSES = 5
EXPECTED_DFP_ANIMATIONS_SHA256 = (
    "8ddcb0ba720c236d6913779d924203d5105897c63251224b64e931e272f6a65c"
)


def read(path: Path) -> str:
    return read_source(path, require_bom=True)


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

    obsolete_start, obsolete_end = nested_definition_span(
        poses, "CIP_agressive_longsword"
    )
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


def merged_animations() -> str:
    long_night = read(STANDALONE_LONG_NIGHT / RELATIVE_ANIMATIONS)
    dfp_path = DFP_AGOT / RELATIVE_ANIMATIONS
    if not dfp_path.is_file():
        raise ValueError(f"missing required DFP AGOT source: {dfp_path}")
    dfp_bytes = dfp_path.read_bytes()
    actual_hash = hashlib.sha256(dfp_bytes).hexdigest()
    if actual_hash != EXPECTED_DFP_ANIMATIONS_SHA256:
        raise ValueError(
            "DFP AGOT animations changed upstream: expected "
            f"{EXPECTED_DFP_ANIMATIONS_SHA256}, found {actual_hash}"
        )
    dfp = read(dfp_path)
    newline = newline_style(long_night)

    assert_count(
        long_night,
        r"wight_pose_[A-Za-z0-9_]+",
        EXPECTED_WIGHT_POSES,
        "Long Night+ wight poses",
    )
    assert_count(long_night, r"CIP_[A-Za-z0-9_]+", 0, "Long Night+ DFP poses")
    assert_count(long_night, "hold_long_axe_idle", 1, "AGOT long-axe pose")
    assert_count(long_night, "hold_bow_idle", 1, "Submod Core bow pose")

    poses, expected_pose_names = extract_dfp_poses(dfp, newline)

    high_septon_marker = f"\t\t#AGOT Added{newline}\t\thigh_septon = {{"
    unique_marker(long_night, high_septon_marker, "Long Night+ high_septon")

    merged = long_night.replace(high_septon_marker, poses + high_septon_marker, 1)

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
    return strip_trailing_whitespace(normalize_newlines(merged, "\n"))


def generate(context: GenerationContext) -> None:
    global DFP_AGOT, STANDALONE_LONG_NIGHT
    DFP_AGOT = context.source("dynamic-family-portrait")
    STANDALONE_LONG_NIGHT = context.source("standalone-long-night")
    payload = codecs.BOM_UTF8 + merged_animations().encode("utf-8")
    context.write_bytes(RELATIVE_ANIMATIONS, payload)
