#!/usr/bin/env python3
"""Generate terrain and graphical-region data for AGOT/NOW/LoV/EE."""

from __future__ import annotations

import csv
import fnmatch
import hashlib
import io
import json
import re
import sys
import tomllib
from collections import Counter, defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image

from gen import GenerationContext
from gen.hashing import sha256_file
from gen.sources import canonical_source_path

TARGET_FIRST = 10946
TARGET_LAST = 26420
TARGET_COUNT = TARGET_LAST - TARGET_FIRST + 1
EXPECTED_TITLE_COUNT = 13270
EXPECTED_MASK_COUNT = 188
EXPECTED_SIZE = (9216, 6144)
REFERENCE_ANALYSIS_SIZE = (2304, 1536)
REFERENCE_EXPECTED_SIZES = {
    "detailed": (7400, 4932),
    "google": (3400, 2267),
}
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
OUTPUT_ROOT_OVERRIDE: Path | None = None
ASSETS_DIR_OVERRIDE: Path | None = None
MAP_DEFINITION_OVERRIDE: Path | None = None
REFERENCE_PATHS_OVERRIDE: dict[str, Path] | None = None


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


def normalized_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig").replace("\r\n", "\n")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def bool_value(value: str, *, field: str) -> bool:
    lowered = value.strip().lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    raise ValueError(f"{field}: expected true or false, got {value!r}")


def parse_definitions(path: Path) -> list[Definition]:
    rows: list[Definition] = []
    for line_number, line in enumerate(normalized_text(path).splitlines(), 1):
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

    if len(rows) != TARGET_LAST + 1:
        raise AssertionError(
            f"definition row count changed: {len(rows)} != {TARGET_LAST + 1}"
        )
    ids = [row.province_id for row in rows]
    if ids != list(range(TARGET_LAST + 1)):
        raise AssertionError("definition IDs are no longer contiguous 0..26420")
    packed = [row.packed_rgb for row in rows]
    if len(packed) != len(set(packed)):
        duplicates = [rgb for rgb, count in Counter(packed).items() if count > 1]
        raise AssertionError(f"duplicate definition RGB values: {duplicates[:10]}")
    return rows


def parse_scalar_terrain(path: Path) -> dict[int, str]:
    result: dict[int, str] = {}
    pattern = re.compile(r"^\s*(\d+)\s*=\s*([a-z][a-z0-9_]*)\s*(?:#.*)?$")
    for line in normalized_text(path).splitlines():
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
            for line in normalized_text(path).splitlines():
                if match := pattern.match(line):
                    keys.add(match.group(1))
    return keys


def parse_default_map(path: Path) -> tuple[set[int], set[int], set[int]]:
    categories = {"sea_zones": set(), "river_provinces": set(), "lakes": set()}
    pattern = re.compile(
        r"^\s*(sea_zones|river_provinces|lakes)\s*=\s*" r"(LIST|RANGE)\s*\{([^}]*)\}"
    )
    for line in normalized_text(path).splitlines():
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
    return (
        categories["sea_zones"],
        categories["river_provinces"],
        categories["lakes"],
    )


