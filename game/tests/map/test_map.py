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


def test_is_walkable_bridge_over_ravine():
    """
    BUG REGRESSION BUG-WALK-001:
    Layer 0: ravine  (walkable=False, depth=0)  ← sol non-franchissable
    Layer 1: bridge  (walkable=True, depth=0)   ← sol franchissable, plus haut
    Expected: True — le pont (sol depth=0) couvre le ravin ; le joueur marche dessus.

    Seuls les tiles depth=0 (sol) participent à la walkabilité.
    Le sol le plus haut (layer_order le plus élevé) détermine la walkabilité.
    """
    ravine = MagicMock()
    ravine.walkable = False
    ravine.depth = 0
    bridge = MagicMock()
    bridge.walkable = True
    bridge.depth = 0

    map_d = {
        "layers": {
            1: [[1, 0]],  # Layer 0: ravine (non-walkable, depth=0)
            2: [[2, 0]],  # Layer 1: bridge (walkable, depth=0)
        },
        "tiles": {1: ravine, 2: bridge},
        "layer_names": {1: "00-ground", 2: "01-bridge"},
        "layer_order": [1, 2],
        "layer_order_values": {1: 0, 2: 1},
        "width": 2,
        "height": 1,
        "tile_size": 32,
    }

    layout = MagicMock()
    manager = MapManager(map_d, layout)

    result = manager.is_walkable(0, 0)
    assert result is True, (
        f"Expected True (bridge depth=0 covers ravine) but got {result}. "
        "The topmost depth=0 tile must determine walkability."
    )


def test_is_walkable_ravine_without_bridge():
    """
    Sans pont par dessus, le ravin (walkable=False) bloque le joueur.
    Layer 0: ravine (walkable=False) — seul layer
    Expected: False.
    """
    ravine = MagicMock()
    ravine.walkable = False

    map_d = {
        "layers": {1: [[1, 0]]},
        "tiles": {1: ravine},
        "layer_names": {1: "00-ground"},
        "layer_order": [1],
        "layer_order_values": {1: 0},
        "width": 2,
        "height": 1,
        "tile_size": 32,
    }

    layout = MagicMock()
    manager = MapManager(map_d, layout)

    assert manager.is_walkable(0, 0) is False, "A lone non-walkable tile must block movement."


def test_is_walkable_depth0_ground_blocks_when_not_walkable():
    """
    Un tile de SOL (depth=0) non-walkable bloque le joueur même si c'est la couche la plus haute.
    Layer 0: walkable=False, depth=0 (ravin seul, pas de pont)
    Expected: False.
    """
    ground = MagicMock()
    ground.walkable = False
    ground.depth = 0

    map_d = {
        "layers": {1: [[1, 0]]},
        "tiles": {1: ground},
        "layer_names": {1: "00-ground"},
        "layer_order": [1],
        "layer_order_values": {1: 0},
        "width": 2,
        "height": 1,
        "tile_size": 32,
    }

    layout = MagicMock()
    manager = MapManager(map_d, layout)

    assert manager.is_walkable(0, 0) is False, "Un sol non-walkable depth=0 doit bloquer."


def test_is_walkable_decor_depth2_does_not_block_walkable_ground():
    """
    BUG-WALK-002 (cas réel debug room) :
    Le pont est constitué de :
    - Layer 0 (order=0): sol stone  walkable=True,  depth=0   ← sol franchissable
    - Layer 1 (order=1): rebords   walkable=False, depth=2   ← décor visuel (depth≥1)

    Le décor (depth≥1) NE doit PAS participer à la walkabilité.
    Seuls les tiles depth=0 (sol) déterminent si on peut marcher.
    Expected: True — le sol depth=0 est walkable, le décor depth=2 est ignoré.
    """
    ground = MagicMock()
    ground.walkable = True
    ground.depth = 0
    bridge_edge = MagicMock()  # rebord visuel du pont
    bridge_edge.walkable = False
    bridge_edge.depth = 2

    map_d = {
        "layers": {
            1: [[1, 0]],  # Layer 0: sol walkable depth=0
            2: [[2, 0]],  # Layer 1: rebord du pont walkable=False depth=2
        },
        "tiles": {1: ground, 2: bridge_edge},
        "layer_names": {1: "00-ground", 2: "01-bridge-edge"},
        "layer_order": [1, 2],
        "layer_order_values": {1: 0, 2: 1},
        "width": 2,
        "height": 1,
        "tile_size": 32,
    }

    layout = MagicMock()
    manager = MapManager(map_d, layout)

    result = manager.is_walkable(0, 0)
    assert result is True, (
        f"Expected True (decor depth=2 must not block walkable ground depth=0) but got {result}. "
        "Only depth=0 tiles participate in walkability."
    )


