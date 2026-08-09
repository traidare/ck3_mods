"""Read native CK3 descriptors and derive Launcher descriptors from them."""

from __future__ import annotations

import os
import tempfile
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path, PurePosixPath


class DescriptorError(ValueError):
    """Raised when a CK3 descriptor cannot be parsed or safely derived."""


@dataclass(frozen=True, slots=True)
class DescriptorField:
    key: str
    values: tuple[str, ...]
    block: bool = False


@dataclass(frozen=True, slots=True)
class Descriptor:
    fields: tuple[DescriptorField, ...]

    def values(self, key: str) -> tuple[str, ...]:
        return tuple(
            value for field in self.fields if field.key == key for value in field.values
        )

    def value(self, key: str, default: str | None = None) -> str | None:
        values = self.values(key)
        if not values:
            return default
        if len(values) > 1:
            raise DescriptorError(f"descriptor field {key!r} occurs more than once")
        return values[0]

    @property
    def name(self) -> str:
        name = self.value("name")
        if not name:
            raise DescriptorError("descriptor is missing a non-empty name")
        return name

    @property
    def version(self) -> str | None:
        return self.value("version")

    @property
    def supported_version(self) -> str | None:
        return self.value("supported_version")

    @property
    def tags(self) -> tuple[str, ...]:
        return self.values("tags")

    @property
    def replace_paths(self) -> tuple[str, ...]:
        return self.values("replace_path")


@dataclass(frozen=True, slots=True)
class _Token:
    kind: str
    value: str
    line: int


def _tokens(text: str) -> Iterator[_Token]:
    index = 0
    line = 1
    while index < len(text):
        character = text[index]
        if character in " \t\r":
            index += 1
            continue
        if character == "\n":
            line += 1
            index += 1
            continue
        if character == "#":
            newline = text.find("\n", index)
            index = len(text) if newline == -1 else newline
            continue
        if character in "={}":
            yield _Token(character, character, line)
            index += 1
            continue
        if character == '"':
            start_line = line
            index += 1
            value: list[str] = []
            while index < len(text):
                character = text[index]
                if character == '"':
                    index += 1
                    break
                if character == "\\":
                    index += 1
                    if index >= len(text):
                        raise DescriptorError(
                            f"unterminated escape on line {start_line}"
                        )
                    escaped = text[index]
                    value.append(
                        {"n": "\n", "r": "\r", "t": "\t"}.get(escaped, escaped)
                    )
                else:
                    value.append(character)
                    if character == "\n":
                        line += 1
                index += 1
            else:
                raise DescriptorError(f"unterminated string on line {start_line}")
            yield _Token("value", "".join(value), start_line)
            continue

        start = index
        while index < len(text) and text[index] not in " \t\r\n#={}":
            index += 1
        yield _Token("value", text[start:index], line)


def parse_descriptor(text: str) -> Descriptor:
    """Parse the root assignments used by native and Launcher descriptors."""
    tokens = list(_tokens(text))
    fields: list[DescriptorField] = []
    index = 0
    while index < len(tokens):
        key = tokens[index]
        if key.kind != "value":
            raise DescriptorError(
                f"expected a descriptor field on line {key.line}, got {key.value!r}"
            )
        index += 1
        if index >= len(tokens) or tokens[index].kind != "=":
            raise DescriptorError(
                f"expected '=' after {key.value!r} on line {key.line}"
            )
        index += 1
        if index >= len(tokens):
            raise DescriptorError(f"missing value for {key.value!r} on line {key.line}")

        if tokens[index].kind != "{":
            value = tokens[index]
            if value.kind != "value":
                raise DescriptorError(
                    f"invalid value for {key.value!r} on line {value.line}"
                )
            fields.append(DescriptorField(key.value, (value.value,)))
            index += 1
            continue

        index += 1
        values: list[str] = []
        depth = 1
        while index < len(tokens) and depth:
            token = tokens[index]
            index += 1
            if token.kind == "{":
                depth += 1
            elif token.kind == "}":
                depth -= 1
            elif token.kind == "value" and depth == 1:
                values.append(token.value)
            elif token.kind == "=" and depth == 1:
                raise DescriptorError(
                    f"nested assignments are not supported in {key.value!r}"
                )
        if depth:
            raise DescriptorError(
                f"unterminated block for {key.value!r} on line {key.line}"
            )
        fields.append(DescriptorField(key.value, tuple(values), block=True))
    return Descriptor(tuple(fields))


def load_descriptor(path: Path) -> Descriptor:
    try:
        return parse_descriptor(path.read_text(encoding="utf-8-sig"))
    except OSError as error:
        raise DescriptorError(f"cannot read descriptor {path}: {error}") from error


def validate_native_descriptor(descriptor: Descriptor) -> None:
    """Require CK3-owned metadata and prohibit Launcher-only ``path`` fields."""
    _ = descriptor.name
    if descriptor.values("path"):
        raise DescriptorError(
            "native descriptor.mod must not contain a Launcher-only path field"
        )


def _quoted(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def render_descriptor(descriptor: Descriptor) -> str:
    """Render a deterministic descriptor, primarily for synthetic metadata."""
    lines: list[str] = []
    for field in descriptor.fields:
        if field.block:
            lines.append(f"{field.key}={{")
            lines.extend(f"\t{_quoted(value)}" for value in field.values)
            lines.append("}")
        else:
            lines.extend(f"{field.key}={_quoted(value)}" for value in field.values)
    return "\n".join(lines) + "\n"


def launcher_descriptor_text(
    native_text: str,
    *,
    mod_slug: str,
    launcher_mod_path: str | None = None,
) -> str:
    """Derive a Launcher descriptor while preserving native descriptor formatting."""
    descriptor = parse_descriptor(native_text)
    validate_native_descriptor(descriptor)
    if not mod_slug or mod_slug in {".", ".."} or "/" in mod_slug or "\\" in mod_slug:
        raise DescriptorError(f"invalid mod slug: {mod_slug!r}")
    mod_path = launcher_mod_path or f"mod/{mod_slug}"
    path = PurePosixPath(mod_path)
    if path.is_absolute() or ".." in path.parts or path.as_posix() in {"", "."}:
        raise DescriptorError(f"invalid Launcher mod path: {mod_path!r}")
    return native_text.rstrip("\n") + f"\npath={_quoted(path.as_posix())}\n"


def derive_launcher_descriptor(
    native_path: Path,
    *,
    mod_slug: str,
    launcher_mod_path: str | None = None,
) -> str:
    try:
        native_text = native_path.read_text(encoding="utf-8-sig")
    except OSError as error:
        raise DescriptorError(
            f"cannot read descriptor {native_path}: {error}"
        ) from error
    return launcher_descriptor_text(
        native_text, mod_slug=mod_slug, launcher_mod_path=launcher_mod_path
    )


def write_launcher_descriptor(
    native_path: Path,
    destination: Path,
    *,
    mod_slug: str,
    launcher_mod_path: str | None = None,
    apply: bool = False,
) -> str:
    """Preview or atomically write a derived Launcher descriptor."""
    content = derive_launcher_descriptor(
        native_path, mod_slug=mod_slug, launcher_mod_path=launcher_mod_path
    )
    if not apply:
        return content
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor_mode = native_path.stat().st_mode & 0o777
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=destination.parent,
            prefix=f".{destination.name}.",
            delete=False,
        ) as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
            temporary = Path(handle.name)
        temporary.chmod(descriptor_mode)
        os.replace(temporary, destination)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return content
