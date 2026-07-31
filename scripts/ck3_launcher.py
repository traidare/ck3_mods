"""Shared Paradox Launcher database helpers for the CK3 command-line tools."""

from __future__ import annotations

import os
import sqlite3
import sys
import time
import uuid
from pathlib import Path
from typing import Any, NoReturn

DATABASE_NAME = "launcher-v2.sqlite"
PARADOX_DIRECTORY_ENV = "CK3_PARADOX_DIR"
PLAYSET_NAME_ENV = "CK3_PLAYSET_NAME"


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
