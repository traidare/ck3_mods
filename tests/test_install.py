from __future__ import annotations

from pathlib import Path

import pytest

from ck3mm.install import InstallError, apply_install, plan_install
from ck3mm.workspace import Workspace, WorkspaceSettings


def test_install_is_descriptor_derived_preview_then_apply(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    mod = root / "mods" / "example"
    (mod / ".ck3mm").mkdir(parents=True)
    (mod / "descriptor.mod").write_text('name="Example"\n', encoding="utf-8")
    (mod / "common").mkdir()
    (mod / "common" / "value.txt").write_text("new", encoding="utf-8")
    (mod / ".ck3mm" / "mod.toml").write_text("", encoding="utf-8")
    (mod / "README.md").write_text("development", encoding="utf-8")
    workspace = Workspace(root, WorkspaceSettings())
    launcher = tmp_path / "launcher" / "mod"
    installed = launcher / "example"
    installed.mkdir(parents=True)
    (installed / "stale.txt").write_text("stale", encoding="utf-8")

    plan = plan_install(workspace, launcher)
    assert plan.mod_slugs == ("example",)
    assert not (launcher / "example.mod").exists()
    assert installed.joinpath("stale.txt") in plan.removals
    assert all(".ck3mm" not in item.relative_path for item in plan.files)
    assert all(item.relative_path != "README.md" for item in plan.files)

    apply_install(plan)
    assert (installed / "common" / "value.txt").read_text() == "new"
    assert not (installed / "stale.txt").exists()
    assert 'path="mod/example"' in (launcher / "example.mod").read_text()


def test_install_can_target_one_mod_without_touching_others(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    for slug in ("first", "second"):
        mod = root / "mods" / slug
        mod.mkdir(parents=True)
        (mod / "descriptor.mod").write_text(
            f'name="{slug.title()}"\n', encoding="utf-8"
        )
        (mod / "payload.txt").write_text(slug, encoding="utf-8")
    workspace = Workspace(root, WorkspaceSettings())
    launcher = tmp_path / "launcher" / "mod"
    (launcher / "first").mkdir(parents=True)
    (launcher / "second").mkdir(parents=True)
    (launcher / "second" / "preserve.txt").write_text("keep", encoding="utf-8")

    plan = plan_install(workspace, launcher, mod_slugs=("first",))

    assert plan.mod_slugs == ("first",)
    assert all("second" not in str(path) for path in plan.removals)
    apply_install(plan)
    assert (launcher / "second" / "preserve.txt").read_text() == "keep"
    assert not (launcher / "second.mod").exists()


@pytest.mark.parametrize("destination", ("inside-mods", "contains-mods"))
def test_install_rejects_overlapping_source_and_destination_roots(
    tmp_path: Path, destination: str
) -> None:
    root = tmp_path / "repo"
    mod = root / "mods" / "example"
    mod.mkdir(parents=True)
    (mod / "descriptor.mod").write_text('name="Example"\n', encoding="utf-8")
    workspace = Workspace(root, WorkspaceSettings())
    launcher = root / "mods" / "launcher" if destination == "inside-mods" else root

    with pytest.raises(InstallError, match="must not be inside"):
        plan_install(workspace, launcher)
