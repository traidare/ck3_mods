#!/usr/bin/env python3
"""Generate the EE/Further East part of the AGOT playset compatches.

The stages run in the order their results depend on each other, not in payload
order. Two of them hand their result to a later stage in memory rather than
through a file: the Further East history repair is layered under the lore
governments that rewrite the same two files, and the merged province definitions
are classified by the world-data stage that would otherwise re-read them.
"""

from __future__ import annotations

from agot_playset.compatch import (
    RunInputs,
    further_east,
    lore_governments,
    map_merge,
    world_data,
)
from agot_playset.runtime_fixes import RunInputs as RuntimeInputs
from agot_playset.runtime_fixes.court_character import (
    generate_further_east_startup_government_quarantine,
)
from agot_playset.runtime_fixes.realm_succession import (
    generate_essos_disabled_realm_cleanup,
)
from gen import GenerationContext
from gen.sources import WorkshopSources


def generate(context: GenerationContext) -> None:
    inputs = RunInputs.from_context(context)

    staged_history = further_east.rebase(inputs)
    merged = map_merge.merge(inputs)
    # The LoV compatch is later than the Workshop map parents, so restate the
    # two files Further East intentionally owns over LoV's map when this one is
    # enabled.
    for relative in (
        "map_data/island_region.txt",
        "gfx/map/map_object_data/new_mapobject_1.txt",
    ):
        inputs.write(
            relative,
            inputs.current_map_source(relative).read_text(encoding="utf-8-sig"),
        )
    world_data.build(inputs, merged)
    lore_governments.build(inputs, staged_history)
    runtime = RuntimeInputs(
        WORKSHOP=WorkshopSources(context),
        OUTPUT=context.output_root,
        GAME_ROOT=context.source("game"),
    )
    generate_essos_disabled_realm_cleanup(runtime)
    generate_further_east_startup_government_quarantine(runtime)
