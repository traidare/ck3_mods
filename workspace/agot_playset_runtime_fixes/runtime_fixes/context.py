"""Explicit source and staging roots for one runtime-repair run."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from gen.sources import WorkshopSources


@dataclass(frozen=True, slots=True)
class RunInputs:
    WORKSHOP: WorkshopSources
    OUTPUT: Path
    GAME_ROOT: Path
