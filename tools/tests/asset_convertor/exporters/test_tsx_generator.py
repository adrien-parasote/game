"""
Unit tests for asset_convertor.exporters.tsx_generator

Covers: TC-012, TC-013, TC-014, TC-015, TC-016
"""

import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
from PIL import Image


def _make_tiles_by_frame(frames: int = 3, count: int = 47, size: int = 32, color: tuple = (0, 128, 0, 255)) -> list[list[Image.Image]]:
    """Create list of frames, each containing count uniform RGBA tiles."""
    return [[Image.new("RGBA", (size, size), color) for _ in range(count)] for _ in range(frames)]


# ---------------------------------------------------------------------------
# TC-012 — assemble_sheet stacked vertical height
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_tc012_assemble_sheet_vertical_height():
    from asset_convertor.exporters.tsx_generator import assemble_sheet

    # 3 frames of 47 tiles (32px)
    tiles_by_frame = _make_tiles_by_frame(frames=3, count=47, size=32)
    sheet = assemble_sheet(tiles_by_frame, 32)
    # Width should be 8 * 32 = 256
    # Height should be 6 * 3 * 32 = 576
    assert sheet.size == (256, 576), f"Expected (256, 576), got {sheet.size}"


# ---------------------------------------------------------------------------
# TC-013 — generate_tsx animated includes XML animation nodes
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_tc013_generate_tsx_includes_animation_nodes():
    from asset_convertor.exporters.tsx_generator import generate_tsx

    # 3 frames, animated, duration=150
    xml_str = generate_tsx(
        name="water",
        tile_size=32,
        png_filename="water.png",
        is_animated=True,
        animation_mode="Horizontale",
        duration=150,
        num_frames=3
    )
    root = ET.fromstring(xml_str)

    # Check that <tile id="0"> exists and has <animation>
    tile_node = root.find(".//tile[@id='0']")
    assert tile_node is not None, "Tile node with id=0 not found"
    animation = tile_node.find("animation")
    assert animation is not None, "Animation tag not found under tile 0"
    frames = animation.findall("frame")
    assert len(frames) > 0


# ---------------------------------------------------------------------------
# TC-014 — generate_tsx ping-pong cycle verification
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_tc014_generate_tsx_ping_pong_verification():
    from asset_convertor.exporters.tsx_generator import generate_tsx

    # 3 frames horizontal water -> ping-pong cycle [0, 1, 2, 1]
    xml_str = generate_tsx(
        name="water",
        tile_size=32,
        png_filename="water.png",
        is_animated=True,
        animation_mode="Horizontale",
        duration=150,
        num_frames=3
    )
    root = ET.fromstring(xml_str)
    tile_node = root.find(".//tile[@id='0']")
    animation = tile_node.find("animation")
    frames = animation.findall("frame")

    # Sequence of tileids: 0 -> 48 -> 96 -> 48
    expected_tileids = ["0", "48", "96", "48"]
    actual_tileids = [f.get("tileid") for f in frames]
    assert actual_tileids == expected_tileids, f"Expected {expected_tileids}, got {actual_tileids}"

    # Verify durations are all "150"
    for f in frames:
        assert f.get("duration") == "150"


# ---------------------------------------------------------------------------
# TC-015 — generate_tsx linear loop verification
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_tc015_generate_tsx_linear_loop_verification():
    from asset_convertor.exporters.tsx_generator import generate_tsx

    # 3 frames vertical waterfall -> linear cycle [0, 1, 2]
    xml_str = generate_tsx(
        name="waterfall",
        tile_size=32,
        png_filename="waterfall.png",
        is_animated=True,
        animation_mode="Verticale",
        duration=200,
        num_frames=3
    )
    root = ET.fromstring(xml_str)
    tile_node = root.find(".//tile[@id='5']")
    animation = tile_node.find("animation")
    frames = animation.findall("frame")

    # Sequence of tileids for tile 5: 5 -> 53 (5+48) -> 101 (5+96)
    expected_tileids = ["5", "53", "101"]
    actual_tileids = [f.get("tileid") for f in frames]
    assert actual_tileids == expected_tileids, f"Expected {expected_tileids}, got {actual_tileids}"

    for f in frames:
        assert f.get("duration") == "200"


