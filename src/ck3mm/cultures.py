"""Inspect CK3 cultures and traditions from the effective live playset."""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, NoReturn

from .config import Config
from .launcher import DATABASE_NAME, LauncherError
from .playsets import load_live_playset

CULTURES_PATH = "common/culture/cultures"
TRADITIONS_PATH = "common/culture/traditions"


class CultureToolError(Exception):
    """A user-facing error that prevents a complete result."""


@dataclass(frozen=True)
class Token:
    kind: str
    value: str
    start: int
    end: int
    line: int


@dataclass(frozen=True)
class Block:
    key: Token
    open_index: int
    close_index: int


@dataclass(frozen=True)
class Descriptor:
    name: str | None
    path: str | None
    archive: str | None
    remote_file_id: str | None
    replace_paths: tuple[str, ...]


@dataclass(frozen=True)
class Layer:
    kind: str
    name: str
    position: int | None
    identifier: str
    root: Path
    replace_paths: tuple[str, ...]


@dataclass(frozen=True)
class VirtualFile:
    relative_path: str
    absolute_path: Path
    layer: Layer


@dataclass(frozen=True)
class Definition:
    identifier: str
    text: str
    layer: Layer
    relative_path: str
    line: int
    traditions: tuple[str, ...] = ()


@dataclass(frozen=True)
class Database:
    playset_name: str
    cultures: dict[str, Definition]
    traditions: dict[str, Definition]


def fail(message: str) -> NoReturn:
    raise CultureToolError(message)


def decode_quoted(raw: str) -> str:
    value: list[str] = []
    index = 0
    while index < len(raw):
        if raw[index] == "\\" and index + 1 < len(raw):
            following = raw[index + 1]
            if following in {'"', "\\"}:
                value.append(following)
                index += 2
                continue
        value.append(raw[index])
        index += 1
    return "".join(value)


def tokenize(text: str, label: str) -> list[Token]:
    """Tokenize the Paradox subset needed for descriptors and database blocks."""
    tokens: list[Token] = []
    index = 0
    line = 1
    length = len(text)

    while index < length:
        character = text[index]
        if character.isspace():
            if character == "\n":
                line += 1
            index += 1
            continue
        if character == "#":
            newline = text.find("\n", index)
            if newline == -1:
                break
            index = newline
            continue
        if character in "{}=":
            kind = {"{": "lbrace", "}": "rbrace", "=": "equal"}[character]
            tokens.append(Token(kind, character, index, index + 1, line))
            index += 1
            continue
        if character == '"':
            start = index
            start_line = line
            index += 1
            raw: list[str] = []
            while index < length:
                character = text[index]
                if character == '"':
                    index += 1
                    tokens.append(
                        Token(
                            "string",
                            decode_quoted("".join(raw)),
                            start,
                            index,
                            start_line,
                        )
                    )
                    break
                if character == "\\" and index + 1 < length:
                    raw.append(character)
                    raw.append(text[index + 1])
                    index += 2
                    continue
                if character == "\n":
                    line += 1
                raw.append(character)
                index += 1
            else:
                fail(f"{label}:{start_line}: unterminated quoted string")
            continue

        start = index
        start_line = line
        while index < length:
            character = text[index]
            if character.isspace() or character in '#{}="':
                break
            index += 1
        if start == index:
            # An isolated quote is handled above; this protects against a future
            # delimiter being added without a matching lexer branch.
            fail(f"{label}:{line}: cannot tokenize {text[index]!r}")
        tokens.append(Token("atom", text[start:index], start, index, start_line))

    return tokens


def matching_braces(tokens: list[Token], label: str) -> dict[int, int]:
    matches: dict[int, int] = {}
    stack: list[int] = []
    for index, token in enumerate(tokens):
        if token.kind == "lbrace":
            stack.append(index)
        elif token.kind == "rbrace":
            if not stack:
                fail(f"{label}:{token.line}: unexpected closing brace")
            matches[stack.pop()] = index
    if stack:
        token = tokens[stack[-1]]
        fail(f"{label}:{token.line}: unclosed block")
    return matches


