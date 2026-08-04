#!/usr/bin/env python3
"""Generate narrow runtime repairs for the current AGOT playset.

The source files remain owned by their Workshop parents.  Every replacement is
counted so an upstream update fails loudly instead of silently generating a
stale whole-file override.
"""

from __future__ import annotations

import hashlib
import os
import re
import textwrap
from decimal import Decimal
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKSHOP = ROOT / ".ignored/CK3_workshop"
OUTPUT = ROOT / "mods/agot_playset_runtime_fixes"
AGOT_PLUS_OUTPUT = ROOT / "mods/agot_plus_119_runtime_rebase"
NOW_OUTPUT = ROOT / "mods/agot_now_119_rebase"
MFA_OUTPUT = ROOT / "mods/agot_mfa_039_rebase"
GR_OUTPUT = ROOT / "mods/grand_remembrance_119_runtime_fix"


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def write_text(
    root: Path,
    relative: str,
    text: str,
    *,
    preserve_trailing_whitespace: bool = False,
    force_newline: str | None = None,
    with_bom: bool = True,
) -> None:
    target = root / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    if force_newline is not None:
        newline = force_newline
    elif root == AGOT_PLUS_OUTPUT:
        # AGOT+ ships CRLF files. Preserve that form so generated rebases
        # remain reviewable against both the parent and the tracked override.
        newline = "\r\n"
    else:
        if not preserve_trailing_whitespace:
            text = re.sub(r"[ \t]+(?=\r?$)", "", text, flags=re.MULTILINE)
        newline = ""
    encoding = "utf-8-sig" if with_bom else "utf-8"
    target.write_text(text, encoding=encoding, newline=newline)


def normalize_rebased_source(text: str) -> str:
    """Keep full-file rebases clean without changing their script tokens."""
    text = re.sub(r" +\t", "\t", text)
    return text.rstrip() + "\n"


def replace_exact(
    text: str,
    old: str,
    new: str,
    *,
    expected: int,
    label: str,
) -> str:
    found = text.count(old)
    if found != expected:
        raise RuntimeError(
            f"{label}: expected {expected} exact source match(es), found {found}"
        )
    return text.replace(old, new)


def replace_regex(
    text: str,
    pattern: str,
    replacement: str,
    *,
    expected: int,
    label: str,
    flags: int = 0,
) -> str:
    text, found = re.subn(pattern, replacement, text, flags=flags)
    if found != expected:
        raise RuntimeError(
            f"{label}: expected {expected} regex source match(es), found {found}"
        )
    return text


def assert_source_block_hash(
    text: str,
    key: str,
    expected_hash: str,
    *,
    label: str,
) -> str:
    """Return a pinned top-level block, failing closed on upstream drift."""
    block = extract_top_level_block(text, key)
    actual_hash = hashlib.sha256(block.encode()).hexdigest()
    if actual_hash != expected_hash:
        raise RuntimeError(
            f"{label} changed: expected {expected_hash}, found {actual_hash}"
        )
    return block


def script_brace_delta(line: str) -> int:
    code = line.split("#", 1)[0]
    code = re.sub(r'"(?:\\.|[^"\\])*"', '""', code)
    return code.count("{") - code.count("}")


def balanced_brace_end(text: str, open_index: int) -> int:
    depth = 0
    in_string = False
    escaped = False
    in_comment = False
    for index in range(open_index, len(text)):
        char = text[index]
        if in_comment:
            if char == "\n":
                in_comment = False
            continue
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == "#":
            in_comment = True
        elif char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return index
    raise RuntimeError(f"unbalanced block beginning at byte {open_index}")


def replace_numbered_branch_with_constant(
    text: str,
    number: int,
    value: bool,
    *,
    label: str,
) -> str:
    pattern = re.compile(rf"(?m)^([ \t]*){number}\s*=\s*\{{")
    matches = list(pattern.finditer(text))
    if len(matches) != 1:
        raise RuntimeError(
            f"{label}: expected one switch branch {number}, found {len(matches)}"
        )
    match = matches[0]
    open_index = text.index("{", match.start())
    end_index = balanced_brace_end(text, open_index)
    replacement = (
        f"{match.group(1)}{number} = {{ always = {'yes' if value else 'no'} }}"
    )
    return text[: match.start()] + replacement + text[end_index + 1 :]


def remove_if_block_for_artifact_modifier(
    text: str,
    modifier: str,
    *,
    label: str,
) -> str:
    marker = f"limit = {{ has_artifact_modifier = {modifier} }}"
    marker_count = text.count(marker)
    if marker_count != 1:
        raise RuntimeError(
            f"{label}: expected one {modifier} upgrade limit, found {marker_count}"
        )
    marker_index = text.index(marker)
    candidates = list(re.finditer(r"(?m)^[ \t]*if\s*=\s*\{", text[:marker_index]))
    if not candidates:
        raise RuntimeError(f"{label}: no enclosing if block for {modifier}")
    block_match = candidates[-1]
    open_index = text.index("{", block_match.start())
    end_index = balanced_brace_end(text, open_index)
    if marker_index >= end_index:
        raise RuntimeError(f"{label}: nearest if block did not contain {modifier}")
    if end_index + 1 < len(text) and text[end_index + 1] == "\n":
        end_index += 1
    return text[: block_match.start()] + text[end_index + 1 :]


def unwrap_unconditional_random_pool_ifs(
    text: str, *, expected: int, label: str
) -> str:
    """Remove invalid if wrappers whose sole child is a random-pool effect."""
    pattern = re.compile(
        r"(?m)^[ \t]*if\s*=\s*\{\n[ \t]*random_pool_character\s*=\s*\{"
    )
    replacements: list[tuple[int, int, str]] = []
    for match in pattern.finditer(text):
        if any(start <= match.start() < end for start, end, _ in replacements):
            continue
        if_open = text.find("{", match.start(), match.end())
        if_end = balanced_brace_end(text, if_open)
        child_start = text.find("random_pool_character", if_open, match.end())
        child_open = text.find("{", child_start, match.end())
        child_end = balanced_brace_end(text, child_open)
        if text[child_end + 1 : if_end].strip():
            raise RuntimeError(
                f"{label}: unconditional if contains more than its random pool"
            )
        replacement = text[if_open + 1 : child_end + 1].lstrip("\r\n")
        replacements.append((match.start(), if_end + 1, replacement))

    if len(replacements) != expected:
        raise RuntimeError(
            f"{label}: expected {expected} unconditional random-pool if "
            f"wrapper(s), found {len(replacements)}"
        )
    for start, end, replacement in reversed(replacements):
        text = f"{text[:start]}{replacement}{text[end:]}"
    return text


def scale_fractional_random_list_weights(
    text: str,
    *,
    expected_lists: int,
    expected_fractional_weights: int,
    label: str,
) -> str:
    """Scale affected random-list weights by ten so every weight is integral."""
    replacements: list[tuple[int, int, str]] = []
    affected_lists = 0
    fractional_weights = 0
    random_list_pattern = re.compile(r"(?m)^[ \t]*random_list\s*=\s*\{")
    weight_pattern = re.compile(r"^[ \t]*(\d+(?:\.\d+)?)\s*(?==\s*\{)")

    for match in random_list_pattern.finditer(text):
        open_index = text.find("{", match.start(), match.end())
        end_index = balanced_brace_end(text, open_index)
        cursor = text.find("\n", match.end())
        if cursor < 0 or cursor > end_index:
            continue
        cursor += 1
        depth = 1
        weights: list[tuple[int, int, str]] = []
        list_fractional = 0
        while cursor < end_index:
            newline = text.find("\n", cursor, end_index + 1)
            if newline < 0:
                newline = end_index
            line = text[cursor:newline]
            if depth == 1:
                weight_match = weight_pattern.match(line)
                if weight_match:
                    token = weight_match.group(1)
                    start = cursor + weight_match.start(1)
                    finish = cursor + weight_match.end(1)
                    weights.append((start, finish, token))
                    if "." in token:
                        list_fractional += 1
            depth += script_brace_delta(line)
            cursor = newline + 1

        if list_fractional:
            affected_lists += 1
            fractional_weights += list_fractional
            for start, finish, token in weights:
                scaled = Decimal(token) * 10
                if scaled != scaled.to_integral_value():
                    raise RuntimeError(
                        f"{label}: weight {token} does not become integral "
                        "when scaled by ten"
                    )
                replacements.append((start, finish, str(int(scaled))))

    if affected_lists != expected_lists:
        raise RuntimeError(
            f"{label}: expected {expected_lists} fractional random list(s), "
            f"found {affected_lists}"
        )
    if fractional_weights != expected_fractional_weights:
        raise RuntimeError(
            f"{label}: expected {expected_fractional_weights} fractional "
            f"weight(s), found {fractional_weights}"
        )
    for start, finish, replacement in reversed(replacements):
        text = f"{text[:start]}{replacement}{text[finish:]}"
    return text


def history_character_ids(*workshop_ids: str) -> set[str]:
    ids: set[str] = set()
    pattern = re.compile(r"^([A-Za-z0-9_]+)\s*=\s*\{", re.MULTILINE)
    for workshop_id in workshop_ids:
        history = WORKSHOP / workshop_id / "history/characters"
        if not history.is_dir():
            continue
        for path in history.rglob("*.txt"):
            ids.update(pattern.findall(read_text(path)))
    return ids


def game_root() -> Path:
    configured = os.environ.get("CK3_GAME_DIR")
    if not configured:
        raise RuntimeError(
            "CK3_GAME_DIR is required to generate the vanilla tour-effect "
            "rebase (it is normally loaded from .env by the dev shell)"
        )
    root = Path(configured)
    if (root / "game").is_dir():
        root /= "game"
    if not root.is_dir():
        raise RuntimeError(f"CK3_GAME_DIR does not exist: {root}")
    return root


def generate_seasons_agot_shaders() -> None:
    """Repair legacy Seasons shaders or retire the superseded local override."""
    seasons = WORKSHOP / "3377641022"
    current_tree = read_text(WORKSHOP / "2962333032/gfx/FX/tree.shader")
    include_renames = {
        "gh_atmospheric.fxh": "agot_atmospheric.fxh",
        "gh_portrait_constants.fxh": "agot_portrait_constants.fxh",
        "gh_portrait_decals_shared.fxh": "agot_portrait_decals_shared.fxh",
        "gh_dynamic_terrain.fxh": "agot_dynamic_terrain.fxh",
        "gh_tree.fxh": "agot_tree.fxh",
    }
    for current in include_renames.values():
        if current_tree.count(f'"{current}"') != 1:
            raise RuntimeError(
                f"AGOT tree shader interface changed: expected {current}"
            )
    if re.search(r"\bGH_[A-Za-z0-9_]+", current_tree):
        raise RuntimeError("AGOT tree shader restored the old GH interface")

    filenames = (
        "tree_autumn_orange.shader",
        "tree_autumn_red.shader",
        "tree_autumn_yellow.shader",
        "tree_piney_winey.shader",
    )
    for filename in filenames:
        relative = f"gfx/FX/{filename}"
        text = read_text(seasons / relative)
        stale_includes = sum(text.count(f'"{stale}"') for stale in include_renames)
        if stale_includes:
            if stale_includes != len(include_renames):
                raise RuntimeError(
                    f"Seasons shader interface is partially rebased: {filename}"
                )
            for stale, current in include_renames.items():
                text = replace_exact(
                    text,
                    f'"{stale}"',
                    f'"{current}"',
                    expected=1,
                    label=f"Seasons shader include {stale} in {filename}",
                )
            text = replace_regex(
                text,
                r"\bGH_",
                "AGOT_",
                expected=10,
                label=f"Seasons AGOT shader symbols in {filename}",
            )
            text = replace_exact(
                text,
                "MOD(godherja)",
                "MOD(agot)",
                expected=8,
                label=f"Seasons AGOT shader annotations in {filename}",
            )
            write_text(
                OUTPUT,
                relative,
                text,
                preserve_trailing_whitespace=True,
            )
            continue

        for current in include_renames.values():
            if text.count(f'"{current}"') != 1:
                raise RuntimeError(
                    f"Seasons shader interface changed: expected {current} in {filename}"
                )
        if re.search(r"\bGH_[A-Za-z0-9_]+", text) or "MOD(godherja)" in text:
            raise RuntimeError(
                f"Seasons shader retained the old GH interface: {filename}"
            )

        # Seasons 0.5.6 includes the current AGOT interface itself.  Remove the
        # old whole-file replacement so later updates are not hidden by a stale
        # local copy.
        output_path = OUTPUT / relative
        if output_path.is_file():
            output_path.unlink()
        elif output_path.exists():
            raise RuntimeError(f"expected a file or no output at {output_path}")


def generate_mari_agot_portraits() -> None:
    """Remove portrait genes deleted by AGOT 0.4.40 and repair one DNA typo."""
    mari = WORKSHOP / "3462342647"
    obsolete_gene_line = re.compile(
        r"(?m)^[ \t]*(?:gene_GH_marker_clothing_[1-7]_[rgb]|"
        r"special_accessories_earrings)\s*=\s*\{[^\r\n]*\}\r?\n"
    )
    template_replacements = (
        ('"aegon_crown_gems"', '"agot_crowns"', 0, 1),
        ('"aegon_crown_no_gems"', '"agot_crowns"', 0, 1),
        ('"crowns_of_westeros"', '"agot_crowns"', 13, 18),
        (
            '"valyrian_nobility_clothing_generic"',
            '"agot_all_clothes"',
            3,
            1,
        ),
        (
            '"valyrian_nobility_clothing"',
            '"agot_all_clothes"',
            3,
            3,
        ),
        ('"female_stacked_pearls"', '"no_jewelry"', 2, 0),
        ('"female_pointed_necklace"', '"no_jewelry"', 2, 0),
    )

    relative = "common/dna_data/mari_new_dna_data.txt"
    text = read_text(mari / relative)
    text, removed = obsolete_gene_line.subn("", text)
    if removed != 915:
        raise RuntimeError(
            f"Mari DNA: expected 915 removed AGOT genes, found {removed}"
        )
    for stale, current, expected_dna, _ in template_replacements:
        text = replace_exact(
            text,
            stale,
            current,
            expected=expected_dna,
            label=f"Mari DNA removed template {stale}",
        )
    text = replace_exact(
        text,
        'gene_dragon_size={ "non_dragon_size" 127 "non_dragon_size" 127 }`',
        'gene_dragon_size={ "non_dragon_size" 127 "non_dragon_size" 127 }',
        expected=1,
        label="Mari Aegon V DNA stray backtick",
    )
    text = replace_exact(
        text,
        'gene_height={ "normal_height" 126 "normal_height" 12/ }',
        'gene_height={ "normal_height" 126 "normal_height" 127 }',
        expected=1,
        label="Mari Mace Tyrell DNA height value",
    )
    write_text(
        OUTPUT,
        relative,
        text,
        preserve_trailing_whitespace=True,
    )

    portraits = mari / "common/bookmark_portraits"
    affected: list[tuple[Path, str, int]] = []
    bookmark_replacement_counts = {stale: 0 for stale, _, _, _ in template_replacements}
    for source in sorted(portraits.glob("*.txt")):
        source_text = read_text(source)
        repaired, removed = obsolete_gene_line.subn("", source_text)
        for stale, current, _, _ in template_replacements:
            count = repaired.count(stale)
            bookmark_replacement_counts[stale] += count
            repaired = repaired.replace(stale, current)
        if repaired != source_text:
            affected.append((source, repaired, removed))
    if len(affected) != 50:
        raise RuntimeError(
            f"Mari bookmarks: expected 50 affected files, found {len(affected)}"
        )
    removed_total = sum(removed for _, _, removed in affected)
    if removed_total != 266:
        raise RuntimeError(
            f"Mari bookmarks: expected 266 removed AGOT genes, found {removed_total}"
        )
    expected_bookmark_counts = {
        stale: expected for stale, _, _, expected in template_replacements
    }
    if bookmark_replacement_counts != expected_bookmark_counts:
        raise RuntimeError(
            "Mari bookmarks: removed-template counts changed: expected "
            f"{expected_bookmark_counts}, found {bookmark_replacement_counts}"
        )
    for source, repaired, _ in affected:
        write_text(
            OUTPUT,
            f"common/bookmark_portraits/{source.name}",
            repaired,
            preserve_trailing_whitespace=True,
        )


