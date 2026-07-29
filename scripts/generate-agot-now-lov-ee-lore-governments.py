#!/usr/bin/env python3
"""Generate lore governments and the Ibben faith transition for LoV/EE."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import sys
from collections import defaultdict, deque
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

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
PLACEHOLDER_HOLDERS = {
    "0",
    "Ruin_Empress",
    "Unknown_Emperor",
    "Wilderness_Empress",
}
WORKSHOP_IDS = {
    "AGOT": "2962333032",
    "LOV": "3403938445",
    "RC": "3719888822",
    "EE": "3682802751",
    "EEP": "3768149491",
}


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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate AGOT + NOW + LoV + EE lore governments."
    )
    parser.add_argument(
        "--root", type=Path, default=Path(__file__).resolve().parents[1]
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--audit", action="store_true", help="Write audit CSVs only.")
    mode.add_argument(
        "--check", action="store_true", help="Verify checked-in generated files."
    )
    mode.add_argument(
        "--update-source-manifest",
        action="store_true",
        help="Accept current upstream hashes after reviewing their changes.",
    )
    return parser.parse_args()


def normalized_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig").replace("\r\n", "\n")


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
                key=key,
                value=value,
                start=token_start,
                end=look,
                parent=parent_block(),
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
    for previous, current in zip(ordered, ordered[1:]):
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


def csv_bytes(fieldnames: list[str], rows: Iterable[dict[str, object]]) -> bytes:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue().encode("utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


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
    document = parse_document(normalized_text(landed_titles_path))
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


def parse_character_sources(
    winners: dict[Path, tuple[str, Path]],
) -> tuple[dict[Path, str], dict[Path, Document], dict[str, Character]]:
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
        text = normalized_text(path)
        if relative.name == "bookmark_chars.txt":
            broken = "# Each ruler has: father, 2 siblings (share father), 2 childrengen_719 = {"
            fixed = (
                "# Each ruler has: father, 2 siblings (share father), 2 children\n"
                "gen_719 = {"
            )
            if text.count(broken) != 1:
                raise AssertionError("EE bookmark gen_719 malformed header changed")
            text = text.replace(broken, fixed)
        document = parse_document(text)
        texts[relative] = text
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
            if block.key in characters:
                raise AssertionError(f"duplicate effective character ID {block.key}")
            characters[block.key] = character
    return texts, documents, characters


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
        raise AssertionError("map compatch input already contains lore integration")
    text = text.replace(
        "# NOW 1.2.4 + LoV RC65 + Essos Expanded 1.0.3 semantic merge.",
        "# NOW + LoV + Essos Expanded lore-government integration.",
        1,
    )
    marker = "\n\t### ASSIGN TO LIST ###"
    if text.count(marker) != 1:
        raise AssertionError("assign_government_data_effect marker changed")
    removals = []
    for short in ("nomad", "celestial", "meritocratic", "mandala"):
        removals.append(
            "\tif = {\n"
            f"\t\tlimit = {{ NOT = {{ flag:$GOV$ = flag:{short} }} }}\n"
            f"\t\tremove_list_global_variable = {{ name = {short}_government_list target = $SCOPE$ }}\n"
            "\t}\n"
        )
    text = text.replace(
        marker,
        "\n\t### LORE GOVERNMENT INTEGRATION ###\n" + "".join(removals) + marker,
    )
    prune_needle = "\tremove_list_global_variable = { name = ruins_government_list target = $SCOPE$ }\n"
    if text.count(prune_needle) != 2:
        raise AssertionError("prune government list tail changed")
    prune_add = "".join(
        f"\tremove_list_global_variable = {{ name = {short}_government_list target = $SCOPE$ }}\n"
        for short in ("nomad", "celestial", "meritocratic", "mandala")
    )
    prune_position = text.rfind(prune_needle)
    text = (
        text[:prune_position]
        + prune_needle
        + prune_add
        + text[prune_position + len(prune_needle) :]
    )
    switch_needle = "\t\t\tclan_government = { assign_government_data_effect = { GOV = clan SCOPE = $SCOPE$ } }\n"
    if text.count(switch_needle) != 1:
        raise AssertionError("government switch clan branch changed")
    switch_add = "".join(
        f"\t\t\t{short}_government = {{ assign_government_data_effect = {{ GOV = {short} SCOPE = $SCOPE$ }} }}\n"
        for short in ("nomad", "celestial", "meritocratic", "mandala")
    )
    text = text.replace(switch_needle, switch_needle + switch_add)
    fallback_needle = (
        "\t\t\tif = {\n"
        "\t\t\t\tlimit = { $SCOPE$.primary_title.previous_holder ?= { agot_ruler_is_government_trigger = { GOV = landless_adventurer } } }\n"
    )
    if text.count(fallback_needle) != 1:
        raise AssertionError("fallback government insertion point changed")
    fallback_add = ""
    for short in ("nomad", "celestial", "meritocratic", "mandala"):
        fallback_add += (
            "\t\t\tif = {\n"
            f"\t\t\t\tlimit = {{ $SCOPE$.primary_title.previous_holder ?= {{ agot_ruler_is_government_trigger = {{ GOV = {short} }} }} }}\n"
            "\t\t\t\tset_variable = {\n"
            "\t\t\t\t\tname = temp_government_type\n"
            f"\t\t\t\t\tvalue = flag:{short}\n"
            "\t\t\t\t\tdays = 1\n"
            "\t\t\t\t}\n"
            "\t\t\t}\n"
        )
    text = text.replace(fallback_needle, fallback_add + fallback_needle)
    if text.count("culture = culture:jhalai") != 2:
        raise AssertionError("Jogos/Jhalai flavor branch changed")
    text = text.replace("culture = culture:jhalai", "culture = culture:jogos_nhai")
    dothraki_needle = (
        "\t\t\t\t\t\t\tculture = culture:dothraki\n"
        "\t\t\t\t\t\t\thas_government = tribal_government\n"
    )
    if text.count(dothraki_needle) != 2:
        raise AssertionError("Dothraki flavor government checks changed")
    dothraki_replacement = (
        "\t\t\t\t\t\t\tculture = culture:dothraki\n"
        "\t\t\t\t\t\t\tOR = {\n"
        "\t\t\t\t\t\t\t\thas_government = nomad_government\n"
        "\t\t\t\t\t\t\t\thas_government = tribal_government\n"
        "\t\t\t\t\t\t\t}\n"
    )
    text = text.replace(dothraki_needle, dothraki_replacement)
    ibben_needle = "\t\t\t\t\t\t\tculture = culture:ibbatese\n"
    if text.count(ibben_needle) != 1:
        raise AssertionError("Ibben flavor branch changed")
    text = text.replace(
        ibben_needle,
        ibben_needle + "\t\t\t\t\t\t\tfaith = faith:ib_ven_god_king\n",
    )
    return text


def target_manifest(
    root: Path,
    workshop: dict[str, Path],
    inputs: Iterable[Path],
) -> dict[str, object]:
    def display(path: Path) -> str:
        try:
            return path.relative_to(root).as_posix()
        except ValueError:
            return str(path)

    files = {
        display(path): {"sha256": sha256_file(path), "size": path.stat().st_size}
        for path in sorted(set(inputs))
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
        "schema_version": 1,
        "workshop_ids": WORKSHOP_IDS,
        "versions": versions,
        "doom_date": DOOM_TEXT,
        "files": files,
    }


def main() -> int:
    args = parse_args()
    root = args.root.resolve()
    workshop_root = root / ".ignored/CK3_workshop"
    workshop = {
        label: workshop_root / workshop_id
        for label, workshop_id in WORKSHOP_IDS.items()
    }
    missing = [
        f"{label}:{path}" for label, path in workshop.items() if not path.is_dir()
    ]
    if missing:
        raise FileNotFoundError(f"missing Workshop modules: {missing}")

    module = root / "mods/agot_now_lov_ee_lore_governments"
    source = module / "content_source/lore_governments"
    rules_path = source / "government_lore_rules.csv"
    manifest_path = source / "source_manifest.json"
    effect_source = (
        root
        / "mods/agot_now_lov_ee_map_compatch/common/scripted_effects/replace/00_agot_character_data_effects.txt"
    )
    roots = [
        ("LOV", workshop["LOV"]),
        ("RC", workshop["RC"]),
        ("LOV_REBASE", root / "mods/legacy_of_valyria_039_runtime_rebase"),
        ("EE", workshop["EE"]),
        ("EE_REBASE", root / "mods/essos_expanded_119_rebase"),
        ("EEP", workshop["EEP"]),
    ]
    title_winners = source_winners(
        roots,
        Path("history/titles"),
        lambda name: (
            name == "hist_titles.txt"
            or name.startswith("vassal_titles_e_")
            or name.startswith("lv_")
            or name == "agot_sothori_history_titles.txt"
        ),
    )
    character_winners = source_winners(
        roots, Path("history/characters"), lambda name: True
    )
    province_winners = source_winners(
        roots, Path("history/provinces"), lambda name: name == "k_generated.txt"
    )
    if Path("history/provinces/k_generated.txt") not in province_winners:
        raise FileNotFoundError("effective EE k_generated province history not found")

    landed_titles = workshop["EEP"] / "common/landed_titles/01_landed_titles.txt"
    input_paths = [
        rules_path,
        effect_source,
        landed_titles,
        workshop["AGOT"] / "common/governments/00_government_types.txt",
        workshop["AGOT"] / "common/religion/religion_types/00_agot_the_venerations.txt",
        *[path for _, path in title_winners.values()],
        *[path for _, path in character_winners.values()],
        *[path for _, path in province_winners.values()],
    ]
    current_manifest = target_manifest(root, workshop, input_paths)
    if args.update_source_manifest:
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(
            json.dumps(current_manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print(f"Updated {manifest_path.relative_to(root)}")
        return 0
    if not manifest_path.is_file():
        raise FileNotFoundError(
            f"{manifest_path} missing; review inputs and run --update-source-manifest"
        )
    if json.loads(manifest_path.read_text(encoding="utf-8")) != current_manifest:
        raise AssertionError(
            "upstream source manifest drifted; review and run --update-source-manifest"
        )

    rules = load_rules(rules_path)
    title_empire, province_empire = title_and_province_scope(landed_titles)
    character_texts, character_documents, characters = parse_character_sources(
        character_winners
    )

    title_texts: dict[Path, str] = {}
    title_documents: dict[Path, Document] = {}
    events: list[HolderEvent] = []
    holder_empires: dict[str, set[str]] = defaultdict(set)
    for relative, (_, path) in sorted(
        title_winners.items(), key=lambda item: str(item[0])
    ):
        text = normalized_text(path)
        document = parse_document(text)
        title_texts[relative] = text
        title_documents[relative] = document
        for title_block in document.children(None):
            if not re.fullmatch(r"[ekdc]_[A-Za-z0-9_]+", title_block.key):
                continue
            tier = TIER[title_block.key[0]]
            empire = title_empire.get(title_block.key, "")
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
                    word in holder.lower() for word in ("ruin", "wilderness", "unknown")
                ):
                    continue
                governments = document.direct_scalars(date_block.ident, "government")
                culture = characters.get(holder).culture if holder in characters else ""
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

    jogos_seeds = {event.holder for event in events if event.empire == "e_jogos_nhai"}
    ibben_seeds = {event.holder for event in events if event.empire == "e_ibben"}
    jogos_characters = family_closure(
        jogos_seeds, characters, holder_empires, "e_jogos_nhai"
    )
    ibben_characters = family_closure(
        ibben_seeds, characters, holder_empires, "e_ibben"
    )
    corrected_culture = {
        key: (
            "jogos_nhai"
            if key in jogos_characters and char.culture == "nefer"
            else char.culture
        )
        for key, char in characters.items()
    }
    for event in events:
        event.culture = corrected_culture.get(event.holder, event.culture)
        event.rule = matching_rule(event, rules)

    event_groups: dict[tuple[str, tuple[int, int, int]], list[HolderEvent]] = (
        defaultdict(list)
    )
    for event in events:
        event_groups[(event.holder, event.date)].append(event)

    title_edits: dict[Path, list[tuple[int, int, str]]] = defaultdict(list)
    government_at_date: dict[tuple[str, tuple[int, int, int]], str] = {}
    government_audit: list[dict[str, object]] = []
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
            target_rule = max(candidates, key=lambda event: rule_priority(event.rule))
        else:
            max_tier = max(event.tier for event in candidates)
            ranked = [event for event in candidates if event.tier == max_tier]
            max_priority = max(rule_priority(event.rule) for event in ranked)
            ranked = [
                event for event in ranked if rule_priority(event.rule) == max_priority
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
            event for event in group if event.tier == max(item.tier for item in group)
        ]
        insertion = sorted(insertion_candidates, key=lambda event: event.title)[0]
        old_values = {
            event.government_scalar.value for event in group if event.government_scalar
        }
        for event in group:
            scalar = event.government_scalar
            if event is insertion:
                if scalar:
                    title_edits[event.relative].append(
                        (scalar.start, scalar.end, f"government = {target_government}")
                    )
                else:
                    title_edits[event.relative].append(
                        insert_direct_scalar(
                            title_texts[event.relative],
                            event.block,
                            event.holder_scalar,
                            "government",
                            target_government,
                        )
                    )
            elif scalar:
                start, end = removal_span(title_texts[event.relative], scalar)
                title_edits[event.relative].append((start, end, ""))
        government_at_date[(holder, date)] = target_government
        government_audit.append(
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

    transition_dates = sorted(
        {rule.start_date for rule in rules if rule.start_date is not None}
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
        for relative, document in title_documents.items():
            for title_block in document.children(None):
                if not re.fullmatch(r"[ekdc]_[A-Za-z0-9_]+", title_block.key):
                    continue
                dated_holders: list[tuple[tuple[int, int, int], Block, Scalar]] = []
                dated_governments: list[tuple[tuple[int, int, int], str]] = []
                for date_block in document.children(title_block.ident):
                    event_date = parse_date(date_block.key)
                    if not event_date or event_date > transition_date:
                        continue
                    holder_scalars = document.direct_scalars(date_block.ident, "holder")
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
                    word in holder.lower() for word in ("ruin", "wilderness", "unknown")
                ):
                    continue
                culture = corrected_culture.get(
                    holder,
                    characters.get(holder).culture if holder in characters else "",
                )
                empire = title_empire.get(title_block.key, "")
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
                current_rule = matching_rule(current, rules)
                previous_rule = matching_rule(previous, rules)
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
            existing = government_at_date.get((holder, transition_date))
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
            document = title_documents[current.relative]
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
                    title_edits[current.relative].append(
                        (
                            scalar.start,
                            scalar.end,
                            f"government = {target_government}",
                        )
                    )
                else:
                    title_edits[current.relative].append(
                        insert_child_block(
                            title_texts[current.relative],
                            transition_blocks[0],
                            f"government = {target_government}",
                        )
                    )
            else:
                later_blocks = sorted(
                    (
                        block
                        for block in document.children(title_block.ident)
                        if (date := parse_date(block.key)) and date > transition_date
                    ),
                    key=lambda block: parse_date(block.key),
                )
                if later_blocks:
                    title_edits[current.relative].append(
                        insert_before_block(
                            title_texts[current.relative],
                            later_blocks[0],
                            f"{transition_text} = "
                            f"{{ government = {target_government} }}",
                        )
                    )
                else:
                    title_edits[current.relative].append(
                        insert_child_block(
                            title_texts[current.relative],
                            title_block,
                            f"{transition_text} = "
                            f"{{ government = {target_government} }}",
                        )
                    )
            government_at_date[(holder, transition_date)] = target_government
            government_audit.append(
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

    generated: dict[Path, bytes] = {}
    for relative, edits in title_edits.items():
        generated[relative] = apply_edits(title_texts[relative], edits).encode(
            "utf-8-sig"
        )

    character_edits: dict[Path, list[tuple[int, int, str]]] = defaultdict(list)
    culture_audit: list[dict[str, object]] = []
    faith_audit: list[dict[str, object]] = []
    for key in sorted(jogos_characters):
        character = characters.get(key)
        if not character or character.culture != "nefer":
            continue
        document = character_documents[character.relative]
        culture_scalars = document.direct_scalars(character.block.ident, "culture")
        if len(culture_scalars) != 1:
            raise AssertionError(f"{key}: expected one direct culture")
        scalar = culture_scalars[0]
        character_edits[character.relative].append(
            (scalar.start, scalar.end, "culture = jogos_nhai")
        )
        culture_audit.append(
            {
                "character": key,
                "source_file": character.relative.as_posix(),
                "old_culture": "nefer",
                "new_culture": "jogos_nhai",
                "reason": "Jogos title or in-scope family closure",
            }
        )

    for key in sorted(ibben_characters):
        character = characters.get(key)
        if not character or character.religion != "ib_ven_god_king":
            continue
        if character.death and character.death < DOOM:
            continue
        document = character_documents[character.relative]
        religion_scalars = document.direct_scalars(character.block.ident, "religion")
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
                        character_texts[character.relative],
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
                            character_texts[character.relative],
                            later_blocks[0],
                            f"{DOOM_TEXT} = {{ religion = ib_ven_sound }}",
                        )
                    )
                else:
                    character_edits[character.relative].append(
                        insert_child_block(
                            character_texts[character.relative],
                            character.block,
                            f"{DOOM_TEXT} = {{ religion = ib_ven_sound }}",
                        )
                    )
            mode = "dated_transition"
        faith_audit.append(
            {
                "character": key,
                "source_file": character.relative.as_posix(),
                "old_faith": "ib_ven_god_king",
                "new_faith": "ib_ven_sound",
                "transition": DOOM_TEXT,
                "mode": mode,
            }
        )

    for (holder, date), government in government_at_date.items():
        if government not in NO_LEGITIMACY or holder not in characters:
            continue
        character = characters[holder]
        document = character_documents[character.relative]
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
                    character_texts[character.relative], date_block
                )
                character_edits[character.relative].append((start, end, ""))
                continue
            for scalar in legitimacy_scalars:
                start, end = removal_span(character_texts[character.relative], scalar)
                character_edits[character.relative].append((start, end, ""))

    for relative, edits in character_edits.items():
        generated[relative] = apply_edits(character_texts[relative], edits).encode(
            "utf-8-sig"
        )
    bookmark_relative = Path("history/characters/bookmark_chars.txt")
    if bookmark_relative not in generated:
        generated[bookmark_relative] = character_texts[bookmark_relative].encode(
            "utf-8-sig"
        )

    province_relative = Path("history/provinces/k_generated.txt")
    province_text = normalized_text(province_winners[province_relative][1])
    province_document = parse_document(province_text)
    ibben_provinces = {
        province for province, empire in province_empire.items() if empire == "e_ibben"
    }
    province_edits: list[tuple[int, int, str]] = []
    province_audit: list[dict[str, object]] = []
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
        province_audit.append(
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
    generated[province_relative] = apply_edits(province_text, province_edits).encode(
        "utf-8-sig"
    )

    effect_relative = Path(
        "common/scripted_effects/replace/00_agot_character_data_effects.txt"
    )
    generated[effect_relative] = transform_effect(
        normalized_text(effect_source)
    ).encode("utf-8-sig")

    government_audit.sort(
        key=lambda row: (
            parse_date(str(row["date"])) or (0, 0, 0),
            str(row["holder"]),
            str(row["title"]),
        )
    )
    audit_outputs = {
        Path("content_source/lore_governments/government_audit.csv"): csv_bytes(
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
            government_audit,
        ),
        Path("content_source/lore_governments/culture_correction_audit.csv"): csv_bytes(
            [
                "character",
                "source_file",
                "old_culture",
                "new_culture",
                "reason",
            ],
            culture_audit,
        ),
        Path("content_source/lore_governments/ibben_faith_audit.csv"): csv_bytes(
            [
                "character",
                "source_file",
                "old_faith",
                "new_faith",
                "transition",
                "mode",
            ],
            faith_audit,
        ),
        Path("content_source/lore_governments/ibben_province_audit.csv"): csv_bytes(
            ["province", "empire", "old_faith", "new_faith", "transition"],
            province_audit,
        ),
    }
    generated.update(audit_outputs)

    if not government_audit:
        raise AssertionError("government audit is empty")
    if not culture_audit:
        raise AssertionError("Jogos culture correction audit is empty")
    if not faith_audit or not province_audit:
        raise AssertionError("Ibben faith audit is incomplete")

    selected = audit_outputs if args.audit else generated
    if args.check:
        stale: list[str] = []
        for relative, content in generated.items():
            path = module / relative
            if not path.is_file() or path.read_bytes() != content:
                stale.append(relative.as_posix())
        if stale:
            raise AssertionError(f"generated lore-government files are stale: {stale}")
        print(
            f"Checked {len(generated)} generated files: "
            f"{len(government_audit)} governments, "
            f"{len(culture_audit)} culture corrections, "
            f"{len(faith_audit)} Ibben characters, "
            f"{len(province_audit)} Ibben provinces"
        )
        return 0

    for relative, content in selected.items():
        path = module / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    action = "Audited" if args.audit else "Generated"
    print(
        f"{action} {len(selected)} files: {len(government_audit)} governments, "
        f"{len(culture_audit)} culture corrections, "
        f"{len(faith_audit)} Ibben characters, "
        f"{len(province_audit)} Ibben provinces"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AssertionError, FileNotFoundError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(1)
