"""Staged entrypoint for the VIET and AGOT runtime rebase."""

from __future__ import annotations

from ck3mm.generation import GenerationContext, load_colocated_module


def generate(context: GenerationContext) -> None:
    implementation = load_colocated_module(__file__)
    implementation.ROOT = context.workspace.root
    implementation.SOURCE = context.source("viet")
    implementation.OUTPUT = context.output_root
    implementation.DISABLED_EVENTS_FILE = context.assets_dir / "disabled-events.txt"
    implementation.main()
