"""Staged entrypoint for the standalone fixed Long Night mod."""

from __future__ import annotations

from ck3mm.generation import GenerationContext, load_colocated_module


def generate(context: GenerationContext) -> None:
    implementation = load_colocated_module(__file__)
    implementation.ROOT = context.workspace.root
    implementation.OUTPUT = context.output_root
    implementation.AGOT = context.source("agot")
    implementation.CORE = context.source("submod-core")
    implementation.SEASONS = context.source("seasons")
    implementation.LONG_NIGHT = context.source("long-night")
    implementation.legacy.ROOT = context.workspace.root
    implementation.legacy.AGOT = implementation.AGOT
    implementation.legacy.SUBMOD_CORE = implementation.CORE
    implementation.legacy.LONG_NIGHT = implementation.LONG_NIGHT
    core_animations = (
        implementation.CORE / "gfx/portraits/portrait_animations/animations.txt"
    )
    season_events = implementation.SEASONS / "events/season_events.txt"
    long_night_animations = (
        implementation.LONG_NIGHT / "gfx/portraits/portrait_animations/animations.txt"
    )
    implementation.PINNED_HASHES = {
        core_animations: (
            "c0b7d8bf00ce21001e28a10ca76cc0c95cf850a0bf5ef3dd81d98b671b1a111a"
        ),
        season_events: (
            "f5f618b90ff2f5697517310b4d3c63f95c44ecf56150a2d1ad4cb3e26b217c04"
        ),
        long_night_animations: (
            "2d8de11f686ba6772c4607f0d1a8b7938153b589a1c081d5d194dd45c06142bd"
        ),
    }
    files = implementation.expected_files()
    for relative, content in sorted(files.items()):
        context.write_bytes(relative, content)
