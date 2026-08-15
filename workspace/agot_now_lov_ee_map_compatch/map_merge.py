#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image

from gen import GenerationContext
from gen.hashing import sha256_file
from gen.sources import canonical_source_path
from gen.text import read_source

Image.MAX_IMAGE_PIXELS = None

RECT = (
    575.0,
    2060.0,
    1932.0,
    3560.0,
)  # x min/max, z min/max; inverse of image y 2584..4212

MAP_SIZE = (9216, 6144)

# AGOT 0.5.0 numbers its new Ibben/Norvos/Qohor/Lorath/Rhoyne region 8233-9400.
# The effective map already spends those ids on Essos Expanded's authored
# baronies, so the new region is renumbered onto free ids above the Essos
# Expanded ceiling and the parents keep their numbering. Expect this to unwind
# once NOW, LoV and Essos Expanded publish their own 0.5.0 rebases; the remap
# table below is the only place that encodes it.
AGOT_NEW_FIRST = 8233
AGOT_NEW_LAST = 9400
AGOT_NEW_COUNT = AGOT_NEW_LAST - AGOT_NEW_FIRST + 1
REMAP_FIRST = 26421

# AGOT's 1168 new province colours are disjoint from the Essos Expanded lineage
# apart from b_punulea_sar, which reuses the colour Essos Expanded gives 9142.
# Only that one province is recoloured, to the highest free value.
EXPECTED_RECOLOURS = {9083: (255, 255, 254)}

EXPECTED_FOOTPRINT_PIXELS = 927787
# Taking AGOT's region wholesale empties 970 Essos Expanded rows, 345 of them
# authored baronies rather than generated R<r>G<g>B<b> filler. A further 241
# rows arrive empty from upstream. Both counts are pinned so a footprint change
# has to be reviewed rather than absorbed.
EXPECTED_CONSUMED_ROWS = 970
EXPECTED_BASELINE_EMPTY_ROWS = 241

# Upstream subtrees the landed-titles graft replaces outright. Their land is
# AGOT's too, so whatever pixels survive the paste are absorbed into the
# neighbouring merged provinces instead of being left as unreachable slivers
# under a title that no longer exists.
REPLACED_SUBTREES = {
    "common/landed_titles/lv_rhoyne_titles.txt": ("e_rhoyne",),
    "common/landed_titles/01_landed_titles.txt": ("k_lorath",),
}
EXPECTED_ABSORBED_PROVINCES = 410
EXPECTED_ABSORBED_PIXELS = 578
EXPECTED_ABSORBED_ROWS = 14

# Upstream landed-titles files this compatch re-emits without the baronies whose
# provinces the paste leaves without pixels, and without the replaced subtrees
# above. Rewriting them beats relying on a later redefinition to shadow them:
# the result does not depend on how CK3 treats a title defined twice.
STRIPPED_TITLE_FILES = (
    "common/landed_titles/lv_rhoyne_titles.txt",
    "common/landed_titles/lv_volantis_titles.txt",
    "common/landed_titles/01_landed_titles.txt",
)
LOV_SOTHORYOS_TITLES = "common/landed_titles/lv_sothoryos_titles.txt"
EXPECTED_RELOCATED_SOTHORYOS_TITLES = 692
EXPECTED_RELOCATED_SOTHORYOS_KINGDOMS = 2
EXPECTED_STRIPPED_BARONIES = 980
EXPECTED_SOURCE_STRIPPED_TITLES = 1208
EXPECTED_STRIPPED_TITLES = 1197
REMOVED_TITLES_ARTIFACT = "map_data/removed_titles.json"

# Title history upstream keeps for titles the strip removes. Left in place it
# would address titles that no longer exist.
STRIPPED_HISTORY_FILES = (
    "history/titles/lv_development_levels.txt",
    "history/titles/zz_eetlv_cob_dejure.txt",
)
EXPECTED_STRIPPED_HISTORY = 17

# AGOT's province history for the new region, replayed at the renumbered ids.
# The 59 band ids without an entry are its new lakes, mountains and sea zones.
AGOT_PROVINCE_HISTORY = (
    "history/provinces/00_k_ar_noy_prov.txt",
    "history/provinces/00_k_chroyane_prov.txt",
    "history/provinces/00_k_ghoyan_drohe_prov.txt",
    "history/provinces/00_k_lorath_prov.txt",
    "history/provinces/00_k_norvos_prov.txt",
    "history/provinces/00_k_ny_sar_prov.txt",
    "history/provinces/00_k_pentos_prov.txt",
    "history/provinces/00_k_qohor_prov.txt",
    "history/provinces/00_k_the_axe_prov.txt",
)
PROVINCE_HISTORY_OUTPUT = "history/provinces/zz_agot_new_region_prov.txt"
EXPECTED_REMAPPED_HISTORY = 1109

# AGOT 0.5's pasted footprint consumes these LoV county capitals while leaving
# other baronies in each county alive.  CK3 treats the first surviving barony
# as the new implicit capital, so move the complete province history with it.
# Keep this explicit and fail closed: a changed set means the map overlap needs
# a fresh lore/history decision, not an automatic guess.
CONSUMED_CAPITAL_MIGRATIONS = {
    "c_ar_mynar": ("b_ar_mynar", 10919, "b_harasan", 10924),
    "c_arosenyr": ("b_death_swamps18", 10630, "b_death_swamps21", 10633),
    "c_noksarys": ("b_death_swamps12", 10663, "b_death_swamps13", 10664),
}
LOV_VOLANTIS_TITLES = "common/landed_titles/lv_volantis_titles.txt"
LOV_VOLANTIS_PROVINCE_HISTORY = "history/provinces/lv_k_volantis.txt"

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
            inputs.agot / "map_data/default.map",
            inputs.winner("map_data/default.map"),
            inputs.agot / TITLE_PATH,
            inputs.now / TITLE_PATH,
            *(inputs.winner(relative) for relative in STRIPPED_TITLE_FILES),
            inputs.lov / LOV_SOTHORYOS_TITLES,
            *(inputs.winner(relative) for relative in STRIPPED_HISTORY_FILES),
            inputs.winner(LOV_VOLANTIS_PROVINCE_HISTORY),
            *(inputs.agot / relative for relative in AGOT_PROVINCE_HISTORY),
            inputs.agot / "map_data/provinces.png",
            inputs.winner("map_data/provinces.png"),
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


