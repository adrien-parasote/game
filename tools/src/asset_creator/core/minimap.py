"""Minimap bitmask engine for terrain grids.

Provides bitmask computation and lookup for Wang blob tilesets.
Extracted from preview/pygame_preview.py for reuse in GUI and CLI.

Bitmask layout: NW=1, N=2, NE=4, W=8, E=16, SW=32, S=64, SE=128.
Diagonals only count if both adjacent cardinals are filled.
"""

from __future__ import annotations

from asset_creator.core.tile_assembler import BLOB_BITMASKS


def generate_empty_grid(cols: int, rows: int) -> list[list[bool]]:
    """Generate an empty terrain grid (all False).

    Args:
        cols: Number of columns (width).
        rows: Number of rows (height).

    Returns:
        A grid of ``rows`` lists, each containing ``cols`` False values.
    """
    return [[False] * cols for _ in range(rows)]


def compute_bitmask(grid: list[list[bool]], x: int, y: int) -> int:
    """Compute the 8-direction Wang blob bitmask for a cell.

    Checks the 8 surrounding neighbors. Diagonal neighbors only count
    when both adjacent cardinal neighbors are also filled.

    Layout: NW=1, N=2, NE=4, W=8, E=16, SW=32, S=64, SE=128.

    Args:
        grid: 2D boolean grid (grid[y][x]).
        x: Column index of the cell.
        y: Row index of the cell.

    Returns:
        8-bit bitmask (0–255).
    """  # noqa: RUF002
    rows = len(grid)
    cols = len(grid[0])

    def _filled(dx: int, dy: int) -> bool:
        nx, ny = x + dx, y + dy
        if 0 <= nx < cols and 0 <= ny < rows:
            return grid[ny][nx]
        return False

    n = _filled(0, -1)
    s = _filled(0, 1)
    w = _filled(-1, 0)
    e = _filled(1, 0)
    nw = _filled(-1, -1) and n and w
    ne = _filled(1, -1) and n and e
    sw = _filled(-1, 1) and s and w
    se = _filled(1, 1) and s and e

    return (
        int(nw)
        | (int(n) << 1)
        | (int(ne) << 2)
        | (int(w) << 3)
        | (int(e) << 4)
        | (int(sw) << 5)
        | (int(s) << 6)
        | (int(se) << 7)
    )


def find_closest_bitmask_index(bitmask: int) -> int:
    """Find the index of the closest valid bitmask in BLOB_BITMASKS.

    Tries an exact match first. If not found, selects the entry with
    the smallest Hamming distance (fewest differing bits).

    Args:
        bitmask: 8-bit bitmask to look up.

    Returns:
        Index into BLOB_BITMASKS (0–46).
    """  # noqa: RUF002
    if bitmask in BLOB_BITMASKS:
        return BLOB_BITMASKS.index(bitmask)

    best_idx = 0
    best_dist = 256
    for idx, valid_bm in enumerate(BLOB_BITMASKS):
        dist = bin(bitmask ^ valid_bm).count("1")
        if dist < best_dist:
            best_dist = dist
            best_idx = idx
    return best_idx
