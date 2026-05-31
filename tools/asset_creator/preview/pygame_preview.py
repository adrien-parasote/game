"""Pygame-based preview for generated tilesets.

Shows the tileset strip and a simulated mini-map using the generated tiles.
Press ESC or close the window to exit.
"""
from __future__ import annotations

import random
import sys
from typing import TYPE_CHECKING

from tools.asset_creator.core.constants import (
    PREVIEW_BG_COLOR,
    PREVIEW_GRID_COLOR,
    PREVIEW_GRID_COLS,
    PREVIEW_GRID_ROWS,
    PREVIEW_MINIMAP_MARGIN,
    PREVIEW_TEXT_COLOR,
    TILE_SIZE,
)
from tools.asset_creator.core.minimap import (
    compute_bitmask,
    find_closest_bitmask_index,
)

if TYPE_CHECKING:
    from PIL import Image
    from pygame import Surface

    from tools.asset_creator.core.subtile import SubTileSet

try:
    import pygame
except ImportError:
    pygame = None  # type: ignore[assignment]


STRIP_HEIGHT_AREA = TILE_SIZE + 20


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
    for gy in range(PREVIEW_GRID_ROWS):
        for gx in range(PREVIEW_GRID_COLS):
            px = map_x + gx * TILE_SIZE
            py = map_y + gy * TILE_SIZE

            if grid[gy][gx]:
                bitmask = compute_bitmask(grid, gx, gy)
                tile_idx = find_closest_bitmask_index(bitmask)
                if tile_idx < len(tile_surfaces):
                    screen.blit(tile_surfaces[tile_idx], (px, py))
            else:
                pygame.draw.rect(
                    screen, PREVIEW_GRID_COLOR,
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

    minimap_w = PREVIEW_GRID_COLS * TILE_SIZE
    minimap_h = PREVIEW_GRID_ROWS * TILE_SIZE

    strip_w = tileset_image.width
    win_w = max(strip_w, minimap_w) + PREVIEW_MINIMAP_MARGIN * 2
    win_h = STRIP_HEIGHT_AREA + PREVIEW_MINIMAP_MARGIN * 3 + minimap_h + 40

    pygame.init()
    screen = pygame.display.set_mode((win_w, win_h))
    pygame.display.set_caption("Asset Creator — Preview")

    strip_surface = _pil_to_surface(tileset_image)
    tile_surfaces = _extract_tile_surfaces(strip_surface)
    grid = _generate_minimap_grid(PREVIEW_GRID_COLS, PREVIEW_GRID_ROWS)
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
                    grid = _generate_minimap_grid(PREVIEW_GRID_COLS, PREVIEW_GRID_ROWS)

        screen.fill(PREVIEW_BG_COLOR)

        # ── Draw strip ────────────────────────────────────────────────
        strip_x = (win_w - strip_w) // 2
        strip_y = PREVIEW_MINIMAP_MARGIN
        label = font.render("Tileset Strip (47 blob tiles)", True, PREVIEW_TEXT_COLOR)
        screen.blit(label, (strip_x, strip_y - 2))
        screen.blit(strip_surface, (strip_x, strip_y + 16))

        # ── Draw mini-map ─────────────────────────────────────────────
        map_x = (win_w - minimap_w) // 2
        map_y = STRIP_HEIGHT_AREA + PREVIEW_MINIMAP_MARGIN * 2 + 10

        label2 = font.render(
            "Mini-map Preview (SPACE = regenerate, ESC = quit)",
            True, PREVIEW_TEXT_COLOR,
        )
        screen.blit(label2, (map_x, map_y - 16))

        _draw_minimap(screen, grid, tile_surfaces, map_x, map_y)

        pygame.display.flip()
        pygame.time.Clock().tick(30)

    pygame.quit()
