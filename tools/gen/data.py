"""Small serialization helpers shared by data-oriented generators."""

from __future__ import annotations

import csv
import io
from collections.abc import Iterable, Sequence


def csv_bytes(fieldnames: Sequence[str], rows: Iterable[dict[str, object]]) -> bytes:
    """Render deterministic UTF-8 CSV with Unix line endings."""
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue().encode()
