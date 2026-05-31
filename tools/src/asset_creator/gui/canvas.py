"""Canvas grid state and coordinate helpers.

Manages the paint canvas grid for both autotile and standalone modes.
DPG-specific rendering lives in app.py — this module is testable without DPG.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from asset_creator.core.minimap import generate_empty_grid


@dataclass
class CanvasState:
    """Mutable canvas state for the paint grid.

    Attributes:
        cols: Number of grid columns.
        rows: Number of grid rows.
        mode: Drawing mode — "autotile" or "standalone".
        grid: Boolean grid for autotile mode (grid[y][x]).
        tile_grid: Tile index grid for standalone mode (-1 = empty).
        selected_tile_index: Currently selected tile for standalone painting.
    """

    cols: int = 16
    rows: int = 12
    mode: str = "autotile"  # "autotile" | "standalone"
    grid: list[list[bool]] = field(default_factory=list)
    tile_grid: list[list[int]] = field(default_factory=list)
    selected_tile_index: int = 0

    def __post_init__(self) -> None:
        if not self.grid:
            self.grid = generate_empty_grid(self.cols, self.rows)
        if not self.tile_grid:
            self.tile_grid = [[-1] * self.cols for _ in range(self.rows)]

    def clear(self) -> None:
        """Reset both grids to empty state, preserving dimensions."""
        self.grid = generate_empty_grid(self.cols, self.rows)
        self.tile_grid = [[-1] * self.cols for _ in range(self.rows)]


def grid_to_canvas_coords(
    px: float,
    py: float,
    cell_size: int,
) -> tuple[int, int]:
    """Convert pixel coordinates to grid cell indices.

    Negative pixel values are clamped to 0.

    Args:
        px: Pixel x coordinate relative to canvas origin.
        py: Pixel y coordinate relative to canvas origin.
        cell_size: Size of each grid cell in pixels.

    Returns:
        Tuple of (grid_x, grid_y) indices.
    """
    gx = max(0, int(px) // cell_size)
    gy = max(0, int(py) // cell_size)
    return gx, gy