def renumber_record(record: str, new_id: int) -> str:
    renumbered, count = re.subn(
        r"(?m)^([ \t]*id\s*=\s*)\d+\s*$", rf"\g<1>{new_id}", record, count=1
    )
    assert count == 1, "locator record has no id line"
    return renumbered


def merge_locator(base, ours, now, remap):
    bp, bs, b = parse_instances(base)
    op, os, o = parse_instances(ours)
    np, ns, n = parse_instances(now)
    out = {}
    for k in sorted(set(b) | set(o) | set(n)):
        # These ids belong to the Essos Expanded lineage on the merged map;
        # AGOT's records for them are re-emitted at their renumbered ids below
        # and must not shadow whatever the lineage puts here.
        bv = None if AGOT_NEW_FIRST <= k <= AGOT_NEW_LAST else b.get(k)
        ov, nv = o.get(k), n.get(k)
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
    for old in sorted(remap.ids):
        record = b.get(old)
        if record is not None:
            new = remap.new_id(old)
            assert new not in out, f"renumbered locator {new} already present"
            out[new] = renumber_record(record, new)
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


def line_in_footprint(line, mask):
    """Map a transform's world position onto the province raster.

    World x runs with image x; world z is the image y axis inverted, the same
    convention RECT documents.
    """
    parts = line.split()
    if len(parts) < 3:
        return False
    x = int(float(parts[0]))
    y = MAP_SIZE[1] - 1 - int(float(parts[2]))
    if not (0 <= x < MAP_SIZE[0] and 0 <= y < MAP_SIZE[1]):
        return False
    return bool(mask[y, x])


def merge_object_block(ours, now, base, mask):
    ot = transforms(ours)
    nt = transforms(now)
    if not ot or not nt:
        return ours
    om, ol = ot
    nm, nl = nt
    bt = transforms(base) if base else None
    bl = bt[1] if bt else []
    merged = []
    seen = set()
    for line in (
        [x for x in ol if not line_inside(x) and not line_in_footprint(x, mask)]
        + [x for x in nl if line_inside(x)]
        + [x for x in bl if line_in_footprint(x, mask)]
    ):
        if line not in seen:
            seen.add(line)
            merged.append(line)
    body = "\n".join(merged)
    out = ours[: om.start(1)] + body + ours[om.end(1) :]
    out = re.sub(r"(?m)^\tcount=\d+", f"\tcount={len(merged)}", out, count=1)
    return out


def merge_objects(ours, now, base, mask):
    ob = object_blocks(ours)
    nb = object_blocks(now)
    nd = {n: b for n, b, _, _ in nb}
    bd = {n: b for n, b, _, _ in object_blocks(base)} if base else {}
    parts = []
    cursor = 0
    for name, block, start, end in ob:
        parts.append(ours[cursor:start])
        parts.append(
            merge_object_block(block, nd[name], bd.get(name), mask)
            if name in nd
            else block
        )
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


def merge_map_objects(inputs: MapInputs, remap: Remap, mask: np.ndarray) -> None:
    for relative in MAP_PATHS:
        base = read(inputs.agot / relative)
        ours = read(inputs.winner(relative))
        now = read(inputs.now / relative)
        result = (
            merge_locator(base, ours, now, remap)
            if relative.endswith(LOCATOR_SUFFIXES)
            else merge_objects(ours, now, base, mask)
        )
        assert "<<<<<<<" not in result
        inputs.write(relative, result)


# Definition: use current EE/LoV winner, replacing only rows NOW changed from AGOT.
def rows(p):
    lines = read(p).splitlines()
    d = {line.split(";", 1)[0]: line for line in lines if ";" in line}
    return lines, d


def definition_fields(path: Path) -> dict[int, tuple[int, int, int, str]]:
    parsed: dict[int, tuple[int, int, int, str]] = {}
    for line in read(path).splitlines():
        fields = line.split(";")
        if len(fields) < 5 or not fields[0].strip().isdigit():
            continue
        parsed[int(fields[0])] = (
            int(fields[1]),
            int(fields[2]),
            int(fields[3]),
            fields[4].strip(),
        )
    return parsed


@dataclass(frozen=True, slots=True)
class Remap:
    """AGOT's new-region ids and colours as this compatch renumbers them."""

    ids: dict[int, int]
    rgb: dict[int, tuple[int, int, int]]
    names: dict[int, str]

    @property
    def new_first(self) -> int:
        return REMAP_FIRST

    @property
    def new_last(self) -> int:
        return REMAP_FIRST + AGOT_NEW_COUNT - 1

    def new_id(self, old: int) -> int:
        return self.ids[old]

    def as_json(self) -> str:
        return (
            json.dumps(
                {
                    "schema_version": 1,
                    "agot_range": [AGOT_NEW_FIRST, AGOT_NEW_LAST],
                    "merged_range": [self.new_first, self.new_last],
                    "recoloured": {
                        str(old): list(self.rgb[old])
                        for old in sorted(EXPECTED_RECOLOURS)
                    },
                    "ids": {str(old): self.ids[old] for old in sorted(self.ids)},
                    "names": {str(old): self.names[old] for old in sorted(self.names)},
                },
                indent=1,
                sort_keys=False,
            )
            + "\n"
        )


def free_colour(used: set[tuple[int, int, int]]) -> tuple[int, int, int]:
    """Highest RGB value no definition row claims, so the pick is stable."""
    for value in range((1 << 24) - 1, -1, -1):
        rgb = (value >> 16, (value >> 8) & 255, value & 255)
        if rgb not in used:
            return rgb
    raise AssertionError("no free province colour remains")


