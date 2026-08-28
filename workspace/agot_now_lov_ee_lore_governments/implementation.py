#!/usr/bin/env python3
"""Generate lore governments and the Ibben faith transition for LoV/EE."""

from __future__ import annotations

import csv
import json
import re
from collections import defaultdict, deque
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from gen import GenerationContext
from gen.data import csv_bytes
from gen.hashing import sha256_file
from gen.script import read_text
from gen.sources import canonical_source_path

DOOM = (7899, 8, 14)
DOOM_TEXT = "7899.8.14"
TIER = {"c": 1, "d": 2, "k": 3, "e": 4}
TARGET_GOVERNMENTS = {
    "administrative_government",
    "celestial_government",
    "clan_government",
    "feudal_government",
    "mandala_government",
    "meritocratic_government",
    "nomad_government",
    "oligarchic_government",
    "pirate_government",
    "pirate_no_dlc_government",
    "theocracy_government",
    "tribal_government",
}
NO_LEGITIMACY = {
    "administrative_government",
    "oligarchic_government",
    "pirate_government",
    "pirate_no_dlc_government",
    "theocracy_government",
}
PRESERVED_SPECIAL_GOVERNMENTS = {
    "landless_adventurer_government",
    "pirate_government",
    "pirate_no_dlc_government",
    "ruins_government",
    "unknown_government",
    "wilderness_government",
}
PLACEHOLDER_HOLDERS = {"0", "Ruin_Empress", "Unknown_Emperor", "Wilderness_Empress"}
WORKSHOP_IDS = {
    "AGOT": "2962333032",
    "LOV": "3403938445",
    "RC": "3719888822",
    "EE": "3682802751",
    "EEP": "3768149491",
    "BRIDGE": "3773608127",
}


@dataclass(frozen=True, slots=True)
class RunInputs:
    root: Path
    workshop_root: Path
    output_root: Path
    assets_dir: Path
    local_sources: dict[str, Path]


@dataclass
class Block:
    ident: int
    key: str
    start: int
    open: int
    close: int
    parent: int | None


@dataclass(frozen=True)
class Scalar:
    key: str
    value: str
    start: int
    end: int
    parent: int | None


@dataclass
class Document:
    text: str
    blocks: list[Block]
    scalars: list[Scalar]

    def children(self, parent: int | None) -> list[Block]:
        return [block for block in self.blocks if block.parent == parent]

    def direct_scalars(self, parent: int, key: str | None = None) -> list[Scalar]:
        return [
            scalar
            for scalar in self.scalars
            if scalar.parent == parent and (key is None or scalar.key == key)
        ]

    def descendants(self, ancestor: Block) -> Iterable[Block]:
        for block in self.blocks:
            if ancestor.open < block.start and block.close < ancestor.close:
                yield block


@dataclass(frozen=True)
class Rule:
    scope_type: str
    scope: str
    start_date: tuple[int, int, int] | None
    end_date: tuple[int, int, int] | None
    min_tier: int | None
    max_tier: int | None
    government: str
    faith: str
    confidence: str
    reason: str
    source_url: str
    row_number: int


@dataclass
class Character:
    key: str
    relative: Path
    block: Block
    culture: str
    religion: str
    birth: tuple[int, int, int] | None
    death: tuple[int, int, int] | None
    relations: set[str]


@dataclass
class HolderEvent:
    relative: Path
    filename: str
    title: str
    empire: str
    tier: int
    date: tuple[int, int, int]
    date_text: str
    holder: str
    block: Block
    holder_scalar: Scalar
    government_scalar: Scalar | None
    culture: str
    rule: Rule | None = None


def parse_date(value: str) -> tuple[int, int, int] | None:
    match = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)", value)
    return tuple(map(int, match.groups())) if match else None


def parse_document(text: str) -> Document:
    blocks: list[Block] = []
    scalars: list[Scalar] = []
    stack: list[int | None] = []
    index = 0
    length = len(text)

    def parent_block() -> int | None:
        return next((value for value in reversed(stack) if value is not None), None)

    while index < length:
        char = text[index]
        if char == "#":
            newline = text.find("\n", index)
            index = length if newline < 0 else newline + 1
            continue
        if char == '"':
            index += 1
            while index < length:
                if text[index] == '"' and text[index - 1] != "\\":
                    index += 1
                    break
                index += 1
            continue
        if char == "{":
            stack.append(None)
            index += 1
            continue
        if char == "}":
            if not stack:
                raise ValueError(f"unmatched closing brace at byte {index}")
            block_id = stack.pop()
            if block_id is not None:
                blocks[block_id].close = index
            index += 1
            continue
        if not (char.isalnum() or char in "_.$"):
            index += 1
            continue

        token_start = index
        while index < length and (text[index].isalnum() or text[index] in "_.$:-"):
            index += 1
        key = text[token_start:index]
        look = index
        while look < length and text[look].isspace():
            look += 1
        if look >= length or text[look] != "=":
            continue
        look += 1
        while look < length and text[look].isspace():
            look += 1
        if look < length and text[look] == "{":
            block_id = len(blocks)
            blocks.append(
                Block(
                    ident=block_id,
                    key=key,
                    start=token_start,
                    open=look,
                    close=-1,
                    parent=parent_block(),
                )
            )
            stack.append(block_id)
            index = look + 1
            continue
        value_start = look
        if look < length and text[look] == '"':
            look += 1
            while look < length:
                if text[look] == '"' and text[look - 1] != "\\":
                    look += 1
                    break
                look += 1
        else:
            while (
                look < length and not text[look].isspace() and text[look] not in "{}#"
            ):
                look += 1
        value = text[value_start:look].strip().strip('"')
        scalars.append(
            Scalar(
                key=key, value=value, start=token_start, end=look, parent=parent_block()
            )
        )
        index = look

    if stack:
        raise ValueError("unterminated brace block")
    if any(block.close < 0 for block in blocks):
        raise ValueError("unterminated assigned block")
    return Document(text=text, blocks=blocks, scalars=scalars)


def scalar_value(document: Document, parent: int, key: str) -> str:
    values = document.direct_scalars(parent, key)
    return values[-1].value if values else ""


