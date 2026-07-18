#!/usr/bin/env python3
"""Import and export Crusader Kings III Paradox Launcher playsets."""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, NoReturn

DATABASE_NAME = "launcher-v2.sqlite"
PARADOX_DIRECTORY_ENV = "CK3_PARADOX_DIR"
PLAYSET_NAME_ENV = "CK3_PLAYSET_NAME"


@dataclass(frozen=True)
class ResolvedMod:
    mod_id: str
    display_name: str
    enabled: int
    source_position: int
    source_index: int


@dataclass(frozen=True)
class UnresolvedMod:
    source_index: int
    display_name: str
    reason: str


def fail(message: str, exit_code: int = 1) -> NoReturn:
    print(f"error: {message}", file=sys.stderr)
    raise SystemExit(exit_code)


def qident(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def first_value(obj: dict[str, Any], *names: str) -> Any:
    for name in names:
        if name in obj and obj[name] not in (None, ""):
            return obj[name]
    return None


def row_value(row: sqlite3.Row, *names: str) -> Any:
    columns = set(row.keys())
    for name in names:
        if name in columns and row[name] not in (None, ""):
            return row[name]
    return None


def parse_enabled(value: Any) -> int:
    if value is None:
        return 1
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float)):
        return int(value != 0)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"0", "false", "no", "off", "disabled"}:
            return 0
        if normalized in {"1", "true", "yes", "on", "enabled"}:
            return 1
    return int(bool(value))


def parse_position(value: Any, fallback: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError, OverflowError):
        return fallback


def database_path(argument: Path | None) -> Path:
    if argument is not None:
        path = argument.expanduser()
    else:
        directory = os.environ.get(PARADOX_DIRECTORY_ENV)
        if not directory:
            fail(
                f"pass --db or set {PARADOX_DIRECTORY_ENV} to the CK3 user-data directory"
            )
        path = Path(directory).expanduser() / DATABASE_NAME

    if not path.is_file():
        fail(f"launcher database not found: {path}")
    return path.resolve()


def connect_database(path: Path, *, readonly: bool) -> sqlite3.Connection:
    if readonly:
        connection = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True, timeout=3)
    else:
        connection = sqlite3.connect(path, timeout=3)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 3000")
    return connection


def table_info(connection: sqlite3.Connection, table: str) -> dict[str, sqlite3.Row]:
    return {
        str(row["name"]): row
        for row in connection.execute(f"PRAGMA table_info({qident(table)})")
    }


def inspect_schema(
    connection: sqlite3.Connection,
) -> tuple[dict[str, sqlite3.Row], dict[str, sqlite3.Row], dict[str, sqlite3.Row]]:
    tables = {
        str(row[0])
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        )
    }
    required_tables = {"playsets", "mods", "playsets_mods"}
    missing_tables = required_tables - tables
    if missing_tables:
        fail(
            "unexpected launcher database; missing tables: "
            + ", ".join(sorted(missing_tables))
        )

    playset_info = table_info(connection, "playsets")
    mod_info = table_info(connection, "mods")
    link_info = table_info(connection, "playsets_mods")

    required_columns = {
        "playsets": ({"id", "name", "createdOn"}, set(playset_info)),
        "mods": ({"id", "displayName"}, set(mod_info)),
        "playsets_mods": (
            {"playsetId", "modId", "enabled", "position"},
            set(link_info),
        ),
    }
    for table, (required, available) in required_columns.items():
        missing = required - available
        if missing:
            fail(
                f"unexpected {table} table schema; missing columns: "
                + ", ".join(sorted(missing))
            )

    return playset_info, mod_info, link_info


def live_playset_clause(columns: set[str]) -> str:
    if "isRemoved" in columns:
        return "COALESCE(isRemoved, 0) = 0"
    return "1 = 1"


def select_playset(
    connection: sqlite3.Connection,
    columns: set[str],
    name: str | None,
) -> sqlite3.Row:
    where = live_playset_clause(columns)
    params: tuple[Any, ...] = ()
    label = "active playset"

    if name is not None:
        where += " AND name = ?"
        params = (name,)
        label = f'playset named "{name}"'
    else:
        if "isActive" not in columns:
            fail("the launcher schema cannot identify an active playset")
        where += " AND COALESCE(isActive, 0) = 1"

    rows = connection.execute(
        f"SELECT * FROM playsets WHERE {where}", params
    ).fetchall()
    if not rows:
        fail(f"no {label} was found")
    if len(rows) > 1:
        fail(f"more than one {label} was found")
    return rows[0]


