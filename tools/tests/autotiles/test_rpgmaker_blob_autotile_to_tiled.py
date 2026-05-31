"""
TDD tests for scripts/rpgmaker_blob_autotile_to_tiled.py

Tests derived from scripts/game/docs/specs/blob_autotile_pipeline_spec.md
"""

import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
from PIL import Image

BLOB_SLOTS = 47
TILE_SIZE = 32


def _synthetic(width: int = 96, height: int = 128, color=(0, 100, 200, 255)) -> Image.Image:
    return Image.new("RGBA", (width, height), color)


def _save(tmp_path: Path, width: int = 96, height: int = 128) -> Path:
    p = tmp_path / "src.png"
    _synthetic(width, height).save(p)
    return p


# ---------------------------------------------------------------------------
# UT-001 — _assemble_tile : dimensions correctes
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_ut001_assemble_tile_size():
    from tools.src.autotiles.rpgmaker_blob_autotile_to_tiled import _build_blob_tile

    frame = _synthetic(96, 128)
    tile = _build_blob_tile(frame, 255)  # bitmask 255 = fully surrounded
    assert tile.size == (32, 32)


# ---------------------------------------------------------------------------
# UT-002 — _blob_mask : règle diagonal (cardinal absent → diagonal=0)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_ut002_blob_mask_diagonal_cleared():
    from tools.src.autotiles.rpgmaker_blob_autotile_to_tiled import _blob_mask

    # n=True, nw=True, w=False → nw doit être forcé à 0
    result = _blob_mask(nw=True, n=True, ne=False, w=False, e=False, sw=False, s=False, se=False)
    # With w=False, nw bit must be 0; only N bit set → bitmask = 2
    assert result == 2

    # All neighbors → 255
    assert _blob_mask(True, True, True, True, True, True, True, True) == 255

    # None → 0
    assert _blob_mask(False, False, False, False, False, False, False, False) == 0


# ---------------------------------------------------------------------------
# UT-003 — _blob_wang_id : bitmask 255 (entouré complet)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_ut003_wang_id_full():
    from tools.src.autotiles.rpgmaker_blob_autotile_to_tiled import _blob_wang_id

    assert _blob_wang_id(255) == "1,1,1,1,1,1,1,1"


# ---------------------------------------------------------------------------
# UT-004 — _blob_wang_id : bitmask 0 (isolé)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_ut004_wang_id_isolated():
    from tools.src.autotiles.rpgmaker_blob_autotile_to_tiled import _blob_wang_id

    assert _blob_wang_id(0) == "0,0,0,0,0,0,0,0"


# ---------------------------------------------------------------------------
# UT-005 — Strip statique : dimensions (N=1 → 49x32, 32)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_ut005_strip_size_static():
    from tools.src.autotiles.rpgmaker_blob_autotile_to_tiled import _build_blob_strip

    src = _synthetic(96, 128)
    strip = _build_blob_strip(src, n_frames=1)
    assert strip.size == (BLOB_SLOTS * TILE_SIZE, TILE_SIZE), (
        f"Got {strip.size} expected ({BLOB_SLOTS * TILE_SIZE}, 32)"
    )