def build_remap(inputs: MapInputs) -> Remap:
    agot = definition_fields(inputs.agot / "map_data/definition.csv")
    ours = definition_fields(inputs.winner("map_data/definition.csv"))
    new_ids = [i for i in agot if AGOT_NEW_FIRST <= i <= AGOT_NEW_LAST]
    assert new_ids == list(range(AGOT_NEW_FIRST, AGOT_NEW_LAST + 1)), (
        f"AGOT new-region ids are no longer {AGOT_NEW_FIRST}-{AGOT_NEW_LAST}: "
        f"{len(new_ids)} rows"
    )
    assert max(ours) == REMAP_FIRST - 1, (
        f"merged ceiling moved to {max(ours)}; REMAP_FIRST {REMAP_FIRST} would collide"
    )

    used = {value[:3] for value in ours.values()}
    ids: dict[int, int] = {}
    rgb: dict[int, tuple[int, int, int]] = {}
    names: dict[int, str] = {}
    recoloured: dict[int, tuple[int, int, int]] = {}
    for old in new_ids:
        red, green, blue, name = agot[old]
        ids[old] = REMAP_FIRST + (old - AGOT_NEW_FIRST)
        names[old] = name
        if (red, green, blue) in used:
            replacement = free_colour(used | set(recoloured.values()))
            recoloured[old] = replacement
            rgb[old] = replacement
        else:
            rgb[old] = (red, green, blue)
    if recoloured != EXPECTED_RECOLOURS:
        raise AssertionError(
            f"province colour collisions changed: {recoloured} != {EXPECTED_RECOLOURS}"
        )
    assert len(set(rgb.values())) == AGOT_NEW_COUNT, "AGOT new colours are not unique"
    return Remap(ids=ids, rgb=rgb, names=names)


def merge_definition(inputs: MapInputs, remap: Remap) -> None:
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
    while output and not output[-1].strip():
        output.pop()
    for old in sorted(remap.ids):
        red, green, blue = remap.rgb[old]
        output.append(f"{remap.new_id(old)};{red};{green};{blue};{remap.names[old]};x")
    # definition.csv is deliberately BOM-free; Clausewitz treats the BOM as
    # part of the first province id on some startup paths.
    inputs.write("map_data/definition.csv", "\n".join(output) + "\n", "utf-8")


TITLE_PATH = "common/landed_titles/01_agot_landed_titles.txt"

# AGOT 0.5.0 subtrees that carry the new region. The same file also restructures
# Westeros de jure -- d_knellstone, d_ninestars, d_the_northern_mountains and
# c_tormore move counties and baronies NOW already places deliberately. Those
# hold no new-region province, so they stay NOW's and are not grafted.
GRAFT_INTO = {
    "e_daoryrdembos": ("k_lorath", "k_norvos", "k_qohor", "k_the_axe"),
    "c_daarilaro_aajon": ("b_vornegollo",),
}
GRAFT_TOP_LEVEL = ("e_rhoyne",)
EXPECTED_GRAFTED_TITLES = 1380
EXPECTED_GRAFTED_PROVINCES = 1109

TITLE_BLOCK = re.compile(r"^(\s*)([ekdcbx]_[A-Za-z0-9_\-'.]+)\s*=\s*\{")
TITLE_PROVINCE = re.compile(r"^(\s*province\s*=\s*)(\d+)(\s*)$")


def strip_script_comment(line: str) -> str:
    kept: list[str] = []
    quoted = False
    for char in line:
        if char == '"':
            quoted = not quoted
        if char == "#" and not quoted:
            break
        kept.append(char)
    return "".join(kept)


def title_blocks(text: str) -> tuple[list[str], dict[str, tuple[int, int, int]]]:
    """Map every title to its (start, end, depth) line span."""
    lines = text.splitlines()
    nodes: dict[str, tuple[int, int, int]] = {}
    stack: list[tuple[int, str, int]] = []
    depth = 0
    for index, line in enumerate(lines):
        code = strip_script_comment(line)
        match = TITLE_BLOCK.match(code)
        if match:
            stack.append((depth, match.group(2), index))
        depth += code.count("{") - code.count("}")
        while stack and depth <= stack[-1][0]:
            opened, name, start = stack.pop()
            if name in nodes:
                raise AssertionError(f"landed title {name} is defined twice")
            nodes[name] = (start, index + 1, opened)
    assert not stack, "unbalanced landed-titles braces"
    return lines, nodes


def graft_subtree(
    lines: list[str], span: tuple[int, int, int], remap: Remap
) -> list[str]:
    start, end, _ = span
    grafted: list[str] = []
    for line in lines[start:end]:
        match = TITLE_PROVINCE.match(strip_script_comment(line))
        if not match:
            grafted.append(line)
            continue
        old = int(match.group(2))
        if not AGOT_NEW_FIRST <= old <= AGOT_NEW_LAST:
            raise AssertionError(
                f"grafted title references province {old} outside "
                f"{AGOT_NEW_FIRST}-{AGOT_NEW_LAST}"
            )
        grafted.append(f"{match.group(1)}{remap.new_id(old)}{match.group(3)}")
    return grafted


