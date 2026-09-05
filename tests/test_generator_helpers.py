from __future__ import annotations

import re
import tempfile
import unittest
from pathlib import Path

from gen.__main__ import load_entrypoint
from gen.data import csv_bytes
from gen.reads import ReadRecorder
from gen.script import guard_event_deaths
from gen.text import direct_child_block_start, line_block_end

ROOT = Path(__file__).resolve().parents[1]


def generator_function(relative: str, name: str):
    return load_entrypoint(ROOT / relative, name)


class SharedGeneratorHelperTest(unittest.TestCase):
    def test_csv_bytes_has_stable_field_and_line_order(self) -> None:
        self.assertEqual(
            csv_bytes(["id", "name"], [{"name": "Essos", "id": 7}]),
            b"id,name\n7,Essos\n",
        )

    def test_line_blocks_ignore_nested_and_commented_braces(self) -> None:
        lines = (
            "outer = {\n"
            '\tnested = { value = "} not structural" } # {\n'
            "\trandom_list = {\n"
            "\t\t1 = yes\n"
            "\t}\n"
            "}\n"
        ).splitlines(keepends=True)
        pattern = re.compile(r"^\s*random_list\s*=\s*\{")
        self.assertEqual(line_block_end(lines, 0), len(lines))
        self.assertEqual(direct_child_block_start(lines, 0, pattern), 2)

    def test_nested_recorders_each_capture_the_read(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.txt"
            source.write_text("source", encoding="utf-8")
            outer = ReadRecorder([directory])
            inner = ReadRecorder([directory])

            with outer.active(), inner.active():
                self.assertEqual(source.read_text(encoding="utf-8"), "source")

            expected = [str(source.resolve())]
            self.assertEqual(outer.paths(), expected)
            self.assertEqual(inner.paths(), expected)

    def test_paths_outside_source_roots_are_ignored(self) -> None:
        with (
            tempfile.TemporaryDirectory() as source_directory,
            tempfile.TemporaryDirectory() as other_directory,
        ):
            source = Path(source_directory) / "source.txt"
            other = Path(other_directory) / "other.txt"
            source.write_text("source", encoding="utf-8")
            other.write_text("other", encoding="utf-8")
            recorder = ReadRecorder([source_directory])

            with recorder.active():
                source.read_bytes()
                other.read_bytes()

            self.assertEqual(recorder.paths(), [str(source.resolve())])

    def test_exception_restores_read_functions(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.txt"
            source.write_text("source", encoding="utf-8")
            original_read_text = Path.read_text
            recorder = ReadRecorder([directory])

            with (
                self.assertRaisesRegex(RuntimeError, "generator stopped"),
                recorder.active(),
            ):
                source.read_text(encoding="utf-8")
                raise RuntimeError("generator stopped")

            self.assertIs(Path.read_text, original_read_text)
            self.assertEqual(recorder.paths(), [str(source.resolve())])

    def test_map_locator_parser_keeps_prefix_suffix_and_ids(self) -> None:
        text = (
            "locator = {\n"
            "\tinstances = {\n"
            "\t\t{\n\t\t\tid = 3\n\t\t\tposition={ 1 0 2 }\n\t\t}\n"
            "\t\t{\n\t\t\tid = 8\n\t\t\tposition={ 4 0 5 }\n\t\t}\n"
            "\t}\n}\n"
        )
        with generator_function(
            "workspace/agot_now_lov_ee_compatch/compatch/map_merge.py",
            "locator_records",
        ) as locator_records:
            prefix, suffix, order, records = locator_records(text)
        self.assertTrue(prefix.endswith("\tinstances = {\n"))
        self.assertEqual(suffix, "\n\t}\n}\n")
        self.assertEqual(order, [3, 8])
        self.assertEqual(list(records), [3, 8])

    def test_map_locator_parser_accepts_inline_records(self) -> None:
        text = (
            "locator = {\n"
            "\tinstances = {\n"
            "\t\t{ id = 3 position = { 1 0 2 } }\n"
            "\t\t{\n\t\t\tid = 8\n\t\t\tposition={ 4 0 5 }\n\t\t}\n"
            "\t}\n}\n"
        )
        with generator_function(
            "workspace/agot_now_lov_ee_compatch/compatch/map_merge.py",
            "locator_records",
        ) as locator_records:
            prefix, suffix, order, records = locator_records(text)
        self.assertTrue(prefix.endswith("\tinstances = {\n"))
        self.assertEqual(suffix, "\n\t}\n}\n")
        self.assertEqual(order, [3, 8])
        self.assertEqual(list(records), [3, 8])

        duplicate = text.replace("{ id = 3", "{ id = 8")
        with (
            generator_function(
                "workspace/agot_now_lov_ee_compatch/compatch/map_merge.py",
                "locator_records",
            ) as locator_records,
            self.assertRaisesRegex(RuntimeError, "duplicate locator id 8"),
        ):
            locator_records(duplicate)

    def test_map_locator_definition_dependencies_track_colour_remaps(self) -> None:
        agot_definition = {
            3: "3;1;2;3;b_first;x",
            8: "8;4;5;6;b_second;x",
            9: "9;7;8;9;b_old_name;x",
        }
        now_definition = {
            3: "3;4;5;6;b_first;x",
            8: "8;1;2;3;b_second;x",
            9: "9;7;8;9;b_new_name;x",
        }
        agot_locators = {
            key: f"{{ id={key} position={{ {key} 0 0 }} }}" for key in (3, 8, 9)
        }
        now_locators = {
            key: f"{{ id={key} position={{ {key + 1} 0 0 }} }}" for key in (3, 8, 9)
        }
        with generator_function(
            "workspace/agot_now_lov_ee_compatch/compatch/map_merge.py",
            "locator_definition_dependencies",
        ) as dependencies:
            self.assertEqual(
                dependencies(
                    agot_definition, now_definition, agot_locators, now_locators
                ),
                {3, 8},
            )

    def test_map_title_parser_handles_inline_assignments_and_comments(self) -> None:
        source = (
            "b_first = { province = 7 color = { 1 2 3 } }\n"
            "b_second = {\n\tprovince = 9\n}\n"
            "# b_retired = { province = 11 }\n"
        )
        with generator_function(
            "workspace/agot_now_lov_ee_compatch/compatch/map_merge.py",
            "province_ids_from_landed_titles",
        ) as province_ids:
            self.assertEqual(province_ids(source), (7, 9))

    def test_map_quarantine_is_deterministic_and_non_passable(self) -> None:
        source = "sea_zones = LIST { 2 }\nimpassable_mountains = LIST { 3 }\n"
        with (
            generator_function(
                "workspace/agot_now_lov_ee_compatch/compatch/map_merge.py",
                "append_impassable_quarantine",
            ) as append_quarantine,
            generator_function(
                "workspace/agot_now_lov_ee_compatch/compatch/map_merge.py",
                "land_provinces",
            ) as land_provinces,
        ):
            output = append_quarantine(source, (4, 5, 6), chunk_size=2)
            self.assertIn("impassable_mountains = LIST { 4 5 }", output)
            self.assertIn("impassable_mountains = LIST { 6 }", output)
            self.assertEqual(land_provinces(output, frozenset(range(1, 7))), {1})

    def test_map_region_gaps_are_restored_into_their_own_list(self) -> None:
        block = (
            "coastal_counties = {\n"
            "\tduchies = {\n\t\td_first\n\t}\n"
            "\tcounties = {\n\t\tc_first\n\t\tc_second\n\t}\n"
            "}"
        )
        with generator_function(
            "workspace/agot_now_lov_ee_compatch/compatch/map_merge.py",
            "restore_region_members",
        ) as restore:
            restored = restore(
                block,
                frozenset({"counties:c_third", "duchies:d_second"}),
                "regions coastal_counties",
            )
        self.assertEqual(
            restored,
            "coastal_counties = {\n"
            "\tduchies = {\n\t\td_first\n\t\td_second\n\t}\n"
            "\tcounties = {\n\t\tc_first\n\t\tc_second\n\t\tc_third\n\t}\n"
            "}",
        )

        with (
            generator_function(
                "workspace/agot_now_lov_ee_compatch/compatch/map_merge.py",
                "restore_region_members",
            ) as restore,
            self.assertRaisesRegex(RuntimeError, "no provinces list"),
        ):
            restore(block, frozenset({"provinces:42"}), "regions coastal_counties")

    def test_crash_repair_guards_all_appointment_scores(self) -> None:
        block = (
            "\t\t\tscope:target = {\n\t\t\t\tholder = {\n"
            "\t\t\t\t\thas_realm_law_flag = appointment_type_succession\n"
            "\t\t\t\t}\n\t\t\t}\n"
            "\t\t\tscope:target = {\n\t\t\t\tholder = {\n"
            "\t\t\t\t\thas_realm_law_flag = appointment_type_succession\n"
            "\t\t\t\t}\n\t\t\t}\n"
            '\t\t\t\t\t\t"appointment_candidate_accumulated_score'
            '(scope:target)" > 0\n'
            '\t\t\t\t\t\t"appointment_candidate_accumulated_score'
            '(scope:target)" > 0\n'
            '\t\t\t\t"appointment_candidate_accumulated_score'
            '(scope:target)" <= 0\n'
        )
        with generator_function(
            "workspace/agot_playset_runtime_fixes/runtime_fixes/crash_stability.py",
            "guard_appointment_score_calls",
        ) as guard_scores:
            repaired = guard_scores(block)
        self.assertEqual(repaired.count("trigger_else = { always = no }"), 3)
        self.assertEqual(
            repaired.count("has_title_law_flag = appointment_type_succession"), 5
        )

    def test_crash_repair_drops_surplus_title_giver_arguments(self) -> None:
        source = (
            "\t\t\tep3_become_landed_warning_effect = {\n"
            "\t\t\t\tTITLE_RECEIVER = scope:attacker\n"
            "\t\t\t\tTITLE_GIVER = scope:defender\n"
            "\t\t\t\tTITLE = scope:target\n"
            "\t\t\t}\n"
            "\t\t\tep3_landless_invasion_titles_taken_effect = {\n"
            "\t\t\t\tTITLE_GIVER = scope:defender\n"
            "\t\t\t\tTITLE_RECEIVER = scope:attacker\n"
            "\t\t\t\tTITLE = scope:target\n"
            "\t\t\t\tTITLE_LIST = target_titles\n"
            "\t\t\t}\n"
        )
        with generator_function(
            "workspace/agot_playset_runtime_fixes/runtime_fixes/crash_stability.py",
            "drop_unneeded_title_giver_arguments",
        ) as drop_title_giver:
            repaired = drop_title_giver(source)
        warning_block, invasion_block = repaired.split(
            "ep3_landless_invasion_titles_taken_effect"
        )
        # The warning effect loses the surplus argument...
        self.assertNotIn("TITLE_GIVER", warning_block)
        self.assertIn("TITLE_RECEIVER = scope:attacker", warning_block)
        # ...while the invasion effect keeps the one it actually declares.
        self.assertIn("TITLE_GIVER = scope:defender", invasion_block)
        self.assertIn("TITLE_LIST = target_titles", invasion_block)

    def test_crash_repair_strips_all_kraken_environment_fields(self) -> None:
        source = "".join(
            f"event.{index} = {{\n\toverride_environment = "
            "{ event_environment = x }\n}\n"
            for index in range(13)
        )
        with generator_function(
            "workspace/agot_playset_runtime_fixes/runtime_fixes/crash_stability.py",
            "strip_unsupported_override_environments",
        ) as strip_fields:
            repaired = strip_fields(source)
        self.assertNotIn("override_environment", repaired)

    def test_map_locator_band_replacement_removes_stale_parent_ids(self) -> None:
        current = (
            "prefix\n",
            "\nsuffix\n",
            [1, 3, 4, 5, 7],
            {key: f"current-{key}" for key in (1, 3, 4, 5, 7)},
        )
        canonical = (
            "ignored-prefix\n",
            "\nignored-suffix\n",
            [3, 5],
            {3: "canonical-3", 5: "canonical-5"},
        )
        with generator_function(
            "workspace/agot_now_lov_ee_compatch/compatch/map_merge.py",
            "replace_locator_band",
        ) as replace_locator_band:
            prefix, suffix, order, records = replace_locator_band(
                current, canonical, range(3, 6)
            )
        self.assertEqual(prefix, "prefix\n")
        self.assertEqual(suffix, "\nsuffix\n")
        self.assertEqual(order, [1, 3, 5, 7])
        self.assertEqual(
            records,
            {1: "current-1", 3: "canonical-3", 5: "canonical-5", 7: "current-7"},
        )

    def test_lore_parser_and_edit_overlap_guard(self) -> None:
        source = (
            'c_test = {\n\tculture = "essosi"\n\t1.2.3 = { government = clan }\n}\n'
        )
        with generator_function(
            "workspace/agot_now_lov_ee_compatch/compatch/pdx.py",
            "parse_document",
        ) as parse_document:
            document = parse_document(source)
        title = document.children(None)[0]
        self.assertEqual(title.key, "c_test")
        self.assertEqual(
            document.direct_scalars(title.ident, "culture")[0].value, "essosi"
        )

        with (
            generator_function(
                "workspace/agot_now_lov_ee_compatch/compatch/pdx.py",
                "apply_edits",
            ) as apply_edits,
            self.assertRaisesRegex(AssertionError, "overlapping"),
        ):
            apply_edits("abcdef", [(1, 4, "x"), (3, 5, "y")])

    def test_world_region_parser_ignores_braces_in_strings_and_comments(self) -> None:
        source = (
            'first = { name = "}" # }\n nested = { value = yes }\n}\nsecond = { }\n'
        )
        with generator_function(
            "workspace/agot_now_lov_ee_compatch/compatch/pdx.py",
            "top_level_blocks",
        ) as top_level_blocks:
            _prefix, _suffix, order, blocks = top_level_blocks(source)
        self.assertEqual(order, ["first", "second"])
        self.assertEqual(list(blocks), ["first", "second"])

    def test_canon_dragon_birthday_bridge_restores_agot_dispatch(self) -> None:
        agot_childhood = """on_10th_birthday = {
\ton_actions = { on_10th_birthday_tame_canon_dragon }
}
"""
        personality_childhood = """on_10th_birthday = {
\tevents = { child_personality.4000 }
}
"""
        agot_actions = """on_10th_birthday_tame_canon_dragon = {
\ttrigger = {
\t\tagot_canon_dragons_enabled = yes
\t\tis_ai = yes
\t\tagot_is_canon_rider = yes
\t\tany_relation = { type = agot_dragon count = 0 }
\t\tNOT = { any_scheme = { scheme_type = bond_with_dragon_scheme } }
\t}
\teffect = { add_character_flag = { flag = attempting_canon_bond years = 2 } }
\tevents = { dragon_taming_events.9000 }
}
"""
        with generator_function(
            "workspace/agot_full_playset_compatch/implementation.py",
            "generate_canon_dragon_birthday_on_action",
        ) as generate_bridge:
            output = generate_bridge(
                agot_childhood, agot_actions, personality_childhood
            )
        self.assertEqual(output.count("on_10th_birthday_tame_canon_dragon"), 1)
        self.assertIn("on_10th_birthday = {", output)

    def test_canon_dragon_birthday_bridge_rejects_duplicate_dispatch(self) -> None:
        childhood = """on_10th_birthday = {
\ton_actions = { on_10th_birthday_tame_canon_dragon }
}
"""
        with (
            generator_function(
                "workspace/agot_full_playset_compatch/implementation.py",
                "generate_canon_dragon_birthday_on_action",
            ) as generate_bridge,
            self.assertRaisesRegex(AssertionError, "already dispatches"),
        ):
            generate_bridge(childhood, "", childhood)

    def test_canon_dragon_birthday_bridge_rejects_changed_agot_action(self) -> None:
        agot_childhood = """on_10th_birthday = {
\ton_actions = { on_10th_birthday_tame_canon_dragon }
}
"""
        personality_childhood = "on_10th_birthday = { events = { test.1 } }\n"
        changed_action = """on_10th_birthday_tame_canon_dragon = {
\ttrigger = { agot_canon_dragons_enabled = yes is_ai = yes }
}
"""
        with (
            generator_function(
                "workspace/agot_full_playset_compatch/implementation.py",
                "generate_canon_dragon_birthday_on_action",
            ) as generate_bridge,
            self.assertRaisesRegex(AssertionError, "action changed"),
        ):
            generate_bridge(agot_childhood, changed_action, personality_childhood)


CANON_ENFORCEMENT = "workspace/agot_canon_enforcement/implementation.py"

# Two dragons, four riders, shaped like AGOT's own files: a rider recorded
# below age ten, a rider AGOT creates after game start, a rider whose canon
# flag nothing adds, and an ordinary rider the tenth birthday reaches.
DRAGON_HISTORY = """dragon_sheepstealer = {
\tname = Sheepstealer
\t8080.1.1 = {
\t\tbirth = yes
\t}
\t8129.12.6 = {
\t\teffect = {
\t\t\tagot_tame_dragon = {
\t\t\t\tTAMER = character:Farseed_1 # Nettles
\t\t\t\tDRAGON = ROOT
\t\t\t}
\t\t}
\t}
}
dragon_syrax = {
\tname = Syrax
\t8104.1.1 = {
\t\teffect = {
\t\t\tagot_tame_dragon = {
\t\t\t\tTAMER = character:Targaryen_63 # Joffrey
\t\t\t\tDRAGON = ROOT
\t\t\t}
\t\t}
\t}
\t8140.1.1 = {
\t\teffect = {
\t\t\tagot_tame_dragon = {
\t\t\t\tTAMER = character:Belaerys_3
\t\t\t\tDRAGON = ROOT
\t\t\t}
\t\t}
\t}
\t8150.1.1 = {
\t\teffect = {
\t\t\tagot_tame_dragon = {
\t\t\t\tTAMER = character:Targaryen_70
\t\t\t\tDRAGON = ROOT
\t\t\t}
\t\t}
\t}
}
"""

TRAIT_TRIGGERS = """is_character_dragon_sheepstealer = {
\tOR = {
\t\thas_inactive_trait = is_dragon_sheepstealer
\t\tAND = {
\t\t\texists = character:dragon_sheepstealer
\t\t\tthis = character:dragon_sheepstealer
\t\t}
\t}
}
is_character_dragon_syrax = {
\tOR = {
\t\thas_inactive_trait = is_dragon_syrax
\t\tAND = {
\t\t\texists = character:dragon_syrax
\t\t\tthis = character:dragon_syrax
\t\t}
\t}
}
"""

CANON_TRIGGERS = """agot_is_canon_rider_dragon_pair = {
\t$RIDER$ = { save_temporary_scope_as = canon_rider }
\t$DRAGON$ = { save_temporary_scope_as = canon_dragon }
\ttrigger_if = {
\t\tlimit = {
\t\t\tscope:canon_dragon = { is_character_dragon_sheepstealer = yes }
\t\t}
\t\tscope:canon_rider = {
\t\t\tOR = {
\t\t\t\thas_character_flag = is_Farseed_1
\t\t\t}
\t\t}
\t}
\ttrigger_else_if = {
\t\tlimit = {
\t\t\tscope:canon_dragon = { is_character_dragon_syrax = yes }
\t\t}
\t\tscope:canon_rider = {
\t\t\tOR = {
\t\t\t\thas_character_flag = is_Targaryen_63
\t\t\t}
\t\t}
\t}
}
"""

INIT_EFFECTS = """agot_init_Targaryen_63 = {
\tadd_character_flag = is_Targaryen_63
}
agot_init_Targaryen_70 = {
\tadd_character_flag = is_Targaryen_70
}
"""

SPAWN_EFFECTS = """spawn_historical_characters_effect = {
\tif = { # Nettles
\t\tcreate_character = { age = 16 }
\t\tadd_character_flag = is_Farseed_1
\t}
}
"""

BIRTHS = {
    "Farseed_1": (8113, 1, 1),
    "Targaryen_63": (8097, 1, 1),
    "Targaryen_70": (8116, 1, 1),
    "Belaerys_3": (8120, 1, 1),
}


def canon_taming_records():
    with generator_function(CANON_ENFORCEMENT, "build_taming_records") as build:
        return build(
            DRAGON_HISTORY,
            CANON_TRIGGERS,
            TRAIT_TRIGGERS,
            INIT_EFFECTS,
            SPAWN_EFFECTS,
            expected_flagless=frozenset({"Belaerys_3"}),
            expected_dynamic=frozenset({"Farseed_1"}),
        )


class CanonDragonTamingTest(unittest.TestCase):
    def test_records_carry_the_recorded_pairing_and_day(self) -> None:
        records = canon_taming_records()
        self.assertEqual(
            [
                (record.rider, record.dragon_token, record.date_text)
                for record in records
            ],
            [
                ("Targaryen_63", "syrax", "8104.1.1"),
                ("Farseed_1", "sheepstealer", "8129.12.6"),
                ("Belaerys_3", "syrax", "8140.1.1"),
                ("Targaryen_70", "syrax", "8150.1.1"),
            ],
        )

    def test_rider_without_a_canon_flag_is_identified_by_character(self) -> None:
        identities = {
            record.rider: record.identity_lines for record in canon_taming_records()
        }
        self.assertEqual(
            identities["Farseed_1"], ("has_character_flag = is_Farseed_1",)
        )
        self.assertEqual(
            identities["Belaerys_3"],
            ("exists = character:Belaerys_3", "this = character:Belaerys_3"),
        )

    def test_event_gates_on_the_recorded_date_and_never_on_age(self) -> None:
        with generator_function(CANON_ENFORCEMENT, "build_canon_taming_event") as build:
            event = build(canon_taming_records())
        # Recorded below age ten, so a minimum-age gate would defer it past the
        # date the history gives.
        self.assertIn("current_date >= 8104.1.1", event)
        self.assertIn(
            "agot_ce_canon_dragon_bond_effect = { DRAGON = sheepstealer }", event
        )
        self.assertNotIn("age >", event)
        self.assertNotIn("age =", event)
        self.assertEqual(event.count("current_date >="), 4)
        self.assertEqual(event.count("\t\tif = {"), 1)
        self.assertEqual(event.count("\t\telse_if = {"), 3)

    def test_trigger_pairs_every_identity_with_its_recorded_date(self) -> None:
        with generator_function(
            CANON_ENFORCEMENT, "build_canon_taming_trigger"
        ) as build:
            trigger = build(canon_taming_records())
        self.assertIn("agot_ce_canon_taming_due_trigger = {", trigger)
        self.assertEqual(trigger.count("AND = {"), 4)
        self.assertIn(
            "\t\t\thas_character_flag = is_Farseed_1\n"
            "\t\t\tcurrent_date >= 8129.12.6\n",
            trigger,
        )

    def test_coverage_names_why_agot_dispatch_misses_a_record(self) -> None:
        records = {record.rider: record for record in canon_taming_records()}
        with generator_function(CANON_ENFORCEMENT, "canon_taming_coverage") as coverage:
            pairs = {("is_farseed_1", "sheepstealer"), ("is_targaryen_63", "syrax")}
            spawn_flags = {"is_Farseed_1"}
            verdicts = {
                rider: coverage(record, BIRTHS, spawn_flags, pairs)[0]
                for rider, record in records.items()
            }
        self.assertEqual(verdicts["Farseed_1"], "created_after_game_start")
        self.assertEqual(verdicts["Belaerys_3"], "no_canon_flag")
        self.assertEqual(verdicts["Targaryen_70"], "unpaired")
        self.assertEqual(verdicts["Targaryen_63"], "before_tenth_birthday")

    def test_generation_fails_when_a_rider_gains_a_second_record(self) -> None:
        history = DRAGON_HISTORY.replace(
            "TAMER = character:Belaerys_3", "TAMER = character:Targaryen_63"
        )
        with (
            generator_function(CANON_ENFORCEMENT, "build_taming_records") as build,
            self.assertRaisesRegex(ValueError, "more than one taming record"),
        ):
            build(history, CANON_TRIGGERS, TRAIT_TRIGGERS, INIT_EFFECTS, SPAWN_EFFECTS)

    def test_generation_fails_when_a_recorded_dragon_has_no_identity(self) -> None:
        with (
            generator_function(CANON_ENFORCEMENT, "build_taming_records") as build,
            self.assertRaisesRegex(ValueError, "no is_character_dragon_"),
        ):
            build(
                DRAGON_HISTORY,
                CANON_TRIGGERS,
                TRAIT_TRIGGERS.replace("dragon_syrax", "dragon_caraxes"),
                INIT_EFFECTS,
                SPAWN_EFFECTS,
            )

    def test_generation_fails_when_a_new_rider_is_created_after_game_start(
        self,
    ) -> None:
        spawn = SPAWN_EFFECTS.replace(
            "add_character_flag = is_Farseed_1",
            "add_character_flag = is_Farseed_1\n"
            "\t\tadd_character_flag = is_Targaryen_70",
        )
        with (
            generator_function(CANON_ENFORCEMENT, "build_taming_records") as build,
            self.assertRaisesRegex(ValueError, "creates after game start changed"),
        ):
            build(
                DRAGON_HISTORY,
                CANON_TRIGGERS,
                TRAIT_TRIGGERS,
                INIT_EFFECTS,
                spawn,
                expected_flagless=frozenset({"Belaerys_3"}),
                expected_dynamic=frozenset({"Farseed_1"}),
            )

    def test_generation_fails_when_a_taming_record_has_no_date(self) -> None:
        history = "dragon_syrax = {\n\tagot_tame_dragon = { TAMER = character:X }\n}\n"
        with (
            generator_function(CANON_ENFORCEMENT, "parse_taming_records") as parse,
            self.assertRaisesRegex(ValueError, "outside a dated block"),
        ):
            parse(history)


class GuardEventDeathsTest(unittest.TestCase):
    """Cover the canon-enforcement guard shared by the AGOT rebase modules."""

    EVENT = (
        "tourney.0001 = {\n"
        "\timmediate = {\n"
        "\t\tdeath = {\n"
        "\t\t\tdeath_reason = death_accident\n"
        "\t\t}\n"
        "\t}\n"
        "\tshow_as_tooltip = {\n"
        "\t\tdeath = {\n"
        "\t\t\tdeath_reason = death_accident\n"
        "\t\t}\n"
        "\t}\n"
        "}\n"
    )

    def test_every_death_is_wrapped_in_the_guard(self) -> None:
        guarded = guard_event_deaths(self.EVENT, "tourney.0001", expected=2)
        self.assertEqual(guarded.count("agot_ce_event_death_protected_trigger = no"), 2)
        self.assertIn("\t\tif = {\n\t\t\tlimit = {", guarded)

    def test_skip_tooltips_leaves_display_copies_alone(self) -> None:
        guarded = guard_event_deaths(
            self.EVENT, "tourney.0001", expected=1, skip_tooltips=True
        )
        self.assertEqual(guarded.count("agot_ce_event_death_protected_trigger = no"), 1)
        tooltip = guarded[guarded.index("show_as_tooltip") :]
        self.assertNotIn("agot_ce_event_death_protected_trigger", tooltip)

    def test_a_miscounted_event_fails_instead_of_guarding_part_of_it(self) -> None:
        # An MFA release that adds a lethal outcome has to stop the generator,
        # not leave the new one silently unguarded.
        with self.assertRaisesRegex(RuntimeError, "expected 1 death effect"):
            guard_event_deaths(self.EVENT, "tourney.0001", expected=1)

    def test_text_outside_the_named_event_is_untouched(self) -> None:
        other = "other.0002 = {\n\timmediate = {\n\t\tdeath = { }\n\t}\n}\n"
        guarded = guard_event_deaths(self.EVENT + other, "tourney.0001", expected=2)
        self.assertIn(other, guarded)


if __name__ == "__main__":
    unittest.main()
