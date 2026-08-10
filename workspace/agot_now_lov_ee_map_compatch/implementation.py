"""Entrypoint for the semantic NOW, LoV, and EE map merge.

The merge itself runs as a subprocess: it is a long numpy and Pillow job whose
memory is best released with the process that did the work.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from ck3mm.generation import GenerationContext

WORKSHOP_SOURCES = (
    "agot",
    "now",
    "lov",
    "lov-bridge",
    "essos-expanded",
    "essos-bridge",
)


def generate(context: GenerationContext) -> None:
    merge = Path(__file__).with_name("map_merge.py")
    environment = os.environ.copy()
    environment["CK3_WORKSHOP_DIR"] = str(context.workshop_root(*WORKSHOP_SOURCES))
    environment["CK3MM_SOURCE_MANIFEST"] = str(
        context.assets_dir / "source_manifest.json"
    )
    command = [
        sys.executable,
        str(merge),
        "--root",
        str(context.workspace.root),
        "--output",
        str(context.output_root),
    ]
    if context.options.get("text_only", False):
        command.append("--text-only")
    subprocess.run(command, check=True, env=environment)