def generate_faster_transitions_gui() -> None:
    """Carry CK3 1.19 event-window additions into Faster Transitions."""
    relative = "gui/00_no_transition.gui"
    text = read_text(WORKSHOP / "3437814875" / relative)
    tournament = read_text(
        game_root() / "gui/activity_window_widgets/tournament_widget_types.gui"
    )
    chariot = read_text(
        game_root() / "gui/activity_window_widgets/chariot_race_widget_types.gui"
    )
    event_windows = read_text(game_root() / "gui/shared/event_windows.gui")

    fullscreen_effect = """\t\tvideo_icon = {
\t\t\tname = "shrouded_event_effect"
\t\t\tvideo = "gfx/interface/component_masks/animated_masks/contest_reveal_fin.bk2"
\t\t\tsize = { 100% 100% }
\t\t\tloop = no
\t\t\trestart_on_show = yes
\t\t}"""
    compact_effect = """\t\tvideo_icon = {
\t\t\tname = "shrouded_event_effect"
\t\t\tvideo = "gfx/interface/component_masks/animated_masks/contest_reveal_fin.bk2"
\t\t\tsize = { 95.5% 99% }
\t\t\tparentanchor = top|hcenter
\t\t\tloop = no
\t\t\trestart_on_show = yes
\t\t}"""
    if tournament.count(fullscreen_effect) != 1:
        raise RuntimeError(
            "CK3 pivotal fullscreen event effect changed; rebase Faster Transitions"
        )
    if chariot.count(compact_effect) != 1:
        raise RuntimeError(
            "CK3 compact pivotal event effect changed; rebase Faster Transitions"
        )
    if event_windows.count("\t\talwaystransparent = no\n") < 1:
        raise RuntimeError(
            "CK3 event transition input handling changed; rebase Faster Transitions"
        )
    if "shrouded_event_effect" in text:
        raise RuntimeError("Faster Transitions now carries CK3's pivotal event effects")

    text = replace_exact(
        text,
        """    blockoverride "event_transition_video_properties"
    {
      parentanchor = center
      loop = no
      restart_on_show = yes
    }
  }

  type event_window_transition_widget""",
        """    blockoverride "event_transition_video_properties"
    {
      parentanchor = center
      loop = no
      restart_on_show = yes
    }

    video_icon = {
      name = "shrouded_event_effect"
      video = "gfx/interface/component_masks/animated_masks/contest_reveal_fin.bk2"
      size = { 100% 100% }
      loop = no
      restart_on_show = yes
    }
  }

  type event_window_transition_widget""",
        expected=1,
        label="Faster Transitions fullscreen pivotal event effect",
    )
    text = replace_exact(
        text,
        """  type event_window_transition_widget = margin_widget {
\t\tsize = { 100% 100% }
\t\tdatacontext""",
        """  type event_window_transition_widget = margin_widget {
\t\tsize = { 100% 100% }
\t\talwaystransparent = no
\t\tdatacontext""",
        expected=1,
        label="Faster Transitions event-transition input handling",
    )
    text = replace_exact(
        text,
        """\t\tblockoverride "event_transition_video_properties"
\t\t{
\t\t\tparentanchor = center
\t\t\tloop = no
\t\t\trestart_on_show = yes
\t\t}
\t}
}


template PivotalMomentTransitionAnimation""",
        """\t\tblockoverride "event_transition_video_properties"
\t\t{
\t\t\tparentanchor = center
\t\t\tloop = no
\t\t\trestart_on_show = yes
\t\t}

\t\tvideo_icon = {
\t\t\tname = "shrouded_event_effect"
\t\t\tvideo = "gfx/interface/component_masks/animated_masks/contest_reveal_fin.bk2"
\t\t\tsize = { 95.5% 99% }
\t\t\tparentanchor = top|hcenter
\t\t\tloop = no
\t\t\trestart_on_show = yes
\t\t}
\t}
}


template PivotalMomentTransitionAnimation""",
        expected=1,
        label="Faster Transitions compact pivotal event effect",
    )
    write_text(
        OUTPUT,
        relative,
        text,
        force_newline="\r\n",
        with_bom=False,
    )


def generate_additional_models_on_action_deduplication() -> None:
    """Retire the superseded AMSB dynasty-on-action suppressor."""
    relative = "common/on_action/amsb_dynasty_on_actions.txt"
    compatch_relative = "common/scripted_effects/zz_am_lov_artifact_dedup_effects.txt"
    additional_models = read_text(WORKSHOP / "3319354609" / relative)
    compatch = read_text(WORKSHOP / "3762892081" / compatch_relative)
    definitions = (
        "amsb_set_legacies",
        "amsb_set_dragonlord_legacies",
        "amsb_set_starting_dynasty_levels",
    )
    for definition in definitions:
        pattern = rf"(?m)^{definition}\s*=\s*\{{"
        if len(re.findall(pattern, additional_models)) != 1:
            raise RuntimeError(f"Additional Models definition changed: {definition}")
        if len(re.findall(pattern, compatch)) != 0:
            raise RuntimeError(
                f"Additional Models/AGOT+/LoV compatch restored duplicate "
                f"definition: {definition}"
            )
    for definition in (
        "amsb_historical_artifacts_setup",
        "amsb_assign_starting_family_weapons_effect",
    ):
        if len(re.findall(rf"(?m)^{definition}\s*=\s*\{{", compatch)) != 1:
            raise RuntimeError(
                f"Additional Models/AGOT+/LoV compatch definition changed: {definition}"
            )
    output_path = OUTPUT / relative
    if output_path.is_file():
        output_path.unlink()
    elif output_path.exists():
        raise RuntimeError(f"expected a file or no output at {output_path}")


def generate_kurultai_succession_scope_repairs() -> None:
    """Repair the two invalid scopes reached by chaotic Kurultai succession."""
    source_relative = "common/scripted_effects/09_dlc_mpo_scripted_effects.txt"
    parent_sources = {
        "AGOT": read_text(WORKSHOP / "2962333032" / source_relative),
        "CK3": read_text(game_root() / source_relative),
    }
    expected_hashes = {
        "nomadic_heir_cleanup_realm_effect": (
            "5833144559ca644280803314b5874e04e397b6705bcc2af2539b201562d563bf"
        ),
        "nomadic_realm_split_effect": (
            "3dbe761f4557589422c44a5ef276549550a22a7d168bc736f20dee27b51423b6"
        ),
    }
    blocks: dict[str, str] = {}
    for effect, expected_hash in expected_hashes.items():
        for parent, source in parent_sources.items():
            block = extract_top_level_block(source, effect)
            actual_hash = hashlib.sha256(block.encode()).hexdigest()
            if actual_hash != expected_hash:
                raise RuntimeError(
                    f"{parent} Kurultai source changed: {effect} expected "
                    f"{expected_hash}, found {actual_hash}"
                )
            if parent == "AGOT":
                blocks[effect] = block

    cleanup = replace_exact(
        blocks["nomadic_heir_cleanup_realm_effect"],
        "\t\t\t\tscope:recipient = {\n\t\t\t\t\tchange_liege = {",
        "\t\t\t\tscope:inheritor_char = {\n\t\t\t\t\tchange_liege = {",
        expected=1,
        label="Kurultai inheritor liege scope",
    )
    if "scope:recipient = {" in cleanup:
        raise RuntimeError("Kurultai cleanup retained the missing recipient scope")

    realm_split = replace_exact(
        blocks["nomadic_realm_split_effect"],
        "\t\t\tif = {\n"
        "\t\t\t\tlimit = {\n"
        "\t\t\t\t\tNOT = {\n"
        "\t\t\t\t\t\tthis = scope:new_ruler_scope\n"
        "\t\t\t\t\t}\n"
        "\t\t\t\t\tholder = {\n",
        "\t\t\tif = {\n"
        "\t\t\t\tlimit = {\n"
        "\t\t\t\t\tNOT = {\n"
        "\t\t\t\t\t\tholder = scope:new_ruler_scope\n"
        "\t\t\t\t\t}\n"
        "\t\t\t\t\tholder = {\n",
        expected=1,
        label="Kurultai county-holder comparison scope",
    )
    repaired_holder_guard = (
        "\t\t\t\t\tNOT = {\n"
        "\t\t\t\t\t\tholder = scope:new_ruler_scope\n"
        "\t\t\t\t\t}\n"
        "\t\t\t\t\tholder = {\n"
    )
    if realm_split.count(repaired_holder_guard) != 1:
        raise RuntimeError("Kurultai split holder comparison repair changed")
    if realm_split.count("this = scope:new_ruler_scope") != 1:
        raise RuntimeError("Kurultai split valid holder-scope comparison changed")

    write_text(
        OUTPUT,
        "common/scripted_effects/zz_agot_playset_kurultai_succession_fixes.txt",
        (
            "# Generated narrow repairs for CK3 1.19 chaotic Kurultai succession.\n"
            "# Source: AGOT 0.4.40 / common/scripted_effects/"
            "09_dlc_mpo_scripted_effects.txt\n\n"
            f"{cleanup}\n\n{realm_split}\n"
        ),
    )


def generate_essos_disabled_realm_cleanup() -> None:
    """Initialize disabled Essos Expanded realms directly as LoV wilderness."""
    realms = (
        "bloodless_men",
        "cannibal_sands",
        "hidden_sea",
        "ibben",
        "ifequevron",
        "lesser_moraq",
        "lorath",
        "mossovy",
        "naath",
        "norvos",
        "omber",
        "qohor",
        "sarnor",
        "sothoryos",
        "summer_isles",
        "thousand_islands",
        "ulthos",
        "upper_sarne_dothraki",
        "lower_sarne_dothraki",
        "great_grass_sea_dothraki",
        "bone_mountain_dothraki",
        "lhazar",
        "qarth",
        "golden_yi_ti",
        "jogos_nhai",
        "great_moraq",
        "leng",
    )
    game_rules = read_text(
        WORKSHOP / "3682802751/common/game_rules/01_essos_empire_game_rules.txt"
    )
    on_action = read_text(WORKSHOP / "3682802751/common/on_action/essos_game_start.txt")
    family_effects = read_text(
        WORKSHOP / "3682802751/common/scripted_effects/essos_family_effects.txt"
    )
    agot_remove_realms = read_text(
        WORKSHOP
        / "2962333032/common/scripted_effects/00_agot_remove_realms_effects.txt"
    )
    lov_colonization = read_text(
        WORKSHOP / "3719888822/common/scripted_effects/00_agot_colonization_effects.txt"
    )
    assert_source_block_hash(
        on_action,
        "essos_generate_families",
        "b94b4bc55ecdf1890ec6667fe4366b38a5b6a6af8f9d4d941b5b9726df14d3f7",
        label="Essos Expanded startup family dispatcher",
    )
    assert_source_block_hash(
        family_effects,
        "essos_give_family_effect",
        "465c1415a8987439f6ce4d1ca9009710793299f5b2bf30301f6b5d34915e8345",
        label="Essos Expanded family effect",
    )
    assert_source_block_hash(
        agot_remove_realms,
        "agot_remove_realm_effect",
        "9168fb5f64500cb04f28a321ddec8c6f658cc459dca4cfb62c3217a361a67b3b",
        label="AGOT realm-removal effect",
    )
    assert_source_block_hash(
        lov_colonization,
        "make_settlement_county_wilderness",
        "4bac248019f401289eac2f39e1e10c5bcd7bd7142db32ef5744af82a9066580b",
        label="LoV wilderness conversion",
    )
    if on_action.count("essos_remove_realms = {") != 1:
        raise RuntimeError("Essos Expanded startup dispatcher changed")

    for realm in realms:
        rule = f"essos_empire_{realm}_disabled"
        root_title = f"title:e_{realm}"
        old_removal = f"agot_remove_realm_effect = {{ REALM = {root_title} }}"
        if game_rules.count(f"{rule} = {{") != 1:
            raise RuntimeError(f"Essos Expanded game rule changed: {rule}")
        if on_action.count(f"essos_remove_realm_{realm} = {{") != 1:
            raise RuntimeError(f"Essos Expanded removal action changed: {realm}")
        on_action = replace_exact(
            on_action,
            old_removal,
            (
                "agot_playset_make_disabled_essos_realm_wilderness = "
                f"{{ REALM = {root_title} }}"
            ),
            expected=1,
            label=f"Essos Expanded {realm} wilderness replacement",
        )

    on_action = replace_exact(
        on_action,
        "on_game_start = {\n\ton_actions = {\n\t\tessos_remove_realms\n"
        "\t\tessos_generate_families\n\t}\n}",
        "on_game_start = {\n\ton_actions = {\n\t\tessos_remove_realms\n\t}\n}\n"
        "\n# Families need final ruler capitals and LoV's wilderness state.\n"
        "on_game_start_after_lobby = {\n\ton_actions = {\n"
        "\t\tessos_generate_families\n\t}\n}",
        expected=1,
        label="Essos Expanded family-generation timing",
    )
    on_action = replace_exact(
        on_action,
        "# Each empire checks its game rule; if disabled, calls agot_remove_realm_effect.",
        "# Each empire checks its game rule; if disabled, initializes LoV wilderness.",
        expected=1,
        label="Essos Expanded direct-wilderness startup description",
    )
    on_action = replace_exact(
        on_action,
        "\t\t\t\tis_ruler = yes\n\t\t\t\tage >= 30",
        "\t\t\t\tis_ruler = yes\n\t\t\t\tis_landed = yes\n"
        "\t\t\t\texists = capital_province\n\t\t\t\texists = top_liege\n"
        "\t\t\t\tage >= 30",
        expected=1,
        label="Essos Expanded family-ruler location guards",
    )

    for descendant in ("essos_child_1", "essos_child_2", "essos_child_3"):
        family_effects = replace_exact(
            family_effects,
            f"LOCATION  = scope:{descendant}",
            "LOCATION  = scope:essos_gen_char",
            expected=1,
            label=f"Essos family {descendant} location",
        )
    family_block = extract_top_level_block(family_effects, "essos_give_family_effect")
    family_open = family_block.index("{")
    guarded_family_block = (
        "essos_give_family_effect = {\n"
        "\t# The dispatcher filters this too; the AGOT helper dereferences\n"
        "\t# $LOCATION$.location, so direct callers must satisfy this invariant.\n"
        "\tif = {\n\t\tlimit = {\n\t\t\tis_landed = yes\n"
        "\t\t\texists = capital_province\n\t\t}\n"
        + textwrap.indent(family_block[family_open + 1 : -1].strip(), "\t\t")
        + "\n\t}\n}"
    )
    family_effects = replace_exact(
        family_effects,
        family_block,
        guarded_family_block,
        expected=1,
        label="Essos family location guard wrapper",
    )

    effect_text = textwrap.dedent(
        """\
        # Disabled Essos realms must not be staged through AGOT's c_unknown or
        # Local_Rulers. Preserve AGOT's removal semantics while converting every
        # county through the effective LoV wilderness operation.
        agot_playset_make_disabled_essos_realm_wilderness = {
        \t$REALM$ = {
        \t\tsave_scope_as = agot_playset_disabled_essos_realm
        \t\t# Remove noble-family titles before the landed hierarchy disappears.
        \t\tevery_in_de_jure_hierarchy = {
        \t\t\tlimit = { exists = holder tier >= tier_duchy }
        \t\t\tholder = {
        \t\t\t\tevery_held_title = {
        \t\t\t\t\tlimit = { is_noble_family_title = yes }
        \t\t\t\t\tholder = {
        \t\t\t\t\t\tif = {
        \t\t\t\t\t\t\tlimit = { is_landed = no }
        \t\t\t\t\t\t\tevery_courtier_or_guest = {
        \t\t\t\t\t\t\t\tdeath = { death_reason = death_vanished }
        \t\t\t\t\t\t\t}
        \t\t\t\t\t\t}
        \t\t\t\t\t\tdestroy_title = prev
        \t\t\t\t\t}
        \t\t\t\t}
        \t\t\t\tevery_vassal = {
        \t\t\t\t\tevery_held_title = {
        \t\t\t\t\t\tlimit = { is_noble_family_title = yes }
        \t\t\t\t\t\tholder = {
        \t\t\t\t\t\t\tif = {
        \t\t\t\t\t\t\t\tlimit = { is_landed = no }
        \t\t\t\t\t\t\t\tevery_courtier_or_guest = {
        \t\t\t\t\t\t\t\t\tdeath = { death_reason = death_vanished }
        \t\t\t\t\t\t\t\t}
        \t\t\t\t\t\t\t}
        \t\t\t\t\t\t\tdestroy_title = prev
        \t\t\t\t\t\t}
        \t\t\t\t\t}
        \t\t\t\t}
        \t\t\t}
        \t\t}
        \t\t# Remove de-jure duchy-and-higher titles before county conversion.
        \t\tevery_in_de_jure_hierarchy = {
        \t\t\tlimit = { exists = holder tier >= tier_duchy }
        \t\t\tholder = { destroy_title = prev }
        \t\t}
        \t\t# Clean landless companies whose capital remains inside this realm.
        \t\tevery_ruler = {
        \t\t\tlimit = {
        \t\t\t\tOR = {
        \t\t\t\t\tis_landless_adventurer = yes
        \t\t\t\t\tprimary_title = { is_mercenary_company = yes }
        \t\t\t\t}
        \t\t\t\texists = capital_province
        \t\t\t\tcapital_province.county = {
        \t\t\t\t\tscope:agot_playset_disabled_essos_realm = {
        \t\t\t\t\t\tis_de_jure_liege_or_above_target = prev
        \t\t\t\t\t}
        \t\t\t\t}
        \t\t\t}
        \t\t\tevery_courtier_or_guest = {
        \t\t\t\tdeath = { death_reason = death_vanished }
        \t\t\t}
        \t\t\tdestroy_title = primary_title
        \t\t\tdeath = { death_reason = death_vanished }
        \t\t}
        \t\tevery_in_de_jure_hierarchy = {
        \t\t\tlimit = { tier = tier_county }
        \t\t\tevery_county_province = {
        \t\t\t\tagot_remove_realms_remove_special_buildings_effect = yes
        \t\t\t\tsave_scope_as = agot_playset_disabled_essos_pool_province
        \t\t\t\tevery_pool_character = {
        \t\t\t\t\tprovince = scope:agot_playset_disabled_essos_pool_province
        \t\t\t\t\tdeath = { death_reason = death_vanished }
        \t\t\t\t}
        \t\t\t}
        \t\t\tif = {
        \t\t\t\tlimit = { exists = holder }
        \t\t\t\tholder = {
        \t\t\t\t\tsave_scope_as = agot_playset_disabled_essos_old_holder
        \t\t\t\t\tevery_courtier_or_guest = {
        \t\t\t\t\t\tdeath = { death_reason = death_vanished }
        \t\t\t\t\t}
        \t\t\t\t}
        \t\t\t\tmake_settlement_county_wilderness = { COUNTY = this }
        \t\t\t\tscope:agot_playset_disabled_essos_old_holder = {
        \t\t\t\t\tif = {
        \t\t\t\t\t\tlimit = { is_ruler = no }
        \t\t\t\t\t\tdeath = { death_reason = death_vanished }
        \t\t\t\t\t}
        \t\t\t\t}
        \t\t\t}
        \t\t\telse = {
        \t\t\t\tmake_settlement_county_wilderness = { COUNTY = this }
        \t\t\t}
        \t\t}
        \t\t# The de-jure iterator excludes the root empire title itself.
        \t\tif = {
        \t\t\tlimit = { exists = holder }
        \t\t\tholder = {
        \t\t\t\tdestroy_title = prev
        \t\t\t\tif = {
        \t\t\t\t\tlimit = { is_ruler = no }
        \t\t\t\t\tdeath = { death_reason = death_vanished }
        \t\t\t\t}
        \t\t\t}
        \t\t}
        \t}
        }
        """
    )
    write_text(
        OUTPUT,
        "common/on_action/essos_game_start.txt",
        normalize_rebased_source(on_action),
    )
    write_text(
        OUTPUT,
        "common/scripted_effects/essos_family_effects.txt",
        normalize_rebased_source(family_effects),
    )
    write_text(
        OUTPUT,
        "common/scripted_effects/zz_essos_disabled_realm_cleanup_effect.txt",
        effect_text,
    )
    for relative in (
        "common/decisions/zz_agot_playset_essos_migration_decision.txt",
        "common/scripted_triggers/zz_agot_playset_essos_migration_triggers.txt",
        "events/zz_agot_playset_essos_migration_events.txt",
        "localization/english/agot_playset_runtime_fixes_l_english.yml",
    ):
        (OUTPUT / relative).unlink(missing_ok=True)
    (OUTPUT / "common/on_action/zz_essos_disabled_realm_cleanup.txt").unlink(
        missing_ok=True
    )


