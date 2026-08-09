"""Portable playset models and Launcher import/export operations."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict, dataclass, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .launcher import (
    LauncherError,
    create_playset,
    database,
    detect_pdx_user_id,
    first_value,
    inspect_schema,
    live_playset_clause,
    parse_enabled,
    parse_position,
    playset_mod_rows,
    qident,
    row_value,
    select_playset,
    update_replaced_playset,
)


@dataclass(frozen=True, slots=True)
class PlaysetMod:
    display_name: str
    enabled: bool
    position: int
    source: str = ""
    steam_id: str = ""
    pdx_id: str = ""
    game_registry_id: str = ""

    @property
    def stable_id(self) -> str:
        if self.game_registry_id:
            return "local:" + normalize_registry_id(self.game_registry_id)
        if self.steam_id:
            return "steam:" + self.steam_id
        if self.pdx_id:
            return "pdx:" + self.pdx_id
        return "name:" + self.display_name

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "displayName": self.display_name,
            "enabled": self.enabled,
            "position": self.position,
        }
        if self.source:
            result["source"] = self.source
        if self.game_registry_id:
            result["gameRegistryId"] = normalize_registry_id(self.game_registry_id)
        if self.steam_id:
            result["steamId"] = self.steam_id
        if self.pdx_id:
            result["pdxId"] = self.pdx_id
        return result


@dataclass(frozen=True, slots=True)
class Playset:
    name: str
    mods: tuple[PlaysetMod, ...]
    game: str = "ck3"
    selection_source: str = "file"

    @property
    def enabled_mods(self) -> tuple[PlaysetMod, ...]:
        return tuple(mod for mod in self.mods if mod.enabled)

    def to_dict(self) -> dict[str, Any]:
        return {
            "game": self.game,
            "name": self.name,
            "mods": [mod.to_dict() for mod in self.mods],
        }


@dataclass(frozen=True, slots=True)
class UnresolvedMod:
    source_index: int
    display_name: str
    reason: str


@dataclass(frozen=True, slots=True)
class ResolvedMod:
    mod_id: str
    display_name: str
    enabled: bool
    source_position: int
    source_index: int


@dataclass(frozen=True, slots=True)
class ImportPlan:
    name: str
    action: str
    resolved: tuple[ResolvedMod, ...]
    unresolved: tuple[UnresolvedMod, ...]
    existing_playset_id: str | None
    backup_path: Path | None = None

    def to_dict(self) -> dict[str, Any]:
        result = {
            "name": self.name,
            "action": self.action,
            "resolved": [asdict(mod) for mod in self.resolved],
            "unresolved": [asdict(mod) for mod in self.unresolved],
        }
        if self.backup_path is not None:
            result["backupPath"] = str(self.backup_path)
        return result


@dataclass(frozen=True, slots=True)
class ChangedMod:
    stable_id: str
    before: PlaysetMod
    after: PlaysetMod

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.stable_id,
            "before": self.before.to_dict(),
            "after": self.after.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class PlaysetDiff:
    before_name: str
    after_name: str
    added: tuple[PlaysetMod, ...]
    removed: tuple[PlaysetMod, ...]
    changed: tuple[ChangedMod, ...]

    @property
    def current(self) -> bool:
        return not (self.added or self.removed or self.changed)

    def to_dict(self) -> dict[str, Any]:
        return {
            "before": self.before_name,
            "after": self.after_name,
            "added": [mod.to_dict() for mod in self.added],
            "removed": [mod.to_dict() for mod in self.removed],
            "changed": [mod.to_dict() for mod in self.changed],
        }


def normalize_registry_id(identifier: str) -> str:
    return Path(identifier.replace("\\", "/")).as_posix()


def requested_playset_name(
    argument: str | None, configured: str | None
) -> tuple[str | None, str]:
    if argument is not None and argument.strip():
        return argument.strip(), "command argument"
    if configured is not None and configured.strip():
        return configured.strip(), "CK3_PLAYSET_NAME"
    return None, "active Launcher playset"


def mod_from_row(row: sqlite3.Row, fallback_position: int) -> PlaysetMod:
    display_name = str(row_value(row, "displayName", "name") or "<unnamed mod>")
    source = str(row_value(row, "source") or "").lower()
    return PlaysetMod(
        display_name=display_name,
        enabled=parse_enabled(row["enabled"]),
        position=parse_position(row["position"], fallback_position),
        source=source,
        steam_id=str(row_value(row, "steamId", "remoteSteamId") or ""),
        pdx_id=str(row_value(row, "pdxId", "remotePdxId") or ""),
        game_registry_id=str(row_value(row, "gameRegistryId") or ""),
    )


def load_live_playset(
    database_path: Path,
    *,
    name: str | None = None,
    configured_name: str | None = None,
) -> Playset:
    requested_name, selection_source = requested_playset_name(name, configured_name)
    with database(database_path) as connection:
        playset_info, _, _ = inspect_schema(connection)
        row = select_playset(connection, set(playset_info), requested_name)
        mods = tuple(
            mod_from_row(mod_row, index)
            for index, mod_row in enumerate(
                playset_mod_rows(connection, str(row["id"]))
            )
        )
        return Playset(
            name=str(row["name"]),
            mods=mods,
            selection_source=selection_source,
        )


def load_playset_file(path: Path) -> Playset:
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as error:
        raise LauncherError(f"could not read playset JSON: {error}") from error
    if not isinstance(data, dict) or not isinstance(data.get("mods"), list):
        raise LauncherError('expected a JSON object containing a "mods" array')
    name = str(data.get("name") or path.stem).strip()
    if not name:
        raise LauncherError("playset name is empty")
    game = str(data.get("game") or "ck3").strip().lower()
    mods: list[PlaysetMod] = []
    for index, raw in enumerate(data["mods"]):
        if not isinstance(raw, dict):
            raise LauncherError(f"playset mod entry {index} is not an object")
        mods.append(
            PlaysetMod(
                display_name=str(
                    first_value(raw, "displayName", "name") or f"entry {index}"
                ),
                enabled=parse_enabled(raw.get("enabled", True)),
                position=parse_position(raw.get("position"), index),
                source=str(first_value(raw, "source") or "").lower(),
                steam_id=str(
                    first_value(raw, "steamId", "steamID", "remoteSteamId") or ""
                ),
                pdx_id=str(first_value(raw, "pdxId", "pdxID", "remotePdxId") or ""),
                game_registry_id=str(first_value(raw, "gameRegistryId") or ""),
            )
        )
    mods.sort(key=lambda mod: (mod.position, mod.display_name))
    return Playset(name=name, game=game, mods=tuple(mods))


def dump_playset(playset: Playset, path: Path | None = None) -> str:
    text = json.dumps(playset.to_dict(), ensure_ascii=False, indent=2) + "\n"
    if path is not None:
        path.write_text(text, encoding="utf-8")
    return text


def playset_summary(playset: Playset) -> dict[str, Any]:
    enabled = playset.enabled_mods
    local = tuple(mod for mod in enabled if mod.source == "local")
    workshop = tuple(mod for mod in enabled if mod.steam_id)
    disabled_local = tuple(
        mod for mod in playset.mods if not mod.enabled and mod.source == "local"
    )
    return {
        "name": playset.name,
        "selectionSource": playset.selection_source,
        "total": len(playset.mods),
        "enabled": len(enabled),
        "local": len(local),
        "workshop": len(workshop),
        "enabledLocalMods": [mod.to_dict() for mod in local],
        "disabledLocalMods": [mod.to_dict() for mod in disabled_local],
    }


def diff_playsets(before: Playset, after: Playset) -> PlaysetDiff:
    """Compare portable mod membership and settings, ignoring load positions."""

    def indexed(playset: Playset) -> dict[str, PlaysetMod]:
        result: dict[str, PlaysetMod] = {}
        for mod in playset.mods:
            if mod.stable_id in result:
                raise LauncherError(
                    f"playset {playset.name!r} has duplicate mod ID {mod.stable_id!r}"
                )
            result[mod.stable_id] = mod
        return result

    def comparable(mod: PlaysetMod) -> dict[str, Any]:
        value = mod.to_dict()
        value.pop("position", None)
        return value

    left = indexed(before)
    right = indexed(after)
    added = tuple(right[stable_id] for stable_id in sorted(right.keys() - left.keys()))
    removed = tuple(left[stable_id] for stable_id in sorted(left.keys() - right.keys()))
    changed = tuple(
        ChangedMod(stable_id, left[stable_id], right[stable_id])
        for stable_id in sorted(left.keys() & right.keys())
        if comparable(left[stable_id]) != comparable(right[stable_id])
    )
    return PlaysetDiff(before.name, after.name, added, removed, changed)


def _unique_rows(rows: list[sqlite3.Row]) -> list[sqlite3.Row]:
    return list({str(row["id"]): row for row in rows}.values())


def _choose_candidate(
    rows: list[sqlite3.Row],
) -> tuple[sqlite3.Row | None, str | None]:
    rows = _unique_rows(rows)
    if not rows:
        return None, "not installed or not yet scanned"
    if len(rows) == 1:
        return rows[0], None
    ready = [row for row in rows if str(row["status"] or "") == "ready_to_play"]
    if len(ready) == 1:
        return ready[0], None
    return None, "ambiguous match"


def _candidate_rows(
    connection: sqlite3.Connection,
    mod_columns: set[str],
    columns: tuple[str, ...],
    value: str,
    *,
    local_only: bool = False,
) -> list[sqlite3.Row] | None:
    available = [column for column in columns if column in mod_columns]
    if not value or not available:
        return None
    predicates = [f"CAST({qident(column)} AS TEXT) = ?" for column in available]
    where = "(" + " OR ".join(predicates) + ")"
    if local_only and "source" in mod_columns:
        where += " AND source = 'local'"
    status = qident("status") if "status" in mod_columns else "NULL AS status"
    return connection.execute(
        f"SELECT id, displayName, {status} FROM mods WHERE {where}",
        [value] * len(available),
    ).fetchall()


def _resolve_mods(
    connection: sqlite3.Connection,
    mod_columns: set[str],
    playset: Playset,
) -> tuple[tuple[ResolvedMod, ...], tuple[UnresolvedMod, ...]]:
    resolved: list[ResolvedMod] = []
    unresolved: list[UnresolvedMod] = []
    seen: set[str] = set()
    for index, mod in enumerate(playset.mods):
        rows: list[sqlite3.Row] | None = None
        match_kind = "name"
        if mod.source == "local" and mod.game_registry_id:
            rows = _candidate_rows(
                connection,
                mod_columns,
                ("gameRegistryId",),
                mod.game_registry_id,
                local_only=True,
            )
            match_kind = f"local registry ID {mod.game_registry_id}"
        if rows is None and mod.steam_id:
            rows = _candidate_rows(
                connection,
                mod_columns,
                ("steamId", "remoteSteamId"),
                mod.steam_id,
            )
            match_kind = f"Steam ID {mod.steam_id}"
        if rows is None and mod.pdx_id:
            rows = _candidate_rows(
                connection,
                mod_columns,
                ("pdxId", "remotePdxId"),
                mod.pdx_id,
            )
            match_kind = f"Paradox ID {mod.pdx_id}"
        if rows is None:
            rows = (
                _candidate_rows(
                    connection,
                    mod_columns,
                    tuple(
                        column
                        for column in ("displayName", "name")
                        if column in mod_columns
                    ),
                    mod.display_name,
                )
                or []
            )
        candidate, reason = _choose_candidate(rows)
        if candidate is None:
            unresolved.append(
                UnresolvedMod(index, mod.display_name, f"{reason} ({match_kind})")
            )
            continue
        mod_id = str(candidate["id"])
        if mod_id in seen:
            unresolved.append(UnresolvedMod(index, mod.display_name, "duplicate mod"))
            continue
        seen.add(mod_id)
        resolved.append(
            ResolvedMod(
                mod_id=mod_id,
                display_name=str(candidate["displayName"] or mod.display_name),
                enabled=mod.enabled,
                source_position=mod.position,
                source_index=index,
            )
        )
    resolved.sort(key=lambda item: (item.source_position, item.source_index))
    return tuple(resolved), tuple(unresolved)


def plan_import(database_path: Path, playset: Playset) -> ImportPlan:
    if len(playset.name) > 255:
        raise LauncherError("playset name exceeds the launcher's 255-character limit")
    with database(database_path) as connection:
        playset_info, mod_info, _ = inspect_schema(connection)
        resolved, unresolved = _resolve_mods(connection, set(mod_info), playset)
        where = live_playset_clause(set(playset_info)) + " AND name = ?"
        existing = connection.execute(
            f"SELECT id FROM playsets WHERE {where}", (playset.name,)
        ).fetchall()
        if len(existing) > 1:
            raise LauncherError(
                f'more than one non-removed playset is named "{playset.name}"'
            )
        existing_id = str(existing[0]["id"]) if existing else None
        return ImportPlan(
            name=playset.name,
            action="replace" if existing_id else "create",
            resolved=resolved,
            unresolved=unresolved,
            existing_playset_id=existing_id,
        )


def apply_import(
    database_path: Path,
    playset: Playset,
    *,
    allow_missing: bool = False,
) -> ImportPlan:
    plan = plan_import(database_path, playset)
    if plan.unresolved and not allow_missing:
        raise LauncherError(
            f"import has {len(plan.unresolved)} unresolved mod(s); "
            "pass allow_missing=True to omit them"
        )
    backup_path = _backup_launcher_database(database_path)
    with database(database_path, readonly=False) as connection:
        playset_info, _, _ = inspect_schema(connection)
        try:
            connection.execute("BEGIN IMMEDIATE")
            if plan.existing_playset_id:
                playset_id = plan.existing_playset_id
                update_replaced_playset(connection, set(playset_info), playset_id)
                connection.execute(
                    "DELETE FROM playsets_mods WHERE playsetId = ?", (playset_id,)
                )
            else:
                playset_id = create_playset(
                    connection,
                    playset_info,
                    playset.name,
                    detect_pdx_user_id(connection, set(playset_info)),
                )
            connection.executemany(
                """
                INSERT INTO playsets_mods (playsetId, modId, enabled, position)
                VALUES (?, ?, ?, ?)
                """,
                [
                    (playset_id, mod.mod_id, int(mod.enabled), position)
                    for position, mod in enumerate(plan.resolved)
                ],
            )
            connection.commit()
        except Exception as error:
            connection.rollback()
            raise LauncherError(
                f"playset import failed; database backup is {backup_path}: {error}"
            ) from error
    return replace(plan, backup_path=backup_path)


def _backup_launcher_database(database_path: Path) -> Path:
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    backup_path = database_path.with_name(f"{database_path.name}.ck3mm-{timestamp}.bak")
    try:
        with database(database_path) as source, sqlite3.connect(backup_path) as target:
            source.backup(target)
    except Exception:
        backup_path.unlink(missing_ok=True)
        raise
    return backup_path
