"""Preview and apply installation of repository-local CK3 mods."""

from __future__ import annotations

import fnmatch
import os
import shutil
import stat
import tempfile
from collections.abc import Sequence
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from .descriptors import derive_launcher_descriptor
from .workspace import Workspace


class InstallError(ValueError):
    """Raised when an installation cannot be planned or applied safely."""


@dataclass(frozen=True, slots=True)
class InstallFile:
    mod_slug: str
    relative_path: str
    source: Path
    destination: Path


@dataclass(frozen=True, slots=True)
class InstalledDescriptor:
    mod_slug: str
    destination: Path
    content: str
    mode: int


@dataclass(frozen=True, slots=True)
class InstallPlan:
    launcher_mod_dir: Path
    files: tuple[InstallFile, ...]
    descriptors: tuple[InstalledDescriptor, ...]
    removals: tuple[Path, ...]
    excluded: tuple[str, ...]

    @property
    def mod_slugs(self) -> tuple[str, ...]:
        return tuple(descriptor.mod_slug for descriptor in self.descriptors)


def _excluded(relative: PurePosixPath, patterns: tuple[str, ...]) -> bool:
    value = relative.as_posix()
    for pattern in patterns:
        normalized = pattern.replace("\\", "/").rstrip("/")
        if fnmatch.fnmatchcase(value, normalized):
            return True
        if normalized.endswith("/**"):
            prefix = normalized[:-3].rstrip("/")
            if value == prefix or value.startswith(prefix + "/"):
                return True
    return False


def _source_files(mod_root: Path, patterns: tuple[str, ...]) -> dict[str, Path]:
    result: dict[str, Path] = {}
    for directory, names, filenames in os.walk(mod_root, followlinks=False):
        root = Path(directory)
        kept_names: list[str] = []
        for name in sorted(names):
            path = root / name
            relative = PurePosixPath(path.relative_to(mod_root).as_posix())
            if _excluded(relative, patterns):
                continue
            if path.is_symlink():
                target = path.resolve(strict=True)
                if not target.is_dir():
                    raise InstallError(
                        f"directory symlink does not target a directory: {path}"
                    )
                # Deliberately copy links like the legacy rsync --copy-links workflow.
                for nested in sorted(target.rglob("*")):
                    if nested.is_dir():
                        continue
                    nested_relative = relative / nested.relative_to(target).as_posix()
                    if not _excluded(nested_relative, patterns):
                        result[nested_relative.as_posix()] = nested
                continue
            kept_names.append(name)
        names[:] = kept_names
        for name in sorted(filenames):
            path = root / name
            relative = PurePosixPath(path.relative_to(mod_root).as_posix())
            if _excluded(relative, patterns):
                continue
            target = path.resolve(strict=True) if path.is_symlink() else path
            mode = target.stat().st_mode
            if not stat.S_ISREG(mode):
                raise InstallError(f"refusing to install non-regular file: {path}")
            result[relative.as_posix()] = target
    return result


def _installed_files(root: Path, patterns: tuple[str, ...]) -> dict[str, Path]:
    if not root.exists():
        return {}
    if root.is_symlink() or not root.is_dir():
        raise InstallError(f"installed mod destination is not a directory: {root}")
    result: dict[str, Path] = {}
    for path in sorted(root.rglob("*")):
        relative = PurePosixPath(path.relative_to(root).as_posix())
        if _excluded(relative, patterns) or path.is_dir():
            continue
        result[relative.as_posix()] = path
    return result


def plan_install(
    workspace: Workspace,
    launcher_mod_dir: Path,
    *,
    mod_slugs: Sequence[str] = (),
) -> InstallPlan:
    """Derive Launcher descriptors and a complete, non-mutating sync plan."""
    destination_root = Path(launcher_mod_dir).resolve(strict=False)
    source_root = workspace.mods_dir.resolve(strict=True)
    if destination_root == source_root or destination_root.is_relative_to(source_root):
        raise InstallError("launcher mod directory must not be inside workspace mods")
    if source_root.is_relative_to(destination_root):
        raise InstallError("workspace mods must not be inside launcher mod directory")

    patterns = workspace.settings.install_exclude
    files: list[InstallFile] = []
    descriptors: list[InstalledDescriptor] = []
    removals: list[Path] = []
    mods = (
        tuple(workspace.get_mod(slug) for slug in mod_slugs)
        if mod_slugs
        else workspace.mods()
    )
    if not mods:
        raise InstallError(f"no local mods found below {workspace.mods_dir}")

    for mod in mods:
        if not mod.descriptor_path.is_file():
            raise InstallError(f"native descriptor is missing: {mod.descriptor_path}")
        destination = destination_root / mod.slug
        source_files = _source_files(mod.root, patterns)
        installed_files = _installed_files(destination, patterns)
        files.extend(
            InstallFile(mod.slug, relative, source, destination / relative)
            for relative, source in sorted(source_files.items())
        )
        removals.extend(
            installed_files[relative]
            for relative in sorted(installed_files.keys() - source_files.keys())
        )
        descriptors.append(
            InstalledDescriptor(
                mod_slug=mod.slug,
                destination=destination_root / f"{mod.slug}.mod",
                content=derive_launcher_descriptor(
                    mod.descriptor_path,
                    mod_slug=mod.slug,
                    launcher_mod_path=f"mod/{mod.slug}",
                ),
                mode=mod.descriptor_path.stat().st_mode & 0o777,
            )
        )

    return InstallPlan(
        launcher_mod_dir=destination_root,
        files=tuple(files),
        descriptors=tuple(descriptors),
        removals=tuple(sorted(set(removals))),
        excluded=patterns,
    )


def _atomic_copy(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=destination.parent, prefix=f".{destination.name}.", delete=False
        ) as handle:
            temporary = Path(handle.name)
        shutil.copy2(source, temporary, follow_symlinks=True)
        os.replace(temporary, destination)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def _atomic_text(content: str, destination: Path, mode: int) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=destination.parent,
            prefix=f".{destination.name}.",
            delete=False,
        ) as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
            temporary = Path(handle.name)
        temporary.chmod(mode)
        os.replace(temporary, destination)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def apply_install(plan: InstallPlan) -> InstallPlan:
    """Apply a previously inspected install plan."""
    plan.launcher_mod_dir.mkdir(parents=True, exist_ok=True)
    for item in plan.files:
        _atomic_copy(item.source, item.destination)
    for item in plan.descriptors:
        _atomic_text(item.content, item.destination, item.mode)
    for path in plan.removals:
        if path.is_dir() and not path.is_symlink():
            raise InstallError(f"refusing planned directory removal: {path}")
        path.unlink(missing_ok=True)
    for descriptor in plan.descriptors:
        root = plan.launcher_mod_dir / descriptor.mod_slug
        if root.is_dir():
            for directory in sorted(
                (path for path in root.rglob("*") if path.is_dir()), reverse=True
            ):
                with suppress(OSError):
                    directory.rmdir()
    return plan
