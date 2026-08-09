"""Small deterministic hashing helpers shared by repository tooling."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Protocol


class Digest(Protocol):
    """The minimal hashlib interface used for streaming file content."""

    def update(self, data: bytes) -> object: ...


def update_digest_from_file(digest: Digest, path: Path) -> None:
    """Feed one file into an existing digest without buffering it all at once."""
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)


def sha256_file(path: Path) -> str:
    """Return the streaming SHA-256 digest for one file."""
    digest = hashlib.sha256()
    update_digest_from_file(digest, path)
    return digest.hexdigest()
