from __future__ import annotations

import subprocess
from datetime import UTC, datetime
from pathlib import Path

from ck3mm.diagnostics import collect_live_diagnostics, write_diagnostic_report


def test_diagnostics_use_explicit_roots_and_optional_steam_log(tmp_path: Path) -> None:
    paradox = tmp_path / "paradox"
    proc = tmp_path / "proc"
    process = proc / "42"
    executable = tmp_path / "bin" / "ck3"
    executable.parent.mkdir()
    executable.write_text("binary", encoding="utf-8")
    process.mkdir(parents=True)
    (process / "exe").symlink_to(executable)
    (process / "cmdline").write_bytes(b"ck3\0-debug_mode\0")
    for name in ("status", "io", "stack"):
        (process / name).write_text(name, encoding="utf-8")
    (paradox / "logs").mkdir(parents=True)
    (paradox / "logs" / "debug.log").write_text("debug-tail", encoding="utf-8")
    steam = tmp_path / "steam" / "gameprocess_log.txt"
    steam.parent.mkdir()
    steam.write_text("steam-tail", encoding="utf-8")

    def runner(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(args[0], 0, stdout="sample")

    report = collect_live_diagnostics(
        paradox_dir=paradox,
        proc_root=proc,
        steam_log_path=steam,
        sample_count=1,
        runner=runner,
        now=lambda: datetime(2026, 1, 2, tzinfo=UTC),
    )
    assert report.visible_pids == (42,)
    assert "debug-tail" in report.text
    assert "steam-tail" in report.text
    destination = tmp_path / "reports" / "live.txt"
    assert write_diagnostic_report(report, destination) == destination
    assert destination.read_text() == report.text