def top_level_blocks(tokens: list[Token], matches: dict[int, int]) -> list[Block]:
    blocks: list[Block] = []
    depth = 0
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if token.kind == "lbrace":
            depth += 1
            index += 1
            continue
        if token.kind == "rbrace":
            depth -= 1
            index += 1
            continue
        if (
            depth == 0
            and token.kind in {"atom", "string"}
            and index + 2 < len(tokens)
            and tokens[index + 1].kind == "equal"
            and tokens[index + 2].kind == "lbrace"
        ):
            open_index = index + 2
            close_index = matches[open_index]
            blocks.append(Block(token, open_index, close_index))
            index = close_index + 1
            continue
        index += 1
    return blocks


def direct_assignments(
    tokens: list[Token],
    matches: dict[int, int],
    open_index: int,
    close_index: int,
) -> Iterable[tuple[Token, Token, int | None]]:
    """Yield immediate key/value assignments within one block."""
    index = open_index + 1
    while index < close_index:
        token = tokens[index]
        if (
            token.kind in {"atom", "string"}
            and index + 2 < close_index
            and tokens[index + 1].kind == "equal"
        ):
            value = tokens[index + 2]
            if value.kind == "lbrace":
                value_close = matches[index + 2]
                yield token, value, value_close
                index = value_close + 1
                continue
            yield token, value, None
            index += 3
            continue
        if token.kind == "lbrace":
            index = matches[index] + 1
            continue
        index += 1


def block_values(tokens: list[Token], open_index: int, close_index: int) -> list[str]:
    values: list[str] = []
    depth = 0
    index = open_index + 1
    while index < close_index:
        token = tokens[index]
        if token.kind == "lbrace":
            depth += 1
        elif token.kind == "rbrace":
            depth -= 1
        elif depth == 0 and token.kind in {"atom", "string"}:
            next_kind = tokens[index + 1].kind if index + 1 < close_index else None
            if next_kind != "equal":
                values.append(token.value)
        index += 1
    return values


def scalar_assignments(text: str, label: str) -> dict[str, list[str]]:
    tokens = tokenize(text, label)
    matching_braces(tokens, label)
    values: dict[str, list[str]] = {}
    depth = 0
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if token.kind == "lbrace":
            depth += 1
            index += 1
            continue
        if token.kind == "rbrace":
            depth -= 1
            index += 1
            continue
        if (
            depth == 0
            and token.kind in {"atom", "string"}
            and index + 2 < len(tokens)
            and tokens[index + 1].kind == "equal"
            and tokens[index + 2].kind in {"atom", "string"}
        ):
            values.setdefault(token.value, []).append(tokens[index + 2].value)
            index += 3
            continue
        index += 1
    return values


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError as exc:
        fail(f"{path}: is not valid UTF-8: {exc}")
    except OSError as exc:
        fail(f"could not read {path}: {exc}")


def parse_descriptor(path: Path) -> Descriptor:
    if not path.is_file():
        fail(f"mod descriptor not found: {path}")
    values = scalar_assignments(read_text(path), str(path))

    def last(key: str) -> str | None:
        items = values.get(key, [])
        return items[-1] if items else None

    return Descriptor(
        name=last("name"),
        path=last("path"),
        archive=last("archive"),
        remote_file_id=last("remote_file_id"),
        replace_paths=tuple(values.get("replace_path", [])),
    )


def find_payload_descriptor(root: Path, *, required: bool) -> Path | None:
    try:
        candidates = sorted(
            (
                path
                for path in root.iterdir()
                if path.is_file() and path.suffix.lower() == ".mod"
            ),
            key=lambda path: path.name.encode("utf-8"),
        )
    except OSError as exc:
        fail(f"could not inspect mod payload {root}: {exc}")
    preferred = [path for path in candidates if path.name.lower() == "descriptor.mod"]
    if len(preferred) == 1:
        return preferred[0]
    if len(candidates) == 1:
        return candidates[0]
    if not candidates and not required:
        return None
    if not candidates:
        fail(f"mod payload has no root-level .mod descriptor: {root}")
    rendered = ", ".join(path.name for path in candidates)
    fail(f"mod payload has ambiguous root-level descriptors in {root}: {rendered}")


def merge_replace_paths(*groups: Iterable[str]) -> tuple[str, ...]:
    normalized = {
        value.replace("\\", "/").strip("/")
        for group in groups
        for value in group
        if value
    }
    return tuple(sorted(normalized, key=lambda value: value.encode("utf-8")))


