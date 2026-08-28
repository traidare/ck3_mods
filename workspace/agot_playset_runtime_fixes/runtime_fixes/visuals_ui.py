"""Runtime repairs for visuals ui."""

from __future__ import annotations

import re
import textwrap
from pathlib import Path

from gen.script import (
    balanced_brace_end,
    normalize_rebased_source,
    read_text,
    replace_regex,
    write_text,
)
from gen.text import replace_exact

from .common import (
    assert_source_block_hash,
    extract_top_level_block,
    game_root,
    guard_scene_culture_triggers,
    rebase_additional_models_scene_guards,
    replace_numbered_branch_with_constant,
)
from .context import RunInputs


def generate_seasons_agot_shaders(inputs: RunInputs) -> None:
    """Repair legacy Seasons shaders or retire the superseded local override."""
    seasons = inputs.WORKSHOP / "3377641022"
    current_tree = read_text(inputs.WORKSHOP / "2962333032/gfx/FX/tree.shader")
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
            write_text(inputs.OUTPUT, relative, text, preserve_trailing_whitespace=True)
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
        output_path = inputs.OUTPUT / relative
        if output_path.is_file():
            output_path.unlink()
        elif output_path.exists():
            raise RuntimeError(f"expected a file or no output at {output_path}")


def generate_mari_agot_portraits(inputs: RunInputs) -> None:
    """Remove portrait genes deleted by AGOT 0.4.40 and repair one DNA typo."""
    mari = inputs.WORKSHOP / "3462342647"
    obsolete_gene_line = re.compile(
        r"(?m)^[ \t]*(?:gene_GH_marker_clothing_[1-7]_[rgb]|"
        r"special_accessories_earrings)\s*=\s*\{[^\r\n]*\}\r?\n"
    )
    template_replacements = (
        ('"aegon_crown_gems"', '"agot_crowns"', 0, 1),
        ('"aegon_crown_no_gems"', '"agot_crowns"', 0, 1),
        ('"crowns_of_westeros"', '"agot_crowns"', 13, 18),
        ('"valyrian_nobility_clothing_generic"', '"agot_all_clothes"', 3, 1),
        ('"valyrian_nobility_clothing"', '"agot_all_clothes"', 3, 3),
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
    write_text(inputs.OUTPUT, relative, text, preserve_trailing_whitespace=True)

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
            inputs.OUTPUT,
            f"common/bookmark_portraits/{source.name}",
            repaired,
            preserve_trailing_whitespace=True,
        )


def generate_faster_transitions_gui(inputs: RunInputs) -> None:
    """Carry CK3 1.19 event-window additions into Faster Transitions."""
    relative = "gui/00_no_transition.gui"
    text = read_text(inputs.WORKSHOP / "3437814875" / relative)
    tournament = read_text(
        game_root(inputs) / "gui/activity_window_widgets/tournament_widget_types.gui"
    )
    chariot = read_text(
        game_root(inputs) / "gui/activity_window_widgets/chariot_race_widget_types.gui"
    )
    event_windows = read_text(game_root(inputs) / "gui/shared/event_windows.gui")

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
    write_text(inputs.OUTPUT, relative, text, force_newline="\r\n", with_bom=False)


def generate_additional_models_on_action_deduplication(inputs: RunInputs) -> None:
    """Retire the superseded AMSB dynasty-on-action suppressor."""
    relative = "common/on_action/amsb_dynasty_on_actions.txt"
    compatch_relative = "common/scripted_effects/zz_am_lov_artifact_dedup_effects.txt"
    additional_models = read_text(inputs.WORKSHOP / "3319354609" / relative)
    compatch = read_text(inputs.WORKSHOP / "3762892081" / compatch_relative)
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
    output_path = inputs.OUTPUT / relative
    if output_path.is_file():
        output_path.unlink()
    elif output_path.exists():
        raise RuntimeError(f"expected a file or no output at {output_path}")


