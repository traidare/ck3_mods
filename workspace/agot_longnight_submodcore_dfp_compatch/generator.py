"""Staged entrypoint for the animation-only Long Night compatibility payload."""

from __future__ import annotations

import codecs

from ck3mm.generation import GenerationContext
from ck3mm.generators import longnight_compat as implementation


def generate(context: GenerationContext) -> None:
    implementation.ROOT = context.workspace.root
    implementation.AGOT = context.source("agot")
    implementation.SUBMOD_CORE = context.source("submod-core")
    implementation.DFP_AGOT = context.source("dynamic-family-portrait")
    implementation.LONG_NIGHT = context.source("long-night")
    implementation.STANDALONE_LONG_NIGHT = context.source("standalone-long-night")
    implementation.MOD_OUTPUT_ROOT = context.output_root
    payload = codecs.BOM_UTF8 + implementation.generate().encode("utf-8")
    context.write_bytes(implementation.RELATIVE_ANIMATIONS, payload)