def merge_landed_titles(inputs: MapInputs, remap: Remap) -> set[str]:
    """Add AGOT's new region to the landed titles NOW wins at this path.

    Returns every title the merged file defines, so the strip below can tell a
    title that is genuinely gone from one this file re-supplies.
    """
    agot_lines, agot = title_blocks(read(inputs.agot / TITLE_PATH))
    now_lines, now = title_blocks(read(inputs.now / TITLE_PATH))

    grafted_titles = 0
    grafted_provinces = 0
    insertions: dict[int, list[str]] = {}
    for parent, children in GRAFT_INTO.items():
        if parent not in now:
            raise AssertionError(f"NOW no longer defines {parent}")
        for child in children:
            if child in now:
                raise AssertionError(
                    f"NOW now defines {child}; the graft would duplicate it"
                )
            span = agot[child]
            if span[2] != now[parent][2] + 1:
                raise AssertionError(
                    f"{child} sits at a different depth than {parent}'s children"
                )
            block = graft_subtree(agot_lines, span, remap)
            insertions.setdefault(now[parent][1] - 1, []).extend(block)
            grafted_titles += sum(
                1 for line in block if TITLE_BLOCK.match(strip_script_comment(line))
            )
            grafted_provinces += sum(
                1 for line in block if TITLE_PROVINCE.match(strip_script_comment(line))
            )

    output = list(now_lines)
    for index in sorted(insertions, reverse=True):
        output[index:index] = insertions[index]

    for name in GRAFT_TOP_LEVEL:
        if name in now:
            raise AssertionError(
                f"NOW now defines {name}; the graft would duplicate it"
            )
        span = agot[name]
        if span[2] != 0:
            raise AssertionError(f"{name} is no longer a top-level title")
        block = graft_subtree(agot_lines, span, remap)
        output.append("")
        output.extend(block)
        grafted_titles += sum(
            1 for line in block if TITLE_BLOCK.match(strip_script_comment(line))
        )
        grafted_provinces += sum(
            1 for line in block if TITLE_PROVINCE.match(strip_script_comment(line))
        )

    if grafted_titles != EXPECTED_GRAFTED_TITLES:
        raise AssertionError(
            f"grafted title count changed: {grafted_titles} != {EXPECTED_GRAFTED_TITLES}"
        )
    if grafted_provinces != EXPECTED_GRAFTED_PROVINCES:
        raise AssertionError(
            f"grafted province count changed: {grafted_provinces} != "
            f"{EXPECTED_GRAFTED_PROVINCES}"
        )
    inputs.write(TITLE_PATH, "\n".join(output) + "\n")
    return set(title_blocks("\n".join(output))[1])


TITLE_CAPITAL = re.compile(r"^(\s*capital\s*=\s*)([ekdcbx]_[A-Za-z0-9_\-'.]+)(\s*)$")


def title_provinces(
    lines: list[str], nodes: dict[str, tuple[int, int, int]]
) -> dict[str, int]:
    """Province id per barony, read from the span each barony owns."""
    found: dict[str, int] = {}
    for name, (start, end, _) in nodes.items():
        if not name.startswith("b_"):
            continue
        for line in lines[start:end]:
            match = re.search(r"\bprovince\s*=\s*(\d+)", strip_script_comment(line))
            if match:
                found[name] = int(match.group(1))
                break
    return found


def title_tree(
    nodes: dict[str, tuple[int, int, int]],
) -> tuple[dict[str, str | None], dict[str, list[str]]]:
    """Parent and child links, derived from span containment in one pass."""
    order = sorted(nodes, key=lambda name: (nodes[name][0], -nodes[name][1]))
    parent: dict[str, str | None] = {}
    children: dict[str, list[str]] = {name: [] for name in nodes}
    stack: list[str] = []
    for name in order:
        start, _, _ = nodes[name]
        while stack and nodes[stack[-1]][1] <= start:
            stack.pop()
        parent[name] = stack[-1] if stack else None
        if stack:
            children[stack[-1]].append(name)
        stack.append(name)
    return parent, children


def descendants(children: dict[str, list[str]], name: str) -> list[str]:
    """Titles nested inside `name`, itself excluded, in document order."""
    out: list[str] = []
    stack = list(reversed(children[name]))
    while stack:
        current = stack.pop()
        out.append(current)
        stack.extend(reversed(children[current]))
    return out


def absorbed_provinces(inputs: MapInputs) -> set[int]:
    """Provinces held by the upstream subtrees the graft replaces."""
    absorbed: set[int] = set()
    for relative, roots in REPLACED_SUBTREES.items():
        lines, nodes = title_blocks(read(inputs.winner(relative)))
        _, children = title_tree(nodes)
        provinces = title_provinces(lines, nodes)
        for root in roots:
            if root not in nodes:
                raise AssertionError(f"{relative} no longer defines {root}")
            absorbed.update(
                provinces[name]
                for name in descendants(children, root)
                if name in provinces
            )
    if len(absorbed) != EXPECTED_ABSORBED_PROVINCES:
        raise AssertionError(
            f"replaced-subtree province count changed: {len(absorbed)} != "
            f"{EXPECTED_ABSORBED_PROVINCES}"
        )
    return absorbed


def absorb_mask(
    inputs: MapInputs, absorbed: set[int], footprint: np.ndarray
) -> np.ndarray:
    """Pixels of the replaced subtrees that AGOT's paste does not already cover."""
    ours = definition_fields(inputs.winner("map_data/definition.csv"))
    keys = np.array(
        sorted(
            (ours[pid][0] << 16) | (ours[pid][1] << 8) | ours[pid][2]
            for pid in absorbed
            if pid in ours
        ),
        dtype=np.uint32,
    )
    packed, _ = packed_rgb(inputs.winner("map_data/provinces.png"))
    mask = np.isin(packed, keys) & ~footprint
    remaining = int(mask.sum())
    if remaining != EXPECTED_ABSORBED_PIXELS:
        raise AssertionError(
            f"replaced-subtree remnant changed: {remaining} != "
            f"{EXPECTED_ABSORBED_PIXELS} pixels"
        )
    return mask


def fill_from_neighbours(image: np.ndarray, holes: np.ndarray) -> None:
    """Grow the surrounding provinces into `holes`, in place.

    The remnants are one- to two-pixel slivers along AGOT's new coastline, so a
    fixed-order flood from the four neighbours settles in a few passes and gives
    the same result on every run.
    """
    todo = holes.copy()
    while todo.any():
        before = int(todo.sum())
        for axis, shift in ((0, 1), (0, -1), (1, 1), (1, -1)):
            source = np.roll(image, shift, axis=axis)
            available = np.roll(~todo, shift, axis=axis)
            take = todo & available
            image[take] = source[take]
            todo &= ~take
        if int(todo.sum()) == before:
            raise AssertionError("a remnant sliver has no resolved neighbour")


