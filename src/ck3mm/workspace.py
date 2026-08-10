"""Repository and per-mod workspace discovery."""

from __future__ import annotations

import tomllib
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

from .config import Config, ConfigError

ROOT_MARKER = "ck3mm.toml"
SOURCE_KINDS = frozenset({"workshop", "game", "repository", "mod"})
ARTIFACT_PREFIX = "artifacts"


class WorkspaceError(ValueError):
    """Raised when repository or mod workspace metadata is invalid."""


def discover_root(start: Path | None = None) -> Path:
    """Find the nearest ancestor containing the repository's ``ck3mm.toml``."""
    candidate = Path.cwd() if start is None else Path(start)
    if candidate.exists() and candidate.is_file():
        candidate = candidate.parent
    candidate = candidate.resolve(strict=False)
    for directory in (candidate, *candidate.parents):
        if (directory / ROOT_MARKER).is_file():
            return directory
    raise WorkspaceError(f"no {ROOT_MARKER} found from {candidate}")


def _read_toml(path: Path) -> dict[str, Any]:
    try:
        with path.open("rb") as handle:
            value = tomllib.load(handle)
    except FileNotFoundError as error:
        raise WorkspaceError(f"workspace metadata not found: {path}") from error
    except tomllib.TOMLDecodeError as error:
        raise WorkspaceError(f"invalid TOML in {path}: {error}") from error
    if not isinstance(value, dict):
        raise WorkspaceError(f"expected a TOML table in {path}")
    return value


def _relative_path(value: object, *, field_name: str, allow_glob: bool = False) -> str:
    if not isinstance(value, str) or not value.strip():
        raise WorkspaceError(f"{field_name} must be a non-empty POSIX path")
    text = value.strip().replace("\\", "/")
    path = PurePosixPath(text)
    if path.is_absolute() or ".." in path.parts:
        raise WorkspaceError(
            f"{field_name} must stay within its declared root: {value}"
        )
    if not allow_glob and any(character in text for character in "*?["):
        raise WorkspaceError(f"{field_name} must not contain a glob: {value}")
    normalized = path.as_posix()
    if normalized in {"", "."}:
        raise WorkspaceError(f"{field_name} must not be empty")
    return normalized


def _string_list(value: object, *, field_name: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise WorkspaceError(f"{field_name} must be an array of strings")
    return tuple(value)


@dataclass(frozen=True, slots=True)
class WorkspaceSettings:
    """Repository layout, loaded from ``ck3mm.toml`` at the workspace root."""

    mods_dir: str = "mods"
    tooling_dir: str = "workspace"
    state_dir: str = ".ignored/ck3mm"
    descriptor: str = "descriptor.mod"
    manifest: str = "mod.toml"
    artifacts_dir: str = ARTIFACT_PREFIX
    install_exclude: tuple[str, ...] = ("README.md",)

    @classmethod
    def from_root(cls, root: Path) -> WorkspaceSettings:
        data = _read_toml(root / ROOT_MARKER).get("workspace", {})
        if not isinstance(data, dict):
            raise WorkspaceError(f"{ROOT_MARKER}: workspace must be a table")
        defaults = cls()
        values: dict[str, Any] = {}
        for field_name in (
            "mods_dir",
            "tooling_dir",
            "state_dir",
            "descriptor",
            "manifest",
            "artifacts_dir",
        ):
            value = data.get(field_name, getattr(defaults, field_name))
            if not isinstance(value, str) or not value.strip():
                raise WorkspaceError(
                    f"{ROOT_MARKER}: workspace.{field_name} must be a non-empty string"
                )
            values[field_name] = value.strip()
        exclude = data.get("install_exclude")
        values["install_exclude"] = (
            _string_list(exclude, field_name="workspace.install_exclude")
            if exclude is not None
            else defaults.install_exclude
        )
        return cls(**values)


@dataclass(frozen=True, slots=True)
class SourceSpec:
    name: str
    kind: str
    path: str | None = None
    item_id: str | None = None
    mod: str | None = None

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any], *, path: Path) -> SourceSpec:
        name = data.get("name")
        kind = data.get("kind")
        if not isinstance(name, str) or not name.strip():
            raise WorkspaceError(f"{path}: each source requires a non-empty name")
        if kind not in SOURCE_KINDS:
            raise WorkspaceError(
                f"{path}: source {name!r} has invalid kind {kind!r}; "
                f"expected one of {', '.join(sorted(SOURCE_KINDS))}"
            )

        source_path = data.get("path")
        normalized_path = (
            _relative_path(source_path, field_name=f"source {name}.path")
            if source_path not in (None, "")
            else None
        )
        item_id_value = data.get("item_id")
        item_id = str(item_id_value) if item_id_value is not None else None
        mod = data.get("mod")
        if mod is not None and (not isinstance(mod, str) or not mod.strip()):
            raise WorkspaceError(f"{path}: source {name}.mod must be a mod slug")

        if kind == "workshop" and not item_id:
            raise WorkspaceError(f"{path}: workshop source {name!r} requires item_id")
        if kind in {"game", "repository"} and not normalized_path:
            raise WorkspaceError(f"{path}: {kind} source {name!r} requires path")
        if kind == "mod" and not mod:
            raise WorkspaceError(f"{path}: mod source {name!r} requires mod")

        return cls(
            name=name.strip(),
            kind=kind,
            path=normalized_path,
            item_id=item_id,
            mod=mod.strip() if isinstance(mod, str) else None,
        )