def generate_nomad_yurt_guards() -> None:
    """Keep title-gain yurt setup within current vanilla building laws."""
    relative = "common/on_action/title_on_actions.txt"
    source = read_text(WORKSHOP / "3719888822" / relative)

    def yurt_main_block(external_count: int) -> str:
        external = (
            "\n".join(
                "\t\t\t\t\tadd_random_yurt_external_building_effect = yes"
                for _ in range(external_count)
            )
            + "\n"
            + "\n".join(
                "\t\t\t\t\tupgrade_random_yurt_external_building_effect = yes"
                for _ in range(external_count)
            )
        )
        return textwrap.indent(
            (
                "\t\t\t\ttitle_domicile = {\n"
                "\t\t\t\t\tif = {\n"
                "\t\t\t\t\t\tlimit = {\n"
                "\t\t\t\t\t\t\tNOT = { has_domicile_building = yurt_main_02 }\n"
                "\t\t\t\t\t\t}\n"
                "\t\t\t\t\t\tadd_domicile_building = yurt_main_02\n"
                "\t\t\t\t\t}\n"
                "\t\t\t\t\tif = {\n"
                "\t\t\t\t\t\tlimit = {\n"
                "\t\t\t\t\t\t\thas_domicile_building = yurt_main_02\n"
                "\t\t\t\t\t\t\towner ?= {\n"
                "\t\t\t\t\t\t\t\tOR = {\n"
                "\t\t\t\t\t\t\t\t\thas_realm_law = nomadic_authority_2\n"
                "\t\t\t\t\t\t\t\t\thas_realm_law = nomadic_authority_3\n"
                "\t\t\t\t\t\t\t\t\thas_realm_law = nomadic_authority_4\n"
                "\t\t\t\t\t\t\t\t\thas_realm_law = nomadic_authority_5\n"
                "\t\t\t\t\t\t\t\t}\n"
                "\t\t\t\t\t\t\t}\n"
                "\t\t\t\t\t\t\tNOT = { has_domicile_building = yurt_main_03 }\n"
                "\t\t\t\t\t\t}\n"
                "\t\t\t\t\t\tadd_domicile_building = yurt_main_03\n"
                "\t\t\t\t\t}\n"
                "\t\t\t\t\tif = {\n"
                "\t\t\t\t\t\tlimit = {\n"
                "\t\t\t\t\t\t\thas_domicile_building = yurt_main_03\n"
                "\t\t\t\t\t\t\towner ?= {\n"
                "\t\t\t\t\t\t\t\tOR = {\n"
                "\t\t\t\t\t\t\t\t\thas_realm_law = nomadic_authority_3\n"
                "\t\t\t\t\t\t\t\t\thas_realm_law = nomadic_authority_4\n"
                "\t\t\t\t\t\t\t\t\thas_realm_law = nomadic_authority_5\n"
                "\t\t\t\t\t\t\t\t}\n"
                "\t\t\t\t\t\t\t}\n"
                "\t\t\t\t\t\t\tNOT = { has_domicile_building = yurt_main_04 }\n"
                "\t\t\t\t\t\t}\n"
                "\t\t\t\t\t\tadd_domicile_building = yurt_main_04\n"
                "\t\t\t\t\t}\n"
                f"{external}\n"
                "\t\t\t\t}"
            ),
            "\t\t\t",
        )

    old_1300 = (
        "\t\t\t\ttitle_domicile = {\n"
        "\t\t\t\t\tadd_domicile_building = yurt_main_02\n"
        "\t\t\t\t\tadd_domicile_building = yurt_main_03\n"
        "\t\t\t\t\tadd_domicile_building = yurt_main_04\n"
        "\t\t\t\t\tadd_random_yurt_external_building_effect = yes\n"
        "\t\t\t\t\tadd_random_yurt_external_building_effect = yes\n"
        "\t\t\t\t\tadd_random_yurt_external_building_effect = yes\n"
        "\t\t\t\t\tadd_random_yurt_external_building_effect = yes\n"
        "\t\t\t\t\tupgrade_random_yurt_external_building_effect = yes\n"
        "\t\t\t\t\tupgrade_random_yurt_external_building_effect = yes\n"
        "\t\t\t\t\tupgrade_random_yurt_external_building_effect = yes\n"
        "\t\t\t\t\tupgrade_random_yurt_external_building_effect = yes\n"
        "\t\t\t\t}"
    )
    old_1300 = textwrap.indent(old_1300, "\t\t\t")
    old_1200 = (
        "\t\t\t\ttitle_domicile = {\n"
        "\t\t\t\t\tadd_domicile_building = yurt_main_02\n"
        "\t\t\t\t\tadd_domicile_building = yurt_main_03\n"
        "\t\t\t\t\tadd_domicile_building = yurt_main_04\n"
        "\t\t\t\t\tadd_random_yurt_external_building_effect = yes\n"
        "\t\t\t\t\tadd_random_yurt_external_building_effect = yes\n"
        "\t\t\t\t\tadd_random_yurt_external_building_effect = yes\n"
        "\t\t\t\t\tupgrade_random_yurt_external_building_effect = yes\n"
        "\t\t\t\t\tupgrade_random_yurt_external_building_effect = yes\n"
        "\t\t\t\t\tupgrade_random_yurt_external_building_effect = yes\n"
        "\t\t\t\t}"
    )
    old_1200 = textwrap.indent(old_1200, "\t\t\t")
    source = replace_exact(
        source,
        old_1300,
        yurt_main_block(4),
        expected=1,
        label="LoV nomad 1300 yurt setup",
    )
    source = replace_exact(
        source,
        old_1200,
        yurt_main_block(3),
        expected=1,
        label="LoV nomad 1200 yurt setup",
    )

    old_1100 = (
        "\t\t\t\ttitle_domicile = {\n"
        "\t\t\t\t\tadd_domicile_building = yurt_main_02\n"
        "\t\t\t\t\tif = {\n"
        "\t\t\t\t\t\tlimit = {\n"
        "\t\t\t\t\t\t\thas_domicile_building = yurt_main_02\n"
        "\t\t\t\t\t\t\towner ?= {\n"
        "\t\t\t\t\t\t\t\tOR = {\n"
        "\t\t\t\t\t\t\t\t\thas_realm_law = nomadic_authority_2\n"
        "\t\t\t\t\t\t\t\t\thas_realm_law = nomadic_authority_3\n"
        "\t\t\t\t\t\t\t\t\thas_realm_law = nomadic_authority_4\n"
        "\t\t\t\t\t\t\t\t\thas_realm_law = nomadic_authority_5\n"
        "\t\t\t\t\t\t\t\t}\n"
        "\t\t\t\t\t\t\t}\n"
        "\t\t\t\t\t\t}\n"
        "\t\t\t\t\t\tadd_domicile_building = yurt_main_03\n"
        "\t\t\t\t\t}\n"
        "\t\t\t\t\tadd_random_yurt_external_building_effect = yes\n"
        "\t\t\t\t\tadd_random_yurt_external_building_effect = yes\n"
        "\t\t\t\t\tupgrade_random_yurt_external_building_effect = yes\n"
        "\t\t\t\t\tupgrade_random_yurt_external_building_effect = yes\n"
        "\t\t\t\t}"
    )
    new_1100 = old_1100.replace(
        "\t\t\t\t\tadd_domicile_building = yurt_main_02\n",
        "\t\t\t\t\tif = {\n"
        "\t\t\t\t\t\tlimit = { NOT = { has_domicile_building = yurt_main_02 } }\n"
        "\t\t\t\t\t\tadd_domicile_building = yurt_main_02\n"
        "\t\t\t\t\t}\n",
        1,
    )
    new_1100 = new_1100.replace(
        "\t\t\t\t\t\t\t}\n"
        "\t\t\t\t\t\t}\n"
        "\t\t\t\t\t\tadd_domicile_building = yurt_main_03\n",
        "\t\t\t\t\t\t\t}\n"
        "\t\t\t\t\t\t\tNOT = { has_domicile_building = yurt_main_03 }\n"
        "\t\t\t\t\t\t}\n"
        "\t\t\t\t\t\tadd_domicile_building = yurt_main_03\n",
        1,
    )
    old_1100 = textwrap.indent(old_1100, "\t\t\t")
    new_1100 = textwrap.indent(new_1100, "\t\t\t")
    source = replace_exact(
        source,
        old_1100,
        new_1100,
        expected=1,
        label="LoV nomad 1100 yurt setup",
    )
    old_900 = (
        "\t\t\t\ttitle_domicile = {\n"
        "\t\t\t\t\tadd_domicile_building = yurt_main_02\n"
        "\t\t\t\t\tadd_random_yurt_external_building_effect = yes\n"
        "\t\t\t\t\tupgrade_random_yurt_external_building_effect = yes\n"
        "\t\t\t\t}"
    )
    new_900 = old_900.replace(
        "\t\t\t\t\tadd_domicile_building = yurt_main_02\n",
        "\t\t\t\t\tif = {\n"
        "\t\t\t\t\t\tlimit = { NOT = { has_domicile_building = yurt_main_02 } }\n"
        "\t\t\t\t\t\tadd_domicile_building = yurt_main_02\n"
        "\t\t\t\t\t}\n",
        1,
    )
    old_900 = textwrap.indent(old_900, "\t\t\t")
    new_900 = textwrap.indent(new_900, "\t\t\t")
    source = replace_exact(
        source,
        old_900,
        new_900,
        expected=1,
        label="LoV nomad 900 yurt setup",
    )
    write_text(OUTPUT, relative, source)


def generate_pirate_succession_guards() -> None:
    """Keep pirate elective law on titles that satisfy its duchy floor."""
    on_action_relative = "common/on_action/agot_on_actions/agot_title_on_actions.txt"
    on_action = read_text(WORKSHOP / "3719888822" / on_action_relative)
    block = extract_top_level_block(on_action, "agot_on_title_gain")
    repaired_block = replace_exact(
        block,
        "\t\t\t\t\ttier >= tier_county\n",
        "\t\t\t\t\ttier >= tier_duchy\n",
        expected=1,
        label="LoV pirate title-gain law floor",
    )
    repaired_block = replace_exact(
        repaired_block,
        "\t\t\t\t\tscope:title = {\n"
        "\t\t\t\t\t\tNOT = { var:current_house = root.house }\n"
        "\t\t\t\t\t\tNOT = { var:legitimate_house = root.house }\n"
        "\t\t\t\t\t}",
        "\t\t\t\t\tscope:title = {\n"
        "\t\t\t\t\t\texists = var:current_house\n"
        "\t\t\t\t\t\texists = var:legitimate_house\n"
        "\t\t\t\t\t\tNOT = { var:current_house = root.house }\n"
        "\t\t\t\t\t\tNOT = { var:legitimate_house = root.house }\n"
        "\t\t\t\t\t}",
        expected=1,
        label="AGOT title-gain legitimate-house guard",
    )
    repaired_block = replace_exact(
        repaired_block,
        "\t\t\t\t\t\tvar:current_house = root.house\n",
        "\t\t\t\t\t\texists = var:current_house\n"
        "\t\t\t\t\t\tvar:current_house = root.house\n",
        expected=1,
        label="AGOT title-gain current-house guard",
    )
    on_action = on_action.replace(block, repaired_block, 1)
    write_text(OUTPUT, on_action_relative, on_action)

    effect_relative = (
        "common/scripted_effects/zz_lv_agot_pirate_succession_reconciliation_rc69.txt"
    )
    effect = read_text(WORKSHOP / "3719888822" / effect_relative)
    effect = replace_exact(
        effect,
        "\t\t\ttier >= tier_county\n",
        "\t\t\ttier >= tier_duchy\n",
        expected=1,
        label="LoV pirate reconciliation law floor",
    )
    write_text(OUTPUT, effect_relative, effect)


def generate_faction_legitimate_house_guards() -> None:
    """Guard AGOT claimant-faction legitimate-house comparisons."""
    relative = "common/scripted_modifiers/00_faction_modifiers.txt"
    source = read_text(WORKSHOP / "2962333032" / relative)
    source = replace_exact(
        source,
        "\t\t$FACTION_TITLE$ = {\n"
        "\t\t\ttitle_uses_legitimate_house_mechanic = yes\n"
        "\t\t\tNOT = { var:legitimate_house = $FACTION_TARGET$.house } # Not held by the legitimate house\n"
        "\t\t}",
        "\t\t$FACTION_TITLE$ = {\n"
        "\t\t\ttitle_uses_legitimate_house_mechanic = yes\n"
        "\t\t\ttitle_is_not_held_by_legitimate_house = yes\n"
        "\t\t}",
        expected=1,
        label="AGOT claimant faction illegitimate-house guard",
    )
    source = replace_exact(
        source,
        "\t\t$FACTION_TITLE$ = {\n"
        "\t\t\ttitle_uses_legitimate_house_mechanic = yes\n"
        "\t\t\tvar:legitimate_house = $FACTION_TARGET$.house # The title is held by the legitimate house\n"
        "\t\t}",
        "\t\t$FACTION_TITLE$ = {\n"
        "\t\t\ttitle_uses_legitimate_house_mechanic = yes\n"
        "\t\t\ttitle_is_held_by_legitimate_house = yes\n"
        "\t\t}",
        expected=1,
        label="AGOT claimant faction legitimate-house guard",
    )
    write_text(OUTPUT, relative, source)


def generate_dragon_wives_legitimate_house_guards() -> None:
    """Use AGOT's guarded legitimate-house trigger in Dragon Wives modifiers."""
    relative = "common/scripted_modifiers/00_marriage_scripted_modifiers.txt"
    source = read_text(WORKSHOP / "3541596590" / relative)
    source = replace_exact(
        source,
        "\t\t\tNOT = { var:legitimate_house = var:current_house }\n",
        "\t\t\ttitle_is_not_held_by_legitimate_house = yes\n",
        expected=2,
        label="Dragon Wives legitimate-house comparison",
    )
    write_text(OUTPUT, relative, source)


def generate_court_events_3020_role_guard() -> None:
    """Remove optional-scope syntax unsupported by court-scene roles."""
    relative = "events/court_events/01_ep3_court_events_3.txt"
    source = read_text(WORKSHOP / "2962333032" / relative)
    event = extract_top_level_block(source, "court_events.3020")
    physician_role = (
        "\t\t\tscope:physician ?= {\n"
        "\t\t\t\tgroup = event_group\n"
        "\t\t\t\tanimation = physician\n"
        "\t\t\t}\n"
    )
    repaired_event = replace_exact(
        event,
        physician_role,
        "",
        expected=1,
        label="AGOT court_events.3020 physician role",
    )
    source = replace_exact(
        source,
        event,
        repaired_event,
        expected=1,
        label="AGOT court event 3020 in-place replacement",
    )
    if "namespace = court_events" not in source:
        raise RuntimeError("AGOT court events source lost its namespace during rebase")
    if "court_events.3000 = {" not in source:
        raise RuntimeError(
            "AGOT court events source lost sibling event court_events.3000"
        )
    source = normalize_rebased_source(source)
    write_text(
        OUTPUT,
        relative,
        "# Runtime rebase: court scene roles require an existing scope.\n\n" + source,
    )


def generate_aurion_title_gain_guard() -> None:
    """Disable LoV's obsolete title-gain recovery fallback.

    Aurion's recovery event is already attached to travel-plan movement and
    arrival in the LoV base on-actions.  The later RC61 title-gain fallback
    tests every gained county for the expedition building, then attempts to
    grant unique titles to whichever holder happens to gain that county.  The
    latter is the source of repeated title-holder collision errors in normal
    title transfers, so retain its registration but make the fallback inert.
    """
    relative = "common/on_action/cob_on_actions/zz_lv_aurion_lost_expedition_title_gain_rc61.txt"
    source = read_text(WORKSHOP / "3719888822" / relative)
    handler = extract_top_level_block(
        source, "lv_aurion_lost_expedition_recovery_on_title_gain"
    )
    replacement = (
        "lv_aurion_lost_expedition_recovery_on_title_gain = {\n"
        "    # RC61's title-gain fallback runs in the wrong scope. Recovery\n"
        "    # remains owned by LoV's travel movement/arrival on-actions.\n"
        "    trigger = { always = no }\n"
        "    effect = { }\n"
        "}"
    )
    source = source.replace(handler, replacement, 1)
    write_text(OUTPUT, relative, source)


