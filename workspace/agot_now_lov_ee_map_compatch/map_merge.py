#!/usr/bin/env python3
"""Merge NOW's Westeros deltas onto Further East EEP's native AGOT 0.5 map.

Further East v4 already uses AGOT's 8233-9400 province band.  This layer must
therefore never paste AGOT raster data or renumber provinces: it starts from
EEP's canonical map and carries only the small, independently authored NOW
map-object deltas that still apply to Westeros.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import tempfile
from bisect import insort
from dataclasses import dataclass
from pathlib import Path

from gen import GenerationContext
from gen.sources import canonical_source_path
from gen.text import matching_brace, read_source

DEFINITION = "map_data/definition.csv"
DEFAULT_MAP = "map_data/default.map"
PROVINCES_RASTER = "map_data/provinces.png"
LANDED_TITLES = "common/landed_titles"
QUARANTINE_ASSET = "untitled_province_quarantine.json"
GEO_REGIONS = "map_data/geographical_regions/00_agot_geographical_region.txt"
NOW_GEO_REGIONS = (
    "map_data/geographical_regions/replace/00_agot_geographical_region.txt"
)
BUILDING_LOCATORS = "gfx/map/map_object_data/building_locators.txt"
SPECIAL_BUILDING_LOCATORS = "gfx/map/map_object_data/special_building_locators.txt"
LOCATOR_FILES = (BUILDING_LOCATORS, SPECIAL_BUILDING_LOCATORS)
# The remaining locator families, carried verbatim from the Essos compatch that
# is their effective last writer.  This layer adopts them only so the raster
# repair below can reach them; no delta of its own is applied to their records.
ADOPTED_LOCATOR_FILES = (
    "gfx/map/map_object_data/player_stack_locators.txt",
    "gfx/map/map_object_data/combat_locators.txt",
    "gfx/map/map_object_data/siege_locators.txt",
    "gfx/map/map_object_data/activities.txt",
)
AGOT_NATIVE_PROVINCE_BAND = range(8233, 9401)
IDENTITY_ROTATION = "{ -0.000000 -0.000000 -0.000000 1.000000 }"
NEW_MAPOBJECT_3 = "gfx/map/map_object_data/new_mapobject_3.txt"
OBJECT_FILES = (
    "gfx/map/map_object_data/new_mapobject_2.txt",
    NEW_MAPOBJECT_3,
)
# These are the NOW colour remaps required by the accepted Westeros locator
# deltas.  The remaining NOW definition edits either predate AGOT 0.5's
# canonical map or are unrelated to the map objects carried by this compatch.
NOW_DEFINITION_ROWS = frozenset(
    (
        3274,
        3823,
        3967,
        3969,
        4124,
        4125,
        4126,
        4136,
        4138,
        4419,
        4420,
        4422,
        4426,
    )
)
# Records both EEP and NOW edited, where load order cannot decide.  Each entry
# pins all three inputs, so any upstream change re-raises the conflict instead
# of silently reusing a stale review.
LOCATOR_RESOLUTIONS: dict[tuple[str, int], tuple[str, dict[str, str]]] = {
    (SPECIAL_BUILDING_LOCATORS, 3462): (
        # b_cuy.  EEP re-placed the special building and, as it does at every
        # locator it re-places, reset height and scale to the editor defaults.
        # NOW instead deliberately resized the same model from 0.267 to 0.468.
        # Keep EEP's placement and NOW's size; neither source loses its intent.
        "14f9365da82ba20d77959154de3fff59465f20d2bc670baf436e86f99c5b4968",
        {"position": "current", "rotation": "current", "scale": "incoming"},
    ),
}
# Dunstonbury, Ryamsport and Planky Town render the larger castle meshes from
# COW-AGOT (2971198450), which no map source in this merge accounts for.  Their
# locators are pinned to the placement and scale those meshes need.  Each entry
# also states the merged value it overrides, so a later EEP or NOW re-placement
# fails generation rather than being silently discarded.
#
# building_locators 4945 (Planky Town) pins a 0.017 scale, which suppresses the
# default barony building in favour of COW's mesh.  Scales far below 1.0 are
# ordinary in these files, so the value is not self-evidently wrong; it pairs
# with OBJECT_INSTANCE_SUPPRESSIONS below.
LOCATOR_PINS: dict[tuple[str, int], tuple[str, dict[str, str], dict[str, str]]] = {
    (BUILDING_LOCATORS, 3823): (
        "b_dunstonbury",
        {
            "position": "{ 1173.776733 0.000000 2584.794189 }",
            "scale": "{ 1.000000 1.000000 1.000000 }",
        },
        {
            "position": "{ 1175.936401 0.000000 2585.005859 }",
            "scale": "{ 0.199512 0.199512 0.199512 }",
        },
    ),
    (BUILDING_LOCATORS, 4945): (
        "b_plankytown",
        {
            "position": "{ 2055.625977 0.000000 1982.029541 }",
            "rotation": "{ -0.000000 -0.261055 -0.000000 -0.965323 }",
            "scale": "{ 1.000000 1.000000 1.000000 }",
        },
        {
            "position": "{ 2047.949341 0.000000 1975.962158 }",
            "rotation": "{ -0.000000 0.848302 -0.000000 -0.529512 }",
            "scale": "{ 0.017446 0.017446 0.017446 }",
        },
    ),
    (SPECIAL_BUILDING_LOCATORS, 3823): (
        "b_dunstonbury",
        {
            "position": "{ 1183.000000 0.000000 2577.000000 }",
            "rotation": "{ -0.000000 -0.984608 -0.000000 -0.174778 }",
        },
        {
            "position": "{ 1174.838623 0.000000 2583.583008 }",
            "rotation": "{ -0.000000 -0.987678 -0.000000 0.156499 }",
        },
    ),
    (SPECIAL_BUILDING_LOCATORS, 4125): (
        "b_ryamsport",
        {"scale": "{ 0.412966 0.412966 0.412966 }"},
        {"scale": "{ 0.114806 0.114806 0.114806 }"},
    ),
    (SPECIAL_BUILDING_LOCATORS, 4945): (
        "b_plankytown",
        {
            "position": "{ 2058.529053 0.000000 1979.114258 }",
            "rotation": "{ 0.000000 0.903833 -0.000000 0.427885 }",
            "scale": "{ 0.412966 0.412966 0.412966 }",
        },
        {
            "position": "{ 2046.637939 -1.086914 1976.357056 }",
            "rotation": "{ -0.000000 0.375156 -0.000000 0.926962 }",
            "scale": "{ 0.492788 0.492788 0.492788 }",
        },
    ),
}
# NOW places a bridge mesh across the Greenblood at Planky Town.  That barony
# renders COW's own model instead, so the instance is suppressed here to keep a
# bridge from crossing that mesh; it pairs with the 4945 locator scale above.
# `merge_object_block` recomputes `count=` from the surviving rows.
OBJECT_INSTANCE_SUPPRESSIONS: dict[tuple[str, str], tuple[str, tuple[str, ...]]] = {
    (NEW_MAPOBJECT_3, "Bridge_India"): (
        "b_plankytown",
        (
            "2046.174194 0.876465 1976.477051 0.000000 0.279843 "
            "0.000000 0.960045 1.000000 1.000000 1.000000",
        ),
    ),
}
LOCATOR_FIELD = re.compile(
    r"(?m)^[ \t]*(?P<field>[a-z_]+)\s*=\s*(?:\{[^}]*\}|\S+)[ \t]*$"
)


def locator_field_value(block: str, field: str) -> str | None:
    """Read one locator field, in either the multi-line or single-line form."""
    found = re.search(rf"\b{field}\s*=\s*(\{{[^}}]*\}}|\S+)", block)
    return None if found is None else found.group(1)


def set_locator_field(block: str, field: str, value: str, label: str) -> str:
    """Rewrite one locator field, leaving the record's own layout untouched."""
    block, count = re.subn(
        rf"(\b{field}\s*=\s*)(?:\{{[^}}]*\}}|\S+)",
        lambda match: match.group(1) + value,
        block,
        count=1,
    )
    if count != 1:
        raise RuntimeError(f"{label}: no {field} field to write")
    return block


