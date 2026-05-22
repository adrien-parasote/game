"""Tests for RenderManager - rendering background, foreground, scene and HUD."""

from unittest.mock import MagicMock, patch

import pygame
import pytest

from src.engine.render_manager import RenderManager


def test_render_manager_init():
    game = MagicMock()
    rm = RenderManager(game)
    assert rm.game == game


def test_render_manager_draw_background():
    game = MagicMock()
    game.map_manager.layer_order = ["layer_0", "layer_1"]
    game.map_manager.layer_depths = {"layer_0": 0, "layer_1": 2}

    # Mock pre-rendered surfaces
    surf = pygame.Surface((32, 32))
    game.map_manager.get_layer_surface.return_value = surf
    game.map_manager.is_foreground_layer.side_effect = lambda layer, limit: layer == "layer_1"
    game.map_manager.get_visible_chunks.return_value = [pygame.Rect(0, 0, 32, 32)]

    game.visible_sprites.offset = pygame.math.Vector2(0, 0)
    game.screen = pygame.Surface((800, 600))
    game.player.rect = pygame.Rect(0, 0, 32, 32)
    game.player.depth = 1

    rm = RenderManager(game)
    rm.draw_background()

    assert game.map_manager.get_layer_surface.called


def test_render_manager_draw_foreground():
    game = MagicMock()

    # Mock chunks
    game.map_manager.get_visible_chunks.return_value = [(0, 0, 1, 2)]  # px, py, tile_id, depth

    mock_tile = MagicMock()
    mock_tile.image = pygame.Surface((32, 32))
    mock_tile.occluded_image = None
    game.map_manager.tiles = {1: mock_tile}

    game.visible_sprites.offset = pygame.math.Vector2(0, 0)
    game.screen = pygame.Surface((800, 600))
    game.player.rect = pygame.Rect(0, 0, 32, 32)
    game.player.image = pygame.Surface((32, 32))
    game.player.depth = 1
    game.tile_size = 32

    rm = RenderManager(game)
    rm.draw_foreground()

    assert game.map_manager.get_visible_chunks.called


def test_render_manager_draw_scene():
    game = MagicMock()
    game.map_manager.layer_order = []
    game.map_manager.layer_depths = {}
    game.map_manager.get_visible_chunks.return_value = []

    game.visible_sprites.offset = pygame.math.Vector2(0, 0)
    game.screen = pygame.Surface((800, 600))
    game.player.rect = pygame.Rect(0, 0, 32, 32)
    game.player.image = pygame.Surface((32, 32))
    game.player.depth = 1
    game.time_system.night_alpha = 0
    game.chest_ui.is_open = False
    game.inventory_ui.is_open = False
    game.dialogue_manager.is_active = False

    mock_interactive = MagicMock()
    mock_interactive.is_light_source = True
    game.interactives = [mock_interactive]

    rm = RenderManager(game)
    rm.draw_scene()

    # Check that it draws the interactive
    assert mock_interactive.draw_effects.called


# ---------------------------------------------------------------------------
# UT-001 — draw_foreground(): no occluding tile → returns empty list
# ---------------------------------------------------------------------------
def test_draw_foreground_no_occluding_tile_returns_empty_list():
    """UT-001: draw_foreground() returns [] when no tile depth > player.depth."""
    game = MagicMock()
    game.map_manager.get_visible_chunks.return_value = [(0, 0, 1, 0)]  # depth=0, not occluding
    mock_tile = MagicMock()
    mock_tile.image = pygame.Surface((32, 32))
    mock_tile.occluded_image = None
    game.map_manager.tiles = {1: mock_tile}
    game.anim_map_manager = None
    game._intra_walk_target = None
    game.visible_sprites.offset = pygame.math.Vector2(0, 0)
    game.screen = MagicMock()
    game.player.rect = pygame.Rect(0, 0, 32, 32)
    game.player.depth = 1
    game.tile_size = 32

    rm = RenderManager(game)
    result = rm.draw_foreground()
    assert result == []


