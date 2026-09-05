"""A positional Clausewitz document model shared by the compatch stages.

`gen.text` and `gen.script` cover the common case: find one named definition and
splice it. The stages here instead rewrite thousands of scattered tokens across
history files, so they need every block and scalar located once, with byte spans
stable enough to batch the edits and apply them back to front.

`top_level_blocks` is the cheaper half of the same idea, for files that are read
as an ordered map of complete top-level blocks rather than edited in place.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass

from gen.text import matching_brace


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


TOP_LEVEL_KEY = re.compile(r"(?m)^(?P<key>[A-Za-z0-9_]+)\s*=\s*\{")


def top_level_blocks(
    text: str,
    pattern: re.Pattern[str] = TOP_LEVEL_KEY,
    *,
    label: str = "block",
    require_blocks: bool = True,
) -> tuple[str, str, list[str], dict[str, str]]:
    """Split a file into its complete top-level blocks, keyed and in order.

    Returns the text before the first block, the text after the last, the key
    order, and each key's complete block including its own header. The scan
    resumes past each block's closing brace, so a key written at column zero
    inside a block belongs to that block rather than opening a new one.

    Trailing comments between blocks are dropped rather than attached to either
    neighbour: they are ambiguous for generated data, and the callers here keep
    the file headers they care about in the prefix.

    An empty result is an error by default, because a caller naming one file has
    lost its target if that file declares nothing. Pass `require_blocks=False`
    when sweeping a directory, where a file may legitimately define no keys.
    """
    blocks: dict[str, str] = {}
    order: list[str] = []
    prefix: str | None = None
    cursor = 0
    while match := pattern.search(text, cursor):
        key = match.group("key")
        if prefix is None:
            prefix = text[: match.start()]
        if key in blocks:
            raise RuntimeError(f"duplicate {label} {key}")
        opening = text.index("{", match.start())
        end = matching_brace(text, opening) + 1
        blocks[key] = text[match.start() : end]
        order.append(key)
        cursor = end
    if prefix is None:
        if require_blocks:
            raise RuntimeError(f"expected at least one top-level {label}")
        return text, "", order, blocks
    return prefix, text[cursor:], order, blocks