@dataclass(frozen=True, slots=True)
class GeneratorSpec:
    entrypoint: str
    owned_outputs: tuple[str, ...]
    owned_artifacts: tuple[str, ...] = ()
    assets: tuple[str, ...] = ()

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any], *, path: Path) -> GeneratorSpec:
        entrypoint = data.get("entrypoint")
        if not isinstance(entrypoint, str) or not entrypoint.strip():
            raise WorkspaceError(f"{path}: generator.entrypoint is required")
        module_path, separator, function = entrypoint.partition(":")
        if not separator or not function.isidentifier():
            raise WorkspaceError(
                f"{path}: generator.entrypoint must be FILE.py:function"
            )
        module_path = _relative_path(
            module_path, field_name="generator.entrypoint module"
        )
        if not module_path.endswith(".py"):
            raise WorkspaceError(f"{path}: generator entrypoint must use a .py file")

        outputs = tuple(
            _relative_path(item, field_name="generator.owned_outputs", allow_glob=True)
            for item in _string_list(
                data.get("owned_outputs"), field_name="generator.owned_outputs"
            )
        )
        if not outputs:
            raise WorkspaceError(f"{path}: generator.owned_outputs must not be empty")
        for output in outputs:
            if PurePosixPath(output).parts[0] == ARTIFACT_PREFIX:
                raise WorkspaceError(
                    f"{path}: {ARTIFACT_PREFIX}/ is reserved for "
                    f"generator.owned_artifacts: {output}"
                )

        artifacts = tuple(
            _relative_path(
                item, field_name="generator.owned_artifacts", allow_glob=True
            )
            for item in _string_list(
                data.get("owned_artifacts", []),
                field_name="generator.owned_artifacts",
            )
        )

        assets = tuple(
            _relative_path(item, field_name="generator.assets", allow_glob=True)
            for item in _string_list(
                data.get("assets", []), field_name="generator.assets"
            )
        )
        return cls(
            entrypoint=f"{module_path}:{function}",
            owned_outputs=outputs,
            owned_artifacts=artifacts,
            assets=assets,
        )


@dataclass(frozen=True, slots=True)
class ModManifest:
    path: Path
    slug: str
    generator: GeneratorSpec | None = None
    sources: tuple[SourceSpec, ...] = ()


@dataclass(frozen=True, slots=True)
class Mod:
    """One mod: an installable payload root plus its non-shipping tooling root."""

    slug: str
    root: Path
    tooling_root: Path
    descriptor_path: Path
    manifest_path: Path
    artifacts_root: Path
    manifest: ModManifest | None = None


def _source_mappings(value: object, *, path: Path) -> list[Mapping[str, Any]]:
    if value is None:
        return []
    if isinstance(value, list):
        if not all(isinstance(item, dict) for item in value):
            raise WorkspaceError(f"{path}: sources must contain tables")
        return value
    if isinstance(value, dict):
        result: list[Mapping[str, Any]] = []
        for name, entry in value.items():
            if not isinstance(entry, dict):
                raise WorkspaceError(f"{path}: source {name!r} must be a table")
            result.append({"name": name, **entry})
        return result
    raise WorkspaceError(f"{path}: sources must be an array of tables")


