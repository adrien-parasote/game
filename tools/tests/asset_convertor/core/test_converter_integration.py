"""
TDD RED integration tests for the autotile converter pipeline.

Derived from: tools/docs/specs/autotile_converter_spec.md § Test Cases IT-001..IT-006
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
# IT-001 — XP full pipeline: load → convert → export
# ---------------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.skipif(not SAMPLE_XP.exists(), reason="sample_xp.png not found")
def test_it001_xp_full_pipeline():
    from asset_convertor.core.converter_xp import convert_xp
    from asset_convertor.exporters.tsx_generator import export

    img = Image.open(SAMPLE_XP).convert("RGBA")
    tiles = convert_xp(img)
    assert len(tiles) == 47

    with tempfile.TemporaryDirectory() as tmp:
        png_path, tsx_path = export(tiles, "grass_xp", tmp, 32)

        # PNG must exist and be 256x192
        png = Image.open(png_path)
        assert png.size == (256, 192), f"XP PNG size {png.size} != (256, 192)"

        # TSX must be valid with 47 wangtiles
        root = ET.parse(tsx_path).getroot()
        wangtiles = root.findall(".//wangtile")
        assert len(wangtiles) == 47, f"Expected 47 wangtiles, got {len(wangtiles)}"


# ---------------------------------------------------------------------------
# IT-002 — MV full pipeline: load → convert → export
# ---------------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.skipif(not SAMPLE_MV.exists(), reason="sample_mv_32px.png not found")
def test_it002_mv_full_pipeline():
    from asset_convertor.core.converter_mv import convert_mv
    from asset_convertor.exporters.tsx_generator import export

    img = Image.open(SAMPLE_MV).convert("RGBA")
    tiles = convert_mv(img)
    assert len(tiles) == 47

    with tempfile.TemporaryDirectory() as tmp:
        png_path, tsx_path = export(tiles, "grass_mv", tmp, 32)

        png = Image.open(png_path)
        assert png.size == (256, 192), f"MV PNG size {png.size} != (256, 192)"

        root = ET.parse(tsx_path).getroot()
        wangtiles = root.findall(".//wangtile")
        assert len(wangtiles) == 47


# ---------------------------------------------------------------------------
# IT-003 — XP output tiles cover all 47 bitmasks (all non-empty)
# ---------------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.skipif(not SAMPLE_XP.exists(), reason="sample_xp.png not found")
def test_it003_xp_all_tiles_non_empty():
    from asset_convertor.core.converter_xp import convert_xp

    img = Image.open(SAMPLE_XP).convert("RGBA")
    tiles = convert_xp(img)
    for i, tile in enumerate(tiles):
        pixels = list(tile.getdata())
        opaque = [px for px in pixels if px[3] > 0]
        assert len(opaque) > 0, f"Tile {i} (slot index {i}) is entirely transparent"


# ---------------------------------------------------------------------------
# IT-004 — Canvas pattern renders without error (25 cells, 5x5)
# ---------------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.skipif(not SAMPLE_XP.exists(), reason="sample_xp.png not found")
def test_it004_canvas_pattern_renders():
    """Verify that 25 cells can be assembled from the 47 output tiles without error."""
    from asset_convertor.core.converter_xp import BLOB_BITMASKS, convert_xp

    img = Image.open(SAMPLE_XP).convert("RGBA")
    tiles = convert_xp(img)

    bitmask_to_idx = {bm: idx for idx, bm in enumerate(BLOB_BITMASKS)}
    # 5x5 test pattern bitmasks (simplified: center surrounded)
    test_bitmasks = [
        [0, 2, 2, 2, 0],
        [8, 255, 255, 255, 16],
        [8, 255, 255, 255, 16],
        [8, 255, 255, 255, 16],
        [0, 64, 64, 64, 0],
    ]
    rendered_count = 0
    for row in test_bitmasks:
        for bm in row:
            # Find closest valid bitmask
            idx = bitmask_to_idx.get(bm, 0)
            tile = tiles[idx]
            assert tile is not None
            assert tile.size == (32, 32)
            rendered_count += 1
    assert rendered_count == 25


# ---------------------------------------------------------------------------
# IT-005 — TSX is valid XML with wangset type="mixed"
# ---------------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.skipif(not SAMPLE_XP.exists(), reason="sample_xp.png not found")
def test_it005_tsx_schema_valid():
    from asset_convertor.core.converter_xp import convert_xp
    from asset_convertor.exporters.tsx_generator import export

    img = Image.open(SAMPLE_XP).convert("RGBA")
    tiles = convert_xp(img)

    with tempfile.TemporaryDirectory() as tmp:
        _png, tsx_path = export(tiles, "test_terrain", tmp, 32)
        root = ET.parse(tsx_path).getroot()
        assert root.get("tilecount") is not None
        assert root.get("columns") is not None
        wangset = root.find(".//wangset")
        assert wangset is not None
        assert wangset.get("type") == "mixed"


# ---------------------------------------------------------------------------
# IT-006 — TSX wangtile entries match BLOB_BITMASKS order
# ---------------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.skipif(not SAMPLE_XP.exists(), reason="sample_xp.png not found")
def test_it006_tsx_wangtile_tileids_match_order():
    from asset_convertor.core.converter_xp import convert_xp
    from asset_convertor.exporters.tsx_generator import export

    img = Image.open(SAMPLE_XP).convert("RGBA")
    tiles = convert_xp(img)

    with tempfile.TemporaryDirectory() as tmp:
        _png, tsx_path = export(tiles, "test_terrain", tmp, 32)
        root = ET.parse(tsx_path).getroot()
        wangtiles = root.findall(".//wangtile")
        tileids = [int(wt.get("tileid")) for wt in wangtiles]
        assert tileids == list(range(47)), f"Wangtile ids not sequential 0..46: {tileids[:5]}..."


# ---------------------------------------------------------------------------
# IT-007 — MV 48px full pipeline: load -> detect -> convert -> export
# ---------------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.skipif(not SAMPLE_MV_48.exists(), reason="sample_mv_48px.png not found")
def test_it007_mv48_full_pipeline():
    from asset_convertor.core.converter_mv import convert_mv, detect_tile_size
    from asset_convertor.exporters.tsx_generator import export

    img = Image.open(SAMPLE_MV_48).convert("RGBA")
    assert detect_tile_size(img) == 48, "sample_mv_48px.png should auto-detect as 48px"

    tiles = convert_mv(img)
    assert len(tiles) == 47

    with tempfile.TemporaryDirectory() as tmp:
        png_path, tsx_path = export(tiles, "grass_mv48", tmp, 32)
        png = Image.open(png_path)
        assert png.size == (256, 192), f"MV48 PNG size {png.size} != (256, 192)"
        root = ET.parse(tsx_path).getroot()
        wangtiles = root.findall(".//wangtile")
        assert len(wangtiles) == 47


# ---------------------------------------------------------------------------
# IT-008 — MV 48px all output tiles are 32x32 RGBA (normalized from 48px)
# ---------------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.skipif(not SAMPLE_MV_48.exists(), reason="sample_mv_48px.png not found")
def test_it008_mv48_tiles_normalized_to_32():
    from asset_convertor.core.converter_mv import convert_mv

    img = Image.open(SAMPLE_MV_48).convert("RGBA")
    tiles = convert_mv(img)
    for i, tile in enumerate(tiles):
        assert tile.size == (32, 32), f"Tile {i} from 48px source: expected 32x32, got {tile.size}"
        assert tile.mode == "RGBA", f"Tile {i} mode {tile.mode!r} != 'RGBA'"


# ---------------------------------------------------------------------------
# IT-009 — MV 48px output tiles are non-empty (not all transparent)
# ---------------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.skipif(not SAMPLE_MV_48.exists(), reason="sample_mv_48px.png not found")
def test_it009_mv48_all_tiles_non_empty():
    from asset_convertor.core.converter_mv import convert_mv

    img = Image.open(SAMPLE_MV_48).convert("RGBA")
    tiles = convert_mv(img)
    for i, tile in enumerate(tiles):
        pixels = list(tile.getdata())
        opaque = [px for px in pixels if px[3] > 0]
        assert len(opaque) > 0, f"Tile {i} from 48px sample is entirely transparent"
