import pytest
import math
import pygame
from unittest.mock import MagicMock, patch
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


@pytest.fixture
def map_manager(map_data):
    layout = MagicMock()
    layout.tile_size = 32
    layout.to_screen.side_effect = lambda x, y: (x * 32, y * 32)
    return MapManager(map_data, layout)


# --- Init ---

def test_map_manager_init(map_data):
    layout = MagicMock()
    layout.tile_size = 32
    mm = MapManager(map_data, layout)
    assert mm.width == 2
    assert mm.height == 2
    assert mm.layer_order == [1]


def test_map_manager_empty_layers():
    """MapManager with no layers: width and height are 0."""
    mm = MapManager({"layers": {}, "tiles": {}, "layer_names": {}, "layer_order": []}, MagicMock())
    assert mm.width == 0
    assert mm.height == 0


# --- is_collidable ---

def test_map_manager_collision(map_data):
    layout = MagicMock()
    mm = MapManager(map_data, layout)
    assert mm.is_collidable(0, 0) is True
    assert mm.is_collidable(1, 0) is False
    assert mm.is_collidable(-1, 0) is True  # Out of bounds


# --- get_layer_surface ---

def test_map_manager_render_layer(map_manager):
    """First render creates surface of correct size."""
    surface = map_manager.get_layer_surface(1, pygame)
    assert surface is not None
    assert surface.get_width() == 64  # 2 * 32
    assert surface.get_height() == 64


def test_map_manager_render_layer_cached(map_manager):
    """Second call returns cached surface (same object)."""
    surface_first = map_manager.get_layer_surface(1, pygame)
    surface_second = map_manager.get_layer_surface(1, pygame)
    assert surface_first is surface_second


def test_map_manager_render_layer_exception(map_data):
    """get_layer_surface returns None when pygame.Surface raises."""
    layout = MagicMock()
    layout.tile_size = 32
    mm = MapManager(map_data, layout)

    mock_pygame = MagicMock()
    mock_pygame.SRCALPHA = pygame.SRCALPHA
    mock_pygame.Surface.side_effect = Exception("surface error")

    result = mm.get_layer_surface(1, mock_pygame)
    assert result is None


# --- get_visible_chunks ---

def test_get_visible_chunks_full_viewport(map_manager):
    """Full viewport yields all non-zero tiles with correct depth."""
    viewport = MagicMock()
    viewport.left = 0
    viewport.right = 64
    viewport.top = 0
    viewport.bottom = 64

    chunks = list(map_manager.get_visible_chunks(viewport))
    # Only tile at (0,0) is non-zero (tile_id=1)
    assert len(chunks) == 1
    px, py, tile_id, depth = chunks[0]
    assert tile_id == 1
    assert depth == 1


def test_get_visible_chunks_outside_viewport(map_manager):
    """Viewport far from tiles yields no chunks."""
    viewport = MagicMock()
    viewport.left = 1000
    viewport.right = 1064
    viewport.top = 1000
    viewport.bottom = 1064

    chunks = list(map_manager.get_visible_chunks(viewport))
    assert chunks == []


def test_get_visible_chunks_partial_viewport(map_manager):
    """Partial viewport covering only empty tiles yields no chunks."""
    viewport = MagicMock()
    viewport.left = 32   # starts at column 1 (only zeros)
    viewport.right = 64
    viewport.top = 0
    viewport.bottom = 32

    chunks = list(map_manager.get_visible_chunks(viewport))
    assert chunks == []

