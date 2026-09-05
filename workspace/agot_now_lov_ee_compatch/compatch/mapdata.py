"""The `map_data/definition.csv` row model shared by the map and world stages.

The map stage merges definition rows and must reproduce every field it did not
decide byte-for-byte, so each row keeps the source line it came from. The world
stage reads the same rows as typed province colours and names. One parse serves
both: `raw` for the merge, the typed fields for the classification.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class Definition:
    province_id: int
    red: int
    green: int
    blue: int
    name: str
    # The source line is carried for the merge, not compared: two rows are the
    # same province when their id, colour, and barony match, whatever trailing
    # fields a parent happens to write after them.
    raw: str = field(compare=False)

    @property
    def packed_rgb(self) -> int:
        return (self.red << 16) | (self.green << 8) | self.blue

    @property
    def rgb_text(self) -> str:
        return f"{self.red}:{self.green}:{self.blue}"


def parse_definitions(text: str, *, label: str, expected_rows: int) -> list[Definition]:
    """Parse every definition row, asserting the map's shape has not moved.

    The three assertions are what make an upstream map change fail here instead
    of silently reclassifying provinces: the row count, contiguous ids from zero,
    and colours unique enough to index the province raster by.
    """
    rows: list[Definition] = []
    for line_number, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        fields = line.split(";")
        if len(fields) < 5:
            raise ValueError(f"{label}:{line_number}: malformed definition row")
        try:
            province_id, red, green, blue = map(int, fields[:4])
        except ValueError as error:
            raise ValueError(
                f"{label}:{line_number}: non-numeric definition fields"
            ) from error
        rows.append(Definition(province_id, red, green, blue, fields[4], line))

    if len(rows) != expected_rows:
        raise AssertionError(
            f"{label} definition row count changed: {len(rows)} != {expected_rows}"
        )
    ids = [row.province_id for row in rows]
    if ids != list(range(expected_rows)):
        raise AssertionError(
            f"{label} definition IDs are no longer contiguous 0..{expected_rows - 1}"
        )
    packed = [row.packed_rgb for row in rows]
    if len(packed) != len(set(packed)):
        duplicates = [rgb for rgb, count in Counter(packed).items() if count > 1]
        raise AssertionError(f"duplicate definition RGB values: {duplicates[:10]}")
    return rows


def definition_lines(text: str) -> tuple[list[str], dict[int, str]]:
    """Return every source line, and the numbered rows keyed by province id.

    The map merge works on raw lines because it has to preserve rows it does not
    own, including any the header or a trailing comment occupies.
    """
    lines = text.splitlines()
    rows = {
        int(line.split(";", 1)[0]): line
        for line in lines
        if ";" in line and line.split(";", 1)[0].strip().isdigit()
    }
    return lines, rows


def province_identity(row: str | None) -> str | None:
    """Return the barony a definition row names, ignoring its colour."""
    if row is None:
        return None
    fields = row.split(";")
    return fields[4] if len(fields) > 4 else None


def definition_colours(text: str) -> dict[int, int]:
    """Map each province id to its packed definition colour."""
    colours: dict[int, int] = {}
    for line in text.splitlines():
        fields = line.split(";")
        if len(fields) < 4 or not fields[0].strip().isdigit():
            continue
        province = int(fields[0])
        if province == 0:
            continue
        try:
            red, green, blue = (int(fields[index]) for index in (1, 2, 3))
        except ValueError:
            continue
        colours[province] = (red << 16) | (green << 8) | blue
    return colours
