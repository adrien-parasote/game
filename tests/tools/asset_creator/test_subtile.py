"""Tests for sub-tile generation (TC-007 through TC-010).

Tests the SubTileSet structure and edge mask generation
without depending on the full palette/texture pipeline.
"""
from __future__ import annotations

import numpy as np
import pytest
from PIL import Image

from tools.asset_creator.core.subtile import (
    Quadrant,
    SubTileSet,
    SubTileType,
    generate_subtiles,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def base_texture_32() -> Image.Image:
    """Create a simple 32×32 RGBA texture for testing.

    Uses distinct colors per quadrant so we can verify correct cropping.
    """
    img = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
    pixels = img.load()
    assert pixels is not None
    for y in range(32):
        for x in range(32):
            if x < 16 and y < 16:
                pixels[x, y] = (100, 50, 50, 255)   # TL red-ish
            elif x >= 16 and y < 16:
                pixels[x, y] = (50, 100, 50, 255)   # TR green-ish
            elif x < 16 and y >= 16:
                pixels[x, y] = (50, 50, 100, 255)   # BL blue-ish
            else:
                pixels[x, y] = (100, 100, 50, 255)  # BR yellow-ish
    return img


@pytest.fixture()
def organic_edge_config() -> dict[str, object]:
    """Edge config with organic (simplex noise) style."""
    return {"style": "organic", "width": 4, "noise_scale": 0.3}


@pytest.fixture()
def straight_edge_config() -> dict[str, object]:
    """Edge config with straight (no noise) style."""
    return {"style": "straight", "width": 4, "noise_scale": 0.0}


@pytest.fixture()
def subtile_set_organic(
    base_texture_32: Image.Image,
    organic_edge_config: dict[str, object],
) -> SubTileSet:
    """Generate a SubTileSet with organic edges."""
    return generate_subtiles(base_texture_32, organic_edge_config, seed=42)


@pytest.fixture()
def subtile_set_straight(
    base_texture_32: Image.Image,
    straight_edge_config: dict[str, object],
) -> SubTileSet:
    """Generate a SubTileSet with straight edges."""
    return generate_subtiles(base_texture_32, straight_edge_config, seed=42)


# ---------------------------------------------------------------------------
# TC-007: SubTileSet contains all 20 sub-tiles
# ---------------------------------------------------------------------------

ALL_QUADRANTS = [Quadrant.TL, Quadrant.TR, Quadrant.BL, Quadrant.BR]
ALL_TYPES = [
    SubTileType.FILL,
    SubTileType.EDGE_V,
    SubTileType.EDGE_H,
    SubTileType.OUTER_CORNER,
    SubTileType.INNER_CORNER,
]


@pytest.mark.tc("TC-007")
@pytest.mark.unit
class TestSubTileSetCompleteness:
    """TC-007: SubTileSet contains all 20 sub-tiles (4 quadrants × 5 types)."""

    def test_contains_all_20_entries(self, subtile_set_organic: SubTileSet) -> None:
        """All 20 (quadrant, type) combinations must be present."""
        for quadrant in ALL_QUADRANTS:
            for tile_type in ALL_TYPES:
                tile = subtile_set_organic.get(quadrant, tile_type)
                assert tile is not None, (
                    f"Missing sub-tile for ({quadrant.value}, {tile_type.value})"
                )

    def test_tile_count_is_20(self, subtile_set_organic: SubTileSet) -> None:
        """The tiles dict must have exactly 20 entries."""
        assert len(subtile_set_organic.tiles) == 20


# ---------------------------------------------------------------------------
# TC-008: All sub-tiles are 16×16 RGBA
# ---------------------------------------------------------------------------

@pytest.mark.tc("TC-008")
@pytest.mark.unit
class TestSubTileDimensions:
    """TC-008: All sub-tiles are 16×16 RGBA."""

    @pytest.mark.parametrize("quadrant", ALL_QUADRANTS)
    @pytest.mark.parametrize("tile_type", ALL_TYPES)
    def test_size_and_mode(
        self,
        subtile_set_organic: SubTileSet,
        quadrant: Quadrant,
        tile_type: SubTileType,
    ) -> None:
        tile = subtile_set_organic.get(quadrant, tile_type)
        assert tile.size == (16, 16), (
            f"Expected 16×16, got {tile.size} for ({quadrant.value}, {tile_type.value})"
        )
        assert tile.mode == "RGBA", (
            f"Expected RGBA, got {tile.mode} for ({quadrant.value}, {tile_type.value})"
        )


# ---------------------------------------------------------------------------
# TC-009: No sub-tile is fully transparent (L-MAP-003)
# ---------------------------------------------------------------------------

@pytest.mark.tc("TC-009")
@pytest.mark.unit
class TestSubTileNotFullyTransparent:
    """TC-009: No sub-tile is fully transparent.

    FILL must be fully opaque.
    EDGE/CORNER tiles must have at least 1 pixel with alpha > 0.
    """

    @pytest.mark.parametrize("quadrant", ALL_QUADRANTS)
    def test_fill_is_fully_opaque(
        self,
        subtile_set_organic: SubTileSet,
        quadrant: Quadrant,
    ) -> None:
        tile = subtile_set_organic.get(quadrant, SubTileType.FILL)
        alpha = np.array(tile)[:, :, 3]
        assert np.all(alpha == 255), (
            f"FILL for {quadrant.value} has non-opaque pixels"
        )

    @pytest.mark.parametrize("quadrant", ALL_QUADRANTS)
    @pytest.mark.parametrize(
        "tile_type",
        [SubTileType.EDGE_V, SubTileType.EDGE_H, SubTileType.OUTER_CORNER, SubTileType.INNER_CORNER],
    )
    def test_edge_corner_not_fully_transparent(
        self,
        subtile_set_organic: SubTileSet,
        quadrant: Quadrant,
        tile_type: SubTileType,
    ) -> None:
        tile = subtile_set_organic.get(quadrant, tile_type)
        alpha = np.array(tile)[:, :, 3]
        assert np.any(alpha > 0), (
            f"Sub-tile ({quadrant.value}, {tile_type.value}) is fully transparent"
        )


# ---------------------------------------------------------------------------
# TC-010: Edge mask correctness
# ---------------------------------------------------------------------------

@pytest.mark.tc("TC-010")
@pytest.mark.unit
class TestEdgeMaskCorrectness:
    """TC-010: Edge mask correctness with straight edges (no noise)."""

    def test_fill_center_opaque(self, subtile_set_straight: SubTileSet) -> None:
        """FILL center pixels are fully opaque (alpha=255)."""
        for quadrant in ALL_QUADRANTS:
            tile = subtile_set_straight.get(quadrant, SubTileType.FILL)
            alpha = np.array(tile)[:, :, 3]
            # All pixels should be opaque for FILL
            assert np.all(alpha == 255), (
                f"FILL for {quadrant.value} has transparent pixels"
            )

    def test_edge_v_tl_left_transparent_right_opaque(
        self,
        subtile_set_straight: SubTileSet,
    ) -> None:
        """EDGE_V for TL quadrant: x=0 transparent, x=15 opaque."""
        tile = subtile_set_straight.get(Quadrant.TL, SubTileType.EDGE_V)
        alpha = np.array(tile)[:, :, 3]
        # Left edge (x=0) should be transparent
        assert np.all(alpha[:, 0] == 0), (
            "EDGE_V TL: pixels at x=0 should be transparent"
        )
        # Right side (x=15) should be opaque
        assert np.all(alpha[:, 15] == 255), (
            "EDGE_V TL: pixels at x=15 should be opaque"
        )

    def test_edge_v_tr_right_transparent_left_opaque(
        self,
        subtile_set_straight: SubTileSet,
    ) -> None:
        """EDGE_V for TR quadrant: x=15 transparent, x=0 opaque."""
        tile = subtile_set_straight.get(Quadrant.TR, SubTileType.EDGE_V)
        alpha = np.array(tile)[:, :, 3]
        # Right edge (x=15) should be transparent
        assert np.all(alpha[:, 15] == 0), (
            "EDGE_V TR: pixels at x=15 should be transparent"
        )
        # Left side (x=0) should be opaque
        assert np.all(alpha[:, 0] == 255), (
            "EDGE_V TR: pixels at x=0 should be opaque"
        )

    def test_edge_h_tl_top_transparent_bottom_opaque(
        self,
        subtile_set_straight: SubTileSet,
    ) -> None:
        """EDGE_H for TL quadrant: y=0 transparent, y=15 opaque."""
        tile = subtile_set_straight.get(Quadrant.TL, SubTileType.EDGE_H)
        alpha = np.array(tile)[:, :, 3]
        # Top edge (y=0) should be transparent
        assert np.all(alpha[0, :] == 0), (
            "EDGE_H TL: pixels at y=0 should be transparent"
        )
        # Bottom (y=15) should be opaque
        assert np.all(alpha[15, :] == 255), (
            "EDGE_H TL: pixels at y=15 should be opaque"
        )

    def test_outer_corner_tl_corner_transparent(
        self,
        subtile_set_straight: SubTileSet,
    ) -> None:
        """OUTER_CORNER: corner pixel (0,0 for TL) should be transparent."""
        tile = subtile_set_straight.get(Quadrant.TL, SubTileType.OUTER_CORNER)
        alpha = np.array(tile)[:, :, 3]
        assert alpha[0, 0] == 0, (
            "OUTER_CORNER TL: pixel (0,0) should be transparent"
        )

    def test_outer_corner_br_corner_transparent(
        self,
        subtile_set_straight: SubTileSet,
    ) -> None:
        """OUTER_CORNER: corner pixel (15,15 for BR) should be transparent."""
        tile = subtile_set_straight.get(Quadrant.BR, SubTileType.OUTER_CORNER)
        alpha = np.array(tile)[:, :, 3]
        assert alpha[15, 15] == 0, (
            "OUTER_CORNER BR: pixel (15,15) should be transparent"
        )


# ---------------------------------------------------------------------------
# Additional edge style tests
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestEdgeStyles:
    """Verify different edge styles produce valid sub-tile sets."""

    def test_dithered_style(self, base_texture_32: Image.Image) -> None:
        """Dithered edge style should produce valid sub-tiles."""
        config = {"style": "dithered", "width": 4, "noise_scale": 0.0}
        result = generate_subtiles(base_texture_32, config, seed=42)
        assert len(result.tiles) == 20

    def test_deterministic_with_same_seed(
        self, base_texture_32: Image.Image, organic_edge_config: dict[str, object],
    ) -> None:
        """Same seed should produce identical results."""
        result_a = generate_subtiles(base_texture_32, organic_edge_config, seed=123)
        result_b = generate_subtiles(base_texture_32, organic_edge_config, seed=123)
        for quadrant in ALL_QUADRANTS:
            for tile_type in ALL_TYPES:
                arr_a = np.array(result_a.get(quadrant, tile_type))
                arr_b = np.array(result_b.get(quadrant, tile_type))
                assert np.array_equal(arr_a, arr_b), (
                    f"Non-deterministic for ({quadrant.value}, {tile_type.value})"
                )

    def test_different_seeds_produce_different_results(
        self, base_texture_32: Image.Image, organic_edge_config: dict[str, object],
    ) -> None:
        """Different seeds should produce different edge patterns."""
        result_a = generate_subtiles(base_texture_32, organic_edge_config, seed=1)
        result_b = generate_subtiles(base_texture_32, organic_edge_config, seed=999)
        # At least one edge sub-tile should differ
        any_different = False
        for quadrant in ALL_QUADRANTS:
            for tile_type in [SubTileType.EDGE_V, SubTileType.EDGE_H]:
                arr_a = np.array(result_a.get(quadrant, tile_type))
                arr_b = np.array(result_b.get(quadrant, tile_type))
                if not np.array_equal(arr_a, arr_b):
                    any_different = True
                    break
            if any_different:
                break
        assert any_different, "Different seeds should produce different edge patterns"
