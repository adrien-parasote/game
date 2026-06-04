"""
TDD RED tests for asset_convertor.exporters.tsx_generator

Derived from: tools/docs/specs/autotile_converter_spec.md § Test Cases TC-021..TC-035
"""

import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
from PIL import Image


def _make_tiles(count: int = 47, size: int = 32, color: tuple = (0, 128, 0, 255)) -> list:
    """Create list of count uniform RGBA tiles."""
    return [Image.new("RGBA", (size, size), color) for _ in range(count)]


def _make_distinct_tiles(count: int = 47, size: int = 32) -> list:
    """Create tiles each filled with a unique color."""
    tiles = []
    for i in range(count):
        r = (i * 37) % 256
        g = (i * 73) % 256
        b = (i * 113) % 256
        tiles.append(Image.new("RGBA", (size, size), (r, g, b, 255)))
    return tiles


# ---------------------------------------------------------------------------
# TC-021 — assemble_sheet returns correct dimensions (32px)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_tc021_sheet_dimensions_32px():
    from asset_convertor.exporters.tsx_generator import assemble_sheet

    tiles = _make_tiles(47, 32)
    sheet = assemble_sheet(tiles, 32)
    assert sheet.size == (256, 192), f"Expected (256, 192), got {sheet.size}"


# ---------------------------------------------------------------------------
# TC-022 — assemble_sheet returns correct dimensions (48px)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_tc022_sheet_dimensions_48px():
    from asset_convertor.exporters.tsx_generator import assemble_sheet

    tiles = _make_tiles(47, 48)
    sheet = assemble_sheet(tiles, 48)
    assert sheet.size == (384, 288), f"Expected (384, 288), got {sheet.size}"


# ---------------------------------------------------------------------------
# TC-023 — assemble_sheet places tile[0] at (0,0)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_tc023_tile0_at_origin():
    from asset_convertor.exporters.tsx_generator import assemble_sheet

    tiles = _make_distinct_tiles(47, 32)
    sheet = assemble_sheet(tiles, 32)
    expected = tiles[0].getpixel((0, 0))
    actual = sheet.getpixel((0, 0))
    assert actual == expected, f"Tile[0] at (0,0): expected {expected}, got {actual}"


# ---------------------------------------------------------------------------
# TC-024 — assemble_sheet places tile[8] at col=0, row=1
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_tc024_tile8_at_row1():
    from asset_convertor.exporters.tsx_generator import assemble_sheet

    tiles = _make_distinct_tiles(47, 32)
    sheet = assemble_sheet(tiles, 32)
    expected = tiles[8].getpixel((0, 0))
    actual = sheet.getpixel((0, 32))  # row=1, col=0
    assert actual == expected, f"Tile[8] at (0,32): expected {expected}, got {actual}"


# ---------------------------------------------------------------------------
# TC-025 — assemble_sheet slot 47 is transparent
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_tc025_slot47_is_transparent():
    from asset_convertor.exporters.tsx_generator import assemble_sheet

    tiles = _make_tiles(47, 32, color=(255, 0, 0, 255))
    sheet = assemble_sheet(tiles, 32)
    # Slot 47 = col=7, row=5 -> pixel at (7*32 + center, 5*32 + center)
    # Sheet is 8 cols x 6 rows = 48 slots; slot 47 = last (col=7, row=5)
    px = sheet.getpixel((7 * 32 + 16, 5 * 32 + 16))
    assert px[3] == 0, f"Slot 47 center pixel should be transparent (alpha=0), got alpha={px[3]}"


# ---------------------------------------------------------------------------
# TC-026 — bitmask_to_wangid(0) returns all-zero
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_tc026_bitmask_to_wangid_0():
    from asset_convertor.exporters.tsx_generator import bitmask_to_wangid

    assert bitmask_to_wangid(0) == "0,0,0,0,0,0,0,0"