def apply_locator_pins(
    order: list[int], merged: dict[int, str], relative: str
) -> tuple[list[int], dict[int, str]]:
    """Override merged locator records field by field with their pinned values."""
    pins = {
        key: value for (path, key), value in LOCATOR_PINS.items() if path == relative
    }
    if not pins:
        return order, merged
    result = dict(merged)
    for key, (title, baseline, pinned) in pins.items():
        label = f"locator pin {relative} {key} ({title})"
        block = result.get(key)
        if block is None:
            raise RuntimeError(f"{label}: the record it pins no longer exists")
        for field, expected in baseline.items():
            actual = locator_field_value(block, field)
            if actual != expected:
                raise RuntimeError(
                    f"{label}: {field} changed upstream to {actual}, "
                    f"pinned baseline is {expected}; re-review the pin"
                )
        for field, value in pinned.items():
            block = set_locator_field(block, field, value, label)
        result[key] = block
    return order, result


@dataclass(frozen=True, slots=True)
class ProvinceGeometry:
    """Where each province actually sits on the effective province raster.

    Further East supplies `provinces.png` while this layer supplies
    `definition.csv`, so the two must be read as a pair.  That pairing is exact
    rather than approximate: the thirteen NOW colour edits are a closed
    permutation within a set of neighbouring ids, so every colour this layer
    names is present in Further East's raster and refers to the pixels NOW
    intended.
    """

    land: frozenset[int]
    anchor: dict[int, tuple[float, float]]
    id_raster: object
    width: int
    height: int
    unpainted: tuple[int, ...]

    def holds(self, province: int, x: float, z: float) -> bool:
        """Report whether a world position falls inside its own province."""
        column, row = int(x), int(self.height - z)
        if not (0 <= column < self.width and 0 <= row < self.height):
            return False
        return int(self.id_raster[row, column]) == province


def land_provinces(text: str, defined: frozenset[int]) -> frozenset[int]:
    """Province ids `default.map` does not classify as water or impassable.

    Comments are stripped first: the effective `default.map` carries a
    commented-out `max_provinces`, which a naive scan would read as a real cap
    and silently discard every province above it.
    """
    stripped = "\n".join(line.split("#")[0] for line in text.splitlines())
    excluded: set[int] = set()
    for key in (
        "sea_zones",
        "river_provinces",
        "lakes",
        "impassable_seas",
        "impassable_mountains",
    ):
        for found in re.finditer(
            rf"\b{key}\s*=\s*(RANGE|LIST)\s*\{{([^}}]*)\}}", stripped
        ):
            numbers = [int(value) for value in found.group(2).split()]
            if found.group(1) == "RANGE" and len(numbers) == 2:
                excluded.update(range(numbers[0], numbers[1] + 1))
            else:
                excluded.update(numbers)
    return defined - excluded


