"""
Unit tests for asset_convertor.core.converter_xp

Covers: TC-001, TC-002, TC-003, TC-004, TC-005
"""

from pathlib import Path

import pytest
from PIL import Image

SAMPLES_DIR = Path(__file__).parents[3] / "src" / "input"
SAMPLE_XP = SAMPLES_DIR / "sample_xp.png"


def _make_xp(width: int = 96, height: int = 128, color: tuple = (0, 128, 0, 255)) -> Image.Image:
    """Create a synthetic XP autotile block."""
    return Image.new("RGBA", (width, height), color)


# ---------------------------------------------------------------------------
# TC-001 — convert_xp static returns 1 frame
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_tc001_convert_xp_static_returns_1_frame():
    from asset_convertor.core.converter_xp import convert_xp

    img = _make_xp()
    result = convert_xp(img, is_animated=False)
    assert len(result) == 1
    assert len(result[0]) == 47


# ---------------------------------------------------------------------------
# TC-002 — convert_xp animated horizontal
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_tc002_convert_xp_animated_horizontal():
    from asset_convertor.core.converter_xp import convert_xp

    # 3 frames: 288x128
    img = _make_xp(width=288)
    result = convert_xp(img, is_animated=True, animation_mode="Horizontale")
    assert len(result) == 3
    for frame in result:
        assert len(frame) == 47
        for tile in frame:
            assert tile.size == (32, 32)
            assert tile.mode == "RGBA"


# ---------------------------------------------------------------------------
# TC-003 — convert_xp animated vertical raises error
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_tc003_convert_xp_animated_vertical_raises_error():
    from asset_convertor.core.converter_xp import convert_xp

    img = _make_xp()
    with pytest.raises(ValueError, match=r"animation.*vertical"):
        convert_xp(img, is_animated=True, animation_mode="Verticale")


# ---------------------------------------------------------------------------
# TC-004 — convert_xp invalid dimensions raise error
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_tc004_convert_xp_invalid_dimensions():
    from asset_convertor.core.converter_xp import convert_xp

    # 100x128 instead of 96x128
    img = _make_xp(width=100)
    with pytest.raises(ValueError, match=r"Expected XP autotile"):
        convert_xp(img)


# ---------------------------------------------------------------------------
# TC-005 — convert_xp does not mutate source
# ---------------------------------------------------------------------------

@pytest.mark.unit
@pytest.mark.skipif(not SAMPLE_XP.exists(), reason="sample_xp.png not found")
def test_tc005_convert_xp_does_not_mutate_source():
    from asset_convertor.core.converter_xp import convert_xp

    img = Image.open(SAMPLE_XP).convert("RGBA")
    original_pixels = list(img.getdata())
    convert_xp(img)
    after_pixels = list(img.getdata())
    assert original_pixels == after_pixels, "Source image was mutated by convert_xp"


# ---------------------------------------------------------------------------
# Additional existing tests updated for signature/structure change
# ---------------------------------------------------------------------------

@pytest.mark.unit
@pytest.mark.skipif(not SAMPLE_XP.exists(), reason="sample_xp.png not found")
def test_isolated_tile_is_assembled():
    from asset_convertor.core.converter_xp import convert_xp

    img = Image.open(SAMPLE_XP).convert("RGBA")
    result = convert_xp(img)
    tile = result[0][0]  # First frame, first tile
    center_pixel = tile.getpixel((16, 16))
    assert center_pixel[3] > 0


@pytest.mark.unit
@pytest.mark.skipif(not SAMPLE_XP.exists(), reason="sample_xp.png not found")
def test_fully_surrounded_tile_is_assembled():
    from asset_convertor.core.converter_xp import convert_xp

    img = Image.open(SAMPLE_XP).convert("RGBA")
    result = convert_xp(img)
    tile = result[0][46]  # First frame, last tile
    center_pixel = tile.getpixel((16, 16))
    assert center_pixel[3] > 0