# ---------------------------------------------------------------------------
# TC-027 — bitmask_to_wangid(255) returns all-one
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_tc027_bitmask_to_wangid_255():
    from asset_convertor.exporters.tsx_generator import bitmask_to_wangid

    assert bitmask_to_wangid(255) == "1,1,1,1,1,1,1,1"


# ---------------------------------------------------------------------------
# TC-028 — bitmask_to_wangid(N only) — N bit active
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_tc028_bitmask_to_wangid_n_only():
    from asset_convertor.exporters.tsx_generator import bitmask_to_wangid

    # In the existing convention: N=2 (bit 1)
    # wangid order: [top, topRight, right, bottomRight, bottom, bottomLeft, left, topLeft]
    # N=top → first position = 1, rest = 0
    result = bitmask_to_wangid(2)  # N=2
    parts = result.split(",")
    assert parts[0] == "1", f"N bit should set top=1, got {result}"
    assert all(p == "0" for p in parts[1:]), f"Only top should be 1, got {result}"


# ---------------------------------------------------------------------------
# TC-029 — generate_tsx XML is valid
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_tc029_generate_tsx_is_valid_xml():
    from asset_convertor.exporters.tsx_generator import generate_tsx

    tiles = _make_tiles(47, 32)
    xml_str = generate_tsx("test_tileset", 32, "test_tileset.png")
    # Must parse without error
    root = ET.fromstring(xml_str)
    assert root.tag == "tileset"


# ---------------------------------------------------------------------------
# TC-030 — generate_tsx has exactly 47 wangtile entries
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_tc030_generate_tsx_has_47_wangtiles():
    from asset_convertor.exporters.tsx_generator import generate_tsx

    xml_str = generate_tsx("test_tileset", 32, "test_tileset.png")
    root = ET.fromstring(xml_str)
    wangtiles = root.findall(".//wangtile")
    assert len(wangtiles) == 47, f"Expected 47 wangtiles, got {len(wangtiles)}"


# ---------------------------------------------------------------------------
# TC-031 — generate_tsx wangset type is "mixed"
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_tc031_wangset_type_is_mixed():
    from asset_convertor.exporters.tsx_generator import generate_tsx

    xml_str = generate_tsx("test_tileset", 32, "test_tileset.png")
    root = ET.fromstring(xml_str)
    wangset = root.find(".//wangset")
    assert wangset is not None
    assert wangset.get("type") == "mixed", f"Expected type='mixed', got {wangset.get('type')!r}"


# ---------------------------------------------------------------------------
# TC-032 — export creates PNG file
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_tc032_export_creates_png():
    from asset_convertor.exporters.tsx_generator import export

    tiles = _make_tiles(47, 32)
    with tempfile.TemporaryDirectory() as tmp:
        png_path, _tsx_path = export(tiles, "terrain", tmp, 32)
        assert Path(png_path).exists(), f"PNG not found at {png_path}"


# ---------------------------------------------------------------------------
# TC-033 — export creates TSX file
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_tc033_export_creates_tsx():
    from asset_convertor.exporters.tsx_generator import export

    tiles = _make_tiles(47, 32)
    with tempfile.TemporaryDirectory() as tmp:
        _png_path, tsx_path = export(tiles, "terrain", tmp, 32)
        assert Path(tsx_path).exists(), f"TSX not found at {tsx_path}"


# ---------------------------------------------------------------------------
# TC-034 — export raises OSError for non-writable dir
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_tc034_export_raises_oserror_for_bad_dir():
    from asset_convertor.exporters.tsx_generator import export

    tiles = _make_tiles(47, 32)
    with pytest.raises((OSError, PermissionError)):
        export(tiles, "terrain", "/root/nope_cannot_write_here", 32)


# ---------------------------------------------------------------------------
# TC-035 — export raises ValueError for != 47 tiles
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_tc035_export_raises_for_wrong_tile_count():
    from asset_convertor.exporters.tsx_generator import export

    tiles = _make_tiles(46, 32)  # 46, not 47
    with tempfile.TemporaryDirectory() as tmp, pytest.raises(ValueError, match=r"47"):
        export(tiles, "terrain", tmp, 32)