def parse_titles(
    path: Path, *, require_unique_provinces: bool = True
) -> list[TitleRow]:
    title_pattern = re.compile(r"^\s*([ekdcb]_[A-Za-z0-9_]+)\s*=\s*\{")
    province_pattern = re.compile(r"^\s*province\s*=\s*(\d+)\b")
    stack: list[tuple[str, int]] = []
    depth = 0
    rows: list[TitleRow] = []

    for raw_line in normalized_text(path).splitlines():
        line = raw_line.split("#", 1)[0]
        while stack and depth < stack[-1][1]:
            stack.pop()
        if title_match := title_pattern.match(line):
            stack.append((title_match.group(1), depth + 1))
        if province_match := province_pattern.match(line):
            ancestry: dict[str, str] = {}
            for title, _ in stack:
                ancestry[title[0]] = title
            required = set("ekdcb")
            if set(ancestry) != required:
                raise AssertionError(
                    f"incomplete title ancestry for province {province_match.group(1)}: "
                    f"{ancestry}"
                )
            rows.append(
                TitleRow(
                    int(province_match.group(1)),
                    ancestry["e"],
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
    data = tomllib.loads(normalized_text(path))
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
        expected = {
            "scope",
            "key",
            "graphical_region",
            "allow_disconnected",
            "reason",
        }
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
    count = np.bincount(flat, minlength=TARGET_LAST + 1).astype(np.int64)
    sum_x = np.zeros(TARGET_LAST + 1, dtype=np.float64)
    sum_y = np.zeros(TARGET_LAST + 1, dtype=np.float64)
    width, height = EXPECTED_SIZE
    x_values = np.arange(width, dtype=np.float64)
    for y0 in range(0, height, 256):
        chunk = id_raster[y0 : y0 + 256]
        rows = chunk.shape[0]
        chunk_flat = chunk.ravel()
        sum_x += np.bincount(
            chunk_flat,
            weights=np.tile(x_values, rows),
            minlength=TARGET_LAST + 1,
        )
        sum_y += np.bincount(
            chunk_flat,
            weights=np.repeat(np.arange(y0, y0 + rows, dtype=np.float64), width),
            minlength=TARGET_LAST + 1,
        )
    centroid_x = np.full(TARGET_LAST + 1, -1.0, dtype=np.float64)
    centroid_y = np.full(TARGET_LAST + 1, -1.0, dtype=np.float64)
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
    intensity = np.bincount(flat_ids, weights=flat_values, minlength=TARGET_LAST + 1)
    coverage = np.bincount(flat_ids[nonzero], minlength=TARGET_LAST + 1).astype(
        np.float64
    )
    strong_coverage = np.bincount(flat_ids[strong], minlength=TARGET_LAST + 1).astype(
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
    target_ids: np.ndarray,
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
            flat_ids,
            weights=elevation_pixels.ravel(),
            minlength=TARGET_LAST + 1,
        )
        / safe_area
    ).astype(np.float32)
    high_elevation = (
        np.bincount(
            flat_ids[elevation_pixels.ravel() >= 0.55],
            minlength=TARGET_LAST + 1,
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
        np.bincount(
            flat_ids,
            weights=slope_pixels.ravel(),
            minlength=TARGET_LAST + 1,
        )
        / safe_area
    ).astype(np.float32)
    high_slope = (
        np.bincount(
            flat_ids[slope_pixels.ravel() >= 0.015],
            minlength=TARGET_LAST + 1,
        )
        / safe_area
    ).astype(np.float32)
    del slope_pixels

    gameplay_groups = [group for group in groups if group.role == "gameplay"]
    group_index = {group.name: index for index, group in enumerate(gameplay_groups)}
    shape = (len(gameplay_groups), TARGET_LAST + 1)
    group_intensity = np.zeros(shape, dtype=np.float32)
    group_coverage = np.zeros(shape, dtype=np.float32)
    group_strong = np.zeros(shape, dtype=np.float32)
    gameplay_masks = [
        path
        for path in mask_paths
        if mask_to_group[path.relative_to(terrain_root).as_posix()].role == "gameplay"
    ]
    mask_shape = (len(gameplay_masks), TARGET_LAST + 1)
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
    reference_area = np.bincount(reference_flat_ids, minlength=TARGET_LAST + 1).astype(
        np.float64
    )
    reference_safe_area = np.maximum(reference_area, 1)

    def aggregate_reference(values: np.ndarray) -> np.ndarray:
        return (
            np.bincount(
                reference_flat_ids,
                weights=values.astype(np.float32, copy=False).ravel(),
                minlength=TARGET_LAST + 1,
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
    *,
    cache_dir: Path,
    cache_key: str,
    no_cache: bool,
    **kwargs: object,
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


def build_model_features(
    features: dict[str, np.ndarray], gameplay_groups: list[MaskGroup]
) -> np.ndarray:
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
                standardized[training],
                labels[training],
                len(classes),
                penalty,
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
                    np.clip(
                        probabilities[np.arange(len(labels)), labels],
                        1e-12,
                        1.0,
                    )
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
            result.update(parse_top_level_blocks(normalized_text(path)))
    return result


def direct_graphical_flag(block: str) -> bool:
    return bool(re.search(r"(?m)^\s*graphical\s*=\s*yes\s*(?:#.*)?$", block))


def append_provinces_to_block(block: str, province_ids: Iterable[int]) -> str:
    province_ids = sorted(set(province_ids))
    property_pattern = re.compile(r"(?ms)^([ \t]+)provinces\s*=\s*\{(.*?)^\1\}")
    match = property_pattern.search(block)
    existing: set[int] = set()
    if match:
        existing.update(
            int(value)
            for value in re.findall(r"(?m)(?<![A-Za-z0-9_])\d+", match.group(2))
        )
    combined = sorted(existing | set(province_ids))
    lines = [
        "\tprovinces = {",
        *[
            "\t\t" + " ".join(str(value) for value in combined[offset : offset + 16])
            for offset in range(0, len(combined), 16)
        ],
        "\t}",
    ]
    replacement = "\n".join(lines)
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


def csv_bytes(fieldnames: list[str], rows: Iterable[dict[str, object]]) -> bytes:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue().encode("utf-8")


def reference_map_paths(root: Path) -> dict[str, Path]:
    if REFERENCE_PATHS_OVERRIDE is not None:
        return REFERENCE_PATHS_OVERRIDE
    reference_root = root / "references/agot/map_images"
    return {
        "detailed": reference_root / "KnownWorldDetailed.jpg",
        "google": reference_root / "KnownWorldGoogleMaps.jpg",
    }


def target_source_manifest(
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
        MAP_DEFINITION_OVERRIDE
        or root / "mods/agot_now_lov_ee_map_compatch/map_data/definition.csv",
    }
    source_files.update(reference_map_paths(root).values())
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
    versions: dict[str, str] = {}
    for label, module_root in workshop.items():
        descriptor = module_root / "descriptor.mod"
        if descriptor.is_file():
            match = re.search(
                r'(?m)^\s*version\s*=\s*"([^"]+)"', normalized_text(descriptor)
            )
            versions[label] = match.group(1) if match else "unversioned"
    return {
        "schema_version": 2,
        "workshop_ids": WORKSHOP_IDS,
        "versions": versions,
        "expected": {
            "definition_rows": TARGET_LAST + 1,
            "target_first": TARGET_FIRST,
            "target_last": TARGET_LAST,
            "target_count": TARGET_COUNT,
            "title_count": EXPECTED_TITLE_COUNT,
            "mask_count": EXPECTED_MASK_COUNT,
            "image_width": EXPECTED_SIZE[0],
            "image_height": EXPECTED_SIZE[1],
        },
        "files": files,
        "terrain_masks": masks,
    }


@dataclass(frozen=True, slots=True)
class Options:
    """Everything one generation run needs that is not a declared source."""

    root: Path
    workshop_root: Path
    check: bool = False
    update_source_manifest: bool = False
    audit: bool = False
    no_cache: bool = False


def main(options: Options) -> int:
    root = options.root.resolve()
    workshop_root = options.workshop_root
    workshop = {
        label: workshop_root / workshop_id
        for label, workshop_id in WORKSHOP_IDS.items()
    }
    missing_modules = [
        f"{label}:{path}" for label, path in workshop.items() if not path.is_dir()
    ]
    if missing_modules:
        raise FileNotFoundError(f"missing Workshop modules: {missing_modules}")

    module = OUTPUT_ROOT_OVERRIDE or root / "mods/agot_now_lov_ee_world_data"
    tooling = root / "workspace/agot_now_lov_ee_world_data"
    # Audits are development artifacts: staged under the reserved artifacts/
    # prefix, promoted into the tooling tree, never installed into CK3.
    artifacts = (module if OUTPUT_ROOT_OVERRIDE else tooling) / "artifacts"
    source = artifacts / "world_data"
    assets = ASSETS_DIR_OVERRIDE or tooling / "assets/world_data"
    mask_config_path = assets / "terrain_mask_groups.toml"
    decisions_path = assets / "terrain_decisions.csv"
    lore_regions_path = assets / "terrain_lore_regions.csv"
    graphical_config_path = assets / "graphical_style_map.csv"
    manifest_path = assets / "source_manifest.json"
    reference_paths = reference_map_paths(root)
    missing_reference_maps = [
        path.relative_to(root).as_posix()
        for path in reference_paths.values()
        if not path.is_file()
    ]
    if missing_reference_maps:
        raise FileNotFoundError(
            f"missing lore reference maps: {missing_reference_maps}"
        )
    terrain_root = workshop["EE"] / "gfx/map/terrain"
    mask_paths = sorted(terrain_root.rglob("*_mask.png"))
    if len(mask_paths) != EXPECTED_MASK_COUNT:
        raise AssertionError(
            f"terrain mask count changed: {len(mask_paths)} != {EXPECTED_MASK_COUNT}"
        )
    groups, mask_to_group = load_mask_groups(mask_config_path, mask_paths, terrain_root)
    gameplay_groups = [group for group in groups if group.role == "gameplay"]

    ee_definitions = parse_definitions(workshop["EE"] / "map_data/definition.csv")
    merged_definitions = parse_definitions(
        MAP_DEFINITION_OVERRIDE
        or root / "mods/agot_now_lov_ee_map_compatch/map_data/definition.csv"
    )
    eep_definitions = parse_definitions(workshop["EEP"] / "map_data/definition.csv")
    for province_id in range(TARGET_FIRST, TARGET_LAST + 1):
        if eep_definitions[province_id] != merged_definitions[province_id]:
            raise AssertionError(
                f"map compatch changed TempLoV target definition row {province_id}"
            )
        if (
            ee_definitions[province_id].packed_rgb
            == eep_definitions[province_id].packed_rgb
        ):
            continue
        if ee_definitions[province_id].name == eep_definitions[province_id].name:
            continue
        if (
            province_id != 26357
            or ee_definitions[province_id].name != "LAKE"
            or eep_definitions[province_id].name != "IMPASSABLE_RIDGE"
        ):
            raise AssertionError(
                f"TempLoV recoloured target row {province_id} beyond its colour"
            )

    ee_terrain = parse_scalar_terrain(
        workshop["EE"] / "common/province_terrain/ee_province_terrain.txt"
    )
    eep_terrain = parse_scalar_terrain(
        workshop["EEP"] / "common/province_terrain/ee_province_terrain.txt"
    )
    expected_ids = set(range(TARGET_FIRST, TARGET_LAST + 1))
    ee_defaults = {
        province_id
        for province_id, terrain in ee_terrain.items()
        if terrain == "default" and province_id in expected_ids
    }
    if ee_defaults != expected_ids:
        raise AssertionError(
            f"EE unfinished terrain set changed: {len(ee_defaults)} target defaults"
        )
    # TempLoV compatch 2.5.0 replaced its blanket `plains` placeholder with real
    # authored terrain for the east.  Those authored assignments are the
    # effective upstream decision and win over this module's lore-map proposal;
    # provinces the compatch still leaves at `plains` are the remaining
    # placeholder and keep the generated terrain.
    eep_authored = {
        province_id: terrain
        for province_id, terrain in eep_terrain.items()
        if province_id in expected_ids and terrain != "plains"
    }
    eep_placeholder = {
        province_id
        for province_id, terrain in eep_terrain.items()
        if province_id in expected_ids and terrain == "plains"
    }
    if not eep_authored:
        raise AssertionError(
            "TempLoV compatch no longer authors any non-plains target terrain"
        )
    if eep_authored.keys() & eep_placeholder:
        raise AssertionError("TempLoV target terrain is both authored and placeholder")

    ee_titles = [
        row
        for row in parse_titles(
            workshop["EEP"] / "common/landed_titles/01_landed_titles.txt"
        )
        if TARGET_FIRST <= row.province_id <= TARGET_LAST
    ]
    if len(ee_titles) != EXPECTED_TITLE_COUNT:
        raise AssertionError(
            f"EE titled province count changed: {len(ee_titles)} "
            f"!= {EXPECTED_TITLE_COUNT}"
        )
    if any(row.province_id not in expected_ids for row in ee_titles):
        raise AssertionError("EE landed titles reference an out-of-range province")
    empire_keys = {row.empire for row in ee_titles}
    if len(empire_keys) != 27:
        raise AssertionError(f"EE empire scope count changed: {len(empire_keys)}")
    lore_regions = load_lore_regions(lore_regions_path)
    if set(lore_regions) != empire_keys:
        raise AssertionError(
            "lore-region empire mappings changed: "
            f"missing={sorted(empire_keys - set(lore_regions))}, "
            f"extra={sorted(set(lore_regions) - empire_keys)}"
        )

    now_titles = parse_titles(
        workshop["NOW"] / "common/landed_titles/01_agot_landed_titles.txt",
        require_unique_provinces=False,
    )
    rutting_titles = [row for row in now_titles if row.county == "c_rutting"]
    if {row.province_id for row in rutting_titles} != set(RUTTING_IDS):
        raise AssertionError(
            f"c_rutting province set changed: "
            f"{sorted(row.province_id for row in rutting_titles)}"
        )
    graphical_titles = sorted(
        [*ee_titles, *rutting_titles], key=lambda row: row.province_id
    )

    with Image.open(workshop["EEP"] / "map_data/provinces.png") as image:
        if image.size != EXPECTED_SIZE or image.mode != "RGB":
            raise AssertionError(
                f"unexpected provinces image: size={image.size}, mode={image.mode}"
            )
    with Image.open(workshop["EEP"] / "map_data/heightmap.png") as image:
        if image.size != EXPECTED_SIZE or image.mode not in {"I;16", "I;16L", "I"}:
            raise AssertionError(
                f"unexpected heightmap image: size={image.size}, mode={image.mode}"
            )

    current_manifest = target_source_manifest(
        root=root,
        workshop=workshop,
        workshop_root=workshop_root,
        mask_paths=mask_paths,
    )
    if options.update_source_manifest:
        # The full painted-color assertion is intentionally part of accepting a
        # new source baseline, not merely a hash refresh.
        _, area, _, _ = build_id_raster(
            eep_definitions, workshop["EEP"] / "map_data/provinces.png"
        )
        unpainted_titles = [
            row.province_id for row in ee_titles if area[row.province_id] == 0
        ]
        if unpainted_titles:
            raise AssertionError(
                f"EE titled provinces have no painted pixels: {unpainted_titles[:10]}"
            )
        manifest_path.write_text(
            json.dumps(current_manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print(f"Updated {manifest_path.relative_to(root)}")
        return 0

    if not manifest_path.is_file():
        raise FileNotFoundError(
            f"{manifest_path} does not exist; run --update-source-manifest "
            "after reviewing the current inputs"
        )
    recorded_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if recorded_manifest != current_manifest:
        raise AssertionError(
            "upstream source manifest drifted; review the source changes and run "
            "--update-source-manifest"
        )

    id_raster, area, centroid_x, centroid_y = build_id_raster(
        eep_definitions, workshop["EEP"] / "map_data/provinces.png"
    )
    unpainted_titles = [
        row.province_id for row in graphical_titles if area[row.province_id] == 0
    ]
    if unpainted_titles:
        raise AssertionError(
            f"graphical target provinces have no painted pixels: "
            f"{unpainted_titles[:10]}"
        )
    pairs = adjacency_pairs(id_raster)
    adjacency: dict[int, set[int]] = defaultdict(set)
    for first, second in pairs:
        adjacency[first].add(second)
        adjacency[second].add(first)

    sea_zones, river_provinces, lakes = parse_default_map(
        workshop["EEP"] / "map_data/default.map"
    )
    water_ids = sea_zones | river_provinces | lakes
    target_ids = np.arange(TARGET_FIRST, TARGET_LAST + 1, dtype=np.int32)
    cache_key = feature_cache_key(current_manifest, mask_config_path)
    features = load_or_compute_features(
        cache_dir=root / ".ignored/cache/agot_now_lov_ee_world_data",
        cache_key=cache_key,
        no_cache=options.no_cache,
        heightmap_path=workshop["EEP"] / "map_data/heightmap.png",
        mask_paths=mask_paths,
        terrain_root=terrain_root,
        groups=groups,
        mask_to_group=mask_to_group,
        id_raster=id_raster,
        area=area,
        target_ids=target_ids,
        reference_paths=reference_paths,
    )
    if list(features["group_names"]) != [group.name for group in gameplay_groups]:
        raise AssertionError("feature cache mask-group order mismatch")

    terrain_modules = [
        workshop["AGOT"],
        workshop["NOW"],
        workshop["LOV"],
        workshop["RC"],
        workshop["EE"],
        workshop["EEP"],
    ]
    terrain_by_province = terrain_winners(terrain_modules)
    valid_terrains = terrain_type_keys(terrain_modules)
    gameplay_terrains = {
        group.terrain for group in gameplay_groups if group.terrain is not None
    }
    missing_terrain_types = gameplay_terrains - valid_terrains
    if missing_terrain_types:
        raise AssertionError(
            f"configured terrain types are not loaded: {sorted(missing_terrain_types)}"
        )
    lore_terrains = {region.base_terrain for region in lore_regions.values()} | {
        region.wooded_terrain
        for region in lore_regions.values()
        if region.wooded_terrain
    }
    missing_lore_terrains = lore_terrains - valid_terrains
    if missing_lore_terrains:
        raise AssertionError(
            f"configured lore terrain types are not loaded: "
            f"{sorted(missing_lore_terrains)}"
        )
    model_features = build_model_features(features, gameplay_groups)
    (
        classes,
        feature_mean,
        feature_scale,
        model_weights,
        label_counts,
        validation_f1,
        confidence_thresholds,
        logit_scale,
    ) = train_terrain_model(
        model_features=model_features,
        terrain_by_province=terrain_by_province,
        water_ids=water_ids,
        centroid_x=centroid_x,
        centroid_y=centroid_y,
        valid_terrains=valid_terrains,
        gameplay_terrains=gameplay_terrains,
    )
    standardized_targets = (model_features[target_ids] - feature_mean) / feature_scale
    probabilities = softmax(
        predict_scores(standardized_targets, model_weights) * logit_scale
    )
    best_indices = np.argmax(probabilities, axis=1)
    sorted_probabilities = np.sort(probabilities, axis=1)
    confidences = sorted_probabilities[:, -1]
    margins = sorted_probabilities[:, -1] - sorted_probabilities[:, -2]

    group_index = {group.name: index for index, group in enumerate(gameplay_groups)}
    proposed: dict[int, str] = {}
    review_reasons: dict[int, list[str]] = defaultdict(list)
    runner_up: dict[int, str] = {}
    confidence_by_id: dict[int, float] = {}
    margin_by_id: dict[int, float] = {}
    priority_group_by_id: dict[int, str] = {}
    water_class_by_id: dict[int, str] = {}

    for offset, province_id_raw in enumerate(target_ids):
        province_id = int(province_id_raw)
        if province_id in lakes or province_id in river_provinces:
            proposed[province_id] = "sea"
            water_class_by_id[province_id] = "lake" if province_id in lakes else "river"
            runner_up[province_id] = ""
            confidence_by_id[province_id] = 1.0
            margin_by_id[province_id] = 1.0
            continue
        if province_id in sea_zones:
            touches_land = any(
                neighbor not in water_ids for neighbor in adjacency.get(province_id, ())
            )
            proposed[province_id] = "coastal_sea" if touches_land else "sea"
            water_class_by_id[province_id] = "coastal_sea" if touches_land else "sea"
            runner_up[province_id] = ""
            confidence_by_id[province_id] = 1.0
            margin_by_id[province_id] = 1.0
            continue

        class_index = int(best_indices[offset])
        model_terrain = classes[class_index]
        selected = model_terrain
        priority_candidates: list[tuple[float, MaskGroup]] = []
        for group in gameplay_groups:
            if group.priority_threshold is None:
                continue
            intensity = float(
                features["group_intensity"][group_index[group.name], province_id]
            )
            if intensity >= group.priority_threshold:
                priority_candidates.append((intensity * group.weight, group))
        if priority_candidates:
            _, priority_group = max(
                priority_candidates, key=lambda value: (value[0], value[1].name)
            )
            priority_group_by_id[province_id] = priority_group.name
            if priority_group.terrain != model_terrain:
                selected = str(priority_group.terrain)
                review_reasons[province_id].append(
                    f"priority:{priority_group.name}_over_{model_terrain}"
                )

        proposed[province_id] = selected
        order = np.argsort(probabilities[offset])
        runner_up[province_id] = classes[int(order[-2])]
        confidence_by_id[province_id] = float(confidences[offset])
        margin_by_id[province_id] = float(margins[offset])
        if confidences[offset] < confidence_thresholds[class_index]:
            review_reasons[province_id].append("below_95pct_precision_threshold")
        if margins[offset] < 0.10:
            review_reasons[province_id].append("top_two_margin_below_0.10")

    model_proposed = dict(proposed)
    model_review_reasons = review_reasons
    title_by_id = {row.province_id: row for row in ee_titles}
    proposed = {}
    review_reasons = defaultdict(list)
    lore_base_by_id: dict[int, str] = {}
    lore_reason_by_id: dict[int, str] = {}
    group_intensity = features["group_intensity"]

    for province_id in sorted(expected_ids):
        if province_id in water_ids:
            proposed[province_id] = model_proposed[province_id]
            lore_base_by_id[province_id] = model_proposed[province_id]
            lore_reason_by_id[province_id] = "Water class from EE default.map."
            continue

        title = title_by_id.get(province_id)
        region = lore_regions.get(title.empire) if title else None
        forest_signal = float(features["lore_forest"][province_id])
        deep_forest_signal = float(features["lore_deep_forest"][province_id])
        google_green_signal = float(features["lore_google_green"][province_id])
        arid_signal = float(features["lore_arid"][province_id])
        red_desert_signal = float(features["lore_red_desert"][province_id])
        dark_signal = float(features["lore_dark"][province_id])
        snow_signal = float(features["lore_snow"][province_id])
        google_mountain_signal = float(features["lore_google_mountain"][province_id])
        slope = float(features["slope"][province_id])
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

        desert_intensity = float(group_intensity[group_index["desert"], province_id])
        desert_mountain_intensity = float(
            group_intensity[group_index["desert_mountains"], province_id]
        )
        if base == "drylands" and (
            red_desert_signal >= 0.28 or desert_intensity >= 0.50
        ):
            base = "desert"
            evidence.append("strong_desert_evidence")

        special: str | None = None
        if float(group_intensity[group_index["oasis"], province_id]) >= 0.08:
            special = "oasis"
        elif (
            float(group_intensity[group_index["floodplains"], province_id]) >= 0.16
            and slope < 0.003
        ):
            special = "floodplains"
        elif (
            float(group_intensity[group_index["wetlands"], province_id]) >= 0.24
            and slope < 0.003
        ):
            special = "wetlands"
        elif float(group_intensity[group_index["jungle"], province_id]) >= 0.18:
            special = "jungle"
        elif float(group_intensity[group_index["frozen"], province_id]) >= 0.30 or (
            title and title.empire == "e_ibben" and snow_signal >= 0.45
        ):
            special = "frozen_flats"
        elif float(group_intensity[group_index["farmlands"], province_id]) >= 0.45 and (
            not title or title.empire != "e_ibben"
        ):
            special = "farmlands"
        if special:
            base = special
            evidence.append(f"strong_mask={special}")

        wooded_strength = max(
            forest_signal,
            deep_forest_signal,
            google_green_signal,
        )
        volcanic_intensity = float(
            group_intensity[group_index["volcanic"], province_id]
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

        proposed[province_id] = selected
        lore_base_by_id[province_id] = base
        lore_reason_by_id[province_id] = "|".join(evidence)

    decisions = load_terrain_decisions(decisions_path)
    unknown_decision_ids = set(decisions) - expected_ids
    if unknown_decision_ids:
        raise AssertionError(
            f"terrain decisions reference non-target IDs: "
            f"{sorted(unknown_decision_ids)[:10]}"
        )
    final_terrain = dict(proposed)
    # Defer to the TempLoV compatch's authored terrain before applying local
    # exceptions, but never override this module's water classes: the compatch
    # lists only land provinces, while `proposed` also carries EE's sea and
    # coastal-sea assignments from `default.map`.
    eep_applied = 0
    for province_id, terrain in eep_authored.items():
        if final_terrain.get(province_id) in {"sea", "coastal_sea"}:
            continue
        if terrain not in valid_terrains:
            raise AssertionError(
                f"TempLoV terrain {terrain} for {province_id} is not loaded"
            )
        if final_terrain[province_id] != terrain:
            eep_applied += 1
        final_terrain[province_id] = terrain

    pending: list[int] = []
    for province_id in sorted(expected_ids):
        decision = decisions.get(province_id)
        if decision is None:
            continue
        action, terrain, _ = decision
        if terrain not in valid_terrains:
            raise AssertionError(
                f"terrain decision {province_id} uses unloaded terrain {terrain}"
            )
        if action == "accept":
            if terrain != proposed[province_id]:
                raise AssertionError(
                    f"accept decision for {province_id} must use proposed terrain "
                    f"{proposed[province_id]}, got {terrain}"
                )
        else:
            final_terrain[province_id] = terrain

    mask_names = [str(value) for value in features["mask_names"]]
    mask_intensity = features["mask_intensity"][:, target_ids]
    terrain_audit_rows: list[dict[str, object]] = []
    for offset, province_id_raw in enumerate(target_ids):
        province_id = int(province_id_raw)
        title = title_by_id.get(province_id)
        top_masks = np.argsort(mask_intensity[:, offset])[-3:][::-1]
        contributions = [
            f"{mask_names[index]}:{float(mask_intensity[index, offset]):.4f}"
            for index in top_masks
            if mask_intensity[index, offset] > 0
        ]
        decision = decisions.get(province_id)
        terrain_audit_rows.append(
            {
                "province_id": province_id,
                "rgb": eep_definitions[province_id].rgb_text,
                "barony": title.barony if title else "",
                "county": title.county if title else "",
                "duchy": title.duchy if title else "",
                "kingdom": title.kingdom if title else "",
                "empire": title.empire if title else "",
                "model_terrain": model_proposed[province_id],
                "proposed_terrain": proposed[province_id],
                "eep_terrain": eep_terrain.get(province_id, ""),
                "final_terrain": final_terrain[province_id],
                "model_confidence": f"{confidence_by_id[province_id]:.6f}",
                "model_runner_up": runner_up[province_id],
                "model_margin": f"{margin_by_id[province_id]:.6f}",
                "model_priority_group": priority_group_by_id.get(province_id, ""),
                "model_warning": "|".join(model_review_reasons.get(province_id, [])),
                "lore_base": lore_base_by_id[province_id],
                "lore_forest": f"{float(features['lore_forest'][province_id]):.6f}",
                "lore_google_green": (
                    f"{float(features['lore_google_green'][province_id]):.6f}"
                ),
                "lore_arid": f"{float(features['lore_arid'][province_id]):.6f}",
                "lore_google_mountain": (
                    f"{float(features['lore_google_mountain'][province_id]):.6f}"
                ),
                "slope": f"{float(features['slope'][province_id]):.6f}",
                "lore_reason": lore_reason_by_id[province_id],
                "leading_masks": "|".join(contributions),
                "water_class": water_class_by_id.get(province_id, "land"),
                "review_reason": "|".join(review_reasons.get(province_id, [])),
                "decision": decision[0] if decision else "",
                "decision_reason": decision[2] if decision else "",
                "review_status": (
                    "pending"
                    if province_id in pending
                    else "reviewed"
                    if decision
                    else "automatic"
                ),
            }
        )

    mappings = load_graphical_mappings(graphical_config_path)
    mapping_by_scope_key = {
        (mapping.scope, mapping.key): mapping for mapping in mappings
    }
    config_empire_keys = {
        mapping.key for mapping in mappings if mapping.scope == "empire"
    }
    if config_empire_keys != empire_keys:
        raise AssertionError(
            "graphical empire mappings changed: "
            f"missing={sorted(empire_keys - config_empire_keys)}, "
            f"extra={sorted(config_empire_keys - empire_keys)}"
        )
    region_blocks = effective_region_blocks(
        [
            workshop["AGOT"],
            workshop["NOW"],
            workshop["LOV"],
            workshop["RC"],
            workshop["EE"],
            workshop["EEP"],
        ]
    )
    graphical_blocks = {
        key: block
        for key, block in region_blocks.items()
        if direct_graphical_flag(block)
    }
    missing_styles = {mapping.graphical_region for mapping in mappings} - set(
        graphical_blocks
    )
    if missing_styles:
        raise AssertionError(
            f"mapped graphical styles are not loaded: {sorted(missing_styles)}"
        )

    scope_order = ("province", "county", "duchy", "kingdom", "empire")
    assigned_mapping: dict[int, GraphicalMapping] = {}
    used_mappings: Counter[tuple[str, str]] = Counter()
    for title in graphical_titles:
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
        raise AssertionError(f"unused graphical mappings: {sorted(unused_mappings)}")

    graphical_pending: list[str] = []
    mapping_components: dict[tuple[str, str], dict[int, int]] = {}
    for mapping in mappings:
        mapped_ids = {
            province_id
            for province_id, assigned in assigned_mapping.items()
            if assigned == mapping
        }
        components = connected_components(mapped_ids, adjacency)
        mapping_components[(mapping.scope, mapping.key)] = components
        component_count = max(components.values(), default=0)
        if component_count > 1 and not mapping.allow_disconnected:
            graphical_pending.append(
                f"{mapping.scope}:{mapping.key} has {component_count} components"
            )

    style_to_ids: dict[str, set[int]] = defaultdict(set)
    for province_id, mapping in assigned_mapping.items():
        style_to_ids[mapping.graphical_region].add(province_id)
    if set().union(*style_to_ids.values()) != {
        row.province_id for row in graphical_titles
    }:
        raise AssertionError("graphical target coverage is incomplete")
    if sum(len(values) for values in style_to_ids.values()) != len(graphical_titles):
        raise AssertionError("a graphical target was assigned more than once")

    style_components = {
        style: connected_components(province_ids, adjacency)
        for style, province_ids in style_to_ids.items()
    }
    graphical_audit_rows: list[dict[str, object]] = []
    for title in graphical_titles:
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
        graphical_audit_rows.append(
            {
                "province_id": title.province_id,
                "rgb": eep_definitions[title.province_id].rgb_text,
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
        terrain_audit_rows,
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
        graphical_audit_rows,
    )

    terrain_lines = [
        "\ufeff# Generated by ck3mm from the mod's workspace implementation.",
        "# Final terrain uses aligned lore-map biomes, slope relief, and "
        "strong semantic masks.",
        f"# Audit-only mask-model spatial five-fold macro-F1: {validation_f1:.6f}",
        "# Training labels: "
        + ", ".join(f"{name}={label_counts[name]}" for name in classes),
        f"# Target IDs: {TARGET_FIRST}..{TARGET_LAST} ({TARGET_COUNT})",
        "",
    ]
    terrain_lines.extend(
        f"{province_id} = {final_terrain[province_id]}"
        for province_id in range(TARGET_FIRST, TARGET_LAST + 1)
    )
    terrain_output = ("\n".join(terrain_lines) + "\n").encode("utf-8")

    region_lines = [
        "\ufeff# Generated by ck3mm from the mod's workspace implementation.",
        "# Complete replacements for touched graphical-region keys.",
        "",
    ]
    for style in sorted(style_to_ids):
        source_block = repair_inherited_graphical_block(style, graphical_blocks[style])
        region_lines.append(
            append_provinces_to_block(source_block, style_to_ids[style])
        )
        region_lines.append("")
    region_output = ("\n".join(region_lines)).encode("utf-8")

    outputs = {
        source / "terrain_audit.csv": terrain_audit,
        source / "graphical_region_audit.csv": graphical_audit,
        module / "common/province_terrain/ee_province_terrain.txt": terrain_output,
        module
        / "map_data/geographical_regions/zzzz_agot_now_lov_ee_world_data.txt": region_output,
    }

    if options.audit:
        for path in (
            source / "terrain_audit.csv",
            source / "graphical_region_audit.csv",
        ):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(outputs[path])
            print(f"Wrote {path.relative_to(root)}")
        print(
            f"Audit summary: pending terrain={len(pending)}, "
            f"pending graphical mappings={len(graphical_pending)}, "
            f"validation macro-F1={validation_f1:.4f}"
        )
        for warning in graphical_pending:
            print(f"graphical review required: {warning}", file=sys.stderr)
        return 0

    if pending:
        raise AssertionError(
            f"{len(pending)} terrain provinces require decisions; "
            "run --audit and update terrain_decisions.csv"
        )
    if graphical_pending:
        raise AssertionError(
            "graphical mappings require disconnected-component review: "
            + "; ".join(graphical_pending)
        )
    if set(final_terrain) != expected_ids:
        raise AssertionError("terrain output does not cover the full target range")
    if any(terrain == "default" for terrain in final_terrain.values()):
        raise AssertionError("terrain output still contains default")
    for province_id in expected_ids & water_ids:
        if final_terrain[province_id] not in {"sea", "coastal_sea"}:
            raise AssertionError(f"water province {province_id} has land terrain")

    if options.check:
        stale: list[str] = []
        for path, expected in outputs.items():
            if not path.is_file() or path.read_bytes() != expected:
                stale.append(path.relative_to(root).as_posix())
        if stale:
            raise AssertionError(f"generated outputs are stale: {stale}")
        print(
            f"World-data outputs are current: terrain={TARGET_COUNT}, "
            f"graphical={len(graphical_titles)}, macro-F1={validation_f1:.4f}"
        )
        return 0

    for path, data in outputs.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        print(f"Wrote {path.relative_to(root)}")
    print(
        f"Generated terrain={TARGET_COUNT}, graphical={len(graphical_titles)}, "
        f"macro-F1={validation_f1:.4f}"
    )
    return 0


def generate(context: GenerationContext) -> None:
    global OUTPUT_ROOT_OVERRIDE, ASSETS_DIR_OVERRIDE, MAP_DEFINITION_OVERRIDE
    global REFERENCE_PATHS_OVERRIDE
    OUTPUT_ROOT_OVERRIDE = context.output_root
    ASSETS_DIR_OVERRIDE = context.assets_dir / "world_data"
    MAP_DEFINITION_OVERRIDE = context.source("map-definition")
    REFERENCE_PATHS_OVERRIDE = {
        "detailed": context.source("known-world-detailed"),
        "google": context.source("known-world-google"),
    }
    result = main(
        Options(
            root=context.workspace_root,
            workshop_root=context.workshop_root(
                "agot",
                "agot-now",
                "legacy-of-valyria",
                "legacy-of-valyria-bridge",
                "essos-expanded",
                "essos-expanded-bridge",
            ),
            no_cache=bool(context.options.get("no_cache", False)),
        )
    )
    if result not in (None, 0):
        raise RuntimeError(f"generator returned unsuccessful status {result}")