def generate_cow_province_setup_rebase() -> None:
    """Repair COW's stale startup scopes and current AGOT identifiers."""
    relative = "common/on_action/cowagot_province_on_actions.txt"
    source = read_text(WORKSHOP / "2971198450" / relative)
    lordsport_change = (
        "\t\t\ttitle:b_lordsport = {\n"
        "\t\t\t\tchange_title_holder = {\n"
        "\t\t\t\t  holder = scope:lordsport_holder\n"
        "\t\t\t\t  change = scope:change\n"
        "\t\t\t  }\n"
        "\t\t\t}\n"
    )
    source = replace_exact(
        source,
        lordsport_change,
        "",
        expected=1,
        label="COW Lordsport undefined title-change scope",
    )
    source = replace_exact(
        source,
        "\t\t\t\tadd_building = common_trade_03\n",
        "\t\t\t\tadd_building = common_tradeport_03\n",
        expected=1,
        label="COW stale trade-port building",
    )
    source = replace_exact(
        source,
        "\t\t\t\tremove_building = ironwood_01\n",
        "\t\t\t\tremove_building = agot_ironwood_01\n",
        expected=1,
        label="COW stale ironwood building",
    )
    source = replace_exact(
        source,
        "\t\t\ttitle:b_graced_castle.title_province = {\n"
        "\t\t\t\tadd_building = castle_05\n"
        "\t\t\t}\n\n",
        "",
        expected=1,
        label="COW removed Graced Castle barony",
    )
    source = replace_exact(
        source,
        "title:b_cheesemonger_manse.title_province",
        "title:b_cheesemongers_manse.title_province",
        expected=1,
        label="COW stale Cheesemonger barony",
    )
    source = replace_exact(
        source,
        "\t\t\t\tadd_special_building_slot = bearisland_01\n",
        "\t\t\t\tadd_special_building_slot = agot_rodriks_gift_01\n",
        expected=1,
        label="COW stale Bear Island building slot",
    )
    source = replace_exact(
        source,
        "\t\t\t\tadd_special_building = bearisland_01\n",
        "\t\t\t\tadd_special_building = agot_rodriks_gift_01\n",
        expected=1,
        label="COW stale Bear Island building",
    )
    source = replace_exact(
        source,
        "\t\t\tadd_special_building_slot = harlaw_mines_01\n",
        "\t\t\tadd_building = agot_iron_island_mines_01\n",
        expected=1,
        label="COW stale Harlaw mines building",
    )
    write_text(
        OUTPUT,
        relative,
        "# Runtime rebase: remove the dead title-change scope and rebase COW's\n"
        "# stale building/barony identifiers onto current AGOT definitions.\n" + source,
    )


def generate_upgrade_house_banners_event() -> None:
    """Restore the localized close option omitted from the visible event."""
    relative = "events/uhb_court_maintenance.txt"
    text = read_text(WORKSHOP / "3709868073" / relative)
    event = extract_top_level_block(text, "uhb_court_maintenance.0001")
    if "\n\toption = {" in event:
        raise RuntimeError(
            "Upgrade House Banners maintenance event now supplies an option"
        )
    if "hidden = yes" in event:
        raise RuntimeError("Upgrade House Banners maintenance event is now hidden")
    localization = read_text(
        WORKSHOP
        / "3709868073/localization/english/uhb_court_events_altner_l_english.yml"
    )
    if localization.count("uhb_court_maintenance.0001.a:") != 1:
        raise RuntimeError(
            "Upgrade House Banners maintenance-event option localization changed"
        )
    repaired = (
        f"{event[:-1]}\n"
        "\toption = {\n"
        "\t\tname = uhb_court_maintenance.0001.a\n"
        "\t}\n"
        "}"
    )
    text = text.replace(event, repaired, 1)
    write_text(
        OUTPUT,
        relative,
        text,
        preserve_trailing_whitespace=True,
    )


def extract_top_level_block(text: str, key: str) -> str:
    match = re.search(rf"(?m)^{re.escape(key)}\s*=\s*\{{", text)
    if not match:
        raise RuntimeError(f"top-level block not found: {key}")
    depth = 0
    in_string = False
    escaped = False
    in_comment = False
    for index in range(match.start(), len(text)):
        char = text[index]
        if in_comment:
            if char == "\n":
                in_comment = False
            continue
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == "#":
            in_comment = True
        elif char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[match.start() : index + 1]
    raise RuntimeError(f"unbalanced top-level block: {key}")


def guard_scene_culture_triggers(
    text: str,
    *,
    expected: int,
    label: str,
) -> str:
    """Return scene-culture definitions guarded against a missing court owner."""
    keys = re.findall(
        r"(?m)^([A-Za-z0-9_]+)\s*=\s*\{",
        text,
    )
    if len(keys) != expected:
        raise RuntimeError(
            f"{label}: expected {expected} scene culture(s), found {len(keys)}"
        )

    marker = "\ttrigger = {\n"
    suffix = "\t}\n}"
    for key in keys:
        block = extract_top_level_block(text, key)
        marker_index = block.find(marker)
        if marker_index < 0 or not block.endswith(suffix):
            raise RuntimeError(f"{label}: unexpected trigger structure for {key}")
        body_start = marker_index + len(marker)
        body_end = len(block) - len(suffix)
        body = block[body_start:body_end]
        indented_body = "".join(
            f"\t{line}" if line.strip() else line
            for line in body.splitlines(keepends=True)
        )
        guarded = (
            f"{block[:body_start]}"
            "\t\t# Scene selection is briefly queried without a valid court "
            "owner during cleanup.\n"
            "\t\ttrigger_if = {\n"
            "\t\t\tlimit = { exists = root }\n"
            f"{indented_body}"
            "\t\t}\n"
            "\t\ttrigger_else = { always = no }\n"
            "\t}\n"
            "}"
        )
        text = text.replace(block, guarded, 1)
    return text


def rebase_additional_models_scene_guards(text: str) -> str:
    """Carry current Additional Models exclusions into the later LoV compatch."""
    relative = "gfx/court_scene/scene_cultures/00_default_cultures.txt"
    additional_models = read_text(WORKSHOP / "3319354609" / relative)
    for key in ("indian", "japanese", "southeast_asia"):
        current_block = extract_top_level_block(additional_models, key)
        compatch_block = extract_top_level_block(text, key)
        if current_block.count("amsb_has_throne_room = no") != 1:
            raise RuntimeError(
                f"Additional Models current scene guard changed for {key}"
            )
        amsb_guard_count = compatch_block.count("amsb_has_throne_room = no")
        if amsb_guard_count > 1:
            raise RuntimeError(
                f"Additional Models/AGOT+/LoV compatch duplicates its AMSB "
                f"guard for {key}"
            )
        if amsb_guard_count == 0:
            guarded_block = replace_exact(
                compatch_block,
                "\t\tagot_has_throne_room = no\n",
                ("\t\tagot_has_throne_room = no\n\t\tamsb_has_throne_room = no\n"),
                expected=1,
                label=f"Additional Models 0.4.40 scene exclusion for {key}",
            )
        else:
            # Newer upstream compatches can carry this exclusion themselves.
            # Preserve that authoritative guard instead of duplicating it.
            guarded_block = compatch_block
        text = text.replace(compatch_block, guarded_block, 1)
    if text.count("amsb_has_throne_room = no") != 10:
        raise RuntimeError(
            "Additional Models/AGOT+/LoV generic scenes: expected ten "
            "active AMSB exclusions after rebase"
        )
    return text


def generate_scene_culture_owner_guards() -> None:
    sources = (
        (
            "3762892081",
            "gfx/court_scene/scene_cultures/00_default_cultures.txt",
            11,
            "Additional Models/AGOT+/LoV generic court scenes",
        ),
        (
            "2962333032",
            "gfx/court_scene/scene_cultures/agot_default_cultures.txt",
            19,
            "AGOT named court scenes",
        ),
    )
    for workshop_id, relative, expected, label in sources:
        text = read_text(WORKSHOP / workshop_id / relative)
        if workshop_id == "3762892081":
            text = rebase_additional_models_scene_guards(text)
        text = guard_scene_culture_triggers(
            text,
            expected=expected,
            label=label,
        )
        write_text(OUTPUT, relative, text)


def generate_now_summerhall_candidate_guards() -> None:
    relative = "events/agot_events/agot_summerhall_events.txt"
    text = read_text(WORKSHOP / "3664900993" / relative)
    for candidate, expected in ((1, 23), (2, 13), (3, 3)):
        text = replace_exact(
            text,
            f"NOT = {{ this = scope:candidate_{candidate} }}",
            f"NOT = {{ scope:candidate_{candidate} ?= this }}",
            expected=expected,
            label=f"NOW Summerhall optional candidate {candidate} comparisons",
        )
    write_text(NOW_OUTPUT, relative, text)


def generate_now_core_rebase() -> None:
    """Regenerate NOW's non-event whole-file runtime repairs."""
    relative = "common/landed_titles/replace/03_agot_landed_titles_westeros_titular.txt"
    text = read_text(WORKSHOP / "3664900993" / relative)
    text = replace_exact(
        text,
        "capital = c_great_for\n",
        "capital = c_great_fork\n",
        expected=1,
        label="NOW dummy Great Fork title capital",
    )
    write_text(NOW_OUTPUT, relative, normalize_rebased_source(text))

    relative = "common/on_action/agot_now_on_actions.txt"
    text = read_text(WORKSHOP / "3664900993" / relative)
    text = replace_regex(
        text,
        r"(?m)^([ \t]*)agot_now_apply_command_governments_on_action(?=\n[ \t]*\}\n\})",
        r"\1agot_now_apply_command_governments_on_game_start",
        expected=1,
        label="NOW game-start command-government dispatcher",
    )
    text = replace_exact(
        text,
        "                duration = -1\n",
        "",
        expected=7,
        label="NOW permanent population-modifier durations",
    )
    game_start_effect = """agot_now_apply_command_governments_on_game_start = {
\teffect = {
\t\tif = {
\t\t\tlimit = { exists = title:b_oldtown.holder }
\t\t\ttitle:b_oldtown.holder = { change_government = command_government }
\t\t}
\t\tif = {
\t\t\tlimit = { exists = title:c_moongates.holder }
\t\t\ttitle:c_moongates.holder = { change_government = command_government }
\t\t}
\t\tif = {
\t\t\tlimit = { exists = title:c_the_bloody_gate.holder }
\t\t\ttitle:c_the_bloody_gate.holder = { change_government = command_government }
\t\t}
\t}
}

"""
    text = replace_exact(
        text,
        "# ON DEATH\n",
        game_start_effect + "# ON DEATH\n",
        expected=1,
        label="NOW scoped game-start command-government effect insertion",
    )
    text = replace_exact(
        text,
        "change = scope:great_fork_change",
        "change = scope:blackwater_change",
        expected=1,
        label="NOW Great Fork title-change scope",
    )
    text = replace_exact(
        text,
        "set_government = command_government",
        "change_government = command_government",
        expected=1,
        label="NOW command-government effect",
    )
    text = replace_exact(
        text,
        "set_de_jure_liege = title:e_the_crownlands",
        "set_de_jure_liege_title = title:e_the_crownlands",
        expected=1,
        label="NOW Blackwater de-jure liege effect",
    )
    write_text(NOW_OUTPUT, relative, normalize_rebased_source(text))

    relative = "events/agot_events/replace/agot_coa_events.txt"
    text = read_text(WORKSHOP / "3664900993" / relative)
    text = replace_exact(
        text,
        "agot_coa_events.0003 = {",
        "namespace = agot_coa_events\n\nagot_coa_events.0003 = {",
        expected=1,
        label="NOW personal-COA event namespace",
    )
    write_text(NOW_OUTPUT, relative, text)


def generate_mfa_delayed_pulse_scopes() -> None:
    prefix = "common/on_action/activities"
    fractional_random_lists = {
        "MFA_agot_coronation_on_actions.txt": (1, 1),
        "MFA_coronation_on_actions.txt": (1, 10),
        "MFA_pilgrimage_on_actions.txt": (1, 3),
        "MFA_tournament_on_actions.txt": (1, 4),
        "MFA_wedding_on_actions.txt": (1, 1),
    }
    province_scope_counts = {
        "MFA_adult_education_on_actions.txt": 19,
        "MFA_agot_coronation_on_actions.txt": 46,
        "MFA_chariot_race_on_actions.txt": 14,
        "MFA_coronation_on_actions.txt": 92,
        "MFA_feast_on_actions.txt": 53,
        "MFA_festival_on_actions.txt": 13,
        "MFA_funeral_on_actions.txt": 45,
        "MFA_gruesome_festival_on_actions.txt": 21,
        "MFA_hunt_on_actions.txt": 4,
        "MFA_pilgrimage_on_actions.txt": 28,
        "MFA_playdate_on_actions.txt": 24,
        "MFA_tour_on_actions.txt": 39,
        "MFA_tournament_on_actions.txt": 37,
        "MFA_wedding_on_actions.txt": 59,
        "MFA_witch_ritual_on_actions.txt": 10,
        "converted_pulse_actions/MFA_agot_coronation_pulse_actions.txt": 10,
        "converted_pulse_actions/MFA_chariot_race_pulse_actions.txt": 2,
        "converted_pulse_actions/MFA_coronation_pulse_actions.txt": 12,
        "converted_pulse_actions/MFA_education_pulse_actions.txt": 1,
        "converted_pulse_actions/MFA_feast_oltner_pulse_actions.txt": 29,
        "converted_pulse_actions/MFA_feast_pulse_actions.txt": 26,
        "converted_pulse_actions/MFA_general_pulse_actions.txt": 4,
        "converted_pulse_actions/MFA_pilgrimage_pulse_actions.txt": 17,
        "converted_pulse_actions/MFA_playdate_pulse_actions.txt": 26,
        "converted_pulse_actions/MFA_tour_pulse_actions.txt": 12,
        "converted_pulse_actions/MFA_tournament_pulse_actions.txt": 22,
        "converted_pulse_actions/MFA_wedding_pulse_actions.txt": 22,
        "converted_pulse_actions/MFA_witch_ritual_pulse_actions.txt": 8,
    }
    for filename, expected in province_scope_counts.items():
        relative = f"{prefix}/{filename}"
        text = read_text(WORKSHOP / "3723597729" / relative)
        if filename == "MFA_playdate_on_actions.txt":
            text = replace_exact(
                text,
                """			limit = {
				var:MFA_phase_0_remaining >= 1
				scope:activity = { is_current_phase_active = yes }
""",
                """			limit = {
				var:MFA_phase_0_remaining >= 1
				exists = scope:activity
				scope:activity = { is_current_phase_active = yes }
""",
                expected=1,
                label="MFA delayed playdate activity-scope guard",
            )
        text = replace_exact(
            text,
            "scope:province",
            "scope:activity.activity_location",
            expected=expected,
            label=f"MFA delayed pulse activity locations in {filename}",
        )
        if filename == "MFA_hunt_on_actions.txt":
            text = replace_exact(
                text,
                "multiply = hunt_success_chance_roco_amenity_level_value",
                (
                    "multiply = scope:activity."
                    "hunt_success_chance_roco_amenity_level_value"
                ),
                expected=1,
                label="MFA delayed hunt success activity value",
            )
            text = replace_exact(
                text,
                "root.activity_host",
                "scope:activity.activity_host",
                expected=6,
                label="MFA delayed hunt activity-host scopes",
            )
            text = replace_exact(
                text,
                "is_participant_in_activity = root",
                "is_participant_in_activity = scope:activity",
                expected=1,
                label="MFA delayed hunt participant activity scope",
            )
        if filename in fractional_random_lists:
            expected_lists, expected_weights = fractional_random_lists[filename]
            text = scale_fractional_random_list_weights(
                text,
                expected_lists=expected_lists,
                expected_fractional_weights=expected_weights,
                label=f"MFA random-list weights in {filename}",
            )
        write_text(MFA_OUTPUT, relative, text)


def generate_grand_remembrance_agot_obituary() -> None:
    relative = "common/on_action/gr_on_actions.txt"
    text = read_text(WORKSHOP / "3678529052" / relative)
    rice_revalidation = "# RICE COMPATIBILITY REVALIDATION"
    npc_obituary = "# NPC Obituary Processing"
    section_k = "\t\t\t\t# SECTION K: FAME / EVENT TRAITS"
    section_l = "\t\t\t\t# SECTION L: HEALTH & INFAMY"
    section_m2b = "\t\t\t\t# SECTION M2b: ELECTIVE SUCCESSION DETECTION"
    section_m3 = "\t\t\t\t# SECTION M3: SUCCESSION CRISIS MOD DETECTION"
    for marker in (
        rice_revalidation,
        npc_obituary,
        section_k,
        section_l,
        section_m2b,
        section_m3,
    ):
        if text.count(marker) != 1:
            raise RuntimeError(
                "Grand Remembrance obituary rebase: expected one marker "
                f"{marker.strip()!r}, found {text.count(marker)}"
            )

    start = text.index(rice_revalidation)
    end = text.index(npc_obituary)
    text = (
        text[:start]
        + (
            "# RICE COMPATIBILITY: disabled for this AGOT playset\n"
            "# The RICE-only placeholder faith cannot be queried safely when "
            "RICE is absent.\n\n"
        )
        + text[end:]
    )

    start = text.index(section_k)
    end = text.index(section_l)
    text = (
        text[:start]
        + (
            "\t\t\t\t# SECTION K: AGOT compatibility\n"
            "\t\t\t\t# Vanilla/RICE fame traits and vanilla religion/"
            "heritage crossings are\n"
            "\t\t\t\t# unavailable in AGOT. Its compatibility submod "
            "supplies AGOT obituary data.\n"
            "\t\t\t\t\n"
        )
        + text[end:]
    )

    start = text.index(section_m2b)
    end = text.index(section_m3)
    text = (
        text[:start]
        + (
            "\t\t\t\t# SECTION M2b: AGOT compatibility\n"
            "\t\t\t\t# Vanilla elective title laws are removed by AGOT; "
            "skip this flavor classifier.\n"
            "\t\t\t\t\n"
        )
        + text[end:]
    )
    text = replace_exact(
        text,
        (
            "\t\t\t\tif = { limit = { root = { has_trait = "
            "born_in_the_purple } } set_variable = { name = "
            "gr_dynasty_purple value = yes } }\n"
        ),
        ("\t\t\t\t# AGOT removes the vanilla born_in_the_purple trait.\n"),
        expected=1,
        label="Grand Remembrance AGOT born-in-the-purple classifier",
    )
    write_text(GR_OUTPUT, relative, text)

    relative = "common/scripted_effects/gr_npc_obituary_data_effect.txt"
    text = read_text(WORKSHOP / "3678529052" / relative)
    text = replace_exact(
        text,
        """		# Player's opinion of the dead NPC. opinion:X targets a saved event
		# scope by its bare name (no "scope:" prefix — gotcha #9), and it
		# is evaluated relative to the CURRENT scope, so this must run with
		# scope:gr_iter_player (the player) as the acting scope.
		scope:gr_iter_player = {
			save_temporary_scope_as = gr_opinion_holder
		}
		scope:dead_npc = {
			set_variable = { name = gr_opinion value = scope:gr_opinion_holder.opinion:dead_npc }
		}""",
        """		# Capture the player's opinion while both character scopes are valid.
		# save_temporary_opinion_value_as is the CK3 1.19 interface for
		# materializing an opinion as a numeric temporary scope.
		scope:gr_iter_player = {
			save_temporary_opinion_value_as = {
				name = gr_opinion_of_dead_npc
				target = scope:dead_npc
			}
			scope:dead_npc = {
				set_variable = {
					name = gr_opinion
					value = scope:gr_opinion_of_dead_npc
				}
			}
		}""",
        expected=1,
        label="Grand Remembrance NPC obituary opinion value",
    )
    section_k = "\t\t# SECTION K: FAME / EVENT TRAITS"
    section_l = "\t\t# SECTION L: HEALTH & INFAMY"
    section_n = "\t\t# SECTION N: LEGACY SCORE CALCULATION"
    elective = "\t\t\t# Elective"
    for marker in (section_k, section_l, elective, section_n):
        if text.count(marker) != 1:
            raise RuntimeError(
                "Grand Remembrance NPC obituary rebase: expected one marker "
                f"{marker.strip()!r}, found {text.count(marker)}"
            )

    start = text.index(section_k)
    end = text.index(section_l)
    text = (
        text[:start]
        + (
            "\t\t# SECTION K: AGOT compatibility\n"
            "\t\t# Vanilla/RICE fame classifiers are unavailable in AGOT; "
            "the AGOT\n"
            "\t\t# compatibility submod supplies its setting-specific "
            "obituary data.\n"
            "\t\t\n"
        )
        + text[end:]
    )
    text = replace_exact(
        text,
        (
            "\t\t\tif = { limit = { has_trait = born_in_the_purple } "
            "set_variable = { name = gr_dynasty_purple value = yes } }\n"
        ),
        "\t\t\t# AGOT removes the vanilla born_in_the_purple trait.\n",
        expected=1,
        label="Grand Remembrance NPC born-in-the-purple classifier",
    )

    start = text.index(elective)
    scope_end = text.index("\n\t\t}\n", start)
    section_n_start = text.index(section_n)
    if scope_end >= section_n_start:
        raise RuntimeError(
            "Grand Remembrance NPC elective classifier did not end before Section N"
        )
    text = (
        text[:start]
        + (
            "\t\t\t# AGOT removes the vanilla elective title laws; skip "
            "this flavor classifier.\n"
        )
        + text[scope_end:]
    )
    write_text(GR_OUTPUT, relative, text)


