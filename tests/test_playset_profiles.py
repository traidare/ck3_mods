"""Invariants of the three AGOT playset compatch modules.

A profile is selected by enabling or disabling whole modules alongside the
optional Workshop families they integrate, so two properties have to hold no
matter how the generators change: a module may only read parents its own profile
enables, and a path two of them both ship must be won by the later one.
"""

from __future__ import annotations

import json
import tomllib
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

CORE = "agot_playset_compatch"
LOV = "agot_playset_lov_compatch"
EE = "agot_playset_lov_ee_compatch"
MODULES = (CORE, LOV, EE)

# Workshop ids of the optional families, keyed by the earliest module allowed to
# read them. A module may read its own family and every family below it.
LOV_FAMILY = frozenset(
    {"3403938445", "3772292501", "3788296332", "3773616784", "3766038754"}
)
EE_FAMILY = frozenset({"3682802751", "3768149491", "3773608127"})

ALLOWED_FAMILIES = {
    CORE: frozenset(),
    LOV: LOV_FAMILY,
    EE: LOV_FAMILY | EE_FAMILY,
}

NON_PAYLOAD = {"descriptor.mod", "README.md", "thumbnail.png"}


def payload(slug: str) -> set[str]:
    root = REPO / "mods" / slug
    return {
        str(path.relative_to(root))
        for path in root.rglob("*")
        if path.is_file() and path.name not in NON_PAYLOAD
    }


def locked_workshop_ids(slug: str) -> set[str]:
    """Every Workshop root the module's last generator run actually read."""
    lock = json.loads((REPO / "workspace" / slug / "sources.lock.json").read_text())
    ids: set[str] = set()
    for entry in json.dumps(lock).split('"'):
        if entry.startswith("workshop/"):
            head = entry.split("/", 2)[1]
            if head.isdigit():
                ids.add(head)
    return ids


def declared_workshop_ids(slug: str) -> set[str]:
    manifest = tomllib.loads((REPO / "workspace" / slug / "mod.toml").read_text())
    return {
        str(source["item_id"])
        for source in manifest.get("sources", [])
        if source.get("kind") == "workshop"
    }


class SourceClosureTest(unittest.TestCase):
    def test_modules_read_no_parent_their_profile_disables(self) -> None:
        for slug in MODULES:
            with self.subTest(module=slug):
                forbidden = (LOV_FAMILY | EE_FAMILY) - ALLOWED_FAMILIES[slug]
                self.assertEqual(
                    locked_workshop_ids(slug) & forbidden,
                    set(),
                    f"{slug} read a Workshop parent its profile does not enable",
                )

    def test_manifests_declare_no_parent_their_profile_disables(self) -> None:
        for slug in MODULES:
            with self.subTest(module=slug):
                forbidden = (LOV_FAMILY | EE_FAMILY) - ALLOWED_FAMILIES[slug]
                self.assertEqual(
                    declared_workshop_ids(slug) & forbidden,
                    set(),
                    f"{slug} declares a Workshop parent its profile does not enable",
                )


class OwnershipTest(unittest.TestCase):
    def test_every_module_ships_payload(self) -> None:
        for slug in MODULES:
            with self.subTest(module=slug):
                self.assertTrue(payload(slug), f"{slug} ships no payload")

    def test_essos_module_restates_only_legacy_of_valyria_paths(self) -> None:
        # The Essos module is never enabled without the LoV one, so a path it
        # shares with the always-on module alone would be an ownership mistake:
        # the LoV copy would be effective in one profile and not in another.
        self.assertEqual(
            payload(CORE) & payload(EE) - payload(LOV),
            set(),
            "the Essos module restates an always-on path the LoV one does not own",
        )

    def test_shared_paths_are_declared_by_the_later_module(self) -> None:
        # A path both ship is only resolved correctly if the later module names
        # it in its own manifest; otherwise a regeneration could drop it and
        # silently hand the profile back to the earlier module's copy.
        for lower, higher in ((CORE, LOV), (LOV, EE)):
            manifest = tomllib.loads(
                (REPO / "workspace" / higher / "mod.toml").read_text()
            )
            owned = manifest["generator"]["owned_outputs"]
            for relative in sorted(payload(lower) & payload(higher)):
                with self.subTest(lower=lower, higher=higher, path=relative):
                    self.assertTrue(
                        any(
                            relative == entry or relative.startswith(f"{entry}/")
                            for entry in owned
                        ),
                        f"{higher} ships {relative} without declaring it",
                    )


class TigerConfigTest(unittest.TestCase):
    def test_later_modules_validate_against_the_ones_beneath_them(self) -> None:
        expected = {CORE: (), LOV: (CORE,), EE: (CORE, LOV)}
        for slug, beneath in expected.items():
            config = (REPO / "workspace" / slug / "ck3-tiger.conf").read_text()
            for lower in beneath:
                with self.subTest(module=slug, beneath=lower):
                    self.assertIn(
                        f"mods/{lower}/descriptor.mod",
                        config,
                        f"{slug} does not load {lower} for validation",
                    )

    def test_configs_load_no_parent_their_profile_disables(self) -> None:
        for slug in MODULES:
            config = (REPO / "workspace" / slug / "ck3-tiger.conf").read_text()
            forbidden = (LOV_FAMILY | EE_FAMILY) - ALLOWED_FAMILIES[slug]
            for workshop_id in sorted(forbidden):
                with self.subTest(module=slug, workshop_id=workshop_id):
                    self.assertNotIn(
                        f'workshop_id = "{workshop_id}"',
                        config,
                        f"{slug} validates against a parent its profile disables",
                    )


if __name__ == "__main__":
    unittest.main()
