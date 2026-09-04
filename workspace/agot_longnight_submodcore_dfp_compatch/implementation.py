#!/usr/bin/env python3
"""Merge Long Night, Submod Core, and DFP AGOT portrait animations."""

from __future__ import annotations

import codecs
import re
from dataclasses import dataclass
from pathlib import Path

from gen import GenerationContext, GenerationError
from gen.text import (
    assert_count,
    direct_definition_names,
    nested_definition_span,
    normalize_newlines,
    read_source,
    strip_trailing_whitespace,
    unique_marker,
)

RELATIVE_ANIMATIONS = Path("gfx/portraits/portrait_animations/animations.txt")

EXPECTED_DFP_POSES = 197
EXPECTED_MERGED_DFP_POSES = 196
EXPECTED_WIGHT_POSES = 5


@dataclass(frozen=True, slots=True)
class RunInputs:
    agot: str
    submod_core: str
    dfp_agot: str
    long_night: str


def read_animations(context: GenerationContext, source: str) -> str:
    """Read one parent's animation file, asserting the encoding assumed below.

    Content drift is not checked here: sources.lock.json pins every file the run
    reads, so a hash repeated in this module would only be a second copy to
    update by hand.
    """
    return read_source(
        context.source(source) / RELATIVE_ANIMATIONS,
        require_bom=True,
        normalize_newlines=True,
    )


def extract_dfp_poses(dfp: str) -> tuple[str, set[str]]:
    pose_names = direct_definition_names(dfp, r"CIP_[A-Za-z0-9_]+")
    if len(pose_names) != EXPECTED_DFP_POSES:
        raise GenerationError(
            f"DFP poses: expected {EXPECTED_DFP_POSES}, found {len(pose_names)}"
        )
    if len(set(pose_names)) != len(pose_names):
        raise GenerationError("DFP poses contain duplicate definition names")

    first_pose = unique_marker(dfp, "\t\tCIP_toast = {", "first DFP pose")
    high_septon_marker = "\t\t#AGOT Added\n\t\thigh_septon = {"
    high_septon = unique_marker(dfp, high_septon_marker, "DFP high_septon")
    if first_pose >= high_septon:
        raise GenerationError("DFP pose region is not before high_septon")
    poses = dfp[first_pose:high_septon]

    obsolete_start, obsolete_end = nested_definition_span(
        poses, "CIP_agressive_longsword"
    )
    removal_start = obsolete_start
    if poses[:obsolete_start].endswith("\n"):
        removal_start -= 1
    poses = poses[:removal_start] + "\n" + poses[obsolete_end:]

    poses, replacements = re.subn(
        r"(?m)^[ \t]*use_longsword_default_trigger\s*=\s*no[ \t]*\n",
        "",
        poses,
    )
    if replacements != 1:
        raise GenerationError(
            "generic DFP aggressive pose: expected one obsolete trigger, "
            f"found {replacements}"
        )

    expected_names = set(pose_names) - {"CIP_agressive_longsword"}
    actual_names = set(direct_definition_names(poses, r"CIP_[A-Za-z0-9_]+"))
    if actual_names != expected_names:
        raise GenerationError("DFP pose extraction changed the expected definitions")
    return poses, expected_names


def extract_bow_pose(submod_core: str) -> str:
    start, end = nested_definition_span(submod_core, "hold_bow_idle")
    bow = submod_core[start:end]
    assert_count(bow, "hold_bow_idle", 1, "Submod Core bow pose")
    return bow


def assert_parent_shapes(inputs: RunInputs) -> None:
    assert_count(inputs.agot, r"wight_pose_[A-Za-z0-9_]+", 0, "AGOT wight poses")
    assert_count(inputs.agot, r"CIP_[A-Za-z0-9_]+", 0, "AGOT DFP poses")
    assert_count(inputs.agot, "hold_bow_idle", 0, "AGOT bow pose")
    assert_count(inputs.agot, "hold_long_axe_idle", 1, "AGOT long-axe pose")

    assert_count(inputs.submod_core, "hold_bow_idle", 1, "Submod Core bow pose")
    assert_count(
        inputs.submod_core,
        r"wight_pose_[A-Za-z0-9_]+",
        0,
        "Submod Core wight poses",
    )
    assert_count(inputs.submod_core, r"CIP_[A-Za-z0-9_]+", 0, "Submod Core DFP poses")

    assert_count(
        inputs.long_night,
        r"wight_pose_[A-Za-z0-9_]+",
        EXPECTED_WIGHT_POSES,
        "Long Night wight poses",
    )
    assert_count(inputs.long_night, r"CIP_[A-Za-z0-9_]+", 0, "Long Night DFP poses")
    assert_count(inputs.long_night, "hold_bow_idle", 0, "Long Night bow pose")
    assert_count(inputs.long_night, "hold_long_axe_idle", 1, "Long Night long-axe pose")


def merged_animations(inputs: RunInputs) -> str:
    assert_parent_shapes(inputs)
    poses, expected_pose_names = extract_dfp_poses(inputs.dfp_agot)
    bow = extract_bow_pose(inputs.submod_core)

    body_marker = "# DEFAULT PERSONALITY ANIMATIONS"
    body_start = unique_marker(inputs.long_night, body_marker, "Long Night body")
    merged = inputs.long_night[body_start:]

    high_septon_marker = "\t\t#AGOT Added\n\t\thigh_septon = {"
    unique_marker(merged, high_septon_marker, "Long Night high_septon")
    merged = merged.replace(high_septon_marker, poses + high_septon_marker, 1)

    hammer_marker = "\t\t#AGOT Added\n\t\thold_hammer_idle = {"
    unique_marker(merged, hammer_marker, "Long Night hold_hammer_idle")
    merged = merged.replace(hammer_marker, bow + "\n" + hammer_marker, 1)

    merged_pose_names = set(direct_definition_names(merged, r"CIP_[A-Za-z0-9_]+"))
    if merged_pose_names != expected_pose_names:
        raise GenerationError("merged file does not contain the expected DFP poses")
    assert_count(
        merged,
        r"CIP_[A-Za-z0-9_]+",
        EXPECTED_MERGED_DFP_POSES,
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
    assert_count(merged, "CIP_agressive_longsword", 0, "obsolete DFP pose")
    if re.search(r"(?m)^[ \t]*use_longsword_default_trigger\s*=", merged):
        raise GenerationError("merged file still has the obsolete longsword trigger")
    return strip_trailing_whitespace(normalize_newlines(merged, "\n"))


def generate(context: GenerationContext) -> None:
    inputs = RunInputs(
        agot=read_animations(context, "agot"),
        submod_core=read_animations(context, "submod-core"),
        dfp_agot=read_animations(context, "dynamic-family-portrait-agot"),
        long_night=read_animations(context, "long-night-azor-ahai"),
    )
    payload = codecs.BOM_UTF8 + merged_animations(inputs).encode("utf-8")
    context.write_bytes(RELATIVE_ANIMATIONS, payload)
