"""Staged, ownership-checked execution for colocated mod generators."""

from __future__ import annotations

import fnmatch
import hashlib
import importlib.util
import io
import json
import os
import sys
import tempfile
from collections.abc import Callable, Mapping
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from types import ModuleType
from typing import Any

from .config import Config
from .hashing import sha256_file, update_digest_from_file
from .workspace import ARTIFACT_PREFIX, Mod, ModManifest, Workspace

SOURCE_LOCK_NAME = "source-lock.json"
SOURCE_LOCK_SCHEMA_VERSION = 1


class GenerationError(RuntimeError):
    """Raised when a generator violates its manifest or cannot be staged."""


class SourceLockError(GenerationError):
    """Raised when configured generator inputs differ from accepted hashes."""


def _load_module(module_path: Path, import_name: str) -> ModuleType:
    if not module_path.is_file():
        raise GenerationError(f"module not found: {module_path}")
    spec = importlib.util.spec_from_file_location(import_name, module_path)
    if spec is None or spec.loader is None:
        raise GenerationError(f"cannot load module: {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[import_name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        sys.modules.pop(import_name, None)
    return module


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
    if not parts or parts[0] != ARTIFACT_PREFIX:
        raise GenerationError(f"not a staged artifact path: {relative_path}")
    if len(parts) == 1:
        raise GenerationError(f"artifact path names no file: {relative_path}")
    return PurePosixPath(*parts[1:]).as_posix()


def output_is_owned(relative_path: str, owned_outputs: tuple[str, ...]) -> bool:
    """Return whether a staged payload path is declared by the manifest."""
    path = _relative_output(relative_path)
    if is_artifact(path):
        return False
    return _matches_declaration(path, owned_outputs)


def artifact_is_owned(relative_path: str, owned_artifacts: tuple[str, ...]) -> bool:
    """Return whether a staged ``artifacts/`` path is declared by the manifest."""
    path = _relative_output(relative_path)
    if not is_artifact(path):
        return False
    return _matches_declaration(artifact_relative(path), owned_artifacts)


def staged_is_owned(relative_path: str, generator: Any) -> bool:
    """Return whether a staged path is declared as payload or as an artifact."""
    if is_artifact(relative_path):
        return artifact_is_owned(relative_path, generator.owned_artifacts)
    return output_is_owned(relative_path, generator.owned_outputs)


@dataclass(frozen=True, slots=True)
class GenerationContext:
    """Portable inputs and a write-only staging root supplied to a generator."""

    workspace: Workspace
    mod: Mod
    manifest: ModManifest
    stage_dir: Path
    sources: Mapping[str, Path]
    options: Mapping[str, Any] = field(default_factory=dict)

    @property
    def assets_dir(self) -> Path:
        return self.manifest.path.parent / "assets"

    @property
    def output_root(self) -> Path:
        return self.stage_dir

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

    @property
    def artifacts_root(self) -> Path:
        """Staging root for development artifacts that never ship to CK3."""
        return self.stage_dir / ARTIFACT_PREFIX

    def output_path(self, relative_path: str | PurePosixPath) -> Path:
        """Resolve a staged path, whether it is payload or an ``artifacts/`` file."""
        relative = _relative_output(relative_path)
        generator = self.manifest.generator
        if generator is None or not staged_is_owned(relative, generator):
            kind = "artifact" if is_artifact(relative) else "output"
            raise GenerationError(
                f"generator for {self.mod.slug} does not own {kind} {relative}"
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


@dataclass(frozen=True, slots=True)
class GenerationResult:
    mod_slug: str
    staged_files: tuple[str, ...]
    changed_files: tuple[str, ...]
    stale_files: tuple[str, ...]
    promoted: bool = False
    stdout: str = ""
    stderr: str = ""

    @property
    def current(self) -> bool:
        return not self.changed_files and not self.stale_files


def sha256_path(path: Path) -> str:
    """Hash a file or a directory tree deterministically."""
    if path.is_file():
        return sha256_file(path)
    if not path.is_dir():
        raise SourceLockError(f"cannot hash missing source: {path}")
    digest = hashlib.sha256()
    for child in sorted(
        (candidate for candidate in path.rglob("*") if candidate.is_file()),
        key=lambda candidate: candidate.relative_to(path).as_posix(),
    ):
        relative = child.relative_to(path).as_posix().encode()
        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        update_digest_from_file(digest, child)
    return digest.hexdigest()


def source_lock_path(manifest: ModManifest) -> Path:
    return manifest.path.with_name(SOURCE_LOCK_NAME)


def load_source_locks(manifest: ModManifest) -> dict[str, str]:
    """Load optional accepted source hashes for one mod."""
    path = source_lock_path(manifest)
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise SourceLockError(f"invalid source lock {path}: {error}") from error
    if not isinstance(data, dict) or data.get("schemaVersion", 1) != 1:
        raise SourceLockError(f"unsupported source lock schema: {path}")
    sources = data.get("sources", {})
    if not isinstance(sources, dict):
        raise SourceLockError(f"source lock sources must be an object: {path}")
    result: dict[str, str] = {}
    for name, record in sources.items():
        digest = record.get("sha256") if isinstance(record, dict) else record
        if not isinstance(name, str) or not isinstance(digest, str):
            raise SourceLockError(f"invalid source lock entry in {path}")
        if len(digest) != 64 or any(
            character not in "0123456789abcdef" for character in digest.lower()
        ):
            raise SourceLockError(f"invalid SHA-256 for source {name!r} in {path}")
        result[name] = digest.lower()
    return result


def verify_source_locks(
    manifest: ModManifest, sources: Mapping[str, Path]
) -> dict[str, str]:
    """Verify every accepted hash and return the current hashes."""
    lock_path = source_lock_path(manifest)
    if not lock_path.is_file():
        return {}
    accepted = load_source_locks(manifest)
    current = {name: sha256_path(path) for name, path in sources.items()}
    unknown = sorted(set(accepted) - set(current))
    unlocked = sorted(set(current) - set(accepted))
    mismatched = sorted(
        name for name, digest in accepted.items() if current.get(name) != digest
    )
    if unknown or unlocked or mismatched:
        details = []
        if unknown:
            details.append("unknown locked sources: " + ", ".join(unknown))
        if unlocked:
            details.append("unlocked sources: " + ", ".join(unlocked))
        if mismatched:
            details.append("changed sources: " + ", ".join(mismatched))
        raise SourceLockError("; ".join(details))
    return current


def write_source_locks(
    manifest: ModManifest,
    sources: Mapping[str, Path],
    *,
    apply: bool = False,
) -> str:
    """Preview or record the current portable source hashes."""
    content = (
        json.dumps(
            {
                "schemaVersion": SOURCE_LOCK_SCHEMA_VERSION,
                "sources": {
                    name: {"sha256": sha256_path(path)}
                    for name, path in sorted(sources.items())
                },
            },
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )
    if apply:
        destination = source_lock_path(manifest)
        destination.parent.mkdir(parents=True, exist_ok=True)
        _atomic_write(destination, content.encode())
    return content


def _load_entrypoint(manifest: ModManifest) -> tuple[ModuleType, Callable[..., Any]]:
    generator = manifest.generator
    if generator is None:
        raise GenerationError(f"mod {manifest.slug} has no generator")
    module_name, function_name = generator.entrypoint.split(":", 1)
    tooling_root = manifest.path.parent.resolve()
    module_path = (tooling_root / module_name).resolve()
    if not module_path.is_relative_to(tooling_root):
        raise GenerationError(
            f"generator entrypoint escapes its tooling root: {module_path}"
        )
    if not module_path.is_file():
        raise GenerationError(f"generator entrypoint not found: {module_path}")

    try:
        import_name = f"_ck3mm_generator_{manifest.slug}_{hash(module_path)}"
        module = _load_module(module_path, import_name)
    except Exception as error:
        raise GenerationError(
            f"cannot import generator {module_path}: {error}"
        ) from error
    function = getattr(module, function_name, None)
    if not callable(function):
        raise GenerationError(
            f"generator entrypoint is not callable: {generator.entrypoint}"
        )
    return module, function


def _materialize_returned_outputs(context: GenerationContext, value: object) -> None:
    if value is None:
        return
    if not isinstance(value, Mapping):
        raise GenerationError(
            "generator must return None or a mapping of relative paths to content"
        )
    for relative, content in value.items():
        if not isinstance(relative, (str, PurePosixPath)):
            raise GenerationError("generator output mapping keys must be paths")
        if isinstance(content, str):
            context.write_text(relative, content)
        elif isinstance(content, bytes):
            context.write_bytes(relative, content)
        else:
            raise GenerationError(
                f"generator output {relative} must contain text or bytes"
            )


def _regular_files(root: Path) -> dict[str, Path]:
    result: dict[str, Path] = {}
    if not root.is_dir():
        return result
    for path in root.rglob("*"):
        if path.is_symlink():
            raise GenerationError(f"generated outputs must not be symlinks: {path}")
        if path.is_file():
            result[path.relative_to(root).as_posix()] = path
    return result


def _same_file(left: Path, right: Path) -> bool:
    if not right.is_file() or left.stat().st_size != right.stat().st_size:
        return False
    return sha256_path(left) == sha256_path(right)


def _atomic_write(destination: Path, content: bytes, *, mode: int = 0o644) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "wb", dir=destination.parent, prefix=f".{destination.name}.", delete=False
        ) as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
            temporary = Path(handle.name)
        temporary.chmod(mode)
        os.replace(temporary, destination)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def _remove_empty_parents(path: Path, *, stop: Path) -> None:
    parent = path.parent
    while parent != stop and parent.is_relative_to(stop):
        try:
            parent.rmdir()
        except OSError:
            break
        parent = parent.parent


def run_generator(
    workspace: Workspace,
    mod: Mod | str,
    config: Config,
    *,
    check: bool = True,
    options: Mapping[str, Any] | None = None,
) -> GenerationResult:
    """Stage one generator, verify ownership, compare, and optionally promote."""
    selected = workspace.get_mod(mod) if isinstance(mod, str) else mod
    manifest = selected.manifest
    if manifest is None or manifest.generator is None:
        raise GenerationError(f"mod {selected.slug} has no configured generator")
    sources = workspace.resolve_sources(manifest, config)
    verify_source_locks(manifest, sources)

    workspace.state_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix=f"generate-{selected.slug}-", dir=workspace.state_dir
    ) as directory:
        stage_dir = Path(directory)
        context = GenerationContext(
            workspace=workspace,
            mod=selected,
            manifest=manifest,
            stage_dir=stage_dir,
            sources=sources,
            options=dict(options or {}),
        )
        stdout = io.StringIO()
        stderr = io.StringIO()
        try:
            with redirect_stdout(stdout), redirect_stderr(stderr):
                _, function = _load_entrypoint(manifest)
                returned = function(context)
        except GenerationError:
            raise
        except Exception as error:
            raise GenerationError(
                f"generator for {selected.slug} failed: {error}"
            ) from error
        _materialize_returned_outputs(context, returned)

        staged = _regular_files(stage_dir)
        unexpected = sorted(
            relative
            for relative in staged
            if not staged_is_owned(relative, manifest.generator)
        )
        if unexpected:
            raise GenerationError(
                f"generator for {selected.slug} wrote undeclared outputs: "
                + ", ".join(unexpected)
            )

        # Payload promotes into mods/<slug>; artifacts promote into the mod's
        # tooling tree and never reach the Launcher.
        destinations = (
            (
                selected.root,
                {rel: path for rel, path in staged.items() if not is_artifact(rel)},
                lambda rel: output_is_owned(rel, manifest.generator.owned_outputs),
                lambda rel: rel,
            ),
            (
                selected.artifacts_root,
                {
                    artifact_relative(rel): path
                    for rel, path in staged.items()
                    if is_artifact(rel)
                },
                lambda rel: _matches_declaration(
                    rel, manifest.generator.owned_artifacts
                ),
                lambda rel: f"{ARTIFACT_PREFIX}/{rel}",
            ),
        )

        changed: list[str] = []
        stale: list[str] = []
        for root, group, owned, label in destinations:
            current_owned = {
                relative for relative in _regular_files(root) if owned(relative)
            }
            group_changed = sorted(
                relative
                for relative, staged_path in group.items()
                if not _same_file(staged_path, root / relative)
            )
            group_stale = sorted(current_owned - set(group))
            changed.extend(label(relative) for relative in group_changed)
            stale.extend(label(relative) for relative in group_stale)

            if check:
                continue
            for relative in group_changed:
                staged_path = group[relative]
                _atomic_write(
                    root / relative,
                    staged_path.read_bytes(),
                    mode=staged_path.stat().st_mode & 0o777,
                )
            for relative in group_stale:
                destination = root / relative
                destination.unlink()
                _remove_empty_parents(destination, stop=root)

        changed.sort()
        stale.sort()
        return GenerationResult(
            mod_slug=selected.slug,
            staged_files=tuple(sorted(staged)),
            changed_files=tuple(changed),
            stale_files=tuple(stale),
            promoted=not check,
            stdout=stdout.getvalue(),
            stderr=stderr.getvalue(),
        )