# ---------------------------------------------------------------------------
# UT-006 — Slot 0 (isolated bitmask=0) is non-transparent (A tile used)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_ut006_isolated_tile_assembled():
    from tools.src.autotiles.rpgmaker_blob_autotile_to_tiled import _build_blob_strip

    src = _synthetic(96, 128, color=(255, 0, 0, 255))
    strip = _build_blob_strip(src, n_frames=1)
    # All 47 slots should be assembled (no empty/transparent tiles)
    for slot in range(BLOB_SLOTS):
        x = slot * TILE_SIZE + TILE_SIZE // 2
        pixel = strip.getpixel((x, TILE_SIZE // 2))
        assert pixel[3] == 255, f"Slot {slot} should be opaque, got alpha={pixel[3]}"


# ---------------------------------------------------------------------------
# UT-007 — Validation height ≠ 128
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_ut007_invalid_height(tmp_path):
    from tools.src.autotiles.rpgmaker_blob_autotile_to_tiled import convert

    src = _save(tmp_path, width=96, height=64)
    with pytest.raises(SystemExit) as exc:
        convert(src, tmp_path / "o.tsx", tmp_path / "o.png", 200)
    assert exc.value.code != 0


# ---------------------------------------------------------------------------
# UT-008 — Validation width % 96 ≠ 0
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_ut008_invalid_width(tmp_path):
    from tools.src.autotiles.rpgmaker_blob_autotile_to_tiled import convert

    src = _save(tmp_path, width=100, height=128)
    with pytest.raises(SystemExit) as exc:
        convert(src, tmp_path / "o.tsx", tmp_path / "o.png", 200)
    assert exc.value.code != 0


# ---------------------------------------------------------------------------
# IT-001 — Pipeline statique complet
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_it001_static_pipeline(tmp_path):
    from tools.src.autotiles.rpgmaker_blob_autotile_to_tiled import convert

    src = _save(tmp_path, width=96, height=128)
    tsx = tmp_path / "grass.tsx"
    png = tmp_path / "grass.png"

    convert(src, tsx, png, frame_duration=200)

    # PNG dimensions
    img = Image.open(png)
    assert img.size == (BLOB_SLOTS * TILE_SIZE, TILE_SIZE), f"Got {img.size}"

    # TSX structure
    root = ET.parse(tsx).getroot()
    assert root.get("tilecount") == str(BLOB_SLOTS)
    assert root.get("columns") == str(BLOB_SLOTS)

    # Wang type = mixed
    wangset = root.find(".//wangset")
    assert wangset is not None
    assert wangset.get("type") == "mixed"

    # 47 wangtiles (not 49 — empty slots 41 and 48 excluded)
    wangtiles = root.findall(".//wangtile")
    assert len(wangtiles) == 47

    # No <tile> animation elements for static
    assert len(root.findall("tile")) == 0


# ---------------------------------------------------------------------------
# IT-002 — Pipeline animé N=4
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_it002_animated_pipeline_4_frames(tmp_path):
    from tools.src.autotiles.rpgmaker_blob_autotile_to_tiled import convert

    src = _save(tmp_path, width=384, height=128)
    tsx = tmp_path / "water.tsx"
    png = tmp_path / "water.png"

    convert(src, tsx, png, frame_duration=200)

    img = Image.open(png)
    assert img.size == (4 * BLOB_SLOTS * TILE_SIZE, TILE_SIZE)

    root = ET.parse(tsx).getroot()
    assert root.get("tilecount") == str(4 * BLOB_SLOTS)

    # 47 <tile><animation> elements
    tile_elements = root.findall("tile")
    assert len(tile_elements) == 47

    for t in tile_elements:
        anim = t.find("animation")
        assert anim is not None
        frames = anim.findall("frame")
        assert len(frames) == 4


# ---------------------------------------------------------------------------
# IT-003 — BITMASK_TO_IDX[255] == 46 (center full tile)
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_it003_bitmask_255_is_slot_46():
    from tools.src.autotiles.rpgmaker_blob_autotile_to_tiled import BITMASK_TO_IDX

    assert BITMASK_TO_IDX.get(255) == 46


# ---------------------------------------------------------------------------
# IT-004 — Image source relative dans le TSX
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_it004_image_source_relative(tmp_path):
    from tools.src.autotiles.rpgmaker_blob_autotile_to_tiled import convert

    src = _save(tmp_path, width=96, height=128)
    tsx = tmp_path / "tilesets" / "t.tsx"
    png = tmp_path / "images" / "t.png"

    convert(src, tsx, png, frame_duration=200)

    root = ET.parse(tsx).getroot()
    source = root.find("image").get("source", "")
    assert not Path(source).is_absolute(), f"Expected relative, got: {source!r}"
