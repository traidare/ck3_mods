"""Staged entrypoint for the Any New Traditions AGOT balance generator."""

from __future__ import annotations

from ck3mm.generation import GenerationContext, load_colocated_module


def generate(context: GenerationContext) -> None:
    implementation = load_colocated_module(__file__)
    implementation.ROOT = context.workspace.root
    implementation.ANT = context.source("any-new-traditions")
    implementation.ANT_AGOT = context.source("any-new-traditions-agot")
    implementation.OUT = context.output_root
    common = implementation.ANT / "common/buildings/ary_common_buildings.txt"
    common2 = implementation.ANT / "common/buildings/ary_common2_buildings.txt"
    agot = (
        implementation.ANT_AGOT
        / "common/buildings/vv_ary_duchy_and_common_buildings.txt"
    )
    implementation.COMMON_CHAINS = {
        "ary_mtg": common,
        "ary_ew": common,
        "ary_eto": common,
        "ary_lmc": common,
        "vv_ary_dim": agot,
        "ary_swt": common,
        "ary_tml": common,
        "ary_dfa": common2,
        "ary_wetm": common2,
        "ary_caryf": common2,
        "ary_swordasa": common2,
        "ary_cameltg": common2,
        "ary_hatg": common2,
        "vv_ary_merchantg": agot,
        "ary_firearmsf": common2,
    }
    implementation.main()
