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
    tile.walkable = False
    tile.depth = 1
    tile.frames = None
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
    """Nested group layers are found and sorted by the 'order' property."""
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
                        "properties": [{"name": "order", "type": "int", "value": 2}],
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
                        "properties": [{"name": "order", "type": "int", "value": 1}],
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
                        # No 'order' property — defaults to 0
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
        "layer_order_values": {},
        "tiles": {},
        "width": 2,
        "height": 2,
        "tile_size": 32,
    }
    parser._process_layers(mock_data["layers"], 2, result)

    assert 1 in result["layer_names"]
    assert 2 in result["layer_names"]
    assert 3 in result["layer_names"]
    assert result["layer_order_values"] == {1: 0, 2: 1, 3: 2}

    manager = MapManager(result, OrthogonalLayout(32))
    # Sorted by order property: id=1 (order=0), id=2 (order=1), id=3 (order=2)
    assert manager.layer_order == [1, 2, 3]


# ---------------------------------------------------------------------------
# Collision detection
# ---------------------------------------------------------------------------


def test_map_manager_walkable_basics():
    """Collision detection works across layers using tile coordinates."""
    map_d = {
        "layers": {1: [[1, 0], [0, 0]]},
        "tiles": {1: MagicMock(walkable=False)},
        "width": 2,
        "height": 2,
        "tile_size": 32,
    }
    manager = MapManager(map_d, OrthogonalLayout(32))
    assert manager.is_walkable(0, 0) is False
    assert manager.is_walkable(1, 0) is False


def test_map_manager_walkable_out_of_bounds(map_data):
    layout = MagicMock()
    mm = MapManager(map_data, layout)
    assert mm.is_walkable(0, 0) is False
    assert mm.is_walkable(1, 0) is False
    assert mm.is_walkable(-1, 0) is False  # Out of bounds → not walkable


# ---------------------------------------------------------------------------
# Directional constraints
# ---------------------------------------------------------------------------

def test_map_manager_get_direction_flags():
    """get_direction_flags returns top layer's set or {'any'} if out of bounds."""
    tile = MagicMock()
    tile.image = pygame.Surface((32, 32))
    tile.walkable = True
    tile.depth = 0
    tile.direction_flags = {"up", "left"}

    map_d = {
        "layers": {1: [[1, 0]]},
        "tiles": {1: tile},
        "layer_names": {1: "00-layer"},
        "layer_order": [1],
        "width": 2,
        "height": 1,
        "tile_size": 32,
    }

    layout = MagicMock()
    manager = MapManager(map_d, layout)

    assert manager.get_direction_flags(0, 0) == {"up", "left"}
    assert manager.get_direction_flags(1, 0) == {"any"}  # Empty coordinate defaults to 'any'
    assert manager.get_direction_flags(-1, 0) == {"any"}  # Out of bounds


def _make_tile(direction_flags, walkable=True, depth=0):
    """Helper: create a MagicMock tile with the given direction_flags."""
    tile = MagicMock()
    tile.image = pygame.Surface((32, 32))
    tile.walkable = walkable
    tile.depth = depth
    tile.direction_flags = direction_flags
    return tile


def test_direction_flags_multilayer_any_does_not_override_constraint():
    """
    BUG REGRESSION: Layer 0=any, Layer 1={down,left,right}, Layer 2=any.
    La couche 'any' ne doit PAS effacer la contrainte {down,left,right} de la couche 1.
    Résultat attendu : {down, left, right} — la direction 'up' doit être bloquée.
    """
    tile_any = _make_tile({"any"})
    tile_restricted = _make_tile({"down", "left", "right"})

    map_d = {
        "layers": {
            1: [[1, 0]],  # Layer 0: any
            2: [[2, 0]],  # Layer 1: down, left, right
            3: [[3, 0]],  # Layer 2: any
        },
        "tiles": {
            1: tile_any,
            2: tile_restricted,
            3: tile_any,
        },
        "layer_names": {1: "00-layer", 2: "01-layer", 3: "02-layer"},
        "layer_order": [1, 2, 3],
        "layer_order_values": {1: 0, 2: 1, 3: 2},
        "width": 2,
        "height": 1,
        "tile_size": 32,
    }

    layout = MagicMock()
    manager = MapManager(map_d, layout)

    result = manager.get_direction_flags(0, 0)
    assert result == {"down", "left", "right"}, (
        f"Expected {{down, left, right}} but got {result}. "
        "A layer with 'any' must not override a constrained layer."
    )
    assert "up" not in result, "'up' must be blocked when a layer restricts to {down, left, right}"


