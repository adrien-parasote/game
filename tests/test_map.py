import pytest
from src.map.layout import OrthogonalLayout

def test_orthogonal_layout_to_screen():
    layout = OrthogonalLayout(tile_size=32)
    # Check origin
    assert layout.to_screen(0, 0) == (0, 0)
    # Check (1, 1) tile
    assert layout.to_screen(1, 1) == (32, 32)
    # Check (2, -1) tile
    assert layout.to_screen(2, -1) == (64, -32)

def test_orthogonal_to_world():
    layout = OrthogonalLayout(tile_size=32)
    assert layout.to_world(32, 32) == (1.0, 1.0)
    assert layout.to_world(16, 16) == (0.5, 0.5)

from src.map.manager import MapManager

def test_map_manager_loading():
    # Multilayer map data
    map_data = {
        "layers": {
            0: [
                [1, 1, 1],
                [1, 0, 1],
                [1, 1, 1]
            ]
        },
        "tiles": {
            0: type('TileMapData', (), {'depth': 0, 'collidable': False})(),
            1: type('TileMapData', (), {'depth': 2, 'collidable': True})()
        }
    }
    layout = OrthogonalLayout(32)
    manager = MapManager(map_data, layout)
    
    assert manager.width == 3
    assert manager.height == 3
    
    # get_tile(layer_id, x, y)
    assert manager.get_tile(0, 1, 1) == 0
    assert manager.get_tile(0, 0, 0) == 1
    
    # is_collidable(x, y) checking across all layers
    assert manager.is_collidable(0, 0) is True
    assert manager.is_collidable(1, 1) is False

def test_map_manager_tile_at_px():
    map_data = {"layers": {0: [[1]]}, "tiles": {1: type('TileMapData', (), {'depth': 0, 'collidable': False})()}}
    layout = OrthogonalLayout(32)
    manager = MapManager(map_data, layout)
    
    # Pixel (16, 16) should be tile (0, 0) on layer 0
    assert manager.get_tile_at_px(0, 16, 16) == 1
    # Pixel (64, 64) should be None or out of bounds
    assert manager.get_tile_at_px(0, 64, 64) is None

import pygame
def test_map_manager_visible_chunks():
    # 10x10 map, tiles of 32px
    map_data = {
        "layers": {
            0: [[2 for _ in range(10)] for _ in range(10)],
            1: [[1 for _ in range(10)] for _ in range(10)] # multiple layers
        },
        "tiles": {
            2: type('TileMapData', (), {'depth': 0, 'collidable': False})(),
            1: type('TileMapData', (), {'depth': 2, 'collidable': False})()
        }
    }
    layout = OrthogonalLayout(32)
    manager = MapManager(map_data, layout)
    
    # Viewport at (32, 32), size 64x64 (covers tiles from index 1 to 2 inclusive in both axes)
    viewport = pygame.Rect(32, 32, 64, 64)
    visible_tiles = list(manager.get_visible_chunks(viewport))
    
    # Expected indices: x in [1, 2], y in [1, 2] -> 4 tiles total * 2 layers = 8 iterations
    assert len(visible_tiles) == 8
    # All positions should be within (32, 32) and (64, 64)
    for px, py, tile_id, depth in visible_tiles:
        assert 32 <= px <= 64
        assert 32 <= py <= 64
        assert depth in (0, 2)
