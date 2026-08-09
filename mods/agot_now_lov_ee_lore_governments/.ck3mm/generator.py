"""Staged entrypoint for LoV/EE lore-government generation."""

from __future__ import annotations

import argparse

from ck3mm.generation import GenerationContext, load_colocated_module

WORKSHOP_SOURCES = (
    "agot",
    "legacy-of-valyria",
    "legacy-of-valyria-bridge",
    "essos-expanded",
    "essos-expanded-bridge",
    "lore-bridge",
)


def generate(context: GenerationContext) -> None:
    implementation = load_colocated_module(__file__)
    implementation.OUTPUT_ROOT_OVERRIDE = context.output_root
    implementation.ASSETS_DIR_OVERRIDE = context.assets_dir / "lore_governments"
    implementation.LOCAL_SOURCE_OVERRIDES = {
        "LOV_REBASE": context.source("legacy-of-valyria-rebase"),
        "EE_REBASE": context.source("essos-expanded-rebase"),
    }
    implementation.resolve_workshop_root = lambda: context.workshop_root(
        *WORKSHOP_SOURCES
    )
    implementation.parse_args = lambda: argparse.Namespace(
        root=context.workspace.root,
        audit=False,
        check=False,
        update_source_manifest=False,
    )
    result = implementation.main()
    if result not in (None, 0):
        raise RuntimeError(f"generator returned unsuccessful status {result}")
