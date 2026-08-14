#!/usr/bin/env python3
"""Generate the CUIO-first GUI owner for the current AGOT playset.

The relevant Workshop GUI files use inconsistent line endings.  We normalise
them before asking ``git merge-file`` for a three-way merge, but pin the raw
files first so an upstream update cannot be mistaken for a harmless reformat.
"""

from __future__ import annotations

import codecs
import hashlib
import re
import subprocess
import tempfile
from pathlib import Path

from gen import GenerationContext
from gen.text import matching_brace


GUI_PARENTS = {
    "gui/interaction_declare_war.gui": "more-interactive-vassals",
    "gui/interaction_menu_window.gui": "better-barbershop",
    "gui/shared/coa_designer.gui": "agot",
    "gui/shared/cooltip.gui": "more-personality-depth",
    "gui/shared/lists.gui": "agot",
    "gui/window_accolade.gui": "agot",
    "gui/window_character.gui": "mpd-dragon-wives-compatch",
    "gui/window_factions.gui": "agot",
}

# Full-file pins deliberately include the vanilla merge base: GUI changes are
# only reviewed when all three sides of a three-way merge are known inputs.
PINS = {
    "game": {
        "gui/interaction_declare_war.gui": "00e47623902d8b4e536444d6c66ac249ecbda672e8f8537df4a8cfcfffc1df1a",
        "gui/interaction_menu_window.gui": "8fdc67edf82d59ac3c0bcbbd5eec00624cb582c4b47f0f35ed2063b96303909a",
        "gui/shared/coa_designer.gui": "2f3b863a7fea692d630825052426ccc674403d096c37dd470e63c923d2d356ec",
        "gui/shared/cooltip.gui": "702a1135d22b28c7a73b902a730d906481c5efb003c6929fe9dcf4350be74a34",
        "gui/shared/lists.gui": "21cb58ce683f514589f34b00f854b492c338b6c4bf3f49457478ca3f4ea28e5c",
        "gui/window_accolade.gui": "5a5d45b4e8994c5b87578c5b2171c6585298c17de3d80d3b505b13c3f5e04cdd",
        "gui/window_character.gui": "474b1979df99c972eb3339d8931a9eb97f2f852579e209e34a6007320e825a58",
        "gui/window_factions.gui": "798f177b1db914b34cce177d8cd29f336e182bc6bb24294bd46ece7b27392770",
    },
    "cuio": {
        "gui/interaction_declare_war.gui": "4b046c4f7a184eb68d97aefe63d15f4d0211a3a45fa1121f9cee2ca56640f938",
        "gui/interaction_menu_window.gui": "fa535010a80b9c4050c96be2a411a8e2b427efbb0f98f8a5f94f7de5beb16a3a",
        "gui/shared/coa_designer.gui": "fa1a7c55fa58b9caeef4ce23e52d5da51d90c5d171aafbbaa06f2f62cffb6bad",
        "gui/shared/cooltip.gui": "d032dc285b878764045538bd0161e36ba545b1935a05de46126003c24f10b9c4",
        "gui/shared/lists.gui": "8aedbaa05219e191f6749edaca91e2f4037d6f55025edd31b9d5e443ba305e06",
        "gui/window_accolade.gui": "0a238e513e9d0b53ec48118c713c32af416c491c7621e514a8900a91b6145711",
        "gui/window_character.gui": "1558fc89001d17964d6569f05c03c1598235330ff16478145f2fcd4093c145a5",
        "gui/window_factions.gui": "4efbb89e9c0c9df4c0897922695d6aeb0374be1f9a4db71ba54a0770ca6aa04e",
    },
    "agot": {
        "gui/interaction_declare_war.gui": "847d997bde45b497274954504b2c8feff4f5ebd343c836d70378604cbe626499",
        "gui/interaction_menu_window.gui": "f54a6dba8a6df9f4db6d97291a9291433e7feeea31157235b3e1bb449b932ad2",
        "gui/shared/coa_designer.gui": "e885c419c0b2942659f687c66df2dfa74f894e42393af168708327efbfefd38f",
        "gui/shared/cooltip.gui": "d157749b64d5d6d8e85f300ae9f8548fde1a4a49661ef06032322688adf5acd3",
        "gui/shared/lists.gui": "897cc471c6ec16dbb34327d68a212d076ea59589f716c677a785709ec2903cad",
        "gui/window_accolade.gui": "17cbd7e1f2370659f2230fe323005cfdde220d2c8ea5ef9f39868df71244172b",
        "gui/window_character.gui": "5fc9c380069105dcd88729dd1b20b1db9bf896d0d4f42277e2173dc69ff3ca11",
        "gui/window_factions.gui": "2457335d6725711e5dd96dbd4bc6b663e5b280c970f71d60afa90779bc3de10d",
    },
    "better-barbershop": {
        "gui/interaction_menu_window.gui": "074c6f12722f4a1830ca6e96432ec60ab555b6b57a9a4e9fff3b98e8599c7ce3",
    },
    "more-interactive-vassals": {
        "gui/interaction_declare_war.gui": "64aae257ca6f06bbc18e3eaf7d58adcb8e2f7c7fc1a381b3835648f8fe321ac7",
    },
    "more-personality-depth": {
        "gui/shared/cooltip.gui": "bf14daef43896cd45366e84ec6e4ada5ab74082023b772d1e3363e92734548c5",
    },
    "mpd-dragon-wives-compatch": {
        "gui/window_character.gui": "64d96d5b670fddc163dddf6905494c40a2d5e88e46af793182242a5a909a5993",
    },
    "artifact-manager": {
        "gfx/interface/icons/artifact/artifact_bg.dds": "5cf39c75f0551be3b93635a7477e3eda16a5b24ba255637ae775968839669b90",
        "gfx/interface/icons/artifact/artifact_unique.dds": "e89cd9340a8d467d4ebbf7f2b1bb073cf75c13a1c42a4f77cb66e4aac52131ad",
    },
}


