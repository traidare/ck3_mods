from pathlib import Path

from ck3mm.discovery import discover_playset
from ck3mm.playsets import Playset, PlaysetMod


def write_descriptor(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_discovers_workshop_and_local_providers_without_report_paths(
    tmp_path: Path,
) -> None:
    workshop = tmp_path / "workshop"
    paradox = tmp_path / "paradox"
    write_descriptor(
        workshop / "123" / "descriptor.mod",
        'name="Workshop"\nreplace_path="common/old"\n',
    )
    (workshop / "123" / "common").mkdir()
    local_root = tmp_path / "repository" / "mods" / "local"
    write_descriptor(local_root / "descriptor.mod", 'name="Local"\n')
    write_descriptor(
        paradox / "mod" / "local.mod",
        f'name="Local"\npath="{local_root}"\n',
    )
    playset = Playset(
        "Test",
        (
            PlaysetMod("Workshop", True, 0, steam_id="123"),
            PlaysetMod(
                "Local",
                True,
                1,
                source="local",
                game_registry_id="mod/local.mod",
            ),
        ),
    )

    discovery = discover_playset(playset, workshop_dir=workshop, paradox_dir=paradox)
    assert [provider.stable_id for provider in discovery.providers] == [
        "steam:123",
        "local:mod/local.mod",
    ]
    assert discovery.providers[0].replace_paths == ("common/old",)
    assert not discovery.warnings
    assert "root" not in discovery.providers[0].to_record().to_dict()


def test_missing_enabled_mod_is_a_structured_warning(tmp_path: Path) -> None:
    playset = Playset("Test", (PlaysetMod("Missing", True, 4, steam_id="999"),))
    discovery = discover_playset(
        playset,
        workshop_dir=tmp_path / "workshop",
        paradox_dir=tmp_path / "paradox",
    )
    assert not discovery.providers
    assert discovery.warnings[0].code == "enabled_mod_missing"
    assert discovery.warnings[0].mod_id == "steam:999"
    assert str(tmp_path) not in discovery.warnings[0].message
