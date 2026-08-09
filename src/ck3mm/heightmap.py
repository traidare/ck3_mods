"""Plan, verify, and apply the AGOT heightmap repack workflow."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

STAGING_NAME = "AGOT Heightmap Repack Staging"
STAGING_REGISTRY_ID = "mod/agot_heightmap_repack_staging.mod"
STAGING_MOD_PATH = "mod/agot_heightmap_repack_staging"
MARKER_NAME = ".agot-heightmap-repack-stage"
HEIGHTMAP_FILES = (
    "heightmap.png",
    "heightmap.heightmap",
    "packed_heightmap.png",
    "indirection_heightmap.png",
)


class HeightmapError(ValueError):
    """Raised when a heightmap operation cannot be planned or verified safely."""


@dataclass(frozen=True, slots=True)
class ImageProperties:
    width: int
    height: int
    depth: int
    colorspace: str
    pixel_signature: str


@dataclass(frozen=True, slots=True)
class FileCopy:
    source: Path
    destination: Path
    overwrite: bool = False


@dataclass(frozen=True, slots=True)
class FileWrite:
    destination: Path
    content: bytes
    mode: int = 0o644
    overwrite: bool = False


@dataclass(frozen=True, slots=True)
class FileMove:
    source: Path
    destination: Path


@dataclass(frozen=True, slots=True)
class HeightmapPlan:
    operation: str
    stage: Path
    copies: tuple[FileCopy, ...] = ()
    writes: tuple[FileWrite, ...] = ()
    backups: tuple[FileCopy, ...] = ()
    moves: tuple[FileMove, ...] = ()


@dataclass(frozen=True, slots=True)
class HeightmapVerification:
    stage: Path
    source_reencoded: bool
    packed_hash_changed: bool
    packed_pixels_changed: bool


ImageInspector = Callable[[Path], ImageProperties]


def inspect_image(
    path: Path, *, identify_executable: str = "identify"
) -> ImageProperties:
    """Read image metadata and ImageMagick's decoded-pixel signature."""
    try:
        result = subprocess.run(
            [
                identify_executable,
                "-quiet",
                "-format",
                "%w %h %z %[colorspace] %#",
                str(path),
            ],
            check=True,
            text=True,
            capture_output=True,
        )
    except (OSError, subprocess.CalledProcessError) as error:
        raise HeightmapError(f"cannot inspect image {path}: {error}") from error
    fields = result.stdout.strip().split(maxsplit=4)
    if len(fields) != 5:
        raise HeightmapError(f"unexpected image metadata for {path}: {result.stdout!r}")
    try:
        width, height, depth = (int(fields[index]) for index in range(3))
    except ValueError as error:
        raise HeightmapError(f"invalid image dimensions for {path}") from error
    return ImageProperties(width, height, depth, fields[3], fields[4])


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _descriptor(*, launcher_path: str | None = None) -> bytes:
    lines = [
        'version="1.0.0"',
        f'name="{STAGING_NAME}"',
        'supported_version="1.19.*"',
        "tags={",
        '    "Map"',
        '    "Utilities"',
        "}",
    ]
    if launcher_path is not None:
        lines.append(f'path="{launcher_path}"')
    return ("\n".join(lines) + "\n").encode()


def minimal_editor_playset() -> bytes:
    """Return the portable minimal playset used by the legacy workflow."""
    names_and_ids = (
        ("A Game of Thrones", "2962333032"),
        ("AGOT Nobility of Westeros", "3664900993"),
        ("Legacy of Valyria", "3403938445"),
        ("Legacy of Valyria - AGOT 0.4.39 Temporary Compatch RC71", "3719888822"),
        ("Essos Expanded", "3682802751"),
        ("Essos Expanded - TempLoV Compatch", "3768149491"),
    )
    mods = [
        {
            "displayName": name,
            "enabled": True,
            "position": position,
            "steamId": steam_id,
        }
        for position, (name, steam_id) in enumerate(names_and_ids)
    ]
    mods.append(
        {
            "displayName": STAGING_NAME,
            "enabled": True,
            "gameRegistryId": STAGING_REGISTRY_ID,
            "position": len(mods),
            "source": "local",
        }
    )
    value = {
        "game": "ck3",
        "name": "AGOT - Heightmap Editor (Minimal)",
        "mods": mods,
    }
    return (json.dumps(value, indent=2) + "\n").encode()


