"""Staged entrypoint for the Culture and Faith Granularity AGOT compatch."""

from __future__ import annotations

from ck3mm.generation import GenerationContext, load_colocated_module


def generate(context: GenerationContext) -> None:
    implementation = load_colocated_module(__file__)
    implementation.ROOT = context.workspace.root
    implementation.MOD_SOURCE = context.source("culture-faith-granularity")
    implementation.SOURCE = implementation.MOD_SOURCE / "common/scripted_effects"
    implementation.MOD_OUTPUT = context.output_root
    implementation.OUTPUT = context.output_root / "common/scripted_effects"
    implementation.main()