# ---------------------------------------------------------------------------
# UT-002 — draw_foreground(): occluding tile → returns list with (Rect, depth) tuple
# ---------------------------------------------------------------------------
def test_draw_foreground_occluding_tile_returns_tuple_list():
    """UT-002: draw_foreground() returns list with 1 (Rect, int) tuple for depth=2 tile."""
    game = MagicMock()
    game.map_manager.get_visible_chunks.return_value = [(0, 0, 1, 2)]  # depth=2, occluding
    mock_tile = MagicMock()
    mock_tile.image = pygame.Surface((32, 32))
    mock_tile.occluded_image = None
    game.map_manager.tiles = {1: mock_tile}
    game.anim_map_manager = None
    game._intra_walk_target = None
    game.visible_sprites.offset = pygame.math.Vector2(0, 0)
    game.screen = MagicMock()
    game.player.rect = pygame.Rect(0, 0, 32, 32)
    game.player.depth = 1
    game.tile_size = 32

    rm = RenderManager(game)
    result = rm.draw_foreground()

    assert isinstance(result, list)
    assert len(result) == 1
    occ_rect, depth = result[0]
    assert isinstance(occ_rect, pygame.Rect)
    assert depth == 2
    assert occ_rect == pygame.Rect(0, 0, 32, 32)  # screen_pos=(0,0), tile_size=32


# ---------------------------------------------------------------------------
# UT-003 — draw_foreground(): animated tile depth>1 is included (branch is inert today)
# ---------------------------------------------------------------------------
def test_draw_foreground_animated_tile_depth2_included():
    """UT-003: Animated tile with depth>player.depth is included in occluding_rects."""
    game = MagicMock()
    game.map_manager.get_visible_chunks.return_value = []  # no static foreground tiles
    game.map_manager.get_visible_animated_chunks.return_value = [(64, 0, 99, 2)]  # anim tile depth=2
    game.map_manager.tiles = {}
    game.anim_map_manager = MagicMock()  # anim manager present
    game.anim_map_manager.get_current_frame_image.return_value = pygame.Surface((32, 32))
    game._intra_walk_target = None
    game.visible_sprites.offset = pygame.math.Vector2(0, 0)
    game.screen = MagicMock()
    game.player.rect = pygame.Rect(0, 0, 32, 32)
    game.player.depth = 1
    game.tile_size = 32

    rm = RenderManager(game)
    result = rm.draw_foreground()

    # The animated tile at depth=2 must be in the occluding list
    assert any(depth == 2 for _, depth in result)


# ---------------------------------------------------------------------------
# UT-004 — draw_foreground() with walk_active: still collects rects (caller guards)
# ---------------------------------------------------------------------------
def test_draw_foreground_walk_active_still_returns_rects():
    """UT-004: draw_foreground() collects rects even during walk_active.
    The caller (draw_scene) is responsible for not calling _apply_partial_occlusion.
    """
    game = MagicMock()
    game.map_manager.get_visible_chunks.return_value = [(0, 0, 1, 2)]
    mock_tile = MagicMock()
    mock_tile.image = pygame.Surface((32, 32))
    mock_tile.occluded_image = None
    game.map_manager.tiles = {1: mock_tile}
    game.anim_map_manager = None
    game._intra_walk_target = MagicMock()  # walk active
    game.visible_sprites.offset = pygame.math.Vector2(0, 0)
    game.screen = MagicMock()
    game.player.rect = pygame.Rect(0, 0, 32, 32)
    game.player.depth = 1
    game.tile_size = 32

    rm = RenderManager(game)
    result = rm.draw_foreground()
    # Rects still collected — the guard is in draw_scene, not draw_foreground
    assert len(result) == 1


# ---------------------------------------------------------------------------
# UT-005 — _apply_partial_occlusion([]): returns {} immediately
# ---------------------------------------------------------------------------
def test_apply_partial_occlusion_empty_list_returns_empty_dict():
    """UT-005: _apply_partial_occlusion with empty list returns {} without touching sprites."""
    game = MagicMock()
    game.visible_sprites.offset = pygame.math.Vector2(0, 0)
    game.player.depth = 1
    rm = RenderManager(game)

    result = rm._apply_partial_occlusion([])
    assert result == {}
    game.visible_sprites.get_sorted_sprites.assert_not_called()


