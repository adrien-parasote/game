"""Tests for tile assembler (TC-011 through TC-016).

Tests blob tile assembly from SubTileSet without depending
on the full palette/texture pipeline.
"""

from __future__ import annotations

import numpy as np
import pytest
from asset_creator.core.subtile import Quadrant, SubTileSet, SubTileType
from asset_creator.core.tile_assembler import (
    BLOB_BITMASKS,
    assemble_tile,
    assemble_tileset,
    blob_wang_id,
    select_subtile,
)
from PIL import Image

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_colored_subtile(r: int, g: int, b: int, alpha: int = 255) -> Image.Image:
    """Create a solid-color 16x16 RGBA image."""
    return Image.new("RGBA", (16, 16), (r, g, b, alpha))


@pytest.fixture
def mock_subtile_set() -> SubTileSet:
    """Create a SubTileSet with distinctly colored sub-tiles.

    Each (quadrant, type) pair gets a unique color so we can verify
    correct tile selection and placement.
    """
    tiles: dict[tuple[Quadrant, SubTileType], Image.Image] = {}
    color_idx = 0
    for quadrant in [Quadrant.TL, Quadrant.TR, Quadrant.BL, Quadrant.BR]:
        for tile_type in [
            SubTileType.FILL,
            SubTileType.EDGE_V,
            SubTileType.EDGE_H,
            SubTileType.OUTER_CORNER,
            SubTileType.INNER_CORNER,
        ]:
            # Use color_idx to create distinct colors
            r = (color_idx * 13) % 256
            g = (color_idx * 37) % 256
            b = (color_idx * 71) % 256
            tiles[(quadrant, tile_type)] = _make_colored_subtile(r, g, b)
            color_idx += 1
    return SubTileSet(tiles=tiles)


# ---------------------------------------------------------------------------
# TC-011: assemble_tileset produces strip with 47 tiles
# ---------------------------------------------------------------------------


@pytest.mark.tc("TC-011")
@pytest.mark.unit
class TestTilesetStrip:
    """TC-011: assemble_tileset produces strip with 47 tiles."""

    def test_strip_width(self, mock_subtile_set: SubTileSet) -> None:
        """Strip width should be 47 x 32 = 1504 pixels."""
        strip = assemble_tileset(mock_subtile_set)
        assert strip.size == (47 * 32, 32)

    def test_strip_mode(self, mock_subtile_set: SubTileSet) -> None:
        """Strip should be RGBA mode."""
        strip = assemble_tileset(mock_subtile_set)
        assert strip.mode == "RGBA"

    def test_bitmask_count(self) -> None:
        """BLOB_BITMASKS should contain exactly 47 entries."""
        assert len(BLOB_BITMASKS) == 47


# ---------------------------------------------------------------------------
# TC-012: All tiles are 32x32 RGBA
# ---------------------------------------------------------------------------


@pytest.mark.tc("TC-012")
@pytest.mark.unit
class TestTileDimensions:
    """TC-012: All assembled tiles are 32x32 RGBA."""

    @pytest.mark.parametrize("bitmask", BLOB_BITMASKS)
    def test_tile_size_and_mode(
        self,
        mock_subtile_set: SubTileSet,
        bitmask: int,
    ) -> None:
        tile = assemble_tile(mock_subtile_set, bitmask)
        assert tile.size == (32, 32), f"Expected 32x32 for bitmask {bitmask}"
        assert tile.mode == "RGBA", f"Expected RGBA for bitmask {bitmask}"


# ---------------------------------------------------------------------------
# TC-013: Bitmask 0 (isolated) uses OUTER_CORNER for all quadrants
# ---------------------------------------------------------------------------