def province_ids_from_landed_titles(text: str) -> tuple[int, ...]:
    """Return province assignments from one landed-title file.

    Assignments occur both on their own line and inside compact one-line barony
    blocks. Comments are removed first so retired definitions do not make land
    appear titled.
    """
    stripped = "\n".join(line.split("#", 1)[0] for line in text.splitlines())
    return tuple(
        int(match.group(1))
        for match in re.finditer(r"\bprovince\s*=\s*(\d+)\b", stripped)
    )


def effective_landed_title_files(inputs: Inputs) -> dict[str, Path]:
    """Resolve the effective landed-title file set by relative path."""
    winners: dict[str, Path] = {}
    for root in (
        inputs.agot,
        inputs.now,
        inputs.lov,
        inputs.lov_bridge,
        inputs.ee,
        inputs.eep,
        inputs.eec,
    ):
        directory = root / LANDED_TITLES
        if not directory.is_dir():
            continue
        for path in sorted(directory.rglob("*.txt")):
            winners[path.relative_to(directory).as_posix()] = path
    return winners


def effective_titled_provinces(
    title_files: dict[str, Path],
) -> tuple[frozenset[int], dict[int, str]]:
    """Return unique province assignments and their effective source files."""
    providers: dict[int, str] = {}
    for relative, path in sorted(title_files.items()):
        for province in province_ids_from_landed_titles(read(path)):
            if previous := providers.get(province):
                raise RuntimeError(
                    f"province {province} is assigned by both {previous} and {relative}"
                )
            providers[province] = relative
    return frozenset(providers), providers


def append_impassable_quarantine(
    default_map: str, provinces: tuple[int, ...], *, chunk_size: int = 80
) -> str:
    """Append a deterministic reviewed impassable-province section."""
    if not provinces:
        raise RuntimeError("untitled province quarantine unexpectedly became empty")
    lines = [
        "",
        "# LOCAL_UNTITLED_PROVINCE_QUARANTINE_START",
        "# Defined but unpainted provinces without effective landed titles.",
    ]
    for offset in range(0, len(provinces), chunk_size):
        values = " ".join(
            str(value) for value in provinces[offset : offset + chunk_size]
        )
        lines.append(f"impassable_mountains = LIST {{ {values} }}")
    lines.append("# LOCAL_UNTITLED_PROVINCE_QUARANTINE_END")
    return default_map.rstrip() + "\n" + "\n".join(lines) + "\n"


def quarantined_default_map(
    inputs: Inputs, definition: str, geometry: ProvinceGeometry
) -> tuple[str, dict[str, object]]:
    """Make every reviewed, titleless definition non-passable."""
    default_map = read(inputs.current_map_source(DEFAULT_MAP))
    defined = frozenset(definition_colours(definition))
    title_files = effective_landed_title_files(inputs)
    titled, providers = effective_titled_provinces(title_files)
    candidates = tuple(sorted(land_provinces(default_map, defined) - titled))

    reviewed = json.loads(
        (inputs.context.assets_dir / QUARANTINE_ASSET).read_text(encoding="utf-8")
    )
    if reviewed.get("schema_version") != 1:
        raise RuntimeError("unsupported untitled-province quarantine schema")
    expected = tuple(reviewed.get("province_ids", ()))
    if candidates != expected:
        added = sorted(set(candidates) - set(expected))
        removed = sorted(set(expected) - set(candidates))
        raise RuntimeError(
            "untitled province quarantine drifted; review the map/title inputs "
            f"(added={added[:20]}, removed={removed[:20]})"
        )

    painted = sorted(set(candidates) - set(geometry.unpainted))
    if painted:
        raise RuntimeError(
            "reviewed untitled provinces became painted; do not quarantine visible "
            f"land without a separate map review: {painted[:20]}"
        )

    output = append_impassable_quarantine(default_map, candidates)
    remaining = sorted(land_provinces(output, defined) - titled)
    if remaining:
        raise RuntimeError(
            f"generated default.map leaves passable untitled provinces: {remaining[:20]}"
        )
    return output, {
        "effective_title_files": {
            relative: canonical_source_path(
                path,
                root=inputs.context.workspace_root,
                workshop_root=inputs.workshop_root,
            )
            for relative, path in sorted(title_files.items())
        },
        "title_assignments": len(providers),
        "quarantined_count": len(candidates),
        "quarantined_painted": 0,
        "quarantined_unpainted": len(candidates),
        "quarantined_provinces": list(candidates),
        "remaining_passable_untitled": 0,
    }


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


