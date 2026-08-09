"""Create update-proof local copies of every enabled mod in a CK3 playset.

Planning performs all source, collision, schema, and disk-space validation without
writing.  Applying a previously returned plan is the only mutating operation.
All host-specific roots are supplied by the caller.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import sqlite3
import stat
import unicodedata
import uuid
import zipfile
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any, NoReturn

from .launcher import (
    connect_database,
    create_playset,
    database,
    detect_pdx_user_id,
    inspect_schema,
    live_playset_clause,
    parse_enabled,
    parse_position,
    playset_mod_rows,
    qident,
    row_value,
    select_playset,
)
from .playsets import requested_playset_name

GOOD_STATUSES = {"ready_to_play", "initialized"}
MANIFEST_FORMAT = "ck3-playset-snapshot-v1"
SKIPPED_DIRECTORIES = {".git"}
DESCRIPTOR_PATH_KEYS = {"path", "archive", "remote_file_id"}
ONE_GIB = 1024**3


class PreservationError(RuntimeError):
    """An expected validation or preservation failure."""


@dataclass(frozen=True, slots=True)
class FileEntry:
    relative_path: PurePosixPath
    source_path: Path
    size: int
    mtime_ns: int


@dataclass(frozen=True, slots=True)
class ZipEntry:
    relative_path: PurePosixPath
    member_name: str
    size: int


@dataclass(slots=True)
class SourceMod:
    source_index: int
    source_position: int
    mod_id: str
    display_name: str
    source: str
    registry_id: str | None
    descriptor_path: Path
    descriptor_text: str
    source_kind: str
    source_path: Path
    row: dict[str, Any]
    clone_name: str
    registry_filename: str
    files: list[FileEntry] = field(default_factory=list)
    zip_entries: list[ZipEntry] = field(default_factory=list)
    byte_count: int = 0
    file_count: int = 0
    content_sha256: str | None = None
    new_mod_id: str | None = None


@dataclass(slots=True)
class PreservationPlan:
    database_path: Path
    paradox_directory: Path
    mod_directory: Path
    workshop_directory: Path | None
    source_playset_id: str
    source_playset_name: str
    selection_source: str
    snapshot_name: str
    snapshot_slug: str
    created_at: str
    final_root: Path
    mods: list[SourceMod]
    source_fingerprint: tuple[tuple[str, int], ...]
    required_bytes: int
    free_bytes: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "sourcePlayset": self.source_playset_name,
            "selectionSource": self.selection_source,
            "snapshotName": self.snapshot_name,
            "snapshotDirectory": str(self.final_root),
            "enabledMods": len(self.mods),
            "contentBytes": sum(mod.byte_count for mod in self.mods),
            "requiredBytes": self.required_bytes,
            "freeBytes": self.free_bytes,
        }


@dataclass(frozen=True, slots=True)
class PreservationResult:
    plan: PreservationPlan
    playset_id: str
    backup_path: Path


def _error(message: str) -> NoReturn:
    raise PreservationError(message)


def _utc_timestamp(now: datetime | None = None) -> tuple[str, str]:
    value = (now or datetime.now(UTC)).astimezone(UTC)
    return value.strftime("%Y-%m-%dT%H:%M:%SZ"), value.strftime("%Y%m%dT%H%M%SZ")


def _slugify(value: str, *, fallback: str = "snapshot", limit: int = 80) -> str:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^A-Za-z0-9]+", "-", normalized).strip("-").lower()
    return (slug or fallback)[:limit].rstrip("-") or fallback


def _safe_registry_path(root: Path, registry_id: str | None) -> Path | None:
    if not registry_id:
        return None
    relative = PurePosixPath(registry_id.replace("\\", "/"))
    if relative.is_absolute() or ".." in relative.parts:
        return None
    candidate = root.joinpath(*relative.parts)
    return candidate if candidate.is_file() else None


def _descriptor_value(text: str, key: str) -> str | None:
    pattern = rf'^\s*{re.escape(key)}\s*=\s*"((?:\\.|[^"\\])*)"'
    for line in text.splitlines():
        if match := re.match(pattern, line):
            return match.group(1).replace('\\"', '"').replace("\\\\", "\\")
    return None


def _transform_descriptor(text: str, *, path: str | None) -> str:
    key_pattern = "|".join(re.escape(key) for key in sorted(DESCRIPTOR_PATH_KEYS))
    retained = [
        line
        for line in text.replace("\r\n", "\n").replace("\r", "\n").splitlines()
        if not re.match(rf"^\s*(?:{key_pattern})\s*=", line)
    ]
    while retained and not retained[-1].strip():
        retained.pop()
    if path is not None:
        escaped = path.replace("\\", "\\\\").replace('"', '\\"')
        retained.append(f'path="{escaped}"')
    return "\n".join(retained) + "\n"


def _resolve_descriptor(
    row: sqlite3.Row, paradox_directory: Path, source_directory: Path | None
) -> tuple[Path, str]:
    registry_value = row_value(row, "gameRegistryId")
    registry = _safe_registry_path(
        paradox_directory,
        str(registry_value) if registry_value is not None else None,
    )
    candidates = [registry]
    if source_directory is not None:
        candidates.append(source_directory / "descriptor.mod")
    for candidate in candidates:
        if candidate is not None and candidate.is_file():
            try:
                return candidate, candidate.read_text(encoding="utf-8-sig")
            except (OSError, UnicodeError) as exc:
                _error(f"could not read descriptor {candidate}: {exc}")
    _error(
        "no readable descriptor was found for "
        f'"{row_value(row, "displayName", "name")}"'
    )


def _path_from_descriptor(text: str, paradox_directory: Path, key: str) -> Path | None:
    value = _descriptor_value(text, key)
    if not value:
        return None
    candidate = Path(value).expanduser()
    if not candidate.is_absolute():
        candidate = paradox_directory / candidate
    return candidate if candidate.exists() else None


def _resolve_source(
    row: sqlite3.Row,
    paradox_directory: Path,
    workshop_directory: Path | None,
) -> tuple[str, Path, Path, str]:
    directory_value = row_value(row, "dirPath")
    directory = Path(str(directory_value)).expanduser() if directory_value else None
    if directory is not None and directory.is_dir():
        descriptor, text = _resolve_descriptor(row, paradox_directory, directory)
        return "directory", directory.resolve(), descriptor, text

    descriptor, text = _resolve_descriptor(row, paradox_directory, None)
    descriptor_directory = _path_from_descriptor(text, paradox_directory, "path")
    if descriptor_directory is not None and descriptor_directory.is_dir():
        return "directory", descriptor_directory.resolve(), descriptor, text

    source = str(row_value(row, "source") or "").lower()
    registry_value = row_value(row, "gameRegistryId")
    if source == "local" and registry_value:
        registry = PurePosixPath(str(registry_value).replace("\\", "/"))
        if (
            not registry.is_absolute()
            and ".." not in registry.parts
            and registry.suffix == ".mod"
        ):
            inferred = paradox_directory.joinpath(*registry.with_suffix("").parts)
            if inferred.is_dir():
                return "directory", inferred.resolve(), descriptor, text

    steam_id = row_value(row, "steamId", "remoteSteamId")
    if workshop_directory is not None and steam_id is not None:
        inferred = workshop_directory / str(steam_id)
        if inferred.is_dir():
            return "directory", inferred.resolve(), descriptor, text

    archive_value = row_value(row, "archivePath")
    archive = Path(str(archive_value)).expanduser() if archive_value else None
    if archive is None or not archive.is_file():
        archive = _path_from_descriptor(text, paradox_directory, "archive")
    if archive is not None and archive.is_file():
        if not zipfile.is_zipfile(archive):
            _error(f"unsupported non-ZIP mod archive: {archive}")
        return "zip", archive.resolve(), descriptor, text

    _error(
        "could not resolve installed content for "
        f'"{row_value(row, "displayName", "name")}"'
    )


def _iter_tree(
    root: Path,
) -> list[tuple[PurePosixPath, Path, os.stat_result]]:
    entries: list[tuple[PurePosixPath, Path, os.stat_result]] = []

    def visit(
        physical: Path,
        logical: PurePosixPath,
        ancestors: frozenset[tuple[int, int]],
    ) -> None:
        try:
            followed = physical.stat()
        except OSError as exc:
            _error(f"could not inspect {physical}: {exc}")
        inode = (followed.st_dev, followed.st_ino)
        if stat.S_ISDIR(followed.st_mode):
            if inode in ancestors:
                _error(f"cyclic directory link found at {physical}")
            try:
                children = sorted(physical.iterdir(), key=lambda item: item.name)
            except OSError as exc:
                _error(f"could not list {physical}: {exc}")
            for child in children:
                if child.name not in SKIPPED_DIRECTORIES:
                    visit(child, logical / child.name, ancestors | {inode})
            return
        if stat.S_ISREG(followed.st_mode):
            entries.append((logical, physical.resolve(), followed))
            return
        _error(f"unsupported special file in mod content: {physical}")

    visit(root, PurePosixPath(), frozenset())
    return entries


def _safe_zip_path(name: str) -> PurePosixPath:
    normalized = name.replace("\\", "/")
    path = PurePosixPath(normalized)
    if path.is_absolute() or ".." in path.parts or not path.parts:
        _error(f"unsafe path in ZIP archive: {name}")
    if re.match(r"^[A-Za-z]:", normalized):
        _error(f"unsafe drive path in ZIP archive: {name}")
    return path


def _scan_source(mod: SourceMod) -> None:
    if mod.source_kind == "directory":
        mod.files = [
            FileEntry(relative, source, int(info.st_size), int(info.st_mtime_ns))
            for relative, source, info in _iter_tree(mod.source_path)
        ]
        mod.files.sort(key=lambda entry: entry.relative_path.as_posix())
        mod.file_count = len(mod.files)
        mod.byte_count = sum(entry.size for entry in mod.files)
        return

    seen: set[PurePosixPath] = set()
    try:
        with zipfile.ZipFile(mod.source_path) as archive:
            for info in archive.infolist():
                relative = _safe_zip_path(info.filename)
                if info.is_dir() or any(
                    part in SKIPPED_DIRECTORIES for part in relative.parts
                ):
                    continue
                mode = info.external_attr >> 16
                if stat.S_ISLNK(mode):
                    _error(
                        "symbolic links in ZIP archives are unsupported: "
                        f"{info.filename}"
                    )
                if relative in seen:
                    _error(f"duplicate destination path in ZIP archive: {relative}")
                seen.add(relative)
                mod.zip_entries.append(
                    ZipEntry(relative, info.filename, info.file_size)
                )
    except (OSError, zipfile.BadZipFile) as exc:
        _error(f"could not inspect ZIP archive {mod.source_path}: {exc}")
    mod.zip_entries.sort(key=lambda entry: entry.relative_path.as_posix())
    mod.file_count = len(mod.zip_entries)
    mod.byte_count = sum(entry.size for entry in mod.zip_entries)


def _source_identifier(row: sqlite3.Row, fallback: str) -> str:
    registry = row_value(row, "gameRegistryId")
    if registry:
        return PurePosixPath(str(registry).replace("\\", "/")).stem
    remote = row_value(row, "steamId", "remoteSteamId", "pdxId", "remotePdxId")
    return str(remote or fallback)


def _validate_mod_insert_schema(columns: dict[str, sqlite3.Row]) -> None:
    known = {
        "id",
        "pdxId",
        "steamId",
        "gameRegistryId",
        "name",
        "displayName",
        "descriptionDeprecated",
        "thumbnailUrl",
        "thumbnailPath",
        "version",
        "tags",
        "requiredVersion",
        "arch",
        "os",
        "repositoryPath",
        "dirPath",
        "archivePath",
        "status",
        "source",
        "cause",
        "timeUpdated",
        "isNew",
        "createdDate",
        "subscribedDate",
        "size",
        "metadataId",
        "remotePdxId",
        "remoteSteamId",
        "metadataVersion",
        "isMetadataApplied",
        "metadataStatus",
        "metadataGameId",
        "descriptionPdx",
        "descriptionSteam",
        "shortDescriptionPdx",
        "keepLatest",
        "userVersion",
        "remotePdxUserId",
        "remoteSteamUserId",
    }
    unknown_required = [
        name
        for name, info in columns.items()
        if bool(info["notnull"]) and info["dflt_value"] is None and name not in known
    ]
    if unknown_required:
        _error(
            "this launcher version has unsupported required mod columns: "
            + ", ".join(sorted(unknown_required))
        )


def plan_preservation(
    database_path: Path,
    mod_directory: Path,
    *,
    workshop_directory: Path | None = None,
    playset_name: str | None = None,
    configured_name: str | None = None,
    snapshot_name: str | None = None,
    now: datetime | None = None,
) -> PreservationPlan:
    """Validate and describe a preservation operation without writing anything."""

    database_path = database_path.expanduser().resolve()
    paradox_directory = database_path.parent
    mod_directory = mod_directory.expanduser().resolve()
    if not mod_directory.is_dir():
        _error(f"launcher mod directory not found: {mod_directory}")
    if workshop_directory is not None:
        workshop_directory = workshop_directory.expanduser().resolve()

    created_at, filename_timestamp = _utc_timestamp(now)
    requested_name, selection_source = requested_playset_name(
        playset_name, configured_name
    )
    with database(database_path) as connection:
        playset_info, mod_info, _ = inspect_schema(connection)
        _validate_mod_insert_schema(mod_info)
        playset = select_playset(connection, set(playset_info), requested_name)
        source_name = str(playset["name"])
        preserved_name = (
            snapshot_name.strip()
            if snapshot_name is not None
            else f"{source_name} (preserved {created_at})"
        )
        if not preserved_name:
            _error("snapshot name cannot be empty")
        if len(preserved_name) > 255:
            _error("snapshot name exceeds the launcher's 255-character limit")

        where = live_playset_clause(set(playset_info)) + " AND name = ?"
        if connection.execute(
            f"SELECT 1 FROM playsets WHERE {where} LIMIT 1", (preserved_name,)
        ).fetchone():
            _error(f'a live playset named "{preserved_name}" already exists')

        rows = playset_mod_rows(connection, str(playset["id"]))
        enabled_rows = [row for row in rows if parse_enabled(row["enabled"])]
        if not enabled_rows:
            _error(f'playset "{source_name}" has no enabled mods')

        snapshot_slug = _slugify(
            snapshot_name
            if snapshot_name is not None
            else f"{source_name}-{filename_timestamp}"
        )
        final_root = mod_directory / snapshot_slug
        if final_root.exists():
            _error(f"snapshot directory already exists: {final_root}")

        width = max(3, len(str(len(enabled_rows) - 1)))
        mods: list[SourceMod] = []
        fingerprint: list[tuple[str, int]] = []
        for source_index, row in enumerate(enabled_rows):
            display_name = str(
                row_value(row, "displayName", "name") or f"mod {source_index}"
            )
            status_value = str(row_value(row, "status") or "")
            if status_value not in GOOD_STATUSES:
                _error(
                    f'mod "{display_name}" has unusable Launcher status '
                    f"{status_value!r}"
                )
            kind, source_path, descriptor_path, descriptor_text = _resolve_source(
                row, paradox_directory, workshop_directory
            )
            identifier = _source_identifier(row, display_name)
            clone_name = (
                f"{source_index:0{width}d}-"
                f"{_slugify(identifier, fallback='mod', limit=64)}"
            )
            registry_filename = f"{snapshot_slug}__{source_index:0{width}d}.mod"
            registry_target = mod_directory / registry_filename
            if registry_target.exists():
                _error(f"launcher descriptor already exists: {registry_target}")
            source_position = parse_position(row["position"], source_index)
            mod = SourceMod(
                source_index=source_index,
                source_position=source_position,
                mod_id=str(row["id"]),
                display_name=display_name,
                source=str(row_value(row, "source") or ""),
                registry_id=(
                    str(row_value(row, "gameRegistryId"))
                    if row_value(row, "gameRegistryId") is not None
                    else None
                ),
                descriptor_path=descriptor_path,
                descriptor_text=descriptor_text,
                source_kind=kind,
                source_path=source_path,
                row=dict(row),
                clone_name=clone_name,
                registry_filename=registry_filename,
            )
            _scan_source(mod)
            mods.append(mod)
            fingerprint.append((mod.mod_id, source_position))

    content_bytes = sum(mod.byte_count for mod in mods)
    margin = max(ONE_GIB, (content_bytes + 19) // 20)
    required_bytes = content_bytes + margin
    try:
        free_bytes = shutil.disk_usage(mod_directory).free
    except OSError as exc:
        _error(f"could not inspect free space under {mod_directory}: {exc}")
    if free_bytes < required_bytes:
        _error(
            f"not enough free space under {mod_directory}: "
            f"need {required_bytes} bytes, have {free_bytes} bytes"
        )

    return PreservationPlan(
        database_path=database_path,
        paradox_directory=paradox_directory,
        mod_directory=mod_directory,
        workshop_directory=workshop_directory,
        source_playset_id=str(playset["id"]),
        source_playset_name=source_name,
        selection_source=selection_source,
        snapshot_name=preserved_name,
        snapshot_slug=snapshot_slug,
        created_at=created_at,
        final_root=final_root,
        mods=mods,
        source_fingerprint=tuple(fingerprint),
        required_bytes=required_bytes,
        free_bytes=free_bytes,
    )


def _copy_file(entry: FileEntry, destination: Path) -> str:
    before = entry.source_path.stat()
    if before.st_size != entry.size or before.st_mtime_ns != entry.mtime_ns:
        _error(f"source changed after preflight: {entry.source_path}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256()
    try:
        with entry.source_path.open("rb") as source, destination.open("xb") as target:
            while chunk := source.read(1024 * 1024):
                target.write(chunk)
                digest.update(chunk)
        shutil.copystat(entry.source_path, destination, follow_symlinks=True)
        after = entry.source_path.stat()
    except OSError as exc:
        _error(f"could not copy {entry.source_path}: {exc}")
    if after.st_size != entry.size or after.st_mtime_ns != entry.mtime_ns:
        _error(f"source changed while being copied: {entry.source_path}")
    return digest.hexdigest()


def _copy_mod(mod: SourceMod, destination: Path, final_relative_path: str) -> str:
    destination.mkdir(parents=True)
    hashes: dict[str, str] = {}
    if mod.source_kind == "directory":
        for entry in mod.files:
            relative = entry.relative_path.as_posix()
            hashes[relative] = _copy_file(
                entry, destination.joinpath(*entry.relative_path.parts)
            )
    else:
        try:
            with zipfile.ZipFile(mod.source_path) as archive:
                for entry in mod.zip_entries:
                    target = destination.joinpath(*entry.relative_path.parts)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    digest = hashlib.sha256()
                    with (
                        archive.open(entry.member_name) as source,
                        target.open("xb") as output,
                    ):
                        while chunk := source.read(1024 * 1024):
                            output.write(chunk)
                            digest.update(chunk)
                    if target.stat().st_size != entry.size:
                        _error(
                            "ZIP member changed size while extracting: "
                            f"{entry.member_name}"
                        )
                    hashes[entry.relative_path.as_posix()] = digest.hexdigest()
        except (OSError, zipfile.BadZipFile, KeyError) as exc:
            _error(f"could not extract {mod.source_path}: {exc}")

    descriptor = _transform_descriptor(mod.descriptor_text, path=None)
    descriptor_path = destination / "descriptor.mod"
    try:
        descriptor_path.write_text(descriptor, encoding="utf-8", newline="")
    except OSError as exc:
        _error(f"could not write {descriptor_path}: {exc}")
    hashes["descriptor.mod"] = hashlib.sha256(descriptor.encode()).hexdigest()
    digest = hashlib.sha256()
    for relative, file_digest in sorted(hashes.items()):
        digest.update(relative.encode("utf-8", "surrogateescape"))
        digest.update(b"\0")
        digest.update(file_digest.encode("ascii"))
        digest.update(b"\n")
    mod.content_sha256 = digest.hexdigest()
    return _transform_descriptor(mod.descriptor_text, path=final_relative_path)


def _manifest_data(
    plan: PreservationPlan, *, registered: bool, playset_id: str | None
) -> dict[str, Any]:
    return {
        "format": MANIFEST_FORMAT,
        "name": plan.snapshot_name,
        "created_at": plan.created_at,
        "source_playset": {
            "id": plan.source_playset_id,
            "name": plan.source_playset_name,
        },
        "registered": registered,
        "launcher_playset_id": playset_id,
        "mods": [
            {
                "position": mod.source_index,
                "source_position": mod.source_position,
                "display_name": mod.display_name,
                "source": mod.source,
                "source_registry_id": mod.registry_id,
                "steam_id": mod.row.get("steamId") or mod.row.get("remoteSteamId"),
                "pdx_id": mod.row.get("pdxId") or mod.row.get("remotePdxId"),
                "version": mod.row.get("version"),
                "required_version": mod.row.get("requiredVersion"),
                "content_path": mod.clone_name,
                "registry_descriptor": mod.registry_filename,
                "file_count": mod.file_count,
                "bytes": mod.byte_count,
                "content_sha256": mod.content_sha256,
                "launcher_mod_id": mod.new_mod_id,
            }
            for mod in plan.mods
        ],
    }


def _write_json_atomic(path: Path, data: dict[str, Any]) -> None:
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        temporary.write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        temporary.replace(path)
    except OSError as exc:
        temporary.unlink(missing_ok=True)
        _error(f"could not write {path}: {exc}")


def _write_text_exclusive(path: Path, content: str) -> None:
    created = False
    try:
        with path.open("x", encoding="utf-8", newline="") as output:
            created = True
            output.write(content)
    except OSError as exc:
        if created:
            path.unlink(missing_ok=True)
        _error(f"could not create {path}: {exc}")


def _readme_text(plan: PreservationPlan) -> str:
    lines = [
        f"Preserved CK3 playset: {plan.snapshot_name}",
        f"Source playset: {plan.source_playset_name}",
        f"Created: {plan.created_at}",
        "",
        "This is a private, update-proof backup of third-party mod content.",
        "Do not distribute it without permission from every source mod author.",
        "The original playset and installed mods were not modified.",
        "",
        "Enabled contents, in load order:",
    ]
    lines.extend(
        f"{mod.source_index}: {mod.display_name} "
        f"({mod.row.get('version') or 'unknown version'})"
        for mod in plan.mods
    )
    return "\n".join(lines) + "\n"


def _stage_snapshot(plan: PreservationPlan) -> tuple[Path, dict[str, str]]:
    staging = plan.mod_directory / f".{plan.snapshot_slug}.{uuid.uuid4().hex}.tmp"
    registries: dict[str, str] = {}
    try:
        staging.mkdir()
        for mod in plan.mods:
            final_relative = f"mod/{plan.snapshot_slug}/{mod.clone_name}"
            registries[mod.registry_filename] = _copy_mod(
                mod, staging / mod.clone_name, final_relative
            )
        _write_text_exclusive(staging / "README.txt", _readme_text(plan))
        _write_json_atomic(
            staging / "snapshot.json",
            _manifest_data(plan, registered=False, playset_id=None),
        )
        return staging, registries
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def _publish_snapshot(
    plan: PreservationPlan, staging: Path, registries: dict[str, str]
) -> None:
    created_descriptors: list[Path] = []
    root_published = False
    try:
        staging.rename(plan.final_root)
        root_published = True
        for filename, content in registries.items():
            target = plan.mod_directory / filename
            _write_text_exclusive(target, content)
            created_descriptors.append(target)
    except BaseException as exc:
        for descriptor in created_descriptors:
            descriptor.unlink(missing_ok=True)
        if root_published:
            shutil.rmtree(plan.final_root, ignore_errors=True)
        else:
            shutil.rmtree(staging, ignore_errors=True)
        if isinstance(exc, OSError):
            _error(f"could not publish snapshot under {plan.mod_directory}: {exc}")
        raise


def _backup_database(database_path: Path, timestamp: str) -> Path:
    backup = database_path.with_name(f"{database_path.name}.preserve-{timestamp}.bak")
    if backup.exists():
        _error(f"database backup already exists: {backup}")
    source = sqlite3.connect(database_path)
    destination = sqlite3.connect(backup)
    try:
        source.backup(destination)
    except BaseException:
        destination.close()
        source.close()
        backup.unlink(missing_ok=True)
        raise
    destination.close()
    source.close()
    return backup


def _insert_local_mod(
    connection: sqlite3.Connection,
    columns: dict[str, sqlite3.Row],
    plan: PreservationPlan,
    mod: SourceMod,
    now_ms: int,
) -> str:
    mod_id = str(uuid.uuid4())
    source = mod.row
    known: dict[str, Any] = {
        "id": mod_id,
        "pdxId": None,
        "steamId": None,
        "gameRegistryId": f"mod/{mod.registry_filename}",
        "name": source.get("name") or mod.display_name,
        "displayName": mod.display_name,
        "descriptionDeprecated": source.get("descriptionDeprecated"),
        "thumbnailUrl": None,
        "thumbnailPath": None,
        "version": source.get("version"),
        "tags": source.get("tags") or "[]",
        "requiredVersion": source.get("requiredVersion"),
        "arch": source.get("arch"),
        "os": source.get("os"),
        "repositoryPath": None,
        "dirPath": str((plan.final_root / mod.clone_name).resolve()),
        "archivePath": None,
        "status": "ready_to_play",
        "source": "local",
        "cause": None,
        "timeUpdated": now_ms,
        "isNew": 1,
        "createdDate": now_ms,
        "subscribedDate": now_ms,
        "size": mod.byte_count,
        "metadataId": None,
        "remotePdxId": None,
        "remoteSteamId": None,
        "metadataVersion": None,
        "isMetadataApplied": 0,
        "metadataStatus": "not_applied",
        "metadataGameId": None,
        "descriptionPdx": None,
        "descriptionSteam": None,
        "shortDescriptionPdx": None,
        "keepLatest": 0,
        "userVersion": None,
        "remotePdxUserId": None,
        "remoteSteamUserId": None,
    }
    values = {name: value for name, value in known.items() if name in columns}
    names = ", ".join(qident(name) for name in values)
    placeholders = ", ".join("?" for _ in values)
    connection.execute(
        f"INSERT INTO mods ({names}) VALUES ({placeholders})", tuple(values.values())
    )
    mod.new_mod_id = mod_id
    return mod_id


def _current_fingerprint(
    connection: sqlite3.Connection, plan: PreservationPlan
) -> tuple[tuple[str, int], ...]:
    playset_info, _, _ = inspect_schema(connection)
    live = live_playset_clause(set(playset_info))
    playset = connection.execute(
        f"SELECT id FROM playsets WHERE id = ? AND {live}",
        (plan.source_playset_id,),
    ).fetchone()
    if playset is None:
        _error("source playset disappeared or was removed during the copy")
    rows = [
        row
        for row in playset_mod_rows(connection, plan.source_playset_id)
        if parse_enabled(row["enabled"])
    ]
    return tuple(
        (str(row["id"]), parse_position(row["position"], index))
        for index, row in enumerate(rows)
    )


def _register_snapshot(plan: PreservationPlan) -> tuple[str, Path]:
    _, backup_timestamp = _utc_timestamp()
    backup = _backup_database(plan.database_path, backup_timestamp)
    connection = connect_database(plan.database_path, readonly=False)
    try:
        connection.execute("BEGIN IMMEDIATE")
        playset_info, mod_info, _ = inspect_schema(connection)
        _validate_mod_insert_schema(mod_info)
        if _current_fingerprint(connection, plan) != plan.source_fingerprint:
            _error(
                "source playset changed during the copy; database registration aborted"
            )
        where = live_playset_clause(set(playset_info)) + " AND name = ?"
        if connection.execute(
            f"SELECT 1 FROM playsets WHERE {where} LIMIT 1", (plan.snapshot_name,)
        ).fetchone():
            _error(f'a live playset named "{plan.snapshot_name}" now exists')

        now_ms = int(datetime.now(UTC).timestamp() * 1000)
        mod_ids = [
            _insert_local_mod(connection, mod_info, plan, mod, now_ms)
            for mod in plan.mods
        ]
        playset_id = create_playset(
            connection,
            playset_info,
            plan.snapshot_name,
            detect_pdx_user_id(connection, set(playset_info)),
        )
        connection.executemany(
            """
            INSERT INTO playsets_mods (playsetId, modId, enabled, position)
            VALUES (?, ?, 1, ?)
            """,
            [(playset_id, mod_id, position) for position, mod_id in enumerate(mod_ids)],
        )
        connection.commit()
        return playset_id, backup
    except BaseException:
        connection.rollback()
        raise
    finally:
        connection.close()


def apply_preservation(plan: PreservationPlan) -> PreservationResult:
    """Copy and register a plan previously returned by :func:`plan_preservation`."""

    if plan.final_root.exists():
        _error(f"snapshot directory already exists: {plan.final_root}")
    for mod in plan.mods:
        descriptor = plan.mod_directory / mod.registry_filename
        if descriptor.exists():
            _error(f"launcher descriptor already exists: {descriptor}")

    staging, registries = _stage_snapshot(plan)
    _publish_snapshot(plan, staging, registries)
    playset_id, backup = _register_snapshot(plan)
    _write_json_atomic(
        plan.final_root / "snapshot.json",
        _manifest_data(plan, registered=True, playset_id=playset_id),
    )
    return PreservationResult(plan=plan, playset_id=playset_id, backup_path=backup)
