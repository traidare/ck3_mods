"""Staged entrypoint for the Mayham and Armies of Westeros compatch."""

from __future__ import annotations

from ck3mm.generation import GenerationContext, load_colocated_module


def generate(context: GenerationContext) -> None:
    implementation = load_colocated_module(__file__)
    implementation.ROOT = context.workspace.root
    implementation.AGOT = context.source("agot")
    implementation.MAYHAM = context.source("mayham")
    implementation.AOW = context.source("armies-of-westeros")
    implementation.OUT = context.output_path(
        "common/culture/traditions/zzz_agot_mayham_aow_compatch_traditions.txt"
    )
    implementation.AOW_UNIQUE_OUT = context.output_path(
        "common/culture/traditions/00_agot_unique_traditions.txt"
    )
    implementation.main()
