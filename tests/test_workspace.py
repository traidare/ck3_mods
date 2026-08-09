from __future__ import annotations

from pathlib import Path

import pytest

from ck3mm.config import load_config
from ck3mm.workspace import Workspace, WorkspaceError, discover_root, load_manifest


def write_workspace(root: Path) -> None:
    (root / "pyproject.toml").write_text("", encoding="utf-8")


def test_discovers_root_and_manifest_with_portable_sources(tmp_path: Path) -> None:
    write_workspace(tmp_path)
    nested = tmp_path / "some" / "nested" / "directory"
    nested.mkdir(parents=True)
    mod_root = tmp_path / "mods" / "sample"
    tooling = mod_root / ".ck3mm"
    tooling.mkdir(parents=True)
    (mod_root / "descriptor.mod").write_text('name="Sample"\n', encoding="utf-8")
    (tooling / "mod.toml").write_text(
        """\
[generator]
entrypoint = "generator.py:generate"
owned_outputs = ["common", "events/**"]
assets = ["assets/**"]
[[sources]]
name = "agot"
kind = "workshop"
item_id = 2962333032
path = "common"
[[sources]]
name = "local"
kind = "repository"
path = "inputs/source.txt"
""",
        encoding="utf-8",
    )

    assert discover_root(nested) == tmp_path
    workspace = Workspace.from_path(nested)
    mod = workspace.get_mod("sample")
    assert mod.manifest is not None
    assert mod.manifest.generator is not None
    assert mod.manifest.generator.owned_outputs == ("common", "events/**")
    assert [source.kind for source in mod.manifest.sources] == [
        "workshop",
        "repository",
    ]


def test_resolves_each_source_kind_under_its_configured_root(tmp_path: Path) -> None:
    write_workspace(tmp_path)
    game = tmp_path / "game"
    workshop = tmp_path / "workshop"
    paradox = tmp_path / "paradox"
    for path in (game / "common", workshop / "42", paradox):
        path.mkdir(parents=True)
    (tmp_path / "repo.txt").write_text("repo", encoding="utf-8")

    dependency = tmp_path / "mods" / "dependency"
    dependency.mkdir(parents=True)
    (dependency / "descriptor.mod").write_text('name="Dependency"\n', encoding="utf-8")
    (dependency / "input.txt").write_text("mod", encoding="utf-8")

    mod_root = tmp_path / "mods" / "sample"
    tooling = mod_root / ".ck3mm"
    tooling.mkdir(parents=True)
    (mod_root / "descriptor.mod").write_text('name="Sample"\n', encoding="utf-8")
    manifest_path = tooling / "mod.toml"
    manifest_path.write_text(
        """\
[[sources]]
name = "workshop"
kind = "workshop"
item_id = "42"
[[sources]]
name = "game"
kind = "game"
path = "common"
[[sources]]
name = "repository"
kind = "repository"
path = "repo.txt"
[[sources]]
name = "dependency"
kind = "mod"
mod = "dependency"
path = "input.txt"
""",
        encoding="utf-8",
    )
    workspace = Workspace.from_path(tmp_path)
    manifest = load_manifest(manifest_path, default_slug="sample")
    config = load_config(
        tmp_path,
        environ={
            "CK3_GAME_DIR": str(game),
            "CK3_PARADOX_DIR": str(paradox),
            "CK3_WORKSHOP_DIR": str(workshop),
        },
    )

    resolved = workspace.resolve_sources(manifest, config)
    assert resolved == {
        "workshop": workshop / "42",
        "game": game / "common",
        "repository": tmp_path / "repo.txt",
        "dependency": dependency / "input.txt",
    }


@pytest.mark.parametrize(
    "manifest, message",
    [
        (
            '[generator]\nentrypoint="generator.py:generate"\n'
            'owned_outputs=["../outside"]\n',
            "must stay within",
        ),
        (
            '[[sources]]\nname="bad"\nkind="game"\npath="../outside"\n',
            "must stay within",
        ),
    ],
)
def test_manifest_paths_cannot_escape(
    tmp_path: Path, manifest: str, message: str
) -> None:
    path = tmp_path / "mod.toml"
    path.write_text(manifest, encoding="utf-8")
    with pytest.raises(WorkspaceError, match=message):
        load_manifest(path, default_slug="sample")