def test_is_walkable_non_walkable_depth0_on_top_blocks():
    """
    Un tile de SOL (depth=0) non-walkable sur le layer le plus haut bloque,
    même si le layer dessous est walkable.
    Layer 0: walkable=True, depth=0
    Layer 1: walkable=False, depth=0  ← sol non-franchissable le plus haut
    Expected: False.
    """
    ground = MagicMock()
    ground.walkable = True
    ground.depth = 0
    wall_ground = MagicMock()
    wall_ground.walkable = False
    wall_ground.depth = 0

    map_d = {
        "layers": {
            1: [[1, 0]],  # Layer 0: sol walkable depth=0
            2: [[2, 0]],  # Layer 1: sol non-walkable depth=0
        },
        "tiles": {1: ground, 2: wall_ground},
        "layer_names": {1: "00-ground", 2: "01-objects"},
        "layer_order": [1, 2],
        "layer_order_values": {1: 0, 2: 1},
        "width": 2,
        "height": 1,
        "tile_size": 32,
    }

    layout = MagicMock()
    manager = MapManager(map_d, layout)

    assert manager.is_walkable(0, 0) is False, (
        "Un sol depth=0 non-walkable sur le layer le plus haut doit bloquer le mouvement."
    )


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
# Architecture: is_walkable (depth=0) + get_direction_flags (all depths)
# ---------------------------------------------------------------------------


def test_depth1_tile_contributes_direction_but_not_walkability():
    """
    Architecture du système de mouvement — les deux fonctions se complètent :

      is_walkable      → seuls les tiles depth=0 (sol) participent
      get_direction_flags → TOUS les tiles (depth=0 ET depth≥1) participent

    Scénario utilisateur :
      Layer 0 (order=0): sol          depth=0, walkable=True,  direction=any
      Layer 1 (order=1): garde-corps  depth=2, walkable=True,  direction={up,left,right}

    Attendu :
      - is_walkable       = True  (sol depth=0 est walkable)
      - get_direction_flags = {up, left, right}  (garde-corps depth=2 contraint les sorties)
      - 'down' est bloqué (le garde-corps empêche de tomber)
    """
    ground = MagicMock()
    ground.walkable = True
    ground.depth = 0
    ground.direction_flags = {"any"}

    guardrail = MagicMock()
    guardrail.walkable = True
    guardrail.depth = 2
    guardrail.direction_flags = {"up", "left", "right"}

    map_d = {
        "layers": {
            1: [[1, 0]],  # Layer 0 (order=0): sol
            2: [[2, 0]],  # Layer 1 (order=1): garde-corps
        },
        "tiles": {1: ground, 2: guardrail},
        "layer_names": {1: "00-ground", 2: "01-guardrail"},
        "layer_order": [1, 2],
        "layer_order_values": {1: 0, 2: 1},
        "width": 2,
        "height": 1,
        "tile_size": 32,
    }

    layout = MagicMock()
    manager = MapManager(map_d, layout)

    # La case est franchissable (sol depth=0 walkable=True)
    assert manager.is_walkable(0, 0) is True, (
        "Le sol depth=0 walkable=True doit rendre la case franchissable, "
        "même si un décor depth=2 est au-dessus."
    )

    # Les directions sont contraintes par le garde-corps depth=2
    direction_result = manager.get_direction_flags(0, 0)
    assert direction_result == {"up", "left", "right"}, (
        f"Expected {{up, left, right}} but got {direction_result}. "
        "get_direction_flags doit inclure les tiles depth≥1."
    )
    assert "down" not in direction_result, "'down' doit être bloqué par le garde-corps depth=2."


