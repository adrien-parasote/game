"""Tests for MapManager — material queries and grass tile image lookup."""

from unittest.mock import MagicMock

import pygame
from src.map import manager


def test_manager_import():
    assert True


# ===========================================================================
# Helpers
# ===========================================================================

def _make_tile(material: str | None = None, depth: int = 0) -> MagicMock:
    """Build a mock tile with the given material property and depth."""
    tile = MagicMock()
    tile.depth = depth
    tile.image = pygame.Surface((32, 32))
    tile.properties = {"material": material} if material else {}
    return tile


def _make_map_manager(
    tile: MagicMock | None,
    *,
    grid_x: int = 1,
    grid_y: int = 1,
    map_w: int = 5,
    map_h: int = 5,
) -> manager.MapManager:
    """Build a MapManager with a single layer containing `tile` at (grid_x, grid_y)."""
    tile_id = 99 if tile is not None else 0

    # Build a 5×5 grid with the tile at (grid_x, grid_y)
    grid = [[0] * map_w for _ in range(map_h)]
    if tile_id != 0:
        grid[grid_y][grid_x] = tile_id

    layout = MagicMock()
    # to_world returns (col, row) for the probe position
    layout.to_world.return_value = (grid_x, grid_y)
    layout.tile_size = 32

    map_data = {
        "layers": {"layer_0": grid},
        "tiles": {tile_id: tile} if tile is not None else {},
        "layer_names": {},
        "entities": [],
        "layer_order": ["layer_0"],
        "layer_order_values": {"layer_0": 0},
        "properties": {},
    }
    mm = manager.MapManager(map_data, layout)
    return mm


# ===========================================================================
# GW-MM-001 — grass tile with depth=0 → returns tile.image
# ===========================================================================
def test_get_grass_tile_image_at_grass_depth0_returns_surface():
    """GW-MM-001: Tile with material='grass' and depth=0 → returns tile.image Surface."""
    tile = _make_tile(material="grass", depth=0)
    mm = _make_map_manager(tile)

    result = mm.get_grass_tile_image_at(40, 40)  # probe inside grid

    assert result is tile.image


# ===========================================================================
# GW-MM-002 — dirt tile → returns None
# ===========================================================================
def test_get_grass_tile_image_at_dirt_returns_none():
    """GW-MM-002: Tile with material='dirt' → returns None."""
    tile = _make_tile(material="dirt", depth=0)
    mm = _make_map_manager(tile)

    result = mm.get_grass_tile_image_at(40, 40)

    assert result is None


# ===========================================================================
# GW-MM-003 — grass tile with depth=2 (roof) → returns None
# ===========================================================================
def test_get_grass_tile_image_at_grass_roof_depth2_returns_none():
    """GW-MM-003: Tile with material='grass' but depth=2 (roof) → None (roof skipped)."""
    tile = _make_tile(material="grass", depth=2)
    mm = _make_map_manager(tile)

    result = mm.get_grass_tile_image_at(40, 40)

    assert result is None


# ===========================================================================
# GW-MM-004 — pixel coords out of bounds → returns None, no crash
# ===========================================================================
def test_get_grass_tile_image_at_out_of_bounds_returns_none():
    """GW-MM-004: Pixel coords out of map bounds → None, no IndexError."""
    tile = _make_tile(material="grass", depth=0)
    mm = _make_map_manager(tile)

    # Override to_world to return out-of-bounds coords
    mm.layout.to_world.return_value = (-1, -1)

    result = mm.get_grass_tile_image_at(-32, -32)

    assert result is None


# ===========================================================================
# GW-MM-005 — tile_id == 0 (empty cell) → returns None
# ===========================================================================
def test_get_grass_tile_image_at_empty_cell_returns_none():
    """GW-MM-005: No tile at position (tile_id=0) → returns None."""
    mm = _make_map_manager(None)  # empty cell

    result = mm.get_grass_tile_image_at(40, 40)

    assert result is None


# ===========================================================================
# GW-MM-006 — two stacked layers: top=dirt(depth=0), bottom=grass(depth=0) → None
# ===========================================================================
def test_get_grass_tile_image_at_top_dirt_bottom_grass_returns_none():
    """GW-MM-006: Top layer=dirt, bottom=grass → None (top layer dirt wins)."""
    tile_dirt = _make_tile(material="dirt", depth=0)
    tile_grass = _make_tile(material="grass", depth=0)

    grid = [[0] * 5 for _ in range(5)]
    grid[1][1] = 10  # dirt (top layer, higher order)
    grid_bottom = [[0] * 5 for _ in range(5)]
    grid_bottom[1][1] = 11  # grass (bottom layer)

    layout = MagicMock()
    layout.to_world.return_value = (1, 1)
    layout.tile_size = 32

    map_data = {
        "layers": {"layer_top": grid, "layer_bottom": grid_bottom},
        "tiles": {10: tile_dirt, 11: tile_grass},
        "layer_names": {},
        "entities": [],
        "layer_order": ["layer_bottom", "layer_top"],
        "layer_order_values": {"layer_bottom": 0, "layer_top": 1},
        "properties": {},
    }
    mm = manager.MapManager(map_data, layout)

    result = mm.get_grass_tile_image_at(40, 40)

    # Top layer (dirt) wins — result must be None
    assert result is None


# ===========================================================================
# GW-MM-007 — two stacked layers: top=roof(depth=2), bottom=grass(depth=0) → grass image
# ===========================================================================
def test_get_grass_tile_image_at_top_roof_bottom_grass_returns_grass():
    """GW-MM-007: Top layer=roof(depth=2), bottom=grass(depth=0) → grass image (roof skipped)."""
    tile_roof = _make_tile(material="stone", depth=2)
    tile_grass = _make_tile(material="grass", depth=0)

    grid_top = [[0] * 5 for _ in range(5)]
    grid_top[1][1] = 20  # roof

    grid_bottom = [[0] * 5 for _ in range(5)]
    grid_bottom[1][1] = 21  # grass

    layout = MagicMock()
    layout.to_world.return_value = (1, 1)
    layout.tile_size = 32

    map_data = {
        "layers": {"layer_top": grid_top, "layer_bottom": grid_bottom},
        "tiles": {20: tile_roof, 21: tile_grass},
        "layer_names": {},
        "entities": [],
        "layer_order": ["layer_bottom", "layer_top"],
        "layer_order_values": {"layer_bottom": 0, "layer_top": 1},
        "properties": {},
    }
    mm = manager.MapManager(map_data, layout)

    result = mm.get_grass_tile_image_at(40, 40)

    # Roof (depth=2) is skipped → grass is returned
    assert result is tile_grass.image
