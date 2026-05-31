"""Tests for the canvas module.

Tests CanvasState initialization, grid manipulation, clear behavior,
mode switching, and coordinate conversion — no DPG required.
"""
from __future__ import annotations

import pytest

from tools.asset_creator.gui.canvas import CanvasState, grid_to_canvas_coords


class TestCanvasStateInit:
    """Test CanvasState initialization."""

    def test_default_dimensions(self) -> None:
        cs = CanvasState()
        assert cs.cols == 16
        assert cs.rows == 12

    def test_default_mode(self) -> None:
        cs = CanvasState()
        assert cs.mode == "autotile"

    def test_grid_initialised_empty(self) -> None:
        cs = CanvasState()
        assert len(cs.grid) == 12
        assert len(cs.grid[0]) == 16
        assert all(not cell for row in cs.grid for cell in row)

    def test_tile_grid_initialised_empty(self) -> None:
        cs = CanvasState()
        assert len(cs.tile_grid) == 12
        assert len(cs.tile_grid[0]) == 16
        assert all(cell == -1 for row in cs.tile_grid for cell in row)

    def test_custom_dimensions(self) -> None:
        cs = CanvasState(cols=8, rows=6)
        assert len(cs.grid) == 6
        assert len(cs.grid[0]) == 8
        assert len(cs.tile_grid) == 6
        assert len(cs.tile_grid[0]) == 8

    def test_selected_tile_index_default(self) -> None:
        cs = CanvasState()
        assert cs.selected_tile_index == 0


class TestCanvasStateClear:
    """Test CanvasState.clear() resets grids."""

    def test_clear_resets_autotile_grid(self) -> None:
        cs = CanvasState(cols=4, rows=4)
        cs.grid[1][2] = True
        cs.clear()
        assert all(not cell for row in cs.grid for cell in row)

    def test_clear_resets_tile_grid(self) -> None:
        cs = CanvasState(cols=4, rows=4)
        cs.tile_grid[1][2] = 5
        cs.clear()
        assert all(cell == -1 for row in cs.tile_grid for cell in row)

    def test_clear_preserves_dimensions(self) -> None:
        cs = CanvasState(cols=8, rows=6)
        cs.grid[0][0] = True
        cs.clear()
        assert len(cs.grid) == 6
        assert len(cs.grid[0]) == 8


class TestCanvasStateGridManipulation:
    """Test direct grid manipulation in autotile mode."""

    def test_paint_cell(self) -> None:
        cs = CanvasState(cols=4, rows=4)
        cs.grid[2][3] = True
        assert cs.grid[2][3] is True

    def test_erase_cell(self) -> None:
        cs = CanvasState(cols=4, rows=4)
        cs.grid[2][3] = True
        cs.grid[2][3] = False
        assert cs.grid[2][3] is False

    def test_standalone_place_tile(self) -> None:
        cs = CanvasState(cols=4, rows=4, mode="standalone")
        cs.tile_grid[1][1] = 5
        assert cs.tile_grid[1][1] == 5

    def test_standalone_erase_tile(self) -> None:
        cs = CanvasState(cols=4, rows=4, mode="standalone")
        cs.tile_grid[1][1] = 5
        cs.tile_grid[1][1] = -1
        assert cs.tile_grid[1][1] == -1


class TestGridToCanvasCoords:
    """Test pixel-to-grid coordinate conversion."""

    def test_origin(self) -> None:
        gx, gy = grid_to_canvas_coords(0.0, 0.0, 32)
        assert gx == 0
        assert gy == 0

    def test_first_cell(self) -> None:
        gx, gy = grid_to_canvas_coords(16.0, 16.0, 32)
        assert gx == 0
        assert gy == 0

    def test_second_cell(self) -> None:
        gx, gy = grid_to_canvas_coords(33.0, 33.0, 32)
        assert gx == 1
        assert gy == 1

    def test_exact_boundary(self) -> None:
        gx, gy = grid_to_canvas_coords(32.0, 0.0, 32)
        assert gx == 1
        assert gy == 0

    def test_negative_coords_clamped(self) -> None:
        gx, gy = grid_to_canvas_coords(-5.0, -5.0, 32)
        assert gx == 0
        assert gy == 0