def test_decor_depth2_walkable_false_no_direction_does_not_constrain():
    """
    Un décor depth=2 avec walkable=False et direction=any (cas des rebords du pont) :
    - N'affecte PAS is_walkable (ignoré)
    - N'affecte PAS get_direction_flags (direction=any = joker neutre)

    Scénario : rebord du pont sur une case franchissable.
    """
    ground = MagicMock()
    ground.walkable = True
    ground.depth = 0
    ground.direction_flags = {"any"}

    bridge_edge = MagicMock()  # rebord de pont
    bridge_edge.walkable = False
    bridge_edge.depth = 2
    bridge_edge.direction_flags = {"any"}

    map_d = {
        "layers": {
            1: [[1, 0]],
            2: [[2, 0]],
        },
        "tiles": {1: ground, 2: bridge_edge},
        "layer_names": {1: "00-ground", 2: "01-edge"},
        "layer_order": [1, 2],
        "layer_order_values": {1: 0, 2: 1},
        "width": 2,
        "height": 1,
        "tile_size": 32,
    }

    layout = MagicMock()
    manager = MapManager(map_d, layout)

    assert manager.is_walkable(0, 0) is True, (
        "Le rebord (depth=2, walkable=False, direction=any) ne doit pas bloquer le sol."
    )
    assert manager.get_direction_flags(0, 0) == {"any"}, (
        "Le rebord avec direction=any ne doit pas contraindre les directions."
    )


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


@pytest.mark.tc("IT-006")
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
    anim_tile.image.fill((255, 0, 0))  # Red
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


def _make_material_tile(depth, material=None):
    """Helper: create a MagicMock tile with given depth and optional material."""
    tile = MagicMock()
    tile.depth = depth
    tile.properties = {"material": material} if material else {}
    tile.frames = None
    tile.walkable = True
    return tile


def test_get_terrain_material_at_skips_depth_above_1():
    """
    BUG-SFX-001: get_terrain_material_at must skip tiles with depth>1.

    Scenario: grass (depth=0, material=grass) + plank (depth=1, material=wood)
              + roof (depth=2, walkable=True, material=roof).

    Expected: 'wood' — the roof (depth=2) must be ignored; the plank (depth=1)
    is the highest tile with depth<=1 and carries the material underfoot.
    """
    layout = OrthogonalLayout(32)
    grass = _make_material_tile(depth=0, material="grass")
    plank = _make_material_tile(depth=1, material="wood")
    roof = _make_material_tile(depth=2, material="roof")

    map_data = {
        "layers": {
            1: [[1, 0]],  # grass  (order=0, depth=0)
            2: [[2, 0]],  # plank  (order=1, depth=1)
            3: [[3, 0]],  # roof   (order=2, depth=2)
        },
        "tiles": {1: grass, 2: plank, 3: roof},
        "layer_names": {1: "00-ground", 2: "01-plank", 3: "02-roof"},
        "layer_order": [1, 2, 3],
        "layer_order_values": {1: 0, 2: 1, 3: 2},
        "width": 2,
        "height": 1,
        "tile_size": 32,
    }

    manager = MapManager(map_data, layout)
    result = manager.get_terrain_material_at(15, 0)
    assert result == "wood", (
        f"Expected 'wood' (plank depth=1) but got '{result}'. "
        "Tiles with depth>1 must not contribute to terrain material (BUG-SFX-001)."
    )