def generate_upgrade_house_banners_event(inputs: RunInputs) -> None:
    """Restore the localized close option omitted from the visible event."""
    relative = "events/uhb_court_maintenance.txt"
    text = read_text(inputs.WORKSHOP / "3709868073" / relative)
    event = extract_top_level_block(text, "uhb_court_maintenance.0001")
    if "\n\toption = {" in event:
        raise RuntimeError(
            "Upgrade House Banners maintenance event now supplies an option"
        )
    if "hidden = yes" in event:
        raise RuntimeError("Upgrade House Banners maintenance event is now hidden")
    localization = read_text(
        inputs.WORKSHOP
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
    write_text(inputs.OUTPUT, relative, text, preserve_trailing_whitespace=True)


def generate_scene_culture_owner_guards(inputs: RunInputs) -> None:
    sources = (
        (
            "3762892081",
            "gfx/court_scene/scene_cultures/00_default_cultures.txt",
            12,
            "Additional Models/AGOT+/LoV generic court scenes",
        ),
        (
            "2962333032",
            "gfx/court_scene/scene_cultures/agot_default_cultures.txt",
            21,
            "AGOT named court scenes",
        ),
    )
    for workshop_id, relative, expected, label in sources:
        text = read_text(inputs.WORKSHOP / workshop_id / relative)
        if workshop_id == "3762892081":
            text = rebase_additional_models_scene_guards(inputs, text)
        text = guard_scene_culture_triggers(text, expected=expected, label=label)
        write_text(inputs.OUTPUT, relative, text)


def generate_additional_models_decision_illustrations(inputs: RunInputs) -> None:
    missing = "gfx/interface/illustrations/agot_court/throne.dds"
    fallback = (
        "gfx/interface/illustrations/event_scenes/ironthrone/throneroom_ironthrone.dds"
    )
    sources = {
        "common/decisions/amsb_bent_knees_decision.txt": 1,
        "common/decisions/amsb_abdicate_decision.txt": 2,
    }
    if not (inputs.WORKSHOP / "2962333032" / fallback).is_file():
        raise RuntimeError(
            "Additional Models decision illustration fallback is absent "
            "from current AGOT"
        )
    if (inputs.WORKSHOP / "3319354609" / missing).exists():
        raise RuntimeError(
            "Additional Models now supplies its throne illustration; "
            "remove the local fallback rebase"
        )
    for relative, expected in sources.items():
        text = read_text(inputs.WORKSHOP / "3319354609" / relative)
        text = replace_exact(
            text,
            missing,
            fallback,
            expected=expected,
            label=f"Additional Models decision illustration in {relative}",
        )
        write_text(inputs.OUTPUT, relative, text)


def _holding_illustration_defines(
    inputs: RunInputs, relative: str, label: str
) -> dict[str, str]:
    """Return AGOT's illustration constants for one holding type."""
    agot = inputs.WORKSHOP / "2962333032"
    defines = dict(
        re.findall(
            r'(?m)^@(holding_illustration_[a-z_]+)\s*=\s*"([^"]+)"',
            read_text(agot / relative),
        )
    )
    if not defines:
        raise RuntimeError(f"AGOT declares no {label} holding illustrations")
    for name, target in sorted(defines.items()):
        if not (agot / target).is_file() and not (game_root(inputs) / target).is_file():
            raise RuntimeError(f"AGOT {label} illustration @{name} targets {target}")
    return defines


def generate_additional_models_holding_art_constants(inputs: RunInputs) -> None:
    """Resolve the merged holding-art file's unset illustration constants."""
    relative = "common/buildings/zz_am_lov_nv_holding_art.txt"
    text = read_text(inputs.WORKSHOP / "3762892081" / relative)
    # `@` constants are file-scoped. This file merges castle, city, and temple
    # keys that AGOT keeps in separate files, each of which binds the same
    # constant names to its own art, so the merge cannot carry one define block
    # and declares none at all. Every reference then reaches the VFS as the
    # literal string `@holding_illustration_*`, and the lookup fails on every
    # frame that draws the holding. Bind each reference to the art AGOT gives
    # that constant in the file the block came from.
    if re.search(r"(?m)^@", text):
        raise RuntimeError(
            "Additional Models/AGOT+/LoV holding art now declares constants of "
            "its own; re-audit before resolving them here"
        )
    defines = {
        "castle": _holding_illustration_defines(
            inputs, "common/buildings/00_agot_castle_buildings.txt", "castle"
        ),
        "city": _holding_illustration_defines(
            inputs, "common/buildings/00_agot_city_buildings.txt", "city"
        ),
    }
    expected = {"castle": 292, "city": 273}
    resolved: dict[str, int] = {holding: 0 for holding in defines}
    pieces: list[str] = []
    cursor = 0
    for match in re.finditer(r"(?m)^([a-z_0-9]+) = \{", text):
        end = balanced_brace_end(text, text.index("{", match.start())) + 1
        key = match.group(1)
        holding = key.rsplit("_", 1)[0]
        block = text[match.start() : end]
        used = set(re.findall(r"@(holding_illustration_[a-z_]+)", block))
        if used:
            if holding not in defines:
                raise RuntimeError(
                    f"holding art block {key} references illustration constants "
                    f"that no AGOT holding type defines"
                )
            missing = sorted(used - defines[holding].keys())
            if missing:
                raise RuntimeError(
                    f"AGOT leaves {', '.join(missing)} undefined for {holding} "
                    f"holdings, reached from block {key}"
                )
            block, count = re.subn(
                r"@(holding_illustration_[a-z_]+)",
                lambda found, holding=holding: f'"{defines[holding][found.group(1)]}"',
                block,
            )
            resolved[holding] += count
        pieces.append(text[cursor : match.start()])
        pieces.append(block)
        cursor = end
    pieces.append(text[cursor:])
    text = "".join(pieces)
    if resolved != expected:
        raise RuntimeError(
            f"Additional Models/AGOT+/LoV holding art illustration counts "
            f"changed: {resolved} is not {expected}"
        )
    if "@holding_illustration" in text:
        raise RuntimeError("holding art retains an unresolved illustration constant")
    write_text(inputs.OUTPUT, relative, text, preserve_trailing_whitespace=True)


def generate_additional_models_scripted_illustration_cultures(
    inputs: RunInputs,
) -> None:
    """Drop a misspelled culture from a per-frame illustration trigger."""
    shadowlanders = read_text(
        inputs.WORKSHOP
        / "2962333032/common/culture/cultures/00_agot_cul_shadowlanders.txt"
    )
    if not re.search(r"(?m)^shadowman\s*=\s*\{", shadowlanders):
        raise RuntimeError("AGOT no longer defines the shadowman culture")
    if re.search(r"(?m)^shadowmen\s*=\s*\{", shadowlanders):
        raise RuntimeError(
            "AGOT now defines a shadowmen culture; keep the reference instead"
        )
    relative = "gfx/interface/illustrations/scripted_illustrations/ingame.txt"
    text = read_text(inputs.WORKSHOP / "3762892081" / relative)
    # `character_view_bg` re-evaluates whenever the portrait redraws, so each
    # unresolvable culture costs a failed lookup per frame. Every `shadowmen`
    # line sits in an OR beside the `shadowman` line it misspells, so dropping
    # it leaves the intended coverage intact.
    live = r"(?m)^([ \t]*)culture = culture:shadowman[ \t]*$"
    if len(re.findall(live, text)) != 6:
        raise RuntimeError(
            "Additional Models/AGOT+/LoV illustration shadowman references changed"
        )
    text = replace_regex(
        text,
        r"(?m)^[ \t]*culture = culture:shadowmen[ \t]*\r?\n",
        "",
        expected=6,
        label="Additional Models/AGOT+/LoV illustration shadowmen references",
    )
    write_text(inputs.OUTPUT, relative, text, preserve_trailing_whitespace=True)


def generate_character_ui_overhaul_hometowns(inputs: RunInputs) -> None:
    """Retain CUIO hometowns while removing its unsafe vanilla assumptions."""
    cuio = inputs.WORKSHOP / "2519175282"
    relative = "common/on_action/hometowns_on_actions.txt"
    source = read_text(cuio / relative)
    save_location = assert_source_block_hash(
        source,
        "hometowns_save_location",
        "41f21d3258bb9287b8e3fa3c82df37a81e1569608898215f38f6ee5e1ab48a5f",
        label="CUIO hometown birth-location action",
    )
    init = assert_source_block_hash(
        source,
        "hometowns_county_modifier_init",
        "961972bdfa5c6ecee1c4eda090322adcc6c27480b0c629fd511e99ab3f644aa5",
        label="CUIO hometown startup action",
    )
    modifier = assert_source_block_hash(
        source,
        "hometowns_county_modifier",
        "b12e7581f6bc9a176d6edbba76869489d4289d9be662f134d392a2e28a92a94c",
        label="CUIO hometown title-gain action",
    )
    repaired_save_location = """hometowns_save_location = {
\teffect = {
\t\t# Some generated children have no maternal location during setup.
\t\tif = {
\t\t\tlimit = { exists = scope:mother.location }
\t\t\tscope:child = {
\t\t\t\tset_variable = {
\t\t\t\t\tname = hometowns_birthplace
\t\t\t\t\tvalue = scope:mother.location
\t\t\t\t}
\t\t\t}
\t\t}
\t}
}"""
    repaired_init = """hometowns_county_modifier_init = {
\teffect = {
\t\tif = {
\t\t\tlimit = { has_game_rule = hometowns_features }
\t\t\tevery_ruler = {
\t\t\t\tlimit = {
\t\t\t\t\thas_variable = hometowns_birthplace
\t\t\t\t\texists = var:hometowns_birthplace.county
\t\t\t\t\tvar:hometowns_birthplace.county.holder = this
\t\t\t\t}
\t\t\t\tvar:hometowns_birthplace.county = {
\t\t\t\t\tadd_county_modifier = hometowns_county_modifier
\t\t\t\t}
\t\t\t}
\t\t}
\t}
}"""
    repaired_modifier = """hometowns_county_modifier = {
\teffect = {
\t\tif = {
\t\t\tlimit = { has_game_rule = hometowns_features }
\t\t\tevery_held_title = {
\t\t\t\tlimit = {
\t\t\t\t\ttier = tier_county
\t\t\t\t\thas_county_modifier = hometowns_county_modifier
\t\t\t\t}
\t\t\t\tsave_temporary_scope_as = hometowns_held_county
\t\t\t\tif = {
\t\t\t\t\tlimit = {
\t\t\t\t\t\tcounty.holder = { has_variable = hometowns_birthplace }
\t\t\t\t\t}
\t\t\t\t\tcounty.holder = {
\t\t\t\t\t\tif = {
\t\t\t\t\t\t\tlimit = {
\t\t\t\t\t\t\t\tNOT = {
\t\t\t\t\t\t\t\t\tvar:hometowns_birthplace.county = scope:hometowns_held_county
\t\t\t\t\t\t\t\t}
\t\t\t\t\t\t\t}
\t\t\t\t\t\t\tscope:hometowns_held_county = {
\t\t\t\t\t\t\t\tcounty = {
\t\t\t\t\t\t\t\t\tremove_county_modifier = hometowns_county_modifier
\t\t\t\t\t\t\t\t}
\t\t\t\t\t\t\t}
\t\t\t\t\t\t}
\t\t\t\t\t}
\t\t\t\t}
\t\t\t\telse = {
\t\t\t\t\tcounty = { remove_county_modifier = hometowns_county_modifier }
\t\t\t\t}
\t\t\t}
\t\t\tif = {
\t\t\t\tlimit = {
\t\t\t\t\thas_variable = hometowns_birthplace
\t\t\t\t\texists = var:hometowns_birthplace.county
\t\t\t\t\tvar:hometowns_birthplace.county.holder = this
\t\t\t\t}
\t\t\t\tvar:hometowns_birthplace.county = {
\t\t\t\t\tadd_county_modifier = hometowns_county_modifier
\t\t\t\t}
\t\t\t}
\t\t}
\t}
}"""
    for original, repaired, label in (
        (save_location, repaired_save_location, "CUIO hometown birth-location rebase"),
        (init, repaired_init, "CUIO hometown startup rebase"),
        (modifier, repaired_modifier, "CUIO hometown title-gain rebase"),
    ):
        source = replace_exact(source, original, repaired, expected=1, label=label)
    if "county.holder.var:hometowns_birthplace" in source:
        raise RuntimeError("CUIO hometown action retained an unguarded variable read")
    write_text(inputs.OUTPUT, relative, normalize_rebased_source(source))

    relative = "events/hometowns_events.txt"
    source = read_text(cuio / relative)
    if source.count("namespace = hometowns") != 1:
        raise RuntimeError("CUIO hometown historical-event namespace changed")
    historical_event = assert_source_block_hash(
        source,
        "hometowns.01",
        "b07a269826a56db66be54930868da4290d6e186b74546650325527cfe769ade0",
        label="CUIO historical hometown assignments",
    )
    inert_event = """hometowns.01 = {
\thidden = yes
\tscope = none
\timmediate = { }
}"""
    source = replace_exact(
        source,
        historical_event,
        inert_event,
        expected=1,
        label="CUIO historical hometown event rebase",
    )
    write_text(inputs.OUTPUT, relative, normalize_rebased_source(source))


def generate_advanced_character_search(inputs: RunInputs) -> None:
    relative = "common/scripted_triggers/gen_acs_st_big_switch.txt"
    text = read_text(inputs.WORKSHOP / "3084203091" / relative)
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
    religion_end = text.index("\n                                8 = {", religion_start)
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
    write_text(inputs.OUTPUT, relative, text)

    relative = "common/scripted_guis/acs_sg_main_scripted_gui.txt"
    text = read_text(inputs.WORKSHOP / "3084203091" / relative)
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
    write_text(inputs.OUTPUT, relative, text, force_newline="\r\n")

    relative = "gui/acs.gui"
    text = read_text(inputs.WORKSHOP / "3084203091" / relative)
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
    write_text(inputs.OUTPUT, relative, text, force_newline="\r\n")