def province_geometry(inputs: Inputs, definition_text: str) -> ProvinceGeometry:
    """Locate every province on the raster, as the map editor itself would.

    A province's anchor is its centroid where that lands inside the province,
    and otherwise the painted pixel nearest the centroid.  The fallback matters
    for concave and split provinces, where the centre of mass falls in a
    neighbour or in the sea.
    """
    import numpy as np
    from PIL import Image

    colours = definition_colours(definition_text)
    with Image.open(inputs.current_map_source(PROVINCES_RASTER)) as image:
        if image.mode != "RGB":
            raise RuntimeError(f"provinces.png is {image.mode}, expected RGB")
        width, height = image.size
        rgb = np.asarray(image, dtype=np.uint8)

    packed = (
        (rgb[:, :, 0].astype(np.uint32) << 16)
        | (rgb[:, :, 1].astype(np.uint32) << 8)
        | rgb[:, :, 2].astype(np.uint32)
    )
    del rgb
    lookup = np.full(1 << 24, -1, dtype=np.int32)
    for province, colour in colours.items():
        lookup[colour] = province
    id_raster = lookup[packed]
    del packed, lookup

    size = max(colours) + 1
    flat = id_raster.ravel()
    painted = flat >= 0
    count = np.bincount(flat[painted], minlength=size).astype(np.int64)
    columns = np.arange(width, dtype=np.float64)
    sum_x = np.zeros(size, dtype=np.float64)
    sum_y = np.zeros(size, dtype=np.float64)
    for top in range(0, height, 256):
        chunk = id_raster[top : top + 256]
        rows = chunk.shape[0]
        inside = chunk.ravel() >= 0
        ids = chunk.ravel()[inside]
        sum_x += np.bincount(
            ids, weights=np.tile(columns, rows)[inside], minlength=size
        )
        sum_y += np.bincount(
            ids,
            weights=np.repeat(np.arange(top, top + rows, dtype=np.float64), width)[
                inside
            ],
            minlength=size,
        )

    anchor: dict[int, tuple[float, float]] = {}
    stray: list[int] = []
    for province in colours:
        if province >= size or count[province] == 0:
            continue
        column = sum_x[province] / count[province]
        row = sum_y[province] / count[province]
        # Accept the centroid using the same truncation the game applies when it
        # samples the raster, so a position this pass accepts is a position that
        # reads back as the same province.
        if int(id_raster[int(row), int(column)]) == province:
            anchor[province] = (column, height - row)
        else:
            stray.append(province)

    if stray:
        wanted = np.zeros(size, dtype=bool)
        wanted[stray] = True
        candidates = np.flatnonzero(painted & wanted[np.maximum(flat, 0)])
        grouped = candidates[np.argsort(flat[candidates], kind="stable")]
        keys = flat[grouped]
        for province in stray:
            first = int(np.searchsorted(keys, province, "left"))
            last = int(np.searchsorted(keys, province, "right"))
            pixels = grouped[first:last]
            rows, columns_of = np.divmod(pixels, width)
            centre_x = sum_x[province] / count[province]
            centre_y = sum_y[province] / count[province]
            nearest = int(
                np.argmin((columns_of - centre_x) ** 2 + (rows - centre_y) ** 2)
            )
            anchor[province] = (
                float(columns_of[nearest]) + 0.5,
                height - (float(rows[nearest]) + 0.5),
            )

    defined = frozenset(colours)
    return ProvinceGeometry(
        land=land_provinces(read(inputs.current_map_source(DEFAULT_MAP)), defined),
        anchor=anchor,
        id_raster=id_raster,
        width=width,
        height=height,
        unpainted=tuple(sorted(defined - set(anchor))),
    )


@dataclass(frozen=True, slots=True)
class Inputs:
    context: GenerationContext
    workshop_root: Path
    agot: Path
    now: Path
    lov: Path
    lov_bridge: Path
    ee: Path
    eep: Path
    eec: Path

    @classmethod
    def from_context(cls, context: GenerationContext) -> Inputs:
        names = (
            "agot",
            "now",
            "legacy-of-valyria",
            "legacy-of-valyria-bridge",
            "essos-expanded",
            "essos-bridge",
            "essos-compatch",
        )
        return cls(
            context=context,
            workshop_root=context.workshop_root(*names),
            agot=context.source("agot"),
            now=context.source("now"),
            lov=context.source("legacy-of-valyria"),
            lov_bridge=context.source("legacy-of-valyria-bridge"),
            ee=context.source("essos-expanded"),
            eep=context.source("essos-bridge"),
            eec=context.source("essos-compatch"),
        )

    def current_map_source(self, relative: str) -> Path:
        """Return EEP's file, falling back to its pre-v4 Essos parent."""
        for root in (self.eep, self.ee):
            candidate = root / relative
            if candidate.is_file():
                return candidate
        raise FileNotFoundError(f"Further East supplies no {relative}")

    def write(self, relative: str, text: str, *, encoding: str = "utf-8-sig") -> None:
        self.context.output_path(relative).write_text(
            text, encoding=encoding, newline="\n"
        )


def read(path: Path) -> str:
    return read_source(path, normalize_newlines=True)


def split_blocks(
    text: str, pattern: re.Pattern[str]
) -> tuple[str, str, list[str], dict[str, str]]:
    """Split a regular top-level Clausewitz file into keyed complete blocks."""
    matches = list(pattern.finditer(text))
    if not matches:
        raise RuntimeError("expected at least one top-level Clausewitz block")
    prefix = text[: matches[0].start()]
    blocks: dict[str, str] = {}
    order: list[str] = []
    cursor = matches[0].start()
    for match in matches:
        key = match.group("key")
        if key in blocks:
            raise RuntimeError(f"duplicate block {key}")
        opening = text.index("{", match.start())
        end = matching_brace(text, opening) + 1
        # Trailing comments and whitespace are dropped rather than attached to
        # either neighbour: they are ambiguous for generated data, and the EEP
        # prefix/suffix already carry the file headers that matter.
        blocks[key] = text[match.start() : end]
        order.append(key)
        cursor = max(cursor, end)
    suffix = text[cursor:] if cursor < len(text) else ""
    return prefix, suffix, order, blocks


REGION_BLOCK = re.compile(r"(?m)^(?P<key>[A-Za-z0-9_]+)\s*=\s*\{")
OBJECT_BLOCK = re.compile(
    r"(?m)^(?P<key>object)\s*=\s*\{\s*\n\tname=\"(?P<name>[^\"]+)\"", re.MULTILINE
)


