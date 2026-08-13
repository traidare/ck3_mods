#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from gen import GenerationContext
from gen.hashing import sha256_file
from gen.sources import canonical_source_path
from gen.text import read_source

RECT = (
    575.0,
    2060.0,
    1932.0,
    3560.0,
)  # x min/max, z min/max; inverse of image y 2584..4212

MAP_PATHS = [
    "gfx/map/map_object_data/activities.txt",
    "gfx/map/map_object_data/building_locators.txt",
    "gfx/map/map_object_data/combat_locators.txt",
    "gfx/map/map_object_data/generated/cactus_cholla_01_generator_1.txt",
    "gfx/map/map_object_data/generated/tree_leaf_01_single_generator_1.txt",
    "gfx/map/map_object_data/generated/tree_leaf_2_high_generator_1.txt",
    "gfx/map/map_object_data/generated/tree_mangrove_generator_1.txt",
    "gfx/map/map_object_data/generated/tree_mangrove_generator_2.txt",
    "gfx/map/map_object_data/generated/tree_mangrove_generator_3.txt",
    "gfx/map/map_object_data/generated/tree_pine_01_a_generator_1.txt",
    "gfx/map/map_object_data/new_mapobject_1.txt",
    "gfx/map/map_object_data/new_mapobject_2.txt",
    "gfx/map/map_object_data/new_mapobject_3.txt",
    "gfx/map/map_object_data/new_mapobject_5.txt",
    "gfx/map/map_object_data/player_stack_locators.txt",
    "gfx/map/map_object_data/siege_locators.txt",
    "gfx/map/map_object_data/special_building_locators.txt",
]


@dataclass(frozen=True, slots=True)
class MapInputs:
    context: GenerationContext
    workshop_root: Path
    agot: Path
    now: Path
    lov: Path
    rc: Path
    ee: Path
    eep: Path
    manifest_path: Path

    @classmethod
    def from_context(cls, context: GenerationContext) -> MapInputs:
        source_names = (
            "agot",
            "now",
            "lov",
            "lov-bridge",
            "essos-expanded",
            "essos-bridge",
        )
        return cls(
            context=context,
            workshop_root=context.workshop_root(*source_names),
            agot=context.source("agot"),
            now=context.source("now"),
            lov=context.source("lov"),
            rc=context.source("lov-bridge"),
            ee=context.source("essos-expanded"),
            eep=context.source("essos-bridge"),
            manifest_path=context.assets_dir / "source_manifest.json",
        )

    def winner(self, relative: str) -> Path:
        for root in (self.eep, self.ee, self.rc, self.lov, self.agot):
            path = root / relative
            if path.is_file():
                return path
        raise FileNotFoundError(relative)

    def write(self, relative: str, text: str, encoding: str = "utf-8-sig") -> None:
        path = self.context.output_path(relative)
        path.write_text(text, encoding=encoding, newline="\n")


def source_manifest(inputs: MapInputs) -> dict[str, object]:
    source_paths = (
        {inputs.agot / relative for relative in MAP_PATHS}
        | {inputs.now / relative for relative in MAP_PATHS}
        | {inputs.winner(relative) for relative in MAP_PATHS}
        | {
            inputs.agot / "map_data/definition.csv",
            inputs.now / "map_data/definition.csv",
            inputs.winner("map_data/definition.csv"),
            inputs.agot / "map_data/heightmap.png",
            inputs.now / "map_data/heightmap.png",
            inputs.ee / "map_data/heightmap.png",
            inputs.agot
            / "content_source/map_objects/masks/tree_leaf_01_single_mask.png",
            inputs.now
            / "content_source/map_objects/masks/tree_leaf_01_single_mask.png",
            inputs.ee / "content_source/map_objects/masks/tree_leaf_01_single_mask.png",
            inputs.agot / "content_source/map_objects/masks/tree_pine_01_a_mask.png",
            inputs.now / "content_source/map_objects/masks/tree_pine_01_a_mask.png",
            inputs.ee / "content_source/map_objects/masks/tree_pine_01_a_mask.png",
        }
    )
    modules = {
        "AGOT": inputs.agot,
        "NOW": inputs.now,
        "LOV": inputs.lov,
        "RC": inputs.rc,
        "EE": inputs.ee,
        "EEP": inputs.eep,
    }
    versions = {}
    for label, module in modules.items():
        descriptor = module / "descriptor.mod"
        match = re.search(
            r'(?m)^version="([^"]+)"', descriptor.read_text(encoding="utf-8-sig")
        )
        versions[label] = match.group(1) if match else "unversioned"
    return {
        "schema_version": 1,
        "workshop_ids": {label: module.name for label, module in modules.items()},
        "versions": versions,
        "files": {
            canonical_source_path(
                path,
                root=inputs.context.workspace_root,
                workshop_root=inputs.workshop_root,
            ): {"sha256": sha256_file(path), "size": path.stat().st_size}
            for path in sorted(source_paths)
        },
    }


