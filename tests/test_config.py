from __future__ import annotations

from pathlib import Path

import pytest

from ck3mm.config import ConfigError, load_config, read_dotenv, validate_config


def test_configuration_precedence_and_launcher_database(tmp_path: Path) -> None:
    dotenv_game = tmp_path / "dotenv-game"
    environment_game = tmp_path / "environment-game"
    explicit_game = tmp_path / "explicit-game"
    paradox = tmp_path / "paradox"
    workshop = tmp_path / "workshop"
    for path in (dotenv_game, environment_game, explicit_game, paradox, workshop):
        path.mkdir()
    (tmp_path / ".env").write_text(
        "\n".join(
            (
                f'CK3_GAME_DIR="{dotenv_game}"',
                f"CK3_PARADOX_DIR={paradox}",
                f"CK3_WORKSHOP_DIR={workshop} # local workshop",
                "CK3_PLAYSET_NAME=dotenv playset",
            )
        ),
        encoding="utf-8",
    )

    config = load_config(
        tmp_path,
        environ={
            "CK3_GAME_DIR": str(environment_game),
            "CK3_PLAYSET_NAME": "environment playset",
        },
        overrides={"game_dir": explicit_game, "playset_name": "explicit playset"},
    )

    assert config.game_dir == explicit_game
    assert config.paradox_dir == paradox
    assert config.workshop_dir == workshop
    assert config.playset_name == "explicit playset"
    assert config.launcher_db == paradox / "launcher-v2.sqlite"
    validate_config(config)


def test_dotenv_supports_export_quotes_and_does_not_modify_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    dotenv = tmp_path / ".env"
    dotenv.write_text(
        "export SIMPLE=value\nSINGLE='literal # value'\nDOUBLE=\"line\\nvalue\"\n",
        encoding="utf-8",
    )
    monkeypatch.delenv("SIMPLE", raising=False)

    assert read_dotenv(dotenv) == {
        "SIMPLE": "value",
        "SINGLE": "literal # value",
        "DOUBLE": "line\nvalue",
    }
    assert "SIMPLE" not in __import__("os").environ


def test_relative_paths_and_missing_required_values_are_rejected(
    tmp_path: Path,
) -> None:
    with pytest.raises(ConfigError, match="CK3_GAME_DIR must be an absolute path"):
        load_config(tmp_path, environ={"CK3_GAME_DIR": "relative/game"})

    config = load_config(tmp_path, environ={})
    with pytest.raises(ConfigError, match="CK3_GAME_DIR is not set") as error:
        validate_config(config)
    assert "CK3_PARADOX_DIR is not set" in str(error.value)
    assert "CK3_WORKSHOP_DIR is not set" in str(error.value)
