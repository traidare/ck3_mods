"""Staged entrypoint for the final AGOT playset compatch."""

from __future__ import annotations

import argparse

from ck3mm.generation import GenerationContext, load_colocated_module

WORKSHOP_SOURCES = ("agot-now", "seasons-bridge")


def generate(context: GenerationContext) -> None:
    implementation = load_colocated_module(__file__)
    implementation.MODULE_RELATIVE = context.output_root.relative_to(
        context.workspace.root
    )
    implementation.SOURCE_MANIFEST_OVERRIDE = (
        context.assets_dir / "source_manifest.json"
    )
    implementation.resolve_workshop_root = lambda: context.workshop_root(
        *WORKSHOP_SOURCES
    )
    implementation.parse_args = lambda: argparse.Namespace(
        root=context.workspace.root,
        check=False,
        update_source_manifest=False,
    )
    result = implementation.main()
    if result not in (None, 0):
        raise RuntimeError(f"generator returned unsuccessful status {result}")