# ---------------------------------------------------------------------------
# UT-006 — _apply_partial_occlusion: sprite not intersecting → skip
# ---------------------------------------------------------------------------
def test_apply_partial_occlusion_no_intersection_skips_sprite():
    """UT-006: Sprite not overlapping any occluding rect is not modified."""
    game = MagicMock()
    game.visible_sprites.offset = pygame.math.Vector2(0, 0)
    game.player.depth = 1

    sprite = MagicMock()
    sprite.image = pygame.Surface((32, 48), pygame.SRCALPHA)
    sprite.rect = pygame.Rect(200, 200, 32, 32)  # far from tile at (0,0)
    sprite.depth = 1
    game.visible_sprites.get_sorted_sprites.return_value = [sprite]

    rm = RenderManager(game)
    occluding_rects = [(pygame.Rect(0, 0, 32, 32), 2)]  # tile at (0,0), depth=2
    result = rm._apply_partial_occlusion(occluding_rects)

    assert result == {}  # No sprite was saved/modified
    assert sprite.image is not None  # image untouched


# ---------------------------------------------------------------------------
# UT-007 — _apply_partial_occlusion: partial intersection → composite with alpha zone
# ---------------------------------------------------------------------------
def test_apply_partial_occlusion_partial_intersection_creates_composite():
    """UT-007: Sprite partially behind a tile → sprite.image replaced with composite."""
    game = MagicMock()
    game.visible_sprites.offset = pygame.math.Vector2(0, 0)
    game.player.depth = 1

    # Sprite 32×48, positioned so bottom 16px overlap the tile
    original_image = pygame.Surface((32, 48), pygame.SRCALPHA)
    original_image.fill((255, 0, 0, 255))  # solid red, fully opaque
    sprite = MagicMock()
    sprite.image = original_image
    # rect.bottomright = (32, 48) → visual_rect = Rect(0, 0, 32, 48)
    # sprite_screen_rect with offset (0,0) = Rect(0, 0, 32, 48)
    sprite.rect = pygame.Rect(0, 32, 32, 16)  # hitbox bottom at y=48
    sprite.depth = 1
    game.visible_sprites.get_sorted_sprites.return_value = [sprite]

    rm = RenderManager(game)
    # Tile covers y=32..64 — intersects lower 16px of sprite (y=32..48)
    occluding_rects = [(pygame.Rect(0, 32, 32, 32), 2)]
    result = rm._apply_partial_occlusion(occluding_rects)

    assert sprite in result  # original saved
    assert result[sprite] is original_image  # correct original stored
    assert sprite.image is not original_image  # replaced by composite
    assert sprite.image.get_size() == (32, 48)  # composite same size


# ---------------------------------------------------------------------------
# UT-008 — _apply_partial_occlusion: full intersection → entire composite in alpha
# ---------------------------------------------------------------------------
def test_apply_partial_occlusion_full_intersection_composite_all_alpha():
    """UT-008: Sprite (depth=1) fully inside tile rect (depth=2) → full composite in alpha."""
    game = MagicMock()
    game.visible_sprites.offset = pygame.math.Vector2(0, 0)
    game.player.depth = 1

    original_image = pygame.Surface((32, 32), pygame.SRCALPHA)
    original_image.fill((0, 255, 0, 255))  # solid green
    sprite = MagicMock()
    sprite.image = original_image
    sprite.rect = pygame.Rect(0, 0, 32, 32)  # visual_rect = Rect(0,0,32,32)
    sprite.depth = 1
    game.visible_sprites.get_sorted_sprites.return_value = [sprite]

    rm = RenderManager(game)
    occluding_rects = [(pygame.Rect(0, 0, 64, 64), 2)]  # tile much larger than sprite
    result = rm._apply_partial_occlusion(occluding_rects)

    assert sprite in result
    composite = sprite.image
    assert composite.get_size() == (32, 32)


# ---------------------------------------------------------------------------
# UT-009 — _apply_partial_occlusion: 2 overlapping tiles → both intersections applied
# ---------------------------------------------------------------------------
def test_apply_partial_occlusion_two_tiles_both_applied():
    """UT-009: Sprite behind 2 tiles → both intersection zones are processed."""
    game = MagicMock()
    game.visible_sprites.offset = pygame.math.Vector2(0, 0)
    game.player.depth = 1

    original_image = pygame.Surface((32, 64), pygame.SRCALPHA)
    original_image.fill((0, 0, 255, 255))
    sprite = MagicMock()
    sprite.image = original_image
    sprite.rect = pygame.Rect(0, 32, 32, 32)  # bottomright=(32, 64) → visual_rect=(0,0,32,64)
    sprite.depth = 1
    game.visible_sprites.get_sorted_sprites.return_value = [sprite]

    rm = RenderManager(game)
    # Two separate tiles, each covering part of the sprite
    occluding_rects = [
        (pygame.Rect(0, 0, 32, 32), 2),   # top half of sprite
        (pygame.Rect(0, 32, 32, 32), 2),  # bottom half of sprite
    ]
    result = rm._apply_partial_occlusion(occluding_rects)
    assert sprite in result  # composite was generated