def generate_landed_knights() -> None:
    relative = "common/on_action/on_add_vet_modifer.txt"
    text = read_text(WORKSHOP / "3361162762" / relative)
    text = replace_exact(
        text,
        """                    NOT = {
                        father = { is_army_owner = root.army_owner }
                    }""",
        """                    # Optional comparison avoids switching through a
                    # missing father and replaces the nonexistent
                    # is_army_owner trigger used by the Workshop source.
                    NOT = { father ?= root.side_primary_participant }""",
        expected=1,
        label="A Landed Knights Mod father/army-owner guard",
    )
    write_text(OUTPUT, relative, text)


def generate_expanded_court_position_hire_events() -> None:
    relative = "events/lunarac_00_hire_events.txt"
    text = read_text(WORKSHOP / "3676293022" / relative)
    text = unwrap_unconditional_random_pool_ifs(
        text,
        expected=12,
        label="Expanded Court Position middle-candidate pools",
    )
    text = replace_exact(
        text,
        "grumpy =",
        "irritable =",
        expected=8,
        label="Expanded Court Position grumpy stress impacts",
    )
    text = replace_exact(
        text,
        "depressed = major_stress_impact_loss",
        (
            "depressed_1 = major_stress_impact_loss "
            "depressed_genetic = major_stress_impact_loss"
        ),
        expected=4,
        label="Expanded Court Position depression stress impacts",
    )
    text = replace_exact(
        text,
        "merciful =",
        "compassionate =",
        expected=1,
        label="Expanded Court Position merciful stress impact",
    )
    write_text(OUTPUT, relative, text)


def generate_legitimacy_over_time_ai() -> None:
    relative = "events/lot_ai_events.txt"
    text = read_text(WORKSHOP / "3305687550" / relative)
    text = replace_exact(
        text,
        """                trigger = {
                    OR = {""",
        """                trigger = {
                    # The yearly story-cycle event can outlive the vassal
                    # selected by the scripted effect.
                    scope:recipient ?= { is_alive = yes }
                    OR = {""",
        expected=1,
        label="Legitimacy Over Time sway-recipient guard",
    )
    write_text(OUTPUT, relative, text)


def generate_red_keep_castellan_guard() -> None:
    relative = "events/red_keep_title_events.txt"
    text = read_text(WORKSHOP / "3662281614" / relative)
    event = extract_top_level_block(text, "rk_nw.0002")
    repaired_event = replace_exact(
        event,
        """	immediate = {	
		cp:councillor_castellan = {
			save_scope_as = rk_hand
		}
	}	""",
        """	immediate = {
		if = {
			limit = { exists = cp:councillor_castellan }
			cp:councillor_castellan = {
				save_scope_as = rk_hand
			}
		}
	}""",
        expected=1,
        label="The Red Keep optional castellan scope",
    )
    text = replace_exact(
        text,
        event,
        repaired_event,
        expected=1,
        label="The Red Keep journey event",
    )
    write_text(OUTPUT, relative, text)


def generate_automated_squire_training_events() -> None:
    relative = "events/agot_events/agot_squirehood_ongoing_events.txt"
    text = read_text(WORKSHOP / "3674548216" / relative)
    event = extract_top_level_block(text, "agot_squirehood_ongoing.0018")
    repaired_event = replace_exact(
        event,
        "right_portrait = scope:second_squire",
        "right_portrait = scope:my_knight",
        expected=1,
        label="AGOT squire downtime portrait scope",
    )
    text = replace_exact(
        text,
        event,
        repaired_event,
        expected=1,
        label="AGOT squire downtime event",
    )
    text = replace_regex(
        text,
        (
            r"(?m)^([ \t]*)desc = "
            r"(agot_squirehood_ongoing\.0400\.had_a_training_session"
            r"\.desc\.[A-Za-z.]+)[ \t]*$"
        ),
        r"\1text = \2",
        expected=5,
        label="Automated Squire Training interface-message tooltips",
    )
    text = replace_exact(
        text,
        """			ai_chance = {
				base = 115
			}
""",
        "",
        expected=1,
        label="Automated Squire Training nested AI chance",
    )
    write_text(OUTPUT, relative, text)


def generate_knighting_ceremony_event() -> None:
    relative = "events/zz_agot_squire_automation_events.txt"
    text = read_text(WORKSHOP / "3673468355" / relative)
    text = replace_exact(
        text,
        "\tis_triggered_only = yes\n",
        "",
        expected=1,
        label="Knighting Ceremony obsolete event field",
    )
    write_text(OUTPUT, relative, text)


def generate_house_founders() -> None:
    relative = "common/character_interactions/00_agot_hf_revealbastards.txt"
    text = read_text(WORKSHOP / "2967263410" / relative)
    text = replace_exact(
        text,
        "\t\t\t\tprimary_title = {",
        "\t\t\t\tprimary_title ?= {",
        expected=2,
        label="House Founders optional primary-title guards",
    )
    text = replace_exact(
        text,
        "\t\tscope:recipient.top_liege = {",
        "\t\tscope:recipient.top_liege ?= {",
        expected=2,
        label="House Founders optional top-liege guards",
    )
    write_text(OUTPUT, relative, text)


def generate_artifact_manager_distribution_event() -> None:
    relative = "events/distribute_artifacts.txt"
    text = read_text(WORKSHOP / "2886417277" / relative)
    text = replace_exact(
        text,
        "small_stress_impact_loss",
        "minor_stress_impact_loss",
        expected=2,
        label="Artifact Manager current stress-impact values",
    )
    text = replace_exact(
        text,
        "highlight_portrait = r_dyny",
        "highlight_portrait = scope:r_dyny",
        expected=1,
        label="Artifact Manager family portrait scope",
    )
    write_text(OUTPUT, relative, text)


def generate_additional_models_decision_illustrations() -> None:
    missing = "gfx/interface/illustrations/agot_court/throne.dds"
    fallback = (
        "gfx/interface/illustrations/event_scenes/ironthrone/throneroom_ironthrone.dds"
    )
    sources = {
        "common/decisions/amsb_bent_knees_decision.txt": 1,
        "common/decisions/amsb_abdicate_decision.txt": 2,
    }
    if not (WORKSHOP / "2962333032" / fallback).is_file():
        raise RuntimeError(
            "Additional Models decision illustration fallback is absent "
            "from current AGOT"
        )
    if (WORKSHOP / "3319354609" / missing).exists():
        raise RuntimeError(
            "Additional Models now supplies its throne illustration; "
            "remove the local fallback rebase"
        )
    for relative, expected in sources.items():
        text = read_text(WORKSHOP / "3319354609" / relative)
        text = replace_exact(
            text,
            missing,
            fallback,
            expected=expected,
            label=f"Additional Models decision illustration in {relative}",
        )
        write_text(OUTPUT, relative, text)


def generate_succession_crisis() -> None:
    relative = "events/sc_power_consolidation_event.txt"
    text = read_text(WORKSHOP / "3713902872" / relative)
    text = replace_exact(
        text,
        "NOT = { this = scope:crisis_special_character }",
        "NOT = { scope:crisis_special_character ?= this }",
        expected=1,
        label="Succession Crisis event optional special-character comparison",
    )
    write_text(OUTPUT, relative, text)

    relative = "common/casus_belli_types/succession_crisis_cb.txt"
    text = read_text(WORKSHOP / "3713902872" / relative)
    assert_source_block_hash(
        text,
        "succession_crisis_cb",
        "251ae06b03e802a3f496f7fb4015a165df73c3bbf468834a4b90c36c3ec970b6",
        label="Succession Crisis casus belli",
    )
    text = replace_exact(
        text,
        "scope:war = {",
        "scope:war ?= {",
        expected=5,
        label="Succession Crisis optional war scopes",
    )
    write_text(OUTPUT, relative, normalize_rebased_source(text))


def generate_more_interactive_vassals_war_join_guards() -> None:
    """Refuse MIV war joins that conflict with any current participant."""
    relative = "events/interactive_events/interactive_events.txt"
    text = read_text(WORKSHOP / "2712590542" / relative)
    assert_source_block_hash(
        text,
        "interactive.0007",
        "9135f5b9aac37842b6e71281041130606bb9a348786e7b4fe6bccb90ad236ddb",
        label="More Interactive Vassals interactive.0007",
    )
    for joiner in ("scope:vassal", "scope:vassals_vassal"):
        pattern = (
            r"(?m)^(?P<indent>\t+)limit = \{\n"
            r"(?P=indent)\tprimary_attacker = \{\n"
            r"(?P=indent)\t\tNOT = \{\n"
            rf"(?P=indent)\t\t\tis_at_war_with = {re.escape(joiner)}\n"
            r"(?P=indent)\t\t\}\n"
            r"(?P=indent)\t\}\n"
            r"(?P=indent)\tprimary_defender = \{\n"
            r"(?P=indent)\t\tNOT = \{\n"
            rf"(?P=indent)\t\t\tis_at_war_with = {re.escape(joiner)}\n"
            r"(?P=indent)\t\t\}\n"
            r"(?P=indent)\t\}\n"
            r"(?P=indent)\}"
        )
        replacement = (
            "\\g<indent>limit = {\n"
            f"\\g<indent>\tNOT = {{ any_war_participant = {{ this = {joiner} }} }}\n"
            f"\\g<indent>\tNOT = {{\n"
            f"\\g<indent>\t\tany_war_participant = {{\n"
            f"\\g<indent>\t\t\tis_at_war_with = {joiner}\n"
            f"\\g<indent>\t\t}}\n"
            f"\\g<indent>\t}}\n"
            "\\g<indent>}"
        )
        text = replace_regex(
            text,
            pattern,
            replacement,
            expected=2,
            label=f"MIV all-participant war guard for {joiner}",
        )
    text = replace_exact(
        text,
        "vassal_contract_has_flag = has_warden_contract",
        "always = no # CK3 1.19 has no has_warden_contract definition",
        expected=3,
        label="MIV unavailable warden-contract branches",
    )
    write_text(OUTPUT, relative, normalize_rebased_source(text))


def generate_agot_war_value_guards() -> None:
    """Make AGOT's house-relation AI score tolerate house-less participants."""
    relative = "common/script_values/00_war_values.txt"
    source = read_text(WORKSHOP / "2962333032" / relative)
    assert_source_block_hash(
        source,
        "house_relation_ai_score_value",
        "5725a0fe1abb147a729742c45c6b164499cc519bff31eb3711cfe87754edce5d",
        label="AGOT house-relation AI score",
    )
    repaired = """house_relation_ai_score_value = {
\tvalue = 0
\tif = {
\t\tlimit = {
\t\t\texists = scope:attacker.house
\t\t\texists = scope:defender.house
\t\t}
\t\tscope:attacker.house = {
\t\t\tif = {
\t\t\t\tlimit = {
\t\t\t\t\tscope:defender.house = {
\t\t\t\t\t\tNOT = { this = scope:attacker.house }
\t\t\t\t\t\thas_house_relation_with = scope:attacker.house
\t\t\t\t\t}
\t\t\t\t}
\t\t\t\tevery_house_relation = {
\t\t\t\t\tlimit = {
\t\t\t\t\t\tany_relation_house = { this = scope:defender.house }
\t\t\t\t\t}
\t\t\t\t\tif = {
\t\t\t\t\t\tlimit = { has_house_relation_parameter = less_likely_war_target }
\t\t\t\t\t\tadd = house_relation_less_likely_war_target_value
\t\t\t\t\t}
\t\t\t\t\telse_if = {
\t\t\t\t\t\tlimit = { has_house_relation_parameter = more_likely_war_target }
\t\t\t\t\t\tadd = house_relation_more_likely_war_target_value
\t\t\t\t\t}
\t\t\t\t}
\t\t\t}
\t\t}
\t}
}
"""
    write_text(
        OUTPUT,
        "common/script_values/zz_agot_playset_war_value_guards.txt",
        repaired,
    )

    relative = "common/scripted_effects/sc_create_landless_adventurer_title_effect.txt"
    text = read_text(WORKSHOP / "3713902872" / relative)
    text = replace_exact(
        text,
        "\t\ttrigger_event = { id = misc.0001 days = 1 }\n",
        (
            "\t\t# AGOT disables misc.0001 and removes this vanilla "
            "rags-to-riches call.\n"
        ),
        expected=1,
        label="Succession Crisis AGOT-disabled misc.0001 call",
    )
    text = replace_exact(
        text,
        """				trigger = {
					NOT = {
						scope:new_landless_adventurer.culture = culture:kurdish
					}
				}
""",
        """				# AGOT has no Kurdish culture, so keep this title-name option
				# available exactly as AGOT does in the parent effect.
""",
        expected=1,
        label="Succession Crisis AGOT-disabled Kurdish culture gate",
    )
    write_text(OUTPUT, relative, text)

    relative = "common/on_action/sc_power_consolidation.txt"
    text = read_text(WORKSHOP / "3713902872" / relative)
    text = replace_exact(
        text,
        "NOT = { this = scope:crisis_special_character }",
        "NOT = { scope:crisis_special_character ?= this }",
        expected=1,
        label="Succession Crisis on-action optional comparisons",
    )
    write_text(OUTPUT, relative, text)


def generate_artifact_manager_scripted_guis() -> None:
    relative = "common/scripted_guis/am_status_events.txt"
    text = read_text(WORKSHOP / "2886417277" / relative)
    text = replace_exact(
        text,
        """AM_combine_artifacts_available = {
    AND = {
        has_game_rule = amx_direct_upgrade_artifacts_enabled
        employs_court_position = antiquarian_court_position
        court_position:antiquarian_court_position = { aptitude:antiquarian_court_position >= 4  }
    }
}

""",
        "",
        expected=1,
        label="Artifact Manager bare trigger in scripted-GUI file",
    )
    text = replace_exact(
        text,
        "	saved_scope = { target }",
        "	saved_scopes = { target }",
        expected=4,
        label="Artifact Manager scripted-GUI saved scopes",
    )
    text = replace_exact(
        text,
        "            AM_combine_artifacts_available = yes",
        """            has_game_rule = amx_direct_upgrade_artifacts_enabled
            employs_court_position = antiquarian_court_position
            court_position:antiquarian_court_position = {
                aptitude:antiquarian_court_position >= 4
            }""",
        expected=1,
        label="Artifact Manager direct-upgrade availability trigger",
    )
    text = replace_exact(
        text,
        "        global_var:exists = at_artifact_trade_loaded",
        "        exists = global_var:at_artifact_trade_loaded",
        expected=1,
        label="Artifact Manager optional integration variable",
    )
    unavailable_agot_modifiers = (
        *(f"artifact_prowess_{level}_modifier" for level in range(6, 11)),
        *(f"artifact_minor_prestige_{level}_modifier" for level in range(1, 8)),
        *(f"artifact_prestige_{level}_modifier" for level in range(1, 8)),
        *(f"artifact_monthly_merit_add_{level}_modifier" for level in range(1, 8)),
        *(f"artifact_montly_lifestyle_xp_{level}_modifier" for level in range(1, 4)),
        *(
            f"artifact_montly_{skill}_lifestyle_xp_{level}_modifier"
            for skill in (
                "diplomacy",
                "martial",
                "stewardship",
                "intrigue",
                "learning",
            )
            for level in range(1, 4)
        ),
        *(
            "artifact_study_confucian_classics_scheme_phase_duration_add_"
            f"{level}_modifier"
            for level in range(1, 4)
        ),
        *(
            f"artifact_monthly_confucian_education_xp_{level}_modifier"
            for level in range(1, 3)
        ),
    )
    if len(unavailable_agot_modifiers) != 49:
        raise RuntimeError(
            "Artifact Manager AGOT modifier filter: expected 49 identifiers, "
            f"constructed {len(unavailable_agot_modifiers)}"
        )
    for modifier in unavailable_agot_modifiers:
        text = replace_regex(
            text,
            rf"(?m)^[ \t]*has_artifact_modifier = {modifier}\n",
            "",
            expected=1,
            label=f"Artifact Manager unavailable AGOT modifier {modifier}",
        )
    write_text(OUTPUT, relative, text)