def strip_landless_titles(
    inputs: MapInputs, pixel_free: set[int]
) -> tuple[set[str], int]:
    """Re-emit the upstream title files without titles that have lost their land."""
    removed: set[str] = set()
    stripped_baronies = 0
    for relative in STRIPPED_TITLE_FILES:
        lines, nodes = title_blocks(read(inputs.winner(relative)))
        parent, children = title_tree(nodes)
        provinces = title_provinces(lines, nodes)

        doomed = {
            name for name, province in provinces.items() if province in pixel_free
        }
        for root in REPLACED_SUBTREES.get(relative, ()):
            doomed.add(root)
            doomed.update(descendants(children, root))
        stripped_baronies += sum(1 for name in doomed if name in provinces)

        # A title survives only if some barony under it still holds land.
        keep = {name for name in provinces if name not in doomed}
        for name in list(keep):
            current = parent[name]
            while current is not None and current not in keep:
                keep.add(current)
                current = parent[current]
        gone = set(nodes) - keep
        removed |= gone

        # Delete only the outermost removed spans; the rest are inside them.
        drop = np.zeros(len(lines), dtype=bool)
        for name in gone:
            if parent[name] is None or parent[name] in keep:
                start, end, _ = nodes[name]
                drop[start:end] = True

        # Retarget capitals that pointed into a removed subtree.
        owner_of = [None] * len(lines)
        for name in sorted(keep, key=lambda n: nodes[n][1] - nodes[n][0], reverse=True):
            start, end, _ = nodes[name]
            for index in range(start, end):
                owner_of[index] = name
        for index, line in enumerate(lines):
            if drop[index]:
                continue
            match = TITLE_CAPITAL.match(strip_script_comment(line))
            if not match or match.group(2) in keep:
                continue
            owner = owner_of[index]
            replacement = next(
                (
                    child
                    for child in (descendants(children, owner) if owner else [])
                    if child.startswith("c_") and child in keep
                ),
                None,
            )
            if replacement is None:
                drop[index] = True
            else:
                lines[index] = f"{match.group(1)}{replacement}{match.group(3)}"

        output = [line for index, line in enumerate(lines) if not drop[index]]
        inputs.write(relative, "\n".join(output).rstrip("\n") + "\n")

    if stripped_baronies != EXPECTED_STRIPPED_BARONIES:
        raise AssertionError(
            f"landless barony count changed: {stripped_baronies} != "
            f"{EXPECTED_STRIPPED_BARONIES}"
        )
    if len(removed) != EXPECTED_SOURCE_STRIPPED_TITLES:
        raise AssertionError(
            f"stripped title count changed: {len(removed)} != "
            f"{EXPECTED_SOURCE_STRIPPED_TITLES}"
        )
    return removed, stripped_baronies


def merge_sothoryos_titles(inputs: MapInputs) -> None:
    """Give the two disjoint Sothoryos trees one top-level empire owner."""
    generic_relative = "common/landed_titles/01_landed_titles.txt"
    generic_path = inputs.context.output_root / generic_relative
    generic_lines, generic_nodes = title_blocks(read(generic_path))
    generic_parent, generic_children = title_tree(generic_nodes)
    root = "e_sothoryos"
    if generic_parent.get(root) is not None:
        raise AssertionError("Further East e_sothoryos is no longer top-level")
    moved = descendants(generic_children, root)
    kingdoms = generic_children[root]
    if len(moved) != EXPECTED_RELOCATED_SOTHORYOS_TITLES:
        raise AssertionError(
            f"relocated Sothoryos title count changed: {len(moved)} != "
            f"{EXPECTED_RELOCATED_SOTHORYOS_TITLES}"
        )
    if len(kingdoms) != EXPECTED_RELOCATED_SOTHORYOS_KINGDOMS or not all(
        title.startswith("k_") for title in kingdoms
    ):
        raise AssertionError("Further East Sothoryos kingdom roots changed")

    lov_lines, lov_nodes = title_blocks(read(inputs.lov / LOV_SOTHORYOS_TITLES))
    lov_parent, _ = title_tree(lov_nodes)
    if lov_parent.get(root) is not None:
        raise AssertionError("LoV e_sothoryos is no longer top-level")
    overlap = sorted(set(moved) & set(lov_nodes))
    if overlap:
        raise AssertionError(f"Sothoryos title trees now overlap: {overlap[:10]}")

    moved_lines: list[str] = []
    for kingdom in kingdoms:
        start, end, _ = generic_nodes[kingdom]
        moved_lines.extend(generic_lines[start:end])

    generic_start, generic_end, _ = generic_nodes[root]
    remaining = generic_lines[:generic_start] + generic_lines[generic_end:]
    inputs.write(generic_relative, "\n".join(remaining).rstrip("\n") + "\n")

    _, lov_end, _ = lov_nodes[root]
    merged_lov = (
        lov_lines[: lov_end - 1] + [""] + moved_lines + lov_lines[lov_end - 1 :]
    )
    inputs.write(LOV_SOTHORYOS_TITLES, "\n".join(merged_lov).rstrip("\n") + "\n")


HISTORY_BLOCK = re.compile(r"^(\S+)\s*=\s*\{")


def history_blocks(text: str) -> tuple[list[str], list[tuple[str, int, int]]]:
    """Top-level `key = { ... }` spans of a history file, in document order."""
    lines = text.splitlines()
    blocks: list[tuple[str, int, int]] = []
    depth = 0
    open_key: str | None = None
    open_at = 0
    for index, line in enumerate(lines):
        code = strip_script_comment(line)
        if depth == 0:
            match = HISTORY_BLOCK.match(code)
            if match:
                open_key = match.group(1)
                open_at = index
        depth += code.count("{") - code.count("}")
        if depth == 0 and open_key is not None:
            blocks.append((open_key, open_at, index + 1))
            open_key = None
    assert depth == 0, "unbalanced history braces"
    return lines, blocks


