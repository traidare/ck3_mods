#!/usr/bin/env python3
"""Freeze an installed CK3 playset as ordered, update-proof local mod copies."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sqlite3
import stat
import sys
import unicodedata
import uuid
import zipfile
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, NoReturn

from ck3_launcher import (
    DATABASE_NAME,
    PARADOX_DIRECTORY_ENV,
    PLAYSET_NAME_ENV,
    connect_database,
    create_playset,
    database_path,
    detect_pdx_user_id,
    inspect_schema,
    live_playset_clause,
    parse_enabled,
    parse_position,
    playset_mod_rows,
    qident,
    requested_playset_name,
    row_value,
    select_playset,
)

WORKSHOP_DIRECTORY_ENV = "CK3_WORKSHOP_DIR"
GOOD_STATUSES = {"ready_to_play", "initialized"}
MANIFEST_FORMAT = "ck3-playset-snapshot-v1"
SKIPPED_DIRECTORIES = {".git"}
DESCRIPTOR_PATH_KEYS = {"path", "archive", "remote_file_id"}
ONE_GIB = 1024**3


class PreservationError(RuntimeError):
    """An expected validation or preservation failure."""


@dataclass(frozen=True)
class FileEntry:
    relative_path: PurePosixPath
    source_path: Path
    size: int
    mtime_ns: int


@dataclass(frozen=True)
class ZipEntry:
    relative_path: PurePosixPath
    member_name: str
    size: int


@dataclass
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
    clone_name: str = ""
    registry_filename: str = ""
    files: list[FileEntry] = field(default_factory=list)
    zip_entries: list[ZipEntry] = field(default_factory=list)
    byte_count: int = 0
    file_count: int = 0
    content_sha256: str | None = None
    new_mod_id: str | None = None


@dataclass
class SnapshotPlan:
    database: Path
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


def error(message: str) -> NoReturn:
    raise PreservationError(message)


def utc_timestamp(now: datetime | None = None) -> tuple[str, str]:
    value = (now or datetime.now(UTC)).astimezone(UTC)
    return value.strftime("%Y-%m-%dT%H:%M:%SZ"), value.strftime("%Y%m%dT%H%M%SZ")


def slugify(value: str, *, fallback: str = "snapshot", limit: int = 80) -> str:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^A-Za-z0-9]+", "-", normalized).strip("-").lower()
    return (slug or fallback)[:limit].rstrip("-") or fallback


def human_size(value: int) -> str:
    size = float(value)
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if size < 1024 or unit == "TiB":
            return f"{size:.2f} {unit}" if unit != "B" else f"{int(size)} B"
        size /= 1024
    raise AssertionError("unreachable")


def safe_registry_path(paradox_directory: Path, registry_id: str | None) -> Path | None:
    if not registry_id:
        return None
    relative = PurePosixPath(registry_id.replace("\\", "/"))
    if relative.is_absolute() or ".." in relative.parts:
        return None
    candidate = paradox_directory.joinpath(*relative.parts)
    return candidate if candidate.is_file() else None


def descriptor_value(text: str, key: str) -> str | None:
    pattern = rf'^\s*{re.escape(key)}\s*=\s*"((?:\\.|[^"\\])*)"'
    for line in text.splitlines():
        match = re.match(pattern, line)
        if match:
            return match.group(1).replace('\\"', '"').replace("\\\\", "\\")
    return None


def transform_descriptor(text: str, *, path: str | None) -> str:
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


def resolve_descriptor(
    row: sqlite3.Row, paradox_directory: Path, source_directory: Path | None
) -> tuple[Path, str]:
    registry_id = row_value(row, "gameRegistryId")
    registry = safe_registry_path(
        paradox_directory, str(registry_id) if registry_id is not None else None
    )
    candidates = [registry]
    if source_directory is not None:
        candidates.append(source_directory / "descriptor.mod")
    for candidate in candidates:
        if candidate is not None and candidate.is_file():
            try:
                return candidate, candidate.read_text(encoding="utf-8-sig")
            except (OSError, UnicodeError) as exc:
                error(f"could not read descriptor {candidate}: {exc}")
    error(
        f'no readable descriptor was found for "{row_value(row, "displayName", "name")}"'
    )


def path_from_descriptor(text: str, paradox_directory: Path, key: str) -> Path | None:
    value = descriptor_value(text, key)
    if not value:
        return None
    candidate = Path(value).expanduser()
    if not candidate.is_absolute():
        candidate = paradox_directory / candidate
    return candidate if candidate.exists() else None


def resolve_source(
    row: sqlite3.Row,
    paradox_directory: Path,
    workshop_directory: Path | None,
) -> tuple[str, Path, Path, str]:
    directory_value = row_value(row, "dirPath")
    directory = Path(str(directory_value)).expanduser() if directory_value else None
    if directory is not None and directory.is_dir():
        descriptor, text = resolve_descriptor(row, paradox_directory, directory)
        return "directory", directory.resolve(), descriptor, text

    descriptor, text = resolve_descriptor(row, paradox_directory, None)
    descriptor_directory = path_from_descriptor(text, paradox_directory, "path")
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
        archive = path_from_descriptor(text, paradox_directory, "archive")
    if archive is not None and archive.is_file():
        if not zipfile.is_zipfile(archive):
            error(f"unsupported non-ZIP mod archive: {archive}")
        return "zip", archive.resolve(), descriptor, text

    error(
        f'could not resolve installed content for "{row_value(row, "displayName", "name")}"'
    )


def iter_tree(
    root: Path,
) -> Iterable[tuple[PurePosixPath, Path, os.stat_result]]:
    def visit(
        physical: Path,
        logical: PurePosixPath,
        ancestors: frozenset[tuple[int, int]],
    ) -> Iterable[tuple[PurePosixPath, Path, os.stat_result]]:
        try:
            followed = physical.stat()
        except OSError as exc:
            error(f"could not inspect {physical}: {exc}")
        inode = (followed.st_dev, followed.st_ino)
        if stat.S_ISDIR(followed.st_mode):
            if inode in ancestors:
                error(f"cyclic directory link found at {physical}")
            try:
                children = sorted(physical.iterdir(), key=lambda item: item.name)
            except OSError as exc:
                error(f"could not list {physical}: {exc}")
            next_ancestors = ancestors | {inode}
            for child in children:
                if child.name in SKIPPED_DIRECTORIES:
                    continue
                yield from visit(child, logical / child.name, next_ancestors)
            return
        if stat.S_ISREG(followed.st_mode):
            yield logical, physical.resolve(), followed
            return
        error(f"unsupported special file in mod content: {physical}")

    yield from visit(root, PurePosixPath(), frozenset())


def safe_zip_path(name: str) -> PurePosixPath:
    normalized = name.replace("\\", "/")
    path = PurePosixPath(normalized)
    if path.is_absolute() or ".." in path.parts or not path.parts:
        error(f"unsafe path in ZIP archive: {name}")
    if re.match(r"^[A-Za-z]:", normalized):
        error(f"unsafe drive path in ZIP archive: {name}")
    return path


def scan_source(mod: SourceMod) -> None:
    if mod.source_kind == "directory":
        for relative, source, info in iter_tree(mod.source_path):
            mod.files.append(
                FileEntry(relative, source, int(info.st_size), int(info.st_mtime_ns))
            )
        mod.files.sort(key=lambda entry: entry.relative_path.as_posix())
        mod.file_count = len(mod.files)
        mod.byte_count = sum(entry.size for entry in mod.files)
        return

    try:
        with zipfile.ZipFile(mod.source_path) as archive:
            for info in archive.infolist():
                relative = safe_zip_path(info.filename)
                if info.is_dir() or any(
                    part in SKIPPED_DIRECTORIES for part in relative.parts
                ):
                    continue
                mode = info.external_attr >> 16
                if stat.S_ISLNK(mode):
                    error(
                        f"symbolic links in ZIP archives are unsupported: {info.filename}"
                    )
                mod.zip_entries.append(
                    ZipEntry(relative, info.filename, info.file_size)
                )
    except (OSError, zipfile.BadZipFile) as exc:
        error(f"could not inspect ZIP archive {mod.source_path}: {exc}")
    mod.zip_entries.sort(key=lambda entry: entry.relative_path.as_posix())
    mod.file_count = len(mod.zip_entries)
    mod.byte_count = sum(entry.size for entry in mod.zip_entries)


def source_identifier(row: sqlite3.Row, fallback: str) -> str:
    registry = row_value(row, "gameRegistryId")
    if registry:
        return PurePosixPath(str(registry).replace("\\", "/")).stem
    remote = row_value(row, "steamId", "remoteSteamId", "pdxId", "remotePdxId")
    return str(remote or fallback)


def validate_mod_insert_schema(columns: dict[str, sqlite3.Row]) -> None:
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
        error(
            "this launcher version has unsupported required mod columns: "
            + ", ".join(sorted(unknown_required))
        )


def prepare_plan(
    args: argparse.Namespace, *, now: datetime | None = None
) -> SnapshotPlan:
    database = database_path(args.db)
    paradox_directory = database.parent
    mod_directory = (
        args.mod_dir.expanduser().resolve()
        if args.mod_dir is not None
        else paradox_directory / "mod"
    )
    if not mod_directory.is_dir():
        error(f"launcher mod directory not found: {mod_directory}")

    workshop_argument = args.workshop_dir
    workshop_directory: Path | None = None
    if workshop_argument is not None:
        workshop_directory = workshop_argument.expanduser().resolve()
    elif configured := os.environ.get(WORKSHOP_DIRECTORY_ENV):
        workshop_directory = Path(configured).expanduser().resolve()

    created_at, filename_timestamp = utc_timestamp(now)
    connection = connect_database(database, readonly=True)
    try:
        playset_info, mod_info, _ = inspect_schema(connection)
        validate_mod_insert_schema(mod_info)
        requested_name, selection_source = requested_playset_name(args.playset)
        playset = select_playset(connection, set(playset_info), requested_name)
        source_name = str(playset["name"])
        snapshot_name = (
            args.name.strip()
            if args.name is not None
            else f"{source_name} (preserved {created_at})"
        )
        if not snapshot_name:
            error("snapshot name cannot be empty")
        if len(snapshot_name) > 255:
            error("snapshot name exceeds the launcher's 255-character limit")

        where = live_playset_clause(set(playset_info)) + " AND name = ?"
        if connection.execute(
            f"SELECT 1 FROM playsets WHERE {where} LIMIT 1", (snapshot_name,)
        ).fetchone():
            error(f'a live playset named "{snapshot_name}" already exists')

        rows = playset_mod_rows(connection, str(playset["id"]))
        enabled_rows = [row for row in rows if parse_enabled(row["enabled"])]
        if not enabled_rows:
            error(f'playset "{source_name}" has no enabled mods')

        snapshot_slug = slugify(
            args.name
            if args.name is not None
            else f"{source_name}-{filename_timestamp}"
        )
        final_root = mod_directory / snapshot_slug
        if final_root.exists():
            error(f"snapshot directory already exists: {final_root}")

        width = max(3, len(str(len(enabled_rows) - 1)))
        mods: list[SourceMod] = []
        fingerprint: list[tuple[str, int]] = []
        for source_index, row in enumerate(enabled_rows):
            display_name = str(
                row_value(row, "displayName", "name") or f"mod {source_index}"
            )
            status_value = str(row_value(row, "status") or "")
            if status_value not in GOOD_STATUSES:
                error(
                    f'mod "{display_name}" has unusable Launcher status {status_value!r}'
                )
            kind, source_path, descriptor_path, descriptor_text = resolve_source(
                row, paradox_directory, workshop_directory
            )
            identifier = source_identifier(row, display_name)
            clone_name = f"{source_index:0{width}d}-{slugify(identifier, fallback='mod', limit=64)}"
            registry_filename = f"{snapshot_slug}__{source_index:0{width}d}.mod"
            registry_target = mod_directory / registry_filename
            if registry_target.exists():
                error(f"launcher descriptor already exists: {registry_target}")
            row_data = {key: row[key] for key in row.keys()}
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
                row=row_data,
                clone_name=clone_name,
                registry_filename=registry_filename,
            )
            scan_source(mod)
            mods.append(mod)
            fingerprint.append((mod.mod_id, source_position))
    finally:
        connection.close()

    content_bytes = sum(mod.byte_count for mod in mods)
    margin = max(ONE_GIB, (content_bytes + 19) // 20)
    required_bytes = content_bytes + margin
    free_bytes = shutil.disk_usage(mod_directory).free
    if free_bytes < required_bytes:
        error(
            f"not enough free space under {mod_directory}: "
            f"need {human_size(required_bytes)}, have {human_size(free_bytes)}"
        )

    return SnapshotPlan(
        database=database,
        mod_directory=mod_directory,
        workshop_directory=workshop_directory,
        source_playset_id=str(playset["id"]),
        source_playset_name=source_name,
        selection_source=selection_source,
        snapshot_name=snapshot_name,
        snapshot_slug=snapshot_slug,
        created_at=created_at,
        final_root=final_root,
        mods=mods,
        source_fingerprint=tuple(fingerprint),
        required_bytes=required_bytes,
        free_bytes=free_bytes,
    )


def print_plan(plan: SnapshotPlan, *, dry_run: bool) -> None:
    local_count = sum(mod.source.lower() == "local" for mod in plan.mods)
    archive_count = sum(mod.source_kind == "zip" for mod in plan.mods)
    content_bytes = sum(mod.byte_count for mod in plan.mods)
    print(f"Source playset: {plan.source_playset_name}")
    print(f"Selected by: {plan.selection_source}")
    print(f"Preserved playset: {plan.snapshot_name}")
    print(
        f"Enabled mods: {len(plan.mods)} "
        f"({local_count} local, {len(plan.mods) - local_count} remote; "
        f"{archive_count} archived)"
    )
    print(f"Content to copy: {human_size(content_bytes)}")
    print(
        f"Space check: {human_size(plan.required_bytes)} required; {human_size(plan.free_bytes)} free"
    )
    print(f"Snapshot directory: {plan.final_root}")
    print(f"Launcher descriptors: {len(plan.mods)} alongside {plan.final_root}")
    if dry_run:
        print("Dry run complete; no files or database rows were changed.")


def copy_file(entry: FileEntry, destination: Path) -> str:
    before = entry.source_path.stat()
    if before.st_size != entry.size or before.st_mtime_ns != entry.mtime_ns:
        error(f"source changed after preflight: {entry.source_path}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256()
    try:
        with entry.source_path.open("rb") as source, destination.open("xb") as target:
            while chunk := source.read(1024 * 1024):
                target.write(chunk)
                digest.update(chunk)
        shutil.copystat(entry.source_path, destination, follow_symlinks=True)
    except OSError as exc:
        error(f"could not copy {entry.source_path}: {exc}")
    after = entry.source_path.stat()
    if after.st_size != entry.size or after.st_mtime_ns != entry.mtime_ns:
        error(f"source changed while being copied: {entry.source_path}")
    return digest.hexdigest()


def copy_directory_mod(mod: SourceMod, destination: Path) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for entry in mod.files:
        relative = entry.relative_path.as_posix()
        hashes[relative] = copy_file(
            entry, destination.joinpath(*entry.relative_path.parts)
        )
    return hashes


def copy_zip_mod(mod: SourceMod, destination: Path) -> dict[str, str]:
    hashes: dict[str, str] = {}
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
                    error(
                        f"ZIP member changed size while extracting: {entry.member_name}"
                    )
                hashes[entry.relative_path.as_posix()] = digest.hexdigest()
    except (OSError, zipfile.BadZipFile, KeyError) as exc:
        error(f"could not extract {mod.source_path}: {exc}")
    return hashes


def tree_digest(hashes: dict[str, str]) -> str:
    digest = hashlib.sha256()
    for relative, file_digest in sorted(hashes.items()):
        digest.update(relative.encode("utf-8", "surrogateescape"))
        digest.update(b"\0")
        digest.update(file_digest.encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest()


def write_text_exclusive(path: Path, content: str) -> None:
    created = False
    try:
        with path.open("x", encoding="utf-8", newline="") as output:
            created = True
            output.write(content)
    except OSError as exc:
        if created:
            path.unlink(missing_ok=True)
        error(f"could not create {path}: {exc}")


def copy_mod(mod: SourceMod, destination: Path, final_relative_path: str) -> str:
    destination.mkdir(parents=True)
    hashes = (
        copy_directory_mod(mod, destination)
        if mod.source_kind == "directory"
        else copy_zip_mod(mod, destination)
    )
    descriptor = transform_descriptor(mod.descriptor_text, path=None)
    descriptor_path = destination / "descriptor.mod"
    try:
        descriptor_path.write_text(descriptor, encoding="utf-8", newline="")
    except OSError as exc:
        error(f"could not write {descriptor_path}: {exc}")
    hashes["descriptor.mod"] = hashlib.sha256(descriptor.encode("utf-8")).hexdigest()
    registry = transform_descriptor(mod.descriptor_text, path=final_relative_path)
    mod.content_sha256 = tree_digest(hashes)
    return registry


def manifest_data(
    plan: SnapshotPlan, *, registered: bool, playset_id: str | None
) -> dict[str, Any]:
    mods = []
    for mod in plan.mods:
        row = mod.row
        mods.append(
            {
                "position": mod.source_index,
                "source_position": mod.source_position,
                "display_name": mod.display_name,
                "source": mod.source,
                "source_registry_id": mod.registry_id,
                "steam_id": row.get("steamId") or row.get("remoteSteamId"),
                "pdx_id": row.get("pdxId") or row.get("remotePdxId"),
                "version": row.get("version"),
                "required_version": row.get("requiredVersion"),
                "content_path": mod.clone_name,
                "registry_descriptor": mod.registry_filename,
                "file_count": mod.file_count,
                "bytes": mod.byte_count,
                "content_sha256": mod.content_sha256,
                "launcher_mod_id": mod.new_mod_id,
            }
        )
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
        "mods": mods,
    }


def write_json_atomic(path: Path, data: dict[str, Any]) -> None:
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        temporary.write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        temporary.replace(path)
    except OSError as exc:
        temporary.unlink(missing_ok=True)
        error(f"could not write {path}: {exc}")


def readme_text(plan: SnapshotPlan) -> str:
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
        f"{mod.source_index}: {mod.display_name} ({mod.row.get('version') or 'unknown version'})"
        for mod in plan.mods
    )
    return "\n".join(lines) + "\n"


def stage_snapshot(plan: SnapshotPlan) -> tuple[Path, dict[str, str]]:
    staging = plan.mod_directory / f".{plan.snapshot_slug}.{uuid.uuid4().hex}.tmp"
    registries: dict[str, str] = {}
    try:
        staging.mkdir()
        for mod in plan.mods:
            print(
                f"Copying {mod.source_index + 1}/{len(plan.mods)}: {mod.display_name}"
            )
            final_relative = f"mod/{plan.snapshot_slug}/{mod.clone_name}"
            registries[mod.registry_filename] = copy_mod(
                mod, staging / mod.clone_name, final_relative
            )
        write_text_exclusive(staging / "README.txt", readme_text(plan))
        write_json_atomic(
            staging / "snapshot.json",
            manifest_data(plan, registered=False, playset_id=None),
        )
        return staging, registries
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def publish_snapshot(
    plan: SnapshotPlan, staging: Path, registries: dict[str, str]
) -> None:
    created_descriptors: list[Path] = []
    root_published = False
    try:
        plan.final_root.mkdir()
        root_published = True
        for child in staging.iterdir():
            child.rename(plan.final_root / child.name)
        staging.rmdir()
        for filename, content in registries.items():
            target = plan.mod_directory / filename
            write_text_exclusive(target, content)
            created_descriptors.append(target)
    except BaseException as exc:
        for descriptor in created_descriptors:
            descriptor.unlink(missing_ok=True)
        if root_published:
            shutil.rmtree(plan.final_root, ignore_errors=True)
        shutil.rmtree(staging, ignore_errors=True)
        if isinstance(exc, OSError):
            error(f"could not publish snapshot under {plan.mod_directory}: {exc}")
        raise


def backup_database(database: Path, timestamp: str) -> Path:
    backup = database.with_name(f"{database.name}.preserve-{timestamp}.bak")
    if backup.exists():
        error(f"database backup already exists: {backup}")
    source = sqlite3.connect(database)
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


def insert_local_mod(
    connection: sqlite3.Connection,
    columns: dict[str, sqlite3.Row],
    plan: SnapshotPlan,
    mod: SourceMod,
    now_ms: int,
) -> str:
    mod_id = str(uuid.uuid4())
    clone_path = (plan.final_root / mod.clone_name).resolve()
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
        "dirPath": str(clone_path),
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


def current_fingerprint(
    connection: sqlite3.Connection, plan: SnapshotPlan
) -> tuple[tuple[str, int], ...]:
    playset_info, _, _ = inspect_schema(connection)
    live = live_playset_clause(set(playset_info))
    playset = connection.execute(
        f"SELECT * FROM playsets WHERE id = ? AND {live}", (plan.source_playset_id,)
    ).fetchone()
    if playset is None:
        error("source playset disappeared or was removed during the copy")
    rows = [
        row
        for row in playset_mod_rows(connection, plan.source_playset_id)
        if parse_enabled(row["enabled"])
    ]
    return tuple(
        (str(row["id"]), parse_position(row["position"], index))
        for index, row in enumerate(rows)
    )


def register_snapshot(plan: SnapshotPlan) -> tuple[str, Path]:
    _, backup_timestamp = utc_timestamp()
    backup = backup_database(plan.database, backup_timestamp)
    connection = connect_database(plan.database, readonly=False)
    try:
        connection.execute("BEGIN IMMEDIATE")
        playset_info, mod_info, _ = inspect_schema(connection)
        if current_fingerprint(connection, plan) != plan.source_fingerprint:
            error(
                "source playset changed during the copy; database registration aborted"
            )
        where = live_playset_clause(set(playset_info)) + " AND name = ?"
        if connection.execute(
            f"SELECT 1 FROM playsets WHERE {where} LIMIT 1", (plan.snapshot_name,)
        ).fetchone():
            error(f'a live playset named "{plan.snapshot_name}" now exists')

        now_ms = int(datetime.now(UTC).timestamp() * 1000)
        mod_ids = [
            insert_local_mod(connection, mod_info, plan, mod, now_ms)
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


def preserve(args: argparse.Namespace) -> None:
    plan = prepare_plan(args)
    print_plan(plan, dry_run=args.dry_run)
    if args.dry_run:
        return

    staging, registries = stage_snapshot(plan)
    publish_snapshot(plan, staging, registries)
    try:
        playset_id, backup = register_snapshot(plan)
    except BaseException:
        print(
            "warning: snapshot files were preserved but Launcher registration failed; "
            f"see {plan.final_root / 'snapshot.json'}",
            file=sys.stderr,
        )
        raise

    write_json_atomic(
        plan.final_root / "snapshot.json",
        manifest_data(plan, registered=True, playset_id=playset_id),
    )
    print(
        f'Created preserved playset "{plan.snapshot_name}" with {len(plan.mods)} local mods.'
    )
    print(f"Launcher database backup: {backup}")
    print("Restart the Paradox Launcher before using the new playset.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Copy every enabled CK3 playset mod into independent local storage and "
            "register an update-proof Launcher playset. Close Steam, CK3, and the "
            "Paradox Launcher before running without --dry-run."
        )
    )
    parser.add_argument(
        "playset",
        nargs="?",
        help=(
            "exact source playset name; defaults to $"
            f"{PLAYSET_NAME_ENV}, then the active playset"
        ),
    )
    parser.add_argument(
        "--name",
        help="new playset name (default: source name plus a UTC preservation timestamp)",
    )
    parser.add_argument(
        "--db",
        type=Path,
        help=f"launcher database (default: ${PARADOX_DIRECTORY_ENV}/{DATABASE_NAME})",
    )
    parser.add_argument(
        "--mod-dir",
        type=Path,
        help="launcher mod directory (default: the database directory's mod/ folder)",
    )
    parser.add_argument(
        "--workshop-dir",
        type=Path,
        help=f"Steam Workshop content directory (default: ${WORKSHOP_DIRECTORY_ENV})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="validate sources, collisions, schema, and disk space without writing",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    try:
        preserve(args)
    except PreservationError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    except sqlite3.OperationalError as exc:
        print(
            f"error: SQLite error: {exc}\n"
            "Make sure CK3 and the Paradox Launcher are completely closed.",
            file=sys.stderr,
        )
        raise SystemExit(1) from exc
    except sqlite3.IntegrityError as exc:
        print(f"error: database integrity error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
