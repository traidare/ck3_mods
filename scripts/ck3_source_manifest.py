"""Portable source references used by generated CK3 compatches."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path


WORKSHOP_DIRECTORY_ENV = "CK3_WORKSHOP_DIR"


def sha256_file(path: Path) -> str:
    """Return a streaming SHA-256 digest for a source file."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def resolve_workshop_root() -> Path:
    """Resolve the current Workshop root from the required environment var."""
    configured = os.environ.get(WORKSHOP_DIRECTORY_ENV)
    if not configured:
        raise SystemExit(f"{WORKSHOP_DIRECTORY_ENV} is not set")
    path = Path(configured).expanduser().resolve()
    if not path.is_dir():
        raise SystemExit(
            f"{WORKSHOP_DIRECTORY_ENV} does not point to a directory: {path}"
        )
    return path


def canonical_source_path(
    path: Path,
    *,
    root: Path,
    workshop_root: Path,
) -> str:
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