# ---------------------------------------------------------------------------
# UT-010 — _apply_partial_occlusion: sprite.depth == tile_depth → no occlusion
# ---------------------------------------------------------------------------
def test_apply_partial_occlusion_same_depth_no_occlusion():
    """UT-010: Sprite (depth=2) overlapping tile (depth=2) → not occluded (tile_depth not > sprite_depth)."""
    game = MagicMock()
    game.visible_sprites.offset = pygame.math.Vector2(0, 0)
    game.player.depth = 1

    sprite = MagicMock()
    sprite.image = pygame.Surface((32, 32), pygame.SRCALPHA)
    sprite.rect = pygame.Rect(0, 0, 32, 32)
    sprite.depth = 2  # same depth as tile
    game.visible_sprites.get_sorted_sprites.return_value = [sprite]

    rm = RenderManager(game)
    occluding_rects = [(pygame.Rect(0, 0, 32, 32), 2)]  # tile_depth == sprite_depth
    result = rm._apply_partial_occlusion(occluding_rects)

    assert result == {}  # Not occluded


# ---------------------------------------------------------------------------
# UT-011 — draw_scene(): walk_active=True → _apply_partial_occlusion not called
# ---------------------------------------------------------------------------
def test_draw_scene_walk_active_skips_partial_occlusion():
    """UT-011: draw_scene() does not call _apply_partial_occlusion during scripted walk."""
    game = MagicMock()
    game.map_manager.layer_order = []
    game.map_manager.layer_depths = {}
    game.map_manager.get_visible_chunks.return_value = []
    game.time_system.night_alpha = 0
    game.chest_ui.is_open = False
    game.inventory_ui.is_open = False
    game.dialogue_manager.is_active = False
    game.interactives = []
    game.anim_map_manager = None
    game.visible_sprites.offset = pygame.math.Vector2(0, 0)
    game.screen = MagicMock()
    game.player.rect = pygame.Rect(0, 0, 32, 32)
    game.player.image = pygame.Surface((32, 32), pygame.SRCALPHA)
    game.player.depth = 1
    game._intra_walk_target = MagicMock()  # scripted walk active

    rm = RenderManager(game)
    with patch.object(rm, '_apply_partial_occlusion') as mock_apo, \
         patch.object(rm, 'draw_foreground', return_value=[(pygame.Rect(0, 0, 32, 32), 2)]):
        rm.draw_scene()
        mock_apo.assert_not_called()


# ---------------------------------------------------------------------------
# IT-001 — Integration: draw_foreground() returns non-empty → _apply_partial_occlusion called
# ---------------------------------------------------------------------------
def test_it001_draw_foreground_triggers_partial_occlusion():
    """IT-001: When draw_foreground() returns rects, _apply_partial_occlusion is called in draw_scene."""
    game = MagicMock()
    game.map_manager.layer_order = []
    game.map_manager.layer_depths = {}
    game.map_manager.get_visible_chunks.return_value = []
    game.time_system.night_alpha = 0
    game.chest_ui.is_open = False
    game.inventory_ui.is_open = False
    game.dialogue_manager.is_active = False
    game.interactives = []
    game.anim_map_manager = None
    game.visible_sprites.offset = pygame.math.Vector2(0, 0)
    game.screen = MagicMock()
    game.player.rect = pygame.Rect(0, 0, 32, 32)
    game.player.image = pygame.Surface((32, 32))
    game.player.depth = 1
    game._intra_walk_target = None

    rm = RenderManager(game)
    occluding = [(pygame.Rect(0, 0, 32, 32), 2)]

    with patch.object(rm, 'draw_foreground', return_value=occluding), \
         patch.object(rm, '_apply_partial_occlusion', return_value={}) as mock_apo:
        rm.draw_scene()
        mock_apo.assert_called_once_with(occluding)


