"""Deterministic, portable conflict report models."""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass, replace
from typing import Any

SCHEMA_VERSION = 2


@dataclass(frozen=True, slots=True)
class PlaysetRecord:
    """Path-free metadata identifying the selected playset."""

    name: str
    game: str = "ck3"
    selection_source: str = "unknown"
    mods_total: int = 0
    mods_enabled: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "game": self.game,
            "name": self.name,
            "selectionSource": self.selection_source,
            "modsTotal": self.mods_total,
            "modsEnabled": self.mods_enabled,
        }


@dataclass(frozen=True, slots=True)
class ModRecord:
    """Public mod metadata; deliberately excludes its filesystem root."""

    stable_id: str
    name: str
    position: int
    source: str = ""
    replace_paths: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "id": self.stable_id,
            "name": self.name,
            "position": self.position,
        }
        if self.source:
            result["source"] = self.source
        if self.replace_paths:
            result["replacePaths"] = list(self.replace_paths)
        return result


@dataclass(frozen=True, slots=True)
class ReportWarning:
    code: str
    message: str
    mod_id: str = ""
    position: int | None = None

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {"code": self.code, "message": self.message}
        if self.mod_id:
            result["modId"] = self.mod_id
        if self.position is not None:
            result["position"] = self.position
        return result


@dataclass(frozen=True, slots=True)
class FileProvider:
    """One mod that physically contains a CK3-relative file."""

    mod_id: str
    position: int
    sha256: str | None = None
    readable: bool | None = None

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "modId": self.mod_id,
            "position": self.position,
        }
        if self.readable is not None:
            result["readable"] = self.readable
        if self.sha256 is not None:
            result["sha256"] = self.sha256
        return result


@dataclass(frozen=True, slots=True)
class ReplacePathOwner:
    """A mod whose replace_path declarations apply to a file."""

    mod_id: str
    position: int
    replace_paths: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "modId": self.mod_id,
            "position": self.position,
            "replacePaths": list(self.replace_paths),
        }


@dataclass(frozen=True, slots=True)
class EffectiveWinner:
    """Describes observed load behavior without judging compatibility."""

    kind: str
    mod_id: str
    position: int
    description: str
    replace_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "kind": self.kind,
            "modId": self.mod_id,
            "position": self.position,
            "description": self.description,
        }
        if self.replace_path is not None:
            result["replacePath"] = self.replace_path
        return result


@dataclass(frozen=True, slots=True)
class FileEntry:
    path: str
    category: str
    conflict_kinds: tuple[str, ...]
    providers: tuple[FileProvider, ...]
    replace_path_owners: tuple[ReplacePathOwner, ...]
    effective_state: str
    effective_winner: EffectiveWinner
    content_status: str

    @property
    def is_conflict(self) -> bool:
        return bool(self.conflict_kinds)

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "category": self.category,
            "conflictKinds": list(self.conflict_kinds),
            "providers": [provider.to_dict() for provider in self.providers],
            "replacePathOwners": [
                owner.to_dict() for owner in self.replace_path_owners
            ],
            "effectiveState": self.effective_state,
            "effectiveWinner": self.effective_winner.to_dict(),
            "contentStatus": self.content_status,
        }


@dataclass(frozen=True, slots=True)
class ReportSummary:
    mods_analyzed: int
    mods_missing: int
    files_scanned: int
    files_reported: int
    conflicts: int
    same_path: int
    replace_path_shadow: int
    identical: int
    divergent: int
    unreadable: int
    effective_present: int
    effective_removed: int

    def to_dict(self) -> dict[str, int]:
        return {
            "modsAnalyzed": self.mods_analyzed,
            "modsMissing": self.mods_missing,
            "filesScanned": self.files_scanned,
            "filesReported": self.files_reported,
            "conflicts": self.conflicts,
            "samePath": self.same_path,
            "replacePathShadow": self.replace_path_shadow,
            "identical": self.identical,
            "divergent": self.divergent,
            "unreadable": self.unreadable,
            "effectivePresent": self.effective_present,
            "effectiveRemoved": self.effective_removed,
        }


