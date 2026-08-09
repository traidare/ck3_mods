"""Staged destination-specific Grand Remembrance runtime-fix generator."""

from __future__ import annotations

from ck3mm.generation import GenerationContext
from ck3mm.generators import agot_runtime as implementation
from ck3mm.generators.sources import WorkshopSources


def generate(context: GenerationContext) -> None:
    implementation.ROOT = context.workspace.root
    implementation.WORKSHOP = WorkshopSources(context)
    implementation.GR_OUTPUT = context.output_root
    implementation.generate_grand_remembrance_agot_obituary()
