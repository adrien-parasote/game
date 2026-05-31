"""Integration tests for GUI pipeline functions.

Tests regenerate_tileset, export, canvas bitmask flow, and preset switching
WITHOUT requiring a DPG display. All tests use the headless pipeline functions.
"""

from __future__ import annotations

import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
from asset_creator.core.minimap import (
    compute_bitmask,
    find_closest_bitmask_index,
)
from asset_creator.core.terrain import get_builtin_presets
from asset_creator.gui.canvas import CanvasState
from asset_creator.gui.pipeline import regenerate_tileset, tiles_to_strip
from asset_creator.gui.state import state_from_preset
from PIL import Image


@pytest.fixture
def presets() -> dict:
    """Load builtin presets once per test."""
    return get_builtin_presets()


class TestIT001FullPipeline:
    """IT-001: Full pipeline produces 47 tiles of 32x32."""

    def test_regenerate_returns_47_tiles(self, presets: dict) -> None:
        state = state_from_preset("grass", presets)
        tiles = regenerate_tileset(state, presets)
        assert len(tiles) == 47

    def test_each_tile_is_32x32(self, presets: dict) -> None:
        state = state_from_preset("grass", presets)
        tiles = regenerate_tileset(state, presets)
        for i, tile in enumerate(tiles):
            assert tile.size == (32, 32), f"Tile {i} is {tile.size}, expected (32, 32)"

    def test_tiles_are_pil_images(self, presets: dict) -> None:
        state = state_from_preset("grass", presets)
        tiles = regenerate_tileset(state, presets)
        for tile in tiles:
            assert isinstance(tile, Image.Image)


class TestIT002CanvasBitmask:
    """IT-002: Paint 3x3 block, check center bitmask = 255."""

    def test_center_bitmask_all_neighbors(self) -> None:
        cs = CanvasState(cols=5, rows=5)
        # Paint 3x3 block at (1,1) to (3,3)
        for y in range(1, 4):
            for x in range(1, 4):
                cs.grid[y][x] = True
        # Center at (2,2) has all 8 neighbors filled
        bitmask = compute_bitmask(cs.grid, 2, 2)
        assert bitmask == 255

    def test_center_bitmask_maps_to_valid_index(self) -> None:
        idx = find_closest_bitmask_index(255)
        assert 0 <= idx <= 46


class TestIT003PresetSwitching:
    """IT-003: Switch preset grass → sand → grass, verify roundtrip."""

    def test_grass_sand_grass_roundtrip(self, presets: dict) -> None:
        state_grass1 = state_from_preset("grass", presets)
        _state_sand = state_from_preset("sand", presets)
        state_grass2 = state_from_preset("grass", presets)

        assert state_grass1.terrain_name == state_grass2.terrain_name
        assert state_grass1.scale == state_grass2.scale
        assert state_grass1.edge_style == state_grass2.edge_style
        assert state_grass1.detail_type == state_grass2.detail_type
        assert state_grass1 == state_grass2


class TestIT004Export:
    """IT-004: Generate + export to temp dir, verify PNG and TSX."""

    def test_export_creates_png_and_tsx(self, presets: dict) -> None:
        from asset_creator.gui.pipeline import do_export

        state = state_from_preset("grass", presets)
        tiles = regenerate_tileset(state, presets)

        with tempfile.TemporaryDirectory() as tmpdir:
            png_dir = Path(tmpdir) / "images"
            tsx_dir = Path(tmpdir) / "tiled"
            png_path, tsx_path = do_export(state, tiles, png_dir, tsx_dir)

            assert png_path.exists(), f"PNG not found: {png_path}"
            assert tsx_path.exists(), f"TSX not found: {tsx_path}"

    def test_exported_png_is_valid_image(self, presets: dict) -> None:
        from asset_creator.gui.pipeline import do_export

        state = state_from_preset("grass", presets)
        tiles = regenerate_tileset(state, presets)

        with tempfile.TemporaryDirectory() as tmpdir:
            png_dir = Path(tmpdir) / "images"
            tsx_dir = Path(tmpdir) / "tiled"
            png_path, _ = do_export(state, tiles, png_dir, tsx_dir)

            img = Image.open(png_path)
            assert img.width == 47 * 32
            assert img.height == 32

    def test_exported_tsx_is_valid_xml(self, presets: dict) -> None:
        from asset_creator.gui.pipeline import do_export

        state = state_from_preset("grass", presets)
        tiles = regenerate_tileset(state, presets)

        with tempfile.TemporaryDirectory() as tmpdir:
            png_dir = Path(tmpdir) / "images"
            tsx_dir = Path(tmpdir) / "tiled"
            _, tsx_path = do_export(state, tiles, png_dir, tsx_dir)

            tree = ET.parse(tsx_path)
            root = tree.getroot()
            assert root.tag == "tileset"


class TestIT006FullDataFlow:
    """IT-006: Full data flow — state → regenerate → verify tiles."""

    def test_full_data_flow(self, presets: dict) -> None:
        state = state_from_preset("grass", presets)
        tiles = regenerate_tileset(state, presets)
        assert len(tiles) == 47
        assert all(t.size == (32, 32) for t in tiles)

    def test_tiles_to_strip_roundtrip(self, presets: dict) -> None:
        state = state_from_preset("grass", presets)
        tiles = regenerate_tileset(state, presets)
        strip = tiles_to_strip(tiles, 32)
        assert strip.size == (47 * 32, 32)
