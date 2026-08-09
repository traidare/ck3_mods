"""Read-only CK3 process and log diagnostics."""

from __future__ import annotations

import os
import subprocess
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path


class DiagnosticError(ValueError):
    """Raised when diagnostic inputs are invalid."""


@dataclass(frozen=True, slots=True)
class DiagnosticReport:
    generated_at: str
    requested_pids: tuple[int, ...]
    visible_pids: tuple[int, ...]
    text: str


def discover_ck3_pids(proc_root: Path) -> tuple[int, ...]:
    """Discover processes whose executable basename is exactly ``ck3``."""
    root = Path(proc_root)
    if not root.is_dir():
        raise DiagnosticError(f"process filesystem is missing: {root}")
    result: list[int] = []
    for entry in root.iterdir():
        if not entry.name.isdigit() or not entry.is_dir():
            continue
        try:
            executable = (entry / "exe").resolve(strict=True)
        except OSError:
            continue
        if executable.name == "ck3":
            result.append(int(entry.name))
    return tuple(sorted(result))


def _tail(path: Path, lines: int = 120) -> str | list[str]:
    try:
        with path.open("rb") as handle:
            handle.seek(0, os.SEEK_END)
            position = handle.tell()
            chunks: list[bytes] = []
            newlines = 0
            while position > 0 and newlines <= lines:
                size = min(8192, position)
                position -= size
                handle.seek(position)
                chunk = handle.read(size)
                chunks.append(chunk)
                newlines += chunk.count(b"\n")
        return (
            b"".join(reversed(chunks))
            .decode("utf-8", errors="replace")
            .splitlines()[-lines:]
        )
    except OSError as error:
        return f"<unavailable: {error}>"


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError as error:
        return f"<unavailable: {error}>"