def source_path(context: GenerationContext, source: str, relative: str) -> Path:
    return context.source(source) / relative


def pinned_text(context: GenerationContext, source: str, relative: str) -> str:
    path = source_path(context, source, relative)
    raw = path.read_bytes()
    expected = PINS[source][relative]
    actual = hashlib.sha256(raw).hexdigest()
    if actual != expected:
        raise RuntimeError(
            f"{source}/{relative} changed: expected {expected}, found {actual}"
        )
    return raw.decode("utf-8-sig").replace("\r\n", "\n").replace("\r", "\n")


def pinned_bytes(context: GenerationContext, source: str, relative: str) -> bytes:
    path = source_path(context, source, relative)
    raw = path.read_bytes()
    expected = PINS[source][relative]
    actual = hashlib.sha256(raw).hexdigest()
    if actual != expected:
        raise RuntimeError(
            f"{source}/{relative} changed: expected {expected}, found {actual}"
        )
    return raw


def merge_three_way(
    *, ours: str, base: str, parent: str, label: str, prefer_cuio: bool
) -> str:
    """Merge normalized text, taking CUIO only where both sides redesign it."""
    with tempfile.TemporaryDirectory(prefix="agot-cuio-") as directory:
        root = Path(directory)
        ours_path = root / "cuio.gui"
        base_path = root / "base.gui"
        parent_path = root / "parent.gui"
        ours_path.write_text(ours, encoding="utf-8", newline="\n")
        base_path.write_text(base, encoding="utf-8", newline="\n")
        parent_path.write_text(parent, encoding="utf-8", newline="\n")
        command = ["git", "merge-file", "-p"]
        if prefer_cuio:
            command.append("--ours")
        command.extend((str(ours_path), str(base_path), str(parent_path)))
        completed = subprocess.run(command, capture_output=True, check=False)
    if completed.returncode not in (0, 1):
        raise RuntimeError(
            f"{label}: git merge-file failed: {completed.stderr.decode().strip()}"
        )
    merged = completed.stdout.decode("utf-8")
    if "<<<<<<<" in merged or ">>>>>>>" in merged:
        raise RuntimeError(f"{label}: unresolved three-way merge")
    return merged


def require_count(text: str, needle: str, expected: int, *, label: str) -> None:
    actual = text.count(needle)
    if actual != expected:
        raise RuntimeError(f"{label}: expected {expected} {needle!r}, found {actual}")


def replace_once(text: str, old: str, new: str, *, label: str) -> str:
    require_count(text, old, 1, label=label)
    return text.replace(old, new, 1)


def nth_index(text: str, marker: str, occurrence: int) -> int:
    index = text.index(marker)
    for _ in range(occurrence):
        index = text.index(marker, index + 1)
    return index


def block_containing(
    text: str,
    marker: str,
    *,
    parent_depth: int,
    label: str,
    occurrence: int = 0,
    expected: int = 1,
) -> tuple[int, int]:
    """Return the enclosing GUI block at a stable nesting depth for marker."""
    require_count(text, marker, expected, label=label)
    marker_index = nth_index(text, marker, occurrence)
    starts = list(
        re.finditer(r"(?m)^[ \t]*[A-Za-z_][A-Za-z0-9_]*\s*=\s*\{", text[:marker_index])
    )
    candidates: list[tuple[int, int]] = []
    for match in reversed(starts):
        opening = text.index("{", match.start(), match.end())
        end = matching_brace(text, opening)
        if end > marker_index:
            candidates.append((match.start(), end))
    if len(candidates) <= parent_depth:
        raise RuntimeError(f"{label}: no enclosing GUI block at depth {parent_depth}")
    return candidates[parent_depth]


def append_to_block(
    text: str, marker: str, snippet: str, *, parent_depth: int, label: str
) -> str:
    _, end = block_containing(text, marker, parent_depth=parent_depth, label=label)
    line_start = text.rfind("\n", 0, end) + 1
    indent = re.match(r"[ \t]*", text[line_start:end]).group(0)
    body = indent_snippet(snippet, f"{indent}\t")
    return f"{text[:line_start]}{body}\n{text[line_start:]}"


