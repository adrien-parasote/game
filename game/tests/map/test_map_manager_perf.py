from unittest.mock import MagicMock

import pygame
import pytest
from src.map.layout import OrthogonalLayout
from src.map.manager import MapManager


@pytest.fixture
def dummy_layout():
    return OrthogonalLayout(32)


@pytest.mark.tc("TC-RPERF-U-006")
def test_build_anim_tile_layer_map_populates_dict(dummy_layout):
    """TC-RPERF-U-006: _build_anim_tile_layer_map populates the dict for animated tiles."""
    tile_mock = MagicMock()
    tile_mock.frames = [(1002, 100)]
    tile_mock.depth = 1

    map_data = {
        "layer_order": [7],
        "layers": {7: [[0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 1001, 0]]},
        "tiles": {1001: tile_mock},
    }
    manager = MapManager(map_data, dummy_layout)
    assert getattr(manager, "_anim_tile_layer_map", None) is not None
    assert manager._anim_tile_layer_map.get((2, 3)) == 7


@pytest.mark.tc("TC-RPERF-U-007")
def test_static_tile_absent_from_anim_layer_map(dummy_layout):
    """TC-RPERF-U-007: Static tiles are not included in _anim_tile_layer_map."""
    static_tile = MagicMock()
    static_tile.frames = None

    map_data = {"layer_order": [1], "layers": {1: [[50]]}, "tiles": {50: static_tile}}
    manager = MapManager(map_data, dummy_layout)
    assert getattr(manager, "_anim_tile_layer_map", None) is not None
    assert (0, 0) not in manager._anim_tile_layer_map


@pytest.mark.tc("TC-RPERF-U-013")
def test_map_has_grass_calculated_at_init(dummy_layout):
    """TC-RPERF-U-013: _map_has_grass is True if a grass tile exists."""
    grass_tile = MagicMock()
    grass_tile.properties = {"material": "grass"}
    grass_tile.depth = 0
    grass_tile.image = pygame.Surface((32, 32))

    map_data = {"layer_order": [1], "layers": {1: [[100]]}, "tiles": {100: grass_tile}}
    manager = MapManager(map_data, dummy_layout)
    assert getattr(manager, "_map_has_grass", None) is True


@pytest.mark.tc("TC-RPERF-U-014")
def test_map_has_grass_false_if_no_grass(dummy_layout):
    """TC-RPERF-U-014: _map_has_grass is False if no grass tile exists."""
    stone_tile = MagicMock()
    stone_tile.properties = {"material": "stone"}
    stone_tile.depth = 0
    stone_tile.image = pygame.Surface((32, 32))

    map_data = {"layer_order": [1], "layers": {1: [[100]]}, "tiles": {100: stone_tile}}
    manager = MapManager(map_data, dummy_layout)
    assert getattr(manager, "_map_has_grass", None) is False