def generate_artifact_manager_upgrade_guis() -> None:
    relative = "common/scripted_guis/am_upgrade_ops.txt"
    text = read_text(WORKSHOP / "2886417277" / relative)
    text = replace_exact(
        text,
        "remove_variable = var:AM_upgrade_op_selected_artifact",
        "remove_variable = AM_upgrade_op_selected_artifact",
        expected=1,
        label="Artifact Manager selected-upgrade variable removal",
    )
    text = replace_exact(
        text,
        "remove_variable = var:AM_upgrade_op_gold_cost",
        "remove_variable = AM_upgrade_op_gold_cost",
        expected=1,
        label="Artifact Manager upgrade-cost variable removal",
    )
    text = replace_exact(
        text,
        "add_artifact_modifier = artifact_prowess_11_modifier",
        "add_artifact_modifier = artifact_prowess_5_modifier",
        expected=12,
        label="Artifact Manager AGOT maximum prowess modifier",
    )
    unavailable_upgrade_sources = (
        *(f"artifact_prowess_{level}_modifier" for level in range(6, 11)),
        *(f"artifact_monthly_merit_add_{level}_modifier" for level in range(1, 8)),
        *(
            "artifact_study_confucian_classics_scheme_phase_duration_add_"
            f"{level}_modifier"
            for level in range(1, 4)
        ),
        *(
            f"artifact_monthly_confucian_education_xp_{level}_modifier"
            for level in range(1, 3)
        ),
    )
    for modifier in unavailable_upgrade_sources:
        text = remove_if_block_for_artifact_modifier(
            text,
            modifier,
            label="Artifact Manager unavailable AGOT artifact upgrade",
        )
    write_text(OUTPUT, relative, text)

    relative = "common/scripted_guis/am_artifacts_batch_ops.txt"
    text = read_text(WORKSHOP / "2886417277" / relative)
    text = replace_exact(
        text,
        "scope:artifact",
        "scope:this_artifact",
        expected=4,
        label="Artifact Manager batch-sale saved artifact scope",
    )
    text = replace_exact(
        text,
        """                    faith = {
                        has_doctrine = tenet_aniconism
                    }""",
        """                    root = {
                        faith = {
                            has_doctrine = tenet_aniconism
                        }
                    }""",
        expected=2,
        label="Artifact Manager batch-sale owner faith scope",
    )
    for scripted_gui in (
        "AM_repair_all_artifacts",
        "AM_repair_selected_artifacts",
    ):
        block = extract_top_level_block(text, scripted_gui)
        repaired_block = replace_exact(
            block,
            "save_scope_as = this_artifact",
            "save_scope_as = this_artifact\n\t\t\tsave_scope_as = artifact",
            expected=1,
            label=(f"Artifact Manager {scripted_gui} repair-cost artifact scope"),
        )
        text = replace_exact(
            text,
            block,
            repaired_block,
            expected=1,
            label=f"Artifact Manager {scripted_gui} scripted GUI",
        )
    text = replace_exact(
        text,
        """            if = {
                exists = scope:gift_recipient
""",
        """            if = {
                limit = { exists = scope:gift_recipient }
""",
        expected=2,
        label="Artifact Manager optional giveaway recipient guard",
    )
    text = replace_exact(
        text,
        "                } else {",
        "                }\n                else = {",
        expected=1,
        label="Artifact Manager batch-combination else effect",
    )
    write_text(OUTPUT, relative, text)

    relative = "common/scripted_guis/distribute_artifacts.txt"
    text = read_text(WORKSHOP / "2886417277" / relative)
    text = replace_exact(
        text,
        "  saved_scope = {",
        "  saved_scopes = {",
        expected=1,
        label="Artifact Manager distribution saved scopes",
    )
    write_text(OUTPUT, relative, text)


def generate_advanced_character_search() -> None:
    relative = "common/scripted_triggers/gen_acs_st_big_switch.txt"
    text = read_text(WORKSHOP / "3084203091" / relative)
    unavailable_titles = (
        "e_minister_of_justice",
        "e_minister_of_rites",
        "e_minister_chancellor",
        "e_minister_of_personnel",
        "e_minister_of_revenue",
        "e_minister_of_works",
        "e_minister_grand_marshal",
        "e_minister_of_war",
        "e_minister_censor",
    )
    title_pattern = "|".join(map(re.escape, unavailable_titles))
    text = replace_regex(
        text,
        (
            rf"(?m)^[ \t]+NOT = \{{ has_title = "
            rf"title:(?:{title_pattern}) ?\}}\r?\n"
        ),
        "",
        expected=9,
        label="Advanced Character Search unavailable AGOT title exclusions",
    )
    text = replace_regex(
        text,
        rf"(?m)^[ \t]+has_title = title:(?:{title_pattern})\r?\n",
        "",
        expected=17,
        label="Advanced Character Search unavailable AGOT title alternatives",
    )
    text = replace_regex(
        text,
        (
            rf"(?m)^([ \t]*\d+ = \{{ )has_title = "
            rf"title:(?:{title_pattern})( \}}\r?)$"
        ),
        r"\1always = no\2",
        expected=5,
        label="Advanced Character Search AGOT-unavailable title filters",
    )
    text = replace_regex(
        text,
        (
            rf"(?m)^([ \t]*\d+ = \{{ )NOT = \{{ has_title = "
            rf"title:(?:{title_pattern}) \}}( \}}\r?)$"
        ),
        r"\1always = yes\2",
        expected=5,
        label="Advanced Character Search inverse AGOT title filters",
    )

    # CK3's generic search includes filters for database objects removed by
    # AGOT's total-conversion replace paths. Keep the generated switch indices
    # stable so the GUI's filter tags still line up, but make unavailable
    # positive filters false and their inverse filters true.
    unavailable_trait_filter_ids = (
        187,  # varangian
        207,  # born_in_the_purple
        209,  # augustus
        227,  # chakravarti
        258,  # hajjaj
        272,  # fp3_struggle_supporter
        274,  # fp3_struggle_detractor
        286,  # the_wake
        590,  # sayyid
        592,  # saoshyant
        594,  # saoshyant_descendant
        1137,  # despoiler_of_byzantium
    )
    for positive_id in unavailable_trait_filter_ids:
        text = replace_numbered_branch_with_constant(
            text,
            positive_id,
            False,
            label="Advanced Character Search unavailable AGOT trait",
        )
        text = replace_numbered_branch_with_constant(
            text,
            positive_id + 1,
            True,
            label="Advanced Character Search inverse unavailable AGOT trait",
        )

    for branch_id in range(3550, 3564):
        text = replace_numbered_branch_with_constant(
            text,
            branch_id,
            branch_id % 2 == 1,
            label=(
                "Advanced Character Search unavailable AGOT Confucian education trait"
            ),
        )

    for branch_id in range(966, 974):
        text = replace_numbered_branch_with_constant(
            text,
            branch_id,
            branch_id % 2 == 1,
            label="Advanced Character Search unavailable AGOT minister",
        )

    religion_marker = "variable = acs_vl_religion_filter"
    religion_start = text.index(religion_marker)
    religion_end = text.index(
        "\n                                8 = {",
        religion_start,
    )
    religion_prefix = text[:religion_start]
    religion_switch = text[religion_start:religion_end]
    religion_suffix = text[religion_end:]
    for branch_id, value in (
        (0, False),
        (1, True),
        (2, False),
        (3, True),
        (4, False),
        (5, True),
        (6, True),
        (7, False),
    ):
        religion_switch = replace_numbered_branch_with_constant(
            religion_switch,
            branch_id,
            value,
            label=("Advanced Character Search unavailable vanilla religion families"),
        )
    text = religion_prefix + religion_switch + religion_suffix

    text = replace_numbered_branch_with_constant(
        text,
        841,
        False,
        label="Advanced Character Search unavailable AGOT gunner accolade",
    )
    text = replace_numbered_branch_with_constant(
        text,
        842,
        True,
        label=("Advanced Character Search inverse unavailable AGOT gunner accolade"),
    )

    unavailable_alternatives = (
        "has_innovation = innovation_repeating_crossbow",
        "has_cultural_tradition = tradition_caucasian_wolves",
        "has_cultural_tradition = tradition_roman_legacy",
        "has_innovation = innovation_valets",
        "has_cultural_tradition = tradition_futuwaa",
        "has_cultural_tradition = tradition_druzhina",
        "has_cultural_tradition = tradition_khadga_puja",
        "has_cultural_tradition = tradition_garuda_warriors",
        "has_cultural_tradition = tradition_himalayan_settlers",
        "has_cultural_tradition = tradition_mubarizuns",
        "has_cultural_tradition = tradition_burman_royal_army",
        "has_cultural_tradition = tradition_mountaineer_ruralism",
        "has_innovation = innovation_sarawit",
        "has_innovation = innovation_legionnaires",
    )
    for unavailable in unavailable_alternatives:
        text = replace_regex(
            text,
            rf"(?m)^[ \t]*{re.escape(unavailable)}\r?\n",
            "",
            expected=2,
            label=(
                "Advanced Character Search unavailable AGOT accolade "
                f"alternative {unavailable}"
            ),
        )
    write_text(OUTPUT, relative, text)

    relative = "common/scripted_guis/acs_sg_main_scripted_gui.txt"
    text = read_text(WORKSHOP / "3084203091" / relative)
    init_block = extract_top_level_block(text, "acs_sg_init")
    effect_match = re.search(r"(?m)^    effect = \{", init_block)
    if effect_match is None:
        raise RuntimeError("Advanced Character Search initialization effect changed")
    effect_open = init_block.index("{", effect_match.start())
    effect_end = balanced_brace_end(init_block, effect_open)
    if init_block[effect_end + 1 :].strip() != "}":
        raise RuntimeError("Advanced Character Search initialization block changed")
    # Keep this effect in scripted-GUI context: it contains GUI list syntax
    # which is not valid in a normal scripted_effect definition. Move the
    # initializer from the pre-game widget hook to the guarded in-game window;
    # leaving two copies also duplicates CK3/Tiger's list registrations.
    initialization = textwrap.dedent(
        init_block[effect_open + 1 : effect_end].strip("\n")
    )
    initialization = replace_exact(
        initialization,
        """every_in_global_list = {
            list = acs_gvl_save_slot""",
        """every_in_global_list = {
            variable = acs_gvl_save_slot""",
        expected=1,
        label="Advanced Character Search global save-slot iteration",
    )
    initialization = textwrap.indent(initialization, "            ")
    text = text.replace(
        init_block,
        """acs_sg_init = {
    # Initialization moved to acs_window, which has a valid character root.
    effect = { }
}""",
        1,
    )
    window_block = extract_top_level_block(text, "acs_window")
    expected_window = (
        "acs_window = {\n"
        "    scope = character\n"
        "    \n"
        "    is_shown = { \n"
        "        NOT = { has_variable = is_acs_building_list }\n"
        "    }\n"
        "\n"
        "    effect = {\n"
        "        create_searched_character_list = yes\n"
        "    }\n"
        "}"
    )
    if window_block != expected_window:
        raise RuntimeError("Advanced Character Search main-window scripted GUI changed")
    guarded_window = f"""acs_window = {{
    scope = character

    is_shown = {{
        exists = root
        NOT = {{ has_variable = is_acs_building_list }}
    }}

    effect = {{
        if = {{
            limit = {{ exists = root }}
{initialization}
            create_searched_character_list = yes
        }}
    }}
}}"""
    text = text.replace(window_block, guarded_window, 1)
    write_text(OUTPUT, relative, text, force_newline="\r\n")

    relative = "gui/acs.gui"
    text = read_text(WORKSHOP / "3084203091" / relative)
    text = replace_exact(
        text,
        "    visible = \"[GetVariableSystem.Exists('acs_window_toggle')]\"",
        (
            '    visible = "[And( GetPlayer.IsValid, '
            "GetVariableSystem.Exists('acs_window_toggle') )]\""
        ),
        expected=1,
        label="Advanced Character Search invalid-player window guard",
    )
    write_text(OUTPUT, relative, text, force_newline="\r\n")


def generate_any_new_traditions() -> None:
    relative = "common/on_action/any_new_traditions_on_action.txt"
    text = read_text(WORKSHOP / "3241130652" / relative)
    text = replace_exact(
        text,
        "dynasty = { has_dynasty_modifier = ary_traditions_5_modifier }",
        "dynasty ?= { has_dynasty_modifier = ary_traditions_5_modifier }",
        expected=2,
        label="Any New Traditions optional dynasty scopes",
    )
    write_text(OUTPUT, relative, text)

    for filename in (
        "any_new_traditions_decisions.txt",
        "any_vanilla_traditions_decisions.txt",
    ):
        relative = f"common/decisions/{filename}"
        text = read_text(WORKSHOP / "3241130652" / relative)
        text = replace_exact(
            text,
            "\t\tOR - {",
            "\t\tOR = {",
            expected=1,
            label=f"Any New Traditions malformed OR in {filename}",
        )
        text = replace_exact(
            text,
            "add_dynasty_prestige >= 10000",
            "add_dynasty_prestige = 10000",
            expected=2,
            label=f"Any New Traditions prestige effect in {filename}",
        )
        write_text(OUTPUT, relative, text)


def generate_great_councils() -> None:
    relative = "events/zzz_Great_Councils_events.txt"
    text = read_text(WORKSHOP / "3621472324" / relative)
    text = replace_regex(
        text,
        r"(\bTRAIT\s*=\s*)([A-Za-z_][A-Za-z0-9_]*)",
        r"\1trait:\2",
        expected=56,
        label="AGOT Great Councils typed scripted-trigger trait parameters",
    )
    text = replace_exact(
        text,
        "has_trait = high_septon",
        "agot_is_high_septon = yes",
        expected=2,
        label="AGOT Great Councils current High Septon trigger",
    )
    write_text(OUTPUT, relative, text)


def generate_suggest_dragon_bonding() -> None:
    relative = (
        "common/character_interactions/00_agot_suggest_dragon_bonding_interaction.txt"
    )
    text = read_text(WORKSHOP / "3324579171" / relative)

    marker = "        # Check if the recipient meets all conditions"
    before, separator, after = text.partition(marker)
    if not separator:
        raise RuntimeError(
            "AGOT Suggest Dragon Bonding: recipient-condition marker missing"
        )
    before = replace_exact(
        before,
        """every_courtier = {
                                    limit = {
                                        has_trait = dragon
                                        is_alive = yes
                                        any_relation = {
                                            type = agot_dragon
                                            count = 0
                                        }
                                    }
                                }""",
        """any_courtier = {
                                    has_trait = dragon
                                    is_alive = yes
                                    any_relation = {
                                        type = agot_dragon
                                        count = 0
                                    }
                                }""",
        expected=1,
        label="Suggest Dragon Bonding trigger-context courtier iterator",
    )
    before = replace_exact(
        before,
        "every_vassal = {",
        "any_vassal = {",
        expected=10,
        label="Suggest Dragon Bonding trigger-context vassal iterators",
    )
    text = before + separator + after

    text = replace_exact(
        text,
        "            is_busy_in_events_localised = yes",
        "            is_available = yes",
        expected=1,
        label="Suggest Dragon Bonding current availability trigger",
    )
    text = replace_exact(
        text,
        """			target = actor
			value = scope:actor.diplomacy""",
        """			target = scope:actor
			value = diplomacy""",
        expected=1,
        label="Suggest Dragon Bonding diplomacy compare modifier",
    )
    text = replace_exact(
        text,
        """			add = intimidated_external_reason_value
            multiplier = 0.1""",
        """			add = {
				value = intimidated_external_reason_value
				multiply = 0.1
			}""",
        expected=1,
        label="Suggest Dragon Bonding intimidated-value scaling",
    )
    text = replace_exact(
        text,
        """			add = cowed_external_reason_value
            multiplier = 0.1""",
        """			add = {
				value = cowed_external_reason_value
				multiply = 0.1
			}""",
        expected=1,
        label="Suggest Dragon Bonding cowed-value scaling",
    )
    write_text(OUTPUT, relative, text)


