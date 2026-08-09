from __future__ import annotations

from pathlib import Path

from ck3mm.heightmap import (
    ImageProperties,
    apply_heightmap_plan,
    plan_prepare,
    plan_promote,
    verify_heightmap,
)


def test_heightmap_prepare_verify_and_promote_are_planned(tmp_path: Path) -> None:
    source_mod = tmp_path / "repo" / "map-mod"
    source = (
        source_mod / "content_source" / "heightmap" / "heightmap_now_delta_unpacked.png"
    )
    source.parent.mkdir(parents=True)
    source.write_bytes(b"source")
    (source_mod / "descriptor.mod").write_text('name="Map"\n', encoding="utf-8")
    essos = tmp_path / "workshop" / "essos"
    map_data = essos / "map_data"
    map_data.mkdir(parents=True)
    (map_data / "heightmap.heightmap").write_text(
        "original_heightmap_size={ 9216 6144 }\n"
        "tile_size=33\nshould_wrap_x=no\n"
        'heightmap_file="map_data/packed_heightmap.png"\n'
        'indirection_file="map_data/indirection_heightmap.png"\n',
        encoding="utf-8",
    )
    (map_data / "packed_heightmap.png").write_bytes(b"packed-seed")
    (map_data / "indirection_heightmap.png").write_bytes(b"indirect")

    def inspect(path: Path) -> ImageProperties:
        if path.name == "indirection_heightmap.png":
            return ImageProperties(288, 192, 8, "sRGB", "indirect")
        if path.name == "packed_heightmap.png":
            signature = "changed" if path.read_bytes() == b"packed-new" else "seed"
            return ImageProperties(300, 200, 16, "Gray", signature)
        return ImageProperties(9216, 6144, 16, "Gray", "source-pixels")

    stage = tmp_path / "paradox" / "mod" / "stage"
    playset = tmp_path / "state" / "heightmap.json"
    plan = plan_prepare(
        source_mod=source_mod,
        source_heightmap=source,
        essos_expanded_root=essos,
        stage=stage,
        playset_path=playset,
        image_inspector=inspect,
    )
    assert not stage.exists()
    apply_heightmap_plan(plan)
    assert stage.is_dir()
    (stage / "map_data" / "packed_heightmap.png").write_bytes(b"packed-new")
    verification = verify_heightmap(stage, image_inspector=inspect)
    assert verification.packed_pixels_changed

    target = tmp_path / "repo" / "target-map-data"
    target.mkdir()
    (target / "heightmap.png").write_bytes(b"old")
    backup = tmp_path / "state" / "backup"
    promote = plan_promote(
        stage=stage,
        target_map_data=target,
        backup_dir=backup,
        image_inspector=inspect,
    )
    assert (target / "heightmap.png").read_bytes() == b"old"
    apply_heightmap_plan(promote)
    assert (backup / "heightmap.png").read_bytes() == b"old"
    assert (target / "packed_heightmap.png").read_bytes() == b"packed-new"