def split_objects(text: str) -> tuple[str, str, list[str], dict[str, str]]:
    """Split object files by their stable `name` field, not duplicate `object`."""
    starts = list(re.finditer(r"(?m)^object\s*=\s*\{", text))
    if not starts:
        raise RuntimeError("map-object file has no object blocks")
    prefix = text[: starts[0].start()]
    blocks: dict[str, str] = {}
    order: list[str] = []
    last_end = starts[0].start()
    for start in starts:
        opening = text.index("{", start.start())
        end = matching_brace(text, opening) + 1
        block = text[start.start() : end]
        name = re.search(r'(?m)^\tname\s*=\s*"([^\"]+)"', block)
        if not name:
            raise RuntimeError(f"map object without a name: {block[:80]!r}")
        key = name.group(1)
        if key in blocks:
            raise RuntimeError(f"duplicate map object {key}")
        blocks[key] = block
        order.append(key)
        last_end = end
    return prefix, text[last_end:], order, blocks


def merge_file_blocks(
    current: tuple[str, str, list[str], dict[str, str]],
    overlays: tuple[Overlay, ...],
    resolutions: dict[object, tuple[str, dict[str, str]]] | None = None,
    conflict=None,
    pins=None,
    separator: str = "\n\n",
) -> str:
    """Apply keyed source deltas onto the EEP baseline.

    Every overlay carries the baseline it was authored against, so a source
    derived from another is diffed against its own parent rather than against
    AGOT, where the shared ancestry would read as conflict.
    """
    prefix, suffix, order, merged = current
    merged = dict(merged)
    order = list(order)
    resolutions = resolutions or {}
    conflict = conflict or three_way_block
    for overlay in overlays:
        base_blocks = overlay.base
        for key in overlay.order:
            incoming = overlay.blocks[key]
            original = base_blocks.get(key)
            existing = merged.get(key)
            if semantic_script(incoming) in (
                semantic_script(original),
                semantic_script(existing),
            ):
                continue
            if existing is None:
                if original is not None:
                    raise RuntimeError(f"{overlay.label}: {key} disappeared from EEP")
                merged[key] = incoming
                order.append(key)
                continue
            if original is None or semantic_script(existing) == semantic_script(
                original
            ):
                merged[key] = incoming
                continue
            reviewed = resolutions.get(key)
            if reviewed is not None:
                merged[key] = apply_resolution(
                    original, existing, incoming, reviewed, f"{overlay.label} {key}"
                )
                continue
            merged[key] = conflict(
                original, existing, incoming, f"{overlay.label} {key}"
            )
    if pins is not None:
        order, merged = pins(order, merged)
    return (
        prefix
        + separator.join(merged[key] for key in order)
        + suffix.rstrip("\n")
        + "\n"
    )


@dataclass(frozen=True, slots=True)
class Overlay:
    label: str
    base: dict[str, str]
    order: list[str]
    blocks: dict[str, str]

    @classmethod
    def build(
        cls,
        label: str,
        base: tuple[str, str, list[str], dict[str, str]],
        parsed: tuple[str, str, list[str], dict[str, str]],
    ) -> Overlay:
        return cls(label=label, base=base[3], order=parsed[2], blocks=parsed[3])


def apply_resolution(
    original: str,
    current: str,
    incoming: str,
    reviewed: tuple[str, dict[str, str]],
    label: str,
) -> str:
    """Rebuild a reviewed conflicting record field by field."""
    digest, choice = reviewed
    sources = {"base": original, "current": current, "incoming": incoming}
    pinned = hashlib.sha256(
        "|".join(
            semantic_script(sources[name]) or ""
            for name in ("base", "current", "incoming")
        ).encode()
    ).hexdigest()
    if pinned != digest:
        raise RuntimeError(f"{label}: reviewed conflict changed upstream, re-review it")
    lines = []
    for line in current.split("\n"):
        match = LOCATOR_FIELD.match(line)
        field = match.group("field") if match else None
        if field in choice:
            replacement = field_line(sources[choice[field]], field, label)
            lines.append(replacement)
            continue
        lines.append(line)
    return "\n".join(lines)


def field_line(record: str, field: str, label: str) -> str:
    for match in LOCATOR_FIELD.finditer(record):
        if match.group("field") == field:
            return match.group(0)
    raise RuntimeError(f"{label}: resolved field {field} is missing from its source")


def semantic_script(text: str | None) -> str | None:
    """Compare Clausewitz blocks while ignoring comment-only source rewrites."""
    if text is None:
        return None
    uncommented = re.sub(r"(?m)#.*$", "", text)
    return re.sub(r"\s+", "", uncommented)


OBJECT_COUNT = re.compile(r"(?m)^\tcount=(\d+)$")
TRANSFORM_OPEN = '\ttransform="'


def object_transforms(block: str, label: str) -> tuple[str, list[str], str]:
    """Split a map object into its header, instance rows, and closing tail."""
    count = OBJECT_COUNT.search(block)
    opening = block.find(TRANSFORM_OPEN)
    if count is None or opening < 0:
        raise RuntimeError(f"{label}: map object has no count/transform pair")
    if block[count.end() : opening] != "\n":
        raise RuntimeError(f"{label}: map object count no longer precedes transform")
    body = opening + len(TRANSFORM_OPEN)
    end = block.index('"', body)
    rows = [row for row in block[body:end].split("\n") if row.strip()]
    if len(rows) != int(count.group(1)) or len(set(rows)) != len(rows):
        raise RuntimeError(f"{label}: map object count and instance rows disagree")
    return block[: count.start()], rows, block[end:]


