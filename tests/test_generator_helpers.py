from __future__ import annotations

import re
import unittest
from pathlib import Path

from gen.__main__ import load_entrypoint
from gen.data import csv_bytes
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

    def test_map_locator_parser_keeps_prefix_suffix_and_ids(self) -> None:
        text = (
            "locator = {\n"
            "\tinstances = {\n"
            "\t\t{\n\t\t\tid = 3\n\t\t\tposition={ 1 0 2 }\n\t\t}\n"
            "\t\t{\n\t\t\tid = 8\n\t\t\tposition={ 4 0 5 }\n\t\t}\n"
            "\t}\n}\n"
        )
        with generator_function(
            "workspace/agot_now_lov_ee_map_compatch/map_merge.py",
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
            "workspace/agot_now_lov_ee_map_compatch/map_merge.py",
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
                "workspace/agot_now_lov_ee_map_compatch/map_merge.py",
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
            "workspace/agot_now_lov_ee_map_compatch/map_merge.py",
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
            "workspace/agot_now_lov_ee_map_compatch/map_merge.py",
            "province_ids_from_landed_titles",
        ) as province_ids:
            self.assertEqual(province_ids(source), (7, 9))

    def test_map_quarantine_is_deterministic_and_non_passable(self) -> None:
        source = "sea_zones = LIST { 2 }\nimpassable_mountains = LIST { 3 }\n"
        with (
            generator_function(
                "workspace/agot_now_lov_ee_map_compatch/map_merge.py",
                "append_impassable_quarantine",
            ) as append_quarantine,
            generator_function(
                "workspace/agot_now_lov_ee_map_compatch/map_merge.py",
                "land_provinces",
            ) as land_provinces,
        ):
            output = append_quarantine(source, (4, 5, 6), chunk_size=2)
            self.assertIn("impassable_mountains = LIST { 4 5 }", output)
            self.assertIn("impassable_mountains = LIST { 6 }", output)
            self.assertEqual(land_provinces(output, frozenset(range(1, 7))), {1})

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
            "workspace/agot_now_lov_ee_map_compatch/map_merge.py",
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
            "workspace/agot_now_lov_ee_lore_governments/implementation.py",
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
                "workspace/agot_now_lov_ee_lore_governments/implementation.py",
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
            "workspace/agot_now_lov_ee_world_data/implementation.py",
            "parse_top_level_blocks",
        ) as parse_blocks:
            blocks = parse_blocks(source)
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


if __name__ == "__main__":
    unittest.main()