@pytest.mark.tc("TC-013")
@pytest.mark.unit
class TestIsolatedTile:
    """TC-013: Bitmask 0 (isolated) uses OUTER_CORNER for all quadrants."""

    def test_all_quadrants_are_outer_corner(
        self,
        mock_subtile_set: SubTileSet,
    ) -> None:
        """With no neighbors, all quadrants should use OUTER_CORNER."""
        # Verify select_subtile returns OUTER_CORNER for each quadrant
        for quadrant, args in [
            (Quadrant.TL, (False, False, False)),
            (Quadrant.TR, (False, False, False)),
            (Quadrant.BL, (False, False, False)),
            (Quadrant.BR, (False, False, False)),
        ]:
            result = select_subtile(mock_subtile_set, quadrant, *args)
            expected = mock_subtile_set.get(quadrant, SubTileType.OUTER_CORNER)
            assert np.array_equal(np.array(result), np.array(expected)), (
                f"Bitmask 0: {quadrant.value} should be OUTER_CORNER"
            )

    def test_assembled_tile_matches(
        self,
        mock_subtile_set: SubTileSet,
    ) -> None:
        """The assembled tile for bitmask 0 should be composed of 4 OUTER_CORNERs."""
        tile = assemble_tile(mock_subtile_set, 0)
        arr = np.array(tile)

        tl = np.array(mock_subtile_set.get(Quadrant.TL, SubTileType.OUTER_CORNER))
        tr = np.array(mock_subtile_set.get(Quadrant.TR, SubTileType.OUTER_CORNER))
        bl = np.array(mock_subtile_set.get(Quadrant.BL, SubTileType.OUTER_CORNER))
        br = np.array(mock_subtile_set.get(Quadrant.BR, SubTileType.OUTER_CORNER))

        assert np.array_equal(arr[0:16, 0:16], tl)
        assert np.array_equal(arr[0:16, 16:32], tr)
        assert np.array_equal(arr[16:32, 0:16], bl)
        assert np.array_equal(arr[16:32, 16:32], br)


# ---------------------------------------------------------------------------
# TC-014: Bitmask 255 (full center) uses FILL for all quadrants
# ---------------------------------------------------------------------------


@pytest.mark.tc("TC-014")
@pytest.mark.unit
class TestFullCenterTile:
    """TC-014: Bitmask 255 (full center) uses FILL for all quadrants."""

    def test_all_quadrants_are_fill(
        self,
        mock_subtile_set: SubTileSet,
    ) -> None:
        """With all neighbors present, all quadrants should use FILL."""
        for quadrant, args in [
            (Quadrant.TL, (True, True, True)),
            (Quadrant.TR, (True, True, True)),
            (Quadrant.BL, (True, True, True)),
            (Quadrant.BR, (True, True, True)),
        ]:
            result = select_subtile(mock_subtile_set, quadrant, *args)
            expected = mock_subtile_set.get(quadrant, SubTileType.FILL)
            assert np.array_equal(np.array(result), np.array(expected)), (
                f"Bitmask 255: {quadrant.value} should be FILL"
            )

    def test_assembled_tile_matches(
        self,
        mock_subtile_set: SubTileSet,
    ) -> None:
        """The assembled tile for bitmask 255 should be composed of 4 FILLs."""
        tile = assemble_tile(mock_subtile_set, 255)
        arr = np.array(tile)

        tl = np.array(mock_subtile_set.get(Quadrant.TL, SubTileType.FILL))
        tr = np.array(mock_subtile_set.get(Quadrant.TR, SubTileType.FILL))
        bl = np.array(mock_subtile_set.get(Quadrant.BL, SubTileType.FILL))
        br = np.array(mock_subtile_set.get(Quadrant.BR, SubTileType.FILL))

        assert np.array_equal(arr[0:16, 0:16], tl)
        assert np.array_equal(arr[0:16, 16:32], tr)
        assert np.array_equal(arr[16:32, 0:16], bl)
        assert np.array_equal(arr[16:32, 16:32], br)


# ---------------------------------------------------------------------------
# TC-015: blob_wang_id correctness
# ---------------------------------------------------------------------------