def strip_title_history(inputs: MapInputs, removed: set[str]) -> None:
    """Drop upstream title history addressing titles the strip removed."""
    dropped = 0
    for relative in STRIPPED_HISTORY_FILES:
        lines, blocks = history_blocks(read(inputs.winner(relative)))
        drop = np.zeros(len(lines), dtype=bool)
        for key, start, end in blocks:
            if key in removed:
                drop[start:end] = True
                dropped += 1
        output = [line for index, line in enumerate(lines) if not drop[index]]
        inputs.write(relative, "\n".join(output).rstrip("\n") + "\n")
    if dropped != EXPECTED_STRIPPED_HISTORY:
        raise AssertionError(
            f"stripped title-history count changed: {dropped} != "
            f"{EXPECTED_STRIPPED_HISTORY}"
        )


def merge_province_history(inputs: MapInputs, remap: Remap) -> None:
    """Replay AGOT's province history for the new region at the renumbered ids."""
    emitted: dict[int, list[str]] = {}
    for relative in AGOT_PROVINCE_HISTORY:
        lines, blocks = history_blocks(read(inputs.agot / relative))
        for key, start, end in blocks:
            if not key.isdigit():
                continue
            old = int(key)
            if not AGOT_NEW_FIRST <= old <= AGOT_NEW_LAST:
                continue
            new = remap.new_id(old)
            if new in emitted:
                raise AssertionError(f"province {old} has history in two AGOT files")
            body = list(lines[start:end])
            head = re.sub(r"^\s*\d+", str(new), body[0], count=1)
            emitted[new] = [head, *body[1:]]
    if len(emitted) != EXPECTED_REMAPPED_HISTORY:
        raise AssertionError(
            f"AGOT new-region province history changed: {len(emitted)} != "
            f"{EXPECTED_REMAPPED_HISTORY}"
        )

    output = [
        f"# AGOT {AGOT_NEW_FIRST}-{AGOT_NEW_LAST} province history, replayed at the",
        f"# ids this compatch renumbers that region onto ({remap.new_first}-"
        f"{remap.new_last}). Generated; do not edit.",
        "",
    ]
    for new in sorted(emitted):
        output.extend(emitted[new])
        output.append("")
    inputs.write(PROVINCE_HISTORY_OUTPUT, "\n".join(output).rstrip("\n") + "\n")


def migrate_consumed_county_capitals(inputs: MapInputs) -> None:
    """Move authored LoV capital history onto each first surviving barony."""
    source_lines, source_nodes = title_blocks(read(inputs.winner(LOV_VOLANTIS_TITLES)))
    _, source_children = title_tree(source_nodes)
    source_provinces = title_provinces(source_lines, source_nodes)

    output_lines, output_nodes = title_blocks(
        read(inputs.context.output_root / LOV_VOLANTIS_TITLES)
    )
    _, output_children = title_tree(output_nodes)
    output_provinces = title_provinces(output_lines, output_nodes)

    for county, (
        old_barony,
        old_province,
        new_barony,
        new_province,
    ) in CONSUMED_CAPITAL_MIGRATIONS.items():
        source_baronies = [
            title for title in source_children[county] if title.startswith("b_")
        ]
        output_baronies = [
            title for title in output_children[county] if title.startswith("b_")
        ]
        actual = (
            source_baronies[0],
            source_provinces[source_baronies[0]],
            output_baronies[0],
            output_provinces[output_baronies[0]],
        )
        expected = (old_barony, old_province, new_barony, new_province)
        if actual != expected:
            raise AssertionError(
                f"{county} capital migration changed: {actual} != {expected}"
            )

    text = read(inputs.winner(LOV_VOLANTIS_PROVINCE_HISTORY))
    lines, blocks = history_blocks(text)
    spans = {int(key): (start, end) for key, start, end in blocks if key.isdigit()}
    replacements: dict[int, list[str]] = {}
    for county, (
        _,
        old_province,
        _,
        new_province,
    ) in CONSUMED_CAPITAL_MIGRATIONS.items():
        old_start, old_end = spans[old_province]
        new_start, new_end = spans[new_province]
        old_block = lines[old_start:old_end]
        new_block = lines[new_start:new_end]
        old_text = "\n".join(old_block)
        new_text = "\n".join(new_block)
        for required in ("culture =", "religion =", "holding ="):
            if required not in old_text:
                raise AssertionError(
                    f"{county} source capital {old_province} lacks {required}"
                )
        if re.sub(r"\s+", " ", new_text).strip() != (
            f"{new_province} = {{ holding = none }}"
        ):
            raise AssertionError(
                f"{county} destination {new_province} is no longer empty"
            )
        moved = list(old_block)
        moved[0] = re.sub(
            rf"^(\s*){old_province}",
            rf"\g<1>{new_province}",
            moved[0],
            count=1,
        )
        replacements[old_start] = [f"{old_province} = {{ holding = none }}"]
        replacements[new_start] = moved

    for start in sorted(replacements, reverse=True):
        _, end = spans[int(HISTORY_BLOCK.match(lines[start]).group(1))]
        lines[start:end] = replacements[start]

    migrated = "\n".join(lines).rstrip("\n") + "\n"
    for county, (_, _, _, new_province) in CONSUMED_CAPITAL_MIGRATIONS.items():
        _, migrated_blocks = history_blocks(migrated)
        block_span = next(
            (start, end)
            for key, start, end in migrated_blocks
            if key == str(new_province)
        )
        block_text = "\n".join(migrated.splitlines()[slice(*block_span)])
        if not all(
            required in block_text
            for required in ("culture =", "religion =", "holding =")
        ):
            raise AssertionError(f"{county} migrated capital history is incomplete")
    inputs.write(LOV_VOLANTIS_PROVINCE_HISTORY, migrated)


DEFAULT_MAP_CATEGORIES = (
    "sea_zones",
    "river_provinces",
    "lakes",
    "impassable_mountains",
    "impassable_seas",
)

