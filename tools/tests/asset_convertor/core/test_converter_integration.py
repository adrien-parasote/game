"""
Integration tests for the autotile converter pipeline

Covers: IT-001, IT-002
"""

import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
from PIL import Image

SAMPLES_DIR = Path(__file__).parents[3] / "src" / "input"
SAMPLE_XP = SAMPLES_DIR / "sample_xp.png"
SAMPLE_MV = SAMPLES_DIR / "sample_mv_32px.png"
SAMPLE_MV_48 = SAMPLES_DIR / "sample_mv_48px.png"


# ---------------------------------------------------------------------------
# IT-001 — MV Animated water conversion and export
# ---------------------------------------------------------------------------

@pytest.mark.integration
@pytest.mark.skipif(not SAMPLE_MV.exists(), reason="sample_mv_32px.png not found")
def test_it001_mv_animated_water_pipeline():
    from asset_convertor.core.converter_mv import convert_mv
    from asset_convertor.exporters.tsx_generator import export

    # 3-frame horizontal water is 6 tiles wide x 3 tiles high = 192x96 px.
    # Let's create a synthetic water image since sample_mv_32px.png is static (64x96).
    img = Image.new("RGBA", (192, 96), (0, 0, 255, 255))
    tiles = convert_mv(img, is_animated=True, animation_mode="Horizontale")
    assert len(tiles) == 3
    assert len(tiles[0]) == 47

    with tempfile.TemporaryDirectory() as tmp:
        png_path, tsx_path = export(
            tiles,
            "animated_water",
            tmp,
            32,
            is_animated=True,
            animation_mode="Horizontale",
            duration=150
        )

        # PNG stacked sheet should be 256 x 576 px
        png = Image.open(png_path)
        assert png.size == (256, 576), f"PNG size {png.size} != (256, 576)"

        # TSX must have 47 animation loops
        root = ET.parse(tsx_path).getroot()
        animations = root.findall(".//animation")
        assert len(animations) == 47, f"Expected 47 animations, got {len(animations)}"


# ---------------------------------------------------------------------------
# IT-002 — MV Waterfall conversion and export
# ---------------------------------------------------------------------------

@pytest.mark.integration
def test_it002_mv_waterfall_pipeline():
    from asset_convertor.core.converter_mv import convert_mv
    from asset_convertor.exporters.tsx_generator import export

    # 3-frame vertical waterfall is 2 tiles wide x 3 tiles high = 64x96 px.
    img = Image.new("RGBA", (64, 96), (0, 128, 255, 255))
    tiles = convert_mv(img, is_animated=True, animation_mode="Verticale")
    assert len(tiles) == 3
    assert len(tiles[0]) == 47

    with tempfile.TemporaryDirectory() as tmp:
        png_path, tsx_path = export(
            tiles,
            "animated_waterfall",
            tmp,
            32,
            is_animated=True,
            animation_mode="Verticale",
            duration=200
        )

        png = Image.open(png_path)
        assert png.size == (256, 576)

        root = ET.parse(tsx_path).getroot()
        animations = root.findall(".//animation")
        assert len(animations) == 47

        # Verify first tile animation loop
        tile_0 = root.find(".//tile[@id='0']")
        assert tile_0 is not None
        frames = tile_0.findall(".//frame")
        assert [f.get("tileid") for f in frames] == ["0", "48", "96"]
        assert [f.get("duration") for f in frames] == ["200", "200", "200"]


# ---------------------------------------------------------------------------
# Original integration tests preserved and updated
# ---------------------------------------------------------------------------

@pytest.mark.integration
@pytest.mark.skipif(not SAMPLE_XP.exists(), reason="sample_xp.png not found")
def test_it_xp_static():
    from asset_convertor.core.converter_xp import convert_xp
    from asset_convertor.exporters.tsx_generator import export

    img = Image.open(SAMPLE_XP).convert("RGBA")
    tiles = convert_xp(img, is_animated=False)
    assert len(result := tiles) == 1

    with tempfile.TemporaryDirectory() as tmp:
        png_path, tsx_path = export(tiles, "grass_xp", tmp, 32, is_animated=False)
        png = Image.open(png_path)
        assert png.size == (256, 192)