@pytest.mark.tc("TC-015")
@pytest.mark.unit
class TestBlobWangId:
    """TC-015: blob_wang_id produces correct Tiled wangid strings.

    Tiled wangid order: Top, TopRight, Right, BottomRight, Bottom,
    BottomLeft, Left, TopLeft (L-MAP-002).
    """

    @pytest.mark.parametrize(
        ("bitmask", "expected_wangid"),
        [
            (0, "0,0,0,0,0,0,0,0"),
            (255, "1,1,1,1,1,1,1,1"),
            (2, "1,0,0,0,0,0,0,0"),  # N only
            (18, "1,0,1,0,0,0,0,0"),  # N + E
            (22, "1,1,1,0,0,0,0,0"),  # N + E + NE
        ],
    )
    def test_known_values(self, bitmask: int, expected_wangid: str) -> None:
        assert blob_wang_id(bitmask) == expected_wangid

    def test_all_47_bitmasks_produce_valid_wangid(self) -> None:
        """All 47 bitmasks should produce a wangid with 8 comma-separated 0/1 values."""
        for bitmask in BLOB_BITMASKS:
            wangid = blob_wang_id(bitmask)
            parts = wangid.split(",")
            assert len(parts) == 8, f"Bitmask {bitmask}: expected 8 parts, got {len(parts)}"
            for part in parts:
                assert part in ("0", "1"), f"Bitmask {bitmask}: unexpected value '{part}' in wangid"


# ---------------------------------------------------------------------------
# TC-016: No tile in the strip is fully transparent
# ---------------------------------------------------------------------------


@pytest.mark.tc("TC-016")
@pytest.mark.unit
class TestNoFullyTransparentTile:
    """TC-016: No tile in the strip is fully transparent (L-MAP-003)."""

    def test_no_fully_transparent_tile(
        self,
        mock_subtile_set: SubTileSet,
    ) -> None:
        strip = assemble_tileset(mock_subtile_set)
        strip_arr = np.array(strip)
        for idx in range(47):
            tile_slice = strip_arr[:, idx * 32 : (idx + 1) * 32, 3]
            assert np.any(tile_slice > 0), (
                f"Tile at index {idx} (bitmask {BLOB_BITMASKS[idx]}) is fully transparent"
            )


# ---------------------------------------------------------------------------
# Additional selection logic tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestSelectSubtile:
    """Test the select_subtile dispatch logic."""

    def test_cardinal1_only_returns_edge_v(
        self,
        mock_subtile_set: SubTileSet,
    ) -> None:
        """Only vertical neighbor → EDGE_V."""
        result = select_subtile(mock_subtile_set, Quadrant.TL, True, False, False)
        expected = mock_subtile_set.get(Quadrant.TL, SubTileType.EDGE_V)
        assert np.array_equal(np.array(result), np.array(expected))

    def test_cardinal2_only_returns_edge_h(
        self,
        mock_subtile_set: SubTileSet,
    ) -> None:
        """Only horizontal neighbor → EDGE_H."""
        result = select_subtile(mock_subtile_set, Quadrant.TL, False, True, False)
        expected = mock_subtile_set.get(Quadrant.TL, SubTileType.EDGE_H)
        assert np.array_equal(np.array(result), np.array(expected))

    def test_both_cardinals_with_diagonal_returns_fill(
        self,
        mock_subtile_set: SubTileSet,
    ) -> None:
        """Both cardinals + diagonal → FILL."""
        result = select_subtile(mock_subtile_set, Quadrant.TL, True, True, True)
        expected = mock_subtile_set.get(Quadrant.TL, SubTileType.FILL)
        assert np.array_equal(np.array(result), np.array(expected))

    def test_both_cardinals_without_diagonal_returns_inner_corner(
        self,
        mock_subtile_set: SubTileSet,
    ) -> None:
        """Both cardinals without diagonal → INNER_CORNER."""
        result = select_subtile(mock_subtile_set, Quadrant.TL, True, True, False)
        expected = mock_subtile_set.get(Quadrant.TL, SubTileType.INNER_CORNER)
        assert np.array_equal(np.array(result), np.array(expected))

    def test_no_neighbors_returns_outer_corner(
        self,
        mock_subtile_set: SubTileSet,
    ) -> None:
        """No neighbors → OUTER_CORNER."""
        result = select_subtile(mock_subtile_set, Quadrant.BR, False, False, False)
        expected = mock_subtile_set.get(Quadrant.BR, SubTileType.OUTER_CORNER)
        assert np.array_equal(np.array(result), np.array(expected))
