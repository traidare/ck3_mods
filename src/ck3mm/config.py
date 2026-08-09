"""Centralized local configuration with explicit, environment, and dotenv layers."""

from __future__ import annotations

import os
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path

PATH_VARIABLES = (
    "CK3_GAME_DIR",
    "CK3_PARADOX_DIR",
    "CK3_WORKSHOP_DIR",
    "CK3_STEAM_LOG_DIR",
)
REQUIRED_PATH_VARIABLES = PATH_VARIABLES[:3]
PLAYSET_VARIABLE = "CK3_PLAYSET_NAME"
KNOWN_VARIABLES = (*PATH_VARIABLES, PLAYSET_VARIABLE)

_FIELD_TO_ENV = {
    "game_dir": "CK3_GAME_DIR",
    "paradox_dir": "CK3_PARADOX_DIR",
    "workshop_dir": "CK3_WORKSHOP_DIR",
    "steam_log_dir": "CK3_STEAM_LOG_DIR",
    "playset_name": PLAYSET_VARIABLE,
}
_ENV_TO_FIELD = {value: key for key, value in _FIELD_TO_ENV.items()}
_DOTENV_KEY = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class ConfigError(ValueError):
    """Raised when local CK3 configuration is missing or invalid."""


@dataclass(frozen=True, slots=True)
class Config:
    """Resolved CK3 paths without mutating the process environment."""

    repo_root: Path
    game_dir: Path | None = None
    paradox_dir: Path | None = None
    workshop_dir: Path | None = None
    playset_name: str | None = None
    steam_log_dir: Path | None = None

    @property
    def launcher_db(self) -> Path | None:
        """Return the Launcher database implied by ``CK3_PARADOX_DIR``."""
        if self.paradox_dir is None:
            return None
        return self.paradox_dir / "launcher-v2.sqlite"

    def environment(self) -> dict[str, str]:
        """Return configured values in the names expected by CK3 tooling."""
        result: dict[str, str] = {}
        for field, variable in _FIELD_TO_ENV.items():
            value = getattr(self, field)
            if value is not None:
                result[variable] = str(value)
        return result

    def require(self, *variables: str, must_exist: bool = True) -> Config:
        """Validate selected environment variables and return this configuration."""
        validate_config(self, required=variables, must_exist=must_exist)
        return self


def _strip_inline_comment(value: str) -> str:
    for index, character in enumerate(value):
        if character == "#" and (index == 0 or value[index - 1].isspace()):
            return value[:index].rstrip()
    return value.strip()


def _parse_dotenv_value(value: str, *, line_number: int, path: Path) -> str:
    value = value.strip()
    if not value:
        return ""
    if value[0] not in {"'", '"'}:
        return _strip_inline_comment(value)

    quote = value[0]
    escaped = False
    closing = None
    for index, character in enumerate(value[1:], start=1):
        if quote == '"' and character == "\\" and not escaped:
            escaped = True
            continue
        if character == quote and not escaped:
            closing = index
            break
        escaped = False
    if closing is None:
        raise ConfigError(f"{path}:{line_number}: unterminated quoted value")

    remainder = value[closing + 1 :].strip()
    if remainder and not remainder.startswith("#"):
        raise ConfigError(f"{path}:{line_number}: unexpected text after quoted value")

    parsed = value[1:closing]
    if quote == '"':
        parsed = (
            parsed.replace("\\n", "\n")
            .replace("\\r", "\r")
            .replace("\\t", "\t")
            .replace('\\"', '"')
            .replace("\\\\", "\\")
        )
    return parsed


def read_dotenv(path: Path) -> dict[str, str]:
    """Parse a small, deterministic subset of dotenv syntax."""
    if not path.is_file():
        return {}

    values: dict[str, str] = {}
    for line_number, raw_line in enumerate(
        path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].lstrip()
        if "=" not in line:
            raise ConfigError(f"{path}:{line_number}: expected KEY=VALUE")
        key, raw_value = line.split("=", 1)
        key = key.strip()
        if not _DOTENV_KEY.fullmatch(key):
            raise ConfigError(f"{path}:{line_number}: invalid variable name {key!r}")
        values[key] = _parse_dotenv_value(raw_value, line_number=line_number, path=path)
    return values


def _normalise_overrides(
    overrides: Mapping[str, str | os.PathLike[str] | None] | None,
) -> dict[str, str]:
    result: dict[str, str] = {}
    for key, value in (overrides or {}).items():
        variable = _FIELD_TO_ENV.get(key, key)
        if variable not in KNOWN_VARIABLES:
            raise ConfigError(f"unknown configuration override: {key}")
        if value is not None:
            result[variable] = os.fspath(value)
    return result


def _configured_path(variable: str, raw: str | None) -> Path | None:
    if raw is None or not raw.strip():
        return None
    path = Path(raw).expanduser()
    if not path.is_absolute():
        raise ConfigError(f"{variable} must be an absolute path: {raw}")
    return path.resolve(strict=False)


def load_config(
    repo_root: Path,
    *,
    overrides: Mapping[str, str | os.PathLike[str] | None] | None = None,
    environ: Mapping[str, str] | None = None,
    dotenv_path: Path | None = None,
) -> Config:
    """Resolve configuration with CLI > process environment > repository dotenv.

    Empty values still participate in precedence, making it possible for an explicit
    override to clear an optional setting. The function never updates ``os.environ``.
    """
    root = Path(repo_root).resolve()
    dotenv = read_dotenv(dotenv_path or root / ".env")
    process = dict(os.environ if environ is None else environ)
    explicit = _normalise_overrides(overrides)

    values: dict[str, str | None] = {}
    for variable in KNOWN_VARIABLES:
        if variable in explicit:
            values[variable] = explicit[variable]
        elif variable in process:
            values[variable] = process[variable]
        else:
            values[variable] = dotenv.get(variable)

    playset = values[PLAYSET_VARIABLE]
    return Config(
        repo_root=root,
        game_dir=_configured_path("CK3_GAME_DIR", values["CK3_GAME_DIR"]),
        paradox_dir=_configured_path("CK3_PARADOX_DIR", values["CK3_PARADOX_DIR"]),
        workshop_dir=_configured_path("CK3_WORKSHOP_DIR", values["CK3_WORKSHOP_DIR"]),
        playset_name=playset.strip() if playset and playset.strip() else None,
        steam_log_dir=_configured_path(
            "CK3_STEAM_LOG_DIR", values["CK3_STEAM_LOG_DIR"]
        ),
    )


def validate_config(
    config: Config,
    *,
    required: Iterable[str] = REQUIRED_PATH_VARIABLES,
    must_exist: bool = True,
) -> None:
    """Validate required configured paths, collecting all errors in one message."""
    errors: list[str] = []
    for name in required:
        variable = _FIELD_TO_ENV.get(name, name)
        field = _ENV_TO_FIELD.get(variable)
        if field is None:
            raise ConfigError(f"unknown required configuration variable: {name}")
        value = getattr(config, field)
        if value is None:
            errors.append(f"{variable} is not set")
        elif must_exist and not value.is_dir():
            errors.append(f"{variable} is not a directory: {value}")
    if errors:
        raise ConfigError("invalid CK3 configuration:\n- " + "\n- ".join(errors))
