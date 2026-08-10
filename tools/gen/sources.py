"""Adapters for portable generator source declarations."""

from __future__ import annotations

import os
from pathlib import Path, PurePosixPath

from . import GenerationContext


class WorkshopSources:
    """Resolve Workshop-ID joins through declared context sources."""

    def __init__(self, context: GenerationContext) -> None:
        self.context = context

    def __truediv__(self, relative: str | Path) -> Path:
        parts = PurePosixPath(str(relative)).parts
        if not parts:
            raise ValueError("empty Workshop source path")
        return self.context.source(f"workshop-{parts[0]}").joinpath(*parts[1:])


def canonical_source_path(path: Path, *, root: Path, workshop_root: Path) -> str:
    """Return a stable manifest reference for a source file.

    Files under the Workshop root are identified by their numeric Workshop
    directory.  Other files must live under the repository root and are stored
    as repository-relative paths.
    """
    resolved_path = path.resolve()
    resolved_root = root.resolve()
    resolved_workshop = workshop_root.resolve()
    try:
        return resolved_path.relative_to(resolved_workshop).as_posix()
    except ValueError:
        try:
            return resolved_path.relative_to(resolved_root).as_posix()
        except ValueError as error:
            raise ValueError(
                f"source path is outside both repository and Workshop roots: {path}"
            ) from error


WORKSHOP_DIRECTORY_ENV = "CK3_WORKSHOP_DIR"


def resolve_workshop_root() -> Path:
    """Resolve the Workshop root a generator subprocess was handed."""
    configured = os.environ.get(WORKSHOP_DIRECTORY_ENV)
    if not configured:
        raise SystemExit(f"{WORKSHOP_DIRECTORY_ENV} is not set")
    path = Path(configured).expanduser().resolve()
    if not path.is_dir():
        raise SystemExit(
            f"{WORKSHOP_DIRECTORY_ENV} does not point to a directory: {path}"
        )
    return path