def generate_agot_tour_events() -> None:
    relative = "events/activities/tour_activity/tour_phase_host_a_dinner.txt"
    text = read_text(WORKSHOP / "2962333032" / relative)
    text = replace_exact(
        text,
        """host_dinner_events.3050 = {
\ttype = activity_event
\ttitle = host_dinner_events.3050.title
\tdesc = host_dinner_events.3050.desc

\ttheme = host_dinner
\tleft_portrait = {
\t\tcharacter = root
\t\tanimation = rage
\t}
\tright_portrait = {
\t\tcharacter = scope:non_eater_scope
\t\tanimation = personality_zealous
\t}
\tcooldown = { years = 5 }
\ttrigger = {
\t\tinvolved_activity = {
\t\t\tany_attending_character = {
\t\t\t\tthis != scope:stop_host_scope
\t\t\t\tthis != scope:visiting_liege""",
        """host_dinner_events.3050 = {
\ttype = activity_event
\ttitle = host_dinner_events.3050.title
\tdesc = host_dinner_events.3050.desc

\ttheme = host_dinner
\tleft_portrait = {
\t\tcharacter = root
\t\tanimation = rage
\t}
\tright_portrait = {
\t\tcharacter = scope:non_eater_scope
\t\tanimation = personality_zealous
\t}
\tcooldown = { years = 5 }
\ttrigger = {
\t\texists = scope:stop_host_scope
\t\texists = scope:visiting_liege
\t\tinvolved_activity = {
\t\t\tany_attending_character = {
\t\t\t\tNOT = { scope:stop_host_scope ?= this }
\t\t\t\tNOT = { scope:visiting_liege ?= this }""",
        expected=1,
        label="AGOT host dinner 3050 saved-scope guard",
    )
    text = replace_exact(
        text,
        """host_dinner_events.3080 = {
\ttype = activity_event
\ttitle = host_dinner_events.3080.title
\tdesc = host_dinner_events.3080.desc

\ttheme = host_dinner
\tleft_portrait = {
\t\tcharacter = root
\t\tanimation = shock
\t}
\tright_portrait = {
\t\tcharacter = scope:choking_character_scope
\t\tanimation = sick
\t}
\t#cooldown = { years = 5 }

\ttrigger = {
\t\tlocation = {
\t\t\tany_character_in_location = {
\t\t\t\tis_available_ai_adult = yes
\t\t\t\tany_memory = {
\t\t\t\t\thas_memory_category = positive
\t\t\t\t}
\t\t\t\tthis != scope:stop_host_scope
\t\t\t\tthis != scope:visiting_liege""",
        """host_dinner_events.3080 = {
\ttype = activity_event
\ttitle = host_dinner_events.3080.title
\tdesc = host_dinner_events.3080.desc

\ttheme = host_dinner
\tleft_portrait = {
\t\tcharacter = root
\t\tanimation = shock
\t}
\tright_portrait = {
\t\tcharacter = scope:choking_character_scope
\t\tanimation = sick
\t}
\t#cooldown = { years = 5 }

\ttrigger = {
\t\texists = scope:stop_host_scope
\t\texists = scope:visiting_liege
\t\tlocation = {
\t\t\tany_character_in_location = {
\t\t\t\tis_available_ai_adult = yes
\t\t\t\tany_memory = {
\t\t\t\t\thas_memory_category = positive
\t\t\t\t}
\t\t\t\tNOT = { scope:stop_host_scope ?= this }
\t\t\t\tNOT = { scope:visiting_liege ?= this }""",
        expected=1,
        label="AGOT host dinner 3080 saved-scope guard",
    )
    write_text(OUTPUT, relative, text)

    relative = "events/activities/tour_activity/tour_general_events.txt"
    text = read_text(WORKSHOP / "3719888822" / relative)
    text = replace_exact(
        text,
        """	trigger = {
		is_available_travelling_adult = yes
		scope:stop_host_scope = { this != root }
		exists = scope:stop_host_scope
""",
        """	trigger = {
		exists = scope:stop_host_scope
		is_available_travelling_adult = yes
		scope:stop_host_scope = { this != root }
""",
        expected=1,
        label="LoV tour-general 3001 stop-host guard ordering",
    )
    write_text(OUTPUT, relative, text)

    relative = "events/activities/tour_activity/az_tour_events.txt"
    text = read_text(WORKSHOP / "2962333032" / relative)
    for event_id in ("az_tour.0002", "az_tour.0003", "az_tour.0004"):
        block = extract_top_level_block(text, event_id)
        guarded = replace_regex(
            block,
            (
                r"(?m)^    trigger = \{\n"
                r"(?=[ \t]*scope:stop_host_scope = \{)"
            ),
            ("    trigger = {\n        exists = scope:stop_host_scope\n"),
            expected=1,
            label=f"{event_id} stop-host trigger guard",
        )
        text = text.replace(block, guarded, 1)

    block = extract_top_level_block(text, "az_tour.0005")
    guarded = replace_exact(
        block,
        """    immediate = {
""",
        """    trigger = {
        exists = scope:stop_host_scope
    }

    immediate = {
""",
        expected=1,
        label="az_tour.0005 stop-host event gate",
    )
    text = text.replace(block, guarded, 1)
    write_text(OUTPUT, relative, text)


def generate_adventurers_beneficiary() -> None:
    relative = "common/character_interactions/adventurers_beneficiary_unselect.txt"
    text = read_text(WORKSHOP / "3349316031" / relative)
    text = replace_exact(
        text,
        """			NOT = { scope:recipient = scope:actor }
			scope:recipient = var:val_beneficiary""",
        """			NOT = { scope:recipient = scope:actor }
			has_variable = val_beneficiary
			scope:recipient = var:val_beneficiary""",
        expected=1,
        label="Adventurer's Beneficiary selected-character variable guard",
    )
    write_text(OUTPUT, relative, text)


def generate_all_men_must_serve() -> None:
    relative = "common/scripted_effects/00_ame_effects.txt"
    source = read_text(WORKSHOP / "3761342990" / relative)
    block = extract_top_level_block(source, "ame_charge_service_cost_effect")
    block = replace_exact(
        block,
        "add_gold = -75",
        "remove_short_term_gold = 75",
        expected=1,
        label="All Men Must Serve positive-value service-cost deduction",
    )
    write_text(
        OUTPUT,
        "common/scripted_effects/zz_ame_runtime_cost_effect.txt",
        (
            "# CK3 1.19 rejects negative add_gold values. Preserve the "
            "Workshop mod's 75-gold fee with the current deduction effect.\n"
            f"{block}\n"
        ),
    )


def generate_agot_artifact_succession() -> None:
    relative = "events/artifacts/artifact_events.txt"
    source = read_text(WORKSHOP / "2962333032" / relative)
    block = extract_top_level_block(source, "artifact.0031")
    repaired_block = replace_exact(
        block,
        """				var:artifact_succession_title = { is_title_created = yes } #Does the title the artifact should follow exist?
				scope:old_owner = var:artifact_succession_title.previous_holder #Is the old owner of the artifact also the holder of the title the artifact should follow?""",
        """				var:artifact_succession_title = { is_title_created = yes } #Does the title the artifact should follow exist?
				exists = var:artifact_succession_title.previous_holder
				scope:old_owner = var:artifact_succession_title.previous_holder #Is the old owner of the artifact also the holder of the title the artifact should follow?""",
        expected=1,
        label="AGOT artifact succession previous-holder guard",
    )
    source = replace_exact(
        source,
        block,
        repaired_block,
        expected=1,
        label="AGOT artifact succession in-place replacement",
    )
    source = normalize_rebased_source(source)
    (OUTPUT / "events/artifacts/zz_agot_runtime_artifact_events.txt").unlink(
        missing_ok=True
    )
    write_text(
        OUTPUT,
        relative,
        source,
    )


def generate_agot_artifact_feature_owner_guards() -> None:
    relative = "common/scripted_triggers/00_artifact_triggers.txt"
    source = read_text(WORKSHOP / "2962333032" / relative)
    trigger_names = (
        "artifact_feature_pattern_wolf_trigger",
        "artifact_feature_pattern_animals_trigger",
        "artifact_feature_pattern_local_animal_trigger",
        "artifact_feature_pattern_beasts_trigger",
        "artifact_feature_pattern_bird_trigger",
        "artifact_feature_pattern_war_god_trigger",
        "artifact_feature_pattern_religion_trigger",
        "artifact_feature_pattern_eschatology_trigger",
        "artifact_feature_pattern_religious_symbol_trigger",
        "artifact_feature_pattern_gibberish_trigger",
        "artifact_feature_pattern_culture_symbol_trigger",
        "artifact_feature_pattern_culture_style_trigger",
    )
    repaired_blocks: list[str] = []
    for trigger_name in trigger_names:
        block = extract_top_level_block(source, trigger_name)
        owner_match = re.search(r"(?m)^\tscope:owner\s*=\s*\{", block)
        if not owner_match:
            raise RuntimeError(f"{trigger_name}: expected direct owner-scope condition")
        owner_open = block.index("{", owner_match.start())
        owner_end = balanced_brace_end(block, owner_open)
        owner_block = block[owner_match.start() : owner_end + 1]
        indented_owner = "\n".join(f"\t{line}" for line in owner_block.splitlines())
        guarded_owner = (
            "\t# Artifact generation can evaluate feature triggers before an "
            "owner is assigned.\n"
            "\ttrigger_if = {\n"
            "\t\tlimit = { exists = scope:owner }\n"
            f"{indented_owner}\n"
            "\t}"
        )
        block = block[: owner_match.start()] + guarded_owner + block[owner_end + 1 :]
        repaired_blocks.append(block)

    write_text(
        OUTPUT,
        ("common/scripted_triggers/zz_agot_runtime_artifact_owner_triggers.txt"),
        (
            "# Current AGOT pattern triggers assume an artifact owner already "
            "exists.\n"
            "# These narrow later definitions preserve their logic while "
            "making that scope optional.\n\n" + "\n\n".join(repaired_blocks) + "\n"
        ),
    )


def generate_agot_wall_banner_capital_fallback() -> None:
    relative = "common/scripted_effects/01_ep1_court_artifact_creation_effects.txt"
    source = read_text(WORKSHOP / "2962333032" / relative)
    block = extract_top_level_block(source, "create_artifact_wall_banner_effect")
    block = replace_exact(
        block,
        """\t$OWNER$ = { save_scope_as = owner }
\t$CREATOR$ = { save_scope_as = creator }
\t$TARGET$ = { save_scope_as = target } #Can be a title, a house or a dynasty

\t#This effect can be used to generate banners""",
        """\t$OWNER$ = { save_scope_as = owner }
\t$CREATOR$ = { save_scope_as = creator }
\t$TARGET$ = { save_scope_as = target } #Can be a title, a house or a dynasty

\t# Startup banner history requires a capital province. If a malformed or
\t# titular royal-court owner has none, use the existing created-banner branch
\t# instead; it still creates and grants the banner without an invalid location.
\t$OWNER$ = {
\t\tif = {
\t\t\tlimit = {
\t\t\t\thas_variable = startup_banner
\t\t\t\tNOT = { exists = capital_province }
\t\t\t}
\t\t\tremove_variable = startup_banner
\t\t}
\t}

\t#This effect can be used to generate banners""",
        expected=1,
        label="AGOT wall-banner missing-capital startup fallback",
    )
    write_text(
        OUTPUT,
        "common/scripted_effects/zz_agot_runtime_wall_banner_effect.txt",
        f"{block}\n",
    )


def generate_deadly_ck3_health_location_guards() -> None:
    relative = "events/health_events.txt"
    source = read_text(WORKSHOP / "3445965581" / relative)
    block = extract_top_level_block(source, "health.7300")
    repaired_block = replace_exact(
        block,
        """\t\tmodifier = { # Glare
\t\t\tis_ruler = yes # For performance reasons we limit this as checking modifiers is expensive
\t\t\tlocation = {""",
        """\t\tmodifier = { # Glare
\t\t\tis_ruler = yes # For performance reasons we limit this as checking modifiers is expensive
\t\t\texists = location
\t\t\tlocation = {""",
        expected=1,
        label="Deadly CK3 AGOT clouded-eyes glare location guard",
    )
    repaired_block = replace_exact(
        repaired_block,
        """\t\tmodifier = { # Bright sunlight
\t\t\tlocation = {""",
        """\t\tmodifier = { # Bright sunlight
\t\t\texists = location
\t\t\tlocation = {""",
        expected=1,
        label="Deadly CK3 AGOT clouded-eyes sunlight location guard",
    )
    repaired_block = replace_exact(
        repaired_block,
        """\t\tmodifier = { # Shade
\t\t\tlocation = {""",
        """\t\tmodifier = { # Shade
\t\t\texists = location
\t\t\tlocation = {""",
        expected=1,
        label="Deadly CK3 AGOT clouded-eyes shade location guard",
    )
    source = replace_exact(
        source,
        block,
        repaired_block,
        expected=1,
        label="Deadly CK3 AGOT health event in-place replacement",
    )
    source = normalize_rebased_source(source)
    (OUTPUT / "events/zz_agot_runtime_health_events.txt").unlink(missing_ok=True)
    write_text(
        OUTPUT,
        relative,
        source,
    )


def generate_deadly_ck3_infirm_track() -> None:
    relative = "common/traits/dc_traits.txt"
    source = read_text(WORKSHOP / "3445965581" / relative)
    block = extract_top_level_block(source, "infirm")
    block = replace_exact(
        block,
        """\tflag = is_healthy_trigger_flag
}""",
        """\tflag = infirm_random_xp_gain
\tflag = age_related_ailment
\tflag = is_healthy_trigger_flag

\t# CK3 1.19 and AGOT grant XP to a named infirm track. Deadly CK3 already
\t# applies its full harsher penalties statically, so keep this compatibility
\t# track modifier-free rather than stacking AGOT's progressive penalties.
\ttracks = {
\t\tinfirm = {
\t\t\t100 = { }
\t\t}
\t}
}""",
        expected=1,
        label="Deadly CK3 AGOT current infirm trait track",
    )
    write_text(
        OUTPUT,
        "common/traits/zz_deadly_agot_runtime_infirm.txt",
        f"{block}\n",
    )


def generate_agot_citadel() -> None:
    relative = "common/scripted_effects/00_agot_citadel_effects.txt"
    source = read_text(WORKSHOP / "2962333032" / relative)
    block = extract_top_level_block(source, "agot_seed_maesters_effect")
    block = replace_exact(
        block,
        """		limit = {
			capital_county.title_province = { geographical_region = world_westeros_seven_kingdoms }""",
        """		limit = {
			exists = capital_county
			capital_county.title_province = { geographical_region = world_westeros_seven_kingdoms }""",
        expected=1,
        label="AGOT seed-maesters capital-county guard",
    )
    (OUTPUT / relative).unlink(missing_ok=True)
    write_text(
        OUTPUT,
        "common/scripted_effects/zz_agot_runtime_citadel_effects.txt",
        f"{block}\n",
    )


def generate_agot_starting_legitimacy() -> None:
    relative = (
        "common/on_action/agot_on_actions/agot_starting_legitimacy_on_actions.txt"
    )
    text = read_text(WORKSHOP / "2962333032" / relative)
    text = replace_exact(
        text,
        """					limit = {
						capital_province = { geographical_region = world_westeros_seven_kingdoms }""",
        """					limit = {
						exists = capital_province
						capital_province = { geographical_region = world_westeros_seven_kingdoms }""",
        expected=1,
        label="AGOT starting-legitimacy capital-province guard",
    )
    write_text(OUTPUT, relative, text)


def generate_vanilla_tour_pulse() -> None:
    relative = "common/scripted_effects/04_dlc_ep2_tour_effects.txt"
    source = read_text(game_root() / relative)
    block = extract_top_level_block(source, "tour_monthly_pulse_effect")
    marker = "\tscope:activity.var:stop_host = {"
    marker_index = block.find(marker)
    if marker_index < 0:
        raise RuntimeError("vanilla tour pulse: stop_host scope marker not found")
    if not block.endswith("\n}"):
        raise RuntimeError("vanilla tour pulse: unexpected block ending")
    head = block[:marker_index]
    guarded = block[marker_index:-2]
    indented = "".join(
        f"\t{line}" if line.strip() else line
        for line in guarded.splitlines(keepends=True)
    )
    block = (
        f"{head}\tif = {{\n"
        "\t\tlimit = { scope:activity = { exists = var:stop_host } }\n"
        f"{indented}\t}}\n"
        "}"
    )
    write_text(
        OUTPUT,
        "common/scripted_effects/zz_agot_runtime_tour_pulse_effect.txt",
        (
            "# Guard the vanilla tour pulse when MFA relays it before an "
            "itinerary stop exists.\n"
            f"{block}\n"
        ),
    )

    relative = "events/activities/tour_activity/tour_phase_cultural_festival.txt"
    text = read_text(WORKSHOP / "2962333032" / relative)
    text = replace_exact(
        text,
        """cultural_festival.4100 = { #Your courtier made a cultural faux pas
\ttype = activity_event
\ttitle = cultural_festival.4100.t
\tdesc = cultural_festival.4100.desc\t

\ttheme = cultural_festival

\tleft_portrait = {
\t\tcharacter = root
\t\tanimation = worry
\t}
\tright_portrait = {
\t\tcharacter = scope:offended_character_scope
\t\tanimation = shock
\t}
\tcenter_portrait = {
\t\tcharacter = scope:inconsiderate_character_scope
\t\tanimation = fear
\t}

\tcooldown = { years = 5 }

\ttrigger = {
\t\tOR = {""",
        """cultural_festival.4100 = { #Your courtier made a cultural faux pas
\ttype = activity_event
\ttitle = cultural_festival.4100.t
\tdesc = cultural_festival.4100.desc\t

\ttheme = cultural_festival

\tleft_portrait = {
\t\tcharacter = root
\t\tanimation = worry
\t}
\tright_portrait = {
\t\tcharacter = scope:offended_character_scope
\t\tanimation = shock
\t}
\tcenter_portrait = {
\t\tcharacter = scope:inconsiderate_character_scope
\t\tanimation = fear
\t}

\tcooldown = { years = 5 }

\ttrigger = {
\t\texists = scope:stop_host_scope
\t\texists = scope:visiting_liege
\t\tOR = {""",
        expected=1,
        label="AGOT cultural festival 4100 saved-scope gate",
    )
    text = replace_exact(
        text,
        "culture != scope:stop_host_scope.culture",
        "scope:stop_host_scope ?= { culture != prev.culture }",
        expected=1,
        label="AGOT cultural festival optional stop-host culture",
    )
    text = replace_exact(
        text,
        "culture != scope:visiting_liege.culture",
        "scope:visiting_liege ?= { culture != prev.culture }",
        expected=1,
        label="AGOT cultural festival optional visiting-liege culture",
    )
    write_text(OUTPUT, relative, text)