def resolve_payload_path(
    descriptor_path: Path, descriptor: Descriptor, paradox_dir: Path
) -> Path:
    if descriptor.archive:
        fail(
            f"{descriptor_path}: archive-backed mods are not supported "
            f"({descriptor.archive})"
        )
    if not descriptor.path:
        fail(f"{descriptor_path}: descriptor has no path")

    payload = Path(descriptor.path).expanduser()
    if not payload.is_absolute():
        payload = paradox_dir / payload
    if not payload.is_dir():
        fallback = paradox_dir / "mod" / payload.name
        if fallback.is_dir():
            payload = fallback
    if not payload.is_dir():
        fail(f"{descriptor_path}: mod payload directory not found: {payload}")
    return payload.resolve()


def layer_from_registry(
    *,
    descriptor_path: Path,
    kind: str,
    name: str,
    position: int,
    identifier: str,
    paradox_dir: Path,
) -> Layer:
    launcher_descriptor = parse_descriptor(descriptor_path)
    root = resolve_payload_path(descriptor_path, launcher_descriptor, paradox_dir)
    payload_descriptor_path = find_payload_descriptor(root, required=False)
    payload_descriptor = (
        parse_descriptor(payload_descriptor_path)
        if payload_descriptor_path is not None
        else Descriptor(None, None, None, None, ())
    )
    if payload_descriptor.archive:
        fail(
            f"{payload_descriptor_path}: archive-backed mods are not supported "
            f"({payload_descriptor.archive})"
        )
    return Layer(
        kind=kind,
        name=name,
        position=position,
        identifier=identifier,
        root=root,
        replace_paths=merge_replace_paths(
            launcher_descriptor.replace_paths,
            payload_descriptor.replace_paths,
        ),
    )


def find_pdx_descriptor(pdx_id: str, paradox_dir: Path) -> Path:
    mod_dir = paradox_dir / "mod"
    if not mod_dir.is_dir():
        fail(f"launcher mod directory not found: {mod_dir}")
    candidates: list[Path] = []
    for path in sorted(mod_dir.glob("*.mod")):
        descriptor = parse_descriptor(path)
        if descriptor.remote_file_id == pdx_id:
            candidates.append(path)
    if not candidates:
        fail(f"no installed descriptor found for Paradox mod {pdx_id}")
    if len(candidates) > 1:
        rendered = ", ".join(str(path) for path in candidates)
        fail(f"multiple descriptors match Paradox mod {pdx_id}: {rendered}")
    return candidates[0]


def resolve_layers(
    playset: dict[str, Any], workshop_dir: Path, paradox_dir: Path
) -> list[Layer]:
    raw_mods = playset.get("mods")
    if not isinstance(raw_mods, list):
        fail('ck3-playsets.py returned JSON without a "mods" array')

    layers: list[tuple[int, int, Layer]] = []
    for source_index, item in enumerate(raw_mods):
        if not isinstance(item, dict):
            fail(f"playset mod entry {source_index} is not an object")
        if not item.get("enabled", True):
            continue

        name = str(item.get("displayName") or f"entry {source_index}")
        try:
            position = int(item.get("position", source_index))
        except (TypeError, ValueError):
            fail(f"{name}: invalid playset position {item.get('position')!r}")

        steam_id = item.get("steamId")
        registry_id = item.get("gameRegistryId")
        pdx_id = item.get("pdxId")
        if steam_id is not None:
            identifier = str(steam_id)
            root = workshop_dir / identifier
            if not root.is_dir():
                fail(f"{name}: Workshop payload directory not found: {root}")
            launcher_descriptor_path = paradox_dir / "mod" / f"ugc_{identifier}.mod"
            launcher_descriptor = (
                parse_descriptor(launcher_descriptor_path)
                if launcher_descriptor_path.is_file()
                else Descriptor(None, None, None, None, ())
            )
            if launcher_descriptor.archive:
                fail(
                    f"{launcher_descriptor_path}: archive-backed mods are not "
                    f"supported ({launcher_descriptor.archive})"
                )
            descriptor_path = find_payload_descriptor(root, required=True)
            assert descriptor_path is not None
            descriptor = parse_descriptor(descriptor_path)
            if descriptor.archive:
                fail(
                    f"{descriptor_path}: archive-backed mods are not supported "
                    f"({descriptor.archive})"
                )
            layer = Layer(
                kind="steam",
                name=name,
                position=position,
                identifier=identifier,
                root=root.resolve(),
                replace_paths=merge_replace_paths(
                    launcher_descriptor.replace_paths,
                    descriptor.replace_paths,
                ),
            )
        elif registry_id is not None:
            identifier = str(registry_id).replace("\\", "/")
            descriptor_path = paradox_dir / Path(identifier)
            layer = layer_from_registry(
                descriptor_path=descriptor_path,
                kind="local",
                name=name,
                position=position,
                identifier=identifier,
                paradox_dir=paradox_dir,
            )
        elif pdx_id is not None:
            identifier = str(pdx_id)
            layer = layer_from_registry(
                descriptor_path=find_pdx_descriptor(identifier, paradox_dir),
                kind="pdx",
                name=name,
                position=position,
                identifier=identifier,
                paradox_dir=paradox_dir,
            )
        else:
            fail(
                f"{name}: enabled mod has no Steam ID, Paradox ID, or local registry ID"
            )
        layers.append((position, source_index, layer))

    layers.sort(key=lambda entry: (entry[0], entry[1]))
    return [entry[2] for entry in layers]