def test_get_terrain_material_at_grass_only_no_overlay():
    """
    BUG-SFX-001 baseline: single grass tile (depth=0) returns 'grass'.
    """
    layout = OrthogonalLayout(32)
    grass = _make_material_tile(depth=0, material="grass")

    map_data = {
        "layers": {1: [[1, 0]]},
        "tiles": {1: grass},
        "layer_names": {1: "00-ground"},
        "layer_order": [1],
        "layer_order_values": {1: 0},
        "width": 2,
        "height": 1,
        "tile_size": 32,
    }

    manager = MapManager(map_data, layout)
    result = manager.get_terrain_material_at(15, 0)
    assert result == "grass", (
        f"Expected 'grass' but got '{result}'. Single ground tile must return its material."
    )


def test_get_terrain_material_at_plank_over_grass_no_roof():
    """
    BUG-SFX-001 intermediate: grass (depth=0) under plank (depth=1), no roof.
    Expected: 'wood' (plank is highest depth<=1 tile with a material).
    """
    layout = OrthogonalLayout(32)
    grass = _make_material_tile(depth=0, material="grass")
    plank = _make_material_tile(depth=1, material="wood")

    map_data = {
        "layers": {
            1: [[1, 0]],  # grass (order=0, depth=0)
            2: [[2, 0]],  # plank (order=1, depth=1)
        },
        "tiles": {1: grass, 2: plank},
        "layer_names": {1: "00-ground", 2: "01-plank"},
        "layer_order": [1, 2],
        "layer_order_values": {1: 0, 2: 1},
        "width": 2,
        "height": 1,
        "tile_size": 32,
    }

    manager = MapManager(map_data, layout)
    result = manager.get_terrain_material_at(15, 0)
    assert result == "wood", f"Expected 'wood' (plank depth=1 over grass) but got '{result}'."


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
        "layers": {1: [[0, 1, 2]]},
        "tiles": {
            1: MockTile(depth=0),
            2: MockTile(depth=2),
        },
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
            1: [[1, 0]],  # background tile (depth=0)
            2: [[2, 0]],  # foreground-order tile but depth=0
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
    assert 2 in tile_ids, (
        "Foreground-order layer tile with depth=0 must be visible in foreground pass"
    )
    # Tile 1 (in order=0 background layer, depth=0) must NOT be yielded
    assert 1 not in tile_ids, (
        "Background-order layer tile with depth=0 must not appear in foreground pass"
    )


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


# ===========================================================================
# P-001 — MapManager._build_fg_occlusion_world  (TC-001..TC-006)
# Spec: game/docs/specs/p001-foreground-rendering.md § 8.1
# These tests are RED until _build_fg_occlusion_world is implemented.
# ===========================================================================


def _make_fg_tile(depth: int = 2, has_occ: bool = True, animated: bool = False):
    """Helper: create a foreground tile mock for P-001 tests."""
    tile = MagicMock()
    tile.image = pygame.Surface((32, 32))
    tile.occluded_image = pygame.Surface((32, 32)) if has_occ else None
    tile.depth = depth
    tile.frames = [(1, 100), (2, 100)] if animated else None
    tile.walkable = False
    return tile


def _make_map_data_with_fg(
    tile_depth: int = 2,
    has_occ: bool = True,
    animated: bool = False,
    layer_max_depth: int = 2,
):
    """Helper: map_data with one foreground tile at (0,0) in layer 1."""
    tile = _make_fg_tile(depth=tile_depth, has_occ=has_occ, animated=animated)
    return {
        "layers": {1: [[1, 0], [0, 0]]},
        "tiles": {1: tile},
        "layer_names": {1: "01-layer"},
        "layer_order": [1],
        "layer_order_values": {1: layer_max_depth},
    }


@pytest.mark.tc("TC-001")
def test_fg_occlusion_world_populated_on_init():
    """TC-001: MapManager with fg tile (depth>0) populates _fg_occlusion_world on __init__."""
    layout = MagicMock()
    layout.tile_size = 32
    mm = MapManager(_make_map_data_with_fg(tile_depth=2), layout)

    assert hasattr(mm, "_fg_occlusion_world"), (
        "MapManager must expose _fg_occlusion_world after __init__"
    )
    assert len(mm._fg_occlusion_world) > 0, (
        "Expected at least 1 fg tile in _fg_occlusion_world for a map with depth=2 tile"
    )