def generate_agot_plus() -> None:
    relative = "common/scripted_effects/asoiaf_canon_children_effects.txt"
    text = read_text(WORKSHOP / "2950245430" / relative)
    text = replace_regex(
        text,
        r"(?m)^\s*location = scope:mother\.location\r?\n",
        "",
        expected=202,
        label="AGOT+ redundant canon-child locations",
    )
    text = replace_exact(
        text,
        "character:Hammer_asoiaf_2",
        "character:asoiaf_Hammer_2",
        expected=1,
        label="AGOT+ Hugh Hammer daughter appearance source",
    )

    character_ids = history_character_ids("2962333032", "2950245430")
    appearance_pattern = re.compile(
        r"(copy_inheritable_appearance_from\s*=\s*character:)"
        r"([A-Za-z0-9]+)_asoiaf_([A-Za-z0-9_]+)"
    )
    remapped_appearances = 0

    def remap_appearance(match: re.Match[str]) -> str:
        nonlocal remapped_appearances
        original = f"{match.group(2)}_asoiaf_{match.group(3)}"
        if original in character_ids:
            return match.group(0)
        candidate = f"{match.group(2)}_{match.group(3)}"
        if candidate not in character_ids:
            return match.group(0)
        remapped_appearances += 1
        return f"{match.group(1)}{candidate}"

    text = appearance_pattern.sub(remap_appearance, text)
    if remapped_appearances != 77:
        raise RuntimeError(
            "AGOT+ current historical appearance sources: expected 77 "
            f"remaps, found {remapped_appearances}"
        )
    text = replace_regex(
        text,
        (
            r"(?m)^[ \t]*copy_inheritable_appearance_from = "
            r"character:Targaryen_asoiaf_(?:55_1|61_1)\r?\n"
        ),
        "",
        expected=2,
        label="AGOT+ missing stillborn-child appearance templates",
    )
    text = replace_exact(
        text,
        "character:Targaryen_61_1",
        "global_var:asoiaf_canon_children_Targaryen_61_1_born_variable",
        expected=4,
        label="AGOT+ runtime-created Aerion references",
    )
    text = replace_regex(
        text,
        r"(?m)^([ \t]*)trait = beauty_good_3$",
        r"\1add_trait = beauty_good_3",
        expected=1,
        label="AGOT+ Loras create-character trait effect",
    )
    text = replace_exact(
        text,
        "target = character:dragon_",
        "target_character = character:dragon_",
        expected=24,
        label="AGOT+ dragon bond scheme targets",
    )
    text = replace_exact(
        text,
        "NOT = { any_spouse.house ?= character:Targaryen_13.house }",
        ("NOT = { any_spouse = { house ?= character:Targaryen_13.house } }"),
        expected=1,
        label="AGOT+ spouse-house trigger iterator",
    )
    text = replace_exact(
        text,
        """dynasty:dynn_Targaryen = { #Aegon died
						every_dynasty_member = {""",
        """dynasty:dynn_Targaryen = { #Aegon died
						any_dynasty_member = {""",
        expected=4,
        label="AGOT+ Aegon-death trigger iterators",
    )
    text = replace_exact(
        text,
        """dynasty:dynn_Targaryen = { #Aemond died
						every_dynasty_member = {""",
        """dynasty:dynn_Targaryen = { #Aemond died
						any_dynasty_member = {""",
        expected=2,
        label="AGOT+ Aemond-death trigger iterators",
    )
    write_text(AGOT_PLUS_OUTPUT, relative, text)

    relative = "common/scripted_effects/asoiaf_setup_effects.txt"
    text = read_text(WORKSHOP / "2950245430" / relative)
    text = replace_regex(
        text,
        (
            r"(?m)^([ \t]*)(add_perk = [A-Za-z0-9_]+)"
            r"([ \t]*(?:#[^\r\n]*)?)$"
        ),
        r"\1if = { limit = { is_alive = yes } \2 }\3",
        expected=1360,
        label="AGOT+ historical-character alive perk guards",
    )
    text = replace_exact(
        text,
        "has_claim = title:",
        "has_claim_on = title:",
        expected=15,
        label="AGOT+ current has-claim triggers",
    )
    text = replace_exact(
        text,
        "is_dead = yes",
        "is_alive = no",
        expected=2,
        label="AGOT+ current dead-character triggers",
    )
    text = replace_exact(
        text,
        "house = house:asoiaf_founders_old_house",
        "house = scope:asoiaf_founders_old_house",
        expected=1,
        label="AGOT+ saved founder-house scope",
    )
    text = replace_exact(
        text,
        "track = venator",
        "track = hunter",
        expected=1,
        label="AGOT+ current hunter trait track",
    )
    text = replace_exact(
        text,
        "set_focus = education_stewardhip",
        "set_focus = education_stewardship",
        expected=1,
        label="AGOT+ stewardship education focus typo",
    )
    text = replace_exact(
        text,
        "set_focus = bossy",
        "add_trait = bossy",
        expected=1,
        label="AGOT+ bossy childhood trait effect",
    )
    text = replace_exact(
        text,
        "add_trait = august_trait",
        "add_trait = august",
        expected=1,
        label="AGOT+ current August lifestyle trait",
    )
    text = replace_exact(
        text,
        "\t\tadd_trait = tourney_participan\n",
        "\t\tadd_trait = tourney_participant\n",
        expected=1,
        label="AGOT+ tournament-participant trait typo",
    )
    text = replace_exact(
        text,
        "\t\tremove_trait = lifestyle_reveler_2_history\n",
        "",
        expected=1,
        label="AGOT+ removed reveler history trait",
    )
    text = replace_exact(
        text,
        "add_trait = blademaster",
        "add_trait = lifestyle_blademaster",
        expected=1,
        label="AGOT+ current blademaster trait",
    )
    text = replace_exact(
        text,
        "character:Dormund_1",
        "character:Dormand_10",
        expected=2,
        label="AGOT+ current Artys Dormand character id",
    )
    text = replace_exact(
        text,
        "set_mother = character:Broome_rs_54",
        "set_mother = character:Brax_67",
        expected=1,
        label="AGOT+ Morrec Broome spouse id",
    )
    text = replace_exact(
        text,
        """	exists = character:Strong_30 #Harwin Strong (son of Lyonel)
	character:Targaryen_75 ?= { set_real_father = character:Strong_30 } #for some reason this is not already the case in the base game
	character:Targaryen_76 ?= { set_real_father = character:Strong_30 }
	character:Targaryen_77 ?= { set_real_father = character:Strong_30 }""",
        """	if = {
		limit = { exists = character:Strong_30 }
		character:Targaryen_75 ?= { set_real_father = character:Strong_30 } #for some reason this is not already the case in the base game
		character:Targaryen_76 ?= { set_real_father = character:Strong_30 }
		character:Targaryen_77 ?= { set_real_father = character:Strong_30 }
	}""",
        expected=1,
        label="AGOT+ Harwin Strong existence guard",
    )
    text = replace_exact(
        text,
        "\texists = character:Stark_5 #Lyanna Stark\n",
        "",
        expected=1,
        label="AGOT+ misplaced Lyanna Stark existence trigger",
    )
    text = replace_exact(
        text,
        """			limit = {
				current_date >= 8282.6.15 #one month before Rhaegar and lyanna run away together
			}
			set_relation_soulmate = character:Stark_5""",
        """			limit = {
				current_date >= 8282.6.15 #one month before Rhaegar and lyanna run away together
				exists = character:Stark_5
			}
			set_relation_soulmate = character:Stark_5""",
        expected=1,
        label="AGOT+ Lyanna Stark relationship guard",
    )
    text = replace_exact(
        text,
        """	exists = character:Lannister_1
	character:Lannister_1 = {""",
        "\tcharacter:Lannister_1 ?= {",
        expected=1,
        label="AGOT+ optional Tywin scope",
    )
    text = replace_exact(
        text,
        """	exists = character:Seaworth_1 #Davos
	exists = character:Melisandre_1 #Melisandre
""",
        "",
        expected=1,
        label="AGOT+ misplaced Davos and Melisandre existence triggers",
    )
    text = replace_exact(
        text,
        """			limit = {
				current_date >= 8283.1.1 #Davos saves Storm's End
			}
			set_relation_friend = character:Seaworth_1""",
        """			limit = {
				current_date >= 8283.1.1 #Davos saves Storm's End
				exists = character:Seaworth_1
			}
			set_relation_friend = character:Seaworth_1""",
        expected=1,
        label="AGOT+ Davos relationship guard",
    )
    text = replace_exact(
        text,
        """			limit = {
				current_date >= 8300.1.1 #Melisande arrived some years prior, and by now has Stannis around her finger
			}
			set_relation_lover = character:Melisandre_1""",
        """			limit = {
				current_date >= 8300.1.1 #Melisande arrived some years prior, and by now has Stannis around her finger
				exists = character:Melisandre_1
			}
			set_relation_lover = character:Melisandre_1""",
        expected=1,
        label="AGOT+ Melisandre relationship guard",
    )
    text = replace_exact(
        text,
        "\texists = character:Tyrell_13 #Loras Tyrell (son of Mace)\n",
        "",
        expected=1,
        label="AGOT+ misplaced Loras Tyrell existence trigger",
    )
    text = replace_exact(
        text,
        "\t\tset_relation_friend = character:Tyrell_13 #Loras",
        """		if = {
			limit = { exists = character:Tyrell_13 }
			set_relation_friend = character:Tyrell_13 #Loras
		}""",
        expected=1,
        label="AGOT+ Loras relationship guard",
    )
    text = replace_exact(
        text,
        "\texists = character:Baratheon_4 #Renly Baratheon (son of Steffon); friends before lovers, and even friends while lovers\n",
        "",
        expected=1,
        label="AGOT+ misplaced Renly Baratheon existence trigger",
    )
    text = replace_exact(
        text,
        "\t\tset_relation_best_friend = character:Baratheon_4 #Renly",
        """		if = {
			limit = { exists = character:Baratheon_4 }
			set_relation_best_friend = character:Baratheon_4 #Renly
		}""",
        expected=1,
        label="AGOT+ Renly relationship guard",
    )
    text = replace_exact(
        text,
        """	exists = character:Lannister_135 #Orson Lannister (son of Daven)
	character:Lannister_135 = {""",
        "\tcharacter:Lannister_135 ?= { #Orson Lannister (son of Daven)",
        expected=1,
        label="AGOT+ optional Orson Lannister scope",
    )
    text = replace_exact(
        text,
        """			exists = character:Saan_asoiaf_2_mother
			set_mother = character:Saan_asoiaf_2_mother #Salladhor's Summer Islander mother""",
        """			if = {
				limit = { exists = character:Saan_asoiaf_2_mother }
				set_mother = character:Saan_asoiaf_2_mother #Salladhor's Summer Islander mother
			}""",
        expected=1,
        label="AGOT+ Salladhor Saan mother guard",
    )
    text = replace_exact(
        text,
        "asoiaf_underaged ?= { age >= 16 }",
        "scope:asoiaf_underaged ?= this\n\t\t\t\tage >= 16",
        expected=107,
        label="AGOT+ alternative-age saved-scope checks",
    )
    text = replace_exact(
        text,
        """		if = { #for people using the More Bookmarks mod, so that Selyse is of the proper faith
			limit = {
				faith = faith:rhllor
			}
			set_character_faith = faith:rhllor_fots
		}
""",
        "",
        expected=1,
        label="AGOT+ obsolete More Bookmarks Selyse faith bridge",
    )
    text = replace_exact(
        text,
        """		if = { #for people using the More Bookmarks mod, so that Stannis and his followers are of the proper faith
			limit = {
				#AND = {
					#current_date >= 8299.3.3 #the day Stannis converts
					faith = faith:rhllor
				#}
			}
			set_character_faith = faith:rhllor_fots
			every_courtier_or_guest  = { limit = { faith = faith:rhllor } set_character_faith = faith:rhllor_fots }
			every_vassal_or_below  = { limit = { faith = faith:rhllor } set_character_faith = faith:rhllor_fots }
			every_vassal_or_below = { every_courtier_or_guest  = { limit = { faith = faith:rhllor } set_character_faith = faith:rhllor_fots } }
		}
""",
        "",
        expected=1,
        label="AGOT+ obsolete More Bookmarks Stannis faith bridge",
    )
    write_text(AGOT_PLUS_OUTPUT, relative, text)

    relative = "common/scripted_effects/asoiaf_scripted_effects_strong_seed.txt"
    text = read_text(WORKSHOP / "2950245430" / relative)
    text = replace_exact(
        text,
        "limit = { dynasty ?= dynasty:dynn_Redbeard }",
        "limit = { house ?= house:house_Redbeard }",
        expected=1,
        label="AGOT+ Redbeard house comparison",
    )
    write_text(AGOT_PLUS_OUTPUT, relative, text)

    relative = "common/modifiers/asoiaf_canon_children_modifiers.txt"
    text = read_text(WORKSHOP / "2950245430" / relative)
    modifier_pattern = re.compile(
        r"(?m)^asoiaf_Greyjoy_13_modifier = \{\n"
        r"(?:\t[^\n]*\n)+"
        r"\}"
    )
    matches = modifier_pattern.findall(text)
    if len(matches) != 1:
        raise RuntimeError(
            "AGOT+ Asha/Yara canon-child modifier: expected one source "
            f"modifier, found {len(matches)}"
        )
    alt_modifier = replace_exact(
        matches[0],
        "asoiaf_Greyjoy_13_modifier",
        "asoiaf_Greyjoy_13_alt_modifier",
        expected=1,
        label="AGOT+ Asha canon-child modifier definition",
    )
    write_text(
        AGOT_PLUS_OUTPUT,
        "common/modifiers/zz_asoiaf_runtime_missing_modifiers.txt",
        (
            "# AGOT+ localizes and applies this Asha variant but does not "
            "define it.\n"
            "# Keep its gameplay values synchronized with the Yara variant.\n"
            f"{alt_modifier}\n"
        ),
    )

    incomplete_children = tuple(range(98, 105))
    trigger_source = read_text(
        WORKSHOP
        / "2950245430/common/scripted_triggers/asoiaf_canon_children_triggers.txt"
    )
    effect_source = read_text(
        WORKSHOP
        / "2950245430/common/scripted_effects/asoiaf_canon_children_effects.txt"
    )
    trigger_counts = {
        child: len(
            re.findall(
                rf"(?m)^asoiaf_canon_children_Targaryen_{child}_trigger\s*=\s*\{{",
                trigger_source,
            )
        )
        for child in incomplete_children
    }
    expected_trigger_counts = {
        98: 1,
        99: 2,
        100: 1,
        101: 0,
        102: 0,
        103: 0,
        104: 0,
    }
    if trigger_counts != expected_trigger_counts:
        raise RuntimeError(
            "AGOT+ incomplete Aegon IV child triggers changed: "
            f"expected {expected_trigger_counts}, found {trigger_counts}"
        )
    for child in incomplete_children:
        effect_name = f"asoiaf_canon_children_Targaryen_{child}_birth_effect"
        if re.search(rf"(?m)^{effect_name}\s*=\s*\{{", effect_source):
            raise RuntimeError(
                f"AGOT+ now defines {effect_name}; rebase the disabled branch"
            )
    write_text(
        AGOT_PLUS_OUTPUT,
        "common/scripted_triggers/zz_asoiaf_runtime_disabled_incomplete_children.txt",
        (
            "# AGOT+ references these incomplete branches without defining all "
            "trigger/effect pairs.\n"
            + "\n".join(
                f"asoiaf_canon_children_Targaryen_{child}_trigger = {{ always = no }}"
                for child in incomplete_children
            )
            + "\n"
        ),
    )
    write_text(
        AGOT_PLUS_OUTPUT,
        "common/scripted_effects/zz_asoiaf_runtime_disabled_incomplete_children.txt",
        (
            "# Compile-safe no-ops for the disabled incomplete event branches.\n"
            + "\n".join(
                f"asoiaf_canon_children_Targaryen_{child}_birth_effect = {{ }}"
                for child in incomplete_children
            )
            + "\n"
        ),
    )


def generate_mpo_nomad_event_guards() -> None:
    """Guard MPO nomad events against AGOT's disabled Great Steppe situation."""
    relative = "events/dlc/mpo/mpo_nomads_flavour_events.txt"
    source = read_text(WORKSHOP / "2962333032" / relative)
    source = replace_exact(
        source,
        """\t\tmodifier = {
\t\t\tadd = 3
\t\t\tsituation:the_great_steppe = {
""",
        """\t\tmodifier = {
\t\t\tadd = 3
\t\t\tsituation:the_great_steppe ?= {
""",
        expected=1,
        label="AGOT MPO snow-wolf event optional Great Steppe situation",
    )
    source = replace_exact(
        source,
        """\t\tsituation:the_great_steppe = {
\t\t\tNOR = {
\t\t\t    any_situation_sub_region = {
""",
        """\t\tsituation:the_great_steppe ?= {
\t\t\tNOR = {
\t\t\t    any_situation_sub_region = {
""",
        expected=1,
        label="AGOT MPO low-herd event optional Great Steppe situation",
    )
    write_text(OUTPUT, relative, normalize_rebased_source(source))


def main() -> None:
    generate_seasons_agot_shaders()
    generate_mari_agot_portraits()
    generate_faster_transitions_gui()
    generate_additional_models_on_action_deduplication()
    generate_kurultai_succession_scope_repairs()
    generate_essos_disabled_realm_cleanup()
    generate_nomad_yurt_guards()
    generate_pirate_succession_guards()
    generate_faction_legitimate_house_guards()
    generate_dragon_wives_legitimate_house_guards()
    generate_court_events_3020_role_guard()
    generate_aurion_title_gain_guard()
    generate_cow_province_setup_rebase()
    generate_upgrade_house_banners_event()
    generate_scene_culture_owner_guards()
    generate_now_core_rebase()
    generate_now_summerhall_candidate_guards()
    generate_mfa_delayed_pulse_scopes()
    generate_grand_remembrance_agot_obituary()
    generate_landed_knights()
    generate_expanded_court_position_hire_events()
    generate_legitimacy_over_time_ai()
    generate_red_keep_castellan_guard()
    generate_automated_squire_training_events()
    generate_knighting_ceremony_event()
    generate_house_founders()
    generate_artifact_manager_distribution_event()
    generate_additional_models_decision_illustrations()
    generate_succession_crisis()
    generate_more_interactive_vassals_war_join_guards()
    generate_agot_war_value_guards()
    generate_artifact_manager_scripted_guis()
    generate_artifact_manager_upgrade_guis()
    generate_advanced_character_search()
    generate_any_new_traditions()
    generate_great_councils()
    generate_suggest_dragon_bonding()
    generate_agot_tour_events()
    generate_adventurers_beneficiary()
    generate_all_men_must_serve()
    generate_agot_artifact_succession()
    generate_agot_artifact_feature_owner_guards()
    generate_agot_wall_banner_capital_fallback()
    generate_deadly_ck3_health_location_guards()
    generate_deadly_ck3_infirm_track()
    generate_agot_citadel()
    generate_agot_starting_legitimacy()
    generate_vanilla_tour_pulse()
    generate_mpo_nomad_event_guards()
    generate_agot_plus()
    print("Generated AGOT playset runtime fixes and AGOT+ runtime rebase.")


if __name__ == "__main__":
    main()
