"""Tests for the minimap bitmask engine (core/minimap.py).

Covers:
- TC-001 to TC-005: compute_bitmask grid scenarios
- TC-006 to TC-007: find_closest_bitmask_index lookups
- TC-008: generate_empty_grid dimensions
"""
from __future__ import annotations

from asset_creator.core.minimap import (
    compute_bitmask,
    find_closest_bitmask_index,
    generate_empty_grid,
)
from asset_creator.core.tile_assembler import BLOB_BITMASKS


class TestComputeBitmask:
    """Tests for compute_bitmask(grid, x, y)."""

    def test_tc001_empty_grid_all_zeros(self) -> None:
        """TC-001: Empty 4×4 grid → bitmask == 0 for all cells."""
        grid = [[False] * 4 for _ in range(4)]
        for y in range(4):
            for x in range(4):
                assert compute_bitmask(grid, x, y) == 0

    def test_tc002_single_filled_cell_no_neighbors(self) -> None:
        """TC-002: Single filled cell at (1,1) → bitmask == 0 (no filled neighbors)."""
        grid = [[False] * 4 for _ in range(4)]
        grid[1][1] = True
        assert compute_bitmask(grid, 1, 1) == 0

    def test_tc003_full_row_middle_cells(self) -> None:
        """TC-003: Full row of 4 filled cells → middle cells have W=8+E=16 → bitmask=24."""
        grid = [[False] * 4 for _ in range(4)]
        # Fill row at y=1
        grid[1] = [True, True, True, True]
        # Middle cells (x=1 and x=2) have W and E neighbors
        assert compute_bitmask(grid, 1, 1) == 8 + 16  # W=8, E=16 → 24
        assert compute_bitmask(grid, 2, 1) == 8 + 16  # W=8, E=16 → 24

    def test_tc004_2x2_block_correct_bitmasks(self) -> None:
        """TC-004: 2×2 block at (1,1),(2,1),(1,2),(2,2) → correct 3-neighbor bitmasks."""
        grid = [[False] * 4 for _ in range(4)]
        grid[1][1] = True
        grid[1][2] = True
        grid[2][1] = True
        grid[2][2] = True

        # (1,1): E=16 at (2,1), S=64 at (1,2), SE=128 at (2,2) [diagonal counts: S and E both filled]
        assert compute_bitmask(grid, 1, 1) == 16 + 64 + 128  # 208

        # (2,1): W=8 at (1,1), S=64 at (2,2), SW=32 at (1,2) [diagonal counts: S and W both filled]
        assert compute_bitmask(grid, 2, 1) == 8 + 64 + 32  # 104

        # (1,2): N=2 at (1,1), E=16 at (2,2), NE=4 at (2,1) [diagonal counts: N and E both filled]
        assert compute_bitmask(grid, 1, 2) == 2 + 16 + 4  # 22

        # (2,2): N=2 at (2,1), W=8 at (1,2), NW=1 at (1,1) [diagonal counts: N and W both filled]
        assert compute_bitmask(grid, 2, 2) == 2 + 8 + 1  # 11

    def test_tc005_full_grid_inner_cell_255(self) -> None:
        """TC-005: Full 4×4 grid → inner cells like (1,1) have bitmask == 255."""
        grid = [[True] * 4 for _ in range(4)]
        assert compute_bitmask(grid, 1, 1) == 255
        assert compute_bitmask(grid, 2, 2) == 255

    def test_full_grid_corner_cell(self) -> None:
        """Full grid, corner (0,0) has only E, S, SE → bitmask = 16+64+128 = 208."""
        grid = [[True] * 4 for _ in range(4)]
        assert compute_bitmask(grid, 0, 0) == 16 + 64 + 128  # 208

    def test_full_grid_edge_cell(self) -> None:
        """Full grid, top-edge (1,0) has W, E, SW, S, SE → bitmask = 8+16+32+64+128 = 248."""
        grid = [[True] * 4 for _ in range(4)]
        assert compute_bitmask(grid, 1, 0) == 8 + 16 + 32 + 64 + 128  # 248


class TestFindClosestBitmaskIndex:
    """Tests for find_closest_bitmask_index(bitmask)."""

    def test_tc006_exact_match(self) -> None:
        """TC-006: Exact match from BLOB_BITMASKS → returns exact index."""
        for idx, bitmask in enumerate(BLOB_BITMASKS):
            assert find_closest_bitmask_index(bitmask) == idx

    def test_tc007_closest_hamming(self) -> None:
        """TC-007: Bitmask NOT in BLOB_BITMASKS → returns closest by Hamming distance."""
        # Bitmask 1 is not in BLOB_BITMASKS. Closest by Hamming should be found.
        result = find_closest_bitmask_index(1)
        assert result in range(len(BLOB_BITMASKS))
        # Verify it's a valid index and the returned entry is indeed closest
        chosen_bm = BLOB_BITMASKS[result]
        chosen_dist = bin(1 ^ chosen_bm).count("1")
        for valid_bm in BLOB_BITMASKS:
            dist = bin(1 ^ valid_bm).count("1")
            assert dist >= chosen_dist

    def test_exact_match_zero(self) -> None:
        """Bitmask 0 is in BLOB_BITMASKS at index 0."""
        assert find_closest_bitmask_index(0) == 0

    def test_exact_match_255(self) -> None:
        """Bitmask 255 is in BLOB_BITMASKS at last index."""
        assert find_closest_bitmask_index(255) == len(BLOB_BITMASKS) - 1


class TestGenerateEmptyGrid:
    """Tests for generate_empty_grid(cols, rows)."""

    def test_tc008_dimensions(self) -> None:
        """TC-008: generate_empty_grid(10, 8) → 8 rows × 10 cols, all False."""
        grid = generate_empty_grid(10, 8)
        assert len(grid) == 8
        for row in grid:
            assert len(row) == 10
            assert all(cell is False for cell in row)

    def test_small_grid(self) -> None:
        """generate_empty_grid(2, 3) → 3 rows × 2 cols."""
        grid = generate_empty_grid(2, 3)
        assert len(grid) == 3
        for row in grid:
            assert len(row) == 2

    def test_all_false(self) -> None:
        """All cells in generated grid must be False."""
        grid = generate_empty_grid(5, 5)
        for row in grid:
            for cell in row:
                assert cell is False
