"""Typed access to the Paradox Launcher database.

This module contains no command-line behavior and never guesses a host path.
Callers provide the database path resolved by :mod:`ck3mm.config`.
"""

from __future__ import annotations

import sqlite3
import time
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

DATABASE_NAME = "launcher-v2.sqlite"


class LauncherError(RuntimeError):
    """The Launcher database or requested operation is not usable."""


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


def parse_enabled(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"0", "false", "no", "off", "disabled"}:
            return False
        if normalized in {"1", "true", "yes", "on", "enabled"}:
            return True
    return bool(value)


def parse_position(value: Any, fallback: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError, OverflowError):
        return fallback


def connect_database(path: Path, *, readonly: bool) -> sqlite3.Connection:
    resolved = path.expanduser().resolve()
    if not resolved.is_file():
        raise LauncherError(f"launcher database not found: {resolved}")
    if readonly:
        connection = sqlite3.connect(
            resolved.as_uri() + "?mode=ro", uri=True, timeout=3
        )
    else:
        connection = sqlite3.connect(resolved, timeout=3)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 3000")
    return connection


@contextmanager
def database(path: Path, *, readonly: bool = True) -> Iterator[sqlite3.Connection]:
    connection = connect_database(path, readonly=readonly)
    try:
        yield connection
    finally:
        connection.close()


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
    if missing := required_tables - tables:
        raise LauncherError(
            "unexpected launcher database; missing tables: "
            + ", ".join(sorted(missing))
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
        if missing := required - available:
            raise LauncherError(
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
    parameters: tuple[Any, ...] = ()
    label = "active playset"
    if name is not None:
        where += " AND name = ?"
        parameters = (name,)
        label = f'playset named "{name}"'
    else:
        if "isActive" not in columns:
            raise LauncherError("the launcher schema cannot identify an active playset")
        where += " AND COALESCE(isActive, 0) = 1"

    rows = connection.execute(
        f"SELECT * FROM playsets WHERE {where}", parameters
    ).fetchall()
    if not rows:
        raise LauncherError(f"no {label} was found")
    if len(rows) > 1:
        raise LauncherError(f"more than one {label} was found")
    return rows[0]


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
    unknown_required = [
        column_name
        for column_name, info in columns.items()
        if bool(info["notnull"])
        and info["dflt_value"] is None
        and column_name not in known_values
    ]
    if unknown_required:
        raise LauncherError(
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
    parameters: list[Any] = []
    if "updatedOn" in columns:
        assignments.append("updatedOn = ?")
        parameters.append(int(time.time() * 1000))
    if "isRemoved" in columns:
        assignments.append("isRemoved = 0")
    if "isActive" in columns:
        assignments.append("isActive = 0")
    if assignments:
        parameters.append(playset_id)
        connection.execute(
            f"UPDATE playsets SET {', '.join(assignments)} WHERE id = ?",
            parameters,
        )
