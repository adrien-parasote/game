"""Pygame-based preview for generated tilesets.

Shows the tileset strip and a simulated mini-map using the generated tiles.
Press ESC or close the window to exit.
"""
from __future__ import annotations

import random
import sys
from typing import TYPE_CHECKING

from tools.asset_creator.core.tile_assembler import BLOB_BITMASKS

if TYPE_CHECKING:
    from PIL import Image
    from pygame import Surface

    from tools.asset_creator.core.subtile import SubTileSet

try:
    import pygame
except ImportError:
    pygame = None  # type: ignore[assignment]


TILE_SIZE = 32
GRID_COLS = 12
GRID_ROWS = 8
MINIMAP_MARGIN = 16
STRIP_HEIGHT_AREA = TILE_SIZE + 20
BG_COLOR = (30, 30, 30)
GRID_COLOR = (50, 50, 50)
TEXT_COLOR = (200, 200, 200)


def _pil_to_surface(pil_image: Image.Image) -> Surface:
    """Convert a PIL RGBA Image to a Pygame Surface."""
    if pygame is None:
        raise RuntimeError("Pygame is not installed")
    raw = pil_image.tobytes("raw", "RGBA")
    surface = pygame.image.fromstring(
        raw, pil_image.size, "RGBA",
    )
    return surface


def _generate_minimap_grid(cols: int, rows: int) -> list[list[bool]]:
    """Generate a random terrain grid for the mini-map preview."""
    grid: list[list[bool]] = []
    for _y in range(rows):
        row: list[bool] = []
        for _x in range(cols):
            row.append(random.random() > 0.3)
        grid.append(row)
    return grid


def _compute_bitmask_for_cell(
    grid: list[list[bool]], x: int, y: int,
) -> int:
    """Compute the blob bitmask for a cell in the grid."""
    rows = len(grid)
    cols = len(grid[0])

    def _get(dx: int, dy: int) -> bool:
        nx, ny = x + dx, y + dy
        if 0 <= nx < cols and 0 <= ny < rows:
            return grid[ny][nx]
        return False

    n = _get(0, -1)
    s = _get(0, 1)
    w = _get(-1, 0)
    e = _get(1, 0)
    nw = _get(-1, -1) and n and w
    ne = _get(1, -1) and n and e
    sw = _get(-1, 1) and s and w
    se = _get(1, 1) and s and e

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


def _find_closest_bitmask_index(bitmask: int) -> int:
    """Find the index of the closest valid bitmask in BLOB_BITMASKS."""
    if bitmask in BLOB_BITMASKS:
        return BLOB_BITMASKS.index(bitmask)
    # Fallback: find closest by popcount distance
    best_idx = 0
    best_dist = 256
    for idx, valid_bm in enumerate(BLOB_BITMASKS):
        dist = bin(bitmask ^ valid_bm).count("1")
        if dist < best_dist:
            best_dist = dist
            best_idx = idx
    return best_idx


def _extract_tile_surfaces(strip_surface: Surface) -> list[Surface]:
    """Extract individual tiles from the strip surface."""
    if pygame is None:
        raise RuntimeError("Pygame is not installed")
    tile_surfaces: list[Surface] = []
    tile_count = strip_surface.get_width() // TILE_SIZE
    for i in range(tile_count):
        sub = strip_surface.subsurface(
            pygame.Rect(i * TILE_SIZE, 0, TILE_SIZE, TILE_SIZE),
        )
        tile_surfaces.append(sub.copy())
    return tile_surfaces


def _draw_minimap(
    screen: Surface,
    grid: list[list[bool]],
    tile_surfaces: list[Surface],
    map_x: int,
    map_y: int,
) -> None:
    """Draw the mini-map preview grid."""
    if pygame is None:
        raise RuntimeError("Pygame is not installed")
    for gy in range(GRID_ROWS):
        for gx in range(GRID_COLS):
            px = map_x + gx * TILE_SIZE
            py = map_y + gy * TILE_SIZE

            if grid[gy][gx]:
                bitmask = _compute_bitmask_for_cell(grid, gx, gy)
                tile_idx = _find_closest_bitmask_index(bitmask)
                if tile_idx < len(tile_surfaces):
                    screen.blit(tile_surfaces[tile_idx], (px, py))
            else:
                pygame.draw.rect(
                    screen, GRID_COLOR,
                    (px, py, TILE_SIZE, TILE_SIZE), 1,
                )


def run_preview(
    tileset_image: Image.Image,
    subtile_set: SubTileSet | None = None,
) -> None:
    """Run the Pygame preview window.

    Displays:
    - Top: the 47-tile strip
    - Bottom: a simulated mini-map showing tiles in context

    Args:
        tileset_image: The assembled tileset strip (47×32, 32).
        subtile_set: Optional SubTileSet (unused in current version).
    """
    if pygame is None:
        sys.stderr.write("ERROR: pygame-ce is required for preview.\n")
        return

    minimap_w = GRID_COLS * TILE_SIZE
    minimap_h = GRID_ROWS * TILE_SIZE

    strip_w = tileset_image.width
    win_w = max(strip_w, minimap_w) + MINIMAP_MARGIN * 2
    win_h = STRIP_HEIGHT_AREA + MINIMAP_MARGIN * 3 + minimap_h + 40

    pygame.init()
    screen = pygame.display.set_mode((win_w, win_h))
    pygame.display.set_caption("Asset Creator — Preview")

    strip_surface = _pil_to_surface(tileset_image)
    tile_surfaces = _extract_tile_surfaces(strip_surface)
    grid = _generate_minimap_grid(GRID_COLS, GRID_ROWS)
    font = pygame.font.Font(None, 20)

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_SPACE:
                    grid = _generate_minimap_grid(GRID_COLS, GRID_ROWS)

        screen.fill(BG_COLOR)

        # ── Draw strip ────────────────────────────────────────────────
        strip_x = (win_w - strip_w) // 2
        strip_y = MINIMAP_MARGIN
        label = font.render("Tileset Strip (47 blob tiles)", True, TEXT_COLOR)
        screen.blit(label, (strip_x, strip_y - 2))
        screen.blit(strip_surface, (strip_x, strip_y + 16))

        # ── Draw mini-map ─────────────────────────────────────────────
        map_x = (win_w - minimap_w) // 2
        map_y = STRIP_HEIGHT_AREA + MINIMAP_MARGIN * 2 + 10

        label2 = font.render(
            "Mini-map Preview (SPACE = regenerate, ESC = quit)",
            True, TEXT_COLOR,
        )
        screen.blit(label2, (map_x, map_y - 16))

        _draw_minimap(screen, grid, tile_surfaces, map_x, map_y)

        pygame.display.flip()
        pygame.time.Clock().tick(30)

    pygame.quit()
