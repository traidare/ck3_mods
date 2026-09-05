#!/usr/bin/env python3
"""Generate terrain and graphical-region data for AGOT/NOW/LoV/EE."""

from __future__ import annotations

import csv
import fnmatch
import hashlib
import json
import re
import tomllib
from collections import Counter, defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image

from gen import GenerationContext
from gen.data import csv_bytes
from gen.hashing import sha256_file
from gen.script import read_text
from gen.sources import canonical_source_path

TARGET_FIRST = 10946
TARGET_LAST = 26420
TARGET_COUNT = TARGET_LAST - TARGET_FIRST + 1
# Target provinces Further East gives a landed title. Its v4 restructuring moved
# a further 3,423 of them out of `01_landed_titles.txt` into its own files.
EXPECTED_TITLE_COUNT = 12052
# This module fills gaps; it never same-path overrides an upstream terrain file.
# Further East now authors terrain across most of the east, so the output below
# carries only the provinces no effective module assigns a real terrain to. Every
# other id is upstream's decision and is left alone.
TERRAIN_OUTPUT = "common/province_terrain/zzzz_agot_now_lov_ee_world_data.txt"
EXPECTED_GAP_COUNT = 1435
DEFINITION_ROWS = 27589
# Target rows Further East has promoted from generated filler to named baronies.
EXPECTED_NAMED_TARGETS = 1168
# Empire-tier scopes covering the target range.
EXPECTED_EMPIRE_KEYS = 24
EXPECTED_MASK_COUNT = 188
EXPECTED_SIZE = (9216, 6144)
REFERENCE_ANALYSIS_SIZE = (2304, 1536)
REFERENCE_EXPECTED_SIZES = {"detailed": (7400, 4932), "google": (3400, 2267)}
RUTTING_IDS = tuple(range(1697, 1702))
FEATURE_CACHE_SCHEMA = 3

WORKSHOP_IDS = {
    "AGOT": "2962333032",
    "NOW": "3664900993",
    "LOV": "3403938445",
    "RC": "3719888822",
    "EE": "3682802751",
    "EEP": "3768149491",
}


@dataclass(frozen=True)
class Definition:
    province_id: int
    red: int
    green: int
    blue: int
    name: str

    @property
    def packed_rgb(self) -> int:
        return (self.red << 16) | (self.green << 8) | self.blue

    @property
    def rgb_text(self) -> str:
        return f"{self.red}:{self.green}:{self.blue}"


@dataclass(frozen=True)
class MaskGroup:
    name: str
    role: str
    patterns: tuple[str, ...]
    terrain: str | None
    weight: float
    priority_threshold: float | None
    reason: str


@dataclass(frozen=True)
class TitleRow:
    province_id: int
    empire: str
    kingdom: str
    duchy: str
    county: str
    barony: str

    def value_for_scope(self, scope: str) -> str:
        if scope == "province":
            return str(self.province_id)
        return getattr(self, scope)


@dataclass(frozen=True)
class GraphicalMapping:
    scope: str
    key: str
    graphical_region: str
    allow_disconnected: bool
    reason: str


@dataclass(frozen=True)
class LoreRegion:
    empire: str
    base_terrain: str
    wooded_terrain: str | None
    reason: str


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def bool_value(value: str, *, field: str) -> bool:
    lowered = value.strip().lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    raise ValueError(f"{field}: expected true or false, got {value!r}")


def parse_definitions(
    path: Path, *, expected_rows: int | None = None
) -> list[Definition]:
    rows: list[Definition] = []
    for line_number, line in enumerate(read_text(path).splitlines(), 1):
        if not line.strip():
            continue
        fields = line.split(";")
        if len(fields) < 5:
            raise ValueError(f"{path}:{line_number}: malformed definition row")
        try:
            province_id, red, green, blue = map(int, fields[:4])
        except ValueError as error:
            raise ValueError(
                f"{path}:{line_number}: non-numeric definition fields"
            ) from error
        rows.append(Definition(province_id, red, green, blue, fields[4]))

    expected = TARGET_LAST + 1 if expected_rows is None else expected_rows
    if len(rows) != expected:
        raise AssertionError(
            f"{path.name} definition row count changed: {len(rows)} != {expected}"
        )
    ids = [row.province_id for row in rows]
    if ids != list(range(expected)):
        raise AssertionError(
            f"{path.name} definition IDs are no longer contiguous 0..{expected - 1}"
        )
    packed = [row.packed_rgb for row in rows]
    if len(packed) != len(set(packed)):
        duplicates = [rgb for rgb, count in Counter(packed).items() if count > 1]
        raise AssertionError(f"duplicate definition RGB values: {duplicates[:10]}")
    return rows


def parse_scalar_terrain(path: Path) -> dict[int, str]:
    result: dict[int, str] = {}
    pattern = re.compile(r"^\s*(\d+)\s*=\s*([a-z][a-z0-9_]*)\s*(?:#.*)?$")
    for line in read_text(path).splitlines():
        match = pattern.match(line)
        if match:
            result[int(match.group(1))] = match.group(2)
    return result


def terrain_winners(module_roots: Iterable[Path]) -> dict[int, str]:
    result: dict[int, str] = {}
    for module_root in module_roots:
        terrain_root = module_root / "common/province_terrain"
        if not terrain_root.is_dir():
            continue
        for path in sorted(terrain_root.rglob("*.txt")):
            result.update(parse_scalar_terrain(path))
    return result


def terrain_type_keys(module_roots: Iterable[Path]) -> set[str]:
    keys: set[str] = set()
    pattern = re.compile(r"^([a-z][a-z0-9_]*)\s*=\s*\{")
    for module_root in module_roots:
        terrain_root = module_root / "common/terrain_types"
        if not terrain_root.is_dir():
            continue
        for path in sorted(terrain_root.rglob("*.txt")):
            for line in read_text(path).splitlines():
                if match := pattern.match(line):
                    keys.add(match.group(1))
    return keys


def parse_default_map(path: Path) -> tuple[set[int], set[int], set[int]]:
    categories = {"sea_zones": set(), "river_provinces": set(), "lakes": set()}
    pattern = re.compile(
        r"^\s*(sea_zones|river_provinces|lakes)\s*=\s*" r"(LIST|RANGE)\s*\{([^}]*)\}"
    )
    for line in read_text(path).splitlines():
        line = line.split("#", 1)[0]
        match = pattern.match(line)
        if not match:
            continue
        name, kind, body = match.groups()
        values = [int(value) for value in re.findall(r"\d+", body)]
        if kind == "RANGE":
            if len(values) != 2:
                raise ValueError(f"{path}: malformed {name} RANGE")
            values = list(range(values[0], values[1] + 1))
        categories[name].update(values)
    return (categories["sea_zones"], categories["river_provinces"], categories["lakes"])


def parse_titles(
    path: Path, *, require_unique_provinces: bool = True
) -> list[TitleRow]:
    title_pattern = re.compile(r"^\s*([ekdcb]_[A-Za-z0-9_]+)\s*=\s*\{")
    province_pattern = re.compile(r"^\s*province\s*=\s*(\d+)\b")
    stack: list[tuple[str, int]] = []
    depth = 0
    rows: list[TitleRow] = []

    for raw_line in read_text(path).splitlines():
        line = raw_line.split("#", 1)[0]
        while stack and depth < stack[-1][1]:
            stack.pop()
        if title_match := title_pattern.match(line):
            stack.append((title_match.group(1), depth + 1))
        if province_match := province_pattern.match(line):
            ancestry: dict[str, str] = {}
            for title, _ in stack:
                ancestry[title[0]] = title
            # The empire tier is optional: Further East leaves 146 provinces under
            # a top-level kingdom. Empire-scoped graphical mappings simply do not
            # match those, which is the correct outcome. The lower four tiers are
            # what the mappings and audits key on, so those stay required.
            if not set("kdcb") <= set(ancestry):
                raise AssertionError(
                    f"incomplete title ancestry for province {province_match.group(1)}: "
                    f"{ancestry}"
                )
            rows.append(
                TitleRow(
                    int(province_match.group(1)),
                    ancestry.get("e", ""),
                    ancestry["k"],
                    ancestry["d"],
                    ancestry["c"],
                    ancestry["b"],
                )
            )
        depth += line.count("{") - line.count("}")
        while stack and depth < stack[-1][1]:
            stack.pop()

    ids = [row.province_id for row in rows]
    if require_unique_provinces and len(ids) != len(set(ids)):
        duplicates = [province for province, count in Counter(ids).items() if count > 1]
        raise AssertionError(f"duplicate landed-title province IDs: {duplicates[:10]}")
    return rows


def load_mask_groups(
    path: Path, mask_paths: list[Path], terrain_root: Path
) -> tuple[list[MaskGroup], dict[str, MaskGroup]]:
    data = tomllib.loads(read_text(path))
    if data.get("version") != 1:
        raise ValueError(f"{path}: unsupported mask configuration version")
    groups: list[MaskGroup] = []
    for raw in data.get("groups", []):
        role = raw["role"]
        if role not in {"gameplay", "detail", "ignore"}:
            raise ValueError(f"{path}: invalid role {role!r}")
        terrain = raw.get("terrain")
        if role == "gameplay" and not terrain:
            raise ValueError(f"{path}: gameplay group {raw['name']} needs terrain")
        if role != "gameplay" and terrain:
            raise ValueError(f"{path}: non-gameplay group cannot declare terrain")
        reason = raw.get("reason", "")
        if role != "gameplay" and not reason:
            raise ValueError(f"{path}: {raw['name']} needs an explicit reason")
        groups.append(
            MaskGroup(
                name=raw["name"],
                role=role,
                patterns=tuple(raw["patterns"]),
                terrain=terrain,
                weight=float(raw.get("weight", 1.0)),
                priority_threshold=(
                    float(raw["priority_threshold"])
                    if "priority_threshold" in raw
                    else None
                ),
                reason=reason,
            )
        )
    names = [group.name for group in groups]
    if len(names) != len(set(names)):
        raise ValueError(f"{path}: duplicate mask group names")

    mask_to_group: dict[str, MaskGroup] = {}
    for mask_path in mask_paths:
        relative = mask_path.relative_to(terrain_root).as_posix()
        matches = [
            group
            for group in groups
            if any(fnmatch.fnmatchcase(relative, pattern) for pattern in group.patterns)
        ]
        if len(matches) != 1:
            raise AssertionError(
                f"mask {relative!r} matched {len(matches)} groups: "
                f"{[group.name for group in matches]}"
            )
        mask_to_group[relative] = matches[0]

    empty_groups = [
        group.name
        for group in groups
        if not any(value.name == group.name for value in mask_to_group.values())
    ]
    if empty_groups:
        raise AssertionError(f"mask groups match no files: {empty_groups}")
    return groups, mask_to_group