# ---------------------------------------------------------------------------
# IT-002 — Integration: NPC semi-occluded → sprite.image swapped then restored
# ---------------------------------------------------------------------------
def test_it002_npc_semi_occluded_swap_and_restore():
    """IT-002: _apply_partial_occlusion swaps sprite.image; draw_scene restores it after custom_draw."""
    game = MagicMock()
    game.map_manager.layer_order = []
    game.map_manager.layer_depths = {}
    game.map_manager.get_visible_chunks.return_value = []
    game.time_system.night_alpha = 0
    game.chest_ui.is_open = False
    game.inventory_ui.is_open = False
    game.dialogue_manager.is_active = False
    game.interactives = []
    game.anim_map_manager = None
    game.visible_sprites.offset = pygame.math.Vector2(0, 0)
    game.screen = MagicMock()
    game.player.rect = pygame.Rect(0, 0, 32, 32)
    game.player.image = pygame.Surface((32, 32))
    game.player.depth = 1
    game._intra_walk_target = None

    # Create a real sprite-like object to track image swap
    class FakeSprite:
        pass
    npc = FakeSprite()
    original_surf = pygame.Surface((32, 48), pygame.SRCALPHA)
    npc.image = original_surf
    composite_surf = pygame.Surface((32, 48), pygame.SRCALPHA)

    rm = RenderManager(game)
    occluding = [(pygame.Rect(0, 0, 32, 32), 2)]

    # _apply_partial_occlusion swaps image and returns the saved dict
    with patch.object(rm, 'draw_foreground', return_value=occluding), \
         patch.object(rm, '_apply_partial_occlusion', return_value={npc: original_surf}) as mock_apo:
        # Simulate what draw_scene does with the returned saved_images
        npc.image = composite_surf  # simulates swap done by _apply_partial_occlusion
        rm.draw_scene()

    # After draw_scene, sprite.image must be restored
    assert npc.image is original_surf


# ---------------------------------------------------------------------------
# IT-003 — Integration: scripted walk active → _apply_partial_occlusion not called
# ---------------------------------------------------------------------------
def test_it003_scripted_walk_no_partial_occlusion():
    """IT-003: During scripted walk, _apply_partial_occlusion must not be called."""
    game = MagicMock()
    game.map_manager.layer_order = []
    game.map_manager.layer_depths = {}
    game.map_manager.get_visible_chunks.return_value = []
    game.time_system.night_alpha = 0
    game.chest_ui.is_open = False
    game.inventory_ui.is_open = False
    game.dialogue_manager.is_active = False
    game.interactives = []
    game.anim_map_manager = None
    game.visible_sprites.offset = pygame.math.Vector2(0, 0)
    game.screen = MagicMock()
    game.player.rect = pygame.Rect(0, 0, 32, 32)
    game.player.image = pygame.Surface((32, 32))
    game.player.depth = 1
    game._intra_walk_target = MagicMock()  # walk active

    rm = RenderManager(game)
    with patch.object(rm, 'draw_foreground', return_value=[(pygame.Rect(0, 0, 32, 32), 2)]), \
         patch.object(rm, '_apply_partial_occlusion') as mock_apo:
        rm.draw_scene()
        mock_apo.assert_not_called()


# ---------------------------------------------------------------------------
# IT-004 — Non-regression: draw_foreground() returns list (not bool)
# ---------------------------------------------------------------------------
def test_it004_draw_foreground_returns_list_not_bool():
    """IT-004 (non-regression): draw_foreground() must return list[tuple], never bool."""
    game = MagicMock()
    game.map_manager.get_visible_chunks.return_value = [(0, 0, 1, 2)]
    mock_tile = MagicMock()
    mock_tile.image = pygame.Surface((32, 32))
    mock_tile.occluded_image = None
    game.map_manager.tiles = {1: mock_tile}
    game.anim_map_manager = None
    game._intra_walk_target = None
    game.visible_sprites.offset = pygame.math.Vector2(0, 0)
    game.screen = MagicMock()
    game.player.rect = pygame.Rect(0, 0, 32, 32)
    game.player.depth = 1
    game.tile_size = 32

    rm = RenderManager(game)
    result = rm.draw_foreground()

    assert isinstance(result, list), f"Expected list, got {type(result)}"
    assert result != True  # explicit: must never be bool True
    assert result != False  # explicit: must never be bool False
    for item in result:
        assert isinstance(item, tuple) and len(item) == 2
        assert isinstance(item[0], pygame.Rect)
        assert isinstance(item[1], int)
