"""Record which upstream files a generator actually reads.

The core pins a generator's inputs by content, so it has to know which files a
run consumed.  Declaring them per module is not an option: 111 of the 142
declared sources resolve to a whole Workshop root, and the largest of those is
13G, so neither hand-declaration nor hashing the tree is workable.

The generators do not share a read helper either -- they use ``Path.read_text``,
``Path.read_bytes``, ``Path.open`` and plain ``open``, and Pillow and numpy both
end up in ``builtins.open`` -- so the recorder patches those four call sites for
the duration of one run instead of asking every generator to route reads
somewhere new.  It records paths only; the core hashes them, so that the digests
written into a lock file and the digests checked against it come from one
implementation.
"""

from __future__ import annotations

import builtins
import os
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from pathlib import Path

# Any mode that can write is not an input read. "r+" is included deliberately:
# a file opened for update is being produced, not consumed.
_WRITE_CHARACTERS = "wxa+"


def _is_read_mode(mode: object) -> bool:
    """Return whether an ``open`` mode only ever reads."""
    if mode is None:
        return True
    if not isinstance(mode, str):
        return False
    return not any(character in mode for character in _WRITE_CHARACTERS)


class ReadRecorder:
    """Collect every existing file read from a declared source root."""

    def __init__(self, roots: Iterable[Path | str]) -> None:
        resolved = set()
        for root in roots:
            try:
                resolved.add(Path(root).resolve())
            except OSError:
                continue
        self._roots = tuple(sorted(resolved, key=str))
        self._paths: set[str] = set()

    def paths(self) -> list[str]:
        """Return the recorded absolute paths, in a stable order."""
        return sorted(self._paths)

    def _inside_source(self, resolved: Path) -> bool:
        parents = set(resolved.parents)
        return any(resolved == root or root in parents for root in self._roots)

    def record(self, candidate: object) -> None:
        """Note one read target, ignoring anything that is not a source file."""
        if isinstance(candidate, int):  # already-open file descriptor
            return
        try:
            resolved = Path(os.fspath(candidate)).resolve()
        except (TypeError, ValueError, OSError):
            return
        if not self._inside_source(resolved):
            return
        try:
            if not resolved.is_file():
                return
        except OSError:
            return
        self._paths.add(str(resolved))

    @contextmanager
    def active(self) -> Iterator[ReadRecorder]:
        """Patch the read entry points for the duration of one generator run."""
        if not self._roots:
            yield self
            return

        record = self.record
        original_open = builtins.open
        original_path_open = Path.open
        original_read_text = Path.read_text
        original_read_bytes = Path.read_bytes

        def selected_mode(arguments, keywords):
            """Read the mode without deciding whether it was passed positionally."""
            if "mode" in keywords:
                return keywords["mode"]
            return arguments[0] if arguments else "r"

        def open_wrapper(file, *arguments, **keywords):
            if _is_read_mode(selected_mode(arguments, keywords)):
                record(file)
            return original_open(file, *arguments, **keywords)

        def path_open_wrapper(self, *arguments, **keywords):
            if _is_read_mode(selected_mode(arguments, keywords)):
                record(self)
            return original_path_open(self, *arguments, **keywords)

        def read_text_wrapper(self, *arguments, **keywords):
            record(self)
            return original_read_text(self, *arguments, **keywords)

        def read_bytes_wrapper(self, *arguments, **keywords):
            record(self)
            return original_read_bytes(self, *arguments, **keywords)

        builtins.open = open_wrapper
        Path.open = path_open_wrapper
        Path.read_text = read_text_wrapper
        Path.read_bytes = read_bytes_wrapper
        try:
            yield self
        finally:
            builtins.open = original_open
            Path.open = original_path_open
            Path.read_text = original_read_text
            Path.read_bytes = original_read_bytes
