from __future__ import annotations

from pathlib import Path

import pytest

from ck3mm.descriptors import (
    DescriptorError,
    derive_launcher_descriptor,
    launcher_descriptor_text,
    parse_descriptor,
    validate_native_descriptor,
    write_launcher_descriptor,
)

NATIVE = """\
version="1.2.3"
tags={
    "Fixes"
    "Utilities"
}
name="Example Mod"
replace_path="common/old"
supported_version="1.19.*"
"""


def test_parses_native_descriptor_fields_and_repeated_metadata() -> None:
    descriptor = parse_descriptor(NATIVE)

    assert descriptor.name == "Example Mod"
    assert descriptor.version == "1.2.3"
    assert descriptor.supported_version == "1.19.*"
    assert descriptor.tags == ("Fixes", "Utilities")
    assert descriptor.replace_paths == ("common/old",)
    validate_native_descriptor(descriptor)


def test_launcher_descriptor_is_derived_from_canonical_native_text() -> None:
    launcher = launcher_descriptor_text(NATIVE, mod_slug="example")

    assert launcher.startswith(NATIVE)
    assert launcher.endswith('path="mod/example"\n')
    assert parse_descriptor(launcher).value("path") == "mod/example"


def test_native_descriptor_must_not_contain_launcher_path() -> None:
    with pytest.raises(DescriptorError, match="Launcher-only path"):
        validate_native_descriptor(parse_descriptor('name="Bad"\npath="mod/bad"\n'))


def test_launcher_write_previews_by_default_and_applies_atomically(
    tmp_path: Path,
) -> None:
    native = tmp_path / "descriptor.mod"
    destination = tmp_path / "launcher" / "example.mod"
    native.write_text(NATIVE, encoding="utf-8")

    preview = write_launcher_descriptor(
        native, destination, mod_slug="example", apply=False
    )
    assert not destination.exists()
    assert preview == derive_launcher_descriptor(native, mod_slug="example")

    write_launcher_descriptor(native, destination, mod_slug="example", apply=True)
    assert destination.read_text(encoding="utf-8") == preview
