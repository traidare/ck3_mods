from __future__ import annotations

import json
import sqlite3
import zipfile
from datetime import UTC, datetime
from pathlib import Path

import pytest

import ck3mm.preservation as preservation
from ck3mm.preservation import (
    MANIFEST_FORMAT,
    PreservationError,
    apply_preservation,
    plan_preservation,
)


def preservation_fixture(tmp_path: Path) -> tuple[Path, Path, Path]:
    paradox = tmp_path / "paradox"
    mod_directory = paradox / "mod"
    workshop = tmp_path / "workshop"
    local_source = tmp_path / "local-source"
    archive_path = tmp_path / "archived.zip"
    mod_directory.mkdir(parents=True)
    workshop.mkdir()
    local_source.mkdir()

    (local_source / "descriptor.mod").write_text(
        'name="Local Layer"\npath="ignored"\nreplace_path="history/titles"\n',
        encoding="utf-8",
    )
    (local_source / "common").mkdir()
    (local_source / "common" / "local.txt").write_text("local", encoding="utf-8")
    (mod_directory / "local.mod").write_text(
        f'name="Local Layer"\npath="{local_source}"\n', encoding="utf-8"
    )

    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("descriptor.mod", 'name="Archived Mod"\narchive="old.zip"\n')
        archive.writestr("events/archive.txt", "archive")
    (mod_directory / "archive.mod").write_text(
        f'name="Archived Mod"\narchive="{archive_path}"\n', encoding="utf-8"
    )

    database_path = paradox / "launcher-v2.sqlite"
    connection = sqlite3.connect(database_path)
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
            name TEXT,
            displayName TEXT NOT NULL,
            source TEXT,
            status TEXT,
            steamId TEXT,
            pdxId TEXT,
            gameRegistryId TEXT,
            dirPath TEXT,
            archivePath TEXT,
            version TEXT,
            requiredVersion TEXT,
            tags TEXT,
            size INTEGER,
            createdDate INTEGER
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
        VALUES ('source', 'AGOT', 1, 1, 'user');
        """
    )
    connection.execute(
        """
        INSERT INTO mods
            (id, displayName, source, status, gameRegistryId, dirPath, version, tags)
        VALUES ('local', 'Local Layer', 'local', 'ready_to_play',
                'mod/local.mod', ?, '1.0', '["Local"]')
        """,
        (str(local_source),),
    )
    connection.execute(
        """
        INSERT INTO mods
            (id, displayName, source, status, gameRegistryId, archivePath,
             version, tags)
        VALUES ('archive', 'Archived Mod', 'pdx', 'initialized',
                'mod/archive.mod', ?, '2.0', '[]')
        """,
        (str(archive_path),),
    )
    connection.execute("INSERT INTO playsets_mods VALUES ('source', 'local', 1, 5)")
    connection.execute("INSERT INTO playsets_mods VALUES ('source', 'archive', 1, 8)")
    connection.commit()
    connection.close()
    return database_path, mod_directory, workshop


def test_plan_is_read_only_and_scans_directory_and_zip(tmp_path: Path) -> None:
    database_path, mod_directory, workshop = preservation_fixture(tmp_path)
    before = database_path.read_bytes()
    now = datetime(2026, 8, 9, 12, 0, tzinfo=UTC)

    plan = plan_preservation(
        database_path,
        mod_directory,
        workshop_directory=workshop,
        snapshot_name="Frozen AGOT",
        now=now,
    )

    assert plan.snapshot_slug == "frozen-agot"
    assert plan.created_at == "2026-08-09T12:00:00Z"
    assert [mod.source_kind for mod in plan.mods] == ["directory", "zip"]
    assert [mod.source_position for mod in plan.mods] == [5, 8]
    assert plan.to_dict()["enabledMods"] == 2
    assert database_path.read_bytes() == before
    assert not plan.final_root.exists()
    assert not list(mod_directory.glob("frozen-agot__*.mod"))


def test_apply_stages_manifest_backs_up_and_registers(tmp_path: Path) -> None:
    database_path, mod_directory, workshop = preservation_fixture(tmp_path)
    plan = plan_preservation(
        database_path,
        mod_directory,
        workshop_directory=workshop,
        snapshot_name="Frozen AGOT",
    )

    result = apply_preservation(plan)

    assert result.backup_path.is_file()
    assert (plan.final_root / "000-local" / "common" / "local.txt").is_file()
    assert (plan.final_root / "001-archive" / "events" / "archive.txt").is_file()
    descriptor = (plan.final_root / "001-archive" / "descriptor.mod").read_text()
    assert "archive=" not in descriptor
    registry = (mod_directory / "frozen-agot__001.mod").read_text()
    assert 'path="mod/frozen-agot/001-archive"' in registry

    manifest = json.loads((plan.final_root / "snapshot.json").read_text())
    assert manifest["format"] == MANIFEST_FORMAT
    assert manifest["registered"] is True
    assert manifest["launcher_playset_id"] == result.playset_id
    assert all(mod["content_sha256"] for mod in manifest["mods"])

    with sqlite3.connect(database_path) as connection:
        playset = connection.execute(
            "SELECT id FROM playsets WHERE name = 'Frozen AGOT'"
        ).fetchone()
        assert playset == (result.playset_id,)
        rows = connection.execute(
            """
            SELECT m.source, m.gameRegistryId, pm.enabled, pm.position
            FROM playsets_mods pm JOIN mods m ON m.id = pm.modId
            WHERE pm.playsetId = ? ORDER BY pm.position
            """,
            (result.playset_id,),
        ).fetchall()
    assert rows == [
        ("local", "mod/frozen-agot__000.mod", 1, 0),
        ("local", "mod/frozen-agot__001.mod", 1, 1),
    ]


def test_plan_rejects_output_collisions_without_writing(tmp_path: Path) -> None:
    database_path, mod_directory, workshop = preservation_fixture(tmp_path)
    (mod_directory / "frozen-agot").mkdir()

    with pytest.raises(PreservationError, match="snapshot directory already exists"):
        plan_preservation(
            database_path,
            mod_directory,
            workshop_directory=workshop,
            snapshot_name="Frozen AGOT",
        )

    with sqlite3.connect(database_path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM playsets").fetchone()[0] == 1


def test_plan_rejects_insufficient_disk_space(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    database_path, mod_directory, workshop = preservation_fixture(tmp_path)
    real_usage = preservation.shutil.disk_usage(mod_directory)
    monkeypatch.setattr(
        preservation.shutil,
        "disk_usage",
        lambda _path: real_usage._replace(free=0),
    )

    with pytest.raises(PreservationError, match="not enough free space"):
        plan_preservation(
            database_path,
            mod_directory,
            workshop_directory=workshop,
            snapshot_name="Frozen AGOT",
        )

    assert not (mod_directory / "frozen-agot").exists()


def test_plan_rejects_unsafe_zip_members(tmp_path: Path) -> None:
    database_path, mod_directory, workshop = preservation_fixture(tmp_path)
    archive_path = tmp_path / "archived.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("../escape.txt", "bad")

    with pytest.raises(PreservationError, match="unsafe path in ZIP"):
        plan_preservation(
            database_path,
            mod_directory,
            workshop_directory=workshop,
            snapshot_name="Frozen AGOT",
        )


def test_apply_rechecks_source_playset_fingerprint(tmp_path: Path) -> None:
    database_path, mod_directory, workshop = preservation_fixture(tmp_path)
    plan = plan_preservation(
        database_path,
        mod_directory,
        workshop_directory=workshop,
        snapshot_name="Frozen AGOT",
    )
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            "UPDATE playsets_mods SET position = 99 WHERE modId = 'archive'"
        )
        connection.commit()

    with pytest.raises(PreservationError, match="source playset changed"):
        apply_preservation(plan)

    manifest = json.loads((plan.final_root / "snapshot.json").read_text())
    assert manifest["registered"] is False
    with sqlite3.connect(database_path) as connection:
        assert (
            connection.execute(
                "SELECT COUNT(*) FROM playsets WHERE name = 'Frozen AGOT'"
            ).fetchone()[0]
            == 0
        )
