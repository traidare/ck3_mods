"""Resolve portable playset entries into installed CK3 mod provider roots."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from .conflicts import ModProvider
from .descriptors import Descriptor, DescriptorError, load_descriptor
from .playsets import Playset, PlaysetMod
from .report import PlaysetRecord, ReportWarning


@dataclass(frozen=True, slots=True)
class Discovery:
    providers: tuple[ModProvider, ...]
    warnings: tuple[ReportWarning, ...]
    playset: PlaysetRecord


def _read_descriptor(path: Path, label: str) -> Descriptor:
    """Read a descriptor while keeping host paths out of public warnings."""
    if not path.is_file():
        raise DescriptorError(f"{label} is missing")
    try:
        return load_descriptor(path)
    except DescriptorError as error:
        if isinstance(error.__cause__, OSError):
            raise DescriptorError(f"{label} is unreadable") from error
        raise DescriptorError(f"{label} is invalid: {error}") from error


def _safe_registry_path(paradox_dir: Path, registry_id: str) -> Path:
    relative = PurePosixPath(registry_id.replace("\\", "/"))
    if relative.is_absolute() or ".." in relative.parts or not relative.parts:
        raise DescriptorError(f"unsafe local registry ID: {registry_id!r}")
    path = (paradox_dir / Path(*relative.parts)).resolve(strict=False)
    root = paradox_dir.resolve(strict=False)
    if not path.is_relative_to(root):
        raise DescriptorError(
            f"local registry ID escapes CK3_PARADOX_DIR: {registry_id!r}"
        )
    return path


def _payload_path(descriptor: Descriptor, paradox_dir: Path) -> Path:
    raw_path = descriptor.value("path")
    if not raw_path:
        raise DescriptorError("local Launcher descriptor has no path field")
    path = Path(raw_path).expanduser()
    if not path.is_absolute():
        path = paradox_dir / path
    resolved = path.resolve(strict=False)
    if not resolved.is_dir():
        fallback = (paradox_dir / "mod" / path.name).resolve(strict=False)
        if fallback.is_dir():
            return fallback
        raise DescriptorError("configured local mod payload is missing")
    return resolved


def _merge_replace_paths(*descriptors: Descriptor) -> tuple[str, ...]:
    return tuple(
        sorted(
            {
                path.strip().replace("\\", "/").strip("/")
                for descriptor in descriptors
                for path in descriptor.replace_paths
                if path.strip().strip("/")
            }
        )
    )


def _workshop_provider(mod: PlaysetMod, workshop_dir: Path) -> ModProvider:
    if not mod.steam_id:
        raise DescriptorError("Workshop playset entry has no Steam ID")
    root = (workshop_dir / mod.steam_id).resolve(strict=False)
    descriptor_path = root / "descriptor.mod"
    descriptor = _read_descriptor(descriptor_path, "Workshop descriptor.mod")
    return ModProvider(
        stable_id=mod.stable_id,
        name=descriptor.name if descriptor.values("name") else mod.display_name,
        root=root,
        position=mod.position,
        source="steam",
        replace_paths=_merge_replace_paths(descriptor),
    )


def _local_provider(mod: PlaysetMod, paradox_dir: Path) -> ModProvider:
    if not mod.game_registry_id:
        raise DescriptorError("local playset entry has no gameRegistryId")
    launcher_descriptor = _read_descriptor(
        _safe_registry_path(paradox_dir, mod.game_registry_id),
        "local Launcher descriptor",
    )
    root = _payload_path(launcher_descriptor, paradox_dir)
    payload_path = root / "descriptor.mod"
    payload_descriptor = (
        _read_descriptor(payload_path, "local payload descriptor.mod")
        if payload_path.is_file()
        else launcher_descriptor
    )
    return ModProvider(
        stable_id=mod.stable_id,
        name=(
            payload_descriptor.name
            if payload_descriptor.values("name")
            else mod.display_name
        ),
        root=root,
        position=mod.position,
        source="local",
        replace_paths=_merge_replace_paths(
            launcher_descriptor,
            payload_descriptor,
        ),
    )


def discover_playset(
    playset: Playset,
    *,
    workshop_dir: Path,
    paradox_dir: Path,
) -> Discovery:
    """Resolve enabled playset entries without leaking roots into reports."""

    providers: list[ModProvider] = []
    warnings: list[ReportWarning] = []
    for mod in playset.enabled_mods:
        try:
            if mod.source == "local" or mod.game_registry_id:
                provider = _local_provider(mod, paradox_dir)
            elif mod.steam_id:
                provider = _workshop_provider(mod, workshop_dir)
            else:
                raise DescriptorError(
                    "entry has neither a local registry ID nor a Steam ID"
                )
        except (DescriptorError, OSError) as error:
            detail = (
                str(error)
                if isinstance(error, DescriptorError)
                else "filesystem access failed while resolving installed content"
            )
            warnings.append(
                ReportWarning(
                    code=(
                        "enabled_local_mod_missing"
                        if mod.source == "local" or mod.game_registry_id
                        else "enabled_mod_missing"
                    ),
                    message=f"{mod.display_name}: {detail}",
                    mod_id=mod.stable_id,
                    position=mod.position,
                )
            )
            continue
        providers.append(provider)

    providers.sort(key=lambda provider: (provider.position, provider.stable_id))
    warnings.sort(
        key=lambda warning: (
            warning.position if warning.position is not None else 2**31,
            warning.mod_id,
        )
    )
    return Discovery(
        providers=tuple(providers),
        warnings=tuple(warnings),
        playset=PlaysetRecord(
            name=playset.name,
            game=playset.game,
            selection_source=playset.selection_source,
            mods_total=len(playset.mods),
            mods_enabled=len(playset.enabled_mods),
        ),
    )