def apply_edits(text: str, edits: list[tuple[int, int, str]]) -> str:
    ordered = sorted(edits, key=lambda edit: (edit[0], edit[1]))
    for previous, current in zip(ordered, ordered[1:], strict=False):
        if previous[1] > current[0]:
            raise AssertionError(
                f"overlapping generated edits: {previous} and {current}"
            )
    for start, end, replacement in reversed(ordered):
        text = text[:start] + replacement + text[end:]
    return text


def removal_span(text: str, scalar: Scalar) -> tuple[int, int]:
    line_start = text.rfind("\n", 0, scalar.start) + 1
    line_end = text.find("\n", scalar.end)
    line_end = len(text) if line_end < 0 else line_end + 1
    before = text[line_start : scalar.start]
    after = text[scalar.end : line_end].split("#", 1)[0]
    if not before.strip() and not after.strip():
        return line_start, line_end
    start = scalar.start
    while start > line_start and text[start - 1] in " \t":
        start -= 1
    end = scalar.end
    while end < line_end and text[end] in " \t":
        end += 1
    return start, end


def block_removal_span(text: str, block: Block) -> tuple[int, int]:
    line_start = text.rfind("\n", 0, block.start) + 1
    line_end = text.find("\n", block.close + 1)
    line_end = len(text) if line_end < 0 else line_end + 1
    before = text[line_start : block.start]
    after = text[block.close + 1 : line_end].split("#", 1)[0]
    if not before.strip() and not after.strip():
        return line_start, line_end
    start = block.start
    while start > line_start and text[start - 1] in " \t":
        start -= 1
    end = block.close + 1
    while end < line_end and text[end] in " \t":
        end += 1
    return start, end


def insert_direct_scalar(
    text: str, block: Block, anchor: Scalar, key: str, value: str
) -> tuple[int, int, str]:
    line_end = text.find("\n", anchor.end, block.close)
    if line_end < 0:
        return anchor.end, anchor.end, f" {key} = {value}"
    indent = text[text.rfind("\n", 0, anchor.start) + 1 : anchor.start]
    indent = indent[: len(indent) - len(indent.lstrip())]
    return line_end + 1, line_end + 1, f"{indent}{key} = {value}\n"


def insert_child_block(text: str, block: Block, body: str) -> tuple[int, int, str]:
    line_start = text.rfind("\n", 0, block.start) + 1
    base_indent = text[line_start : block.start]
    base_indent = base_indent[: len(base_indent) - len(base_indent.lstrip())]
    child_indent = base_indent + "\t"
    prefix = "" if text[block.open + 1 : block.close].endswith("\n") else "\n"
    rendered = "\n".join(
        child_indent + line if line else "" for line in body.splitlines()
    )
    return block.close, block.close, f"{prefix}{rendered}\n{base_indent}"


def insert_before_block(text: str, block: Block, body: str) -> tuple[int, int, str]:
    line_start = text.rfind("\n", 0, block.start) + 1
    indent = text[line_start : block.start]
    indent = indent[: len(indent) - len(indent.lstrip())]
    rendered = "\n".join(indent + line if line else "" for line in body.splitlines())
    return line_start, line_start, f"{rendered}\n"


def load_rules(path: Path) -> list[Rule]:
    priority = {"history_file", "empire", "culture", "title"}
    rules: list[Rule] = []
    with path.open(encoding="utf-8", newline="") as handle:
        for row_number, row in enumerate(csv.DictReader(handle), 2):
            if row["scope_type"] not in priority:
                raise ValueError(f"{path}:{row_number}: invalid scope type")
            government = row["government"].strip()
            if government not in TARGET_GOVERNMENTS:
                raise ValueError(
                    f"{path}:{row_number}: unknown target government {government}"
                )
            rules.append(
                Rule(
                    scope_type=row["scope_type"],
                    scope=row["scope"],
                    start_date=parse_date(row["start_date"])
                    if row["start_date"]
                    else None,
                    end_date=parse_date(row["end_date"]) if row["end_date"] else None,
                    min_tier=int(row["min_tier"]) if row["min_tier"] else None,
                    max_tier=int(row["max_tier"]) if row["max_tier"] else None,
                    government=government,
                    faith=row["faith"],
                    confidence=row["confidence"],
                    reason=row["reason"],
                    source_url=row["source_url"],
                    row_number=row_number,
                )
            )
    return rules


def source_winners(
    roots: list[tuple[str, Path]], relative_root: Path, predicate
) -> dict[Path, tuple[str, Path]]:
    winners: dict[Path, tuple[str, Path]] = {}
    for label, root in roots:
        directory = root / relative_root
        if not directory.is_dir():
            continue
        for path in sorted(directory.glob("*.txt")):
            if predicate(path.name):
                relative = relative_root / path.name
                winners[relative] = (label, path)
    return winners


def title_and_province_scope(
    landed_titles_path: Path,
) -> tuple[dict[str, str], dict[int, str]]:
    document = parse_document(read_text(landed_titles_path))
    by_id = {block.ident: block for block in document.blocks}
    title_empire: dict[str, str] = {}
    province_empire: dict[int, str] = {}
    for block in document.blocks:
        if not re.fullmatch(r"[ekdcb]_[A-Za-z0-9_]+", block.key):
            continue
        current: Block | None = block
        empire = ""
        while current is not None:
            if current.key.startswith("e_"):
                empire = current.key
                break
            current = by_id.get(current.parent) if current.parent is not None else None
        if not empire:
            continue
        title_empire[block.key] = empire
        for scalar in document.direct_scalars(block.ident, "province"):
            province_empire[int(scalar.value)] = empire
    return title_empire, province_empire


