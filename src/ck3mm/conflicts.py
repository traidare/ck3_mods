"""Load-aware CK3 mod conflict analysis."""

from __future__ import annotations

import posixpath
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from .hashing import sha256_file
from .report import (
    ConflictReport,
    EffectiveWinner,
    FileEntry,
    FileProvider,
    ModRecord,
    PlaysetRecord,
    ReplacePathOwner,
    ReportWarning,
    report_with_files,
    summarize,
)

_CONFLICT_KIND_ORDER = ("same_path", "replace_path_shadow")


class ConflictAnalysisError(RuntimeError):
    """Raised when a provider tree cannot be analyzed safely."""


class FailOn(StrEnum):
    DIVERGENT = "divergent"
    ANY = "any"
    MISSING = "missing"


@dataclass(frozen=True, slots=True)
class ModProvider:
    """A resolved mod root at one position in effective load order."""

    stable_id: str
    name: str
    root: Path
    position: int
    source: str = ""
    replace_paths: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.stable_id.strip():
            raise ValueError("stable_id must not be empty")
        if not self.name.strip():
            raise ValueError("provider name must not be empty")
        if self.position < 0:
            raise ValueError("provider position must not be negative")
        normalized = tuple(
            sorted({_normalize_relative_path(path) for path in self.replace_paths})
        )
        if "" in normalized:
            raise ValueError("replace_path must not refer to the mod root")
        object.__setattr__(self, "root", Path(self.root))
        object.__setattr__(self, "replace_paths", normalized)

    def to_record(self) -> ModRecord:
        return ModRecord(
            stable_id=self.stable_id,
            name=self.name,
            position=self.position,
            source=self.source,
            replace_paths=self.replace_paths,
        )


def make_stable_mod_id(
    *,
    game_registry_id: str = "",
    steam_id: str = "",
    pdx_id: str = "",
    name: str = "",
) -> str:
    """Build the same portable identity hierarchy used by playset records."""

    if game_registry_id:
        registry_id = _normalize_relative_path(game_registry_id)
        if registry_id:
            return "local:" + registry_id
    if normalized_steam_id := steam_id.strip():
        return "steam:" + normalized_steam_id
    if normalized_pdx_id := pdx_id.strip():
        return "pdx:" + normalized_pdx_id
    if normalized_name := " ".join(name.split()):
        return "name:" + normalized_name
    raise ValueError("at least one mod identifier is required")


def analyze_conflicts(
    providers: Sequence[ModProvider],
    *,
    playset: PlaysetRecord | None = None,
    warnings: Iterable[ReportWarning] = (),
    include_all: bool = False,
    file_hasher: Callable[[Path], str] = sha256_file,
) -> ConflictReport:
    """Analyze provider trees according to their effective CK3 load order.

    A mod's ``replace_path`` operation is applied immediately before files from
    that same mod. Consequently, a mod may remove an earlier file and restore
    its own version in one load step.
    """

    ordered = tuple(sorted(providers, key=lambda mod: (mod.position, mod.stable_id)))
    _validate_providers(ordered)
    provider_files, files_scanned = _scan_provider_files(ordered)
    report_warnings = tuple(sorted(warnings, key=_warning_sort_key))

    entries = tuple(
        _analyze_path(
            relative_path,
            ordered,
            provider_files[relative_path],
            file_hasher=file_hasher,
        )
        for relative_path in sorted(provider_files)
    )
    if not include_all:
        entries = tuple(entry for entry in entries if entry.is_conflict)

    mods = tuple(mod.to_record() for mod in ordered)
    return ConflictReport(
        playset=playset,
        summary=summarize(
            entries,
            mods_analyzed=len(mods),
            files_scanned=files_scanned,
            warnings=report_warnings,
        ),
        warnings=report_warnings,
        mods=mods,
        files=entries,
    )


def filter_report(
    report: ConflictReport,
    *,
    involving: str = "",
    include_prefixes: Iterable[str] = (),
    exclude_prefixes: Iterable[str] = (),
    conflicts_only: bool = False,
    summary_only: bool = False,
) -> ConflictReport:
    """Apply CLI-style filters while rebuilding all report-level counts."""

    included = _normalize_prefixes(include_prefixes)
    excluded = _normalize_prefixes(exclude_prefixes)
    involving_ids = _resolve_involving_ids(report, involving)

    entries = (
        entry
        for entry in report.files
        if (not conflicts_only or entry.is_conflict)
        and _matches_prefixes(entry.path, included, excluded)
        and _entry_involves(entry, involving_ids)
    )
    return report_with_files(report, entries, summary_only=summary_only)


