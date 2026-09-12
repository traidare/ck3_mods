"""Load-order resolution over the parent stack.

CK3 resolves a same-path file by the last module that ships it, and a duplicate
database key by the last definition parsed. Both stages of this module ask those
two questions repeatedly — which module supplies the effective
`hist_titles.txt`, which terrain label wins for a province, which geographical
region block is current — so both are answered here once.

A layer is either a module root on disk or an in-memory overlay produced by an
earlier stage of this same run. The overlay case is what lets one stage hand its
result to a later one without writing an intermediate file into the payload.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Iterable, Iterator
from dataclasses import dataclass
from pathlib import Path

from gen.script import read_text


@dataclass(frozen=True, slots=True)
class Layer:
    """One module in load order: a root on disk, or staged text from this run."""

    label: str
    root: Path | None = None
    files: tuple[tuple[str, str], ...] = ()

    @classmethod
    def of(cls, label: str, root: Path) -> Layer:
        return cls(label=label, root=root)

    @classmethod
    def overlay(cls, label: str, files: dict[str, str]) -> Layer:
        """Wrap texts an earlier stage produced as the topmost layer."""
        return cls(label=label, files=tuple(sorted(files.items())))


@dataclass(frozen=True, slots=True)
class Winner:
    """The effective provider of one relative path."""

    label: str
    relative: str
    path: Path | None
    staged: str | None

    def text(self) -> str:
        if self.staged is not None:
            return self.staged
        assert self.path is not None
        return read_text(self.path)


def _layer_files(
    layer: Layer,
    directory: str,
    *,
    recursive: bool,
    predicate: Callable[[str], bool],
) -> Iterator[Winner]:
    if layer.root is not None:
        base = layer.root / directory
        if not base.is_dir():
            return
        paths = sorted(base.rglob("*.txt") if recursive else base.glob("*.txt"))
        for path in paths:
            relative = path.relative_to(base).as_posix()
            if predicate(relative):
                yield Winner(layer.label, relative, path, None)
        return
    prefix = directory.rstrip("/") + "/"
    for relative, text in layer.files:
        if not relative.startswith(prefix):
            continue
        inner = relative[len(prefix) :]
        if predicate(inner):
            yield Winner(layer.label, inner, None, text)


def file_winners(
    layers: Iterable[Layer],
    directory: str,
    *,
    recursive: bool = False,
    predicate: Callable[[str], bool] = lambda _relative: True,
) -> dict[str, Winner]:
    """Return the effective provider of every file below ``directory``.

    Keys are relative to ``directory``. A later layer replaces an earlier one's
    file outright, which is how CK3 resolves a same-path override.
    """
    winners: dict[str, Winner] = {}
    for layer in layers:
        for winner in _layer_files(
            layer, directory, recursive=recursive, predicate=predicate
        ):
            winners[winner.relative] = winner
    return winners


def key_winners(
    layers: Iterable[Layer],
    directory: str,
    parse: Callable[[str], dict],
    *,
    recursive: bool = True,
    predicate: Callable[[str], bool] = lambda _relative: True,
) -> dict:
    """Merge every file below ``directory`` in load order, last key winning.

    Unlike `file_winners` this reads every layer's file, because a database key
    an earlier module defines survives unless a later one redefines that same
    key in a differently named file.
    """
    result: dict = {}
    for layer in layers:
        for winner in _layer_files(
            layer, directory, recursive=recursive, predicate=predicate
        ):
            result.update(parse(winner.text()))
    return result


_SCALAR_TERRAIN = re.compile(r"^\s*(\d+)\s*=\s*([a-z][a-z0-9_]*)\s*(?:#.*)?$")
_TERRAIN_TYPE = re.compile(r"^([a-z][a-z0-9_]*)\s*=\s*\{")


def parse_scalar_terrain(text: str) -> dict[int, str]:
    """Return the `<province> = <terrain>` assignments one file declares."""
    return {
        int(match.group(1)): match.group(2)
        for line in text.splitlines()
        if (match := _SCALAR_TERRAIN.match(line))
    }


def parse_terrain_type_keys(text: str) -> dict[str, None]:
    """Return the terrain types one file defines, as a key set."""
    return {
        match.group(1): None
        for line in text.splitlines()
        if (match := _TERRAIN_TYPE.match(line))
    }
