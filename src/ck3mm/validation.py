"""Non-mutating validation of repository-owned CK3 mods."""

from __future__ import annotations

import subprocess
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any, Protocol

from .config import Config, ConfigError, validate_config
from .descriptors import (
    DescriptorError,
    load_descriptor,
    validate_native_descriptor,
)
from .generation import GenerationError, GenerationResult, run_generator
from .workspace import Mod, Workspace, WorkspaceError


class ValidationStatus(StrEnum):
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"


class ValidationStep(StrEnum):
    DESCRIPTOR = "descriptor"
    GENERATOR = "generator"
    TIGER = "tiger"


@dataclass(frozen=True, slots=True)
class CommandExecution:
    returncode: int
    stdout: str = ""
    stderr: str = ""


class CommandRunner(Protocol):
    def __call__(self, command: Sequence[str], *, cwd: Path) -> CommandExecution: ...


class GeneratorRunner(Protocol):
    def __call__(
        self,
        workspace: Workspace,
        mod: Mod | str,
        config: Config,
        *,
        check: bool = True,
        options: Mapping[str, Any] | None = None,
    ) -> GenerationResult: ...


@dataclass(frozen=True, slots=True)
class ValidationCheck:
    step: ValidationStep
    status: ValidationStatus
    message: str
    command: tuple[str, ...] = ()
    stdout: str = ""
    stderr: str = ""
    details: tuple[str, ...] = ()

    @property
    def ok(self) -> bool:
        return self.status in {ValidationStatus.PASSED, ValidationStatus.SKIPPED}

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "step": self.step.value,
            "status": self.status.value,
            "message": self.message,
        }
        if self.command:
            result["command"] = list(self.command)
        if self.stdout:
            result["stdout"] = self.stdout
        if self.stderr:
            result["stderr"] = self.stderr
        if self.details:
            result["details"] = list(self.details)
        return result


@dataclass(frozen=True, slots=True)
class ModValidationResult:
    mod_slug: str
    checks: tuple[ValidationCheck, ...]

    @property
    def status(self) -> ValidationStatus:
        statuses = {check.status for check in self.checks}
        if ValidationStatus.ERROR in statuses:
            return ValidationStatus.ERROR
        if ValidationStatus.FAILED in statuses:
            return ValidationStatus.FAILED
        if ValidationStatus.PASSED in statuses:
            return ValidationStatus.PASSED
        return ValidationStatus.SKIPPED

    @property
    def ok(self) -> bool:
        return all(check.ok for check in self.checks)

    def to_dict(self) -> dict[str, Any]:
        return {
            "mod": self.mod_slug,
            "status": self.status.value,
            "checks": [check.to_dict() for check in self.checks],
        }


def run_command(command: Sequence[str], *, cwd: Path) -> CommandExecution:
    """Run a validation command while retaining all output for rendering."""

    completed = subprocess.run(
        tuple(command),
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
    )
    return CommandExecution(
        returncode=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )


def discover_tiger_config(mod: Mod) -> Path | None:
    """Return the mod's colocated Tiger dependency configuration, if present."""

    colocated = mod.tooling_root / "ck3-tiger.conf"
    return colocated if colocated.is_file() else None


def validate_mod(
    workspace: Workspace,
    mod: Mod | str,
    config: Config,
    *,
    command_runner: CommandRunner = run_command,
    generator_runner: GeneratorRunner = run_generator,
    tiger_executable: str = "ck3-tiger",
) -> ModValidationResult:
    """Validate one local mod without promoting outputs or external writes."""

    selected = workspace.get_mod(mod) if isinstance(mod, str) else mod
    checks = (
        _validate_descriptor(selected),
        _validate_generator(
            workspace,
            selected,
            config,
            generator_runner=generator_runner,
        ),
        _validate_tiger(
            workspace,
            selected,
            config,
            command_runner=command_runner,
            tiger_executable=tiger_executable,
        ),
    )
    return ModValidationResult(mod_slug=selected.slug, checks=checks)


