"""Adapters for portable generator source declarations."""

from __future__ import annotations

from pathlib import Path, PurePosixPath

from ck3mm.generation import GenerationContext


class WorkshopSources:
    """Resolve Workshop-ID joins through declared context sources."""

    def __init__(self, context: GenerationContext) -> None:
        self.context = context

    def __truediv__(self, relative: str | Path) -> Path:
        parts = PurePosixPath(str(relative)).parts
        if not parts:
            raise ValueError("empty Workshop source path")
        return self.context.source(f"workshop-{parts[0]}").joinpath(*parts[1:])
