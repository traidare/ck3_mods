from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import ck3mm.install
import ck3mm.preservation
import ck3mm.references
import ck3mm.validation
from ck3mm.cli import main


def workspace_root(root: Path) -> list[str]:
    (root / "pyproject.toml").write_text("", encoding="utf-8")
    return ["--root", str(root)]


def test_heightmap_playset_output_requires_apply(tmp_path: Path, capsys) -> None:
    output = tmp_path / "editor.json"
    base = [
        *workspace_root(tmp_path),
        "map",
        "heightmap",
        "import-playset",
        "--output",
        str(output),
    ]

    assert main(base) == 0
    preview = json.loads(capsys.readouterr().out)
    assert not output.exists()

    assert main([*base, "--apply"]) == 0
    assert json.loads(output.read_text(encoding="utf-8")) == preview


def test_validation_json_is_structured_and_returns_failure(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    mod = tmp_path / "mods" / "sample"
    mod.mkdir(parents=True)
    (mod / "descriptor.mod").write_text('name="Sample"\n', encoding="utf-8")
    check = SimpleNamespace(
        step=SimpleNamespace(value="tiger"),
        status=SimpleNamespace(value="failed"),
        message="Tiger rejected the mod",
        command=("ck3-tiger", "sample"),
        stdout="checked output\n",
        stderr="failure output\n",
        details=("one issue",),
    )
    result = SimpleNamespace(
        mod_slug="sample",
        status=SimpleNamespace(value="failed"),
        checks=(check,),
        ok=False,
        to_dict=lambda: {"mod": "sample", "status": "failed"},
    )
    monkeypatch.setattr(
        ck3mm.validation,
        "validate_mods",
        lambda _workspace, _selected, _config: (result,),
    )

    args = [*workspace_root(tmp_path), "mod", "validate", "sample", "--json"]
    assert main(args) == 1
    assert json.loads(capsys.readouterr().out) == [
        {"mod": "sample", "status": "failed"}
    ]


def test_command_mutation_gates(tmp_path: Path, monkeypatch, capsys) -> None:
    game = tmp_path / "game"
    paradox = tmp_path / "paradox"
    workshop = tmp_path / "workshop"
    for path in (game, paradox, workshop):
        path.mkdir()
    base = [
        *workspace_root(tmp_path),
        "--game-dir",
        str(game),
        "--paradox-dir",
        str(paradox),
        "--workshop-dir",
        str(workshop),
    ]

    install_plan = SimpleNamespace(
        mod_slugs=("sample",), files=(), descriptors=(), removals=()
    )
    installed: list[object] = []
    monkeypatch.setattr(
        ck3mm.install, "plan_install", lambda *_args, **_kwargs: install_plan
    )
    monkeypatch.setattr(ck3mm.install, "apply_install", installed.append)
    assert main([*base, "mod", "install"]) == 0
    capsys.readouterr()
    assert not installed
    assert main([*base, "mod", "install", "--apply"]) == 0
    capsys.readouterr()
    assert installed == [install_plan]

    preservation_plan = SimpleNamespace(to_dict=lambda: {"snapshotName": "Stable"})
    preserved: list[object] = []
    monkeypatch.setattr(
        ck3mm.preservation,
        "plan_preservation",
        lambda *_args, **_kwargs: preservation_plan,
    )
    monkeypatch.setattr(ck3mm.preservation, "apply_preservation", preserved.append)
    assert main([*base, "playset", "preserve", "AGOT"]) == 0
    capsys.readouterr()
    assert not preserved
    assert main([*base, "playset", "preserve", "AGOT", "--apply"]) == 0
    capsys.readouterr()
    assert preserved == [preservation_plan]

    reference_result = SimpleNamespace(
        info_files=1,
        script_doc_logs=0,
        missing=(),
        stale=(),
        unexpected=(),
        manifest_errors=(),
        current=True,
    )
    synced: list[object] = []
    checked: list[object] = []
    monkeypatch.setattr(
        ck3mm.references, "plan_reference_sync", lambda *_args: "reference-plan"
    )
    monkeypatch.setattr(
        ck3mm.references,
        "apply_reference_sync",
        lambda plan: synced.append(plan) or reference_result,
    )
    monkeypatch.setattr(
        ck3mm.references,
        "check_references",
        lambda *_args: checked.append(True) or reference_result,
    )
    assert main([*base, "refs", "sync", "--check"]) == 0
    capsys.readouterr()
    assert checked and not synced
    assert main([*base, "refs", "sync"]) == 0
    capsys.readouterr()
    assert synced == ["reference-plan"]