def merge_object_block(base: str, current: str, incoming: str, label: str) -> str:
    """Merge instance lists as sets rather than as text.

    Adding or removing a single road segment rewrites both the `count=` line and
    the instance list, so any two sources touching the same mesh always collide
    textually.  The rows are unique, order-independent placements, so replaying
    each side's additions and removals is exact where a text merge is not.
    """
    base_header, base_rows, _ = object_transforms(base, f"{label} (AGOT)")
    header, current_rows, tail = object_transforms(current, f"{label} (EEP)")
    incoming_header, incoming_rows, _ = object_transforms(
        incoming, f"{label} (overlay)"
    )
    if incoming_header not in (base_header, header):
        raise RuntimeError(f"{label}: map object header changed on both sides")

    original = set(base_rows)
    dropped = (original - set(current_rows)) | (original - set(incoming_rows))
    merged = [row for row in base_rows if row not in dropped]
    merged += [row for row in current_rows if row not in original]
    merged += [
        row
        for row in incoming_rows
        if row not in original and row not in set(current_rows)
    ]
    return f"{header}\tcount={len(merged)}\n{TRANSFORM_OPEN}" + "\n".join(merged) + tail


def three_way_block(base: str, current: str, incoming: str, label: str) -> str:
    """Merge the rare shared edit instead of deciding by load order."""
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        for name, content in (
            ("base", base),
            ("current", current),
            ("incoming", incoming),
        ):
            (root / name).write_text(content + "\n", encoding="utf-8")
        result = subprocess.run(
            [
                "git",
                "merge-file",
                "-p",
                str(root / "current"),
                str(root / "base"),
                str(root / "incoming"),
            ],
            check=False,
            capture_output=True,
            text=True,
        )
    if result.returncode != 0 or "<<<<<<<" in result.stdout:
        raise RuntimeError(f"{label}: overlapping EEP/NOW change needs review")
    return result.stdout.rstrip("\n")


def locator_records(text: str) -> tuple[str, str, list[int], dict[int, str]]:
    """Parse locator records by numeric id while preserving EEP's file frame."""
    starts = list(
        re.finditer(
            r"(?m)^[ \t]*\{(?:[ \t]+id[ \t]*=[ \t]*\d+|[ \t]*$)",
            text,
        )
    )
    records: dict[int, str] = {}
    order: list[int] = []
    first: int | None = None
    last: int | None = None
    for start in starts:
        opening = text.index("{", start.start())
        end = matching_brace(text, opening) + 1
        block = text[start.start() : end]
        found = re.search(r"\bid\s*=\s*(\d+)", block)
        if not found:
            continue
        key = int(found.group(1))
        if key in records:
            raise RuntimeError(f"duplicate locator id {key}")
        records[key] = block
        order.append(key)
        first = start.start() if first is None else first
        last = end
    if first is None or last is None:
        raise RuntimeError("locator file has no id records")
    return text[:first], text[last:], order, records


def record_separator(text: str, order: list[int], records: dict[int, str]) -> str:
    """Reproduce the spacing a locator file uses between its own records."""
    if len(order) < 2:
        return "\n\n"
    first = text.index(records[order[0]])
    second = text.index(records[order[1]], first + len(records[order[0]]))
    return text[first + len(records[order[0]]) : second]


def modal_scale(records: dict[int, str]) -> str:
    """The scale a file gives to ordinary records, used for the ones we add."""
    seen: dict[str, int] = {}
    for block in records.values():
        value = locator_field_value(block, "scale")
        if value is not None:
            seen[value] = seen.get(value, 0) + 1
    if not seen:
        raise RuntimeError("locator file has no scale field to copy")
    return max(seen, key=lambda value: seen[value])


def new_locator(
    template: str, province: int, position: str, scale: str, label: str
) -> str:
    """Build a missing record from a sibling, so the file's layout carries over."""
    block = re.sub(
        r"(\bid\s*=\s*)\d+",
        lambda match: match.group(1) + str(province),
        template,
        count=1,
    )
    for field, value in (
        ("position", position),
        ("rotation", IDENTITY_ROTATION),
        ("scale", scale),
    ):
        block = set_locator_field(block, field, value, f"{label} {province}")
    return block


def repair_locators(
    order: list[int],
    records: dict[int, str],
    relative: str,
    geometry: ProvinceGeometry,
    audit: dict[str, object],
) -> tuple[list[int], dict[int, str]]:
    """Place every land province's locator inside its own province.

    Records are rewritten only where the shipped position falls outside the
    province the record belongs to, and added only where a land province has no
    record at all.  Rotation and scale are always preserved, so an upstream
    author's deliberate orientation or sizing survives a position repair.

    Positions pinned in `LOCATOR_PINS` are exempt: those sit slightly outside
    their province on purpose, to suit a mesh this merge does not otherwise
    model, and re-centring them would undo the pin.
    """
    exempt = {key for path, key in LOCATOR_PINS if path == relative}
    order = list(order)
    records = dict(records)
    template = records[order[0]]
    scale = modal_scale(records)
    label = f"locator repair {relative}"

    moved: list[int] = []
    added: list[int] = []
    stranded: list[int] = []
    for province in sorted(geometry.land):
        if province in exempt:
            continue
        anchor = geometry.anchor.get(province)
        block = records.get(province)
        if anchor is None:
            # The province is named by definition.csv but painted nowhere on the
            # effective raster, so no position exists to give it.
            if block is None:
                stranded.append(province)
            continue
        if block is not None and geometry.holds(
            province, *position_of(block, f"{label} {province}")
        ):
            continue
        column, row = anchor
        placed = f"{{ {column:.6f} 0.000000 {row:.6f} }}"
        if block is None:
            block = new_locator(template, province, placed, scale, label)
            insort(order, province)
            added.append(province)
        else:
            block = set_locator_field(block, "position", placed, f"{label} {province}")
            moved.append(province)
        records[province] = block

    audit[relative] = {
        "moved": len(moved),
        "added": len(added),
        "unplaceable": len(stranded),
    }
    return order, records