def read(p):
    return read_source(p, normalize_newlines=True)


def pos_from_record(s):
    m = re.search(r"position=\{\s*([-+0-9.]+)\s+[-+0-9.]+\s+([-+0-9.]+)", s)
    return (float(m.group(1)), float(m.group(2))) if m else None


def inside(pos):
    if not pos:
        return False
    x, z = pos
    return RECT[0] <= x <= RECT[1] and RECT[2] <= z <= RECT[3]


def parse_instances(text):
    # Some current EE/LoV locator records retain their normal two-tab opening
    # brace but indent id/position/closing lines more deeply. Clausewitz ignores
    # that whitespace; the merger must not mistake those records for deletions.
    matches = list(
        re.finditer(r"(?ms)^\t\t\{\n[ \t]+id\s*=\s*(\d+)\s*\n.*?^[ \t]+\}", text)
    )
    raw_ids = [int(x) for x in re.findall(r"(?m)^[ \t]*id\s*=\s*(\d+)\s*$", text)]
    parsed_ids = [int(m.group(1)) for m in matches]
    assert matches
    assert len(parsed_ids) == len(set(parsed_ids)), "duplicate locator id in input"
    assert parsed_ids == raw_ids, (
        "locator parser skipped or reordered ids: "
        f"missing={sorted(set(raw_ids) - set(parsed_ids))}"
    )
    return (
        text[: matches[0].start()],
        text[matches[-1].end() :],
        {int(m.group(1)): m.group(0) for m in matches},
    )


def merge_locator(base, ours, now):
    bp, bs, b = parse_instances(base)
    op, os, o = parse_instances(ours)
    np, ns, n = parse_instances(now)
    out = {}
    for k in sorted(set(b) | set(o) | set(n)):
        bv, ov, nv = b.get(k), o.get(k), n.get(k)
        if nv == bv or nv is None:
            v = ov
        elif ov == bv or ov is None:
            v = nv
        elif ov == nv:
            v = ov
        else:
            v = nv if inside(pos_from_record(nv)) else ov
        if v is not None:
            out[k] = v
    return op + "\n".join(out[k] for k in sorted(out)) + os


def object_blocks(text):
    starts = list(re.finditer(r"(?m)^object=\{", text))
    blocks = []
    for sm in starts:
        start = sm.start()
        depth = 0
        quoted = False
        comment = False
        end = None
        for i in range(start, len(text)):
            c = text[i]
            if comment:
                if c == "\n":
                    comment = False
            elif c == '"':
                quoted = not quoted
            elif c == "#" and not quoted:
                comment = True
            elif not quoted:
                if c == "{":
                    depth += 1
                elif c == "}":
                    depth -= 1
                    if depth == 0:
                        end = i + 1
                        break
        assert end
        block = text[start:end]
        nm = re.search(r'(?m)^\tname="([^"]+)"', block)
        assert nm
        blocks.append((nm.group(1), block, start, end))
    return blocks


def transforms(block):
    m = re.search(r'(?ms)^\ttransform="(.*?)\n"', block)
    if not m:
        return None
    lines = [x for x in m.group(1).splitlines() if x.strip()]
    return m, lines


def line_inside(line):
    p = line.split()
    return len(p) >= 3 and inside((float(p[0]), float(p[2])))


def merge_object_block(ours, now):
    ot = transforms(ours)
    nt = transforms(now)
    if not ot or not nt:
        return ours
    om, ol = ot
    nm, nl = nt
    merged = []
    seen = set()
    for line in [x for x in ol if not line_inside(x)] + [
        x for x in nl if line_inside(x)
    ]:
        if line not in seen:
            seen.add(line)
            merged.append(line)
    body = "\n".join(merged)
    out = ours[: om.start(1)] + body + ours[om.end(1) :]
    out = re.sub(r"(?m)^\tcount=\d+", f"\tcount={len(merged)}", out, count=1)
    return out


def merge_objects(ours, now):
    ob = object_blocks(ours)
    nb = object_blocks(now)
    nd = {n: b for n, b, _, _ in nb}
    parts = []
    cursor = 0
    for name, block, start, end in ob:
        parts.append(ours[cursor:start])
        parts.append(merge_object_block(block, nd[name]) if name in nd else block)
        cursor = end
    parts.append(ours[cursor:])
    existing = {n for n, _, _, _ in ob}
    for name, block, _, _ in nb:
        if name not in existing:
            parts.append("\n" + block + "\n")
    return "".join(parts)


LOCATOR_SUFFIXES = (
    "activities.txt",
    "building_locators.txt",
    "combat_locators.txt",
    "player_stack_locators.txt",
    "siege_locators.txt",
    "special_building_locators.txt",
)


def merge_map_objects(inputs: MapInputs) -> None:
    for relative in MAP_PATHS:
        base = read(inputs.agot / relative)
        ours = read(inputs.winner(relative))
        now = read(inputs.now / relative)
        result = (
            merge_locator(base, ours, now)
            if relative.endswith(LOCATOR_SUFFIXES)
            else merge_objects(ours, now)
        )
        assert "<<<<<<<" not in result
        inputs.write(relative, result)