def load_manifest(path: Path, *, default_slug: str) -> ModManifest:
    """Load one ``workspace/<slug>/mod.toml`` manifest."""
    data = _read_toml(path)
    slug = default_slug.strip()
    if slug in {".", ".."} or "/" in slug or "\\" in slug:
        raise WorkspaceError(f"invalid mod directory name {slug!r}")

    generator_data = data.get("generator")
    if generator_data is not None and not isinstance(generator_data, dict):
        raise WorkspaceError(f"{path}: generator must be a table")
    generator = (
        GeneratorSpec.from_mapping(generator_data, path=path)
        if generator_data is not None
        else None
    )
    sources = tuple(
        SourceSpec.from_mapping(item, path=path)
        for item in _source_mappings(data.get("sources"), path=path)
    )
    source_names = [source.name for source in sources]
    if len(source_names) != len(set(source_names)):
        raise WorkspaceError(f"{path}: source names must be unique")

    return ModManifest(
        path=path.resolve(),
        slug=slug,
        generator=generator,
        sources=sources,
    )


@dataclass(frozen=True, slots=True)
class Workspace:
    root: Path
    settings: WorkspaceSettings

    @classmethod
    def from_path(cls, start: Path | None = None) -> Workspace:
        root = discover_root(start)
        return cls(root=root, settings=WorkspaceSettings.from_root(root))

    @property
    def mods_dir(self) -> Path:
        return self.root / self.settings.mods_dir

    @property
    def tooling_dir(self) -> Path:
        return self.root / self.settings.tooling_dir

    @property
    def state_dir(self) -> Path:
        return self.root / self.settings.state_dir

    def _mod_at(self, slug: str) -> Mod | None:
        mod_root = self.mods_dir / slug
        tooling_root = self.tooling_dir / slug
        descriptor = mod_root / self.settings.descriptor
        manifest_path = tooling_root / self.settings.manifest
        if not descriptor.is_file() and not manifest_path.is_file():
            return None
        manifest = (
            load_manifest(manifest_path, default_slug=slug)
            if manifest_path.is_file()
            else None
        )
        return Mod(
            slug=slug,
            root=mod_root,
            tooling_root=tooling_root,
            descriptor_path=descriptor,
            manifest_path=manifest_path,
            artifacts_root=tooling_root / self.settings.artifacts_dir,
            manifest=manifest,
        )

    def iter_mods(self) -> Iterator[Mod]:
        """Yield mods in stable slug order, keyed by their payload directory."""
        if not self.mods_dir.is_dir():
            return
        for slug in sorted(
            path.name for path in self.mods_dir.iterdir() if path.is_dir()
        ):
            mod = self._mod_at(slug)
            if mod is not None:
                yield mod

    def mods(self) -> tuple[Mod, ...]:
        return tuple(self.iter_mods())

    def get_mod(self, slug: str) -> Mod:
        for mod in self.iter_mods():
            if mod.slug == slug:
                return mod
        raise WorkspaceError(f"unknown local mod: {slug}")

    def manifests(self) -> tuple[ModManifest, ...]:
        return tuple(mod.manifest for mod in self.iter_mods() if mod.manifest)

    def resolve_source(
        self,
        source: SourceSpec,
        config: Config,
        *,
        must_exist: bool = True,
    ) -> Path:
        """Resolve a portable logical source into a local read-only path."""
        if source.kind == "workshop":
            if config.workshop_dir is None:
                raise ConfigError("CK3_WORKSHOP_DIR is required for Workshop sources")
            base = config.workshop_dir / str(source.item_id)
        elif source.kind == "game":
            if config.game_dir is None:
                raise ConfigError("CK3_GAME_DIR is required for game sources")
            base = config.game_dir
        elif source.kind == "repository":
            base = self.root
        elif source.kind == "mod":
            base = self.get_mod(source.mod or "").root
        else:  # pragma: no cover - SourceSpec validates this boundary.
            raise WorkspaceError(f"unsupported source kind: {source.kind}")

        resolved_base = base.resolve(strict=False)
        resolved = (resolved_base / (source.path or ".")).resolve(strict=False)
        if not resolved.is_relative_to(resolved_base):
            raise WorkspaceError(f"source escapes its declared root: {source.name}")
        if must_exist and not resolved.exists():
            raise WorkspaceError(f"source {source.name!r} does not exist: {resolved}")
        return resolved

    def resolve_sources(
        self,
        manifest: ModManifest,
        config: Config,
        *,
        must_exist: bool = True,
    ) -> dict[str, Path]:
        return {
            source.name: self.resolve_source(source, config, must_exist=must_exist)
            for source in manifest.sources
        }
