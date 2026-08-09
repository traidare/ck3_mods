"""Synchronize the local, ignored CK3 syntax-reference cache."""

from __future__ import annotations

import json
import os
import shutil
import tempfile
from contextlib import suppress
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

SCRIPT_DOC_LOGS = (
    "effects.log",
    "event_scopes.log",
    "event_targets.log",
    "modifiers.log",
    "triggers.log",
)


class ReferenceSyncError(ValueError):
    """Raised when reference sources or a cache cannot be synchronized safely."""


@dataclass(frozen=True, slots=True)
class ReferenceCopy:
    source: Path
    destination: Path
    relative_path: str


@dataclass(frozen=True, slots=True)
class ReferenceSyncPlan:
    game_dir: Path
    paradox_dir: Path
    cache_root: Path
    copies: tuple[ReferenceCopy, ...]
    removals: tuple[Path, ...]
    info_files: int
    script_doc_logs: int


@dataclass(frozen=True, slots=True)
class ReferenceCheck:
    info_files: int
    script_doc_logs: int
    missing: tuple[str, ...] = ()
    stale: tuple[str, ...] = ()
    unexpected: tuple[str, ...] = ()
    manifest_errors: tuple[str, ...] = ()

    @property
    def current(self) -> bool:
        return not (
            self.missing or self.stale or self.unexpected or self.manifest_errors
        )


def _info_relative(path: Path, game_dir: Path) -> Path:
    relative = path.relative_to(game_dir)
    if relative.parts and relative.parts[0] == "game":
        relative = Path(*relative.parts[1:])
    if not relative.parts:
        raise ReferenceSyncError(f"invalid .info source path: {path}")
    return relative


def _expected_files(
    game_dir: Path, paradox_dir: Path
) -> tuple[dict[str, Path], int, int]:
    if not game_dir.is_dir():
        raise ReferenceSyncError(f"CK3 game directory is missing: {game_dir}")
    if not paradox_dir.is_dir():
        raise ReferenceSyncError(f"CK3 user-data directory is missing: {paradox_dir}")

    expected: dict[str, Path] = {}
    info_sources = sorted(path for path in game_dir.rglob("*.info") if path.is_file())
    if not info_sources:
        raise ReferenceSyncError(
            f"no .info files found below game directory: {game_dir}"
        )
    for source in info_sources:
        relative = (_info_relative(source, game_dir)).as_posix()
        key = f"info/{relative}"
        if key in expected:
            raise ReferenceSyncError(f"multiple .info sources map to {key}")
        expected[key] = source

    docs = 0
    logs_dir = paradox_dir / "logs"
    for filename in SCRIPT_DOC_LOGS:
        source = logs_dir / filename
        if source.is_file():
            expected[f"script_docs/{filename}"] = source
            docs += 1
    return expected, len(info_sources), docs


def plan_reference_sync(
    game_dir: Path, paradox_dir: Path, cache_root: Path
) -> ReferenceSyncPlan:
    """Build a mirror plan without modifying the generated-reference cache."""
    game = Path(game_dir).resolve(strict=False)
    paradox = Path(paradox_dir).resolve(strict=False)
    cache = Path(cache_root).resolve(strict=False)
    if cache == game or cache.is_relative_to(game):
        raise ReferenceSyncError(
            "reference cache must not be inside the game directory"
        )
    if cache == paradox or cache.is_relative_to(paradox):
        raise ReferenceSyncError("reference cache must not be inside CK3 user data")
    expected, info_count, docs_count = _expected_files(game, paradox)
    copies = tuple(
        ReferenceCopy(source, cache / relative, relative)
        for relative, source in sorted(expected.items())
    )
    actual: set[str] = set()
    for directory in (cache / "info", cache / "script_docs"):
        if directory.is_dir():
            actual.update(
                path.relative_to(cache).as_posix()
                for path in directory.rglob("*")
                if path.is_file() or path.is_symlink()
            )
    removals = tuple(cache / relative for relative in sorted(actual - expected.keys()))
    return ReferenceSyncPlan(
        game_dir=game,
        paradox_dir=paradox,
        cache_root=cache,
        copies=copies,
        removals=removals,
        info_files=info_count,
        script_doc_logs=docs_count,
    )


def _same_file(left: Path, right: Path) -> bool:
    if not right.is_file() or right.is_symlink():
        return False
    if left.stat().st_size != right.stat().st_size:
        return False
    with left.open("rb") as first, right.open("rb") as second:
        while True:
            left_chunk = first.read(1024 * 1024)
            right_chunk = second.read(1024 * 1024)
            if left_chunk != right_chunk:
                return False
            if not left_chunk:
                return True


def check_references(
    game_dir: Path, paradox_dir: Path, cache_root: Path
) -> ReferenceCheck:
    """Compare sources, cached files, and manifest without writing anything."""
    plan = plan_reference_sync(game_dir, paradox_dir, cache_root)
    missing: list[str] = []
    stale: list[str] = []
    for item in plan.copies:
        if not item.destination.is_file():
            missing.append(item.relative_path)
        elif not _same_file(item.source, item.destination):
            stale.append(item.relative_path)

    manifest_errors: list[str] = []
    manifest_path = plan.cache_root / "manifest.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        manifest_errors.append("manifest.json is missing")
    except (OSError, json.JSONDecodeError) as error:
        manifest_errors.append(f"manifest.json is invalid: {error}")
    else:
        if manifest.get("info_files") != plan.info_files:
            manifest_errors.append("manifest info_files count is stale")
        if manifest.get("script_doc_logs") != plan.script_doc_logs:
            manifest_errors.append("manifest script_doc_logs count is stale")

    return ReferenceCheck(
        info_files=plan.info_files,
        script_doc_logs=plan.script_doc_logs,
        missing=tuple(missing),
        stale=tuple(stale),
        unexpected=tuple(
            path.relative_to(plan.cache_root).as_posix() for path in plan.removals
        ),
        manifest_errors=tuple(manifest_errors),
    )


def _atomic_copy(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=destination.parent, prefix=f".{destination.name}.", delete=False
        ) as handle:
            temporary = Path(handle.name)
        shutil.copy2(source, temporary)
        os.replace(temporary, destination)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def _atomic_json(value: dict[str, object], destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=destination.parent,
            prefix=f".{destination.name}.",
            delete=False,
        ) as handle:
            json.dump(value, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
            temporary = Path(handle.name)
        os.replace(temporary, destination)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def apply_reference_sync(
    plan: ReferenceSyncPlan, *, generated_at: datetime | None = None
) -> ReferenceCheck:
    """Apply an inspected reference sync plan and return its post-check."""
    for item in plan.copies:
        _atomic_copy(item.source, item.destination)
    for path in plan.removals:
        if path.is_dir() and not path.is_symlink():
            raise ReferenceSyncError(f"refusing planned directory removal: {path}")
        path.unlink(missing_ok=True)
    for root in (plan.cache_root / "info", plan.cache_root / "script_docs"):
        if root.is_dir():
            for directory in sorted(
                (path for path in root.rglob("*") if path.is_dir()), reverse=True
            ):
                with suppress(OSError):
                    directory.rmdir()

    timestamp = generated_at or datetime.now(UTC)
    _atomic_json(
        {
            "generated_at": timestamp.isoformat(),
            "info_files": plan.info_files,
            "script_doc_logs": plan.script_doc_logs,
        },
        plan.cache_root / "manifest.json",
    )
    return check_references(plan.game_dir, plan.paradox_dir, plan.cache_root)
