"""Staged destination-specific NOW runtime rebase generator."""

from __future__ import annotations

from ck3mm.generation import GenerationContext
from ck3mm.generators import agot_runtime as implementation
from ck3mm.generators.sources import WorkshopSources


def generate(context: GenerationContext) -> None:
    implementation.ROOT = context.workspace.root
    implementation.WORKSHOP = WorkshopSources(context)
    implementation.NOW_OUTPUT = context.output_root
    implementation.generate_now_core_rebase()
    implementation.generate_now_summerhall_candidate_guards()