# Definition: use current EE/LoV winner, replacing only rows NOW changed from AGOT.
def rows(p):
    lines = read(p).splitlines()
    d = {line.split(";", 1)[0]: line for line in lines if ";" in line}
    return lines, d


def merge_definition(inputs: MapInputs) -> None:
    _, base = rows(inputs.agot / "map_data/definition.csv")
    _, now = rows(inputs.now / "map_data/definition.csv")
    ours, _ = rows(inputs.winner("map_data/definition.csv"))
    changed = {key for key in base.keys() & now.keys() if base[key] != now[key]}
    assert changed == {
        "3967",
        "3969",
        "4124",
        "4125",
        "4126",
        "4136",
        "4138",
        "4419",
        "4420",
        "4422",
        "4426",
    }, changed
    output = [
        now.get(line.split(";", 1)[0], line)
        if line.split(";", 1)[0] in changed
        else line
        for line in ours
    ]
    # definition.csv is deliberately BOM-free; Clausewitz treats the BOM as
    # part of the first province id on some startup paths.
    inputs.write("map_data/definition.csv", "\n".join(output) + "\n", "utf-8")


# Exact-pixel delta composites for source heightmap and the two NOW-changed generator masks.
def composite_delta(base, now, ours, out):
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as td:
        mask = Path(td) / "mask.png"
        subprocess.run(
            [
                "magick",
                str(base),
                str(now),
                "-compose",
                "difference",
                "-composite",
                "-threshold",
                "0",
                str(mask),
            ],
            check=True,
        )
        subprocess.run(
            ["magick", str(ours), str(now), str(mask), "-composite", str(out)],
            check=True,
        )


def merge_rasters(inputs: MapInputs) -> None:
    composite_delta(
        inputs.agot / "map_data/heightmap.png",
        inputs.now / "map_data/heightmap.png",
        inputs.ee / "map_data/heightmap.png",
        inputs.context.artifact_path("heightmap/heightmap_now_delta_unpacked.png"),
    )
    for name in ("tree_leaf_01_single_mask.png", "tree_pine_01_a_mask.png"):
        composite_delta(
            inputs.agot / "content_source/map_objects/masks" / name,
            inputs.now / "content_source/map_objects/masks" / name,
            inputs.ee / "content_source/map_objects/masks" / name,
            inputs.context.artifact_path("map_objects/masks/" + name),
        )


def verify_source_manifest(inputs: MapInputs) -> None:
    asset = inputs.manifest_path.relative_to(inputs.context.workspace_root)
    if not inputs.manifest_path.is_file():
        raise FileNotFoundError(
            f"{asset} is missing; review the upstream inputs and replace the "
            "reviewed asset deliberately"
        )
    recorded = json.loads(inputs.manifest_path.read_text(encoding="utf-8"))
    if recorded != source_manifest(inputs):
        raise AssertionError(
            f"map-compatch upstream source manifest drifted; review the "
            f"differences and replace {asset} deliberately"
        )


def validate_outputs(inputs: MapInputs) -> None:
    """Fail rather than emitting structurally inconsistent map objects."""
    locator_paths = {path for path in MAP_PATHS if path.endswith(LOCATOR_SUFFIXES)}
    for relative in MAP_PATHS:
        text = read(inputs.context.output_root / relative)
        if relative in locator_paths:
            ids = [
                int(value)
                for value in re.findall(r"(?m)^[ \t]*id\s*=\s*(\d+)\s*$", text)
            ]
            _, _, parsed = parse_instances(text)
            assert ids == list(parsed), f"locator parser mismatch in {relative}"
            assert len(ids) == len(set(ids)), f"duplicate locator id in {relative}"
            continue
        for name, block, _, _ in object_blocks(text):
            parsed = transforms(block)
            if parsed:
                declared = re.search(r"(?m)^\tcount=(\d+)$", block)
                assert declared and int(declared.group(1)) == len(parsed[1]), (
                    f"bad count for {name} in {relative}"
                )

    definition = read(inputs.context.output_root / "map_data/definition.csv")
    definition_ids = [
        line.split(";", 1)[0] for line in definition.splitlines() if ";" in line
    ]
    assert len(definition_ids) == len(set(definition_ids)), (
        "duplicate province id in definition.csv"
    )


def generate(context: GenerationContext) -> None:
    inputs = MapInputs.from_context(context)
    verify_source_manifest(inputs)
    merge_map_objects(inputs)
    merge_definition(inputs)
    if not context.options.get("text_only", False):
        merge_rasters(inputs)
    validate_outputs(inputs)

    print("generated", context.output_root)
    for source in sorted(
        path for path in context.output_root.rglob("*") if path.is_file()
    ):
        print(source.relative_to(context.output_root), source.stat().st_size)
