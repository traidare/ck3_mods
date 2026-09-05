#!/usr/bin/env python3
"""Generate the CUIO-first GUI owner for the current AGOT playset.

The relevant Workshop GUI files use inconsistent line endings.  We normalise
them before asking ``git merge-file`` for a three-way merge, which means a real
upstream edit and a harmless reformat look alike here; sources.lock.json tells
them apart, by recording the raw bytes of every file this run reads.
"""

from __future__ import annotations

import codecs
import re
import subprocess
import tempfile
from pathlib import Path

from gen import GenerationContext
from gen.text import matching_brace, read_source, replace_exact

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


def source_path(context: GenerationContext, source: str, relative: str) -> Path:
    return context.source(source) / relative


def source_text(context: GenerationContext, source: str, relative: str) -> str:
    """Read one upstream GUI file with its line endings normalised.

    The vanilla merge base is read through here too, deliberately: a GUI change
    is only reviewable when all three sides of the three-way merge are recorded
    inputs.  Content drift is not checked here, because sources.lock.json pins
    every file the run reads rather than the subset someone remembered to list.
    """
    return read_source(source_path(context, source, relative), normalize_newlines=True)


def source_bytes(context: GenerationContext, source: str, relative: str) -> bytes:
    """Read one upstream asset verbatim, for files that are copied unchanged."""
    return source_path(context, source, relative).read_bytes()


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
    block = replace_exact(text[start : end + 1], old, new, label=label)
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


def replace_every(text: str, old: str, new: str, *, expected: int, label: str) -> str:
    require_count(text, old, expected, label=label)
    return text.replace(old, new)


def insert_after_line(
    text: str, anchor: str, addition: str, *, label: str, expected: int = 1
) -> str:
    """Add sibling lines after each anchor line, matching its indentation."""
    pattern = re.compile(rf"(?m)^([ \t]*){re.escape(anchor)}[ \t]*$")
    matches = list(pattern.finditer(text))
    if len(matches) != expected:
        raise RuntimeError(
            f"{label}: expected {expected} {anchor!r} lines, found {len(matches)}"
        )

    def expand(match: re.Match[str]) -> str:
        indent = match.group(1)
        body = "\n".join(f"{indent}{line}" for line in addition.strip().splitlines())
        return f"{match.group(0)}\n{body}"

    return pattern.sub(expand, text)


def set_visible_in_block(
    text: str, marker: str, condition: str, *, parent_depth: int, label: str
) -> str:
    """Rewrite a block's own visible condition, whatever the merge left there."""
    start, end = block_containing(text, marker, parent_depth=parent_depth, label=label)
    block = text[start : end + 1]
    match = re.search(r'(?m)^[ \t]*visible = "\[.*\]"[ \t]*$', block)
    if match is None:
        raise RuntimeError(f"{label}: no visible condition to rewrite")
    indent = re.match(r"[ \t]*", match.group(0)).group(0)
    block = f'{block[: match.start()]}{indent}visible = "[{condition}]"{block[match.end() :]}'
    return f"{text[:start]}{block}{text[end + 1 :]}"


def remove_type(text: str, name: str, *, label: str) -> str:
    """Drop a whole type declaration, with any comment lines introducing it."""
    pattern = re.compile(rf"(?m)^[ \t]*type\s+{re.escape(name)}\s*=\s*[^\n]*\{{")
    matches = list(pattern.finditer(text))
    if len(matches) != 1:
        raise RuntimeError(f"{label}: expected one type {name}, found {len(matches)}")
    match = matches[0]
    end = matching_brace(text, text.index("{", match.start(), match.end()))
    head = text.rfind("\n", 0, match.start()) + 1
    while head:
        previous = text.rfind("\n", 0, head - 1) + 1
        line = text[previous : head - 1].strip()
        if line and not line.startswith("#"):
            break
        head = previous
    tail = text.find("\n", end)
    return text[:head] + (text[tail + 1 :] if tail != -1 else "")


def script_tokens(block: str) -> str:
    """Normalise a GUI block to its functional tokens.

    Iron and Salt reproduces AGOT's shared portrait types with its own
    formatting and without AGOT's `#AGOT Modified` provenance comments, so a
    line diff reports reflow as an upstream change.  Collapsing the block to one
    whitespace-normalised token stream compares only what the engine parses.
    """
    return " ".join(
        re.sub(r"\s+", " ", line.strip())
        for line in block.splitlines()
        if line.strip() and not line.strip().startswith("#")
    )