def test_direction_flags_multilayer_intersection():
    """
    Deux couches avec des contraintes différentes : l'intersection doit être retournée.
    Layer 0: {down, left, right, up}, Layer 1: {down, left}.
    Résultat attendu : {down, left} (intersection).
    """
    tile_a = _make_tile({"down", "left", "right", "up"})
    tile_b = _make_tile({"down", "left"})

    map_d = {
        "layers": {
            1: [[1, 0]],  # Layer 0: {down,left,right,up}
            2: [[2, 0]],  # Layer 1: {down,left}
        },
        "tiles": {1: tile_a, 2: tile_b},
        "layer_names": {1: "00-layer", 2: "01-layer"},
        "layer_order": [1, 2],
        "layer_order_values": {1: 0, 2: 1},
        "width": 2,
        "height": 1,
        "tile_size": 32,
    }

    layout = MagicMock()
    manager = MapManager(map_d, layout)

    result = manager.get_direction_flags(0, 0)
    assert result == {"down", "left"}, (
        f"Expected {{down, left}} but got {result}. Intersection of two constrained layers must be applied."
    )


def test_direction_flags_all_any_returns_any():
    """
    Toutes les couches avec 'any' → résultat doit être {'any'}.
    """
    tile_any = _make_tile({"any"})

    map_d = {
        "layers": {
            1: [[1, 0]],
            2: [[2, 0]],
        },
        "tiles": {1: tile_any, 2: tile_any},
        "layer_names": {1: "00-layer", 2: "01-layer"},
        "layer_order": [1, 2],
        "layer_order_values": {1: 0, 2: 1},
        "width": 2,
        "height": 1,
        "tile_size": 32,
    }

    layout = MagicMock()
    manager = MapManager(map_d, layout)

    result = manager.get_direction_flags(0, 0)
    assert result == {"any"}, f"Expected {{any}} but got {result}"


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
# MapManager: get_visible_animated_chunks
# ---------------------------------------------------------------------------


def test_get_visible_animated_chunks_static_map(map_manager):
    """TC-004: get_visible_animated_chunks called on static map yields empty sequence."""
    viewport = MagicMock()
    viewport.left, viewport.right, viewport.top, viewport.bottom = 0, 64, 0, 64
    chunks = list(map_manager.get_visible_animated_chunks(viewport))
    assert len(chunks) == 0

def test_get_visible_animated_chunks_with_animated_tile(map_data):
    """Animated chunks should yield animated tiles, while static chunks should ignore them."""
    layout = MagicMock()
    layout.tile_size = 32
    layout.to_screen.side_effect = lambda x, y: (x * 32, y * 32)

    # Setup tile 1 to be static, tile 2 to be animated
    static_tile = MagicMock()
    static_tile.image = pygame.Surface((32, 32))
    static_tile.frames = None
    static_tile.depth = 0

    anim_tile = MagicMock()
    anim_tile.image = pygame.Surface((32, 32))
    anim_tile.frames = [(2, 150), (3, 150)]
    anim_tile.depth = 0

    map_data["layers"][1] = [[1, 2], [0, 0]]
    map_data["tiles"] = {1: static_tile, 2: anim_tile}
    map_data["width"] = 2
    map_data["height"] = 2

    manager = MapManager(map_data, layout)
    viewport = MagicMock()
    viewport.left, viewport.right, viewport.top, viewport.bottom = 0, 64, 0, 64

    # Static chunks should yield tile 1
    static_chunks = list(manager.get_visible_chunks(viewport))
    assert len(static_chunks) == 1
    assert static_chunks[0][2] == 1  # tile_id is 1

    # Animated chunks should yield tile 2
    anim_chunks = list(manager.get_visible_animated_chunks(viewport))
    assert len(anim_chunks) == 1
    assert anim_chunks[0][2] == 2  # tile_id is 2

def test_get_layer_surface_ignores_animated_tiles(map_data):
    """Static cache rendering should skip animated tiles leaving a transparent hole."""
    layout = MagicMock()
    layout.tile_size = 32
    layout.to_screen.side_effect = lambda x, y: (x * 32, y * 32)

    # Setup tile 1 to be animated
    anim_tile = MagicMock()
    anim_tile.image = pygame.Surface((32, 32))
    anim_tile.image.fill((255, 0, 0)) # Red
    anim_tile.frames = [(1, 150), (2, 150)]
    anim_tile.depth = 0

    map_data["layers"][1] = [[1, 0], [0, 0]]
    map_data["tiles"] = {1: anim_tile}
    map_data["width"] = 2
    map_data["height"] = 2

    manager = MapManager(map_data, layout)
    mock_pygame = MagicMock()
    mock_pygame.SRCALPHA = pygame.SRCALPHA
    mock_surface = MagicMock()
    mock_pygame.Surface.return_value = mock_surface

    surface = manager.get_layer_surface(1, mock_pygame)

    # mock_surface should NOT have been blitted on because the only tile is animated
    mock_surface.blit.assert_not_called()


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



