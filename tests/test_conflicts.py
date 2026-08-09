from __future__ import annotations

import json
from pathlib import Path

import pytest

from ck3mm.conflicts import (
    ConflictAnalysisError,
    FailOn,
    ModProvider,
    analyze_conflicts,
    failure_exit_code,
    filter_report,
    make_stable_mod_id,
    sha256_file,
    should_fail,
)
from ck3mm.report import PlaysetRecord, ReportWarning, render_text

FIXTURES = Path(__file__).parent / "fixtures" / "conflicts"


def provider(
    fixture: str,
    stable_id: str,
    position: int,
    *,
    replace_paths: tuple[str, ...] = (),
) -> ModProvider:
    return ModProvider(
        stable_id=stable_id,
        name=fixture.replace("_", " ").title(),
        root=FIXTURES / fixture,
        position=position,
        source="test",
        replace_paths=replace_paths,
    )


def entry_by_path(report: object, path: str):
    return next(entry for entry in report.files if entry.path == path)


def test_same_path_providers_are_load_ordered_and_hashed() -> None:
    hashed: list[str] = []

    def recording_hasher(path: Path) -> str:
        hashed.append(path.name)
        return sha256_file(path)

    report = analyze_conflicts(
        (
            provider("beta", "steam:beta", 20),
            provider("alpha", "steam:alpha", 10),
        ),
        file_hasher=recording_hasher,
    )

    assert [entry.path for entry in report.files] == [
        "common/shared/divergent.txt",
        "common/shared/identical.txt",
    ]
    divergent = report.files[0]
    assert divergent.conflict_kinds == ("same_path",)
    assert [item.mod_id for item in divergent.providers] == [
        "steam:alpha",
        "steam:beta",
    ]
    assert divergent.content_status == "divergent"
    assert divergent.effective_state == "present"
    assert divergent.effective_winner.mod_id == "steam:beta"
    assert all(item.sha256 for item in divergent.providers)
    assert report.files[1].content_status == "identical"
    assert len(hashed) == 4
    assert report.summary.files_scanned == 4


def test_replace_path_can_remove_and_a_later_provider_can_restore() -> None:
    hashed: list[Path] = []

    def recording_hasher(path: Path) -> str:
        hashed.append(path)
        return sha256_file(path)

    report = analyze_conflicts(
        (
            provider("base", "steam:base", 0),
            provider(
                "remover",
                "steam:remover",
                1,
                replace_paths=("history/titles", "map_data"),
            ),
            provider("restorer", "local:mod/restorer.mod", 2),
        ),
        file_hasher=recording_hasher,
    )

    removed = entry_by_path(report, "history/titles/removed.txt")
    assert removed.conflict_kinds == ("replace_path_shadow",)
    assert removed.content_status == "not_applicable"
    assert removed.effective_state == "removed"
    assert removed.effective_winner.kind == "replace_path"
    assert removed.effective_winner.mod_id == "steam:remover"
    assert removed.effective_winner.replace_path == "history/titles"

    restored = entry_by_path(report, "map_data/restored.txt")
    assert restored.conflict_kinds == ("same_path", "replace_path_shadow")
    assert restored.effective_state == "present"
    assert restored.effective_winner.mod_id == "local:mod/restorer.mod"
    assert [owner.mod_id for owner in restored.replace_path_owners] == ["steam:remover"]
    # The single-provider removed file is not read for content comparison.
    assert {path.parent.parent.name for path in hashed} == {"base", "restorer"}


def test_replacing_mod_can_restore_its_own_file_in_the_same_load_step() -> None:
    report = analyze_conflicts(
        (
            provider("combined_base", "steam:base", 0),
            provider(
                "combined_owner",
                "steam:owner",
                1,
                replace_paths=("common",),
            ),
        )
    )

    entry = report.files[0]
    assert entry.conflict_kinds == ("same_path", "replace_path_shadow")
    assert entry.effective_state == "present"
    assert entry.effective_winner.mod_id == "steam:owner"


def test_replace_path_before_first_provider_does_not_create_a_shadow() -> None:
    calls = 0

    def forbidden_hasher(path: Path) -> str:
        nonlocal calls
        calls += 1
        return sha256_file(path)

    report = analyze_conflicts(
        (
            provider(
                "early_replacer",
                "steam:early",
                0,
                replace_paths=("gfx",),
            ),
            provider("late_provider", "steam:late", 1),
        ),
        include_all=True,
        file_hasher=forbidden_hasher,
    )

    assert report.summary.conflicts == 0
    assert calls == 0
    entry = report.files[0]
    assert entry.conflict_kinds == ()
    assert entry.effective_state == "present"
    assert entry.effective_winner.mod_id == "steam:late"
    assert entry.replace_path_owners[0].mod_id == "steam:early"


