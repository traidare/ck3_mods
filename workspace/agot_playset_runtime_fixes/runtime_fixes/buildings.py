"""Repairs for special-building database entries the reader rejects.

These faults are raised while `common/buildings` is parsed, so the affected
field, and in one case the enclosing block, never reaches the database at all.
"""

from __future__ import annotations

import re

from gen.script import (
    normalize_rebased_source,
    read_text,
    replace_regex,
    write_text,
)
from gen.text import replace_exact

from .context import RunInputs

LANDMARKS_RELATIVE = (
    "common/buildings/zzz_landmarks_agot_special_buildings_westeros.txt"
)
LANDMARKS_COMPATCH_RELATIVE = (
    "common/buildings/zzzz_cow_agot_landmarks_special_buildings_westeros.txt"
)

# AGOT declares normal_building_tier_1_cost through _8_cost in
# common/script_values/00_building_values.txt and nothing above tier 8.
HIGHEST_AGOT_BUILDING_TIER = 8


def generate_landmarks_building_repairs(inputs: RunInputs) -> None:
    path = inputs.WORKSHOP / "3692879370" / LANDMARKS_RELATIVE
    source = read_text(path)

    tier = HIGHEST_AGOT_BUILDING_TIER
    if f"normal_building_tier_{tier + 1}_cost" not in source:
        raise RuntimeError(
            "Landmarks of Westeros no longer names an undefined building cost tier"
        )
    source = replace_exact(
        source,
        f"cost_gold = normal_building_tier_{tier + 1}_cost",
        f"cost_gold = normal_building_tier_{tier}_cost",
        expected=4,
        label="Landmarks undefined building cost tier",
    )

    source = replace_exact(
        source,
        "forest_development_growth_faction",
        "forest_development_growth_factor",
        expected=1,
        label="Landmarks forest development growth tag",
    )

    # Every other fort_level in the file sits in a province_modifier. This one
    # is a direct child of its building, where the reader rejects it outright.
    stray = len(re.findall(r"(?m)^\tfort_level\s*=", source))
    nested = len(re.findall(r"(?m)^\t\tfort_level\s*=", source))
    if stray != 1 or nested < 100:
        raise RuntimeError(
            "Landmarks fort_level repair expects one building-level field beside "
            f"the province_modifier ones; found {stray} and {nested}"
        )
    source = replace_regex(
        source,
        r"(?m)^\tfort_level = (?P<level>\d+)$",
        "\tprovince_modifier = {\n\t\tfort_level = \\g<level>\n\t}",
        expected=1,
        label="Landmarks building-level fort_level",
    )

    write_text(inputs.OUTPUT, LANDMARKS_RELATIVE, normalize_rebased_source(source))


def generate_landmarks_compatch_building_repairs(inputs: RunInputs) -> None:
    path = inputs.WORKSHOP / "3697008412" / LANDMARKS_COMPATCH_RELATIVE
    source = read_text(path)

    # A building's on_complete runs in the province scope, which is why the
    # sibling blocks reach the holder through `barony.holder`. There is no
    # `holding` link, so the reader drops the whole can_construct-to-on_complete
    # span and the upgrade never runs.
    source = replace_exact(
        source,
        """        if ={
            limit = {
                holding = {
                    NOR = {
                        has_building = castle_05
                    }
                }
            }
            add_building = castle_05
        }""",
        """        if = {
            limit = {
                NOT = { has_building = castle_05 }
            }
            add_building = castle_05
        }""",
        expected=1,
        label="High Tide completion holding scope",
    )

    # agot_cities is defined by no mod in the playset, so each of these blocks
    # only produces `Event [agot_cities.5000] not found` on completion. The
    # blocks hold nothing else, so they are removed rather than redirected.
    source = replace_exact(
        source,
        """
    on_complete = {
        barony.holder = {
            trigger_event = agot_cities.5000
        }
    }
""",
        "",
        expected=3,
        label="Landmarks compatch dead completion event",
    )
    if "agot_cities" in source:
        raise RuntimeError(
            "Landmarks compatch still references the agot_cities namespace"
        )

    write_text(
        inputs.OUTPUT, LANDMARKS_COMPATCH_RELATIVE, normalize_rebased_source(source)
    )
