#!/usr/bin/env python3
"""Carry CaFG's LoV-contested files for players who also run LoV.

`gui/window_county_view.gui` and the two event files below are the paths where
CaFG's AGOT compatch and Legacy of Valyria genuinely want the same file. Both
content types override whole-file and same-path only, so no keyed override can
split them — the only correct answer is a separate, later-loading item that
rebuilds CaFG's hooks on top of LoV's versions.

Everything else CaFG needs for AGOT stays in the base compatch, which this
module does not duplicate.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from gen import GenerationContext, GenerationError

BASE_MODULE = "cafg_agot_compatch"

# The event files the LoV AGOT bridge ships its own whole-file copy of, so the
# base compatch's merged version is no longer the last writer once the bridge
# loads. Each is rebuilt here from the bridge's copy instead of AGOT's.
CONTESTED_EVENTS = (
    "events/activities/tournaments/contest_events.txt",
    "events/lifestyles/governance_lifestyle/stewardship_domain_events.txt",
)


def load_base(path: Path):
    """Import the base compatch generator so both items share one code path.

    The merge strategy, conflict resolutions, and county-view anchors must not
    drift between the base and this variant, so they are defined once.
    """
    if not path.is_file():
        raise GenerationError(f"missing base generator: {path}")
    spec = importlib.util.spec_from_file_location(f"{BASE_MODULE}_impl", path)
    if spec is None:
        raise GenerationError(f"cannot load base generator: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    # Read the source here rather than through the loader: `exec_module` opens
    # the file with `io.open_code`, which the sidecar's read recorder does not
    # see, and the base generator has to be pinned like any other input.
    exec(compile(path.read_text(encoding="utf-8"), str(path), "exec"), module.__dict__)
    return module


def generate(context: GenerationContext) -> None:
    base = load_base(context.source("base-generator"))

    MOD_SOURCE = context.source("culture-faith-granularity")
    LOV_SOURCE = context.source("legacy-of-valyria-agot-bridge")
    MOD_OUTPUT = context.output_root
    inputs = base.RunInputs(
        MOD_SOURCE=MOD_SOURCE,
        SOURCE=MOD_SOURCE / "common/scripted_effects",
        MOD_OUTPUT=MOD_OUTPUT,
        OUTPUT=MOD_OUTPUT / "common/scripted_effects",
        AGOT_SOURCE=LOV_SOURCE,
        VANILLA_SOURCE=context.source("vanilla"),
    )

    merges = {merge.relative: merge for merge in base.EVENT_MERGES}
    for relative in CONTESTED_EVENTS:
        if relative not in merges:
            raise GenerationError(f"base compatch no longer merges {relative}")
        base.merge_event_file(inputs, merges[relative], label="LoV AGOT bridge")
    base.generate_county_view(inputs, LOV_SOURCE, "LoV AGOT bridge")

    print(
        f"Generated CaFG/LoV variant: {len(CONTESTED_EVENTS)} event files merged "
        "and 1 county view rebuilt on the Legacy of Valyria AGOT bridge."
    )
