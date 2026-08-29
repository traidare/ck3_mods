#!/usr/bin/env python3
"""Merge NOW's Westeros deltas onto Further East EEP's native AGOT 0.5 map.

Further East v4 already uses AGOT's 8233-9400 province band.  This layer must
therefore never paste AGOT raster data or renumber provinces: it starts from
EEP's canonical map and carries only the small, independently authored NOW and
COW/NOW map-object deltas that still apply to Westeros.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from gen import GenerationContext
from gen.sources import canonical_source_path
from gen.text import matching_brace, read_source

DEFINITION = "map_data/definition.csv"
GEO_REGIONS = "map_data/geographical_regions/00_agot_geographical_region.txt"
NOW_GEO_REGIONS = (
    "map_data/geographical_regions/replace/00_agot_geographical_region.txt"
)
LOCATOR_FILES = (
    "gfx/map/map_object_data/building_locators.txt",
    "gfx/map/map_object_data/special_building_locators.txt",
)
OBJECT_FILES = (
    "gfx/map/map_object_data/new_mapobject_2.txt",
    "gfx/map/map_object_data/new_mapobject_3.txt",
)
# These are the only NOW rows EEP v4 still inherits unchanged from AGOT.  The
# remaining NOW definition edits either predate AGOT 0.5's canonical map or
# touch an EEP-authored row and are intentionally left to EEP.
NOW_DEFINITION_ROWS = frozenset(
    (3967, 3969, 4124, 4125, 4126, 4136, 4138, 4419, 4420, 4422, 4426)
)
# Records both EEP and NOW edited, where load order cannot decide.  Each entry
# pins all three inputs, so any upstream change re-raises the conflict instead
# of silently reusing a stale review.
LOCATOR_RESOLUTIONS: dict[tuple[str, int], tuple[str, dict[str, str]]] = {
    ("gfx/map/map_object_data/special_building_locators.txt", 3462): (
        # b_cuy.  EEP re-placed the special building and, as it does at every
        # locator it re-places, reset height and scale to the editor defaults.
        # NOW instead deliberately resized the same model from 0.267 to 0.468.
        # Keep EEP's placement and NOW's size; neither source loses its intent.
        "14f9365da82ba20d77959154de3fff59465f20d2bc670baf436e86f99c5b4968",
        {"position": "current", "rotation": "current", "scale": "incoming"},
    ),
}
LOCATOR_FIELD = re.compile(
    r"(?m)^[ \t]*(?P<field>[a-z_]+)\s*=\s*(?:\{[^}]*\}|\S+)[ \t]*$"
)


@dataclass(frozen=True, slots=True)
class Inputs:
    context: GenerationContext
    workshop_root: Path
    agot: Path
    now: Path
    ee: Path
    eep: Path
    cow: Path

    @classmethod
    def from_context(cls, context: GenerationContext) -> Inputs:
        names = ("agot", "now", "essos-expanded", "essos-bridge", "cow-now-compatch")
        return cls(
            context=context,
            workshop_root=context.workshop_root(*names),
            agot=context.source("agot"),
            now=context.source("now"),
            ee=context.source("essos-expanded"),
            eep=context.source("essos-bridge"),
            cow=context.source("cow-now-compatch"),
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
) -> str:
    """Apply keyed source deltas onto the EEP baseline.

    Every overlay carries the baseline it was authored against, so a source
    derived from another (COW/NOW extends NOW) is diffed against its own parent
    rather than against AGOT, where the shared ancestry would read as conflict.
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
    return (
        prefix + "\n\n".join(merged[key] for key in order) + suffix.rstrip("\n") + "\n"
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


def stacked_overlays(inputs: Inputs, relative: str, parse) -> tuple[Overlay, ...]:
    """NOW diffs against AGOT; COW/NOW diffs against the NOW it integrates."""
    agot = parse(read(inputs.agot / relative))
    now = parse(read(inputs.now / relative))
    overlays = [Overlay.build(f"NOW {relative}", agot, now)]
    cow_path = inputs.cow / relative
    if cow_path.is_file():
        overlays.append(
            Overlay.build(f"COW/NOW {relative}", now, parse(read(cow_path)))
        )
    return tuple(overlays)


def merge_locator_file(inputs: Inputs, relative: str) -> str:
    current = locator_records(read(inputs.current_map_source(relative)))
    resolutions = {
        key: value
        for (path, key), value in LOCATOR_RESOLUTIONS.items()
        if path == relative
    }
    return merge_file_blocks(
        current, stacked_overlays(inputs, relative, locator_records), resolutions
    )


def merge_object_file(inputs: Inputs, relative: str) -> str:
    current = split_objects(read(inputs.current_map_source(relative)))
    return merge_file_blocks(
        current,
        stacked_overlays(inputs, relative, split_objects),
        conflict=merge_object_block,
    )


def definition_rows(path: Path) -> tuple[list[str], dict[int, str]]:
    lines = read(path).splitlines()
    rows = {
        int(line.split(";", 1)[0]): line
        for line in lines
        if ";" in line and line.split(";", 1)[0].strip().isdigit()
    }
    return lines, rows


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


def source_manifest(inputs: Inputs) -> dict[str, object]:
    relatives = [
        DEFINITION,
        GEO_REGIONS,
        NOW_GEO_REGIONS,
        *LOCATOR_FILES,
        *OBJECT_FILES,
    ]
    paths = (
        {
            inputs.agot / relative
            for relative in relatives
            if (inputs.agot / relative).is_file()
        }
        | {
            inputs.now / relative
            for relative in (DEFINITION, NOW_GEO_REGIONS, *LOCATOR_FILES, *OBJECT_FILES)
            if (inputs.now / relative).is_file()
        }
        | {
            inputs.current_map_source(relative)
            for relative in (DEFINITION, GEO_REGIONS, *LOCATOR_FILES, *OBJECT_FILES)
        }
        | {
            inputs.cow / relative
            for relative in (*LOCATOR_FILES, *OBJECT_FILES)
            if (inputs.cow / relative).is_file()
        }
    )
    modules = {
        "AGOT": inputs.agot,
        "NOW": inputs.now,
        "EEP": inputs.eep,
        "COW_NOW": inputs.cow,
    }
    return {
        "schema_version": 2,
        "versions": {
            label: re.search(
                r'(?m)^version="([^\"]+)"', read(root / "descriptor.mod")
            ).group(1)
            for label, root in modules.items()
        },
        "files": {
            canonical_source_path(
                path,
                root=inputs.context.workspace_root,
                workshop_root=inputs.workshop_root,
            ): {
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "size": path.stat().st_size,
            }
            for path in sorted(paths)
        },
        "intent": "EEP-native map; apply NOW/COW semantic Westeros deltas only",
    }


def generate(context: GenerationContext) -> None:
    inputs = Inputs.from_context(context)
    manifest = source_manifest(inputs)
    manifest_path = context.assets_dir / "source_manifest.json"
    if json.loads(manifest_path.read_text(encoding="utf-8")) != manifest:
        raise RuntimeError("map source manifest drifted; review and replace the asset")

    inputs.write(DEFINITION, merge_definition(inputs), encoding="utf-8")
    inputs.write(GEO_REGIONS, merge_geographical_regions(inputs))
    for relative in LOCATOR_FILES:
        inputs.write(relative, merge_locator_file(inputs, relative))
    for relative in OBJECT_FILES:
        inputs.write(relative, merge_object_file(inputs, relative))
    inputs.context.artifact_path("map_data/merge_audit.json").write_text(
        json.dumps(
            {
                "definition_rows": sorted(NOW_DEFINITION_ROWS),
                "baseline": "Further East EEP v4 native map",
                "raster_outputs": "none",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
