from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from ck3mm.config import Config
from ck3mm.validation import (
    CommandExecution,
    ModValidationResult,
    ValidationStatus,
    ValidationStep,
    validate_mod,
)
from ck3mm.workspace import Workspace


def make_workspace(
    root: Path,
    *,
    slug: str = "sample",
    descriptor: str = 'name="Sample"\n',
    manifest: str | None = None,
) -> tuple[Workspace, Config]:
    (root / "pyproject.toml").write_text("", encoding="utf-8")
    mod_root = root / "mods" / slug
    tooling = mod_root / ".ck3mm"
    tooling.mkdir(parents=True)
    (mod_root / "descriptor.mod").write_text(descriptor, encoding="utf-8")
    if manifest is not None:
        (tooling / "mod.toml").write_text(manifest, encoding="utf-8")
    game = root / "game"
    paradox = root / "paradox"
    game.mkdir()
    paradox.mkdir()
    return (
        Workspace.from_path(root),
        Config(repo_root=root, game_dir=game, paradox_dir=paradox),
    )


def check(result: ModValidationResult, step: ValidationStep):
    return next(item for item in result.checks if item.step is step)


def test_validation_returns_typed_checks_and_prefers_colocated_tiger_config(
    tmp_path: Path,
) -> None:
    workspace, config = make_workspace(tmp_path)
    mod = workspace.get_mod("sample")
    primary = mod.root / ".ck3mm" / "ck3-tiger.conf"
    primary.write_text("primary", encoding="utf-8")
    calls: list[tuple[tuple[str, ...], Path]] = []

    def runner(command: Sequence[str], *, cwd: Path) -> CommandExecution:
        calls.append((tuple(command), cwd))
        return CommandExecution(0, stdout="checked\n", stderr="diagnostic\n")

    result = validate_mod(workspace, mod, config, command_runner=runner)

    assert result.status is ValidationStatus.PASSED
    assert result.ok
    assert [item.status for item in result.checks] == [
        ValidationStatus.PASSED,
        ValidationStatus.SKIPPED,
        ValidationStatus.PASSED,
    ]
    tiger = check(result, ValidationStep.TIGER)
    command, cwd = calls[0]
    assert cwd == workspace.root
    assert command[:3] == ("ck3-tiger", "--no-color", "--consolidate")
    assert command[command.index("--game") + 1] == str(config.game_dir)
    assert command[command.index("--paradox") + 1] == str(config.paradox_dir)
    assert command[command.index("--config") + 1] == str(primary)
    assert command[-1] == str(mod.descriptor_path)
    assert tiger.stdout == "checked\n"
    assert tiger.stderr == "diagnostic\n"
    assert result.to_dict()["checks"][2]["command"] == list(command)


def test_generator_freshness_uses_check_mode_without_promoting(
    tmp_path: Path,
) -> None:
    workspace, config = make_workspace(
        tmp_path,
        manifest="""\
[generator]
entrypoint = "generator.py:generate"
owned_outputs = ["generated/**"]
""",
    )
    mod = workspace.get_mod("sample")
    assert mod.manifest is not None
    (mod.manifest.path.parent / "generator.py").write_text(
        'def generate(context):\n    return {"generated/output.txt": "expected\\n"}\n',
        encoding="utf-8",
    )

    def tiger_runner(command: Sequence[str], *, cwd: Path) -> CommandExecution:
        return CommandExecution(0)

    stale = validate_mod(
        workspace,
        mod,
        config,
        command_runner=tiger_runner,
    )
    generation = check(stale, ValidationStep.GENERATOR)
    assert generation.status is ValidationStatus.FAILED
    assert generation.details == ("changed: generated/output.txt",)
    assert not (mod.root / "generated" / "output.txt").exists()

    output = mod.root / "generated" / "output.txt"
    output.parent.mkdir()
    output.write_text("expected\n", encoding="utf-8")
    current = validate_mod(
        workspace,
        mod,
        config,
        command_runner=tiger_runner,
    )
    assert check(current, ValidationStep.GENERATOR).status is ValidationStatus.PASSED


def test_invalid_descriptor_and_missing_tiger_are_actionable_results(
    tmp_path: Path,
) -> None:
    workspace, config = make_workspace(
        tmp_path,
        descriptor='name="Bad"\npath="mod/bad"\n',
    )

    def missing_runner(command: Sequence[str], *, cwd: Path) -> CommandExecution:
        raise FileNotFoundError(command[0])

    result = validate_mod(
        workspace,
        "sample",
        config,
        command_runner=missing_runner,
    )
    descriptor = check(result, ValidationStep.DESCRIPTOR)
    tiger = check(result, ValidationStep.TIGER)

    assert descriptor.status is ValidationStatus.FAILED
    assert "Launcher-only path" in descriptor.message
    assert tiger.status is ValidationStatus.ERROR
    assert "not found on PATH" in tiger.message
    assert "nix develop" in tiger.message
    assert result.status is ValidationStatus.ERROR
    assert not result.ok


def test_missing_tiger_paths_are_reported_without_starting_a_process(
    tmp_path: Path,
) -> None:
    workspace, _ = make_workspace(tmp_path)

    def forbidden_runner(command: Sequence[str], *, cwd: Path) -> CommandExecution:
        raise AssertionError((command, cwd))

    result = validate_mod(
        workspace,
        "sample",
        Config(repo_root=tmp_path),
        command_runner=forbidden_runner,
    )
    tiger = check(result, ValidationStep.TIGER)

    assert tiger.status is ValidationStatus.ERROR
    assert "CK3_GAME_DIR is not set" in tiger.message
    assert "CK3_PARADOX_DIR is not set" in tiger.message
