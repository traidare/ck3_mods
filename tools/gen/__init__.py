"""Generator support API for the ck3mm Python sidecar.

The Go core owns discovery, source resolution, staging, ownership, and
promotion.  A generator only ever sees the request the core hands it: read-only
source roots it declared, its own assets, and a write-only staging root.
"""

from __future__ import annotations

import fnmatch
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any

# The staging prefix reserved for development artifacts. Anything staged below
# it is promoted into workspace/<slug>/artifacts/ and never installed.
ARTIFACT_PREFIX = "artifacts"


class GenerationError(RuntimeError):
    """Raised when a generator violates its manifest or cannot be staged."""


def _relative_output(value: str | PurePosixPath) -> str:
    text = str(value).replace("\\", "/")
    path = PurePosixPath(text)
    if path.is_absolute() or ".." in path.parts or path.as_posix() in {"", "."}:
        raise GenerationError(f"output path must stay within the mod: {value}")
    return path.as_posix()


def _matches_declaration(path: str, patterns: tuple[str, ...]) -> bool:
    """Match exact files, directory prefixes, and POSIX glob declarations."""
    for pattern in patterns:
        if any(character in pattern for character in "*?["):
            if fnmatch.fnmatchcase(path, pattern):
                return True
        elif path == pattern or path.startswith(pattern.rstrip("/") + "/"):
            return True
    return False


def is_artifact(relative_path: str) -> bool:
    """Return whether a staged path belongs to the non-shipping tooling tree."""
    return PurePosixPath(_relative_output(relative_path)).parts[0] == ARTIFACT_PREFIX


def artifact_relative(relative_path: str) -> str:
    """Strip the reserved ``artifacts/`` prefix from a staged path."""
    parts = PurePosixPath(_relative_output(relative_path)).parts
    if parts[0] != ARTIFACT_PREFIX:
        raise GenerationError(f"not a staged artifact path: {relative_path}")
    if len(parts) == 1:
        raise GenerationError(f"artifact path names no file: {relative_path}")
    return PurePosixPath(*parts[1:]).as_posix()


@dataclass(frozen=True, slots=True)
class GenerationContext:
    """Portable inputs and a write-only staging root supplied to a generator."""

    mod_slug: str
    workspace_root: Path
    mod_root: Path
    tooling_root: Path
    stage_dir: Path
    sources: Mapping[str, Path]
    owned_outputs: tuple[str, ...] = ()
    owned_artifacts: tuple[str, ...] = ()
    options: Mapping[str, Any] = field(default_factory=dict)

    @property
    def assets_dir(self) -> Path:
        return self.tooling_root / "assets"

    @property
    def output_root(self) -> Path:
        return self.stage_dir

    @property
    def artifacts_root(self) -> Path:
        """Staging root for development artifacts that never ship to CK3."""
        return self.stage_dir / ARTIFACT_PREFIX

    def source(self, name: str) -> Path:
        try:
            return self.sources[name]
        except KeyError as error:
            raise GenerationError(
                f"generator requested unknown source: {name}"
            ) from error

    def workshop_root(self, *source_names: str) -> Path:
        """Return the common Workshop parent for the named source roots."""
        roots = [self.source(name) for name in source_names]
        parents = {path.parent for path in roots}
        if len(parents) != 1:
            raise GenerationError(f"Workshop inputs do not share one root: {roots}")
        return parents.pop()

    def owns(self, relative_path: str) -> bool:
        """Return whether a staged path is declared as payload or as an artifact."""
        path = _relative_output(relative_path)
        if is_artifact(path):
            return _matches_declaration(artifact_relative(path), self.owned_artifacts)
        return _matches_declaration(path, self.owned_outputs)

    def output_path(self, relative_path: str | PurePosixPath) -> Path:
        """Resolve a staged path, whether it is payload or an ``artifacts/`` file."""
        relative = _relative_output(relative_path)
        if not self.owns(relative):
            kind = "artifact" if is_artifact(relative) else "output"
            raise GenerationError(
                f"generator for {self.mod_slug} does not own {kind} {relative}"
            )
        output = self.stage_dir / relative
        output.parent.mkdir(parents=True, exist_ok=True)
        return output

    def artifact_path(self, relative_path: str | PurePosixPath) -> Path:
        """Resolve a path below the mod's ``artifacts/`` staging root."""
        return self.output_path(
            PurePosixPath(ARTIFACT_PREFIX) / _relative_output(relative_path)
        )

    def write_text(
        self,
        relative_path: str | PurePosixPath,
        content: str,
        *,
        encoding: str = "utf-8",
    ) -> Path:
        output = self.output_path(relative_path)
        output.write_text(content, encoding=encoding)
        return output

    def write_bytes(self, relative_path: str | PurePosixPath, content: bytes) -> Path:
        output = self.output_path(relative_path)
        output.write_bytes(content)
        return output
