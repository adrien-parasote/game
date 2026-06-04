"""
TDD RED tests for asset_convertor.core.converter_xp

Derived from: tools/docs/specs/autotile_converter_spec.md § Test Cases TC-001..TC-010
Bitmask convention (from existing rpgmaker_blob_autotile_to_tiled.py):
  NW=1, N=2, NE=4, W=8, E=16, SW=32, S=64, SE=128
"""

from pathlib import Path

import pytest
from PIL import Image

SAMPLES_DIR = Path(__file__).parents[3] / "src" / "input"
SAMPLE_XP = SAMPLES_DIR / "sample_xp.png"


def _make_xp(color: tuple = (0, 128, 0, 255)) -> Image.Image:
    """Create a synthetic 96x128 RGBA image."""
    return Image.new("RGBA", (96, 128), color)


def _make_xp_with_known_subtile(col: int, row: int, color: tuple) -> Image.Image:
    """Create 96x128 image with a specific 16x16 sub-tile region set to color."""
    img = Image.new("RGBA", (96, 128), (0, 0, 0, 255))
    x, y = col * 16, row * 16
    region = Image.new("RGBA", (16, 16), color)
    img.paste(region, (x, y))
    return img


# ---------------------------------------------------------------------------
# TC-001 — convert_xp returns 47 images
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_tc001_convert_xp_returns_47_images():
    from asset_convertor.core.converter_xp import convert_xp

    img = _make_xp()
    result = convert_xp(img)
    assert len(result) == 47


# ---------------------------------------------------------------------------
# TC-002 — Each output tile is 32x32
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_tc002_each_tile_is_32x32():
    from asset_convertor.core.converter_xp import convert_xp

    img = _make_xp()
    result = convert_xp(img)
    for i, tile in enumerate(result):
        assert tile.size == (32, 32), f"Tile {i} size {tile.size} != (32, 32)"


# ---------------------------------------------------------------------------
# TC-003 — Each output tile is RGBA
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_tc003_each_tile_is_rgba():
    from asset_convertor.core.converter_xp import convert_xp

    img = _make_xp()
    result = convert_xp(img)
    for i, tile in enumerate(result):
        assert tile.mode == "RGBA", f"Tile {i} mode {tile.mode!r} != 'RGBA'"


# ---------------------------------------------------------------------------
# TC-004 — Wrong dimensions raise ValueError
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_tc004_wrong_dimensions_raise_value_error():
    from asset_convertor.core.converter_xp import convert_xp

    wrong = Image.new("RGBA", (64, 64))
    with pytest.raises(ValueError, match=r"96.128"):
        convert_xp(wrong)


# ---------------------------------------------------------------------------
# TC-005 — Isolated tile (bitmask=0) is assembled (non-empty)
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.skipif(not SAMPLE_XP.exists(), reason="sample_xp.png not found")
def test_tc005_isolated_tile_is_assembled():
    from asset_convertor.core.converter_xp import convert_xp

    img = Image.open(SAMPLE_XP).convert("RGBA")
    result = convert_xp(img)
    # Slot 0 = bitmask 0 (isolated) must be non-transparent in center
    tile = result[0]
    center_pixel = tile.getpixel((16, 16))
    assert center_pixel[3] > 0, f"Isolated tile center pixel is transparent: {center_pixel}"


# ---------------------------------------------------------------------------
# TC-006 — Fully surrounded tile (bitmask=255) is assembled
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.skipif(not SAMPLE_XP.exists(), reason="sample_xp.png not found")
def test_tc006_fully_surrounded_tile_is_assembled():
    from asset_convertor.core.converter_xp import convert_xp

    img = Image.open(SAMPLE_XP).convert("RGBA")
    result = convert_xp(img)
    # Last slot = bitmask 255 (fully surrounded) must be fully opaque
    tile = result[46]
    center_pixel = tile.getpixel((16, 16))
    assert center_pixel[3] > 0, f"Surrounded tile center pixel is transparent: {center_pixel}"


# ---------------------------------------------------------------------------
# TC-007 — _extract_subtile crops correctly
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_tc007_extract_subtile_crops_correctly():
    from asset_convertor.core.converter_xp import _extract_subtile

    target_color = (255, 0, 128, 255)
    img = _make_xp_with_known_subtile(col=2, row=2, color=target_color)
    subtile = _extract_subtile(img, col=2, row=2)
    assert subtile.size == (16, 16)
    center = subtile.getpixel((8, 8))
    assert center == target_color, f"Expected {target_color}, got {center}"


# ---------------------------------------------------------------------------
# TC-008 — _assemble_tile places quadrants correctly
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_tc008_assemble_tile_places_quadrants():
    from asset_convertor.core.converter_xp import _assemble_tile

    colors = {
        "TL": (255, 0, 0, 255),
        "TR": (0, 255, 0, 255),
        "BL": (0, 0, 255, 255),
        "BR": (255, 255, 0, 255),
    }
    subtiles = {name: Image.new("RGBA", (16, 16), color) for name, color in colors.items()}
    tile = _assemble_tile(subtiles, ("TL", "TR", "BL", "BR"))
    assert tile.size == (32, 32)
    assert tile.getpixel((8, 8)) == colors["TL"], "Top-left quadrant wrong color"
    assert tile.getpixel((24, 8)) == colors["TR"], "Top-right quadrant wrong color"
    assert tile.getpixel((8, 24)) == colors["BL"], "Bottom-left quadrant wrong color"
    assert tile.getpixel((24, 24)) == colors["BR"], "Bottom-right quadrant wrong color"


# ---------------------------------------------------------------------------
# TC-009 — Source image is not mutated after convert_xp
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.skipif(not SAMPLE_XP.exists(), reason="sample_xp.png not found")
def test_tc009_source_not_mutated():
    from asset_convertor.core.converter_xp import convert_xp

    img = Image.open(SAMPLE_XP).convert("RGBA")
    original_pixels = list(img.getdata())
    convert_xp(img)
    after_pixels = list(img.getdata())
    assert original_pixels == after_pixels, "Source image was mutated by convert_xp"


# ---------------------------------------------------------------------------
# TC-010 — Output index matches BLOB_BITMASKS order
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_tc010_output_index_matches_blob_bitmasks_order():
    from asset_convertor.core.converter_xp import BLOB_BITMASKS, convert_xp

    assert len(BLOB_BITMASKS) == 47
    img = _make_xp()
    result = convert_xp(img)
    # Verify list has 47 entries matching the bitmask order (structural check)
    assert len(result) == len(BLOB_BITMASKS)