def indent_snippet(snippet: str, indent: str) -> str:
    return "\n".join(
        f"{indent}{line}" if line else line for line in snippet.strip().splitlines()
    )


def prepend_to_block(
    text: str,
    marker: str,
    snippet: str,
    *,
    parent_depth: int,
    label: str,
    occurrence: int = 0,
    expected: int = 1,
) -> str:
    """Insert lines directly after a block's opening brace."""
    start, _ = block_containing(
        text,
        marker,
        parent_depth=parent_depth,
        label=label,
        occurrence=occurrence,
        expected=expected,
    )
    indent = re.match(r"[ \t]*", text[start:]).group(0)
    opening = text.index("\n", text.index("{", start))
    body = indent_snippet(snippet, f"{indent}\t")
    return f"{text[: opening + 1]}{body}\n{text[opening + 1 :]}"


def insert_before_block(
    text: str,
    marker: str,
    snippet: str,
    *,
    parent_depth: int,
    label: str,
    occurrence: int = 0,
    expected: int = 1,
) -> str:
    """Insert lines as the preceding sibling of a block."""
    start, _ = block_containing(
        text,
        marker,
        parent_depth=parent_depth,
        label=label,
        occurrence=occurrence,
        expected=expected,
    )
    indent = re.match(r"[ \t]*", text[start:]).group(0)
    return f"{text[:start]}{indent_snippet(snippet, indent)}\n{text[start:]}"


def append_to_blockoverride(
    text: str,
    name: str,
    snippet: str,
    *,
    label: str,
    occurrence: int = 0,
    expected: int = 1,
) -> str:
    """Insert lines as the last child of a named blockoverride."""
    marker = f'blockoverride "{name}"'
    require_count(text, marker, expected, label=label)
    opening = text.index("{", nth_index(text, marker, occurrence))
    end = matching_brace(text, opening)
    line_start = text.rfind("\n", 0, end) + 1
    indent = re.match(r"[ \t]*", text[line_start:end]).group(0)
    body = indent_snippet(snippet, f"{indent}\t")
    return f"{text[:line_start]}{body}\n{text[line_start:]}"


def insert_before_trailing_expand(
    text: str, marker: str, snippet: str, *, parent_depth: int, label: str
) -> str:
    """Insert rows ahead of a layout box's trailing expand spacer."""
    start, end = block_containing(text, marker, parent_depth=parent_depth, label=label)
    block = text[start : end + 1]
    match = None
    for candidate in re.finditer(r"(?m)^[ \t]*expand = \{ ?\}[ \t]*$", block):
        match = candidate
    if match is None:
        raise RuntimeError(f"{label}: no trailing expand spacer")
    indent = re.match(r"[ \t]*", match.group(0)).group(0)
    body = "\n".join(
        f"{indent}{line}" if line else line for line in snippet.strip().splitlines()
    )
    block = f"{block[: match.start()]}{body}\n{block[match.start() :]}"
    return f"{text[:start]}{block}{text[end + 1 :]}"


def replace_within_block(
    text: str,
    marker: str,
    old: str,
    new: str,
    *,
    parent_depth: int,
    label: str,
    occurrence: int = 0,
    expected: int = 1,
) -> str:
    start, end = block_containing(
        text,
        marker,
        parent_depth=parent_depth,
        label=label,
        occurrence=occurrence,
        expected=expected,
    )
    block = replace_once(text[start : end + 1], old, new, label=label)
    return f"{text[:start]}{block}{text[end + 1 :]}"


def append_to_descendant(
    text: str,
    outer_marker: str,
    inner_marker: str,
    snippet: str,
    *,
    inner_parent_depth: int,
    label: str,
) -> str:
    start, end = block_containing(text, outer_marker, parent_depth=0, label=label)
    block = append_to_block(
        text[start : end + 1],
        inner_marker,
        snippet,
        parent_depth=inner_parent_depth,
        label=label,
    )
    return f"{text[:start]}{block}{text[end + 1 :]}"


def replace_between(
    text: str, start_marker: str, end_marker: str, replacement: str, *, label: str
) -> str:
    require_count(text, start_marker, 1, label=label)
    require_count(text, end_marker, 1, label=label)
    start = text.index(start_marker)
    end = text.index(end_marker, start)
    if end <= start:
        raise RuntimeError(f"{label}: end marker occurs before start marker")
    return f"{text[:start]}{replacement}{text[end:]}"


def dedent_block(block: str) -> str:
    """Strip a lifted block's original nesting so it can be re-indented."""
    prefix = re.match(r"[ \t]*", block).group(0)
    if not prefix:
        return block
    return "\n".join(
        line[len(prefix) :] if line.startswith(prefix) else line
        for line in block.splitlines()
    )