def _command(
    arguments: Sequence[str], runner: Callable[..., subprocess.CompletedProcess[str]]
) -> str:
    try:
        result = runner(
            list(arguments),
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
    except (OSError, subprocess.SubprocessError) as error:
        return f"<unavailable: {error}>"
    return result.stdout.rstrip() or f"<no output; exit {result.returncode}>"


def _section(lines: list[str], title: str, content: str | Sequence[str]) -> None:
    lines.append(f"=== {title} ===")
    if isinstance(content, str):
        lines.append(content.rstrip())
    else:
        lines.extend(str(item).rstrip() for item in content)


def collect_live_diagnostics(
    *,
    paradox_dir: Path,
    proc_root: Path,
    pids: Sequence[int] = (),
    steam_log_path: Path | None = None,
    capture_backtrace: bool = False,
    sample_count: int = 2,
    sample_interval: float = 5.0,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
    sleeper: Callable[[float], None] = time.sleep,
    now: Callable[[], datetime] | None = None,
) -> DiagnosticReport:
    """Collect a text report; every host-specific filesystem root is explicit.

    Native backtraces are opt-in because attaching a debugger can pause a live
    game and is more invasive than the rest of this read-only report.
    """
    paradox = Path(paradox_dir)
    proc = Path(proc_root)
    if not paradox.is_dir():
        raise DiagnosticError(f"CK3 user-data directory is missing: {paradox}")
    if not proc.is_dir():
        raise DiagnosticError(f"process filesystem is missing: {proc}")
    if sample_count < 1:
        raise DiagnosticError("sample_count must be at least one")
    if sample_interval < 0:
        raise DiagnosticError("sample_interval must not be negative")
    if any(
        isinstance(pid, bool) or not isinstance(pid, int) or pid <= 0 for pid in pids
    ):
        raise DiagnosticError("PIDs must be positive integers")

    requested = tuple(dict.fromkeys(pids)) or discover_ck3_pids(proc)
    visible = tuple(pid for pid in requested if (proc / str(pid)).is_dir())
    clock = now or (lambda: datetime.now(UTC))
    generated = clock().astimezone(UTC).isoformat()
    lines: list[str] = []
    _section(lines, "TIME", generated)
    pid_lines = [
        str(pid) if pid in visible else f"{pid} (not visible under process root)"
        for pid in requested
    ]
    _section(lines, "CK3 PIDS", pid_lines or ["<none>"])

    pid_csv = ",".join(str(pid) for pid in visible)
    for sample in range(1, sample_count + 1):
        if visible:
            _section(
                lines,
                f"PROCESS SAMPLE {sample}",
                _command(
                    [
                        "ps",
                        "-p",
                        pid_csv,
                        "-o",
                        "pid,ppid,stat,lstart,etime,%cpu,%mem,rss,vsz,wchan:32,comm",
                    ],
                    runner,
                ),
            )
            for pid in visible:
                process = proc / str(pid)
                try:
                    executable = str((process / "exe").resolve(strict=True))
                except OSError as error:
                    executable = f"<unavailable: {error}>"
                _section(lines, f"PID {pid} EXECUTABLE", executable)
                try:
                    command_line = (
                        (process / "cmdline")
                        .read_bytes()
                        .replace(b"\0", b" ")
                        .decode("utf-8", errors="replace")
                    )
                except OSError as error:
                    command_line = f"<unavailable: {error}>"
                _section(lines, f"PID {pid} COMMAND LINE", command_line)
                _section(lines, f"PID {pid} STATUS", _read_text(process / "status"))
                _section(lines, f"PID {pid} I/O", _read_text(process / "io"))
                _section(
                    lines,
                    f"PID {pid} THREADS",
                    _command(
                        [
                            "ps",
                            "-L",
                            "-p",
                            str(pid),
                            "-o",
                            "pid,tid,psr,stat,%cpu,wchan:32,comm",
                        ],
                        runner,
                    ),
                )
                _section(
                    lines, f"PID {pid} KERNEL STACK", _read_text(process / "stack")
                )

        sizes: list[str] = []
        for name in ("debug", "error", "game", "system"):
            path = paradox / "logs" / f"{name}.log"
            try:
                metadata = path.stat()
            except OSError:
                continue
            sizes.append(
                f"{name}.log size={metadata.st_size} mtime_ns={metadata.st_mtime_ns}"
            )
        _section(lines, f"LOG SIZES {sample}", sizes or ["<none>"])
        if sample < sample_count:
            sleeper(sample_interval)

    if capture_backtrace:
        dumps = [
            f"--- PID {pid} ---\n"
            + _command(
                [
                    "timeout",
                    "60s",
                    "gdb",
                    "--batch",
                    "--quiet",
                    "-ex",
                    "set pagination off",
                    "-ex",
                    f"attach {pid}",
                    "-ex",
                    "thread apply all bt",
                    "-ex",
                    "detach",
                ],
                runner,
            )
            for pid in visible
        ]
        _section(
            lines, "NATIVE THREAD BACKTRACES", dumps or ["<no visible CK3 process>"]
        )

    _section(lines, "DEBUG LOG TAIL", _tail(paradox / "logs" / "debug.log"))
    _section(lines, "ERROR LOG TAIL", _tail(paradox / "logs" / "error.log"))
    crashes = paradox / "crashes"
    crash_rows: list[str] = []
    if crashes.is_dir():
        crash_rows = [
            f"{path.stat().st_mtime_ns} {path.name}"
            for path in sorted(
                crashes.iterdir(),
                key=lambda item: item.stat().st_mtime_ns,
                reverse=True,
            )[:8]
        ]
    _section(lines, "NEWEST CRASH BUNDLES", crash_rows or ["<none>"])
    _section(
        lines,
        "RECENT CK3 COREDUMPS",
        _command(
            [
                "coredumpctl",
                "--no-pager",
                "--since",
                "-15 minutes",
                "list",
                "ck3",
            ],
            runner,
        ),
    )
    if steam_log_path is None:
        _section(lines, "RECENT STEAM GAME-PROCESS LOG", "<not requested>")
    else:
        _section(lines, "RECENT STEAM GAME-PROCESS LOG", _tail(Path(steam_log_path)))
    return DiagnosticReport(generated, requested, visible, "\n".join(lines) + "\n")


def write_diagnostic_report(report: DiagnosticReport, destination: Path) -> Path:
    """Write an already-collected report; collection itself never writes."""
    path = Path(destination)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(report.text, encoding="utf-8")
    return path