def load_graphical_mappings(path: Path) -> list[GraphicalMapping]:
    allowed_scopes = {"empire", "kingdom", "duchy", "county", "province"}
    rows: list[GraphicalMapping] = []
    seen: set[tuple[str, str]] = set()
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        expected = {"scope", "key", "graphical_region", "allow_disconnected", "reason"}
        if set(reader.fieldnames or []) != expected:
            raise ValueError(f"{path}: expected columns {sorted(expected)}")
        for line_number, raw in enumerate(reader, 2):
            scope = raw["scope"].strip()
            key = raw["key"].strip()
            if scope not in allowed_scopes:
                raise ValueError(f"{path}:{line_number}: invalid scope {scope!r}")
            pair = (scope, key)
            if pair in seen:
                raise ValueError(f"{path}:{line_number}: duplicate mapping {pair}")
            seen.add(pair)
            reason = raw["reason"].strip()
            if not reason:
                raise ValueError(f"{path}:{line_number}: reason is required")
            rows.append(
                GraphicalMapping(
                    scope,
                    key,
                    raw["graphical_region"].strip(),
                    bool_value(
                        raw["allow_disconnected"],
                        field=f"{path}:{line_number}:allow_disconnected",
                    ),
                    reason,
                )
            )
    return rows


def load_lore_regions(path: Path) -> dict[str, LoreRegion]:
    rows: dict[str, LoreRegion] = {}
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        expected = {"empire", "base_terrain", "wooded_terrain", "reason"}
        if set(reader.fieldnames or []) != expected:
            raise ValueError(f"{path}: expected columns {sorted(expected)}")
        for line_number, raw in enumerate(reader, 2):
            empire = raw["empire"].strip()
            if empire in rows:
                raise ValueError(f"{path}:{line_number}: duplicate empire {empire}")
            base_terrain = raw["base_terrain"].strip()
            wooded_terrain = raw["wooded_terrain"].strip() or None
            reason = raw["reason"].strip()
            if not empire or not base_terrain or not reason:
                raise ValueError(
                    f"{path}:{line_number}: empire, base terrain, and reason "
                    "are required"
                )
            rows[empire] = LoreRegion(
                empire=empire,
                base_terrain=base_terrain,
                wooded_terrain=wooded_terrain,
                reason=reason,
            )
    return rows


def load_terrain_decisions(path: Path) -> dict[int, tuple[str, str, str]]:
    rows: dict[int, tuple[str, str, str]] = {}
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        expected = {"province_id", "decision", "terrain", "reason"}
        if set(reader.fieldnames or []) != expected:
            raise ValueError(f"{path}: expected columns {sorted(expected)}")
        for line_number, raw in enumerate(reader, 2):
            province_id = int(raw["province_id"])
            if province_id in rows:
                raise ValueError(f"{path}:{line_number}: duplicate province decision")
            decision = raw["decision"].strip()
            if decision not in {"accept", "override"}:
                raise ValueError(f"{path}:{line_number}: invalid decision {decision!r}")
            terrain = raw["terrain"].strip()
            reason = raw["reason"].strip()
            if not terrain or not reason:
                raise ValueError(
                    f"{path}:{line_number}: terrain and reason are required"
                )
            rows[province_id] = (decision, terrain, reason)
    return rows


