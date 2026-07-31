#!/usr/bin/env python3
"""Import and export Crusader Kings III Paradox Launcher playsets."""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from ck3_launcher import (
    DATABASE_NAME,
    PARADOX_DIRECTORY_ENV,
    PLAYSET_NAME_ENV,
    connect_database,
    create_playset,
    database_path,
    detect_pdx_user_id,
    fail,
    first_value,
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