def merge_character_override(
    texts: dict[Path, str],
    override_relative: Path,
    *,
    base_relatives: set[Path] | None = None,
    label: str,
) -> set[Path]:
    """Fold a late whole-character override into its generated base files."""
    if override_relative not in texts:
        return set()

    base_blocks: dict[str, list[tuple[Path, Block]]] = defaultdict(list)
    for relative, text in texts.items():
        if relative == override_relative:
            continue
        if base_relatives is not None and relative not in base_relatives:
            continue
        document = parse_document(text)
        for block in document.children(None):
            if re.fullmatch(r"[A-Za-z0-9_]+", block.key):
                base_blocks[block.key].append((relative, block))

    override_text = texts[override_relative]
    override_document = parse_document(override_text)
    edits_by_relative: dict[Path, list[tuple[int, int, str]]] = defaultdict(list)
    for override in override_document.children(None):
        if not re.fullmatch(r"[A-Za-z0-9_]+", override.key):
            continue
        matches = base_blocks.get(override.key, [])
        if len(matches) != 1:
            raise AssertionError(
                f"{label} override {override.key}: expected one base character, "
                f"found {len(matches)}"
            )
        relative, base = matches[0]
        edits_by_relative[relative].append(
            (
                base.start,
                base.close + 1,
                override_text[override.start : override.close + 1],
            )
        )

    if not edits_by_relative:
        raise AssertionError(f"{label} override contains no character definitions")
    for relative, edits in edits_by_relative.items():
        texts[relative] = apply_edits(texts[relative], edits)
    del texts[override_relative]
    return set(edits_by_relative)


def parse_character_sources(
    winners: dict[Path, tuple[str, Path]],
) -> tuple[dict[Path, str], dict[Path, Document], dict[str, Character], set[Path]]:
    texts: dict[Path, str] = {}
    documents: dict[Path, Document] = {}
    characters: dict[str, Character] = {}
    relation_keys = {
        "add_matrilineal_spouse",
        "add_same_sex_spouse",
        "add_spouse",
        "father",
        "mother",
    }
    for relative, (_, path) in sorted(winners.items(), key=lambda item: str(item[0])):
        text = read_text(path)
        if relative.name == "bookmark_chars.txt":
            broken = "# Each ruler has: father, 2 siblings (share father), 2 childrengen_719 = {"
            fixed = (
                "# Each ruler has: father, 2 siblings (share father), 2 children\n"
                "gen_719 = {"
            )
            if text.count(broken) != 1:
                raise AssertionError("EE bookmark gen_719 malformed header changed")
            text = text.replace(broken, fixed)
        texts[relative] = text

    merged_relatives = merge_character_override(
        texts,
        Path("history/characters/zz_eetlv_bookmark_char_overrides.txt"),
        base_relatives={Path("history/characters/essos_7898_chars.txt")},
        label="EEP bookmark",
    )
    merged_relatives.update(
        merge_character_override(
            texts,
            Path("history/characters/zz_eetlv_khal_name_fixes.txt"),
            label="EEP khal-name",
        )
    )

    for relative, text in sorted(texts.items(), key=lambda item: str(item[0])):
        document = parse_document(text)
        documents[relative] = document
        for block in document.children(None):
            if not re.fullmatch(r"[A-Za-z0-9_]+", block.key):
                continue
            culture = scalar_value(document, block.ident, "culture")
            religion = scalar_value(document, block.ident, "religion")
            dates = [
                (parse_date(child.key), child)
                for child in document.children(block.ident)
                if parse_date(child.key)
            ]
            birth_dates = [
                date
                for date, child in dates
                if date
                and (
                    document.direct_scalars(child.ident, "birth")
                    or any(
                        grandchild.key == "birth"
                        for grandchild in document.children(child.ident)
                    )
                )
            ]
            death_dates = [
                date
                for date, child in dates
                if date
                and (
                    document.direct_scalars(child.ident, "death")
                    or any(
                        grandchild.key == "death"
                        for grandchild in document.children(child.ident)
                    )
                )
            ]
            relations = {
                scalar.value
                for scalar in document.scalars
                if block.open < scalar.start < block.close
                and scalar.key in relation_keys
                and re.fullmatch(r"[A-Za-z0-9_]+", scalar.value)
            }
            character = Character(
                key=block.key,
                relative=relative,
                block=block,
                culture=culture,
                religion=religion,
                birth=min(birth_dates) if birth_dates else None,
                death=min(death_dates) if death_dates else None,
                relations=relations,
            )
            existing = characters.get(block.key)
            if existing and existing.relative == relative:
                raise AssertionError(
                    f"duplicate character ID {block.key} in {relative}"
                )
            characters[block.key] = character
    return texts, documents, characters, merged_relatives


def rule_priority(rule: Rule) -> int:
    return {"history_file": 70, "empire": 80, "culture": 90, "title": 100}[
        rule.scope_type
    ]


def matching_rule(event: HolderEvent, rules: list[Rule]) -> Rule | None:
    matches: list[Rule] = []
    for rule in rules:
        scope_match = {
            "title": event.title == rule.scope,
            "culture": event.culture == rule.scope,
            "empire": event.empire == rule.scope,
            "history_file": event.filename == rule.scope,
        }[rule.scope_type]
        if not scope_match:
            continue
        if rule.start_date and event.date < rule.start_date:
            continue
        if rule.end_date and event.date > rule.end_date:
            continue
        if rule.min_tier and event.tier < rule.min_tier:
            continue
        if rule.max_tier and event.tier > rule.max_tier:
            continue
        matches.append(rule)
    if not matches:
        return None
    priority = max(rule_priority(rule) for rule in matches)
    winners = [rule for rule in matches if rule_priority(rule) == priority]
    values = {(rule.government, rule.faith) for rule in winners}
    if len(values) != 1:
        raise AssertionError(
            f"conflicting rules for {event.title}/{event.holder}/{event.date_text}: "
            f"{[(rule.row_number, rule.government) for rule in winners]}"
        )
    return winners[0]


def family_closure(
    seeds: set[str],
    characters: dict[str, Character],
    holder_empires: dict[str, set[str]],
    empire: str,
) -> set[str]:
    graph: dict[str, set[str]] = defaultdict(set)
    for character in characters.values():
        for relation in character.relations:
            if relation in characters:
                graph[character.key].add(relation)
                graph[relation].add(character.key)
    result = set(seeds)
    queue = deque(sorted(seeds))
    while queue:
        current = queue.popleft()
        for neighbor in graph.get(current, set()):
            if neighbor in result:
                continue
            outside = holder_empires.get(neighbor, set()) - {empire}
            if outside:
                continue
            result.add(neighbor)
            queue.append(neighbor)
    return result


