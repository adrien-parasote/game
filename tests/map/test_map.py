"""Tests for Map system: layers, collision, MapManager, layout."""

from unittest.mock import MagicMock, patch

import pygame
import pytest

from src.map.layout import OrthogonalLayout
from src.map.manager import MapManager
from src.map.tmj_parser import TmjParser

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


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
        "layer_order": [1],
    }


@pytest.fixture
def map_manager(map_data):
    layout = MagicMock()
    layout.tile_size = 32
    layout.to_screen.side_effect = lambda x, y: (x * 32, y * 32)
    layout.to_world.side_effect = lambda x, y: (x // 32, y // 32)
    return MapManager(map_data, layout)


# ---------------------------------------------------------------------------
# Layer parsing & ordering (TmjParser)
# ---------------------------------------------------------------------------


def test_layer_recursive_order():
    """Nested group layers are found and sorted by name prefix."""
    parser = TmjParser()
    mock_data = {
        "width": 2,
        "height": 2,
        "tilewidth": 32,
        "tileheight": 32,
        "layers": [
            {"type": "group", "name": "Sprites", "layers": []},
            {
                "type": "group",
                "name": "Layers",
                "layers": [
                    {
                        "id": 3,
                        "name": "02-layer",
                        "type": "tilelayer",
                        "data": [0, 0, 0, 0],
                        "width": 2,
                        "height": 2,
                        "opacity": 1,
                        "visible": True,
                    },
                    {
                        "id": 2,
                        "name": "01-layer",
                        "type": "tilelayer",
                        "data": [0, 0, 0, 0],
                        "width": 2,
                        "height": 2,
                        "opacity": 1,
                        "visible": True,
                    },
                    {
                        "id": 1,
                        "name": "00-layer",
                        "type": "tilelayer",
                        "data": [0, 0, 0, 0],
                        "width": 2,
                        "height": 2,
                        "opacity": 1,
                        "visible": True,
                    },
                ],
            },
        ],
        "tilesets": [],
    }
    result = {
        "layers": {},
        "layer_order": [],
        "layer_names": {},
        "tiles": {},
        "width": 2,
        "height": 2,
        "tile_size": 32,
    }
    parser._process_layers(mock_data["layers"], 2, result)

    assert 1 in result["layer_names"]
    assert 2 in result["layer_names"]
    assert 3 in result["layer_names"]

    manager = MapManager(result, OrthogonalLayout(32))
    assert manager.layer_order == [1, 2, 3]


# ---------------------------------------------------------------------------
# Collision detection
# ---------------------------------------------------------------------------


def test_map_manager_collision_basics():
    """Collision detection works across layers using tile coordinates."""
    map_d = {
        "layers": {1: [[1, 0], [0, 0]]},
        "tiles": {1: MagicMock(collidable=True)},
        "width": 2,
        "height": 2,
        "tile_size": 32,
    }
    manager = MapManager(map_d, OrthogonalLayout(32))
    assert manager.is_collidable(0, 0) is True
    assert manager.is_collidable(1, 0) is False


def test_map_manager_collision_out_of_bounds(map_data):
    layout = MagicMock()
    mm = MapManager(map_data, layout)
    assert mm.is_collidable(0, 0) is True
    assert mm.is_collidable(1, 0) is False
    assert mm.is_collidable(-1, 0) is True  # Out of bounds → collidable


# ---------------------------------------------------------------------------
# Layout
# ---------------------------------------------------------------------------


def test_orthogonal_layout():
    layout = OrthogonalLayout(32)
    assert layout.to_screen(1, 1) == (32, 32)
    assert layout.to_world(64, 64) == (2, 2)


# ---------------------------------------------------------------------------
# MapManager: init & empty
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# MapManager: get_layer_surface
# ---------------------------------------------------------------------------


def test_map_manager_render_layer(map_manager):
    """First render creates surface of correct size."""
    surface = map_manager.get_layer_surface(1, pygame)
    assert surface is not None
    assert surface.get_width() == 64
    assert surface.get_height() == 64


def test_map_manager_render_layer_cached(map_manager):
    """Second call returns cached surface (same object)."""
    s1 = map_manager.get_layer_surface(1, pygame)
    s2 = map_manager.get_layer_surface(1, pygame)
    assert s1 is s2


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


# ---------------------------------------------------------------------------
# MapManager: get_visible_chunks
# ---------------------------------------------------------------------------


def test_get_visible_chunks_full_viewport(map_manager):
    """Full viewport yields all non-zero tiles."""
    viewport = MagicMock()
    viewport.left, viewport.right, viewport.top, viewport.bottom = 0, 64, 0, 64
    chunks = list(map_manager.get_visible_chunks(viewport))
    assert len(chunks) == 1
    px, py, tile_id, depth = chunks[0]
    assert tile_id == 1
    assert depth == 1


def test_get_visible_chunks_outside_viewport(map_manager):
    """Viewport far from tiles yields no chunks."""
    viewport = MagicMock()
    viewport.left, viewport.right, viewport.top, viewport.bottom = 1000, 1064, 1000, 1064
    assert list(map_manager.get_visible_chunks(viewport)) == []


def test_get_visible_chunks_partial_viewport(map_manager):
    """Partial viewport covering only empty tiles yields no chunks."""
    viewport = MagicMock()
    viewport.left, viewport.right, viewport.top, viewport.bottom = 32, 64, 0, 32
    assert list(map_manager.get_visible_chunks(viewport)) == []


# ---------------------------------------------------------------------------
# TiledProject schema resolution
# ---------------------------------------------------------------------------


def test_tiled_project_resolution():
    from src.map.project_schema import TiledProject

    project_data = {
        "propertyTypes": [
            {
                "type": "class",
                "name": "base_entity",
                "members": [
                    {"name": "speed", "type": "int", "value": 100},
                    {"name": "name", "type": "string", "value": "Unknown"},
                ],
            }
        ]
    }
    with (
        patch("os.path.exists", return_value=True),
        patch("builtins.open", MagicMock()),
        patch("json.load", return_value=project_data),
    ):
        project = TiledProject("dummy.tiled-project")

        res = project.resolve("base_entity")
        assert res["speed"] == 100
        assert res["name"] == "Unknown"

        res = project.resolve("base_entity", {"speed": 200, "ad_hoc": "test"})
        assert res["speed"] == 200
        assert res["name"] == "Unknown"
        assert res["ad_hoc"] == "test"


# ---------------------------------------------------------------------------
# MapManager: get_terrain_material_at
# ---------------------------------------------------------------------------


def test_get_terrain_material_at(map_manager):
    """get_terrain_material_at returns the material property of the topmost tile."""
    # map_data fixture has tile 1 at layer 1, which has collidable=True and depth=1
    # We will patch its properties to have material
    tile = map_manager.tiles[1]
    tile.properties = {"material": "wood"}

    # Grid coordinates are x=0, y=0. Screen coordinates for this are 0..31
    material = map_manager.get_terrain_material_at(15, 15)
    assert material == "wood"

    # Outside map returns None
    assert map_manager.get_terrain_material_at(-10, -10) is None

    # Empty tile returns None
    assert map_manager.get_terrain_material_at(32, 0) is None  # x=1, y=0 is 0 in the mock map_data