def _tree_files(root: Path) -> tuple[Path, ...]:
    result: list[Path] = []
    for path in sorted(root.rglob("*")):
        if path.is_dir():
            continue
        target = path.resolve(strict=True) if path.is_symlink() else path
        if not stat.S_ISREG(target.stat().st_mode):
            raise HeightmapError(f"refusing non-regular staging source: {path}")
        result.append(path)
    return tuple(result)


def plan_prepare(
    *,
    source_mod: Path,
    source_heightmap: Path,
    essos_expanded_root: Path,
    stage: Path,
    playset_path: Path,
    launcher_descriptor: Path | None = None,
    launcher_mod_path: str = STAGING_MOD_PATH,
    image_inspector: ImageInspector = inspect_image,
) -> HeightmapPlan:
    """Plan creation of a writable editor stage; perform no writes."""
    source_root = Path(source_mod).resolve(strict=False)
    source_map = Path(source_heightmap).resolve(strict=False)
    essos = Path(essos_expanded_root).resolve(strict=False)
    staging = Path(stage).resolve(strict=False)
    playset = Path(playset_path).resolve(strict=False)
    if staging.exists():
        raise HeightmapError(f"staging path already exists: {staging}")
    if not source_root.is_dir():
        raise HeightmapError(f"local map compatch is missing: {source_root}")
    if not source_map.is_file():
        raise HeightmapError(f"merged source heightmap is missing: {source_map}")
    if staging == source_root or staging.is_relative_to(source_root):
        raise HeightmapError("staging path must not be inside the source mod")
    properties = image_inspector(source_map)
    if (
        properties.width,
        properties.height,
        properties.depth,
        properties.colorspace,
    ) != (
        9216,
        6144,
        16,
        "Gray",
    ):
        raise HeightmapError(f"unexpected merged source properties: {properties}")

    seed_paths = {name: essos / "map_data" / name for name in HEIGHTMAP_FILES[1:]}
    for path in seed_paths.values():
        if not path.is_file():
            raise HeightmapError(f"Essos Expanded seed is missing: {path}")
    seed_packed = seed_paths["packed_heightmap.png"]
    packed_signature = image_inspector(seed_packed).pixel_signature

    copies: dict[Path, FileCopy] = {}
    for source in _tree_files(source_root):
        destination = staging / source.relative_to(source_root)
        copies[destination] = FileCopy(source, destination)
    copies[staging / "map_data" / "heightmap.png"] = FileCopy(
        source_map, staging / "map_data" / "heightmap.png"
    )
    for name, source in seed_paths.items():
        copies[staging / "map_data" / name] = FileCopy(
            source, staging / "map_data" / name
        )

    preserved = staging / "content_source" / "heightmap" / source_map.name
    if preserved not in copies:
        copies[preserved] = FileCopy(source_map, preserved)
    hashes = {
        "map_data/heightmap.png": _sha256(source_map),
        **{f"map_data/{name}": _sha256(path) for name, path in seed_paths.items()},
    }
    hash_text = "".join(
        f"{digest}  {name}\n" for name, digest in hashes.items()
    ).encode()
    writes = [
        FileWrite(staging / MARKER_NAME, b"AGOT heightmap repack staging directory\n"),
        FileWrite(staging / "descriptor.mod", _descriptor(), overwrite=True),
        FileWrite(staging / "pre-repack.sha256", hash_text),
        FileWrite(
            staging / "pre-repack-packed-pixel-signature",
            (packed_signature + "\n").encode(),
        ),
        FileWrite(playset, minimal_editor_playset(), overwrite=True),
    ]
    if launcher_descriptor is not None:
        descriptor = Path(launcher_descriptor).resolve(strict=False)
        relative_launcher_path = PurePosixPath(launcher_mod_path)
        if (
            relative_launcher_path.is_absolute()
            or ".." in relative_launcher_path.parts
            or relative_launcher_path.as_posix() in {"", "."}
        ):
            raise HeightmapError(f"invalid Launcher mod path: {launcher_mod_path}")
        registered_stage = (
            descriptor.parent.parent / relative_launcher_path.as_posix()
        ).resolve(strict=False)
        if staging != registered_stage:
            raise HeightmapError(
                f"registered staging must be {registered_stage}; "
                "omit launcher_descriptor for a custom stage"
            )
        if descriptor.exists():
            text = descriptor.read_text(encoding="utf-8-sig")
            if f'name="{STAGING_NAME}"' not in text:
                raise HeightmapError(
                    f"refusing to replace unrelated descriptor: {descriptor}"
                )
        writes.append(
            FileWrite(
                descriptor,
                _descriptor(launcher_path=launcher_mod_path),
                overwrite=True,
            )
        )
    return HeightmapPlan(
        operation="prepare",
        stage=staging,
        copies=tuple(copies[path] for path in sorted(copies)),
        writes=tuple(writes),
    )


