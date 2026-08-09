from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from ck3mm.config import load_config
from ck3mm.generation import (
    GenerationError,
    SourceLockError,
    output_is_owned,
    run_generator,
    sha256_path,
)
from ck3mm.workspace import Workspace


def make_generated_workspace(
    root: Path, generator_source: str, *, owned: str = "generated/**"
) -> tuple[Workspace, object]:
    (root / "pyproject.toml").write_text("", encoding="utf-8")
    source = root / "input.txt"
    source.write_text("source", encoding="utf-8")
    mod_root = root / "mods" / "sample"
    tooling = mod_root / ".ck3mm"
    tooling.mkdir(parents=True)
    (mod_root / "descriptor.mod").write_text('name="Sample"\n', encoding="utf-8")
    (tooling / "mod.toml").write_text(
        f'''\
[generator]
entrypoint = "generator.py:generate"
owned_outputs = ["{owned}"]
[[sources]]
name = "input"
kind = "repository"
path = "input.txt"
''',
        encoding="utf-8",
    )
    (tooling / "generator.py").write_text(generator_source, encoding="utf-8")
    workspace = Workspace.from_path(root)
    return workspace, workspace.get_mod("sample")


def test_output_ownership_accepts_files_directories_and_globs() -> None:
    assert output_is_owned("events/a/b.txt", ("events",))
    assert output_is_owned("events/a/b.txt", ("events/**",))
    assert output_is_owned("common/file.txt", ("common/file.txt",))
    assert not output_is_owned("history/file.txt", ("events/**",))
    assert not output_is_owned(".ck3mm/mod.toml", ("**",))


def test_generator_checks_then_promotes_and_removes_stale_outputs(
    tmp_path: Path,
) -> None:
    workspace, mod = make_generated_workspace(
        tmp_path,
        """\
def generate(context):
    return {"generated/new.txt": context.source("input").read_text() + " generated"}
""",
    )
    generated = mod.root / "generated"
    generated.mkdir()
    (generated / "stale.txt").write_text("old", encoding="utf-8")
    config = load_config(tmp_path, environ={})

    checked = run_generator(workspace, mod, config)
    assert checked.changed_files == ("generated/new.txt",)
    assert checked.stale_files == ("generated/stale.txt",)
    assert not (generated / "new.txt").exists()

    promoted = run_generator(workspace, mod, config, check=False)
    assert promoted.promoted
    assert (generated / "new.txt").read_text() == "source generated"
    assert not (generated / "stale.txt").exists()
    assert run_generator(workspace, mod, config).current


def test_generator_output_is_captured_for_structured_callers(tmp_path: Path) -> None:
    workspace, mod = make_generated_workspace(
        tmp_path,
        """\
import sys

def generate(context):
    print("generator progress")
    print("generator warning", file=sys.stderr)
    return {"generated/file.txt": "ok"}
""",
    )

    result = run_generator(workspace, mod, load_config(tmp_path, environ={}))

    assert result.stdout == "generator progress\n"
    assert result.stderr == "generator warning\n"


def test_generator_cannot_stage_undeclared_files(tmp_path: Path) -> None:
    workspace, mod = make_generated_workspace(
        tmp_path,
        """\
def generate(context):
    output = context.stage_dir / "outside.txt"
    output.write_text("bad")
""",
    )

    with pytest.raises(GenerationError, match="undeclared outputs"):
        run_generator(workspace, mod, load_config(tmp_path, environ={}))


def test_source_locks_are_verified_before_generator_execution(tmp_path: Path) -> None:
    workspace, mod = make_generated_workspace(
        tmp_path, 'def generate(context):\n    return {"generated/file.txt": "ok"}\n'
    )
    assert mod.manifest is not None
    lock = mod.manifest.path.with_name("source-lock.json")
    lock.write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "sources": {"input": {"sha256": "0" * 64}},
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(SourceLockError, match="changed sources"):
        run_generator(workspace, mod, load_config(tmp_path, environ={}))

    digest = sha256_path(tmp_path / "input.txt")
    lock.write_text(
        json.dumps({"schemaVersion": 1, "sources": {"input": {"sha256": digest}}}),
        encoding="utf-8",
    )
    assert run_generator(
        workspace, mod, load_config(tmp_path, environ={})
    ).changed_files


def test_sha256_path_keeps_the_directory_hash_format(tmp_path: Path) -> None:
    source = tmp_path / "source"
    nested = source / "nested"
    nested.mkdir(parents=True)
    (source / "alpha.txt").write_text("alpha", encoding="utf-8")
    (nested / "beta.txt").write_text("beta", encoding="utf-8")

    expected = hashlib.sha256()
    for relative in ("alpha.txt", "nested/beta.txt"):
        expected.update(len(relative).to_bytes(8, "big"))
        expected.update(relative.encode())
        expected.update((source / relative).read_bytes())

    assert sha256_path(source) == expected.hexdigest()
