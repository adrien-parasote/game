import pytest
import pygame
from unittest.mock import MagicMock
from src.map.manager import MapManager

@pytest.fixture
def map_data():
    tile = MagicMock()
    tile.image = pygame.Surface((32, 32))
    tile.collidable = True
    tile.depth = 1
    
    return {
        "layers": {1: [[1, 0], [0, 0]]},
        "tiles": {1: tile},
        "layer_names": {1: "00-layer"},
        "layer_order": [1]
    }

def test_map_manager_init(map_data):
    layout = MagicMock()
    layout.tile_size = 32
    mm = MapManager(map_data, layout)
    assert mm.width == 2
    assert mm.height == 2
    assert mm.layer_order == [1]

def test_map_manager_collision(map_data):
    layout = MagicMock()
    mm = MapManager(map_data, layout)
    assert mm.is_collidable(0, 0) is True
    assert mm.is_collidable(1, 0) is False
    assert mm.is_collidable(-1, 0) is True # Out of bounds

def test_map_manager_render_layer(map_data):
    layout = MagicMock()
    layout.tile_size = 32
    layout.to_screen.return_value = (0, 0)
    mm = MapManager(map_data, layout)
    
    assert mm.width == 2
    assert mm.height == 2
    
    surface = mm.get_layer_surface(1, pygame)
    assert surface is not None
    # width_px = 2 * 32 = 64
    assert surface.get_width() == 64
    assert surface.get_height() == 64