def validate_mods(
    workspace: Workspace,
    mods: Iterable[Mod | str],
    config: Config,
    *,
    command_runner: CommandRunner = run_command,
    generator_runner: GeneratorRunner = run_generator,
    tiger_executable: str = "ck3-tiger",
) -> tuple[ModValidationResult, ...]:
    """Validate only the selected mods, preserving their requested order."""

    return tuple(
        validate_mod(
            workspace,
            mod,
            config,
            command_runner=command_runner,
            generator_runner=generator_runner,
            tiger_executable=tiger_executable,
        )
        for mod in mods
    )


def _validate_descriptor(mod: Mod) -> ValidationCheck:
    try:
        descriptor = load_descriptor(mod.descriptor_path)
        validate_native_descriptor(descriptor)
    except DescriptorError as error:
        return ValidationCheck(
            step=ValidationStep.DESCRIPTOR,
            status=ValidationStatus.FAILED,
            message=str(error),
        )
    return ValidationCheck(
        step=ValidationStep.DESCRIPTOR,
        status=ValidationStatus.PASSED,
        message=f"canonical descriptor is valid: {descriptor.name}",
    )


def _validate_generator(
    workspace: Workspace,
    mod: Mod,
    config: Config,
    *,
    generator_runner: GeneratorRunner,
) -> ValidationCheck:
    if mod.manifest is None or mod.manifest.generator is None:
        return ValidationCheck(
            step=ValidationStep.GENERATOR,
            status=ValidationStatus.SKIPPED,
            message="no generator is configured",
        )
    try:
        result = generator_runner(workspace, mod, config, check=True)
    except (GenerationError, ConfigError, WorkspaceError, OSError) as error:
        return ValidationCheck(
            step=ValidationStep.GENERATOR,
            status=ValidationStatus.ERROR,
            message=f"generator freshness check failed: {error}",
        )
    if result.current:
        return ValidationCheck(
            step=ValidationStep.GENERATOR,
            status=ValidationStatus.PASSED,
            message="generated outputs are current",
        )

    details = (
        *(f"changed: {path}" for path in result.changed_files),
        *(f"stale: {path}" for path in result.stale_files),
    )
    return ValidationCheck(
        step=ValidationStep.GENERATOR,
        status=ValidationStatus.FAILED,
        message="generated outputs are stale; run `ck3mm mod generate`",
        details=details,
    )


def _validate_tiger(
    workspace: Workspace,
    mod: Mod,
    config: Config,
    *,
    command_runner: CommandRunner,
    tiger_executable: str,
) -> ValidationCheck:
    try:
        validate_config(
            config,
            required=("CK3_GAME_DIR", "CK3_PARADOX_DIR"),
        )
    except ConfigError as error:
        return ValidationCheck(
            step=ValidationStep.TIGER,
            status=ValidationStatus.ERROR,
            message=f"ck3-tiger cannot run: {error}",
        )
    assert config.game_dir is not None
    assert config.paradox_dir is not None

    tiger_config = discover_tiger_config(mod)
    command = [
        tiger_executable,
        "--no-color",
        "--consolidate",
        "--game",
        str(config.game_dir),
        "--paradox",
        str(config.paradox_dir),
    ]
    if tiger_config is not None:
        command.extend(("--config", str(tiger_config)))
    command.append(str(mod.descriptor_path))
    command_tuple = tuple(command)

    try:
        execution = command_runner(command_tuple, cwd=workspace.root)
    except FileNotFoundError:
        return ValidationCheck(
            step=ValidationStep.TIGER,
            status=ValidationStatus.ERROR,
            message=(
                f"{tiger_executable} was not found on PATH; run validation inside "
                "`nix develop` or install ck3-tiger, then retry"
            ),
            command=command_tuple,
        )
    except OSError as error:
        return ValidationCheck(
            step=ValidationStep.TIGER,
            status=ValidationStatus.ERROR,
            message=f"could not start {tiger_executable}: {error}",
            command=command_tuple,
        )

    if execution.returncode == 0:
        message = "ck3-tiger passed"
        status = ValidationStatus.PASSED
    else:
        message = f"ck3-tiger exited with status {execution.returncode}"
        status = ValidationStatus.FAILED
    return ValidationCheck(
        step=ValidationStep.TIGER,
        status=status,
        message=message,
        command=command_tuple,
        stdout=execution.stdout,
        stderr=execution.stderr,
    )