def should_fail(report: ConflictReport, policy: FailOn | str | None) -> bool:
    """Return whether a report violates the requested opt-in CI policy."""

    if policy is None or policy == "":
        return False
    try:
        selected = policy if isinstance(policy, FailOn) else FailOn(policy)
    except ValueError as error:
        choices = ", ".join(item.value for item in FailOn)
        raise ValueError(
            f"unknown fail-on policy {policy!r}; choose {choices}"
        ) from error
    if selected is FailOn.DIVERGENT:
        return report.summary.divergent > 0
    if selected is FailOn.ANY:
        return report.summary.conflicts > 0
    return report.summary.mods_missing > 0


def failure_exit_code(report: ConflictReport, policy: FailOn | str | None) -> int:
    return int(should_fail(report, policy))


def _validate_providers(providers: Sequence[ModProvider]) -> None:
    seen: set[str] = set()
    for provider in providers:
        if provider.stable_id in seen:
            raise ConflictAnalysisError(
                f"duplicate stable mod identity: {provider.stable_id}"
            )
        seen.add(provider.stable_id)
        if not provider.root.is_dir():
            raise ConflictAnalysisError(
                f"provider root is not a readable directory: {provider.stable_id}"
            )


def _scan_provider_files(
    providers: Sequence[ModProvider],
) -> tuple[dict[str, dict[str, Path]], int]:
    by_path: dict[str, dict[str, Path]] = {}
    files_scanned = 0
    for provider in providers:
        try:
            candidates = sorted(
                provider.root.rglob("*"),
                key=lambda path: path.relative_to(provider.root).as_posix(),
            )
        except OSError as error:
            raise ConflictAnalysisError(
                f"could not enumerate provider {provider.stable_id}: {error.strerror}"
            ) from error
        for path in candidates:
            relative = path.relative_to(provider.root)
            if any(part.startswith(".") for part in relative.parts):
                continue
            # CK3 payloads live in subdirectories. Root files are descriptors or
            # repository metadata and must not participate in conflict reports.
            if len(relative.parts) == 1 or not path.is_file():
                continue
            relative_path = _normalize_relative_path(relative.as_posix())
            files_scanned += 1
            by_path.setdefault(relative_path, {})[provider.stable_id] = path
    return by_path, files_scanned


def _analyze_path(
    relative_path: str,
    providers: Sequence[ModProvider],
    physical_files: dict[str, Path],
    *,
    file_hasher: Callable[[Path], str],
) -> FileEntry:
    file_mods = tuple(
        provider for provider in providers if provider.stable_id in physical_files
    )
    same_path = len(file_mods) > 1
    replacement_owners: list[ReplacePathOwner] = []
    current_provider: ModProvider | None = None
    last_replacement: tuple[ModProvider, str] | None = None
    replace_path_shadow = False

    for provider in providers:
        matching_paths = tuple(
            path
            for path in provider.replace_paths
            if _replace_path_matches(relative_path, path)
        )
        if matching_paths:
            replacement_owners.append(
                ReplacePathOwner(
                    mod_id=provider.stable_id,
                    position=provider.position,
                    replace_paths=matching_paths,
                )
            )
            if current_provider is not None:
                replace_path_shadow = True
            current_provider = None
            last_replacement = (
                provider,
                min(matching_paths, key=lambda path: (-len(path), path)),
            )
        if provider.stable_id in physical_files:
            current_provider = provider

    kinds = tuple(
        kind
        for kind, applies in zip(
            _CONFLICT_KIND_ORDER,
            (same_path, replace_path_shadow),
            strict=True,
        )
        if applies
    )
    content_status, file_providers = _content_analysis(
        file_mods,
        physical_files,
        same_path=same_path,
        file_hasher=file_hasher,
    )

    if current_provider is not None:
        effective_state = "present"
        effective_winner = EffectiveWinner(
            kind="provider",
            mod_id=current_provider.stable_id,
            position=current_provider.position,
            description=(
                f"{current_provider.name} is the last provider after load-order "
                "replace_path processing."
            ),
        )
    else:
        if last_replacement is None:  # pragma: no cover - every path has a provider
            raise AssertionError("a known file has neither provider nor replacement")
        replacement_mod, replace_path = last_replacement
        effective_state = "removed"
        effective_winner = EffectiveWinner(
            kind="replace_path",
            mod_id=replacement_mod.stable_id,
            position=replacement_mod.position,
            replace_path=replace_path,
            description=(
                f"{replacement_mod.name} is the last applicable replace_path owner; "
                "no later provider restores the file."
            ),
        )

    return FileEntry(
        path=relative_path,
        category=relative_path.partition("/")[0],
        conflict_kinds=kinds,
        providers=file_providers,
        replace_path_owners=tuple(replacement_owners),
        effective_state=effective_state,
        effective_winner=effective_winner,
        content_status=content_status,
    )


