"""Staged entrypoint for the AGOT More Personality Depth rebase."""

from __future__ import annotations

from ck3mm.generation import GenerationContext, load_colocated_module

OUTPUT = "common/traits/01_personality_overrides.txt"


def generate(context: GenerationContext) -> None:
    implementation = load_colocated_module(__file__)
    implementation.ROOT = context.workspace.root
    implementation.SOURCE = context.source("more-personality-depth")
    implementation.AGOT_TRAITS = context.source("agot-traits")
    implementation.OUTPUT = context.output_path(OUTPUT)
    implementation.main()