def _seed_hashes(stage: Path) -> dict[str, str]:
    path = stage / "pre-repack.sha256"
    try:
        rows = path.read_text(encoding="utf-8").splitlines()
    except OSError as error:
        raise HeightmapError(f"cannot read pre-repack hashes: {error}") from error
    result: dict[str, str] = {}
    for row in rows:
        parts = row.split(maxsplit=1)
        if len(parts) == 2:
            result[parts[1].strip()] = parts[0]
    return result


def verify_heightmap(
    stage: Path, *, image_inspector: ImageInspector = inspect_image
) -> HeightmapVerification:
    """Verify a coherent four-file editor output without modifying it."""
    staging = Path(stage).resolve(strict=False)
    if not (staging / MARKER_NAME).is_file() or not (staging / "map_data").is_dir():
        raise HeightmapError(f"not a prepared staging directory: {staging}")
    paths = {name: staging / "map_data" / name for name in HEIGHTMAP_FILES}
    for path in paths.values():
        if not path.is_file() or path.stat().st_size == 0:
            raise HeightmapError(f"missing or empty staging artifact: {path}")
    hashes = _seed_hashes(staging)
    expected_source = hashes.get("map_data/heightmap.png")
    expected_packed = hashes.get("map_data/packed_heightmap.png")
    if not expected_source or not expected_packed:
        raise HeightmapError("required seed hashes are missing")
    preserved = (
        staging / "content_source" / "heightmap" / "heightmap_now_delta_unpacked.png"
    )
    if not preserved.is_file() or _sha256(preserved) != expected_source:
        raise HeightmapError("preserved merged source changed after preparation")
    source = image_inspector(paths["heightmap.png"])
    preserved_info = image_inspector(preserved)
    source_reencoded = _sha256(paths["heightmap.png"]) != expected_source
    if source.pixel_signature != preserved_info.pixel_signature:
        raise HeightmapError("heightmap.png pixels changed after preparation")
    if (source.width, source.height, source.depth, source.colorspace) != (
        9216,
        6144,
        16,
        "Gray",
    ):
        raise HeightmapError(f"unexpected heightmap.png properties: {source}")
    indirect = image_inspector(paths["indirection_heightmap.png"])
    if (indirect.width, indirect.height) != (288, 192):
        raise HeightmapError(f"unexpected indirection dimensions: {indirect}")
    packed = image_inspector(paths["packed_heightmap.png"])
    if (packed.depth, packed.colorspace) != (16, "Gray"):
        raise HeightmapError(f"unexpected packed heightmap properties: {packed}")
    metadata = (
        paths["heightmap.heightmap"]
        .read_text(encoding="utf-8", errors="replace")
        .replace("\r", "")
    )
    checks = (
        (r"original_heightmap_size\s*=\s*\{\s*9216\s+6144\s*\}", "original size"),
        (r"tile_size\s*=\s*33(?:\D|$)", "tile size"),
        (r"should_wrap_x\s*=\s*no(?:\W|$)", "horizontal wrapping"),
    )
    for pattern, label in checks:
        if re.search(pattern, metadata) is None:
            raise HeightmapError(f"heightmap metadata has invalid {label}")
    if 'heightmap_file="map_data/packed_heightmap.png"' not in metadata:
        raise HeightmapError("heightmap metadata has an invalid packed path")
    if 'indirection_file="map_data/indirection_heightmap.png"' not in metadata:
        raise HeightmapError("heightmap metadata has an invalid indirection path")
    packed_hash_changed = _sha256(paths["packed_heightmap.png"]) != expected_packed
    seed_signature = (
        (staging / "pre-repack-packed-pixel-signature")
        .read_text(encoding="utf-8")
        .strip()
    )
    packed_pixels_changed = packed.pixel_signature != seed_signature
    if not packed_hash_changed or not packed_pixels_changed:
        raise HeightmapError("packed runtime elevation has not changed from its seed")
    return HeightmapVerification(
        staging, source_reencoded, packed_hash_changed, packed_pixels_changed
    )


