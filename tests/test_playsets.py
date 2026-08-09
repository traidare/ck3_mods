from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from ck3mm.launcher import LauncherError
from ck3mm.playsets import (
    Playset,
    PlaysetMod,
    apply_import,
    diff_playsets,
    dump_playset,
    load_live_playset,
    load_playset_file,
    plan_import,
    playset_summary,
)


def launcher_database(path: Path) -> Path:
    connection = sqlite3.connect(path)
    connection.executescript(
        """
        CREATE TABLE playsets (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            isActive INTEGER,
            isRemoved INTEGER DEFAULT 0,
            createdOn INTEGER NOT NULL,
            updatedOn INTEGER,
            pdxUserId TEXT
        );
        CREATE TABLE mods (
            id TEXT PRIMARY KEY,
            displayName TEXT NOT NULL,
            source TEXT,
            status TEXT,
            steamId TEXT,
            pdxId TEXT,
            gameRegistryId TEXT
        );
        CREATE TABLE playsets_mods (
            playsetId TEXT NOT NULL,
            modId TEXT NOT NULL,
            enabled INTEGER NOT NULL,
            position INTEGER NOT NULL,
            FOREIGN KEY(playsetId) REFERENCES playsets(id),
            FOREIGN KEY(modId) REFERENCES mods(id)
        );
        INSERT INTO playsets
            (id, name, isActive, createdOn, pdxUserId)
        VALUES ('active', 'AGOT', 1, 1, 'user');
        INSERT INTO playsets
            (id, name, isActive, createdOn, pdxUserId)
        VALUES ('other', 'Testing', 0, 2, 'user');
        INSERT INTO mods
            (id, displayName, source, status, steamId)
        VALUES ('steam-mod', 'Workshop Mod', 'steam', 'ready_to_play', '123');
        INSERT INTO mods
            (id, displayName, source, status, gameRegistryId)
        VALUES ('local-mod', 'Local Layer', 'local', 'ready_to_play', 'mod/local.mod');
        INSERT INTO playsets_mods VALUES ('active', 'steam-mod', 1, 0);
        INSERT INTO playsets_mods VALUES ('active', 'local-mod', 1, 1);
        """
    )
    connection.commit()
    connection.close()
    return path


def test_live_playset_selection_and_summary(tmp_path: Path) -> None:
    path = launcher_database(tmp_path / "launcher-v2.sqlite")
    playset = load_live_playset(path)

    assert playset.name == "AGOT"
    assert [mod.stable_id for mod in playset.mods] == [
        "steam:123",
        "local:mod/local.mod",
    ]
    summary = playset_summary(playset)
    assert summary["enabled"] == 2
    assert summary["local"] == 1
    assert summary["workshop"] == 1


def test_playset_json_round_trip(tmp_path: Path) -> None:
    original = Playset(
        name="Portable",
        mods=(
            PlaysetMod("One", True, 0, steam_id="1"),
            PlaysetMod(
                "Local", False, 1, source="local", game_registry_id="mod/local.mod"
            ),
        ),
    )
    path = tmp_path / "playset.json"
    path.write_text(dump_playset(original), encoding="utf-8")

    loaded = load_playset_file(path)
    assert loaded.to_dict() == original.to_dict()
    assert json.loads(dump_playset(loaded))["mods"][1]["enabled"] is False


def test_import_is_preview_then_explicit_apply(tmp_path: Path) -> None:
    path = launcher_database(tmp_path / "launcher-v2.sqlite")
    imported = Playset(
        name="Imported",
        mods=(
            PlaysetMod("Workshop Mod", True, 5, steam_id="123"),
            PlaysetMod("Missing", True, 6, steam_id="999"),
        ),
    )

    plan = plan_import(path, imported)
    assert plan.action == "create"
    assert len(plan.resolved) == 1
    assert len(plan.unresolved) == 1
    with sqlite3.connect(path) as connection:
        assert (
            connection.execute(
                "SELECT COUNT(*) FROM playsets WHERE name = 'Imported'"
            ).fetchone()[0]
            == 0
        )

    with pytest.raises(LauncherError, match="unresolved"):
        apply_import(path, imported)
    applied = apply_import(path, imported, allow_missing=True)
    assert applied.backup_path is not None
    assert applied.backup_path.is_file()
    assert load_live_playset(path, name="Imported").mods[0].steam_id == "123"


def test_diff_ignores_positions_but_reports_membership_and_settings() -> None:
    before = Playset(
        "Before",
        (
            PlaysetMod("One", True, 0, steam_id="1"),
            PlaysetMod("Removed", True, 1, steam_id="2"),
        ),
    )
    after = Playset(
        "After",
        (
            PlaysetMod("One", False, 20, steam_id="1"),
            PlaysetMod("Added", True, 10, steam_id="3"),
        ),
    )

    result = diff_playsets(before, after)

    assert [mod.stable_id for mod in result.added] == ["steam:3"]
    assert [mod.stable_id for mod in result.removed] == ["steam:2"]
    assert [mod.stable_id for mod in result.changed] == ["steam:1"]
    reordered = Playset("Reordered", (PlaysetMod("One", True, 99, steam_id="1"),))
    assert diff_playsets(
        Playset("Original", (PlaysetMod("One", True, 0, steam_id="1"),)),
        reordered,
    ).current