def test_tile_depth_overrides_layer_depth():
    from src.map.layout import OrthogonalLayout
    from src.map.manager import MapManager

    class MockTile:
        def __init__(self, depth, frames=None):
            self.depth = depth
            self.frames = frames
            self.image = pygame.Surface((32, 32))

    map_data = {
        "layer_order": [1],
        "layer_names": {1: "00-ground"},
        "layers": {
            1: [[0, 1, 2]]
        },
        "tiles": {
            1: MockTile(depth=0),
            2: MockTile(depth=2),
        }
    }

    layout = OrthogonalLayout(32)
    manager = MapManager(map_data, layout)

    chunks = list(manager.get_visible_chunks(pygame.Rect(0, 0, 100, 100), min_depth=1))
    assert len(chunks) == 1
    assert chunks[0][2] == 2
    assert chunks[0][3] == 2

    mock_pygame = MagicMock()
    mock_surface = MagicMock()
    mock_pygame.Surface.return_value = mock_surface
    mock_pygame.SRCALPHA = 1

    manager.get_layer_surface(1, mock_pygame, max_bg_depth=1)
    assert mock_surface.blit.call_count == 1
    mock_surface.blit.assert_called_with(map_data["tiles"][1].image, (32, 0))


# ---------------------------------------------------------------------------
# Regression: depth=2 object on depth=2 tile (object must be visible above tile)
# ---------------------------------------------------------------------------


class _MockTile:
    """Minimal tile stub for rendering tests."""

    def __init__(self, depth, frames=None):
        self.depth = depth
        self.frames = frames
        self.image = pygame.Surface((32, 32))
        self.occluded_image = None


def test_foreground_layer_yields_all_tiles_regardless_of_tile_depth():
    """
    Regression: tiles in a foreground-order layer (order=2) must be included in
    get_visible_chunks(min_depth=1) even if their individual depth property is 0.
    Previously, the per-tile depth filter would silently drop these tiles.
    """
    layout = OrthogonalLayout(32)
    map_data = {
        "layer_order": [1, 2],
        "layer_names": {1: "00-layer", 2: "02-layer"},
        # Layer 1: order=0 (background), Layer 2: order=2 (foreground)
        "layer_order_values": {1: 0, 2: 2},
        "layers": {
            1: [[1, 0]],   # background tile (depth=0)
            2: [[2, 0]],   # foreground-order tile but depth=0
        },
        "tiles": {
            1: _MockTile(depth=0),
            2: _MockTile(depth=0),  # depth=0 but in order=2 layer
        },
    }
    manager = MapManager(map_data, layout)
    viewport = pygame.Rect(0, 0, 100, 100)

    # With player.depth=1, draw_foreground calls get_visible_chunks(min_depth=1)
    chunks = list(manager.get_visible_chunks(viewport, min_depth=1))

    # Tile 2 (in order=2 foreground layer) must be yielded even though depth=0
    tile_ids = [c[2] for c in chunks]
    assert 2 in tile_ids, "Foreground-order layer tile with depth=0 must be visible in foreground pass"
    # Tile 1 (in order=0 background layer, depth=0) must NOT be yielded
    assert 1 not in tile_ids, "Background-order layer tile with depth=0 must not appear in foreground pass"


def test_order_property_used_for_layer_sorting():
    """
    Regression: layers are sorted by `order` property, NOT by layer name alphabetically.
    A layer with order=2 inserted before order=0 must appear last after sorting.
    """
    layout = OrthogonalLayout(32)
    # Parsing order: layer id=3 (order=2), id=2 (order=1), id=1 (order=0)
    map_data = {
        "layer_order": [3, 2, 1],
        "layer_names": {1: "ground", 2: "mid", 3: "top"},
        "layer_order_values": {1: 0, 2: 1, 3: 2},
        "layers": {1: [[0]], 2: [[0]], 3: [[0]]},
        "tiles": {},
    }
    manager = MapManager(map_data, layout)
    # After sorting by order value: id=1 (0), id=2 (1), id=3 (2)
    assert manager.layer_order == [1, 2, 3]
    assert manager.layer_depths == {1: 0, 2: 1, 3: 2}
