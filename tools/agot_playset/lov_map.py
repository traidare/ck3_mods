"""Merge NOW's Westeros map delta onto the LoV AGOT bridge."""

from __future__ import annotations

from functools import partial

from gen.script import read_text

from .compatch.map_merge import (
    BUILDING_LOCATORS,
    LOV_LOCATOR_BASELINES,
    NOW_DEFINITION_ROWS,
    SPECIAL_BUILDING_LOCATORS,
    Overlay,
    apply_locator_pins,
    apply_object_suppressions,
    definition_lines,
    geographical_block_merger,
    locator_records,
    merge_file_blocks,
    merge_object_block,
    restates_region,
    split_objects,
)
from .compatch.pdx import top_level_blocks


def _roots(context):
    return {
        "agot": context.source("agot"),
        "now": context.source("agot-now"),
        "bridge": context.source("lov-agot-bridge"),
        "seasons": context.source("seasons-bridge"),
    }


def _merge_definition(roots) -> str:
    relative = "map_data/definition.csv"
    bridge_lines, bridge = definition_lines(read_text(roots["bridge"] / relative))
    _, agot = definition_lines(read_text(roots["agot"] / relative))
    _, now = definition_lines(read_text(roots["now"] / relative))
    invalid = [
        key
        for key in NOW_DEFINITION_ROWS
        if bridge.get(key) != agot.get(key) or now.get(key) == agot.get(key)
    ]
    if invalid:
        raise RuntimeError(f"LoV/NOW definition assumptions changed: {invalid}")
    output = [
        now[int(line.split(";", 1)[0])]
        if ";" in line
        and line.split(";", 1)[0].isdigit()
        and int(line.split(";", 1)[0]) in NOW_DEFINITION_ROWS
        else line
        for line in bridge_lines
    ]
    return "\n".join(output) + "\n"


def _merge_adjacencies(roots) -> str:
    relative = "map_data/adjacencies.csv"
    agot = read_text(roots["agot"] / relative)
    now = read_text(roots["now"] / relative)
    bridge = read_text(roots["bridge"] / relative)
    removed = [line for line in agot.splitlines() if line not in now.splitlines()]
    added = [line for line in now.splitlines() if line not in agot.splitlines()]
    if len(removed) != 1 or len(added) != 1:
        raise RuntimeError("NOW adjacency delta is no longer exactly one replacement")
    if bridge.count(removed[0]) != 1:
        raise RuntimeError("LoV bridge no longer carries the adjacency replaced by NOW")
    return bridge.replace(removed[0], added[0], 1).replace("\r\n", "\n")


def _merge_regions(roots) -> str:
    relative = "map_data/island_region.txt"
    parse = partial(top_level_blocks, label="island region", restates=restates_region)
    agot = parse(read_text(roots["agot"] / relative))
    now = parse(read_text(roots["now"] / relative))
    bridge = parse(read_text(roots["bridge"] / relative))
    resolver = geographical_block_merger(
        {"agot": agot[3], "eep": bridge[3], "now": now[3]}
    )
    return merge_file_blocks(
        bridge, (Overlay.build("NOW island regions", agot, now),), conflict=resolver
    )


def _merge_objects(roots, relative: str) -> str:
    agot = split_objects(read_text(roots["agot"] / relative))
    now = split_objects(read_text(roots["now"] / relative))
    bridge = split_objects(read_text(roots["bridge"] / relative))
    return merge_file_blocks(
        bridge,
        (Overlay.build(f"NOW {relative}", agot, now),),
        conflict=merge_object_block,
        pins=lambda order, merged: apply_object_suppressions(order, merged, relative),
    )


def _pinned_locator(roots, relative: str) -> str:
    prefix, suffix, order, records = locator_records(
        read_text(roots["seasons"] / relative)
    )
    order, records = apply_locator_pins(
        order, records, relative, baselines=LOV_LOCATOR_BASELINES
    )
    separator = "\n\n"
    body = separator.join(records[key].rstrip() for key in order)
    return prefix + body + suffix


def generate(context) -> None:
    roots = _roots(context)
    context.write_text("map_data/definition.csv", _merge_definition(roots))
    context.write_text("map_data/adjacencies.csv", _merge_adjacencies(roots))
    context.write_text("map_data/island_region.txt", _merge_regions(roots))
    for relative in (
        "gfx/map/map_object_data/new_mapobject_1.txt",
        "gfx/map/map_object_data/new_mapobject_3.txt",
    ):
        context.write_text(relative, _merge_objects(roots, relative))
    for relative in (BUILDING_LOCATORS, SPECIAL_BUILDING_LOCATORS):
        context.write_text(relative, _pinned_locator(roots, relative))
