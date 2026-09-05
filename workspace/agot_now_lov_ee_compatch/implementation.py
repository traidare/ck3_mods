#!/usr/bin/env python3
"""Generate the single NOW/LoV/Essos Expanded compatch payload.

The stages run in the order their results depend on each other, not in payload
order. Two of them hand their result to a later stage in memory rather than
through a file: the Further East history repair is layered under the lore
governments that rewrite the same two files, and the merged province definitions
are classified by the world-data stage that would otherwise re-read them.
"""

from __future__ import annotations

from gen import GenerationContext

from .compatch import (
    RunInputs,
    further_east,
    lore_governments,
    lov_bridge,
    map_merge,
    world_data,
)


def generate(context: GenerationContext) -> None:
    inputs = RunInputs.from_context(context)

    lov_bridge.rebase(inputs)
    staged_history = further_east.rebase(inputs)
    merged = map_merge.merge(inputs)
    world_data.build(inputs, merged)
    lore_governments.build(inputs, staged_history)
