from __future__ import annotations

import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

import pytest

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
HOST_PATH_PATTERNS = (
    ("Linux user home", re.compile(r"(?<![\w.-])/home/[^/\s\"']+/")),
    ("macOS user home", re.compile(r"(?<![\w.-])/Users/[^/\s\"']+/")),
    ("gaming host root", re.compile(r"(?<![\w.-])/var/lib/gaming(?:/|\b)")),
    (
        "Windows user home",
        re.compile(r"(?i)\b[A-Z]:[\\/]Users[\\/][^\\/\s\"']+[\\/]"),
    ),
)

CONFIG_NAMES = frozenset(
    {
        ".envrc",
        ".env.example",
        "Dockerfile",
        "Justfile",
        "Makefile",
        "flake.nix",
        "justfile",
        "pyproject.toml",
    }
)
CONFIG_SUFFIXES = frozenset({".conf", ".json", ".toml", ".yaml", ".yml"})


@dataclass(frozen=True)
class TrackedEntry:
    mode: str
    path: str


def _run_git(*arguments: str) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        ("git", "-C", str(REPOSITORY_ROOT), *arguments),
        check=False,
        capture_output=True,
    )


@pytest.fixture(scope="module")
def tracked_entries() -> tuple[TrackedEntry, ...]:
    """Return the checked-out source tree or skip metadata-free packages."""
    if not (REPOSITORY_ROOT / ".git").exists():
        pytest.skip("repository policy requires source-tree Git metadata")

    try:
        top_level = _run_git("rev-parse", "--show-toplevel")
    except FileNotFoundError:
        pytest.skip("repository policy requires Git")
    if top_level.returncode != 0:
        pytest.skip("repository policy requires source-tree Git metadata")
    discovered = Path(os.fsdecode(top_level.stdout).strip()).resolve()
    if discovered != REPOSITORY_ROOT.resolve():
        pytest.skip("tests are not running from their source-tree Git root")

    result = _run_git("ls-files", "--stage", "-z")
    if result.returncode != 0:
        pytest.fail(os.fsdecode(result.stderr).strip())

    entries: list[TrackedEntry] = []
    for raw_entry in result.stdout.split(b"\0"):
        if not raw_entry:
            continue
        metadata, raw_path = raw_entry.split(b"\t", 1)
        mode = metadata.split(b" ", 1)[0].decode("ascii")
        entries.append(TrackedEntry(mode, os.fsdecode(raw_path)))
    untracked = _run_git("ls-files", "--others", "--exclude-standard", "-z")
    if untracked.returncode != 0:
        pytest.fail(os.fsdecode(untracked.stderr).strip())
    known = {entry.path for entry in entries}
    for raw_path in untracked.stdout.split(b"\0"):
        if not raw_path:
            continue
        path = os.fsdecode(raw_path)
        if path in known:
            continue
        physical = REPOSITORY_ROOT / path
        mode = "120000" if physical.is_symlink() else "100644"
        entries.append(TrackedEntry(mode, path))
    return tuple(entries)


def _present(path: Path) -> bool:
    return os.path.lexists(path)


def _is_tooling(entry: TrackedEntry) -> bool:
    path = PurePosixPath(entry.path)
    if entry.mode == "100755" or path.name in CONFIG_NAMES:
        return True
    if path.suffix in CONFIG_SUFFIXES:
        return True
    if "scripts" in path.parts:
        return True
    if path.parts and path.parts[0] == "src" and path.suffix == ".py":
        return True
    return ".ck3mm" in path.parts and path.suffix in {".py", ".toml", ".conf"}


def test_tracked_symlinks_stay_inside_repository(
    tracked_entries: tuple[TrackedEntry, ...],
) -> None:
    root = REPOSITORY_ROOT.resolve()
    violations: list[str] = []
    for entry in tracked_entries:
        if entry.mode != "120000":
            continue
        link = REPOSITORY_ROOT / entry.path
        if not link.is_symlink():
            continue
        target_text = os.readlink(link)
        target = Path(target_text)
        if target.is_absolute():
            violations.append(f"{entry.path}: absolute target {target_text!r}")
            continue
        resolved = (link.parent / target).resolve(strict=False)
        if not resolved.is_relative_to(root):
            violations.append(
                f"{entry.path}: target escapes repository: {target_text!r}"
            )

    assert not violations, "non-portable tracked symlinks:\n" + "\n".join(violations)


def test_tooling_does_not_embed_host_paths(
    tracked_entries: tuple[TrackedEntry, ...],
) -> None:
    violations: list[str] = []
    for entry in tracked_entries:
        if not _is_tooling(entry):
            continue
        path = REPOSITORY_ROOT / entry.path
        if not _present(path) or path.is_symlink() or not path.is_file():
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for line_number, line in enumerate(content.splitlines(), start=1):
            for label, pattern in HOST_PATH_PATTERNS:
                if pattern.search(line):
                    violations.append(f"{entry.path}:{line_number}: {label}")

    assert not violations, "host-specific paths in tooling:\n" + "\n".join(violations)


def test_launcher_descriptors_are_not_stored_at_mods_root(
    tracked_entries: tuple[TrackedEntry, ...],
) -> None:
    descriptors = sorted(
        entry.path
        for entry in tracked_entries
        if len(PurePosixPath(entry.path).parts) == 2
        and PurePosixPath(entry.path).parts[0] == "mods"
        and PurePosixPath(entry.path).suffix == ".mod"
        and _present(REPOSITORY_ROOT / entry.path)
    )
    assert not descriptors, (
        "launcher descriptors must be generated during installation:\n"
        + "\n".join(descriptors)
    )

    dependency_metadata = sorted(
        entry.path
        for entry in tracked_entries
        if entry.path.endswith("/descriptor.mod")
        and _present(REPOSITORY_ROOT / entry.path)
        and re.search(
            r"(?m)^\s*dependencies\s*=",
            (REPOSITORY_ROOT / entry.path).read_text(encoding="utf-8"),
        )
    )
    assert not dependency_metadata, (
        "tooling dependencies belong in .ck3mm/ck3-tiger.conf:\n"
        + "\n".join(dependency_metadata)
    )


def test_tiger_modfiles_are_portable_and_resolve(
    tracked_entries: tuple[TrackedEntry, ...],
) -> None:
    root = REPOSITORY_ROOT.resolve()
    violations: list[str] = []
    for entry in tracked_entries:
        if not entry.path.endswith("/.ck3mm/ck3-tiger.conf"):
            continue
        config = REPOSITORY_ROOT / entry.path
        if not config.is_file():
            continue
        for line_number, line in enumerate(
            config.read_text(encoding="utf-8").splitlines(), start=1
        ):
            match = re.match(r'^\s*modfile\s*=\s*"([^"]+)"\s*$', line)
            if match is None:
                continue
            declared = Path(match.group(1))
            resolved = (config.parent / declared).resolve(strict=False)
            if declared.is_absolute() or not resolved.is_relative_to(root):
                violations.append(
                    f"{entry.path}:{line_number}: modfile escapes repository"
                )
            elif not resolved.is_file():
                violations.append(
                    f"{entry.path}:{line_number}: modfile does not resolve"
                )
    assert not violations, "invalid Tiger modfile declarations:\n" + "\n".join(
        violations
    )
