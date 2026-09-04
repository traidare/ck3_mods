#!/usr/bin/env python3
"""Rebase AGOT+ runtime repairs onto the current AGOT playset.

Every replacement is counted, so an upstream update fails loudly instead of
silently generating a stale whole-file override.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from gen import GenerationContext
from gen.script import read_text, replace_regex, write_text
from gen.sources import WorkshopSources
from gen.text import replace_exact


@dataclass(frozen=True, slots=True)
class RunInputs:
    WORKSHOP: WorkshopSources
    AGOT_PLUS_OUTPUT: Path


def history_character_ids(inputs: RunInputs, *workshop_ids: str) -> set[str]:
    ids: set[str] = set()
    pattern = re.compile(r"^([A-Za-z0-9_]+)\s*=\s*\{", re.MULTILINE)
    for workshop_id in workshop_ids:
        history = inputs.WORKSHOP / workshop_id / "history/characters"
        if not history.is_dir():
            continue
        for path in history.rglob("*.txt"):
            ids.update(pattern.findall(read_text(path)))
    return ids


def generate_agot_plus(inputs: RunInputs) -> None:
    relative = "common/scripted_effects/asoiaf_canon_children_effects.txt"
    text = read_text(inputs.WORKSHOP / "2950245430" / relative)
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

    character_ids = history_character_ids(inputs, "2962333032", "2950245430")
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
    write_text(inputs.AGOT_PLUS_OUTPUT, relative, text, force_newline="\r\n")

    relative = "common/scripted_effects/asoiaf_setup_effects.txt"
    text = read_text(inputs.WORKSHOP / "2950245430" / relative)
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
    write_text(inputs.AGOT_PLUS_OUTPUT, relative, text, force_newline="\r\n")

    relative = "common/scripted_effects/asoiaf_scripted_effects_strong_seed.txt"
    text = read_text(inputs.WORKSHOP / "2950245430" / relative)
    text = replace_exact(
        text,
        "limit = { dynasty ?= dynasty:dynn_Redbeard }",
        "limit = { house ?= house:house_Redbeard }",
        expected=1,
        label="AGOT+ Redbeard house comparison",
    )
    write_text(inputs.AGOT_PLUS_OUTPUT, relative, text, force_newline="\r\n")

    relative = "common/modifiers/asoiaf_canon_children_modifiers.txt"
    text = read_text(inputs.WORKSHOP / "2950245430" / relative)
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
        inputs.AGOT_PLUS_OUTPUT,
        "common/modifiers/zz_asoiaf_runtime_missing_modifiers.txt",
        (
            "# AGOT+ localizes and applies this Asha variant but does not "
            "define it.\n"
            "# Keep its gameplay values synchronized with the Yara variant.\n"
            f"{alt_modifier}\n"
        ),
        force_newline="\r\n",
    )

    incomplete_children = tuple(range(98, 105))
    trigger_source = read_text(
        inputs.WORKSHOP
        / "2950245430/common/scripted_triggers/asoiaf_canon_children_triggers.txt"
    )
    effect_source = read_text(
        inputs.WORKSHOP
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
    expected_trigger_counts = {98: 1, 99: 2, 100: 1, 101: 0, 102: 0, 103: 0, 104: 0}
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
        inputs.AGOT_PLUS_OUTPUT,
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
        force_newline="\r\n",
    )
    write_text(
        inputs.AGOT_PLUS_OUTPUT,
        "common/scripted_effects/zz_asoiaf_runtime_disabled_incomplete_children.txt",
        (
            "# Compile-safe no-ops for the disabled incomplete event branches.\n"
            + "\n".join(
                f"asoiaf_canon_children_Targaryen_{child}_birth_effect = {{ }}"
                for child in incomplete_children
            )
            + "\n"
        ),
        force_newline="\r\n",
    )


def generate(context: GenerationContext) -> None:

    WORKSHOP = WorkshopSources(context)
    AGOT_PLUS_OUTPUT = context.output_root
    inputs = RunInputs(WORKSHOP=WORKSHOP, AGOT_PLUS_OUTPUT=AGOT_PLUS_OUTPUT)
    generate_agot_plus(inputs)