def extract_named_widget(text: str, name: str, *, label: str) -> str:
    marker = f'name = "{name}"'
    start, end = block_containing(text, marker, parent_depth=0, label=label)
    return dedent_block(text[start : end + 1])


def remove_named_widget(text: str, name: str, *, label: str) -> str:
    """Drop a whole widget block, with any comment lines introducing it."""
    start, end = block_containing(text, f'name = "{name}"', parent_depth=0, label=label)
    head = text.rfind("\n", 0, start) + 1
    while head:
        previous = text.rfind("\n", 0, head - 1) + 1
        line = text[previous : head - 1].strip()
        if line and not line.startswith("#"):
            break
        head = previous
    tail = text.find("\n", end)
    return text[:head] + text[tail + 1 :] if tail != -1 else text[:head]


def name_block(
    text: str, marker: str, name: str, *, parent_depth: int, label: str
) -> str:
    """Give an unnamed block a name so it stays identifiable across re-merges."""
    start, _ = block_containing(text, marker, parent_depth=parent_depth, label=label)
    indent = re.match(r"[ \t]*", text[start:]).group(0)
    opening = text.index("\n", text.index("{", start))
    return f'{text[: opening + 1]}{indent}\tname = "{name}"\n{text[opening + 1 :]}'


def extract_widget_type(text: str, widget_type: str, *, label: str) -> str:
    pattern = re.compile(rf"(?m)^[ \t]*{re.escape(widget_type)}\s*=\s*\{{")
    matches = list(pattern.finditer(text))
    if len(matches) != 1:
        raise RuntimeError(
            f"{label}: expected one {widget_type} widget, found {len(matches)}"
        )
    match = matches[0]
    opening = text.index("{", match.start(), match.end())
    return text[match.start() : matching_brace(text, opening) + 1]


def extract_type(text: str, name: str, *, label: str) -> str:
    pattern = re.compile(rf"(?m)^[ \t]*type\s+{re.escape(name)}\s*=\s*[^\n]*\{{")
    matches = list(pattern.finditer(text))
    if len(matches) != 1:
        raise RuntimeError(f"{label}: expected one type {name}, found {len(matches)}")
    match = matches[0]
    opening = text.index("{", match.start(), match.end())
    return text[match.start() : matching_brace(text, opening) + 1]


def extract_template(text: str, name: str, *, label: str) -> str:
    pattern = re.compile(rf"(?m)^[ \t]*template\s+{re.escape(name)}\s*\{{")
    matches = list(pattern.finditer(text))
    if len(matches) != 1:
        raise RuntimeError(
            f"{label}: expected one template {name}, found {len(matches)}"
        )
    match = matches[0]
    opening = text.index("{", match.start(), match.end())
    return text[match.start() : matching_brace(text, opening) + 1]


def merge_gui(
    context: GenerationContext, relative: str, *, prefer_cuio: bool
) -> tuple[str, str]:
    parent_source = GUI_PARENTS[relative]
    cuio = pinned_text(context, "cuio", relative)
    base = pinned_text(context, "game", relative)
    parent = pinned_text(context, parent_source, relative)
    return (
        merge_three_way(
            ours=cuio,
            base=base,
            parent=parent,
            label=relative,
            prefer_cuio=prefer_cuio,
        ),
        parent,
    )


def generate_interaction_menu(context: GenerationContext) -> str:
    text, _ = merge_gui(context, "gui/interaction_menu_window.gui", prefer_cuio=True)
    agot = pinned_text(context, "agot", "gui/interaction_menu_window.gui")
    text = replace_once(
        text,
        'text = "[Character.GetUINameNoTooltip|U]"',
        'text = "[AGOTGetNameNoTooltip(Character)|U]"',
        label="interaction menu AGOT name",
    )
    controls = "\n".join(
        extract_widget_type(agot, name, label="AGOT interaction controls")
        for name in (
            "agot_interaction_knight_tree_button",
            "agot_interaction_dragon_tree_button",
            "agot_interaction_dragon_edit_button",
        )
    )
    text = append_to_block(
        text,
        'name = "button_pin"',
        controls,
        parent_depth=1,
        label="interaction menu controls target",
    )
    return replace_once(
        text,
        "visible = \"[And(Character.CanCustomizePortrait, Not(GetGlobalVariable('FSB_is_loaded').IsSet))]\"",
        "visible = \"[Not(GetGlobalVariable('FSB_is_loaded').IsSet)]\"",
        label="Better Barbershop always-visible control",
    )


