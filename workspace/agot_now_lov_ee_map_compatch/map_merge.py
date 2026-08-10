#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from ck3mm.generators.text import read_source
from ck3mm.hashing import sha256_file
from ck3mm.source_manifest import (
    canonical_source_path,
    resolve_workshop_root,
)

parser = argparse.ArgumentParser(
    description="Regenerate the semantic NOW + LoV + Essos map merge."
)
parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
parser.add_argument(
    "--output",
    type=Path,
    default=None,
    help="Destination module or scratch directory (defaults to the tracked map module).",
)
mode = parser.add_mutually_exclusive_group()
mode.add_argument(
    "--check", action="store_true", help="Verify tracked textual outputs."
)
mode.add_argument(
    "--update-source-manifest",
    action="store_true",
    help="Accept reviewed upstream input hashes.",
)
parser.add_argument(
    "--text-only",
    action="store_true",
    help="Skip raster composites; useful when only script/map-object inputs changed.",
)
args = parser.parse_args()

ROOT = args.root.resolve()
WS = resolve_workshop_root()
AGOT = WS / "2962333032"
NOW = WS / "3664900993"
LOV = WS / "3403938445"
RC = WS / "3719888822"
EE = WS / "3682802751"
EEP = WS / "3768149491"
TRACKED_OUTPUT = ROOT / "mods/agot_now_lov_ee_map_compatch"
DESTINATION = (args.output or TRACKED_OUTPUT).resolve()
# Build only in a disposable stage. A failed ImageMagick process must never
# leave a tracked module half-deleted.
OUT = Path(tempfile.mkdtemp(prefix="agot_now_lov_ee_map_compatch."))
MANIFEST_PATH = Path(
    os.environ.get(
        "CK3MM_SOURCE_MANIFEST",
        ROOT / "workspace/agot_now_lov_ee_map_compatch/assets/source_manifest.json",
    )
)
RECT = (
    575.0,
    2060.0,
    1932.0,
    3560.0,
)  # x min/max, z min/max; inverse of image y 2584..4212

map_paths = [
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


def winner(rel):
    for p in (EEP, EE, RC, LOV, AGOT):
        if (p / rel).is_file():
            return p / rel
    raise FileNotFoundError(rel)


def source_manifest() -> dict[str, object]:
    inputs = (
        {AGOT / rel for rel in map_paths}
        | {NOW / rel for rel in map_paths}
        | {winner(rel) for rel in map_paths}
        | {
            AGOT / "map_data/definition.csv",
            NOW / "map_data/definition.csv",
            winner("map_data/definition.csv"),
            AGOT / "map_data/heightmap.png",
            NOW / "map_data/heightmap.png",
            EE / "map_data/heightmap.png",
            AGOT / "content_source/map_objects/masks/tree_leaf_01_single_mask.png",
            NOW / "content_source/map_objects/masks/tree_leaf_01_single_mask.png",
            EE / "content_source/map_objects/masks/tree_leaf_01_single_mask.png",
            AGOT / "content_source/map_objects/masks/tree_pine_01_a_mask.png",
            NOW / "content_source/map_objects/masks/tree_pine_01_a_mask.png",
            EE / "content_source/map_objects/masks/tree_pine_01_a_mask.png",
        }
    )
    modules = {"AGOT": AGOT, "NOW": NOW, "LOV": LOV, "RC": RC, "EE": EE, "EEP": EEP}
    versions = {}
    for label, module in modules.items():
        descriptor = module / "descriptor.mod"
        match = re.search(
            r'(?m)^version="([^"]+)"',
            descriptor.read_text(encoding="utf-8-sig"),
        )
        versions[label] = match.group(1) if match else "unversioned"
    return {
        "schema_version": 1,
        "workshop_ids": {label: module.name for label, module in modules.items()},
        "versions": versions,
        "files": {
            canonical_source_path(path, root=ROOT, workshop_root=WS): {
                "sha256": sha256_file(path),
                "size": path.stat().st_size,
            }
            for path in sorted(inputs)
        },
    }


CURRENT_MANIFEST = source_manifest()
if args.update_source_manifest:
    pass
elif not MANIFEST_PATH.is_file():
    raise FileNotFoundError(
        f"{MANIFEST_PATH} missing; review inputs and run --update-source-manifest"
    )
elif json.loads(MANIFEST_PATH.read_text(encoding="utf-8")) != CURRENT_MANIFEST:
    raise AssertionError(
        "map-compatch upstream source manifest drifted; review and run --update-source-manifest"
    )


def read(p):
    return read_source(p, normalize_newlines=True)


def write(rel, text, encoding="utf-8-sig"):
    p = OUT / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding=encoding, newline="\n")


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
        re.finditer(
            r"(?ms)^\t\t\{\n[ \t]+id\s*=\s*(\d+)\s*\n.*?^[ \t]+\}",
            text,
        )
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