def test_unreadable_overlap_has_no_host_error_or_path() -> None:
    def unreadable_beta(path: Path) -> str:
        if path.parent.parent.parent.name == "beta":
            raise PermissionError("synthetic unreadable fixture")
        return sha256_file(path)

    report = analyze_conflicts(
        (
            provider("alpha", "steam:alpha", 0),
            provider("beta", "steam:beta", 1),
        ),
        file_hasher=unreadable_beta,
    )

    assert {entry.content_status for entry in report.files} == {"unreadable"}
    assert report.summary.unreadable == 2
    assert any(item.readable is False for item in report.files[0].providers)
    serialized = report.to_json()
    assert "synthetic unreadable fixture" not in serialized
    assert str(FIXTURES) not in serialized


def test_filters_include_replace_path_owners_and_preserve_summary_only_counts() -> None:
    report = analyze_conflicts(
        (
            provider("base", "steam:base", 0),
            provider(
                "remover",
                "steam:remover",
                1,
                replace_paths=("history/titles", "map_data"),
            ),
            provider("restorer", "steam:restorer", 2),
        )
    )

    filtered = filter_report(
        report,
        involving="remover",
        include_prefixes=("history", "map_data"),
        exclude_prefixes=("map_data",),
        summary_only=True,
    )
    assert filtered.files == ()
    assert filtered.summary.files_reported == 1
    assert filtered.summary.conflicts == 1
    assert filtered.summary.replace_path_shadow == 1
    assert should_fail(filtered, "any")


def test_fail_on_policies_are_opt_in_and_use_structured_counts() -> None:
    report = analyze_conflicts(
        (
            provider("alpha", "steam:alpha", 0),
            provider("beta", "steam:beta", 1),
        ),
        warnings=(
            ReportWarning(
                code="enabled_mod_missing",
                message="An enabled playset mod could not be resolved.",
                mod_id="steam:missing",
            ),
        ),
    )

    assert not should_fail(report, None)
    assert should_fail(report, FailOn.DIVERGENT)
    assert should_fail(report, "any")
    assert should_fail(report, "missing")
    assert failure_exit_code(report, "divergent") == 1
    with pytest.raises(ValueError, match="unknown fail-on policy"):
        should_fail(report, "identical")


def test_json_v2_is_deterministic_and_omits_provider_roots() -> None:
    playset = PlaysetRecord(
        name="Synthetic",
        selection_source="fixture",
        mods_total=2,
        mods_enabled=2,
    )
    mods = (
        provider("alpha", "steam:alpha", 0),
        provider("beta", "steam:beta", 1),
    )

    first = analyze_conflicts(mods, playset=playset).to_json()
    second = analyze_conflicts(tuple(reversed(mods)), playset=playset).to_json()

    assert first == second
    assert str(FIXTURES) not in first
    payload = json.loads(first)
    assert payload["schemaVersion"] == 2
    assert payload["playset"]["name"] == "Synthetic"
    assert [mod["id"] for mod in payload["mods"]] == [
        "steam:alpha",
        "steam:beta",
    ]
    assert "root" not in first.lower()
    assert render_text(analyze_conflicts(mods)).startswith("Summary\n")


def test_stable_ids_and_provider_validation() -> None:
    assert (
        make_stable_mod_id(game_registry_id=r"mod\local.mod", steam_id="ignored")
        == "local:mod/local.mod"
    )
    assert make_stable_mod_id(steam_id="123") == "steam:123"
    assert make_stable_mod_id(pdx_id="abc") == "pdx:abc"
    assert make_stable_mod_id(name="  Name   Only ") == "name:Name Only"
    with pytest.raises(ValueError, match="relative path"):
        make_stable_mod_id(game_registry_id="/tmp/local.mod")
    with pytest.raises(ValueError, match="relative path"):
        make_stable_mod_id(game_registry_id=r"C:\mods\local.mod")

    duplicate = provider("alpha", "steam:same", 0)
    with pytest.raises(ConflictAnalysisError, match="duplicate stable mod identity"):
        analyze_conflicts((duplicate, provider("beta", "steam:same", 1)))