def generate_declare_war(context: GenerationContext) -> str:
    text, miv = merge_gui(context, "gui/interaction_declare_war.gui", prefer_cuio=True)
    agot = pinned_text(context, "agot", "gui/interaction_declare_war.gui")
    # MIV's source replaces AGOT's file, so restore AGOT's rescue/revenge
    # components explicitly and retain MIV's two warning strings in CUIO's view.
    for control in (
        "agot_rv_comparison_text",
        "agot_rv_rescue_war_items_vbox",
        "agot_rv_revenge_war_items_vbox",
        "agot_rv_rescue_item_box",
        "agot_rv_declare_war_send_button",
    ):
        require_count(agot, control, 1, label="AGOT rescue/revenge source")
    text = append_to_block(
        text,
        'name = "comparison_text"',
        "agot_rv_comparison_text = {}",
        parent_depth=1,
        label="rescue/revenge comparison target",
    )
    text = append_to_block(
        text,
        'name = "casus_belli_items"',
        "agot_rv_rescue_war_items_vbox = {}\nagot_rv_revenge_war_items_vbox = {}",
        parent_depth=0,
        label="rescue/revenge casus belli target",
    )
    text = append_to_block(
        text,
        "### War preview after selecting a Casus Belli",
        "agot_rv_rescue_item_box = {}",
        parent_depth=0,
        label="rescue war preview target",
    )
    text = append_to_block(
        text,
        'name = "send_button"',
        "agot_rv_declare_war_send_button = {}",
        parent_depth=2,
        label="rescue/revenge send target",
    )
    miv_messages = []
    for message in ("interactive_war_ui_second_message", "interactive_war_ui_message"):
        require_count(miv, message, 1, label="MIV declaration warning source")
        miv_messages.append(f'text_single = {{ text = "{message}" }}')
    return append_to_block(
        text,
        "### War preview after selecting a Casus Belli",
        "\n".join(miv_messages),
        parent_depth=0,
        label="MIV declaration warning target",
    )


def generate_lists(context: GenerationContext) -> str:
    text, agot = merge_gui(context, "gui/shared/lists.gui", prefer_cuio=True)
    text = replace_within_block(
        text,
        "maximumsize = { 338 -1 }",
        'text = "[Character.GetUINameNoTooltip|U]"',
        'text = "[AGOTGetLongUINameNoTooltip(Character)|UV]"',
        parent_depth=0,
        label="AGOT compact character list name",
    )
    text = replace_within_block(
        text,
        "maximumsize = { 338 -1 }",
        'text = "[Character.GetRelationToString( GetPlayer )]"',
        'using = visible_if_not_dragon\ntext = "[Character.GetRelationToString( GetPlayer )]"',
        parent_depth=0,
        label="AGOT dragon relation visibility",
    )
    dragon_relations = (
        "agot_dragonrider_list_relation = {}\n"
        "agot_bonded_list_relation = {}\n"
        "agot_host_list_relation = {}\n"
        "agot_owned_list_relation = {}\n"
        "agot_freedom_list_relation = {}\n"
        "agot_wild_list_relation = {}"
    )
    for name in re.findall(r"agot_[a-z_]+_list_relation", dragon_relations):
        require_count(agot, name, 1, label="AGOT dragon relation source")
    return append_to_descendant(
        text,
        "maximumsize = { 338 -1 }",
        'name = "character_relation"',
        dragon_relations,
        inner_parent_depth=1,
        label="AGOT dragon relations target",
    )


DW_VALYRIAN = (
    "GetScriptedGui('dw_valyrian_special')"
    ".IsShown(GuiScope.SetRoot(Character.MakeScope).End)"
)
DW_FOUR_WIVES = (
    "GetScriptedGui('dw_four_wives_shown')"
    ".IsShown(GuiScope.SetRoot(Character.MakeScope).End)"
)


def gate_out_dragon_wives(text: str, widget: str, *, label: str) -> str:
    """Hide a CUIO polygamy row for the characters Dragon Wives handles."""
    marker = f'name = "{widget}"'
    start, end = block_containing(text, marker, parent_depth=0, label=label)
    block = text[start : end + 1]
    match = re.search(r'(?m)^[ \t]*visible = "\[(?P<condition>.*)\]"$', block)
    if match is None:
        raise RuntimeError(f"{label}: no visible condition on {widget}")
    indent = re.match(r"[ \t]*", match.group(0)).group(0)
    gated = f'{indent}visible = "[And(Not({DW_VALYRIAN}), {match.group("condition")})]"'
    block = f"{block[: match.start()]}{gated}{block[match.end() :]}"
    return f"{text[:start]}{block}{text[end + 1 :]}"


AGOT_DRAGON_MILITARY = (
    "GetScriptedGui('agot_can_see_dragon_military_view')"
    ".IsShown(GuiScope.SetRoot(CharacterWindow.GetCharacter.MakeScope).End)"
)


def agot_gender_shown(gender: str) -> str:
    return (
        f"visible = \"[GetScriptedGui('agot_{gender}_gender_shown')"
        '.IsShown(GuiScope.SetRoot(CharacterWindow.GetCharacter.MakeScope).End)]"'
    )