def selected_game_root(game_dir: Path) -> Path:
    candidates = (game_dir, game_dir / "game")
    for candidate in candidates:
        if (candidate / CULTURES_PATH).is_dir() and (
            candidate / TRADITIONS_PATH
        ).is_dir():
            return candidate.resolve()
    fail(
        f"CK3 data directories were not found below {game_dir}; expected "
        f"{CULTURES_PATH} and {TRADITIONS_PATH}, optionally below game/"
    )


def immediate_text_files(root: Path, relative_dir: str) -> list[Path]:
    directory = root / relative_dir
    if not directory.is_dir():
        return []
    try:
        return sorted(
            (
                path
                for path in directory.iterdir()
                if path.is_file() and path.suffix == ".txt"
            ),
            key=lambda path: path.name.encode("utf-8"),
        )
    except OSError as exc:
        fail(f"could not list {directory}: {exc}")


def virtual_files(
    game_root: Path, layers: list[Layer], relative_dir: str
) -> list[VirtualFile]:
    files: dict[str, VirtualFile] = {}
    vanilla_replaced = any(relative_dir in layer.replace_paths for layer in layers)
    vanilla = Layer(
        kind="game",
        name="Crusader Kings III",
        position=None,
        identifier="vanilla",
        root=game_root,
        replace_paths=(),
    )
    if not vanilla_replaced:
        for path in immediate_text_files(game_root, relative_dir):
            relative_path = f"{relative_dir}/{path.name}"
            files[relative_path] = VirtualFile(relative_path, path, vanilla)

    for layer in layers:
        for path in immediate_text_files(layer.root, relative_dir):
            relative_path = f"{relative_dir}/{path.name}"
            files[relative_path] = VirtualFile(relative_path, path, layer)

    return [
        files[key] for key in sorted(files, key=lambda value: value.encode("utf-8"))
    ]


def culture_traditions(
    tokens: list[Token],
    matches: dict[int, int],
    block: Block,
) -> tuple[str, ...]:
    traditions: set[str] = set()
    for key, value, value_close in direct_assignments(
        tokens, matches, block.open_index, block.close_index
    ):
        if key.value == "traditions" and value.kind == "lbrace":
            assert value_close is not None
            value_open = tokens.index(value)
            traditions.update(block_values(tokens, value_open, value_close))
        elif key.value == "dlc_tradition" and value.kind == "lbrace":
            assert value_close is not None
            value_open = tokens.index(value)
            for child_key, child_value, child_close in direct_assignments(
                tokens, matches, value_open, value_close
            ):
                if (
                    child_key.value == "trait"
                    and child_close is None
                    and child_value.kind in {"atom", "string"}
                ):
                    traditions.add(child_value.value)
    return tuple(sorted(traditions))