@pytest.mark.tc("TC-002")
def test_fg_occlusion_world_excludes_background_depth():
    """TC-002: Tiles with depth=0 must NOT appear in _fg_occlusion_world."""
    tile = MagicMock()
    tile.image = pygame.Surface((32, 32))
    tile.occluded_image = None
    tile.depth = 0
    tile.frames = None

    map_data = {
        "layers": {1: [[1, 0], [0, 0]]},
        "tiles": {1: tile},
        "layer_names": {1: "00-layer"},
        "layer_order": [1],
        "layer_order_values": {1: 0},
    }
    layout = MagicMock()
    layout.tile_size = 32
    mm = MapManager(map_data, layout)

    assert hasattr(mm, "_fg_occlusion_world")
    for _wx, _wy, depth, _img, _occ in mm._fg_occlusion_world:
        assert depth > 0, (
            f"Found tile with depth={depth} <= 0 in _fg_occlusion_world (must exclude bg tiles)"
        )


@pytest.mark.tc("TC-003")
def test_fg_occlusion_world_excludes_animated_tiles():
    """TC-003: Animated tiles (frames is not None/empty) must NOT appear in _fg_occlusion_world."""
    layout = MagicMock()
    layout.tile_size = 32
    mm = MapManager(_make_map_data_with_fg(tile_depth=2, animated=True), layout)

    assert hasattr(mm, "_fg_occlusion_world")
    # The map only has 1 tile, and it's animated — cache must be empty
    assert mm._fg_occlusion_world == [], "Animated tile must be excluded from _fg_occlusion_world"


@pytest.mark.tc("TC-004")
def test_fg_occlusion_world_world_coords():
    """TC-004: Coordinates in _fg_occlusion_world are in pixel world-space (multiples of tile_size)."""
    layout = MagicMock()
    layout.tile_size = 32
    mm = MapManager(_make_map_data_with_fg(tile_depth=2), layout)

    assert hasattr(mm, "_fg_occlusion_world")
    assert len(mm._fg_occlusion_world) > 0

    for wx, wy, _depth, _img, _occ in mm._fg_occlusion_world:
        assert wx % 32 == 0, f"world_x={wx} is not a multiple of tile_size=32"
        assert wy % 32 == 0, f"world_y={wy} is not a multiple of tile_size=32"
        assert isinstance(wx, int), f"world_x must be int, got {type(wx)}"
        assert isinstance(wy, int), f"world_y must be int, got {type(wy)}"


@pytest.mark.tc("TC-005")
def test_fg_occlusion_world_occluded_image_none_allowed():
    """TC-005: Tile with occluded_image=None must be included with None as 5th element."""
    layout = MagicMock()
    layout.tile_size = 32
    mm = MapManager(_make_map_data_with_fg(tile_depth=2, has_occ=False), layout)

    assert hasattr(mm, "_fg_occlusion_world")
    assert len(mm._fg_occlusion_world) > 0

    _wx, _wy, _depth, _img, occ_img = mm._fg_occlusion_world[0]
    assert occ_img is None, (
        "Tile with occluded_image=None must be included with occ_img=None (not excluded)"
    )


@pytest.mark.tc("TC-006")
def test_fg_occlusion_world_empty_for_bg_only_map():
    """TC-006: Map with only depth=0 tiles -> _fg_occlusion_world is empty list."""
    tile = MagicMock()
    tile.image = pygame.Surface((32, 32))
    tile.occluded_image = None
    tile.depth = 0
    tile.frames = None

    map_data = {
        "layers": {1: [[1, 1], [1, 1]]},
        "tiles": {1: tile},
        "layer_names": {1: "00-ground"},
        "layer_order": [1],
        "layer_order_values": {1: 0},
    }
    layout = MagicMock()
    layout.tile_size = 32
    mm = MapManager(map_data, layout)

    assert hasattr(mm, "_fg_occlusion_world")
    assert mm._fg_occlusion_world == [], (
        "Map with only depth=0 tiles must yield empty _fg_occlusion_world"
    )