def restore_agot_character_widgets(text: str) -> str:
    """Re-attach AGOT's character-window widgets to CUIO's rebuilt layout.

    CUIO 2.2 redesigns nearly every region AGOT extends, so the CUIO-first
    three-way merge resolves those hunks in CUIO's favour and drops all of
    AGOT's `agot_*` widgets.  The widget types themselves live in AGOT's
    `gui/custom_gui/`, which this module does not own, so each one is restored
    by re-declaring it against the matching anchor in CUIO's layout.
    """
    # AGOT's character and dragon layouts are authored for a 650px sidebar;
    # CUIO otherwise inherits vanilla's 610px Window_Size_Sidebar.  Keep the
    # wider shell so the dragon sheet and relation rows remain inside its frame.
    text = prepend_to_block(
        text,
        'name = "character_window"',
        "size = { 650 100% }",
        parent_depth=0,
        label="AGOT character window width",
    )
    # AGOT gates the human character sheet and supplies its own top-level views
    # for dragons, hidden characters, and faked deaths.  Without the gate a
    # dragon renders through CUIO's human layout.
    text = prepend_to_block(
        text,
        'name = "main_characters"',
        'visible = "[IsCharacterNormal]"',
        parent_depth=3,
        label="AGOT character-kind gate",
    )
    text = prepend_to_block(
        text,
        "size = { 100% 45 }",
        'visible = "[IsCharacterNormal]"',
        parent_depth=0,
        label="CUIO normal-character control strip",
    )
    text = insert_before_block(
        text,
        'name = "court_character_filter_window"',
        "agot_hidden_character_view = {}\n"
        "agot_dragons_character_view = {}\n"
        "agot_fake_death_character_view = {}",
        parent_depth=0,
        label="AGOT character-kind views",
    )
    # Relations tab.  Each AGOT row carries its own scripted-gui condition, so
    # they are siblings of CUIO's rows rather than replacements for them.
    text = insert_before_block(
        text,
        'name = "diarch"',
        "agot_squire_relationship_row = {}\nagot_knight_relationship_row = {}",
        parent_depth=0,
        label="AGOT squire and knight rows",
    )
    text = insert_before_block(
        text,
        'name = "friends"',
        "agot_bodyguard_relationship_row = {}\n"
        "agot_bodyguard_target_relationship_row = {}\n"
        "agot_dragons_relationship_row = {}\n"
        "agot_friends_plus_one = {}\n"
        "agot_friends_plus_two = {}\n"
        "agot_friends_plus_four = {}\n"
        "agot_friends_plus_five = {}",
        parent_depth=0,
        occurrence=0,
        expected=3,
        label="AGOT bodyguard, dragon, and resized friend rows",
    )
    text = replace_within_block(
        text,
        'name = "friends"',
        "visible = \"[Not( GreaterThan_int32( GetDataModelSize( CharacterWindow.GetRelationsOfType( GetRelation( 'disciple' ) ) ), '(int32)0' ) )]\"",
        'visible = "[And(Not(CharacterShowingDisciples), Not(Or(CharacterHasBodyguard, CharacterHasDragon)))]"',
        parent_depth=0,
        occurrence=0,
        expected=3,
        label="AGOT friends row allocation",
    )
    text = replace_within_block(
        text,
        'name = "friends_with_disciples"',
        "visible = \"[GreaterThan_int32( GetDataModelSize( CharacterWindow.GetRelationsOfType( GetRelation( 'disciple' ) ) ), '(int32)0' )]\"",
        'visible = "[And(CharacterShowingDisciples, Not(Or(CharacterHasBodyguard, CharacterHasDragon)))]"',
        parent_depth=0,
        label="AGOT friends-with-disciples row allocation",
    )
    text = replace_once(
        text,
        "text = \"[CharacterWindow.GetTabItemsCount('relations')]\"",
        'text = "[CharacterWindow.GetCharacter.MakeScope'
        ".ScriptValue('agot_relations_value')|0]\"",
        label="AGOT relations tab count",
    )
    # Portrait, window controls, and identity rows.
    text = append_to_block(
        text,
        'visible = "[Or( HasGameStartedForTheFirstTime, '
        'Not( And( GameIsMultiplayer, IsPreparationLobby ) ) )]"',
        "agot_ai_stress_icon = {}",
        parent_depth=0,
        label="AGOT AI stress icon",
    )
    text = append_to_blockoverride(
        text,
        "extra_buttons",
        "agot_knight_tree_button = {}",
        expected=2,
        label="AGOT knight tree button",
    )
    text = insert_before_block(
        text,
        'name = "suzerain"',
        "agot_pre_war_liege_portrait_vbox = {}",
        parent_depth=0,
        occurrence=1,
        expected=2,
        label="AGOT pre-war liege portrait",
    )
    text = append_to_block(
        text,
        'onclick = "[AddWatchWindow( CharacterWindow.GetCharacter.MakeScope )]"',
        "agot_portrait_editor_button = {}",
        parent_depth=1,
        label="AGOT portrait editor button",
    )
    # CUIO already owns the complete name, age, and health row.  Adding AGOT's
    # equivalent hbox duplicates every control, so carry only AGOT's localized
    # name text and tooltip into CUIO's single row.
    text = replace_within_block(
        text,
        'name = "name_health_and_relationship"',
        'text = "CHARACTER_VIEW_NAME"',
        'text = "AGOT_NAME_CHARACTER_COMMA"',
        parent_depth=0,
        label="AGOT character name text",
    )
    text = replace_once(
        text,
        'tooltip = "CHARACTER_VIEW_NAME_TT"',
        'tooltip = "AGOT_NAME_CHARACTER_TOOLTIP"',
        label="AGOT character name tooltip",
    )
    text = append_to_block(
        text,
        'text = "[lowborn|E]"',
        "agot_personal_coat_of_arms = {}",
        parent_depth=2,
        label="AGOT personal coat of arms",
    )
    for gender in ("male", "female"):
        vanilla = (
            "Not(Character.IsFemale)" if gender == "male" else "Character.IsFemale"
        )
        text = replace_once(
            text,
            f'visible = "[{vanilla}]"',
            agot_gender_shown(gender),
            label=f"AGOT {gender} sexuality icon",
        )
    # Title list: AGOT reuses the nomad frame for pirate domiciles.
    text = append_to_block(
        text,
        'visible = "[TitleItem.GetTitle.IsNomad]"',
        "agot_pirate_title_icon = {}",
        parent_depth=1,
        label="AGOT pirate title icon",
    )
    text = replace_once(
        text,
        'visible = "[TitleItem.GetTitle.IsNomad]"',
        'visible = "[And(TitleItem.GetTitle.IsNomad, '
        "Not(TitleItem.GetTitle.MakeScope.Var('is_pirate_domicile').IsSet))]\"",
        label="AGOT nomad title frame",
    )
    # Military strength: AGOT swaps the levy breakdown for a dragon roster.
    text = append_to_block(
        text,
        'name = "icon_combat_strength"',
        "agot_dragon_army_composition = {}",
        parent_depth=2,
        label="AGOT dragon army composition",
    )
    return prepend_to_block(
        text,
        'name = "icon_combat_strength"',
        f'visible = "[Not({AGOT_DRAGON_MILITARY})]"',
        parent_depth=1,
        label="AGOT levy breakdown gate",
    )