def plan_promote(
    *,
    stage: Path,
    target_map_data: Path,
    backup_dir: Path,
    image_inspector: ImageInspector = inspect_image,
) -> HeightmapPlan:
    """Verify and plan quartet promotion and recoverable backups."""
    verification = verify_heightmap(stage, image_inspector=image_inspector)
    target = Path(target_map_data).resolve(strict=False)
    backup = Path(backup_dir).resolve(strict=False)
    if (
        target == backup
        or target.is_relative_to(backup)
        or backup.is_relative_to(target)
    ):
        raise HeightmapError("backup and target directories must not overlap")
    copies = tuple(
        FileCopy(verification.stage / "map_data" / name, target / name, overwrite=True)
        for name in HEIGHTMAP_FILES
    )
    backups = tuple(
        FileCopy(target / name, backup / name)
        for name in HEIGHTMAP_FILES
        if (target / name).is_file()
    )
    hash_text = "".join(
        f"{_sha256(item.source)}  {item.destination.name}\n" for item in copies
    ).encode()
    return HeightmapPlan(
        operation="promote",
        stage=verification.stage,
        copies=copies,
        writes=(
            FileWrite(target / "repacked-heightmap.sha256", hash_text, overwrite=True),
        ),
        backups=backups,
    )


def plan_unregister(
    *, stage: Path, launcher_descriptor: Path, destination: Path
) -> HeightmapPlan:
    """Plan recoverable Launcher unregistration by moving its descriptor."""
    staging = Path(stage).resolve(strict=False)
    descriptor = Path(launcher_descriptor).resolve(strict=False)
    target = Path(destination).resolve(strict=False)
    if not (staging / MARKER_NAME).is_file():
        raise HeightmapError(f"not a prepared staging directory: {staging}")
    if not descriptor.is_file():
        raise HeightmapError(f"launcher descriptor is missing: {descriptor}")
    text = descriptor.read_text(encoding="utf-8-sig")
    if f'path="{STAGING_MOD_PATH}"' not in text:
        raise HeightmapError("launcher descriptor does not point at the staging mod")
    if target.exists():
        raise HeightmapError(f"unregistration destination already exists: {target}")
    return HeightmapPlan(
        operation="unregister",
        stage=staging,
        moves=(FileMove(descriptor, target),),
    )


def _atomic_copy(item: FileCopy) -> None:
    item.destination.parent.mkdir(parents=True, exist_ok=True)
    if item.destination.exists() and not item.overwrite:
        raise HeightmapError(f"destination already exists: {item.destination}")
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=item.destination.parent,
            prefix=f".{item.destination.name}.",
            delete=False,
        ) as handle:
            temporary = Path(handle.name)
        shutil.copy2(item.source, temporary, follow_symlinks=True)
        os.replace(temporary, item.destination)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def _atomic_write(item: FileWrite) -> None:
    item.destination.parent.mkdir(parents=True, exist_ok=True)
    if item.destination.exists() and not item.overwrite:
        raise HeightmapError(f"destination already exists: {item.destination}")
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=item.destination.parent,
            prefix=f".{item.destination.name}.",
            delete=False,
        ) as handle:
            handle.write(item.content)
            handle.flush()
            os.fsync(handle.fileno())
            temporary = Path(handle.name)
        temporary.chmod(item.mode)
        os.replace(temporary, item.destination)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def apply_heightmap_plan(plan: HeightmapPlan) -> HeightmapPlan:
    """Apply an inspected prepare, promote, or unregister plan."""
    if plan.operation == "prepare" and plan.stage.exists():
        raise HeightmapError(f"staging path now exists: {plan.stage}")
    for item in plan.backups:
        _atomic_copy(item)
    for item in plan.copies:
        _atomic_copy(item)
    for item in plan.writes:
        _atomic_write(item)
    for item in plan.moves:
        item.destination.parent.mkdir(parents=True, exist_ok=True)
        if item.destination.exists():
            raise HeightmapError(f"move destination already exists: {item.destination}")
        os.replace(item.source, item.destination)
    return plan


apply_prepare = apply_heightmap_plan
apply_promote = apply_heightmap_plan
apply_unregister = apply_heightmap_plan