for rel in map_paths:
    b = read(AGOT / rel)
    o = read(winner(rel))
    n = read(NOW / rel)
    result = (
        merge_locator(b, o, n)
        if rel.endswith(
            (
                "activities.txt",
                "building_locators.txt",
                "combat_locators.txt",
                "player_stack_locators.txt",
                "siege_locators.txt",
                "special_building_locators.txt",
            )
        )
        else merge_objects(o, n)
    )
    assert "<<<<<<<" not in result
    write(rel, result)


# Definition: use current EE/LoV winner, replacing only rows NOW changed from AGOT.
def rows(p):
    lines = read(p).splitlines()
    d = {line.split(";", 1)[0]: line for line in lines if ";" in line}
    return lines, d


bl, bd = rows(AGOT / "map_data/definition.csv")
nl, nd = rows(NOW / "map_data/definition.csv")
ol, od = rows(winner("map_data/definition.csv"))
changed = {k for k in bd.keys() & nd.keys() if bd[k] != nd[k]}
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
out = [
    nd.get(line.split(";", 1)[0], line) if line.split(";", 1)[0] in changed else line
    for line in ol
]
# definition.csv is deliberately BOM-free; Clausewitz treats the BOM as part
# of the first province id on some startup paths.
write("map_data/definition.csv", "\n".join(out) + "\n", encoding="utf-8")


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


if not args.text_only:
    composite_delta(
        AGOT / "map_data/heightmap.png",
        NOW / "map_data/heightmap.png",
        EE / "map_data/heightmap.png",
        OUT / "artifacts/heightmap/heightmap_now_delta_unpacked.png",
    )
    for f in ("tree_leaf_01_single_mask.png", "tree_pine_01_a_mask.png"):
        composite_delta(
            AGOT / "content_source/map_objects/masks" / f,
            NOW / "content_source/map_objects/masks" / f,
            EE / "content_source/map_objects/masks" / f,
            OUT / "artifacts/map_objects/masks" / f,
        )

# Fail generation rather than emitting structurally inconsistent map objects.
locator_paths = {
    p
    for p in map_paths
    if p.endswith(
        (
            "activities.txt",
            "building_locators.txt",
            "combat_locators.txt",
            "player_stack_locators.txt",
            "siege_locators.txt",
            "special_building_locators.txt",
        )
    )
}
for rel in map_paths:
    text = read(OUT / rel)
    if rel in locator_paths:
        ids = [int(x) for x in re.findall(r"(?m)^[ \t]*id\s*=\s*(\d+)\s*$", text)]
        _, _, parsed = parse_instances(text)
        assert ids == list(parsed), f"locator parser mismatch in {rel}"
        assert len(ids) == len(set(ids)), f"duplicate locator id in {rel}"
    else:
        for name, block, _, _ in object_blocks(text):
            parsed = transforms(block)
            if parsed:
                declared = re.search(r"(?m)^\tcount=(\d+)$", block)
                assert declared and int(declared.group(1)) == len(parsed[1]), (
                    f"bad count for {name} in {rel}"
                )

definition_lines = [
    line for line in read(OUT / "map_data/definition.csv").splitlines() if ";" in line
]
definition_ids = [line.split(";", 1)[0] for line in definition_lines]
assert len(definition_ids) == len(set(definition_ids)), (
    "duplicate province id in definition.csv"
)

text_outputs = [*map_paths, "map_data/definition.csv"]
if args.check:
    stale = [
        relative
        for relative in text_outputs
        if not (TRACKED_OUTPUT / relative).is_file()
        or (TRACKED_OUTPUT / relative).read_bytes() != (OUT / relative).read_bytes()
    ]
    if stale:
        raise AssertionError(
            "tracked map-compatch textual outputs are stale: " + ", ".join(stale)
        )
    print("map-compatch textual outputs are current")
elif args.update_source_manifest:
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(
        json.dumps(CURRENT_MANIFEST, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"updated {MANIFEST_PATH.relative_to(ROOT)}")
else:
    if DESTINATION in {ROOT, ROOT / "mods"}:
        raise ValueError(f"refusing broad map-compatch destination: {DESTINATION}")
    for source in sorted(path for path in OUT.rglob("*") if path.is_file()):
        relative = source.relative_to(OUT)
        target = DESTINATION / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    print("generated", DESTINATION)
    for source in sorted(path for path in OUT.rglob("*") if path.is_file()):
        print(source.relative_to(OUT), source.stat().st_size)

shutil.rmtree(OUT)