def generate_character(context: GenerationContext) -> str:
    text, parent = merge_gui(context, "gui/window_character.gui", prefer_cuio=True)
    # `git merge-file` is line-based.  CUIO 2.2 rebuilt the family tab, so the
    # parent's `family_spouses_expanded` scrollbox merges without a conflict
    # into `vbox_filter_group` instead of the family vbox, and a scrollbox
    # there evaluates `CharacterWindow` relation state that its datacontext
    # cannot provide.  CUIO already ships the same row in the right place, so
    # drop the misplaced copy and move AGOT's header onto CUIO's row.
    text = remove_named_widget(
        text, "family_spouses_expanded", label="misplaced AGOT spouses scrollbox"
    )
    expanded_spouses = "visible = \"[CharacterWindow.IsRelationExpanded( 'spouses' )]\""
    text = replace_within_block(
        text,
        expanded_spouses,
        'text = "SECONDARY_SPOUSES"',
        'text = "AGOT_SECONDARY_SPOUSES"',
        parent_depth=0,
        label="AGOT secondary spouse header",
    )
    text = name_block(
        text,
        expanded_spouses,
        "family_spouses_expanded",
        parent_depth=0,
        label="CUIO expanded spouses scrollbox",
    )
    text = replace_once(
        text,
        'visible = "[Not( Character.IsPlayer )]"',
        "visible = yes",
        label="MPD AI personality visibility",
    )
    text = replace_once(
        text,
        "visible = \"[Not(Or(GreaterThan_int32( Character.GetMaxSpouses, '(int32)1' ), GreaterThan_int32( Character.GetMaxConsorts, '(int32)0' )))]\"",
        "visible = \"[And(Not(GetScriptedGui('dw_valyrian_special').IsShown(GuiScope.SetRoot(Character.MakeScope).End)), Not(Or(GreaterThan_int32( Character.GetMaxSpouses, '(int32)1' ), GreaterThan_int32( Character.GetMaxConsorts, '(int32)0' ))))]\"",
        label="Dragon Wives grandparents visibility",
    )
    text = replace_once(
        text,
        "visible = \"[Or(GreaterThan_int32( Character.GetMaxSpouses, '(int32)1' ), GreaterThan_int32( Character.GetMaxConsorts, '(int32)0' ))]\"",
        "visible = \"[And(Not(GetScriptedGui('dw_valyrian_special').IsShown(GuiScope.SetRoot(Character.MakeScope).End)), Or(GreaterThan_int32( Character.GetMaxSpouses, '(int32)1' ), GreaterThan_int32( Character.GetMaxConsorts, '(int32)0' )))]\"",
        label="Dragon Wives contracted grandparents visibility",
    )
    # CUIO 2.2 rebuilt the family tab and now ships its own secondary-spouse
    # rows.  Those keep the vanilla polygamy path; Dragon Wives keeps the
    # Valyrian path, so each character sees exactly one of the two designs.
    for widget in ("secondary_spouses_inline", "secondary_spouses"):
        text = gate_out_dragon_wives(
            text, widget, label=f"CUIO {widget} Dragon Wives handover"
        )
    dragon_wives_spouses = extract_named_widget(
        parent, "secondary_spouses", label="Dragon Wives family rows"
    )
    dragon_wives_spouses = replace_once(
        dragon_wives_spouses,
        'name = "secondary_spouses"',
        'name = "secondary_spouses_special"',
        label="Dragon Wives secondary spouse row name",
    )
    # Its vanilla-polygamy branch is now CUIO's, so keep only the four-wives one.
    dragon_wives_spouses = re.sub(
        r'(?m)^([ \t]*)visible = "\[Or\(And\(GetScriptedGui\(\'dw_valyrian_special.*$',
        lambda match: (
            f'{match.group(1)}visible = "[And({DW_VALYRIAN}, {DW_FOUR_WIVES})]"'
        ),
        dragon_wives_spouses,
        count=1,
    )
    require_count(
        dragon_wives_spouses,
        f'visible = "[And({DW_VALYRIAN}, {DW_FOUR_WIVES})]"',
        1,
        label="Dragon Wives four-wives spouse row",
    )
    special_rows = "\n".join(
        (
            "agot_paramour_relationship_row = {}",
            extract_named_widget(
                parent, "grandparents_special", label="Dragon Wives family rows"
            ),
            extract_named_widget(
                parent,
                "grandparents_contracted_special",
                label="Dragon Wives family rows",
            ),
            dragon_wives_spouses,
            extract_named_widget(
                parent, "secondary_spouse", label="Dragon Wives family rows"
            ),
        )
    )
    text = insert_before_trailing_expand(
        text,
        'name = "PARENTS"',
        special_rows,
        parent_depth=1,
        label="Dragon Wives family row target",
    )
    return restore_agot_character_widgets(text)