EXPECTED_SPECIAL_PROVINCES = {
    "lakes": 21,
    "impassable_mountains": 35,
    "river_provinces": 3,
}


def parse_default_map(path: Path) -> dict[str, set[int]]:
    found: dict[str, set[int]] = {name: set() for name in DEFAULT_MAP_CATEGORIES}
    pattern = re.compile(
        r"^\s*("
        + "|".join(DEFAULT_MAP_CATEGORIES)
        + r")\s*=\s*(LIST|RANGE)\s*\{([^}]*)\}"
    )
    for line in read(path).splitlines():
        match = pattern.match(line.split("#", 1)[0])
        if not match:
            continue
        name, kind, body = match.groups()
        values = [int(value) for value in re.findall(r"\d+", body)]
        if kind == "RANGE":
            assert len(values) == 2, f"{path}: malformed {name} RANGE"
            values = list(range(values[0], values[1] + 1))
        found[name].update(values)
    return found


def merge_default_map(inputs: MapInputs, remap: Remap) -> None:
    """Re-declare AGOT's new lakes, mountains and rivers at their merged ids."""
    agot = parse_default_map(inputs.agot / "map_data/default.map")
    ours = parse_default_map(inputs.winner("map_data/default.map"))
    band = set(remap.ids)
    overlap = {name: sorted(values & band) for name, values in ours.items()}
    if any(overlap.values()):
        raise AssertionError(
            "the Essos Expanded lineage now declares special provinces inside "
            f"{AGOT_NEW_FIRST}-{AGOT_NEW_LAST}: "
            + ", ".join(f"{k}={v}" for k, v in overlap.items() if v)
        )

    additions: dict[str, list[int]] = {}
    for name, values in agot.items():
        selected = sorted(values & band)
        if selected:
            additions[name] = [remap.new_id(old) for old in selected]
    counts = {name: len(values) for name, values in additions.items()}
    if counts != EXPECTED_SPECIAL_PROVINCES:
        raise AssertionError(
            f"AGOT new-region special provinces changed: {counts} != "
            f"{EXPECTED_SPECIAL_PROVINCES}"
        )
    declared = {value for values in additions.values() for value in values}
    assert len(declared) == sum(counts.values()), "a province is declared twice"

    lines = read(inputs.winner("map_data/default.map")).rstrip("\n").splitlines()
    lines.append("")
    lines.append(
        f"# AGOT {AGOT_NEW_FIRST}-{AGOT_NEW_LAST}, renumbered to "
        f"{remap.new_first}-{remap.new_last} by this compatch."
    )
    for name in DEFAULT_MAP_CATEGORIES:
        values = additions.get(name)
        if not values:
            continue
        for start in range(0, len(values), 50):
            chunk = " ".join(str(value) for value in values[start : start + 50])
            lines.append(f"{name} = LIST {{ {chunk} }}")
    inputs.write("map_data/default.map", "\n".join(lines) + "\n")


def packed_rgb(path: Path) -> tuple[np.ndarray, np.ndarray]:
    image = np.asarray(Image.open(path).convert("RGB"))
    assert image.shape[1::-1] == MAP_SIZE, f"{path} is not {MAP_SIZE[0]}x{MAP_SIZE[1]}"
    return (
        (image[:, :, 0].astype(np.uint32) << 16)
        | (image[:, :, 1].astype(np.uint32) << 8)
        | image[:, :, 2]
    ), image


def footprint_mask(inputs: MapInputs, remap: Remap) -> np.ndarray:
    """Pixels AGOT paints with one of its new-region colours."""
    agot = definition_fields(inputs.agot / "map_data/definition.csv")
    keys = np.array(
        sorted(
            (agot[old][0] << 16) | (agot[old][1] << 8) | agot[old][2]
            for old in remap.ids
        ),
        dtype=np.uint32,
    )
    packed, _ = packed_rgb(inputs.agot / "map_data/provinces.png")
    mask = np.isin(packed, keys)
    covered = int(mask.sum())
    if covered != EXPECTED_FOOTPRINT_PIXELS:
        raise AssertionError(
            f"AGOT new-region footprint changed: {covered} != "
            f"{EXPECTED_FOOTPRINT_PIXELS} pixels"
        )
    return mask


def pixel_free_provinces(
    inputs: MapInputs, footprint: np.ndarray, absorb: np.ndarray
) -> set[int]:
    """Essos Expanded lineage ids with no pixel left once the paste has landed."""
    packed, _ = packed_rgb(inputs.winner("map_data/provinces.png"))
    surviving = set(np.unique(packed[~(footprint | absorb)]).tolist())
    ours = definition_fields(inputs.winner("map_data/definition.csv"))
    return {
        province
        for province, (red, green, blue, _) in ours.items()
        if ((red << 16) | (green << 8) | blue) not in surviving
    }


def merge_provinces(inputs: MapInputs, mask: np.ndarray, absorb: np.ndarray) -> None:
    """Paste AGOT's new region onto the Essos Expanded lineage province map."""
    agot = definition_fields(inputs.agot / "map_data/definition.csv")
    packed, source = packed_rgb(inputs.agot / "map_data/provinces.png")
    source = source.copy()
    for old, replacement in EXPECTED_RECOLOURS.items():
        red, green, blue = agot[old][:3]
        source[packed == ((red << 16) | (green << 8) | blue)] = replacement
    _, merged = packed_rgb(inputs.winner("map_data/provinces.png"))
    merged = merged.copy()
    merged[mask] = source[mask]
    fill_from_neighbours(merged, absorb)
    out = inputs.context.output_path("map_data/provinces.png")
    out.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(merged).save(out, optimize=True)


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


def composite_footprint(overlay: Path, target: Path, mask_png: Path) -> None:
    """Take `overlay` inside the AGOT new-region footprint, keep `target` outside."""
    staged = target.with_suffix(target.suffix + ".staged")
    subprocess.run(
        ["magick", str(target), str(overlay), str(mask_png), "-composite", str(staged)],
        check=True,
    )
    staged.replace(target)