def requested_playset_name(argument: str | None) -> tuple[str | None, str]:
    """Resolve the requested playset without reading or changing launcher state."""
    if argument is not None and argument.strip():
        return argument.strip(), "command argument"

    configured = os.environ.get(PLAYSET_NAME_ENV, "").strip()
    if configured:
        return configured, f"${PLAYSET_NAME_ENV}"

    return None, "active Launcher playset"


def playset_mod_rows(
    connection: sqlite3.Connection, playset_id: str
) -> list[sqlite3.Row]:
    return connection.execute(
        """
        SELECT pm.enabled, pm.position, m.*
        FROM playsets_mods AS pm
        JOIN mods AS m ON m.id = pm.modId
        WHERE pm.playsetId = ?
        ORDER BY pm.position, m.id
        """,
        (playset_id,),
    ).fetchall()


def export_mod(row: sqlite3.Row, fallback_position: int) -> dict[str, Any]:
    display_name = str(row_value(row, "displayName", "name") or "<unnamed mod>")
    entry: dict[str, Any] = {
        "displayName": display_name,
        "enabled": bool(parse_enabled(row["enabled"])),
        "position": parse_position(row["position"], fallback_position),
    }

    source = str(row_value(row, "source") or "").lower()
    if source == "local":
        entry["source"] = "local"
        registry_id = row_value(row, "gameRegistryId")
        if registry_id is not None:
            entry["gameRegistryId"] = str(registry_id)
        else:
            print(
                f'warning: local mod "{display_name}" has no gameRegistryId; '
                "import will have to match it by name",
                file=sys.stderr,
            )
        return entry

    steam_id = row_value(row, "steamId", "remoteSteamId")
    pdx_id = row_value(row, "pdxId", "remotePdxId")
    if steam_id is not None:
        entry["steamId"] = str(steam_id)
    elif pdx_id is not None:
        entry["pdxId"] = str(pdx_id)
    else:
        print(
            f'warning: mod "{display_name}" has no portable identifier; '
            "import will have to match it by name",
            file=sys.stderr,
        )
    return entry