def parse_database_files(
    files: list[VirtualFile], *, cultures: bool
) -> dict[str, Definition]:
    definitions: dict[str, Definition] = {}
    for virtual_file in files:
        text = read_text(virtual_file.absolute_path)
        tokens = tokenize(text, str(virtual_file.absolute_path))
        matches = matching_braces(tokens, str(virtual_file.absolute_path))
        for block in top_level_blocks(tokens, matches):
            close = tokens[block.close_index]
            identifier = block.key.value
            assigned = culture_traditions(tokens, matches, block) if cultures else ()
            definitions[identifier] = Definition(
                identifier=identifier,
                text=text[block.key.start : close.end],
                layer=virtual_file.layer,
                relative_path=virtual_file.relative_path,
                line=block.key.line,
                traditions=assigned,
            )
    return definitions


def invoke_playsets(
    playset_name: str | None, db_path: Path | None, paradox_dir: Path
) -> dict[str, Any]:
    path = db_path or paradox_dir / DATABASE_NAME
    try:
        return load_live_playset(path, name=playset_name).to_dict()
    except LauncherError as exc:
        fail(str(exc))


def required_directory(argument: Path | None, environment_name: str) -> Path:
    raw = argument if argument is not None else os.environ.get(environment_name)
    if raw is None or str(raw).strip() == "":
        option_name = environment_name[4:].lower().replace("_", "-")
        fail(f"pass --{option_name} or set ${environment_name}")
    path = Path(raw).expanduser()
    if not path.is_dir():
        fail(f"{environment_name} directory not found: {path}")
    return path.resolve()


def load_database(args: argparse.Namespace, config: Config | None = None) -> Database:
    game_dir = required_directory(
        getattr(args, "game_dir", None) or (config.game_dir if config else None),
        "CK3_GAME_DIR",
    )
    workshop_dir = required_directory(
        getattr(args, "workshop_dir", None)
        or (config.workshop_dir if config else None),
        "CK3_WORKSHOP_DIR",
    )
    paradox_dir = required_directory(
        getattr(args, "paradox_dir", None) or (config.paradox_dir if config else None),
        "CK3_PARADOX_DIR",
    )
    playset = invoke_playsets(
        getattr(args, "playset", None) or (config.playset_name if config else None),
        getattr(args, "db", None),
        paradox_dir,
    )
    playset_name = str(playset.get("name") or "").strip()
    if not playset_name:
        fail("the selected playset has no name")
    layers = resolve_layers(playset, workshop_dir, paradox_dir)
    game_root = selected_game_root(game_dir)
    cultures = parse_database_files(
        virtual_files(game_root, layers, CULTURES_PATH), cultures=True
    )
    traditions = parse_database_files(
        virtual_files(game_root, layers, TRADITIONS_PATH), cultures=False
    )
    return Database(playset_name, cultures, traditions)


def source_json(definition: Definition) -> dict[str, Any]:
    layer = definition.layer
    source: dict[str, Any] = {
        "layer": layer.kind,
        "name": layer.name,
        "identifier": layer.identifier,
        "file": definition.relative_path,
        "line": definition.line,
    }
    if layer.position is not None:
        source["position"] = layer.position
    return source