def merge_rasters(inputs: MapInputs, mask: np.ndarray) -> None:
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

    # NOW's Westeros rectangle and AGOT's new Essos region are disjoint, so the
    # footprint paste lands cleanly on top of the delta composites above.
    with tempfile.TemporaryDirectory() as td:
        mask_png = Path(td) / "agot_new_footprint.png"
        Image.fromarray(np.where(mask, 255, 0).astype(np.uint8), mode="L").save(
            mask_png
        )
        composite_footprint(
            inputs.agot / "map_data/heightmap.png",
            inputs.context.artifact_path("heightmap/heightmap_now_delta_unpacked.png"),
            mask_png,
        )
        for name in ("tree_leaf_01_single_mask.png", "tree_pine_01_a_mask.png"):
            composite_footprint(
                inputs.agot / "content_source/map_objects/masks" / name,
                inputs.context.artifact_path("map_objects/masks/" + name),
                mask_png,
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


def validate_outputs(inputs: MapInputs, remap: Remap, pixel_free: set[int]) -> None:
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

    merged = definition_fields(inputs.context.output_root / "map_data/definition.csv")
    definition_ids = [
        line.split(";", 1)[0]
        for line in read(
            inputs.context.output_root / "map_data/definition.csv"
        ).splitlines()
        if ";" in line
    ]
    assert len(definition_ids) == len(set(definition_ids)), (
        "duplicate province id in definition.csv"
    )
    assert sorted(merged) == list(range(0, remap.new_last + 1)), (
        "definition.csv is no longer a contiguous id range"
    )
    colours = [value[:3] for value in merged.values()]
    assert len(colours) == len(set(colours)), (
        "duplicate province colour in definition.csv"
    )
    assert not any(
        AGOT_NEW_FIRST <= remap.new_id(old) <= AGOT_NEW_LAST for old in remap.ids
    ), "a renumbered province still lands in AGOT's original range"

    locator_ids: set[int] = set()
    for relative in MAP_PATHS:
        if not relative.endswith(LOCATOR_SUFFIXES):
            continue
        text = read(inputs.context.output_root / relative)
        locator_ids.update(
            int(value) for value in re.findall(r"(?m)^[ \t]*id\s*=\s*(\d+)\s*$", text)
        )
    unknown = sorted(value for value in locator_ids if value not in merged)
    assert not unknown, f"locator ids with no definition row: {unknown[:10]}"

    title_outputs = (TITLE_PATH, *STRIPPED_TITLE_FILES, LOV_SOTHORYOS_TITLES)
    title_owners: dict[str, str] = {}
    landless: dict[str, int] = {}
    for relative in title_outputs:
        lines, nodes = title_blocks(read(inputs.context.output_root / relative))
        for title in nodes:
            previous = title_owners.get(title)
            if previous is not None:
                raise AssertionError(
                    f"landed title {title} is defined by both {previous} and {relative}"
                )
            title_owners[title] = relative
        for title, province in title_provinces(lines, nodes).items():
            if province in pixel_free:
                landless[title] = province
    assert not landless, (
        "landed-title outputs still reference pixel-free provinces: "
        f"{sorted(landless.items())[:10]}"
    )

    if inputs.context.options.get("text_only", False):
        return
    packed, _ = packed_rgb(inputs.context.output_root / "map_data/provinces.png")
    present = set(np.unique(packed).tolist())
    declared = {
        (red << 16) | (green << 8) | blue: province
        for province, (red, green, blue, _) in merged.items()
    }
    orphans = sorted(present - set(declared))
    assert not orphans, f"{len(orphans)} province colours have no definition row"
    empty = sorted(declared[key] for key in set(declared) - present)
    consumed = set(empty) - set(remap.ids.values())
    expected_empty = (
        EXPECTED_CONSUMED_ROWS + EXPECTED_BASELINE_EMPTY_ROWS + EXPECTED_ABSORBED_ROWS
    )
    if consumed != pixel_free or len(consumed) != expected_empty:
        raise AssertionError(
            f"pixel-free province rows changed: {len(consumed)} != {expected_empty}; "
            "re-audit which Essos Expanded provinces AGOT's region consumes"
        )
    assert not (set(remap.ids.values()) & set(empty)), (
        "a renumbered AGOT province has no pixels on the merged map"
    )


def generate(context: GenerationContext) -> None:
    inputs = MapInputs.from_context(context)
    verify_source_manifest(inputs)
    remap = build_remap(inputs)
    mask = footprint_mask(inputs, remap)
    absorb = absorb_mask(inputs, absorbed_provinces(inputs), mask)
    pixel_free = pixel_free_provinces(inputs, mask, absorb)
    context.artifact_path("map_data/agot_new_province_remap.json").write_text(
        remap.as_json(), encoding="utf-8", newline="\n"
    )
    merge_map_objects(inputs, remap, mask)
    merge_definition(inputs, remap)
    merge_default_map(inputs, remap)
    supplied = merge_landed_titles(inputs, remap)
    removed, _ = strip_landless_titles(inputs, pixel_free)
    merge_sothoryos_titles(inputs)
    genuinely_removed = removed - supplied
    if len(genuinely_removed) != EXPECTED_STRIPPED_TITLES:
        raise AssertionError(
            f"final removed-title count changed: {len(genuinely_removed)} != "
            f"{EXPECTED_STRIPPED_TITLES}"
        )
    context.artifact_path(REMOVED_TITLES_ARTIFACT).write_text(
        json.dumps(sorted(genuinely_removed), indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    strip_title_history(inputs, genuinely_removed)
    merge_province_history(inputs, remap)
    migrate_consumed_county_capitals(inputs)
    if not context.options.get("text_only", False):
        merge_provinces(inputs, mask, absorb)
        merge_rasters(inputs, mask)
    validate_outputs(inputs, remap, pixel_free)

    print("generated", context.output_root)
    for source in sorted(
        path for path in context.output_root.rglob("*") if path.is_file()
    ):
        print(source.relative_to(context.output_root), source.stat().st_size)