def generate(context: GenerationContext) -> None:
    outputs: dict[str, str] = {}
    outputs["gui/interaction_declare_war.gui"] = generate_declare_war(context)
    outputs["gui/interaction_menu_window.gui"] = generate_interaction_menu(context)
    for relative in (
        "gui/shared/coa_designer.gui",
        "gui/window_accolade.gui",
        "gui/window_factions.gui",
    ):
        text, _ = merge_gui(context, relative, prefer_cuio=False)
        outputs[relative] = text
    tooltip, _ = merge_gui(context, "gui/shared/cooltip.gui", prefer_cuio=True)
    cuio_tooltip = pinned_text(context, "cuio", "gui/shared/cooltip.gui")
    # AGOT disables the faith struggle effect by commenting its whole type.
    # CUIO modifies that type, so a line-level merge would leave the CUIO body
    # outside a type declaration.  The CUIO-first policy keeps its valid type.
    tooltip = replace_between(
        tooltip,
        "# type StrugglePhaseEffectFaith = vbox {",
        "type StrugglePhaseEffectOther",
        extract_type(
            cuio_tooltip, "StrugglePhaseEffectFaith", label="CUIO faith struggle type"
        )
        + "\n\n",
        label="AGOT/CUIO faith struggle reconciliation",
    )
    tooltip = replace_between(
        tooltip,
        "# template phase_effect_tooltip_faith {",
        "template phase_effect_tooltip_other",
        extract_template(
            cuio_tooltip,
            "phase_effect_tooltip_faith",
            label="CUIO faith struggle template",
        )
        + "\n\n",
        label="AGOT/CUIO faith struggle template reconciliation",
    )
    tooltip = replace_once(
        tooltip,
        "# StrugglePhaseEffectFaith = {}",
        "StrugglePhaseEffectFaith = {}",
        label="CUIO faith struggle widget",
    )
    for expected in (
        "Trait.IsPersonality",
        "AGOT_CULTURE_COOLTIP_CLICK",
        "Culture.HasFascination",
    ):
        require_count(tooltip, expected, 1, label="AGOT/MPD culture and trait tooltip")
    outputs["gui/shared/cooltip.gui"] = tooltip
    outputs["gui/shared/lists.gui"] = generate_lists(context)
    outputs["gui/window_character.gui"] = generate_character(context)

    factions = outputs["gui/window_factions.gui"]
    require_count(
        factions, "agot_loyalist_faction_is_shown", 1, label="AGOT loyalist factions"
    )
    for relative, text in outputs.items():
        context.write_bytes(relative, codecs.BOM_UTF8 + text.encode("utf-8"))

    for relative in (
        "gfx/interface/icons/artifact/artifact_bg.dds",
        "gfx/interface/icons/artifact/artifact_unique.dds",
    ):
        context.write_bytes(
            relative, pinned_bytes(context, "artifact-manager", relative)
        )