@dataclass(frozen=True, slots=True)
class ConflictReport:
    playset: PlaysetRecord | None
    summary: ReportSummary
    warnings: tuple[ReportWarning, ...]
    mods: tuple[ModRecord, ...]
    files: tuple[FileEntry, ...]
    schema_version: int = SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "schemaVersion": self.schema_version,
            "playset": self.playset.to_dict() if self.playset is not None else None,
            "summary": self.summary.to_dict(),
            "warnings": [warning.to_dict() for warning in self.warnings],
            "mods": [mod.to_dict() for mod in self.mods],
            "files": [entry.to_dict() for entry in self.files],
        }

    def to_json(self, *, indent: int | None = 2) -> str:
        """Serialize without timestamps or host-specific filesystem paths."""

        return (
            json.dumps(
                self.to_dict(),
                ensure_ascii=False,
                indent=indent,
                sort_keys=True,
            )
            + "\n"
        )


_MISSING_WARNING_CODES = frozenset(
    {
        "enabled_mod_missing",
        "enabled_local_mod_missing",
        "local_mod_directory_unconfigured",
        "mod_missing",
    }
)


def summarize(
    files: Iterable[FileEntry],
    *,
    mods_analyzed: int,
    files_scanned: int,
    warnings: Iterable[ReportWarning] = (),
) -> ReportSummary:
    entries = tuple(files)
    report_warnings = tuple(warnings)
    return ReportSummary(
        mods_analyzed=mods_analyzed,
        mods_missing=sum(
            warning.code in _MISSING_WARNING_CODES for warning in report_warnings
        ),
        files_scanned=files_scanned,
        files_reported=len(entries),
        conflicts=sum(entry.is_conflict for entry in entries),
        same_path=sum("same_path" in entry.conflict_kinds for entry in entries),
        replace_path_shadow=sum(
            "replace_path_shadow" in entry.conflict_kinds for entry in entries
        ),
        identical=sum(entry.content_status == "identical" for entry in entries),
        divergent=sum(entry.content_status == "divergent" for entry in entries),
        unreadable=sum(entry.content_status == "unreadable" for entry in entries),
        effective_present=sum(entry.effective_state == "present" for entry in entries),
        effective_removed=sum(entry.effective_state == "removed" for entry in entries),
    )


def report_with_files(
    report: ConflictReport,
    files: Iterable[FileEntry],
    *,
    summary_only: bool = False,
) -> ConflictReport:
    """Replace report entries while retaining scan-wide and missing-mod counts."""

    entries = tuple(files)
    summary = summarize(
        entries,
        mods_analyzed=len(report.mods),
        files_scanned=report.summary.files_scanned,
        warnings=report.warnings,
    )
    return replace(report, files=() if summary_only else entries, summary=summary)


def render_text(report: ConflictReport) -> str:
    """Render the same v2 model as a compact, deterministic text report."""

    summary = report.summary
    lines = [
        "Summary",
        f"  Mods analyzed: {summary.mods_analyzed}",
        f"  Mods missing: {summary.mods_missing}",
        f"  Files scanned: {summary.files_scanned}",
        f"  Files reported: {summary.files_reported}",
        f"  Conflicts: {summary.conflicts}",
        f"  Same path: {summary.same_path}",
        f"  Replace path shadow: {summary.replace_path_shadow}",
        f"  Divergent: {summary.divergent}",
    ]
    if report.warnings:
        lines.extend(("", "Warnings"))
        lines.extend(
            f"  [{warning.code}] {warning.message}" for warning in report.warnings
        )
    if report.files:
        lines.extend(("", "Files"))
        for entry in report.files:
            kinds = ", ".join(entry.conflict_kinds) or "none"
            lines.append(f"  {entry.path} [{kinds}] -> {entry.effective_state}")
            lines.extend(
                f"    {provider.mod_id} [{provider.position}]"
                for provider in entry.providers
            )
    return "\n".join(lines) + "\n"