def build_id_raster(
    definitions: list[Definition], provinces_path: Path
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    with Image.open(provinces_path) as image:
        if image.size != EXPECTED_SIZE or image.mode != "RGB":
            raise AssertionError(
                f"unexpected provinces.png: size={image.size}, mode={image.mode}"
            )
        rgb = np.asarray(image, dtype=np.uint8)

    packed = (
        (rgb[:, :, 0].astype(np.uint32) << 16)
        | (rgb[:, :, 1].astype(np.uint32) << 8)
        | rgb[:, :, 2].astype(np.uint32)
    )
    del rgb
    lookup = np.full(1 << 24, -1, dtype=np.int32)
    for row in definitions:
        lookup[row.packed_rgb] = row.province_id
    id_raster = lookup[packed]
    del packed, lookup
    unknown = int(np.count_nonzero(id_raster < 0))
    if unknown:
        raise AssertionError(
            f"provinces.png contains {unknown} pixels with unknown RGB"
        )

    flat = id_raster.ravel()
    count = np.bincount(flat, minlength=DEFINITION_ROWS).astype(np.int64)
    sum_x = np.zeros(DEFINITION_ROWS, dtype=np.float64)
    sum_y = np.zeros(DEFINITION_ROWS, dtype=np.float64)
    width, height = EXPECTED_SIZE
    x_values = np.arange(width, dtype=np.float64)
    for y0 in range(0, height, 256):
        chunk = id_raster[y0 : y0 + 256]
        rows = chunk.shape[0]
        chunk_flat = chunk.ravel()
        sum_x += np.bincount(
            chunk_flat, weights=np.tile(x_values, rows), minlength=DEFINITION_ROWS
        )
        sum_y += np.bincount(
            chunk_flat,
            weights=np.repeat(np.arange(y0, y0 + rows, dtype=np.float64), width),
            minlength=DEFINITION_ROWS,
        )
    centroid_x = np.full(DEFINITION_ROWS, -1.0, dtype=np.float64)
    centroid_y = np.full(DEFINITION_ROWS, -1.0, dtype=np.float64)
    painted = count > 0
    centroid_x[painted] = sum_x[painted] / count[painted]
    centroid_y[painted] = sum_y[painted] / count[painted]
    return id_raster, count, centroid_x, centroid_y


def adjacency_pairs(id_raster: np.ndarray) -> set[tuple[int, int]]:
    pairs: set[tuple[int, int]] = set()

    def add_boundaries(left: np.ndarray, right: np.ndarray) -> None:
        changed = left != right
        if not np.any(changed):
            return
        first = left[changed].astype(np.int64)
        second = right[changed].astype(np.int64)
        low = np.minimum(first, second)
        high = np.maximum(first, second)
        packed = (low << 32) | high
        for value in np.unique(packed):
            pairs.add((int(value >> 32), int(value & 0xFFFFFFFF)))

    height = id_raster.shape[0]
    for y0 in range(0, height, 256):
        chunk = id_raster[y0 : min(height, y0 + 257)]
        add_boundaries(chunk[:, :-1], chunk[:, 1:])
        add_boundaries(chunk[:-1, :], chunk[1:, :])
    return pairs


def aggregate_image(
    values: np.ndarray, id_raster: np.ndarray, area: np.ndarray
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    flat_ids = id_raster.ravel()
    flat_values = values.ravel()
    nonzero = flat_values > 0
    strong = flat_values >= 128
    intensity = np.bincount(flat_ids, weights=flat_values, minlength=DEFINITION_ROWS)
    coverage = np.bincount(flat_ids[nonzero], minlength=DEFINITION_ROWS).astype(
        np.float64
    )
    strong_coverage = np.bincount(flat_ids[strong], minlength=DEFINITION_ROWS).astype(
        np.float64
    )
    safe_area = np.maximum(area, 1)
    return (
        (intensity / (255.0 * safe_area)).astype(np.float32),
        (coverage / safe_area).astype(np.float32),
        (strong_coverage / safe_area).astype(np.float32),
    )


def feature_cache_key(manifest: dict[str, object], mask_config_path: Path) -> str:
    payload = f"feature-schema:{FEATURE_CACHE_SCHEMA}\n".encode()
    payload += json.dumps(manifest, sort_keys=True).encode()
    payload += mask_config_path.read_bytes()
    return sha256_bytes(payload)[:24]


def compute_features(
    *,
    heightmap_path: Path,
    mask_paths: list[Path],
    terrain_root: Path,
    groups: list[MaskGroup],
    mask_to_group: dict[str, MaskGroup],
    id_raster: np.ndarray,
    area: np.ndarray,
    reference_paths: dict[str, Path],
) -> dict[str, np.ndarray]:
    with Image.open(heightmap_path) as image:
        if image.size != EXPECTED_SIZE or image.mode not in {"I;16", "I;16L", "I"}:
            raise AssertionError(
                f"unexpected heightmap.png: size={image.size}, mode={image.mode}"
            )
        elevation_pixels = np.asarray(image, dtype=np.float32) / 65535.0

    flat_ids = id_raster.ravel()
    safe_area = np.maximum(area, 1)
    elevation = (
        np.bincount(
            flat_ids, weights=elevation_pixels.ravel(), minlength=DEFINITION_ROWS
        )
        / safe_area
    ).astype(np.float32)
    high_elevation = (
        np.bincount(
            flat_ids[elevation_pixels.ravel() >= 0.55], minlength=DEFINITION_ROWS
        )
        / safe_area
    ).astype(np.float32)

    slope_pixels = np.zeros_like(elevation_pixels)
    horizontal = np.abs(elevation_pixels[:, 1:] - elevation_pixels[:, :-1])
    slope_pixels[:, 1:] += horizontal
    slope_pixels[:, :-1] += horizontal
    del horizontal
    vertical = np.abs(elevation_pixels[1:, :] - elevation_pixels[:-1, :])
    slope_pixels[1:, :] += vertical
    slope_pixels[:-1, :] += vertical
    del vertical, elevation_pixels
    slope_pixels *= 0.25
    slope = (
        np.bincount(flat_ids, weights=slope_pixels.ravel(), minlength=DEFINITION_ROWS)
        / safe_area
    ).astype(np.float32)
    high_slope = (
        np.bincount(flat_ids[slope_pixels.ravel() >= 0.015], minlength=DEFINITION_ROWS)
        / safe_area
    ).astype(np.float32)
    del slope_pixels

    gameplay_groups = [group for group in groups if group.role == "gameplay"]
    group_index = {group.name: index for index, group in enumerate(gameplay_groups)}
    shape = (len(gameplay_groups), DEFINITION_ROWS)
    group_intensity = np.zeros(shape, dtype=np.float32)
    group_coverage = np.zeros(shape, dtype=np.float32)
    group_strong = np.zeros(shape, dtype=np.float32)
    gameplay_masks = [
        path
        for path in mask_paths
        if mask_to_group[path.relative_to(terrain_root).as_posix()].role == "gameplay"
    ]
    mask_shape = (len(gameplay_masks), DEFINITION_ROWS)
    mask_intensity = np.zeros(mask_shape, dtype=np.float32)
    mask_coverage = np.zeros(mask_shape, dtype=np.float32)
    mask_strong = np.zeros(mask_shape, dtype=np.float32)
    target_mask_names: list[str] = []

    for mask_index, mask_path in enumerate(gameplay_masks):
        relative = mask_path.relative_to(terrain_root).as_posix()
        group = mask_to_group[relative]
        with Image.open(mask_path) as image:
            if image.size != EXPECTED_SIZE or image.mode not in {"L", "P"}:
                raise AssertionError(
                    f"unexpected terrain mask {relative}: "
                    f"size={image.size}, mode={image.mode}"
                )
            values = np.asarray(image.convert("L"), dtype=np.uint8)
        intensity, coverage, strong = aggregate_image(values, id_raster, area)
        del values
        index = group_index[group.name]
        group_intensity[index] += intensity
        group_coverage[index] += coverage
        group_strong[index] += strong
        mask_intensity[mask_index] = intensity
        mask_coverage[mask_index] = coverage
        mask_strong[mask_index] = strong
        target_mask_names.append(relative)

    np.clip(group_intensity, 0.0, 1.0, out=group_intensity)
    np.clip(group_coverage, 0.0, 1.0, out=group_coverage)
    np.clip(group_strong, 0.0, 1.0, out=group_strong)
    reference_ids = np.asarray(
        Image.fromarray(id_raster).resize(
            REFERENCE_ANALYSIS_SIZE, Image.Resampling.NEAREST
        ),
        dtype=np.int32,
    )
    reference_flat_ids = reference_ids.ravel()
    reference_area = np.bincount(reference_flat_ids, minlength=DEFINITION_ROWS).astype(
        np.float64
    )
    reference_safe_area = np.maximum(reference_area, 1)

    def aggregate_reference(values: np.ndarray) -> np.ndarray:
        return (
            np.bincount(
                reference_flat_ids,
                weights=values.astype(np.float32, copy=False).ravel(),
                minlength=DEFINITION_ROWS,
            )
            / reference_safe_area
        ).astype(np.float32)

    reference_features: dict[str, np.ndarray] = {}
    for label, path in reference_paths.items():
        with Image.open(path) as image:
            expected_size = REFERENCE_EXPECTED_SIZES[label]
            if image.size != expected_size or image.mode != "RGB":
                raise AssertionError(
                    f"unexpected {label} lore map: size={image.size}, mode={image.mode}"
                )
            resized = image.resize(REFERENCE_ANALYSIS_SIZE, Image.Resampling.LANCZOS)
            rgb = np.asarray(resized, dtype=np.float32) / 255.0
        red = rgb[:, :, 0]
        green = rgb[:, :, 1]
        blue = rgb[:, :, 2]
        luminance = 0.2126 * red + 0.7152 * green + 0.0722 * blue
        if label == "detailed":
            reference_features.update(
                {
                    "lore_forest": aggregate_reference(
                        np.clip((green - (red + blue) / 2.0) * 5.0, 0.0, 1.0)
                        * (luminance < 0.62)
                    ),
                    "lore_deep_forest": aggregate_reference(
                        (green - red > 0.035)
                        & (green - blue > 0.035)
                        & (luminance < 0.48)
                    ),
                    "lore_arid": aggregate_reference(
                        np.clip((red - green) * 5.0, 0.0, 1.0)
                        * (red > blue)
                        * (luminance > 0.45)
                    ),
                    "lore_red_desert": aggregate_reference(
                        (red - green > 0.06) & (green - blue > 0.015) & (red > 0.55)
                    ),
                    "lore_snow": aggregate_reference(
                        (luminance > 0.73)
                        & (np.abs(red - green) < 0.07)
                        & (blue > green * 0.9)
                    ),
                    "lore_dark": aggregate_reference(luminance < 0.30),
                }
            )
        elif label == "google":
            reference_features.update(
                {
                    "lore_google_green": aggregate_reference(
                        (green > red * 1.025) & (green > blue * 1.06) & (green > 0.45)
                    ),
                    "lore_google_mountain": aggregate_reference(
                        (np.abs(red - green) < 0.04)
                        & (np.abs(green - blue) < 0.04)
                        & (red > 0.62)
                        & (red < 0.93)
                    ),
                }
            )
        else:
            raise AssertionError(f"unsupported lore-map label: {label}")
        del rgb
    del reference_ids

    result = {
        "elevation": elevation,
        "high_elevation": high_elevation,
        "slope": slope,
        "high_slope": high_slope,
        "group_intensity": group_intensity,
        "group_coverage": group_coverage,
        "group_strong": group_strong,
        "group_names": np.asarray([group.name for group in gameplay_groups]),
        "mask_intensity": mask_intensity,
        "mask_coverage": mask_coverage,
        "mask_strong": mask_strong,
        "mask_names": np.asarray(target_mask_names),
        "mask_weights": np.asarray(
            [
                mask_to_group[path.relative_to(terrain_root).as_posix()].weight
                for path in gameplay_masks
            ],
            dtype=np.float32,
        ),
    }
    result.update(reference_features)
    return result


def load_or_compute_features(
    *, cache_dir: Path, cache_key: str, no_cache: bool, **kwargs: object
) -> dict[str, np.ndarray]:
    cache_path = cache_dir / f"features-{cache_key}.npz"
    if cache_path.is_file() and not no_cache:
        with np.load(cache_path, allow_pickle=False) as loaded:
            return {name: loaded[name] for name in loaded.files}

    result = compute_features(**kwargs)  # type: ignore[arg-type]
    cache_dir.mkdir(parents=True, exist_ok=True)
    temporary = cache_path.with_suffix(".tmp.npz")
    np.savez_compressed(temporary, **result)
    temporary.replace(cache_path)
    return result


def normalize_terrain(terrain: str) -> str:
    return re.sub(r"^(?:majorroad|minorroad)_", "", terrain)


def softmax(scores: np.ndarray) -> np.ndarray:
    shifted = scores - np.max(scores, axis=1, keepdims=True)
    values = np.exp(shifted)
    return values / np.sum(values, axis=1, keepdims=True)


def macro_f1(actual: np.ndarray, predicted: np.ndarray, class_count: int) -> float:
    scores: list[float] = []
    for class_index in range(class_count):
        true_positive = int(
            np.count_nonzero((actual == class_index) & (predicted == class_index))
        )
        false_positive = int(
            np.count_nonzero((actual != class_index) & (predicted == class_index))
        )
        false_negative = int(
            np.count_nonzero((actual == class_index) & (predicted != class_index))
        )
        denominator = 2 * true_positive + false_positive + false_negative
        if denominator:
            scores.append(2 * true_positive / denominator)
    return float(np.mean(scores)) if scores else 0.0


def ridge_weights(
    features: np.ndarray, labels: np.ndarray, class_count: int, penalty: float
) -> np.ndarray:
    design = np.column_stack([features, np.ones(len(features), dtype=np.float64)])
    targets = np.eye(class_count, dtype=np.float64)[labels]
    regularizer = np.eye(design.shape[1], dtype=np.float64) * penalty
    regularizer[-1, -1] = 0.0
    return np.linalg.solve(design.T @ design + regularizer, design.T @ targets)


def predict_scores(features: np.ndarray, weights: np.ndarray) -> np.ndarray:
    design = np.column_stack([features, np.ones(len(features), dtype=np.float64)])
    return design @ weights


def class_precision_thresholds(
    actual: np.ndarray, probabilities: np.ndarray, minimum_precision: float = 0.95
) -> np.ndarray:
    predicted = np.argmax(probabilities, axis=1)
    confidence = np.max(probabilities, axis=1)
    thresholds = np.full(probabilities.shape[1], 1.01, dtype=np.float64)
    for class_index in range(probabilities.shape[1]):
        indices = np.flatnonzero(predicted == class_index)
        if not len(indices):
            continue
        order = indices[np.argsort(-confidence[indices])]
        correct = (actual[order] == class_index).astype(np.int64)
        precision = np.cumsum(correct) / np.arange(1, len(order) + 1)
        acceptable = np.flatnonzero(precision >= minimum_precision)
        if len(acceptable):
            last = int(acceptable[-1])
            thresholds[class_index] = float(confidence[order[last]])
    return thresholds


def build_model_features(features: dict[str, np.ndarray]) -> np.ndarray:
    weights = features["mask_weights"][:, None]
    blocks = [
        (features["mask_intensity"] * weights).T,
        (features["mask_coverage"] * weights).T,
        (features["mask_strong"] * weights).T,
        features["elevation"][:, None],
        features["high_elevation"][:, None],
        features["slope"][:, None],
        features["high_slope"][:, None],
    ]
    return np.column_stack(blocks).astype(np.float64)


def train_terrain_model(
    *,
    model_features: np.ndarray,
    terrain_by_province: dict[int, str],
    water_ids: set[int],
    centroid_x: np.ndarray,
    centroid_y: np.ndarray,
    valid_terrains: set[str],
    gameplay_terrains: set[str],
) -> tuple[
    list[str],
    np.ndarray,
    np.ndarray,
    np.ndarray,
    dict[str, int],
    float,
    np.ndarray,
    float,
]:
    excluded = {
        "default",
        "sea",
        "coastal_sea",
        "ocean",
        "smoking_sea",
        "smoking_sea_volcano",
        "urban",
    }
    labels_by_id: dict[int, str] = {}
    for province_id, raw_terrain in terrain_by_province.items():
        terrain = normalize_terrain(raw_terrain)
        if (
            province_id >= TARGET_FIRST
            or province_id in water_ids
            or centroid_x[province_id] < 0
            or terrain in excluded
            or terrain not in valid_terrains
        ):
            continue
        labels_by_id[province_id] = terrain

    counts = Counter(labels_by_id.values())
    classes = sorted(
        terrain
        for terrain, count in counts.items()
        if count >= 20
        and (
            terrain in gameplay_terrains
            or terrain
            in {
                "cloudforest",
                "glacier",
                "highlands",
                "taiga_bog",
                "terraced_hills",
                "the_bog",
            }
        )
    )
    if len(classes) < 8:
        raise AssertionError(f"too few usable terrain classes: {classes}")
    class_index = {name: index for index, name in enumerate(classes)}
    train_ids = np.asarray(
        [
            province_id
            for province_id, terrain in sorted(labels_by_id.items())
            if terrain in class_index
        ],
        dtype=np.int32,
    )
    labels = np.asarray(
        [class_index[labels_by_id[int(province_id)]] for province_id in train_ids],
        dtype=np.int32,
    )
    raw = model_features[train_ids]
    mean = np.mean(raw, axis=0)
    scale = np.std(raw, axis=0)
    scale[scale < 1e-8] = 1.0
    standardized = (raw - mean) / scale
    folds = (
        (centroid_x[train_ids] // 1024).astype(np.int32)
        + 3 * (centroid_y[train_ids] // 1024).astype(np.int32)
    ) % 5

    best_penalty = 1.0
    best_f1 = -1.0
    best_scores: np.ndarray | None = None
    for penalty in (0.01, 0.1, 1.0, 10.0, 100.0):
        out_of_fold = np.zeros((len(train_ids), len(classes)), dtype=np.float64)
        for fold in range(5):
            training = folds != fold
            validation = folds == fold
            weights = ridge_weights(
                standardized[training], labels[training], len(classes), penalty
            )
            out_of_fold[validation] = predict_scores(standardized[validation], weights)
        score = macro_f1(labels, np.argmax(out_of_fold, axis=1), len(classes))
        if score > best_f1:
            best_f1 = score
            best_penalty = penalty
            best_scores = out_of_fold

    assert best_scores is not None
    best_scale = 1.0
    best_loss = float("inf")
    for logit_scale in (0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 50.0):
        probabilities = softmax(best_scores * logit_scale)
        loss = float(
            -np.mean(
                np.log(
                    np.clip(probabilities[np.arange(len(labels)), labels], 1e-12, 1.0)
                )
            )
        )
        if loss < best_loss:
            best_loss = loss
            best_scale = logit_scale
    best_probabilities = softmax(best_scores * best_scale)
    thresholds = class_precision_thresholds(labels, best_probabilities)
    weights = ridge_weights(standardized, labels, len(classes), best_penalty)
    label_counts = {
        terrain: int(np.count_nonzero(labels == index))
        for terrain, index in class_index.items()
    }
    return (
        classes,
        mean,
        scale,
        weights,
        label_counts,
        best_f1,
        thresholds,
        best_scale,
    )


def parse_top_level_blocks(text: str) -> dict[str, str]:
    blocks: dict[str, str] = {}
    start_pattern = re.compile(r"(?m)^([A-Za-z0-9_]+)\s*=\s*\{")
    position = 0
    while match := start_pattern.search(text, position):
        start = match.start()
        depth = 0
        quoted = False
        comment = False
        end: int | None = None
        for index in range(match.end() - 1, len(text)):
            character = text[index]
            if comment:
                if character == "\n":
                    comment = False
            elif character == '"':
                quoted = not quoted
            elif character == "#" and not quoted:
                comment = True
            elif not quoted:
                if character == "{":
                    depth += 1
                elif character == "}":
                    depth -= 1
                    if depth == 0:
                        end = index + 1
                        break
        if end is None:
            raise ValueError(f"unterminated geographical-region block {match.group(1)}")
        blocks[match.group(1)] = text[start:end]
        position = end
    return blocks


def effective_region_blocks(module_roots: Iterable[Path]) -> dict[str, str]:
    result: dict[str, str] = {}
    for module_root in module_roots:
        region_root = module_root / "map_data/geographical_regions"
        if not region_root.is_dir():
            continue
        for path in sorted(region_root.rglob("*.txt")):
            result.update(parse_top_level_blocks(read_text(path)))
    return result


def direct_graphical_flag(block: str) -> bool:
    return bool(re.search(r"(?m)^\s*graphical\s*=\s*yes\s*(?:#.*)?$", block))


# A geographical region names its members by title as well as by province. Each
# of these lists resolves against one scope of the province's title chain; a
# `regions` list resolves against another region block.
MEMBERSHIP_KEYS = {
    "counties": "county",
    "duchies": "duchy",
    "kingdoms": "kingdom",
}

_LIST_PATTERN = r"(?ms)^([ \t]+){key}\s*=\s*\{{(.*?)^\1\}}"


def block_list_body(block: str, key: str) -> re.Match[str] | None:
    return re.search(_LIST_PATTERN.format(key=key), block)


def block_members(block: str, key: str) -> list[str]:
    """Return the named members of one membership list, in source order."""
    match = block_list_body(block, key)
    if not match:
        return []
    return re.sub(r"#.*", "", match.group(2)).split()


def block_province_ids(block: str) -> set[int]:
    """Return the province ids one region block lists directly."""
    match = block_list_body(block, "provinces")
    if not match:
        return set()
    return {
        int(value) for value in re.findall(r"(?m)(?<![A-Za-z0-9_])\d+", match.group(2))
    }


def remove_block_members(block: str, key: str, members: set[str]) -> str:
    """Drop named members from one membership list, removing an emptied list."""
    match = re.search(_LIST_PATTERN.format(key=key) + r"\n?", block)
    if not match:
        raise ValueError(f"graphical block has no {key} list")
    indent = match.group(1)
    kept = [name for name in block_members(block, key) if name not in members]
    if not kept:
        return block[: match.start()] + block[match.end() :]
    body = "".join(f"{indent}\t{name}\n" for name in kept)
    replacement = f"{indent}{key} = {{\n{body}{indent}}}\n"
    return block[: match.start()] + replacement + block[match.end() :]


def set_block_provinces(block: str, province_ids: Iterable[int]) -> str:
    """Replace a region block's province list with exactly these ids."""
    combined = sorted(set(province_ids))
    if not combined:
        match = re.search(_LIST_PATTERN.format(key="provinces") + r"\n?", block)
        return block if not match else block[: match.start()] + block[match.end() :]
    lines = [
        "\tprovinces = {",
        *[
            "\t\t" + " ".join(str(value) for value in combined[offset : offset + 16])
            for offset in range(0, len(combined), 16)
        ],
        "\t}",
    ]
    replacement = "\n".join(lines)
    match = block_list_body(block, "provinces")
    if match:
        return block[: match.start()] + replacement + block[match.end() :]
    closing = block.rfind("}")
    if closing < 0:
        raise ValueError("graphical block has no closing brace")
    prefix = block[:closing]
    if not prefix.endswith("\n"):
        prefix += "\n"
    return prefix + replacement + "\n}"


def repair_inherited_graphical_block(style: str, block: str) -> str:
    if style != "graphical_siberia":
        return block
    # Older NOW sources reference world_westeros_skagos. That helper is not
    # visible after the later geographical-region replacements in this
    # playset, so repeating the reference in our complete block is Tiger-fatal.
    # Newer EEP sources already carry d_skagos directly; accept that upstream
    # repair and extend the same duchy set with the two required Essos edges.
    needle = "\t\tworld_westeros_skagos\n"
    if block.count(needle) == 1:
        block = block.replace(needle, "")
        closing = block.rfind("}")
        if closing < 0:
            raise ValueError("graphical_siberia has no closing brace")
        addition = (
            "\tduchies = {\n\t\td_skagos\n\t\td_deepdown\n\t\td_driftwood_hall\n\t}\n"
        )
        return block[:closing] + addition + block[closing:]

    if block.count(needle) != 0:
        raise AssertionError(
            "graphical_siberia Skagos reference changed; re-audit the repair"
        )
    duchies = re.search(r"(?ms)^\tduchies\s*=\s*\{.*?^\t\}", block)
    if not duchies or block.count("\t\td_skagos\n") != 1:
        raise AssertionError(
            "graphical_siberia direct Skagos block changed; re-audit the repair"
        )
    body = duchies.group(0)
    for duchy in ("d_deepdown", "d_driftwood_hall"):
        if body.count(f"\t\t{duchy}\n") > 1:
            raise AssertionError(
                f"graphical_siberia contains duplicate {duchy}; re-audit the repair"
            )
        if body.count(f"\t\t{duchy}\n") == 0:
            body = body[:-2] + f"\t\t{duchy}\n" + "\t}"
    return block[: duchies.start()] + body + block[duchies.end() :]


def connected_components(
    province_ids: set[int], adjacency: dict[int, set[int]]
) -> dict[int, int]:
    component_by_id: dict[int, int] = {}
    component = 0
    for start in sorted(province_ids):
        if start in component_by_id:
            continue
        component += 1
        stack = [start]
        component_by_id[start] = component
        while stack:
            current = stack.pop()
            for neighbor in adjacency.get(current, set()):
                if neighbor in province_ids and neighbor not in component_by_id:
                    component_by_id[neighbor] = component
                    stack.append(neighbor)
    return component_by_id


def feature_source_state(
    map_definition: Path,
    reference_paths: dict[str, Path],
    *,
    root: Path,
    workshop: dict[str, Path],
    workshop_root: Path,
    mask_paths: list[Path],
) -> dict[str, object]:
    source_files: set[Path] = {
        workshop["EE"] / "map_data/definition.csv",
        workshop["EE"] / "map_data/default.map",
        workshop["EE"] / "map_data/provinces.png",
        workshop["EE"] / "map_data/heightmap.png",
        # The TempLoV compatch recolours EE's province map from 2.5.0 onward.
        # Both halves of that pair are pinned so any future change forces a
        # re-review of the recolour-preserves-geometry assumption below.
        workshop["EEP"] / "map_data/definition.csv",
        workshop["EEP"] / "map_data/provinces.png",
        workshop["EEP"] / "map_data/default.map",
        workshop["EEP"] / "map_data/heightmap.png",
        workshop["EEP"] / "common/landed_titles/01_landed_titles.txt",
        workshop["EE"] / "common/province_terrain/ee_province_terrain.txt",
        workshop["EEP"] / "common/province_terrain/ee_province_terrain.txt",
        workshop["NOW"] / "common/landed_titles/01_agot_landed_titles.txt",
        map_definition,
    }
    source_files.update(reference_paths.values())
    for module_root in workshop.values():
        for relative_root in (
            "common/province_terrain",
            "common/terrain_types",
            "map_data/geographical_regions",
        ):
            directory = module_root / relative_root
            if directory.is_dir():
                source_files.update(directory.rglob("*.txt"))

    files = {
        canonical_source_path(path, root=root, workshop_root=workshop_root): {
            "sha256": sha256_file(path),
            "size": path.stat().st_size,
        }
        for path in sorted(source_files)
    }
    masks = {
        canonical_source_path(path, root=root, workshop_root=workshop_root): {
            "sha256": sha256_file(path),
            "size": path.stat().st_size,
        }
        for path in mask_paths
    }
    return {
        "schema_version": 2,
        "expected": {
            "definition_rows": DEFINITION_ROWS,
            "target_first": TARGET_FIRST,
            "target_last": TARGET_LAST,
            "target_count": TARGET_COUNT,
            "gap_count": EXPECTED_GAP_COUNT,
            "title_count": EXPECTED_TITLE_COUNT,
            "mask_count": EXPECTED_MASK_COUNT,
            "image_width": EXPECTED_SIZE[0],
            "image_height": EXPECTED_SIZE[1],
        },
        "files": files,
        "terrain_masks": masks,
    }


@dataclass
class WorldDataPipeline:
    """Run the ordered generation phases without module-global state."""

    context: GenerationContext

    def run(self) -> None:
        self.load_sources()
        self.build_features()
        self.propose_model_terrain()
        self.apply_lore_terrain()
        self.finalize_terrain()
        self.build_graphical_regions()
        self.write_outputs()

    def load_sources(self) -> None:
        self.root = self.context.workspace_root
        workshop_root = self.context.workshop_root(
            "agot",
            "agot-now",
            "legacy-of-valyria",
            "legacy-of-valyria-bridge",
            "essos-expanded",
            "essos-expanded-bridge",
        )
        self.workshop = {
            label: workshop_root / workshop_id
            for label, workshop_id in WORKSHOP_IDS.items()
        }
        missing_modules = [
            f"{label}:{path}"
            for label, path in self.workshop.items()
            if not path.is_dir()
        ]
        if missing_modules:
            raise FileNotFoundError(f"missing Workshop modules: {missing_modules}")

        self.module = self.context.output_root
        # Audits are development artifacts: staged under the reserved artifacts/
        # prefix, promoted into the tooling tree, never installed into CK3.
        artifacts = self.module / "artifacts"
        self.source = artifacts / "world_data"
        assets = self.context.assets_dir / "world_data"
        self.mask_config_path = assets / "terrain_mask_groups.toml"
        self.decisions_path = assets / "terrain_decisions.csv"
        lore_regions_path = assets / "terrain_lore_regions.csv"
        self.graphical_config_path = assets / "graphical_style_map.csv"
        self.reference_paths = {
            "detailed": self.context.source("known-world-detailed"),
            "google": self.context.source("known-world-google"),
        }
        missing_reference_maps = [
            path.relative_to(self.root).as_posix()
            for path in self.reference_paths.values()
            if not path.is_file()
        ]
        if missing_reference_maps:
            raise FileNotFoundError(
                f"missing lore reference maps: {missing_reference_maps}"
            )
        self.terrain_root = self.workshop["EE"] / "gfx/map/terrain"
        self.mask_paths = sorted(self.terrain_root.rglob("*_mask.png"))
        if len(self.mask_paths) != EXPECTED_MASK_COUNT:
            raise AssertionError(
                f"terrain mask count changed: {len(self.mask_paths)} != {EXPECTED_MASK_COUNT}"
            )
        self.groups, self.mask_to_group = load_mask_groups(
            self.mask_config_path, self.mask_paths, self.terrain_root
        )
        self.gameplay_groups = [
            group for group in self.groups if group.role == "gameplay"
        ]

        merged_definitions = parse_definitions(
            self.context.source("map-definition"), expected_rows=DEFINITION_ROWS
        )
        self.eep_definitions = parse_definitions(
            self.workshop["EEP"] / "map_data/definition.csv",
            expected_rows=DEFINITION_ROWS,
        )
        for province_id in range(TARGET_FIRST, TARGET_LAST + 1):
            if self.eep_definitions[province_id] != merged_definitions[province_id]:
                raise AssertionError(
                    f"map compatch changed TempLoV target definition row {province_id}"
                )
        # Further East owns the target range outright: it colours every row and
        # names most of what would otherwise be a generated `R<r>G<g>B<b>`
        # placeholder.  The pipeline reads its raster alongside its definitions,
        # so the ids classified here describe the land actually sampled.  Pin how
        # much it has named, so a re-authoring pass re-opens that assumption.
        named = sum(
            1
            for province_id in range(TARGET_FIRST, TARGET_LAST + 1)
            if not self.eep_definitions[province_id].name.startswith("R")
        )
        if named != EXPECTED_NAMED_TARGETS:
            raise AssertionError(
                "Further East's authored share of the target range changed: "
                f"{named} != {EXPECTED_NAMED_TARGETS}"
            )

        self.eep_terrain = parse_scalar_terrain(
            self.workshop["EEP"] / "common/province_terrain/ee_province_terrain.txt"
        )
        self.expected_ids = set(range(TARGET_FIRST, TARGET_LAST + 1))
        # TempLoV compatch 2.5.0 replaced its blanket `plains` placeholder with real
        # authored terrain for the east.  Those authored assignments are the
        # effective upstream decision and win over this module's lore-map proposal;
        # provinces the compatch still leaves at `plains` are the remaining
        # placeholder and keep the generated terrain.
        self.eep_authored = {
            province_id: terrain
            for province_id, terrain in self.eep_terrain.items()
            if province_id in self.expected_ids and terrain != "plains"
        }
        eep_placeholder = {
            province_id
            for province_id, terrain in self.eep_terrain.items()
            if province_id in self.expected_ids and terrain == "plains"
        }
        if not self.eep_authored:
            raise AssertionError(
                "TempLoV compatch no longer authors any non-plains target terrain"
            )
        if self.eep_authored.keys() & eep_placeholder:
            raise AssertionError(
                "TempLoV target terrain is both authored and placeholder"
            )

        self.ee_titles = [
            row
            for row in parse_titles(
                self.workshop["EEP"] / "common/landed_titles/01_landed_titles.txt"
            )
            if TARGET_FIRST <= row.province_id <= TARGET_LAST
        ]
        if len(self.ee_titles) != EXPECTED_TITLE_COUNT:
            raise AssertionError(
                f"EE titled province count changed: {len(self.ee_titles)} "
                f"!= {EXPECTED_TITLE_COUNT}"
            )
        if any(row.province_id not in self.expected_ids for row in self.ee_titles):
            raise AssertionError("EE landed titles reference an out-of-range province")
        self.empire_keys = {row.empire for row in self.ee_titles if row.empire}
        if len(self.empire_keys) != EXPECTED_EMPIRE_KEYS:
            raise AssertionError(
                f"EE empire scope count changed: {len(self.empire_keys)}"
            )
        self.lore_regions = load_lore_regions(lore_regions_path)
        if set(self.lore_regions) != self.empire_keys:
            raise AssertionError(
                "lore-region empire mappings changed: "
                f"missing={sorted(self.empire_keys - set(self.lore_regions))}, "
                f"extra={sorted(set(self.lore_regions) - self.empire_keys)}"
            )

        now_titles = parse_titles(
            self.workshop["NOW"] / "common/landed_titles/01_agot_landed_titles.txt",
            require_unique_provinces=False,
        )
        rutting_titles = [row for row in now_titles if row.county == "c_rutting"]
        if {row.province_id for row in rutting_titles} != set(RUTTING_IDS):
            raise AssertionError(
                f"c_rutting province set changed: "
                f"{sorted(row.province_id for row in rutting_titles)}"
            )
        self.graphical_titles = sorted(
            [*self.ee_titles, *rutting_titles], key=lambda row: row.province_id
        )

        with Image.open(self.workshop["EEP"] / "map_data/provinces.png") as image:
            if image.size != EXPECTED_SIZE or image.mode != "RGB":
                raise AssertionError(
                    f"unexpected provinces image: size={image.size}, mode={image.mode}"
                )
        with Image.open(self.workshop["EEP"] / "map_data/heightmap.png") as image:
            if image.size != EXPECTED_SIZE or image.mode not in {"I;16", "I;16L", "I"}:
                raise AssertionError(
                    f"unexpected heightmap image: size={image.size}, mode={image.mode}"
                )

        self.feature_source_state = feature_source_state(
            self.context.source("map-definition"),
            self.reference_paths,
            root=self.root,
            workshop=self.workshop,
            workshop_root=workshop_root,
            mask_paths=self.mask_paths,
        )

    def build_features(self) -> None:
        id_raster, area, centroid_x, centroid_y = build_id_raster(
            self.eep_definitions, self.workshop["EEP"] / "map_data/provinces.png"
        )
        unpainted_titles = [
            row.province_id
            for row in self.graphical_titles
            if area[row.province_id] == 0
        ]
        if unpainted_titles:
            raise AssertionError(
                f"graphical target provinces have no painted pixels: "
                f"{unpainted_titles[:10]}"
            )
        pairs = adjacency_pairs(id_raster)
        self.adjacency: dict[int, set[int]] = defaultdict(set)
        for first, second in pairs:
            self.adjacency[first].add(second)
            self.adjacency[second].add(first)

        self.sea_zones, self.river_provinces, self.lakes = parse_default_map(
            self.workshop["EEP"] / "map_data/default.map"
        )
        self.water_ids = self.sea_zones | self.river_provinces | self.lakes
        self.target_ids = np.arange(TARGET_FIRST, TARGET_LAST + 1, dtype=np.int32)
        cache_key = feature_cache_key(self.feature_source_state, self.mask_config_path)
        self.features = load_or_compute_features(
            cache_dir=self.root / ".ignored/cache/agot_now_lov_ee_world_data",
            cache_key=cache_key,
            no_cache=bool(self.context.options.get("no_cache", False)),
            heightmap_path=self.workshop["EEP"] / "map_data/heightmap.png",
            mask_paths=self.mask_paths,
            terrain_root=self.terrain_root,
            groups=self.groups,
            mask_to_group=self.mask_to_group,
            id_raster=id_raster,
            area=area,
            reference_paths=self.reference_paths,
        )
        if list(self.features["group_names"]) != [
            group.name for group in self.gameplay_groups
        ]:
            raise AssertionError("feature cache mask-group order mismatch")

        terrain_modules = [
            self.workshop["AGOT"],
            self.workshop["NOW"],
            self.workshop["LOV"],
            self.workshop["RC"],
            self.workshop["EE"],
            self.workshop["EEP"],
        ]
        # Every module here shares one province numbering: Further East adopted
        # AGOT's 8233-9400 band natively, so an AGOT terrain label and the pixels
        # measured at that id describe the same land.  No range is excluded from
        # the training labels.
        terrain_by_province = terrain_winners(terrain_modules)
        self.upstream_terrain = {
            province_id: terrain
            for province_id, terrain in terrain_by_province.items()
            if terrain != "default"
        }
        self.valid_terrains = terrain_type_keys(terrain_modules)
        gameplay_terrains = {
            group.terrain for group in self.gameplay_groups if group.terrain is not None
        }
        missing_terrain_types = gameplay_terrains - self.valid_terrains
        if missing_terrain_types:
            raise AssertionError(
                f"configured terrain types are not loaded: {sorted(missing_terrain_types)}"
            )
        lore_terrains = {
            region.base_terrain for region in self.lore_regions.values()
        } | {
            region.wooded_terrain
            for region in self.lore_regions.values()
            if region.wooded_terrain
        }
        missing_lore_terrains = lore_terrains - self.valid_terrains
        if missing_lore_terrains:
            raise AssertionError(
                f"configured lore terrain types are not loaded: "
                f"{sorted(missing_lore_terrains)}"
            )
        model_features = build_model_features(self.features)
        (
            self.classes,
            feature_mean,
            feature_scale,
            model_weights,
            self.label_counts,
            self.validation_f1,
            self.confidence_thresholds,
            logit_scale,
        ) = train_terrain_model(
            model_features=model_features,
            terrain_by_province=terrain_by_province,
            water_ids=self.water_ids,
            centroid_x=centroid_x,
            centroid_y=centroid_y,
            valid_terrains=self.valid_terrains,
            gameplay_terrains=gameplay_terrains,
        )
        standardized_targets = (
            model_features[self.target_ids] - feature_mean
        ) / feature_scale
        self.probabilities = softmax(
            predict_scores(standardized_targets, model_weights) * logit_scale
        )
        self.best_indices = np.argmax(self.probabilities, axis=1)
        sorted_probabilities = np.sort(self.probabilities, axis=1)
        self.confidences = sorted_probabilities[:, -1]
        self.margins = sorted_probabilities[:, -1] - sorted_probabilities[:, -2]

    def propose_model_terrain(self) -> None:
        self.group_index = {
            group.name: index for index, group in enumerate(self.gameplay_groups)
        }
        self.proposed: dict[int, str] = {}
        self.review_reasons: dict[int, list[str]] = defaultdict(list)
        self.runner_up: dict[int, str] = {}
        self.confidence_by_id: dict[int, float] = {}
        self.margin_by_id: dict[int, float] = {}
        self.priority_group_by_id: dict[int, str] = {}
        self.water_class_by_id: dict[int, str] = {}

        for offset, province_id_raw in enumerate(self.target_ids):
            province_id = int(province_id_raw)
            if province_id in self.lakes or province_id in self.river_provinces:
                self.proposed[province_id] = "sea"
                self.water_class_by_id[province_id] = (
                    "lake" if province_id in self.lakes else "river"
                )
                self.runner_up[province_id] = ""
                self.confidence_by_id[province_id] = 1.0
                self.margin_by_id[province_id] = 1.0
                continue
            if province_id in self.sea_zones:
                touches_land = any(
                    neighbor not in self.water_ids
                    for neighbor in self.adjacency.get(province_id, ())
                )
                self.proposed[province_id] = "coastal_sea" if touches_land else "sea"
                self.water_class_by_id[province_id] = (
                    "coastal_sea" if touches_land else "sea"
                )
                self.runner_up[province_id] = ""
                self.confidence_by_id[province_id] = 1.0
                self.margin_by_id[province_id] = 1.0
                continue

            class_index = int(self.best_indices[offset])
            model_terrain = self.classes[class_index]
            selected = model_terrain
            priority_candidates: list[tuple[float, MaskGroup]] = []
            for group in self.gameplay_groups:
                if group.priority_threshold is None:
                    continue
                intensity = float(
                    self.features["group_intensity"][
                        self.group_index[group.name], province_id
                    ]
                )
                if intensity >= group.priority_threshold:
                    priority_candidates.append((intensity * group.weight, group))
            if priority_candidates:
                _, priority_group = max(
                    priority_candidates, key=lambda value: (value[0], value[1].name)
                )
                self.priority_group_by_id[province_id] = priority_group.name
                if priority_group.terrain != model_terrain:
                    selected = str(priority_group.terrain)
                    self.review_reasons[province_id].append(
                        f"priority:{priority_group.name}_over_{model_terrain}"
                    )

            self.proposed[province_id] = selected
            order = np.argsort(self.probabilities[offset])
            self.runner_up[province_id] = self.classes[int(order[-2])]
            self.confidence_by_id[province_id] = float(self.confidences[offset])
            self.margin_by_id[province_id] = float(self.margins[offset])
            if self.confidences[offset] < self.confidence_thresholds[class_index]:
                self.review_reasons[province_id].append(
                    "below_95pct_precision_threshold"
                )
            if self.margins[offset] < 0.10:
                self.review_reasons[province_id].append("top_two_margin_below_0.10")

        self.model_proposed = dict(self.proposed)
        self.model_review_reasons = self.review_reasons

    def apply_lore_terrain(self) -> None:
        self.title_by_id = {row.province_id: row for row in self.ee_titles}
        self.proposed = {}
        self.review_reasons = defaultdict(list)
        self.lore_base_by_id: dict[int, str] = {}
        self.lore_reason_by_id: dict[int, str] = {}
        group_intensity = self.features["group_intensity"]

        for province_id in sorted(self.expected_ids):
            if province_id in self.water_ids:
                self.proposed[province_id] = self.model_proposed[province_id]
                self.lore_base_by_id[province_id] = self.model_proposed[province_id]
                self.lore_reason_by_id[province_id] = "Water class from EE default.map."
                continue

            title = self.title_by_id.get(province_id)
            region = self.lore_regions.get(title.empire) if title else None
            forest_signal = float(self.features["lore_forest"][province_id])
            deep_forest_signal = float(self.features["lore_deep_forest"][province_id])
            google_green_signal = float(self.features["lore_google_green"][province_id])
            arid_signal = float(self.features["lore_arid"][province_id])
            red_desert_signal = float(self.features["lore_red_desert"][province_id])
            dark_signal = float(self.features["lore_dark"][province_id])
            snow_signal = float(self.features["lore_snow"][province_id])
            google_mountain_signal = float(
                self.features["lore_google_mountain"][province_id]
            )
            slope = float(self.features["slope"][province_id])
            evidence: list[str] = []

            if region:
                base = region.base_terrain
                evidence.append(f"region:{region.empire}={base}")
                wooded_threshold = (
                    0.06
                    if region.wooded_terrain == "jungle"
                    else 0.08
                    if region.wooded_terrain == "taiga"
                    else 0.12
                )
                wooded = (
                    forest_signal >= wooded_threshold
                    or deep_forest_signal >= 0.05
                    or google_green_signal >= 0.10
                    or (region.wooded_terrain == "jungle" and dark_signal >= 0.35)
                )
                if region.wooded_terrain and wooded:
                    base = region.wooded_terrain
                    evidence.append(f"lore_wooded={base}")
            elif arid_signal >= 0.16 or red_desert_signal >= 0.18:
                base = "desert" if red_desert_signal >= 0.18 else "drylands"
                evidence.append(f"untitled_lore_arid={base}")
            elif (
                forest_signal >= 0.22
                or deep_forest_signal >= 0.12
                or google_green_signal >= 0.25
            ):
                base = "forest"
                evidence.append("untitled_lore_wooded=forest")
            else:
                base = "plains"
                evidence.append("untitled_lore_default=plains")

            desert_intensity = float(
                group_intensity[self.group_index["desert"], province_id]
            )
            desert_mountain_intensity = float(
                group_intensity[self.group_index["desert_mountains"], province_id]
            )
            if base == "drylands" and (
                red_desert_signal >= 0.28 or desert_intensity >= 0.50
            ):
                base = "desert"
                evidence.append("strong_desert_evidence")

            special: str | None = None
            if float(group_intensity[self.group_index["oasis"], province_id]) >= 0.08:
                special = "oasis"
            elif (
                float(group_intensity[self.group_index["floodplains"], province_id])
                >= 0.16
                and slope < 0.003
            ):
                special = "floodplains"
            elif (
                float(group_intensity[self.group_index["wetlands"], province_id])
                >= 0.24
                and slope < 0.003
            ):
                special = "wetlands"
            elif (
                float(group_intensity[self.group_index["jungle"], province_id]) >= 0.18
            ):
                special = "jungle"
            elif float(
                group_intensity[self.group_index["frozen"], province_id]
            ) >= 0.30 or (title and title.empire == "e_ibben" and snow_signal >= 0.45):
                special = "frozen_flats"
            elif float(
                group_intensity[self.group_index["farmlands"], province_id]
            ) >= 0.45 and (not title or title.empire != "e_ibben"):
                special = "farmlands"
            if special:
                base = special
                evidence.append(f"strong_mask={special}")

            wooded_strength = max(
                forest_signal, deep_forest_signal, google_green_signal
            )
            volcanic_intensity = float(
                group_intensity[self.group_index["volcanic"], province_id]
            )
            mountain = (
                slope >= 0.006
                or (google_mountain_signal >= 0.30 and slope >= 0.0025)
                or volcanic_intensity >= 0.16
            )
            hill = slope >= 0.003
            relief_exempt = {
                "farmlands",
                "floodplains",
                "frozen_flats",
                "oasis",
                "wetlands",
            }
            if mountain and base not in relief_exempt:
                if base in {"desert", "drylands"} or desert_mountain_intensity >= 0.34:
                    selected = "desert_mountains"
                else:
                    selected = "mountains"
                evidence.append(f"mountain_relief={selected}")
            elif hill and base not in relief_exempt and wooded_strength < 0.22:
                if base in {"desert", "drylands"} and desert_mountain_intensity >= 0.18:
                    selected = "desert_mountains"
                else:
                    selected = "hills"
                evidence.append(f"hill_relief={selected}")
            else:
                selected = base

            self.proposed[province_id] = selected
            self.lore_base_by_id[province_id] = base
            self.lore_reason_by_id[province_id] = "|".join(evidence)

    def finalize_terrain(self) -> None:
        decisions = load_terrain_decisions(self.decisions_path)
        unknown_decision_ids = set(decisions) - self.expected_ids
        if unknown_decision_ids:
            raise AssertionError(
                f"terrain decisions reference non-target IDs: "
                f"{sorted(unknown_decision_ids)[:10]}"
            )
        self.final_terrain = dict(self.proposed)
        # Defer to the TempLoV compatch's authored terrain before applying local
        # exceptions, but never override this module's water classes: the compatch
        # lists only land provinces, while `proposed` also carries EE's sea and
        # coastal-sea assignments from `default.map`.
        eep_applied = 0
        for province_id, terrain in self.eep_authored.items():
            if self.final_terrain.get(province_id) in {"sea", "coastal_sea"}:
                continue
            if terrain not in self.valid_terrains:
                raise AssertionError(
                    f"TempLoV terrain {terrain} for {province_id} is not loaded"
                )
            if self.final_terrain[province_id] != terrain:
                eep_applied += 1
            self.final_terrain[province_id] = terrain

        self.pending: list[int] = []
        for province_id in sorted(self.expected_ids):
            decision = decisions.get(province_id)
            if decision is None:
                continue
            action, terrain, _ = decision
            if terrain not in self.valid_terrains:
                raise AssertionError(
                    f"terrain decision {province_id} uses unloaded terrain {terrain}"
                )
            if action == "accept":
                if terrain != self.proposed[province_id]:
                    raise AssertionError(
                        f"accept decision for {province_id} must use proposed terrain "
                        f"{self.proposed[province_id]}, got {terrain}"
                    )
            else:
                self.final_terrain[province_id] = terrain

        mask_names = [str(value) for value in self.features["mask_names"]]
        mask_intensity = self.features["mask_intensity"][:, self.target_ids]
        self.terrain_audit_rows: list[dict[str, object]] = []
        for offset, province_id_raw in enumerate(self.target_ids):
            province_id = int(province_id_raw)
            title = self.title_by_id.get(province_id)
            top_masks = np.argsort(mask_intensity[:, offset])[-3:][::-1]
            contributions = [
                f"{mask_names[index]}:{float(mask_intensity[index, offset]):.4f}"
                for index in top_masks
                if mask_intensity[index, offset] > 0
            ]
            decision = decisions.get(province_id)
            self.terrain_audit_rows.append(
                {
                    "province_id": province_id,
                    "rgb": self.eep_definitions[province_id].rgb_text,
                    "barony": title.barony if title else "",
                    "county": title.county if title else "",
                    "duchy": title.duchy if title else "",
                    "kingdom": title.kingdom if title else "",
                    "empire": title.empire if title else "",
                    "model_terrain": self.model_proposed[province_id],
                    "proposed_terrain": self.proposed[province_id],
                    "eep_terrain": self.eep_terrain.get(province_id, ""),
                    "final_terrain": self.final_terrain[province_id],
                    "model_confidence": f"{self.confidence_by_id[province_id]:.6f}",
                    "model_runner_up": self.runner_up[province_id],
                    "model_margin": f"{self.margin_by_id[province_id]:.6f}",
                    "model_priority_group": self.priority_group_by_id.get(
                        province_id, ""
                    ),
                    "model_warning": "|".join(
                        self.model_review_reasons.get(province_id, [])
                    ),
                    "lore_base": self.lore_base_by_id[province_id],
                    "lore_forest": f"{float(self.features['lore_forest'][province_id]):.6f}",
                    "lore_google_green": (
                        f"{float(self.features['lore_google_green'][province_id]):.6f}"
                    ),
                    "lore_arid": f"{float(self.features['lore_arid'][province_id]):.6f}",
                    "lore_google_mountain": (
                        f"{float(self.features['lore_google_mountain'][province_id]):.6f}"
                    ),
                    "slope": f"{float(self.features['slope'][province_id]):.6f}",
                    "lore_reason": self.lore_reason_by_id[province_id],
                    "leading_masks": "|".join(contributions),
                    "water_class": self.water_class_by_id.get(province_id, "land"),
                    "review_reason": "|".join(self.review_reasons.get(province_id, [])),
                    "decision": decision[0] if decision else "",
                    "decision_reason": decision[2] if decision else "",
                    "review_status": (
                        "pending"
                        if province_id in self.pending
                        else "reviewed"
                        if decision
                        else "automatic"
                    ),
                }
            )

    def build_graphical_regions(self) -> None:
        mappings = load_graphical_mappings(self.graphical_config_path)
        mapping_by_scope_key = {
            (mapping.scope, mapping.key): mapping for mapping in mappings
        }
        config_empire_keys = {
            mapping.key for mapping in mappings if mapping.scope == "empire"
        }
        if config_empire_keys != self.empire_keys:
            raise AssertionError(
                "graphical empire mappings changed: "
                f"missing={sorted(self.empire_keys - config_empire_keys)}, "
                f"extra={sorted(config_empire_keys - self.empire_keys)}"
            )
        self.region_blocks = effective_region_blocks(
            [
                self.workshop["AGOT"],
                self.workshop["NOW"],
                self.workshop["LOV"],
                self.workshop["RC"],
                self.workshop["EE"],
                self.workshop["EEP"],
            ]
        )
        self.graphical_blocks = {
            key: block
            for key, block in self.region_blocks.items()
            if direct_graphical_flag(block)
        }
        missing_styles = {mapping.graphical_region for mapping in mappings} - set(
            self.graphical_blocks
        )
        if missing_styles:
            raise AssertionError(
                f"mapped graphical styles are not loaded: {sorted(missing_styles)}"
            )

        scope_order = ("province", "county", "duchy", "kingdom", "empire")
        assigned_mapping: dict[int, GraphicalMapping] = {}
        used_mappings: Counter[tuple[str, str]] = Counter()
        for title in self.graphical_titles:
            match: GraphicalMapping | None = None
            for scope in scope_order:
                key = title.value_for_scope(scope)
                if candidate := mapping_by_scope_key.get((scope, key)):
                    match = candidate
                    break
            if match is None:
                raise AssertionError(
                    f"no graphical mapping for province {title.province_id} "
                    f"({title.barony})"
                )
            assigned_mapping[title.province_id] = match
            used_mappings[(match.scope, match.key)] += 1
        unused_mappings = set(mapping_by_scope_key) - set(used_mappings)
        if unused_mappings:
            raise AssertionError(
                f"unused graphical mappings: {sorted(unused_mappings)}"
            )

        self.graphical_pending: list[str] = []
        mapping_components: dict[tuple[str, str], dict[int, int]] = {}
        for mapping in mappings:
            mapped_ids = {
                province_id
                for province_id, assigned in assigned_mapping.items()
                if assigned == mapping
            }
            components = connected_components(mapped_ids, self.adjacency)
            mapping_components[(mapping.scope, mapping.key)] = components
            component_count = max(components.values(), default=0)
            if component_count > 1 and not mapping.allow_disconnected:
                self.graphical_pending.append(
                    f"{mapping.scope}:{mapping.key} has {component_count} components"
                )

        self.assigned_style = {
            province_id: mapping.graphical_region
            for province_id, mapping in assigned_mapping.items()
        }
        self.targets_by_title: dict[str, dict[str, set[int]]] = {
            scope: defaultdict(set) for scope in MEMBERSHIP_KEYS.values()
        }
        for title in self.graphical_titles:
            for scope in MEMBERSHIP_KEYS.values():
                self.targets_by_title[scope][title.value_for_scope(scope)].add(
                    title.province_id
                )

        self.style_to_ids: dict[str, set[int]] = defaultdict(set)
        for province_id, mapping in assigned_mapping.items():
            self.style_to_ids[mapping.graphical_region].add(province_id)
        if set().union(*self.style_to_ids.values()) != {
            row.province_id for row in self.graphical_titles
        }:
            raise AssertionError("graphical target coverage is incomplete")
        if sum(len(values) for values in self.style_to_ids.values()) != len(
            self.graphical_titles
        ):
            raise AssertionError("a graphical target was assigned more than once")

        style_components = {
            style: connected_components(province_ids, self.adjacency)
            for style, province_ids in self.style_to_ids.items()
        }
        self.graphical_audit_rows: list[dict[str, object]] = []
        for title in self.graphical_titles:
            mapping = assigned_mapping[title.province_id]
            components = mapping_components[(mapping.scope, mapping.key)]
            component_count = max(components.values(), default=0)
            warning = ""
            review_status = "reviewed"
            if component_count > 1:
                warning = f"mapping_has_{component_count}_components"
                review_status = (
                    "approved_disconnected" if mapping.allow_disconnected else "pending"
                )
            self.graphical_audit_rows.append(
                {
                    "province_id": title.province_id,
                    "rgb": self.eep_definitions[title.province_id].rgb_text,
                    "barony": title.barony,
                    "county": title.county,
                    "duchy": title.duchy,
                    "kingdom": title.kingdom,
                    "empire": title.empire,
                    "graphical_region": mapping.graphical_region,
                    "mapping_scope": mapping.scope,
                    "mapping_key": mapping.key,
                    "component_id": components[title.province_id],
                    "style_component_id": style_components[mapping.graphical_region][
                        title.province_id
                    ],
                    "adjacency_warning": warning,
                    "review_status": review_status,
                    "reason": mapping.reason,
                }
            )

    def named_member_coverage(self, key: str, member: str) -> set[int]:
        """Return the target provinces one named membership entry covers.

        Only target provinces matter here. Everything else a `duchies` or
        `regions` entry pulls in lies outside the classified range and keeps its
        own author's style, so this module neither moves nor re-lists it.
        """
        if key in MEMBERSHIP_KEYS:
            return set(self.targets_by_title[MEMBERSHIP_KEYS[key]].get(member, set()))
        return self.region_coverage(member, frozenset())

    def region_coverage(self, name: str, seen: frozenset[str]) -> set[int]:
        """Return the target provinces a named region covers, following `regions`."""
        if name in seen:
            return set()
        block = self.region_blocks.get(name)
        if block is None:
            raise AssertionError(f"region {name} is referenced but not defined")
        covered = block_province_ids(block) & set(self.assigned_style)
        for key in (*MEMBERSHIP_KEYS, "regions"):
            for member in block_members(block, key):
                if key == "regions":
                    covered |= self.region_coverage(member, seen | {name})
                else:
                    covered |= self.named_member_coverage(key, member)
        return covered

    def build_graphical_block(self, style: str) -> str:
        """Rebuild one graphical region as a complete replacement.

        The inherited block already covers the whole map, so this keeps every
        membership entry that only reaches provinces outside the classified
        range or provinces this run still assigns to `style`, and drops the
        entries whose target provinces moved to another style. The province list
        is then rewritten to the ids that are neither reassigned away nor
        already covered by a retained entry, which is what keeps a province from
        appearing in two regions or twice in one.
        """
        block = repair_inherited_graphical_block(style, self.graphical_blocks[style])
        assigned = self.style_to_ids[style]
        retained_coverage: set[int] = set()
        for key in (*MEMBERSHIP_KEYS, "regions"):
            dropped: set[str] = set()
            for member in block_members(block, key):
                covered = self.named_member_coverage(key, member)
                if not covered:
                    continue
                if covered <= assigned:
                    retained_coverage |= covered
                elif covered.isdisjoint(assigned):
                    dropped.add(member)
                else:
                    raise AssertionError(
                        f"{style} {key} entry {member} straddles the graphical "
                        f"reassignment: {len(covered & assigned)} of "
                        f"{len(covered)} target provinces stay; split the entry "
                        "or re-audit the mapping"
                    )
            if dropped:
                block = remove_block_members(block, key, dropped)
        kept_ids = {
            province_id
            for province_id in block_province_ids(block)
            if self.assigned_style.get(province_id, style) == style
        }
        return set_block_provinces(block, (kept_ids | assigned) - retained_coverage)

    def assert_graphical_blocks_disjoint(self, emitted: dict[str, str]) -> None:
        """Fail unless every target province is expressed once, in one style.

        CK3 reports the two ways this can go wrong as `Province 'N' lies in
        multiple graphical regions` and `Region 'N' has multiple entries for the
        province 'N'`, both at world init, and resolves an ambiguous province to
        whichever style it reaches first.
        """
        seen: dict[int, str] = {}
        for style, block in emitted.items():
            explicit = block_province_ids(block)
            named: set[int] = set()
            for key in (*MEMBERSHIP_KEYS, "regions"):
                for member in block_members(block, key):
                    covered = self.named_member_coverage(key, member)
                    twice = covered & (named | explicit)
                    if twice:
                        raise AssertionError(
                            f"{style} lists {len(twice)} target province(s) "
                            f"twice, including {min(twice)}, via {key} entry "
                            f"{member}"
                        )
                    named |= covered
            for province_id in (explicit & set(self.assigned_style)) | named:
                owner = seen.setdefault(province_id, style)
                if owner != style:
                    raise AssertionError(
                        f"target province {province_id} is in both {owner} and {style}"
                    )
        if seen != self.assigned_style:
            missing = sorted(set(self.assigned_style) - set(seen))
            wrong = sorted(
                province_id
                for province_id, style in seen.items()
                if self.assigned_style.get(province_id) != style
            )
            raise AssertionError(
                "emitted graphical regions do not reproduce the assignment: "
                f"{len(missing)} missing (e.g. {missing[:5]}), "
                f"{len(wrong)} misplaced (e.g. {wrong[:5]})"
            )

    def write_outputs(self) -> None:
        terrain_audit = csv_bytes(
            [
                "province_id",
                "rgb",
                "barony",
                "county",
                "duchy",
                "kingdom",
                "empire",
                "model_terrain",
                "proposed_terrain",
                "eep_terrain",
                "final_terrain",
                "model_confidence",
                "model_runner_up",
                "model_margin",
                "model_priority_group",
                "model_warning",
                "lore_base",
                "lore_forest",
                "lore_google_green",
                "lore_arid",
                "lore_google_mountain",
                "slope",
                "lore_reason",
                "leading_masks",
                "water_class",
                "review_reason",
                "decision",
                "decision_reason",
                "review_status",
            ],
            self.terrain_audit_rows,
        )
        graphical_audit = csv_bytes(
            [
                "province_id",
                "rgb",
                "barony",
                "county",
                "duchy",
                "kingdom",
                "empire",
                "graphical_region",
                "mapping_scope",
                "mapping_key",
                "component_id",
                "style_component_id",
                "adjacency_warning",
                "review_status",
                "reason",
            ],
            self.graphical_audit_rows,
        )

        gap_ids = sorted(set(self.final_terrain) - set(self.upstream_terrain))
        if len(gap_ids) != EXPECTED_GAP_COUNT:
            raise AssertionError(
                "upstream terrain coverage changed: this module would fill "
                f"{len(gap_ids)} provinces, not {EXPECTED_GAP_COUNT}"
            )
        if set(gap_ids) & set(self.upstream_terrain):
            raise AssertionError("gap output would override an upstream terrain")

        terrain_lines = [
            "\ufeff# Generated by ck3mm from the mod's workspace implementation.",
            "# Final terrain uses aligned lore-map biomes, slope relief, and "
            "strong semantic masks.",
            f"# Audit-only mask-model spatial five-fold macro-F1: {self.validation_f1:.6f}",
            "# Training labels: "
            + ", ".join(f"{name}={self.label_counts[name]}" for name in self.classes),
            f"# Classified IDs: {TARGET_FIRST}..{TARGET_LAST} ({TARGET_COUNT})",
            "",
            "# This file does not override any upstream terrain file. It emits only",
            "# the provinces no effective module assigns a real terrain to; every",
            "# other id keeps the value its own author chose.",
            f"# Gap-filled IDs: {len(gap_ids)}",
            "",
        ]
        terrain_lines.extend(
            f"{province_id} = {self.final_terrain[province_id]}"
            for province_id in gap_ids
        )
        terrain_output = ("\n".join(terrain_lines) + "\n").encode("utf-8")

        region_lines = [
            "\ufeff# Generated by ck3mm from the mod's workspace implementation.",
            "# Complete replacements for touched graphical-region keys.",
            "",
        ]
        emitted = {
            style: self.build_graphical_block(style) for style in self.style_to_ids
        }
        self.assert_graphical_blocks_disjoint(emitted)
        for style in sorted(emitted):
            region_lines.append(emitted[style])
            region_lines.append("")
        region_output = ("\n".join(region_lines)).encode("utf-8")

        outputs = {
            self.source / "terrain_audit.csv": terrain_audit,
            self.source / "graphical_region_audit.csv": graphical_audit,
            self.module / TERRAIN_OUTPUT: terrain_output,
            self.module
            / "map_data/geographical_regions/zzzz_agot_now_lov_ee_world_data.txt": region_output,
        }

        if self.pending:
            raise AssertionError(
                f"{len(self.pending)} terrain provinces require decisions; "
                "review and update terrain_decisions.csv"
            )
        if self.graphical_pending:
            raise AssertionError(
                "graphical mappings require disconnected-component review: "
                + "; ".join(self.graphical_pending)
            )
        if set(self.final_terrain) != self.expected_ids:
            raise AssertionError("terrain output does not cover the full target range")
        if any(terrain == "default" for terrain in self.final_terrain.values()):
            raise AssertionError("terrain output still contains default")
        for province_id in self.expected_ids & self.water_ids:
            if self.final_terrain[province_id] not in {"sea", "coastal_sea"}:
                raise AssertionError(f"water province {province_id} has land terrain")

        for path, data in outputs.items():
            self.context.write_bytes(path.relative_to(self.module), data)
            print(f"Wrote {path.relative_to(self.root)}")
        print(
            f"Generated terrain={TARGET_COUNT}, graphical={len(self.graphical_titles)}, "
            f"macro-F1={self.validation_f1:.4f}"
        )
        return None


def generate(context: GenerationContext) -> None:
    WorldDataPipeline(context).run()