def transform_effect(text: str) -> str:
    if "### LORE GOVERNMENT INTEGRATION ###" in text:
        raise AssertionError("bridge input already contains lore integration")
    upstream_mappings = (
        "\t\t\tnomad_government = { assign_government_data_effect = { GOV = tribal SCOPE = $SCOPE$ } }\n"
        "\t\t\tcelestial_government = { assign_government_data_effect = { GOV = feudal SCOPE = $SCOPE$ } }\n"
    )
    if text.count(upstream_mappings) != 1:
        raise AssertionError(
            "bridge nomad/celestial historical-government mappings changed"
        )
    text = text.replace(
        upstream_mappings,
        upstream_mappings
        + "\t\t\t# Lore governments reuse AGOT's feudal historical-title path.\n"
        + "\t\t\tmeritocratic_government = { assign_government_data_effect = { GOV = feudal SCOPE = $SCOPE$ } }\n"
        + "\t\t\tmandala_government = { assign_government_data_effect = { GOV = feudal SCOPE = $SCOPE$ } }\n",
        1,
    )
    fallback_needle = (
        "\t\t\tif = {\n"
        "\t\t\t\tlimit = { $SCOPE$.primary_title.previous_holder ?= { agot_ruler_is_government_trigger = { GOV = landless_adventurer } } }\n"
    )
    if text.count(fallback_needle) != 1:
        raise AssertionError("fallback government insertion point changed")
    fallback_add = ""
    for short in ("meritocratic", "mandala"):
        fallback_add += (
            "\t\t\tif = {\n"
            f"\t\t\t\tlimit = {{ $SCOPE$.primary_title.previous_holder ?= {{ agot_ruler_is_government_trigger = {{ GOV = {short} }} }} }}\n"
            "\t\t\t\tset_variable = {\n"
            "\t\t\t\t\tname = temp_government_type\n"
            "\t\t\t\t\tvalue = flag:feudal\n"
            "\t\t\t\t\tdays = 1\n"
            "\t\t\t\t}\n"
            "\t\t\t}\n"
        )
    text = text.replace(fallback_needle, fallback_add + fallback_needle)
    # The bridge names `jogos_nhai` in both arms of its own flavor branch, so
    # this module only asserts that state instead of rewriting the culture.
    if text.count("culture = culture:jogos_nhai") != 2:
        raise AssertionError("Jogos flavor branch changed")
    dothraki_branch = (
        "\t\t\t\t\t\t\tculture = culture:dothraki\n"
        "\t\t\t\t\t\t\tOR = {\n"
        "\t\t\t\t\t\t\t\thas_government = tribal_government\n"
        "\t\t\t\t\t\t\t\thas_government = nomad_government\n"
        "\t\t\t\t\t\t\t}\n"
    )
    if text.count(dothraki_branch) != 5:
        raise AssertionError("Dothraki flavor government ladder changed")
    ibben_needle = "\t\t\t\t\t\t\tculture = culture:ibbatese\n"
    if text.count(ibben_needle) != 1:
        raise AssertionError("Ibben flavor branch changed")
    text = text.replace(
        ibben_needle, ibben_needle + "\t\t\t\t\t\t\tfaith = faith:ib_ven_god_king\n"
    )
    if text.count("ee_yiti_governor_male") != 1:
        raise AssertionError("Yi Ti governor title branch changed")
    for short in ("nomad", "celestial", "meritocratic", "mandala"):
        if f"{short}_government_list" in text:
            raise AssertionError(f"unexpected {short} historical-government list")
    return text


def target_manifest(
    root: Path, workshop: dict[str, Path], workshop_root: Path, inputs: Iterable[Path]
) -> dict[str, object]:
    files = {
        canonical_source_path(path, root=root, workshop_root=workshop_root): {
            "sha256": sha256_file(path),
            "size": path.stat().st_size,
        }
        for path in sorted(set(inputs))
    }
    versions: dict[str, str] = {}
    for label, module_root in workshop.items():
        descriptor = module_root / "descriptor.mod"
        if descriptor.is_file():
            match = re.search(r'(?m)^\s*version\s*=\s*"([^"]+)"', read_text(descriptor))
            versions[label] = match.group(1) if match else "unversioned"
    return {
        "schema_version": 1,
        "workshop_ids": WORKSHOP_IDS,
        "versions": versions,
        "doom_date": DOOM_TEXT,
        "files": files,
    }


