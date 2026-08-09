from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from ck3mm.references import (
    apply_reference_sync,
    check_references,
    plan_reference_sync,
)


def test_reference_sync_and_check_include_optional_logs(tmp_path: Path) -> None:
    game = tmp_path / "game-root"
    paradox = tmp_path / "user-data"
    cache = tmp_path / "cache"
    (game / "game" / "common").mkdir(parents=True)
    (game / "game" / "common" / "effects.info").write_text("effect", encoding="utf-8")
    (paradox / "logs").mkdir(parents=True)
    (paradox / "logs" / "effects.log").write_text("docs", encoding="utf-8")
    (cache / "info").mkdir(parents=True)
    (cache / "info" / "orphan.info").write_text("old", encoding="utf-8")

    plan = plan_reference_sync(game, paradox, cache)
    assert plan.info_files == 1
    assert plan.script_doc_logs == 1
    assert cache.joinpath("info/orphan.info") in plan.removals
    assert not check_references(game, paradox, cache).current

    result = apply_reference_sync(plan, generated_at=datetime(2026, 1, 2, tzinfo=UTC))
    assert result.current
    assert (cache / "info" / "common" / "effects.info").read_text() == "effect"
    assert (cache / "script_docs" / "effects.log").read_text() == "docs"
    assert not (cache / "info" / "orphan.info").exists()
    manifest = json.loads((cache / "manifest.json").read_text())
    assert "game_dir" not in manifest
    assert "paradox_dir" not in manifest

    (game / "game" / "common" / "effects.info").write_text("changed", encoding="utf-8")
    assert check_references(game, paradox, cache).stale == ("info/common/effects.info",)