def position_of(block: str, label: str) -> tuple[float, float]:
    """Read a locator's world X and Z, ignoring its height."""
    value = locator_field_value(block, "position")
    if value is None:
        raise RuntimeError(f"{label}: record has no position")
    numbers = value.strip("{} ").split()
    if len(numbers) != 3:
        raise RuntimeError(f"{label}: position is not a 3-vector")
    return float(numbers[0]), float(numbers[2])


def adopt_locator_file(
    inputs: Inputs,
    relative: str,
    geometry: ProvinceGeometry,
    audit: dict[str, object],
) -> str:
    """Carry an Essos-compatch locator family through, repaired but undiffed."""
    text = read(inputs.eec / relative)
    prefix, suffix, order, records = locator_records(text)
    separator = record_separator(text, order, records)
    order, records = repair_locators(order, records, relative, geometry, audit)
    return (
        prefix
        + separator.join(records[key] for key in order)
        + suffix.rstrip("\n")
        + "\n"
    )


def replace_locator_band(
    current: tuple[str, str, list[int], dict[int, str]],
    canonical: tuple[str, str, list[int], dict[int, str]],
    band: range,
) -> tuple[str, str, list[int], dict[int, str]]:
    """Replace one province-id band while preserving the current file frame."""
    prefix, suffix, order, records = current
    _, _, canonical_order, canonical_records = canonical
    band_keys = set(band)
    replacement_order = [key for key in canonical_order if key in band_keys]
    merged_order: list[int] = []
    inserted = False
    for key in order:
        if key in band_keys:
            if not inserted:
                merged_order.extend(replacement_order)
                inserted = True
            continue
        merged_order.append(key)
    if not inserted:
        merged_order.extend(replacement_order)

    merged_records = {
        key: record for key, record in records.items() if key not in band_keys
    }
    merged_records.update((key, canonical_records[key]) for key in replacement_order)
    return prefix, suffix, merged_order, merged_records


def stacked_overlays(inputs: Inputs, relative: str, parse) -> tuple[Overlay, ...]:
    """NOW diffs against AGOT."""
    agot = parse(read(inputs.agot / relative))
    now = parse(read(inputs.now / relative))
    return (Overlay.build(f"NOW {relative}", agot, now),)


def merge_locator_file(
    inputs: Inputs,
    relative: str,
    geometry: ProvinceGeometry,
    audit: dict[str, object],
) -> str:
    text = read(inputs.current_map_source(relative))
    current = locator_records(text)
    # Read the spacing before any band replacement, while every record still
    # comes from this file.
    separator = record_separator(text, current[2], current[3])
    if relative == BUILDING_LOCATORS:
        # Further East v4 restores AGOT's 8233-9400 province identities but
        # omits this locator file.  Its Essos Expanded parent still uses those
        # ids for Anogaria, so only the rest of that parent file is reusable.
        current = replace_locator_band(
            current,
            locator_records(read(inputs.agot / relative)),
            AGOT_NATIVE_PROVINCE_BAND,
        )
    resolutions = {
        key: value
        for (path, key), value in LOCATOR_RESOLUTIONS.items()
        if path == relative
    }

    def finalize(
        order: list[int], merged: dict[int, str]
    ) -> tuple[list[int], dict[int, str]]:
        order, merged = repair_locators(order, merged, relative, geometry, audit)
        return apply_locator_pins(order, merged, relative)

    return merge_file_blocks(
        current,
        stacked_overlays(inputs, relative, locator_records),
        resolutions,
        pins=finalize,
        separator=separator,
    )


def apply_object_suppressions(
    order: list[str], merged: dict[str, str], relative: str
) -> tuple[list[str], dict[str, str]]:
    """Drop the map-object instances this compatch suppresses."""
    pins = {
        key: value
        for (path, key), value in OBJECT_INSTANCE_SUPPRESSIONS.items()
        if path == relative
    }
    if not pins:
        return order, merged
    result = dict(merged)
    for key, (title, suppressed) in pins.items():
        label = f"object suppression {relative} {key} ({title})"
        block = result.get(key)
        if block is None:
            raise RuntimeError(f"{label}: the map object it pins no longer exists")
        header, rows, tail = object_transforms(block, label)
        absent = [row for row in suppressed if row not in rows]
        if absent:
            raise RuntimeError(
                f"{label}: upstream no longer places {len(absent)} suppressed "
                "row(s), so this entry is stale; re-review it"
            )
        rows = [row for row in rows if row not in set(suppressed)]
        # Reproduce the sources' own layout, which terminates the last instance
        # row before the closing quote.  `object_transforms` drops that newline
        # along with the blank entries it splits away.
        result[key] = (
            f"{header}\tcount={len(rows)}\n{TRANSFORM_OPEN}"
            + "".join(f"{row}\n" for row in rows)
            + tail
        )
    return order, result


def merge_object_file(inputs: Inputs, relative: str) -> str:
    current = split_objects(read(inputs.current_map_source(relative)))
    return merge_file_blocks(
        current,
        stacked_overlays(inputs, relative, split_objects),
        conflict=merge_object_block,
        pins=lambda order, merged: apply_object_suppressions(order, merged, relative),
    )


