"""Staged entrypoint for the Bloodlines: Legacies of AGOT rebase."""

from __future__ import annotations

from ck3mm.generation import GenerationContext, load_colocated_module


def generate(context: GenerationContext) -> None:
    implementation = load_colocated_module(__file__)
    implementation.ROOT = context.workspace.root
    implementation.BLOODLINES = context.source("bloodlines-legacies")
    implementation.AGOT = context.source("agot")
    implementation.OUTPUT = context.output_root
    implementation.main()