def write_json(value: Any) -> None:
    json.dump(value, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")


def ensure_known_traditions(
    requested: Iterable[str], traditions: dict[str, Definition]
) -> tuple[str, ...]:
    values = tuple(dict.fromkeys(requested))
    unknown = sorted(value for value in values if value not in traditions)
    if unknown:
        fail("unknown tradition(s): " + ", ".join(unknown))
    return values


def list_cultures(args: argparse.Namespace, database: Database) -> None:
    requested = ensure_known_traditions(args.tradition, database.traditions)
    match = args.match
    selected: list[Definition] = []
    for identifier in sorted(database.cultures):
        definition = database.cultures[identifier]
        assigned = set(definition.traditions)
        if requested:
            matches = [tradition in assigned for tradition in requested]
            if match == "all" and not all(matches):
                continue
            if match == "any" and not any(matches):
                continue
        selected.append(definition)

    if args.output_format == "json":
        cultures: list[dict[str, Any]] = []
        for definition in selected:
            item: dict[str, Any] = {
                "id": definition.identifier,
                "source": source_json(definition),
            }
            if args.with_traditions:
                item["traditions"] = list(definition.traditions)
            cultures.append(item)
        write_json(
            {
                "playset": database.playset_name,
                "command": "list-cultures",
                "filter": {
                    "traditions": list(requested),
                    "match": match,
                },
                "cultures": cultures,
            }
        )
        return

    for definition in selected:
        if args.with_traditions:
            print(f"{definition.identifier}: " + ", ".join(definition.traditions))
        else:
            print(definition.identifier)


def list_traditions(args: argparse.Namespace, database: Database) -> None:
    selected = [
        database.traditions[identifier] for identifier in sorted(database.traditions)
    ]
    if args.output_format == "json":
        write_json(
            {
                "playset": database.playset_name,
                "command": "list-traditions",
                "traditions": [
                    {
                        "id": definition.identifier,
                        "source": source_json(definition),
                    }
                    for definition in selected
                ],
            }
        )
        return
    for definition in selected:
        print(definition.identifier)


def show_tradition(args: argparse.Namespace, database: Database) -> None:
    definition = database.traditions.get(args.tradition_id)
    if definition is None:
        fail(f"unknown tradition: {args.tradition_id}")
    if args.output_format == "json":
        write_json(
            {
                "playset": database.playset_name,
                "command": "show-tradition",
                "tradition": {
                    "id": definition.identifier,
                    "definition": definition.text,
                    "source": source_json(definition),
                },
            }
        )
        return
    sys.stdout.write(definition.text)
    if not definition.text.endswith("\n"):
        sys.stdout.write("\n")


def common_options() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument(
        "--playset",
        default=argparse.SUPPRESS,
        help=(
            "exact playset name; defaults to $CK3_PLAYSET_NAME, then the "
            "active Launcher playset"
        ),
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=argparse.SUPPRESS,
        help="Launcher database override",
    )
    parser.add_argument(
        "--format",
        dest="output_format",
        choices=("text", "json"),
        default=argparse.SUPPRESS,
        help="output format (default: text)",
    )
    parser.add_argument(
        "--game-dir",
        type=Path,
        default=argparse.SUPPRESS,
        help="CK3 installation directory (default: $CK3_GAME_DIR)",
    )
    parser.add_argument(
        "--workshop-dir",
        type=Path,
        default=argparse.SUPPRESS,
        help="CK3 Workshop directory (default: $CK3_WORKSHOP_DIR)",
    )
    parser.add_argument(
        "--paradox-dir",
        type=Path,
        default=argparse.SUPPRESS,
        help="CK3 user-data directory (default: $CK3_PARADOX_DIR)",
    )
    return parser


def build_parser() -> argparse.ArgumentParser:
    shared = common_options()
    parser = argparse.ArgumentParser(
        description=(
            "Inspect effective CK3 cultures and traditions from a live "
            "Launcher playset."
        ),
        parents=[shared],
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    cultures_parser = subparsers.add_parser(
        "list-cultures",
        parents=[shared],
        help="list effective static cultures",
    )
    cultures_parser.add_argument(
        "--with-traditions",
        action="store_true",
        help="include each culture's assigned traditions",
    )
    cultures_parser.add_argument(
        "--tradition",
        action="append",
        default=[],
        help="only include cultures with this tradition; repeatable",
    )
    cultures_parser.add_argument(
        "--match",
        choices=("all", "any"),
        default="all",
        help="how repeated --tradition filters combine (default: all)",
    )
    cultures_parser.set_defaults(handler=list_cultures)

    traditions_parser = subparsers.add_parser(
        "list-traditions",
        parents=[shared],
        help="list effective tradition definitions",
    )
    traditions_parser.set_defaults(handler=list_traditions)

    show_parser = subparsers.add_parser(
        "show-tradition",
        parents=[shared],
        help="print the exact effective definition of one tradition",
    )
    show_parser.add_argument("tradition_id", help="tradition database ID")
    show_parser.set_defaults(handler=show_tradition)
    return parser


def main(
    argv: Iterable[str] | None = None,
    *,
    config: Config | None = None,
) -> int:
    args = build_parser().parse_args(list(argv) if argv is not None else None)
    if not hasattr(args, "output_format"):
        args.output_format = "text"
    try:
        database = load_database(args, config)
        args.handler(args, database)
    except CultureToolError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except BrokenPipeError:
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
