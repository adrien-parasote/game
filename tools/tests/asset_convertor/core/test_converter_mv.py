"""
TDD RED tests for asset_convertor.core.converter_mv

Derived from: tools/docs/specs/autotile_converter_spec.md § Test Cases TC-011..TC-020
"""

from pathlib import Path

import pytest
from PIL import Image

SAMPLES_DIR = Path(__file__).parents[3] / "src" / "input"
SAMPLE_MV = SAMPLES_DIR / "sample_mv_32px.png"


def _make_mv(width: int = 64, height: int = 96, color: tuple = (0, 128, 128, 255)) -> Image.Image:
    """Create a synthetic MV autotile block."""
    return Image.new("RGBA", (width, height), color)


# ---------------------------------------------------------------------------
# TC-011 — detect_tile_size returns 32 for 64x96
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_tc011_detect_tile_size_32px():
    from asset_convertor.core.converter_mv import detect_tile_size

    img = Image.new("RGBA", (64, 96))
    assert detect_tile_size(img) == 32


# ---------------------------------------------------------------------------
# TC-012 — detect_tile_size returns 48 for 96x144
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_tc012_detect_tile_size_48px():
    from asset_convertor.core.converter_mv import detect_tile_size

    img = Image.new("RGBA", (96, 144))
    assert detect_tile_size(img) == 48


# ---------------------------------------------------------------------------
# TC-013 — detect_tile_size raises ValueError for unknown size
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_tc013_detect_tile_size_raises_for_unknown():
    from asset_convertor.core.converter_mv import detect_tile_size

    img = Image.new("RGBA", (128, 192))
    with pytest.raises(ValueError, match=r"Unrecognized"):
        detect_tile_size(img)


# ---------------------------------------------------------------------------
# TC-014 — convert_mv returns 47 images (32px input)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_tc014_convert_mv_returns_47_images():
    from asset_convertor.core.converter_mv import convert_mv

    img = _make_mv(64, 96)
    result = convert_mv(img)
    assert len(result) == 47


# ---------------------------------------------------------------------------
# TC-015 — Each output tile is 32x32 for 64x96 input
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_tc015_tiles_are_32x32_for_64x96():
    from asset_convertor.core.converter_mv import convert_mv

    img = _make_mv(64, 96)
    result = convert_mv(img)
    for i, tile in enumerate(result):
        assert tile.size == (32, 32), f"Tile {i} size {tile.size} != (32, 32)"


# ---------------------------------------------------------------------------
# TC-016 — Each output tile is RGBA
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_tc016_tiles_are_rgba():
    from asset_convertor.core.converter_mv import convert_mv

    img = _make_mv(64, 96)
    result = convert_mv(img)
    for i, tile in enumerate(result):
        assert tile.mode == "RGBA", f"Tile {i} mode {tile.mode!r} != 'RGBA'"


# ---------------------------------------------------------------------------
# TC-017 — Wrong dimensions raise ValueError
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_tc017_wrong_dimensions_raise_value_error():
    from asset_convertor.core.converter_mv import convert_mv

    wrong = Image.new("RGBA", (64, 64))
    with pytest.raises(ValueError, match=r"Unrecognized"):
        convert_mv(wrong)


# ---------------------------------------------------------------------------
# TC-018 — Isolated tile (bitmask=0) uses outer corners (non-transparent center)
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.skipif(not SAMPLE_MV.exists(), reason="sample_mv_32px.png not found")
def test_tc018_isolated_tile_non_transparent():
    from asset_convertor.core.converter_mv import convert_mv

    img = Image.open(SAMPLE_MV).convert("RGBA")
    result = convert_mv(img)
    tile = result[0]  # bitmask=0 = isolated
    center = tile.getpixel((16, 16))
    assert center[3] > 0, f"Isolated tile center is transparent: {center}"


# ---------------------------------------------------------------------------
# TC-019 — Fully surrounded (bitmask=255) uses inner fill (non-transparent)
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.skipif(not SAMPLE_MV.exists(), reason="sample_mv_32px.png not found")
def test_tc019_fully_surrounded_non_transparent():
    from asset_convertor.core.converter_mv import convert_mv

    img = Image.open(SAMPLE_MV).convert("RGBA")
    result = convert_mv(img)
    tile = result[46]  # bitmask=255 = fully surrounded
    center = tile.getpixel((16, 16))
    assert center[3] > 0, f"Fully surrounded tile center is transparent: {center}"


# ---------------------------------------------------------------------------
# TC-020 — Source image not mutated after convert_mv
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.skipif(not SAMPLE_MV.exists(), reason="sample_mv_32px.png not found")
def test_tc020_source_not_mutated():
    from asset_convertor.core.converter_mv import convert_mv

    img = Image.open(SAMPLE_MV).convert("RGBA")
    original_pixels = list(img.getdata())
    convert_mv(img)
    after_pixels = list(img.getdata())
    assert original_pixels == after_pixels, "Source image was mutated by convert_mv"