def export_playset(args: argparse.Namespace) -> None:
    path = database_path(args.db)
    connection = connect_database(path, readonly=True)
    try:
        playset_info, _, _ = inspect_schema(connection)
        requested_name, _ = requested_playset_name(args.playset)
        playset = select_playset(connection, set(playset_info), requested_name)
        rows = playset_mod_rows(connection, str(playset["id"]))

        data = {
            "game": "ck3",
            "name": str(playset["name"]),
            "mods": [export_mod(row, index) for index, row in enumerate(rows)],
        }
        json.dump(data, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
    finally:
        connection.close()


def summary_playset(args: argparse.Namespace) -> None:
    """Print the live launcher order needed for routine compatibility work."""
    path = database_path(args.db)
    connection = connect_database(path, readonly=True)
    try:
        playset_info, _, _ = inspect_schema(connection)
        requested_name, selection_source = requested_playset_name(args.playset)
        playset = select_playset(connection, set(playset_info), requested_name)
        rows = playset_mod_rows(connection, str(playset["id"]))

        enabled_rows = [row for row in rows if parse_enabled(row["enabled"])]
        local_rows = [
            row
            for row in enabled_rows
            if str(row_value(row, "source") or "").lower() == "local"
        ]
        workshop_rows = [
            row
            for row in enabled_rows
            if row not in local_rows
            and row_value(row, "steamId", "remoteSteamId") is not None
        ]
        disabled_local_rows = [
            row
            for row in rows
            if not parse_enabled(row["enabled"])
            and str(row_value(row, "source") or "").lower() == "local"
        ]

        print(f"Playset: {playset['name']}")
        print(f"Selected by: {selection_source}")
        print(
            "Mods: "
            f"{len(rows)} total; {len(enabled_rows)} enabled; "
            f"{len(local_rows)} local; {len(workshop_rows)} Workshop"
        )
        print()
        print("Enabled local layers (launcher order):")
        if not local_rows:
            print("  (none)")
        for row in local_rows:
            index = rows.index(row)
            previous = (
                "<start>"
                if index == 0
                else str(
                    row_value(rows[index - 1], "displayName", "name") or "<unnamed>"
                )
            )
            following = (
                "<end>"
                if index + 1 == len(rows)
                else str(
                    row_value(rows[index + 1], "displayName", "name") or "<unnamed>"
                )
            )
            display_name = str(row_value(row, "displayName", "name") or "<unnamed>")
            registry_id = row_value(row, "gameRegistryId")
            print(f"  {row['position']}: {display_name}")
            print(f"      registry: {registry_id or '<missing>'}")
            print(f"      before: {previous}")
            print(f"      after: {following}")

        print()
        print("Disabled local layers:")
        if not disabled_local_rows:
            print("  (none)")
        for row in disabled_local_rows:
            print(
                f"  {row['position']}: "
                f"{row_value(row, 'displayName', 'name') or '<unnamed>'}"
            )

        malformed = [
            row
            for row in local_rows + disabled_local_rows
            if row_value(row, "gameRegistryId") is None
        ]
        if malformed:
            print()
            print("Local metadata warnings:")
            for row in malformed:
                print(
                    f"  {row['position']}: "
                    f"{row_value(row, 'displayName', 'name') or '<unnamed>'} "
                    "has no gameRegistryId"
                )
    finally:
        connection.close()


def unique_rows(rows: Iterable[sqlite3.Row]) -> list[sqlite3.Row]:
    return list({str(row["id"]): row for row in rows}.values())


def choose_candidate(rows: list[sqlite3.Row]) -> tuple[sqlite3.Row | None, str | None]:
    rows = unique_rows(rows)
    if not rows:
        return None, "not installed or not yet scanned"
    if len(rows) == 1:
        return rows[0], None

    ready = [row for row in rows if str(row["status"] or "") == "ready_to_play"]
    if len(ready) == 1:
        return ready[0], None
    return None, "ambiguous match"


def candidate_rows(
    connection: sqlite3.Connection,
    mod_columns: set[str],
    columns: tuple[str, ...],
    value: Any,
    *,
    local_only: bool = False,
) -> list[sqlite3.Row] | None:
    available = [column for column in columns if column in mod_columns]
    if value is None or not available:
        return None

    predicates = [f"CAST({qident(column)} AS TEXT) = ?" for column in available]
    params: list[Any] = [str(value)] * len(available)
    where = "(" + " OR ".join(predicates) + ")"
    if local_only and "source" in mod_columns:
        where += " AND source = 'local'"

    status = qident("status") if "status" in mod_columns else "NULL AS status"
    return connection.execute(
        f"SELECT id, displayName, {status} FROM mods WHERE {where}", params
    ).fetchall()


def resolve_mods(
    connection: sqlite3.Connection,
    mod_columns: set[str],
    items: list[Any],
) -> tuple[list[ResolvedMod], list[UnresolvedMod]]:
    resolved: list[ResolvedMod] = []
    unresolved: list[UnresolvedMod] = []
    seen_mod_ids: set[str] = set()

    for source_index, item in enumerate(items):
        if not isinstance(item, dict):
            unresolved.append(
                UnresolvedMod(source_index, "<invalid entry>", "not a JSON object")
            )
            continue

        display_name = str(
            first_value(item, "displayName", "name") or f"entry {source_index}"
        )
        source = str(first_value(item, "source") or "").lower()
        registry_id = first_value(item, "gameRegistryId")
        steam_id = first_value(item, "steamId", "steamID", "remoteSteamId")
        pdx_id = first_value(item, "pdxId", "pdxID", "remotePdxId")

        rows: list[sqlite3.Row] | None = None
        match_kind = "name"
        if source == "local" and registry_id is not None:
            rows = candidate_rows(
                connection,
                mod_columns,
                ("gameRegistryId",),
                registry_id,
                local_only=True,
            )
            match_kind = f"local registry ID {registry_id}"
        if rows is None and steam_id is not None:
            rows = candidate_rows(
                connection,
                mod_columns,
                ("steamId", "remoteSteamId"),
                steam_id,
            )
            match_kind = f"Steam ID {steam_id}"
        if rows is None and pdx_id is not None:
            rows = candidate_rows(
                connection,
                mod_columns,
                ("pdxId", "remotePdxId"),
                pdx_id,
            )
            match_kind = f"Paradox ID {pdx_id}"
        if rows is None:
            name_columns = tuple(
                column for column in ("displayName", "name") if column in mod_columns
            )
            rows = (
                candidate_rows(connection, mod_columns, name_columns, display_name)
                or []
            )

        candidate, reason = choose_candidate(rows)
        if candidate is None:
            unresolved.append(
                UnresolvedMod(source_index, display_name, f"{reason} ({match_kind})")
            )
            continue

        mod_id = str(candidate["id"])
        if mod_id in seen_mod_ids:
            unresolved.append(
                UnresolvedMod(source_index, display_name, "duplicate mod in JSON")
            )
            continue
        seen_mod_ids.add(mod_id)
        resolved.append(
            ResolvedMod(
                mod_id=mod_id,
                display_name=str(candidate["displayName"] or display_name),
                enabled=parse_enabled(item.get("enabled", True)),
                source_position=parse_position(item.get("position"), source_index),
                source_index=source_index,
            )
        )

    resolved.sort(key=lambda mod: (mod.source_position, mod.source_index))
    return resolved, unresolved


def detect_pdx_user_id(
    connection: sqlite3.Connection, playset_columns: set[str]
) -> str | None:
    if "pdxUserId" not in playset_columns:
        return None

    order_terms: list[str] = []
    if "isActive" in playset_columns:
        order_terms.append("CASE WHEN COALESCE(isActive, 0) = 1 THEN 0 ELSE 1 END")
    if "updatedOn" in playset_columns and "createdOn" in playset_columns:
        order_terms.append("COALESCE(updatedOn, createdOn, 0) DESC")
    elif "createdOn" in playset_columns:
        order_terms.append("COALESCE(createdOn, 0) DESC")
    order_clause = f" ORDER BY {', '.join(order_terms)}" if order_terms else ""

    row = connection.execute(
        "SELECT pdxUserId FROM playsets "
        "WHERE pdxUserId IS NOT NULL AND CAST(pdxUserId AS TEXT) <> ''"
        + order_clause
        + " LIMIT 1"
    ).fetchone()
    return str(row[0]) if row else None


def create_playset(
    connection: sqlite3.Connection,
    columns: dict[str, sqlite3.Row],
    name: str,
    pdx_user_id: str | None,
) -> str:
    now_ms = int(time.time() * 1000)
    playset_id = str(uuid.uuid4())
    known_values: dict[str, Any] = {
        "id": playset_id,
        "name": name,
        "isActive": 0,
        "loadOrder": None,
        "pdxId": None,
        "pdxUserId": pdx_user_id,
        "createdOn": now_ms,
        "updatedOn": now_ms,
        "syncedOn": None,
        "deprecatedLastServerChecksum": None,
        "lastServerChecksum": None,
        "isRemoved": 0,
        "hasNotApprovedChanges": 0,
        "syncState": "NOT_ELIGIBLE",
        "state": "private",
        "owned": 1,
        "author": "",
        "subscribersCount": 0,
        "ratingsCount": 0,
        "thumbnailFileUrl": None,
        "description": "",
        "offDisk": 0,
        "version": None,
        "lastSyncAttemptAt": None,
    }

    unknown_required = []
    for column_name, info in columns.items():
        required = bool(info["notnull"]) and info["dflt_value"] is None
        if required and column_name not in known_values:
            unknown_required.append(column_name)
    if unknown_required:
        fail(
            "this launcher version has unsupported required playset columns: "
            + ", ".join(sorted(unknown_required))
        )

    values = {
        column: value for column, value in known_values.items() if column in columns
    }
    column_sql = ", ".join(qident(column) for column in values)
    placeholders = ", ".join("?" for _ in values)
    connection.execute(
        f"INSERT INTO playsets ({column_sql}) VALUES ({placeholders})",
        tuple(values.values()),
    )
    return playset_id


def update_replaced_playset(
    connection: sqlite3.Connection,
    columns: set[str],
    playset_id: str,
) -> None:
    assignments: list[str] = []
    params: list[Any] = []
    if "updatedOn" in columns:
        assignments.append("updatedOn = ?")
        params.append(int(time.time() * 1000))
    if "isRemoved" in columns:
        assignments.append("isRemoved = 0")
    if "isActive" in columns:
        assignments.append("isActive = 0")
    if assignments:
        params.append(playset_id)
        connection.execute(
            f"UPDATE playsets SET {', '.join(assignments)} WHERE id = ?", params
        )


def load_playset_json(path: Path) -> tuple[dict[str, Any], str]:
    if not path.is_file():
        fail(f"JSON file not found: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        fail(f"could not read playset JSON: {exc}")
    if not isinstance(data, dict) or not isinstance(data.get("mods"), list):
        fail('expected a launcher JSON object containing a "mods" array')

    name = str(data.get("name") or path.stem).strip()
    if not name:
        fail("the playset name is empty and the filename has no usable fallback")
    if len(name) > 255:
        fail("the playset name exceeds the launcher's 255-character limit")

    game = str(data.get("game") or "").strip().lower()
    accepted_games = {"", "ck3", "crusader kings iii", "crusader kings 3"}
    if game not in accepted_games:
        print(f'warning: JSON game is "{data.get("game")}", not CK3', file=sys.stderr)
    return data, name


def import_playset(args: argparse.Namespace) -> None:
    json_path = args.json_file.expanduser().resolve()
    data, name = load_playset_json(json_path)
    path = database_path(args.db)
    connection = connect_database(path, readonly=False)
    try:
        playset_info, mod_info, _ = inspect_schema(connection)
        playset_columns = set(playset_info)
        resolved, unresolved = resolve_mods(connection, set(mod_info), data["mods"])

        if unresolved:
            print("Unresolved entries:", file=sys.stderr)
            for item in unresolved:
                print(
                    f"  {item.source_index}: {item.display_name} — {item.reason}",
                    file=sys.stderr,
                )
            if not args.allow_missing:
                fail(
                    f"import aborted because {len(unresolved)} mod(s) could not be resolved; "
                    "use --allow-missing to omit them"
                )

        where = live_playset_clause(playset_columns) + " AND name = ?"
        existing = connection.execute(
            f"SELECT * FROM playsets WHERE {where}", (name,)
        ).fetchall()
        if len(existing) > 1:
            fail(
                f'more than one non-removed playset is named "{name}"; '
                "rename or remove the duplicates in the launcher first"
            )

        action = "replace" if existing else "create"
        print(f'Playset: "{name}"')
        print(f"Action: {action}")
        print(f"Resolved mods: {len(resolved)}")
        print(f"Skipped mods: {len(unresolved)}")
        if args.dry_run:
            print("Dry run complete; database was not changed.")
            return

        try:
            connection.execute("BEGIN IMMEDIATE")
            if existing:
                playset_id = str(existing[0]["id"])
                update_replaced_playset(connection, playset_columns, playset_id)
                connection.execute(
                    "DELETE FROM playsets_mods WHERE playsetId = ?", (playset_id,)
                )
            else:
                playset_id = create_playset(
                    connection,
                    playset_info,
                    name,
                    detect_pdx_user_id(connection, playset_columns),
                )

            connection.executemany(
                """
                INSERT INTO playsets_mods (playsetId, modId, enabled, position)
                VALUES (?, ?, ?, ?)
                """,
                [
                    (playset_id, mod.mod_id, mod.enabled, position)
                    for position, mod in enumerate(resolved)
                ],
            )
            connection.commit()
        except Exception:
            connection.rollback()
            raise

        verb = "Replaced" if existing else "Created"
        print(f'{verb} playset "{name}" with {len(resolved)} mods.')
    finally:
        connection.close()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Import and export Crusader Kings III launcher playsets."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    export_parser = subparsers.add_parser(
        "export", help="export a playset as JSON on standard output"
    )
    export_parser.add_argument(
        "playset",
        nargs="?",
        help=(
            "exact playset name; defaults to $"
            f"{PLAYSET_NAME_ENV}, then the active playset"
        ),
    )
    export_parser.add_argument(
        "--db",
        type=Path,
        help=f"launcher database (default: ${PARADOX_DIRECTORY_ENV}/{DATABASE_NAME})",
    )
    export_parser.set_defaults(handler=export_playset)

    summary_parser = subparsers.add_parser(
        "summary", help="summarize a live launcher playset"
    )
    summary_parser.add_argument(
        "playset",
        nargs="?",
        help=(
            "exact playset name; defaults to $"
            f"{PLAYSET_NAME_ENV}, then the active playset"
        ),
    )
    summary_parser.add_argument(
        "--db",
        type=Path,
        help=f"launcher database (default: ${PARADOX_DIRECTORY_ENV}/{DATABASE_NAME})",
    )
    summary_parser.set_defaults(handler=summary_playset)

    import_parser = subparsers.add_parser(
        "import", help="create or replace a playset from JSON"
    )
    import_parser.add_argument("json_file", type=Path, help="playset JSON file")
    import_parser.add_argument(
        "--db",
        type=Path,
        help=f"launcher database (default: ${PARADOX_DIRECTORY_ENV}/{DATABASE_NAME})",
    )
    import_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="resolve and report the import without changing the database",
    )
    import_parser.add_argument(
        "--allow-missing",
        action="store_true",
        help="omit unresolved or ambiguous mods instead of aborting",
    )
    import_parser.set_defaults(handler=import_playset)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    try:
        args.handler(args)
    except sqlite3.OperationalError as exc:
        fail(
            f"SQLite error: {exc}\n"
            "Make sure CK3 and the Paradox Launcher are completely closed for imports."
        )
    except sqlite3.IntegrityError as exc:
        fail(f"database integrity error: {exc}; nothing was committed")


if __name__ == "__main__":
    main()