# ---------------------------------------------------------------------------
# TC-016 — generate_tsx static has no animation nodes
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_tc016_generate_tsx_static_no_animation():
    from asset_convertor.exporters.tsx_generator import generate_tsx

    # is_animated=False
    xml_str = generate_tsx(
        name="grass",
        tile_size=32,
        png_filename="grass.png",
        is_animated=False
    )
    root = ET.fromstring(xml_str)

    # Check that no <tile> node has <animation>
    animations = root.findall(".//animation")
    assert len(animations) == 0, f"Expected 0 animations, got {len(animations)}"


# ---------------------------------------------------------------------------
# Additional export test checking signature
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_export_animated():
    from asset_convertor.exporters.tsx_generator import export

    tiles_by_frame = _make_tiles_by_frame(frames=3, count=47, size=32)
    with tempfile.TemporaryDirectory() as tmp:
        png_path, tsx_path = export(
            tiles_by_frame,
            "water_export",
            tmp,
            32,
            is_animated=True,
            animation_mode="Horizontale",
            duration=150
        )
        assert Path(png_path).exists()
        assert Path(tsx_path).exists()

        # Verify height of exported PNG sheet (576 px)
        img = Image.open(png_path)
        assert img.size == (256, 576)


# ---------------------------------------------------------------------------
# TC-017 — generate_tsx_simple produces valid XML without wangset
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_tc017_generate_tsx_simple_no_wangset():
    from asset_convertor.exporters.tsx_generator import generate_tsx_simple

    xml_str = generate_tsx_simple(
        name="building",
        tile_size=48,
        png_filename="building.png",
        tile_count=47,
        columns=8,
    )
    root = ET.fromstring(xml_str)

    # Must have no wangsets element
    assert root.find("wangsets") is None, "Simple tileset must not have wangsets"
    # Must have correct attributes
    assert root.get("tilecount") == "47"
    assert root.get("columns") == "8"
    assert root.get("tilewidth") == "48"


# ---------------------------------------------------------------------------
# TC-018 — generate_tsx_simple image dimensions match tile grid
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_tc018_generate_tsx_simple_image_dimensions():
    from asset_convertor.exporters.tsx_generator import generate_tsx_simple

    xml_str = generate_tsx_simple(
        name="wall",
        tile_size=32,
        png_filename="wall.png",
        tile_count=16,
        columns=4,
    )
    root = ET.fromstring(xml_str)
    img_el = root.find("image")
    assert img_el is not None
    # 4 cols × 32 = 128; ceil(16/4)=4 rows × 32 = 128
    assert img_el.get("width") == "128"
    assert img_el.get("height") == "128"


# ---------------------------------------------------------------------------
# TC-019 — export_simple_sheet writes PNG + TSX to disk
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_tc019_export_simple_sheet_writes_files():
    from asset_convertor.exporters.tsx_generator import export_simple_sheet

    # 8 columns × 6 rows = 48 tiles at 48px
    sheet = Image.new("RGBA", (8 * 48, 6 * 48), (200, 100, 50, 255))
    with tempfile.TemporaryDirectory() as tmp:
        png_path, tsx_path = export_simple_sheet(sheet, "building_a3", tmp, 48, columns=8)
        assert Path(png_path).exists()
        assert Path(tsx_path).exists()

        xml_str = Path(tsx_path).read_text(encoding="utf-8")
        root = ET.fromstring(xml_str)
        assert root.get("name") == "building_a3"
        assert root.get("tilecount") == "48"  # 8×6
        assert root.get("columns") == "8"


# ---------------------------------------------------------------------------
# TC-020 — export_simple_sheet raises ValueError on bad dimensions
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_tc020_export_simple_sheet_bad_dimensions():
    from asset_convertor.exporters.tsx_generator import export_simple_sheet
    import pytest

    # Sheet width not divisible by tile_size
    bad_sheet = Image.new("RGBA", (100, 48), (0, 0, 0, 255))  # 100 not divisible by 48
    with tempfile.TemporaryDirectory() as tmp:
        with pytest.raises(ValueError, match="not divisible by tile_size"):
            export_simple_sheet(bad_sheet, "bad", tmp, tile_size=48, columns=2)