def _content_analysis(
    providers: Sequence[ModProvider],
    physical_files: dict[str, Path],
    *,
    same_path: bool,
    file_hasher: Callable[[Path], str],
) -> tuple[str, tuple[FileProvider, ...]]:
    if not same_path:
        return "not_applicable", tuple(
            FileProvider(mod_id=provider.stable_id, position=provider.position)
            for provider in providers
        )

    hashes: list[str] = []
    records: list[FileProvider] = []
    unreadable = False
    for provider in providers:
        try:
            digest = file_hasher(physical_files[provider.stable_id])
        except OSError:
            unreadable = True
            records.append(
                FileProvider(
                    mod_id=provider.stable_id,
                    position=provider.position,
                    readable=False,
                )
            )
            continue
        hashes.append(digest)
        records.append(
            FileProvider(
                mod_id=provider.stable_id,
                position=provider.position,
                sha256=digest,
                readable=True,
            )
        )
    if unreadable:
        status = "unreadable"
    elif len(set(hashes)) == 1:
        status = "identical"
    else:
        status = "divergent"
    return status, tuple(records)


def _normalize_relative_path(path: str) -> str:
    candidate = path.strip().replace("\\", "/")
    if not candidate:
        return ""
    normalized = posixpath.normpath(candidate).removeprefix("./").rstrip("/")
    if (
        normalized.startswith("/")
        or (len(normalized) >= 3 and normalized[1:3] == ":/")
        or normalized == ".."
        or normalized.startswith("../")
    ):
        raise ValueError(f"expected a repository-independent relative path: {path!r}")
    return normalized


def _replace_path_matches(path: str, replace_path: str) -> bool:
    return path == replace_path or path.startswith(replace_path + "/")


def _normalize_prefixes(prefixes: Iterable[str]) -> tuple[str, ...]:
    return tuple(
        sorted(
            {
                normalized
                for prefix in prefixes
                if (normalized := _normalize_relative_path(prefix))
            }
        )
    )


def _matches_prefixes(
    path: str, include_prefixes: tuple[str, ...], exclude_prefixes: tuple[str, ...]
) -> bool:
    if any(path.startswith(prefix) for prefix in exclude_prefixes):
        return False
    return not include_prefixes or any(
        path.startswith(prefix) for prefix in include_prefixes
    )


def _resolve_involving_ids(report: ConflictReport, involving: str) -> frozenset[str]:
    if not involving:
        return frozenset()
    matches: set[str] = set()
    for mod in report.mods:
        identity_type, separator, identity_value = mod.stable_id.partition(":")
        aliases = {mod.stable_id, mod.name}
        if separator:
            aliases.add(identity_value)
        if identity_type == "local":
            registry_name = posixpath.basename(identity_value)
            aliases.add(registry_name)
            aliases.add(registry_name.removesuffix(".mod"))
        if involving in aliases:
            matches.add(mod.stable_id)
    return frozenset(matches or {involving})


def _entry_involves(entry: FileEntry, involving_ids: frozenset[str]) -> bool:
    if not involving_ids:
        return True
    referenced = {
        *(provider.mod_id for provider in entry.providers),
        *(owner.mod_id for owner in entry.replace_path_owners),
        entry.effective_winner.mod_id,
    }
    return not referenced.isdisjoint(involving_ids)


def _warning_sort_key(warning: ReportWarning) -> tuple[int, str, str, str]:
    position = warning.position if warning.position is not None else 2**63 - 1
    return position, warning.code, warning.mod_id, warning.message