def assert_reproduces(
    parent: str, derived: str, edits: tuple[tuple[str, str], ...], *, label: str
) -> None:
    """Assert a derived type is its parent plus exactly the named edits."""
    expected = script_tokens(parent)
    for old, new in edits:
        normalized_old = script_tokens(old)
        if normalized_old not in expected:
            raise RuntimeError(f"{label}: parent no longer contains {old!r}")
        expected = expected.replace(normalized_old, script_tokens(new), 1)
    if expected != script_tokens(derived):
        raise RuntimeError(f"{label}: derived type is no longer the parent plus edits")


def merge_gui(
    context: GenerationContext, relative: str, *, prefer_cuio: bool
) -> tuple[str, str]:
    parent_source = GUI_PARENTS[relative]
    cuio = source_text(context, "cuio", relative)
    base = source_text(context, "game", relative)
    parent = source_text(context, parent_source, relative)
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
    agot = source_text(context, "agot", "gui/interaction_menu_window.gui")
    text = replace_exact(
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
    return replace_exact(
        text,
        "visible = \"[And(Character.CanCustomizePortrait, Not(GetGlobalVariable('FSB_is_loaded').IsSet))]\"",
        "visible = \"[Not(GetGlobalVariable('FSB_is_loaded').IsSet)]\"",
        label="Better Barbershop always-visible control",
    )


def generate_declare_war(context: GenerationContext) -> str:
    text, miv = merge_gui(context, "gui/interaction_declare_war.gui", prefer_cuio=True)
    agot = source_text(context, "agot", "gui/interaction_declare_war.gui")
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
    # for dragons and hidden characters. Without the gate a dragon renders
    # through CUIO's human layout.
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
        "agot_hidden_character_view = {}\nagot_dragons_character_view = {}",
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
    text = replace_exact(
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
    text = replace_exact(
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
    # CUIO added a plain sex icon beside each sexuality icon, so the bare
    # vanilla gender condition now appears twice per gender and cannot be
    # matched on its own.  Anchor on each icon's texture instead.  Both pairs
    # get AGOT's scripted gate: it excludes dragons, which are characters in
    # AGOT and would otherwise draw a human sex icon in their character window.
    for gender in ("male", "female"):
        vanilla = (
            "Not(Character.IsFemale)" if gender == "male" else "Character.IsFemale"
        )
        for icon in (f"sex_icon_{gender}", f"sexuality_icons_{gender}"):
            text = replace_within_block(
                text,
                f'texture = "gfx/interface/icons/character_status/{icon}.dds"',
                f'visible = "[{vanilla}]"',
                agot_gender_shown(gender),
                parent_depth=0,
                label=f"AGOT {icon} gate",
            )
    # Title list: AGOT reuses the nomad frame for pirate domiciles.
    text = append_to_block(
        text,
        'visible = "[TitleItem.GetTitle.IsNomad]"',
        "agot_pirate_title_icon = {}",
        parent_depth=1,
        label="AGOT pirate title icon",
    )
    text = replace_exact(
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
    text = replace_exact(
        text,
        'visible = "[Not( Character.IsPlayer )]"',
        "visible = yes",
        label="MPD AI personality visibility",
    )
    # MPD's XP roller hangs off an invisible 1x1 widget in the character window.
    # CUIO rebuilds that region, so the three-way merge resolves the insertion
    # away and the roller never fires for characters this playset only ever
    # views.  Re-attach it to the window itself, where CUIO's layout cannot
    # move it; placement is irrelevant for a zero-size hook.
    text = append_to_block(
        text,
        'name = "character_window"',
        extract_named_widget(parent, "mpd_view_hook", label="MPD view hook"),
        parent_depth=0,
        label="MPD view hook target",
    )
    text = replace_exact(
        text,
        "visible = \"[Not(Or(GreaterThan_int32( Character.GetMaxSpouses, '(int32)1' ), GreaterThan_int32( Character.GetMaxConsorts, '(int32)0' )))]\"",
        "visible = \"[And(Not(GetScriptedGui('dw_valyrian_special').IsShown(GuiScope.SetRoot(Character.MakeScope).End)), Not(Or(GreaterThan_int32( Character.GetMaxSpouses, '(int32)1' ), GreaterThan_int32( Character.GetMaxConsorts, '(int32)0' ))))]\"",
        label="Dragon Wives grandparents visibility",
    )
    text = replace_exact(
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
    dragon_wives_spouses = replace_exact(
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


# Iron and Salt keeps human interface off krakens, which are ordinary characters
# that AGOT's own creature views take over.  It expresses that gate two ways: a
# `kraken_character_window` scripted GUI in the AGOT files it rebuilds, and the
# `Character.HasTrait` data function in its own shared portrait types.  This
# module emits the data function everywhere.
#
# The two forms are equivalent — the scripted GUI's `is_shown` is exactly
# `has_trait = kraken` — but only the data function is safe on an invalid
# datacontext.  Several of these host widgets are instantiated with one:
# `portrait_opinion` carries `Character.IsValid` in vanilla for that reason.
# CK3's `And()` is a function call and evaluates every argument, so an earlier
# validity term does not stop a later one from running, and entering the script
# system with an invalid root raises `untyped trigger [ Scoped object of type
# 'character' is not valid ]` on every GUI update for as long as the widget
# lives.  Data functions return their default on an invalid handle instead.
#
# The character expression is whatever the host widget already provides.
CHARACTER = "Character"
CHARACTER_WINDOW = "CharacterWindow.GetCharacter"

KRAKEN_TRAIT_CHECK = "HasTrait(GetTrait('kraken'))"


def is_kraken(character: str = CHARACTER) -> str:
    return f"{character}.{KRAKEN_TRAIT_CHECK}"


def not_kraken(character: str = CHARACTER) -> str:
    return f"Not({is_kraken(character)})"


def kraken_visible(condition: str, character: str = CHARACTER) -> str:
    return f'visible = "[And({condition}, {not_kraken(character)})]"'


NOT_DRAGON_OR_KRAKEN = kraken_visible("Not(IsCharacterDragon)")


def require_kraken_widgets(
    source: str, widgets: tuple[str, ...], *, label: str
) -> None:
    """Assert Iron and Salt still calls the widgets we re-attach for it."""
    for widget in widgets:
        require_count(source, f"{widget} = {{}}", 1, label=label)


def add_kraken_to_cooltip(text: str, iron_and_salt: str) -> str:
    """Re-apply Iron and Salt's kraken gates to the merged character cooltip."""
    label = "Iron and Salt cooltip"
    require_kraken_widgets(
        iron_and_salt,
        ("container_kraken_character_tooltip", "kraken_cooltip_type_living"),
        label=label,
    )
    text = insert_after_line(
        text,
        "container_dragon_character_tooltip = {}",
        "container_kraken_character_tooltip = {}",
        label=f"{label} tooltip container",
    )
    text = insert_after_line(
        text,
        "agot_dragon_type_dead = {}",
        "kraken_cooltip_type_living = {}",
        label=f"{label} creature type row",
    )
    # The opinion badge and its spacer share one condition, as do AGOT's two
    # `visible_if_not_dragon` sites: the relation line and the portrait tooltip.
    text = replace_every(
        text,
        'visible = "[And(And(Character.IsAlive, Not(IsCharacterDragon)), Not(Character.IsPlayer))]"',
        kraken_visible(
            "And(And(Character.IsAlive, Not(IsCharacterDragon)), Not(Character.IsPlayer))"
        ),
        expected=2,
        label=f"{label} opinion badge and spacer",
    )
    text = replace_every(
        text,
        "using = visible_if_not_dragon",
        NOT_DRAGON_OR_KRAKEN,
        expected=2,
        label=f"{label} relation line and portrait tooltip",
    )
    for condition, site in (
        ("And(Not(Character.IsPlayer), Not(IsCharacterDragon))", "AI personality"),
        ("And(Character.IsAlive, Not(IsCharacterDragon))", "spouse listing"),
        ("Not(IsCharacterDragon)", "status row"),
    ):
        text = replace_every(
            text,
            f'visible = "[{condition}]"',
            kraken_visible(condition),
            expected=1,
            label=f"{label} {site}",
        )
    # AGOT gates all four gender icons on its scripted GUI so dragons draw no
    # human sex icon, but only the female sexuality icon survived the CUIO-first
    # merge.  Restore the other three from the same anchor `window_character.gui`
    # already uses — each icon's texture — and exclude krakens from all four.
    for gender in ("male", "female"):
        for icon in (f"sex_icon_{gender}", f"sexuality_icons_{gender}"):
            text = set_visible_in_block(
                text,
                f'texture = "gfx/interface/icons/character_status/{icon}.dds"',
                f"And(GetScriptedGui('agot_{gender}_gender_shown')"
                f".IsShown(GuiScope.SetRoot({CHARACTER}.MakeScope).End),"
                f" {not_kraken()})",
                parent_depth=0,
                label=f"{label} {icon} gate",
            )
    return text


def add_kraken_to_lists(text: str, iron_and_salt: str) -> str:
    """Re-apply Iron and Salt's kraken gates to the merged character lists."""
    label = "Iron and Salt lists"
    kraken_rows = (
        "kraken_lists_size_text",
        "kraken_lists_combat_text",
        "kraken_lists_terror_text",
    )
    for widget in kraken_rows:
        require_count(iron_and_salt, f"{widget} = {{}}", 2, label=label)
    text = insert_after_line(
        text,
        "agot_lists_dragon_temper_text = {}",
        "\n".join(f"{widget} = {{}}" for widget in kraken_rows),
        expected=2,
        label=f"{label} creature stat rows",
    )
    # The relation line uses the shared template added by `generate_lists`;
    # AGOT writes the remaining human-only rows as explicit visibility tests.
    text = replace_every(
        text,
        "using = visible_if_not_dragon",
        NOT_DRAGON_OR_KRAKEN,
        expected=1,
        label=f"{label} relation row",
    )
    return replace_every(
        text,
        'visible = "[Not(IsCharacterDragon)]"',
        NOT_DRAGON_OR_KRAKEN,
        expected=7,
        label=f"{label} human-only rows",
    )


def add_kraken_to_character(text: str, iron_and_salt: str) -> str:
    """Hand the character window to AGOT's kraken sheet, as Iron and Salt does."""
    label = "Iron and Salt character window"
    require_kraken_widgets(iron_and_salt, ("agot_kraken_character_view",), label=label)
    text = insert_after_line(
        text,
        "agot_dragons_character_view = {}",
        "agot_kraken_character_view = {}",
        label=f"{label} creature view",
    )
    # Both the AGOT-gated main content and CUIO's control strip; each alternate
    # sheet supplies its own controls.
    return replace_every(
        text,
        'visible = "[IsCharacterNormal]"',
        kraken_visible("IsCharacterNormal", CHARACTER_WINDOW),
        expected=2,
        label=f"{label} normal-character gate",
    )


def generate_portraits(context: GenerationContext) -> dict[str, str]:
    """Own every declaration of the three contested shared portrait types.

    CK3 registers a GUI type from the *first* file that declares it in merged
    path order, the opposite of the last-writer rule for same-path payload, so
    which copy of `portrait_opinion` wins is decided by filename rather than by
    load order.  Rather than depend on that, this module takes over all four
    declaring files so exactly one declaration of each type survives.
    """
    cuio = source_text(context, "cuio", "gui/CUIO_portraits.gui")
    agot = source_text(context, "agot", "gui/shared/portraits.gui")
    kraken_opinion = source_text(
        context, "iron-and-salt", "gui/shared/00_kraken_portrait_opinion.gui"
    )
    kraken_heads = source_text(
        context, "iron-and-salt", "gui/shared/zz_kraken_list_portraits.gui"
    )
    label = "shared portrait types"

    # The small opinion badge and small head follow AGOT's current types with a
    # kraken branch added to each. Iron and Salt supplies the target files and
    # the kraken widgets those branches instantiate.
    agot_small_opinion = 'visible = "[And(And(Character.IsValid, Not(IsCharacterDragon)), And(Character.IsAlive, Not(Character.IsLocalPlayer)))]"'
    kraken_small_opinion = kraken_visible(
        "And(And(And(Character.IsValid, Character.IsAlive),"
        " Not(Character.IsLocalPlayer)), Not(IsCharacterDragon))"
    )
    agot_small_opinion_type = extract_type(agot, "portrait_opinion_small", label=label)
    iron_small_opinion_type = extract_type(
        kraken_opinion, "portrait_opinion_small", label=label
    )
    # Both of Iron and Salt's own declarations of these shared types gate krakens
    # with the trait data function rather than its scripted GUI, because the
    # types are instantiated with invalid character datacontexts.  That is the
    # form this module emits at every call site, so pin it on both.
    for type_name, site in (
        ("portrait_opinion", "opinion badge"),
        ("portrait_opinion_small", "small opinion badge"),
    ):
        require_count(
            extract_type(kraken_opinion, type_name, label=label),
            is_kraken(),
            1,
            label=f"{label}: Iron and Salt {site}",
        )
    kraken_small_opinion_type = replace_exact(
        agot_small_opinion_type,
        agot_small_opinion,
        kraken_small_opinion,
        label=f"{label}: portrait_opinion_small kraken gate",
    )
    kraken_opinion = replace_exact(
        kraken_opinion,
        iron_small_opinion_type,
        kraken_small_opinion_type,
        label=f"{label}: portrait_opinion_small",
    )
    assert_reproduces(
        extract_type(agot, "portrait_head_small", label=label),
        extract_type(kraken_heads, "portrait_head_small", label=label),
        (
            (
                'visible = "[Not(IsCharacterDragon)]"',
                'visible = "[And( Not( IsCharacterDragon ),'
                " Not( Character.HasTrait( GetTrait('kraken') ) ) )]\"",
            ),
            (
                "agot_dragons_portrait_head_small = {}",
                "agot_dragons_portrait_head_small = {}\nkraken_portrait_head_small = {}",
            ),
        ),
        label=f"{label}: portrait_head_small",
    )

    # CUIO's dual opinion badge is the layout owner. Apply AGOT's dragon gates
    # and Iron and Salt's kraken gate to that layout.  CUIO's own condition
    # opens with `Character.IsValid`, as vanilla's does, because the type is
    # instantiated with invalid character datacontexts; the kraken gate is
    # appended in the form that tolerates one.
    portraits = replace_exact(
        cuio,
        'visible = "[And(Character.IsValid, And(Character.IsAlive, Not(Character.IsLocalPlayer)))]"',
        kraken_visible(
            "And(And(Character.IsValid, Not(IsCharacterDragon)),"
            " And(Character.IsAlive, Not(Character.IsLocalPlayer)))"
        ),
        label=f"{label}: CUIO opinion badge",
    )
    portraits = replace_exact(
        portraits,
        'visible = "[Character.ShouldShowDreadEffectIcon]"',
        'visible = "[And(Not(IsCharacterDragon), Character.ShouldShowDreadEffectIcon)]"',
        label=f"{label}: CUIO dread icon",
    )
    outputs = {
        "gui/CUIO_portraits.gui": portraits,
        "gui/shared/00_kraken_portrait_opinion.gui": remove_type(
            kraken_opinion, "portrait_opinion", label=f"{label}: Iron and Salt badge"
        ),
        "gui/shared/zz_kraken_list_portraits.gui": kraken_heads,
        "gui/shared/portraits.gui": agot,
    }
    for name in ("portrait_opinion", "portrait_opinion_small", "portrait_head_small"):
        outputs["gui/shared/portraits.gui"] = remove_type(
            outputs["gui/shared/portraits.gui"], name, label=f"{label}: AGOT {name}"
        )
        declarations = sum(
            len(re.findall(rf"(?m)^[ \t]*type\s+{name}\s*=", text))
            for text in outputs.values()
        )
        if declarations != 1:
            raise RuntimeError(
                f"{label}: {name} is declared {declarations} times, expected 1"
            )
    return outputs


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
    cuio_tooltip = source_text(context, "cuio", "gui/shared/cooltip.gui")
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
    tooltip = replace_exact(
        tooltip,
        "# StrugglePhaseEffectFaith = {}",
        "StrugglePhaseEffectFaith = {}",
        label="CUIO faith struggle widget",
    )
    # AGOT keeps the culture cooltip body in its own additive
    # gui/shared/agot_cooltip.gui and wires it from cooltip.gui by type
    # reference, so assert the two call sites survive the CUIO merge rather
    # than the AGOT_CULTURE_COOLTIP_CLICK text that file no longer holds.
    for expected in (
        "Trait.IsPersonality",
        "agot_culture_tooltip_insert = {}",
        "agot_culture_tooltip_click = {}",
    ):
        require_count(tooltip, expected, 1, label="AGOT/MPD culture and trait tooltip")
    # Two guards, not one: AGOT gates the fascination row *and* the divider
    # above it ("fascinations not always active"), where vanilla and CUIO gate
    # only the row. Dropping to 1 means the CUIO side won the divider and an
    # empty separator draws for cultures without a fascination.
    require_count(
        tooltip,
        "Culture.HasFascination",
        2,
        label="AGOT/MPD culture and trait tooltip",
    )
    outputs["gui/shared/cooltip.gui"] = add_kraken_to_cooltip(
        tooltip, source_text(context, "iron-and-salt", "gui/shared/cooltip.gui")
    )
    outputs["gui/shared/lists.gui"] = add_kraken_to_lists(
        generate_lists(context),
        source_text(context, "iron-and-salt", "gui/shared/lists.gui"),
    )
    outputs["gui/window_character.gui"] = add_kraken_to_character(
        generate_character(context),
        source_text(context, "iron-and-salt", "gui/window_character.gui"),
    )
    outputs.update(generate_portraits(context))

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
            relative, source_bytes(context, "artifact-manager", relative)
        )
