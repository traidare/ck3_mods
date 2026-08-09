"""Staged entrypoint for AGOT/NOW/LoV/EE terrain and region data."""

from __future__ import annotations

import argparse

from ck3mm.generation import GenerationContext, load_colocated_module

WORKSHOP_SOURCES = (
    "agot",
    "agot-now",
    "legacy-of-valyria",
    "legacy-of-valyria-bridge",
    "essos-expanded",
    "essos-expanded-bridge",
)


def generate(context: GenerationContext) -> None:
    implementation = load_colocated_module(__file__)
    implementation.OUTPUT_ROOT_OVERRIDE = context.output_root
    implementation.ASSETS_DIR_OVERRIDE = context.assets_dir / "world_data"
    implementation.MAP_DEFINITION_OVERRIDE = context.source("map-definition")
    implementation.REFERENCE_PATHS_OVERRIDE = {
        "detailed": context.source("known-world-detailed"),
        "google": context.source("known-world-google"),
    }
    implementation.resolve_workshop_root = lambda: context.workshop_root(
        *WORKSHOP_SOURCES
    )
    implementation.parse_args = lambda: argparse.Namespace(
        root=context.workspace.root,
        audit=False,
        check=False,
        update_source_manifest=False,
        no_cache=bool(context.options.get("no_cache", False)),
    )
    result = implementation.main()
    if result not in (None, 0):
        raise RuntimeError(f"generator returned unsuccessful status {result}")