@dataclass
class LoreGovernmentPipeline:
    """Run the ordered generation phases without module-global state."""

    inputs: RunInputs

    def run(self) -> None:
        self.load_sources()
        self.plan_government_edits()
        self.add_transition_edits()
        self.render_title_edits()
        self.build_character_outputs()
        self.build_province_outputs()
        self.write_outputs()

    def load_sources(self) -> None:
        root = self.inputs.root
        workshop_root = self.inputs.workshop_root
        workshop = {
            label: workshop_root / workshop_id
            for label, workshop_id in WORKSHOP_IDS.items()
        }
        missing = [
            f"{label}:{path}" for label, path in workshop.items() if not path.is_dir()
        ]
        if missing:
            raise FileNotFoundError(f"missing Workshop modules: {missing}")

        self.module = self.inputs.output_root
        assets = self.inputs.assets_dir
        rules_path = assets / "government_lore_rules.csv"
        manifest_path = assets / "source_manifest.json"
        self.effect_source = (
            workshop["BRIDGE"]
            / "common/scripted_effects/replace/00_agot_character_data_effects.txt"
        )
        local_sources = self.inputs.local_sources
        roots = [
            ("LOV", workshop["LOV"]),
            ("RC", workshop["RC"]),
            (
                "LOV_REBASE",
                local_sources.get(
                    "LOV_REBASE", root / "mods/legacy_of_valyria_bridge_runtime_rebase"
                ),
            ),
            ("EE", workshop["EE"]),
            ("EEP", workshop["EEP"]),
            (
                "EE_REBASE",
                local_sources.get(
                    "EE_REBASE", root / "mods/essos_expanded_further_east_rebase"
                ),
            ),
        ]
        self.title_winners = source_winners(
            roots,
            Path("history/titles"),
            lambda name: (
                name == "hist_titles.txt"
                or name.startswith("vassal_titles_e_")
                or name.startswith("lv_")
                or name == "agot_sothori_history_titles.txt"
            ),
        )
        self.character_winners = source_winners(
            roots, Path("history/characters"), lambda _name: True
        )
        self.province_winners = source_winners(
            roots, Path("history/provinces"), lambda name: name == "k_generated.txt"
        )
        if Path("history/provinces/k_generated.txt") not in self.province_winners:
            raise FileNotFoundError(
                "effective EE k_generated province history not found"
            )

        # Further East ships the last common/landed_titles/01_landed_titles.txt in
        # the playset, so its file is the effective eastern title tree.
        landed_titles = workshop["EEP"] / "common/landed_titles/01_landed_titles.txt"
        input_paths = [
            rules_path,
            self.effect_source,
            landed_titles,
            workshop["AGOT"] / "common/governments/00_government_types.txt",
            workshop["AGOT"]
            / "common/religion/religion_types/00_agot_the_venerations.txt",
            *[path for _, path in self.title_winners.values()],
            *[path for _, path in self.character_winners.values()],
            *[path for _, path in self.province_winners.values()],
        ]
        current_manifest = target_manifest(root, workshop, workshop_root, input_paths)
        if not manifest_path.is_file():
            raise FileNotFoundError(
                f"{manifest_path.relative_to(root)} is missing; review the upstream "
                "inputs and replace the reviewed asset deliberately"
            )
        if json.loads(manifest_path.read_text(encoding="utf-8")) != current_manifest:
            raise AssertionError(
                "upstream source manifest drifted; review the differences and replace "
                f"{manifest_path.relative_to(root)} deliberately"
            )

        self.rules = load_rules(rules_path)
        self.title_empire, self.province_empire = title_and_province_scope(
            landed_titles
        )
        (
            self.character_texts,
            self.character_documents,
            self.characters,
            self.merged_character_relatives,
        ) = parse_character_sources(self.character_winners)

    def plan_government_edits(self) -> None:
        self.title_texts: dict[Path, str] = {}
        self.title_documents: dict[Path, Document] = {}
        events: list[HolderEvent] = []
        holder_empires: dict[str, set[str]] = defaultdict(set)
        for relative, (_, path) in sorted(
            self.title_winners.items(), key=lambda item: str(item[0])
        ):
            text = read_text(path)
            document = parse_document(text)
            self.title_texts[relative] = text
            self.title_documents[relative] = document
            for title_block in document.children(None):
                if not re.fullmatch(r"[ekdc]_[A-Za-z0-9_]+", title_block.key):
                    continue
                tier = TIER[title_block.key[0]]
                empire = self.title_empire.get(title_block.key, "")
                for date_block in document.children(title_block.ident):
                    date = parse_date(date_block.key)
                    if not date:
                        continue
                    holders = document.direct_scalars(date_block.ident, "holder")
                    if not holders:
                        continue
                    holder_scalar = holders[-1]
                    holder = holder_scalar.value
                    if holder in PLACEHOLDER_HOLDERS or any(
                        word in holder.lower()
                        for word in ("ruin", "wilderness", "unknown")
                    ):
                        continue
                    governments = document.direct_scalars(
                        date_block.ident, "government"
                    )
                    culture = (
                        self.characters.get(holder).culture
                        if holder in self.characters
                        else ""
                    )
                    event = HolderEvent(
                        relative=relative,
                        filename=relative.name,
                        title=title_block.key,
                        empire=empire,
                        tier=tier,
                        date=date,
                        date_text=date_block.key,
                        holder=holder,
                        block=date_block,
                        holder_scalar=holder_scalar,
                        government_scalar=governments[-1] if governments else None,
                        culture=culture,
                    )
                    events.append(event)
                    if empire:
                        holder_empires[holder].add(empire)

        jogos_seeds = {
            event.holder for event in events if event.empire == "e_jogos_nhai"
        }
        ibben_seeds = {event.holder for event in events if event.empire == "e_ibben"}
        self.jogos_characters = family_closure(
            jogos_seeds, self.characters, holder_empires, "e_jogos_nhai"
        )
        self.ibben_characters = family_closure(
            ibben_seeds, self.characters, holder_empires, "e_ibben"
        )
        self.corrected_culture = {
            key: (
                "jogos_nhai"
                if key in self.jogos_characters and char.culture == "nefer"
                else char.culture
            )
            for key, char in self.characters.items()
        }
        for event in events:
            event.culture = self.corrected_culture.get(event.holder, event.culture)
            event.rule = matching_rule(event, self.rules)

        event_groups: dict[tuple[str, tuple[int, int, int]], list[HolderEvent]] = (
            defaultdict(list)
        )
        for event in events:
            event_groups[(event.holder, event.date)].append(event)

        self.title_edits: dict[Path, list[tuple[int, int, str]]] = defaultdict(list)
        self.government_at_date: dict[tuple[str, tuple[int, int, int]], str] = {}
        self.government_audit: list[dict[str, object]] = []
        for (holder, date), group in sorted(event_groups.items()):
            candidates = [event for event in group if event.rule is not None]
            if not candidates:
                continue
            specials = [
                event
                for event in group
                if event.government_scalar
                and event.government_scalar.value in PRESERVED_SPECIAL_GOVERNMENTS
            ]
            if specials:
                special_values = {event.government_scalar.value for event in specials}
                if len(special_values) != 1:
                    raise AssertionError(
                        f"conflicting preserved governments for {holder}/{date}: {special_values}"
                    )
                target_government = next(iter(special_values))
                target_rule = max(
                    candidates, key=lambda event: rule_priority(event.rule)
                )
            else:
                max_tier = max(event.tier for event in candidates)
                ranked = [event for event in candidates if event.tier == max_tier]
                max_priority = max(rule_priority(event.rule) for event in ranked)
                ranked = [
                    event
                    for event in ranked
                    if rule_priority(event.rule) == max_priority
                ]
                target_values = {event.rule.government for event in ranked}
                if len(target_values) != 1:
                    raise AssertionError(
                        f"ambiguous government for {holder}/{date}: "
                        f"{[(event.title, event.rule.government) for event in ranked]}"
                    )
                target_government = next(iter(target_values))
                target_rule = sorted(ranked, key=lambda event: event.title)[0]
            insertion_candidates = [
                event
                for event in group
                if event.tier == max(item.tier for item in group)
            ]
            insertion = sorted(insertion_candidates, key=lambda event: event.title)[0]
            old_values = {
                event.government_scalar.value
                for event in group
                if event.government_scalar
            }
            for event in group:
                scalar = event.government_scalar
                if event is insertion:
                    if scalar:
                        self.title_edits[event.relative].append(
                            (
                                scalar.start,
                                scalar.end,
                                f"government = {target_government}",
                            )
                        )
                    else:
                        self.title_edits[event.relative].append(
                            insert_direct_scalar(
                                self.title_texts[event.relative],
                                event.block,
                                event.holder_scalar,
                                "government",
                                target_government,
                            )
                        )
                elif scalar:
                    start, end = removal_span(self.title_texts[event.relative], scalar)
                    self.title_edits[event.relative].append((start, end, ""))
            self.government_at_date[(holder, date)] = target_government
            self.government_audit.append(
                {
                    "date": target_rule.date_text,
                    "holder": holder,
                    "culture": target_rule.culture,
                    "title": insertion.title,
                    "tier": insertion.tier,
                    "empire": insertion.empire,
                    "source_file": insertion.relative.as_posix(),
                    "old_government": "|".join(sorted(old_values)),
                    "new_government": target_government,
                    "rule_type": target_rule.rule.scope_type,
                    "rule_scope": target_rule.rule.scope,
                    "confidence": target_rule.rule.confidence,
                }
            )

    def add_transition_edits(self) -> None:
        transition_dates = sorted(
            {rule.start_date for rule in self.rules if rule.start_date is not None}
        )
        for transition_date in transition_dates:
            if transition_date[2] <= 1:
                raise AssertionError(
                    f"transition date needs calendar-aware predecessor: {transition_date}"
                )
            prior_date = (
                transition_date[0],
                transition_date[1],
                transition_date[2] - 1,
            )
            transition_text = ".".join(map(str, transition_date))
            transition_holders: dict[
                str, list[tuple[HolderEvent, Rule, Rule, Block, str | None]]
            ] = defaultdict(list)
            for relative, document in self.title_documents.items():
                for title_block in document.children(None):
                    if not re.fullmatch(r"[ekdc]_[A-Za-z0-9_]+", title_block.key):
                        continue
                    dated_holders: list[tuple[tuple[int, int, int], Block, Scalar]] = []
                    dated_governments: list[tuple[tuple[int, int, int], str]] = []
                    for date_block in document.children(title_block.ident):
                        event_date = parse_date(date_block.key)
                        if not event_date or event_date > transition_date:
                            continue
                        holder_scalars = document.direct_scalars(
                            date_block.ident, "holder"
                        )
                        if holder_scalars:
                            dated_holders.append(
                                (event_date, date_block, holder_scalars[-1])
                            )
                        government_scalars = document.direct_scalars(
                            date_block.ident, "government"
                        )
                        if government_scalars:
                            dated_governments.append(
                                (event_date, government_scalars[-1].value)
                            )
                    if not dated_holders:
                        continue
                    _, holder_block, holder_scalar = max(
                        dated_holders, key=lambda item: item[0]
                    )
                    active_government = (
                        max(dated_governments, key=lambda item: item[0])[1]
                        if dated_governments
                        else None
                    )
                    active_special = (
                        active_government
                        if active_government in PRESERVED_SPECIAL_GOVERNMENTS
                        else None
                    )
                    holder = holder_scalar.value
                    if holder in PLACEHOLDER_HOLDERS or any(
                        word in holder.lower()
                        for word in ("ruin", "wilderness", "unknown")
                    ):
                        continue
                    culture = self.corrected_culture.get(
                        holder,
                        self.characters.get(holder).culture
                        if holder in self.characters
                        else "",
                    )
                    empire = self.title_empire.get(title_block.key, "")
                    current = HolderEvent(
                        relative=relative,
                        filename=relative.name,
                        title=title_block.key,
                        empire=empire,
                        tier=TIER[title_block.key[0]],
                        date=transition_date,
                        date_text=transition_text,
                        holder=holder,
                        block=holder_block,
                        holder_scalar=holder_scalar,
                        government_scalar=None,
                        culture=culture,
                    )
                    previous = HolderEvent(
                        relative=relative,
                        filename=relative.name,
                        title=title_block.key,
                        empire=empire,
                        tier=current.tier,
                        date=prior_date,
                        date_text=".".join(map(str, prior_date)),
                        holder=holder,
                        block=holder_block,
                        holder_scalar=holder_scalar,
                        government_scalar=None,
                        culture=culture,
                    )
                    current_rule = matching_rule(current, self.rules)
                    previous_rule = matching_rule(previous, self.rules)
                    if (
                        current_rule is None
                        or previous_rule is None
                        or current_rule.government == previous_rule.government
                    ):
                        continue
                    transition_holders[holder].append(
                        (
                            current,
                            current_rule,
                            previous_rule,
                            title_block,
                            active_special,
                        )
                    )

            for holder, candidates in sorted(transition_holders.items()):
                target_values = {candidate[1].government for candidate in candidates}
                if len(target_values) != 1:
                    raise AssertionError(
                        f"ambiguous transition government for {holder}/{transition_text}: "
                        f"{target_values}"
                    )
                special_values = {
                    candidate[4] for candidate in candidates if candidate[4] is not None
                }
                if len(special_values) > 1:
                    raise AssertionError(
                        f"conflicting transition special governments for "
                        f"{holder}/{transition_text}: {special_values}"
                    )
                target_government = (
                    next(iter(special_values))
                    if special_values
                    else next(iter(target_values))
                )
                existing = self.government_at_date.get((holder, transition_date))
                if existing is not None:
                    if existing != target_government:
                        raise AssertionError(
                            f"transition mismatch for {holder}/{transition_text}: "
                            f"{existing} != {target_government}"
                        )
                    continue
                current, current_rule, previous_rule, title_block, _ = sorted(
                    candidates,
                    key=lambda candidate: (-candidate[0].tier, candidate[0].title),
                )[0]
                document = self.title_documents[current.relative]
                transition_blocks = [
                    block
                    for block in document.children(title_block.ident)
                    if parse_date(block.key) == transition_date
                ]
                if transition_blocks:
                    government_scalars = document.direct_scalars(
                        transition_blocks[0].ident, "government"
                    )
                    if government_scalars:
                        scalar = government_scalars[-1]
                        self.title_edits[current.relative].append(
                            (
                                scalar.start,
                                scalar.end,
                                f"government = {target_government}",
                            )
                        )
                    else:
                        self.title_edits[current.relative].append(
                            insert_child_block(
                                self.title_texts[current.relative],
                                transition_blocks[0],
                                f"government = {target_government}",
                            )
                        )
                else:
                    later_blocks = sorted(
                        (
                            block
                            for block in document.children(title_block.ident)
                            if (date := parse_date(block.key))
                            and date > transition_date
                        ),
                        key=lambda block: parse_date(block.key),
                    )
                    if later_blocks:
                        self.title_edits[current.relative].append(
                            insert_before_block(
                                self.title_texts[current.relative],
                                later_blocks[0],
                                f"{transition_text} = "
                                f"{{ government = {target_government} }}",
                            )
                        )
                    else:
                        self.title_edits[current.relative].append(
                            insert_child_block(
                                self.title_texts[current.relative],
                                title_block,
                                f"{transition_text} = "
                                f"{{ government = {target_government} }}",
                            )
                        )
                self.government_at_date[(holder, transition_date)] = target_government
                self.government_audit.append(
                    {
                        "date": transition_text,
                        "holder": holder,
                        "culture": current.culture,
                        "title": current.title,
                        "tier": current.tier,
                        "empire": current.empire,
                        "source_file": current.relative.as_posix(),
                        "old_government": previous_rule.government,
                        "new_government": target_government,
                        "rule_type": current_rule.scope_type,
                        "rule_scope": current_rule.scope,
                        "confidence": current_rule.confidence,
                    }
                )

    def render_title_edits(self) -> None:
        self.generated: dict[Path, bytes] = {}
        for relative, text in self.title_texts.items():
            edits = self.title_edits.get(relative, [])
            if edits:
                rendered = apply_edits(text, edits).rstrip() + "\n"
                self.generated[relative] = rendered.encode("utf-8-sig")

    def build_character_outputs(self) -> None:
        character_edits: dict[Path, list[tuple[int, int, str]]] = defaultdict(list)
        self.culture_audit: list[dict[str, object]] = []
        self.faith_audit: list[dict[str, object]] = []
        for key in sorted(self.jogos_characters):
            character = self.characters.get(key)
            if not character or character.culture != "nefer":
                continue
            document = self.character_documents[character.relative]
            culture_scalars = document.direct_scalars(character.block.ident, "culture")
            if len(culture_scalars) != 1:
                raise AssertionError(f"{key}: expected one direct culture")
            scalar = culture_scalars[0]
            character_edits[character.relative].append(
                (scalar.start, scalar.end, "culture = jogos_nhai")
            )
            self.culture_audit.append(
                {
                    "character": key,
                    "source_file": character.relative.as_posix(),
                    "old_culture": "nefer",
                    "new_culture": "jogos_nhai",
                    "reason": "Jogos title or in-scope family closure",
                }
            )

        for key in sorted(self.ibben_characters):
            character = self.characters.get(key)
            if not character or character.religion != "ib_ven_god_king":
                continue
            if character.death and character.death < DOOM:
                continue
            document = self.character_documents[character.relative]
            religion_scalars = document.direct_scalars(
                character.block.ident, "religion"
            )
            if len(religion_scalars) != 1:
                raise AssertionError(f"{key}: expected one direct religion")
            if character.birth and character.birth >= DOOM:
                scalar = religion_scalars[0]
                character_edits[character.relative].append(
                    (scalar.start, scalar.end, "religion = ib_ven_sound")
                )
                mode = "post_doom_initial"
            else:
                doom_blocks = [
                    block
                    for block in document.children(character.block.ident)
                    if block.key == DOOM_TEXT
                ]
                if doom_blocks:
                    character_edits[character.relative].append(
                        insert_child_block(
                            self.character_texts[character.relative],
                            doom_blocks[0],
                            "religion = ib_ven_sound",
                        )
                    )
                else:
                    later_blocks = sorted(
                        (
                            block
                            for block in document.children(character.block.ident)
                            if (date := parse_date(block.key)) and date > DOOM
                        ),
                        key=lambda block: parse_date(block.key),
                    )
                    if later_blocks:
                        character_edits[character.relative].append(
                            insert_before_block(
                                self.character_texts[character.relative],
                                later_blocks[0],
                                f"{DOOM_TEXT} = {{ religion = ib_ven_sound }}",
                            )
                        )
                    else:
                        character_edits[character.relative].append(
                            insert_child_block(
                                self.character_texts[character.relative],
                                character.block,
                                f"{DOOM_TEXT} = {{ religion = ib_ven_sound }}",
                            )
                        )
                mode = "dated_transition"
            self.faith_audit.append(
                {
                    "character": key,
                    "source_file": character.relative.as_posix(),
                    "old_faith": "ib_ven_god_king",
                    "new_faith": "ib_ven_sound",
                    "transition": DOOM_TEXT,
                    "mode": mode,
                }
            )

        for (holder, date), government in self.government_at_date.items():
            if government not in NO_LEGITIMACY or holder not in self.characters:
                continue
            character = self.characters[holder]
            document = self.character_documents[character.relative]
            for date_block in document.children(character.block.ident):
                if parse_date(date_block.key) != date:
                    continue
                legitimacy_scalars = document.direct_scalars(
                    date_block.ident, "add_legitimacy"
                )
                if (
                    legitimacy_scalars
                    and len(legitimacy_scalars)
                    == len(document.direct_scalars(date_block.ident))
                    and not document.children(date_block.ident)
                ):
                    start, end = block_removal_span(
                        self.character_texts[character.relative], date_block
                    )
                    character_edits[character.relative].append((start, end, ""))
                    continue
                for scalar in legitimacy_scalars:
                    start, end = removal_span(
                        self.character_texts[character.relative], scalar
                    )
                    character_edits[character.relative].append((start, end, ""))

        for relative in sorted(
            set(character_edits) | self.merged_character_relatives, key=str
        ):
            edits = character_edits[relative]
            self.generated[relative] = apply_edits(
                self.character_texts[relative], edits
            ).encode("utf-8-sig")
        bookmark_relative = Path("history/characters/bookmark_chars.txt")
        if bookmark_relative not in self.generated:
            self.generated[bookmark_relative] = self.character_texts[
                bookmark_relative
            ].encode("utf-8-sig")
        eep_bookmark_override = Path(
            "history/characters/zz_eetlv_bookmark_char_overrides.txt"
        )
        if eep_bookmark_override in self.character_winners:
            self.generated[eep_bookmark_override] = b"\xef\xbb\xbf\n"
        eep_khal_name_override = Path("history/characters/zz_eetlv_khal_name_fixes.txt")
        if eep_khal_name_override in self.character_winners:
            self.generated[eep_khal_name_override] = b"\xef\xbb\xbf\n"

    def build_province_outputs(self) -> None:
        province_relative = Path("history/provinces/k_generated.txt")
        province_text = read_text(self.province_winners[province_relative][1])
        province_document = parse_document(province_text)
        ibben_provinces = {
            province
            for province, empire in self.province_empire.items()
            if empire == "e_ibben"
        }
        province_edits: list[tuple[int, int, str]] = []
        self.province_audit: list[dict[str, object]] = []
        found_provinces: set[int] = set()
        for block in province_document.children(None):
            if not block.key.isdigit() or int(block.key) not in ibben_provinces:
                continue
            province = int(block.key)
            found_provinces.add(province)
            religions = province_document.direct_scalars(block.ident, "religion")
            if len(religions) != 1 or religions[0].value != "ib_ven_god_king":
                raise AssertionError(
                    f"Ibben province {province} expected static ib_ven_god_king"
                )
            doom_blocks = [
                child
                for child in province_document.children(block.ident)
                if child.key == DOOM_TEXT
            ]
            if doom_blocks:
                existing = province_document.direct_scalars(
                    doom_blocks[0].ident, "religion"
                )
                if existing:
                    province_edits.append(
                        (
                            existing[-1].start,
                            existing[-1].end,
                            "religion = ib_ven_sound",
                        )
                    )
                else:
                    province_edits.append(
                        insert_child_block(
                            province_text, doom_blocks[0], "religion = ib_ven_sound"
                        )
                    )
            else:
                later_blocks = sorted(
                    (
                        child
                        for child in province_document.children(block.ident)
                        if (date := parse_date(child.key)) and date > DOOM
                    ),
                    key=lambda child: parse_date(child.key),
                )
                if later_blocks:
                    province_edits.append(
                        insert_before_block(
                            province_text,
                            later_blocks[0],
                            f"{DOOM_TEXT} = {{ religion = ib_ven_sound }}",
                        )
                    )
                else:
                    province_edits.append(
                        insert_child_block(
                            province_text,
                            block,
                            f"{DOOM_TEXT} = {{ religion = ib_ven_sound }}",
                        )
                    )
            self.province_audit.append(
                {
                    "province": province,
                    "empire": "e_ibben",
                    "old_faith": "ib_ven_god_king",
                    "new_faith": "ib_ven_sound",
                    "transition": DOOM_TEXT,
                }
            )
        if found_provinces != ibben_provinces:
            raise AssertionError(
                "Ibben province history coverage changed: "
                f"missing={sorted(ibben_provinces - found_provinces)[:10]}"
            )
        self.generated[province_relative] = apply_edits(
            province_text, province_edits
        ).encode("utf-8-sig")

        effect_relative = Path(
            "common/scripted_effects/replace/00_agot_character_data_effects.txt"
        )
        self.generated[effect_relative] = transform_effect(
            read_text(self.effect_source)
        ).encode("utf-8-sig")

    def write_outputs(self) -> None:
        self.government_audit.sort(
            key=lambda row: (
                parse_date(str(row["date"])) or (0, 0, 0),
                str(row["holder"]),
                str(row["title"]),
            )
        )
        audit_outputs = {
            Path("artifacts/lore_governments/government_audit.csv"): csv_bytes(
                [
                    "date",
                    "holder",
                    "culture",
                    "title",
                    "tier",
                    "empire",
                    "source_file",
                    "old_government",
                    "new_government",
                    "rule_type",
                    "rule_scope",
                    "confidence",
                ],
                self.government_audit,
            ),
            Path("artifacts/lore_governments/culture_correction_audit.csv"): csv_bytes(
                ["character", "source_file", "old_culture", "new_culture", "reason"],
                self.culture_audit,
            ),
            Path("artifacts/lore_governments/ibben_faith_audit.csv"): csv_bytes(
                [
                    "character",
                    "source_file",
                    "old_faith",
                    "new_faith",
                    "transition",
                    "mode",
                ],
                self.faith_audit,
            ),
            Path("artifacts/lore_governments/ibben_province_audit.csv"): csv_bytes(
                ["province", "empire", "old_faith", "new_faith", "transition"],
                self.province_audit,
            ),
        }
        self.generated.update(audit_outputs)

        if not self.government_audit:
            raise AssertionError("government audit is empty")
        if not self.culture_audit:
            raise AssertionError("Jogos culture correction audit is empty")
        if not self.faith_audit or not self.province_audit:
            raise AssertionError("Ibben faith audit is incomplete")

        for relative, content in self.generated.items():
            path = self.module / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
        print(
            f"Generated {len(self.generated)} files: {len(self.government_audit)} governments, "
            f"{len(self.culture_audit)} culture corrections, "
            f"{len(self.faith_audit)} Ibben characters, "
            f"{len(self.province_audit)} Ibben provinces"
        )
        return None


def main(inputs: RunInputs) -> None:
    LoreGovernmentPipeline(inputs).run()


def generate(context: GenerationContext) -> None:
    main(
        RunInputs(
            root=context.workspace_root,
            workshop_root=context.workshop_root(
                "agot",
                "legacy-of-valyria",
                "legacy-of-valyria-bridge",
                "essos-expanded",
                "essos-expanded-bridge",
                "lore-bridge",
            ),
            output_root=context.output_root,
            assets_dir=context.assets_dir / "lore_governments",
            local_sources={
                "LOV_REBASE": context.source("legacy-of-valyria-rebase"),
                "EE_REBASE": context.source("essos-expanded-rebase"),
            },
        )
    )