def definition_rows(path: Path) -> tuple[list[str], dict[int, str]]:
    lines = read(path).splitlines()
    rows = {
        int(line.split(";", 1)[0]): line
        for line in lines
        if ";" in line and line.split(";", 1)[0].strip().isdigit()
    }
    return lines, rows


def locator_definition_dependencies(
    agot_definition: dict[int, str],
    now_definition: dict[int, str],
    agot_locators: dict[int, str],
    now_locators: dict[int, str],
) -> set[int]:
    """Return moved locator ids whose NOW province colour must follow them."""
    dependencies = set()
    for key in agot_locators.keys() & now_locators.keys():
        if key not in agot_definition or key not in now_definition:
            continue
        if semantic_script(agot_locators[key]) == semantic_script(now_locators[key]):
            continue
        agot_colour = agot_definition[key].split(";", 4)[1:4]
        now_colour = now_definition[key].split(";", 4)[1:4]
        if agot_colour != now_colour:
            dependencies.add(key)
    return dependencies


def merge_definition(inputs: Inputs) -> str:
    lines, agot = definition_rows(inputs.agot / DEFINITION)
    _, now = definition_rows(inputs.now / DEFINITION)
    eep_lines, eep = definition_rows(inputs.eep / DEFINITION)
    if len(eep) != 27589 or max(eep) != 27588:
        raise RuntimeError(
            "Further East definition.csv is no longer the native 27,589-row map"
        )
    changed = NOW_DEFINITION_ROWS
    invalid = [
        key
        for key in changed
        if key not in agot
        or key not in now
        or eep.get(key) != agot[key]
        or now[key] == agot[key]
    ]
    if invalid:
        raise RuntimeError(
            "NOW's audited definition rows changed or are no longer EEP-safe: "
            f"{invalid}"
        )
    required = set()
    for relative in LOCATOR_FILES:
        _, _, _, agot_locators = locator_records(read(inputs.agot / relative))
        _, _, _, now_locators = locator_records(read(inputs.now / relative))
        required.update(
            locator_definition_dependencies(agot, now, agot_locators, now_locators)
        )
    missing = sorted(required - changed)
    if missing:
        raise RuntimeError(
            f"NOW locator deltas require unaudited definition colour rows: {missing}"
        )
    output = [
        now[int(line.split(";", 1)[0])]
        if ";" in line
        and line.split(";", 1)[0].strip().isdigit()
        and int(line.split(";", 1)[0]) in changed
        else line
        for line in eep_lines
    ]
    return "\n".join(output) + "\n"


def merge_geographical_regions(inputs: Inputs) -> str:
    base = split_blocks(read(inputs.agot / GEO_REGIONS), REGION_BLOCK)
    current = split_blocks(read(inputs.eep / GEO_REGIONS), REGION_BLOCK)
    now = split_blocks(read(inputs.now / NOW_GEO_REGIONS), REGION_BLOCK)
    overlay = Overlay.build("NOW geographical regions", base, now)
    return merge_file_blocks(current, (overlay,))


# The one-line statement of what this merge is for.  The upstream inputs behind
# it are pinned by sources.lock.json.
INTENT = (
    "EEP-native map; apply NOW semantic Westeros deltas, quarantine reviewed "
    "unpainted definitions without effective titles, then place every land "
    "province's locator inside its own province"
)


def parent_versions(inputs: Inputs) -> dict[str, str]:
    """Read each parent's declared version, for the generation report.

    Reading every descriptor.mod also keeps them in sources.lock.json, which
    makes a parent bump visible to `ck3mm upstream` even when this module's
    own output does not move.
    """
    modules = {
        "AGOT": inputs.agot,
        "NOW": inputs.now,
        "LoV": inputs.lov,
        "LoV AGOT bridge": inputs.lov_bridge,
        "EEP": inputs.eep,
        "EEC": inputs.eec,
    }
    return {
        label: re.search(
            r'(?m)^version="([^\"]+)"', read(root / "descriptor.mod")
        ).group(1)
        for label, root in modules.items()
    }


def generate(context: GenerationContext) -> None:
    inputs = Inputs.from_context(context)
    versions = parent_versions(inputs)
    print("Parents: " + ", ".join(f"{k} {v}" for k, v in versions.items()))

    definition = merge_definition(inputs)
    inputs.write(DEFINITION, definition, encoding="utf-8")
    inputs.write(GEO_REGIONS, merge_geographical_regions(inputs))

    geometry = province_geometry(inputs, definition)
    default_map, title_audit = quarantined_default_map(inputs, definition, geometry)
    inputs.write(DEFAULT_MAP, default_map)
    audit: dict[str, object] = {}
    for relative in LOCATOR_FILES:
        inputs.write(relative, merge_locator_file(inputs, relative, geometry, audit))
    for relative in ADOPTED_LOCATOR_FILES:
        inputs.write(relative, adopt_locator_file(inputs, relative, geometry, audit))
    for relative in OBJECT_FILES:
        inputs.write(relative, merge_object_file(inputs, relative))

    inputs.context.artifact_path("map_data/merge_audit.json").write_text(
        json.dumps(
            {
                "definition_rows": sorted(NOW_DEFINITION_ROWS),
                "baseline": "Further East EEP v4 native map",
                "raster_outputs": "none",
                "land_provinces": len(geometry.land),
                "provinces_unpainted": len(geometry.unpainted),
                "title_quarantine": title_audit,
                "locator_repair": audit,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
