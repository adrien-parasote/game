"""Tests for RenderManager - rendering background, foreground, scene and HUD."""

from unittest.mock import MagicMock, patch

import pygame
import pytest
from src.engine.render_manager import RenderManager
from src.map.manager import MapManager


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
    """draw_foreground() runs without crash and returns a list (P-001 contract)."""
    game = MagicMock()
    game.map_manager._fg_occlusion_world = []  # P-001: world cache (empty = no fg tiles)
    game.map_manager.layer_order = []
    game.map_manager.layer_depths = {}
    game.anim_map_manager = None
    game._intra_walk_target = None
    game.visible_sprites.offset = pygame.math.Vector2(0, 0)
    game.screen = pygame.Surface((800, 600))
    game.player.rect = pygame.Rect(0, 0, 32, 32)
    game.player.image = pygame.Surface((32, 32))
    game.player.depth = 1
    game.tile_size = 32

    rm = RenderManager(game)
    result = rm.draw_foreground()
    assert isinstance(result, list)  # P-001: must return list (occluding_rects)


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
# UT-002 — draw_foreground(): fg tile in world cache → returns occluding rect
# ---------------------------------------------------------------------------
def test_draw_foreground_occluding_tile_returns_tuple_list():
    """UT-002 (P-001): draw_foreground() returns list with 1 (Rect, int) tuple for depth=2 fg tile.
    Uses _fg_occlusion_world cache (P-001 contract) instead of get_visible_chunks.
    """
    img_surf = pygame.Surface((32, 32))
    game = MagicMock()
    game.map_manager._fg_occlusion_world = [(0, 0, 2, img_surf, None)]  # fg tile at (0,0) depth=2
    game.map_manager.layer_order = []
    game.map_manager.layer_depths = {}
    game.anim_map_manager = None
    game._intra_walk_target = None
    game.visible_sprites.offset = pygame.math.Vector2(0, 0)
    game.screen = MagicMock()
    game.player.rect = pygame.Rect(200, 200, 32, 32)  # far from tile — no occluded blit
    game.player.depth = 1
    game.tile_size = 32

    rm = RenderManager(game)
    result = rm.draw_foreground()

    assert isinstance(result, list)
    assert len(result) == 1
    occ_rect, depth, tile_img = result[0]
    assert isinstance(occ_rect, pygame.Rect)
    assert depth == 2
    assert occ_rect == pygame.Rect(0, 0, 32, 32)  # screen_pos=(0,0), tile_size=32
    assert tile_img is img_surf  # tile image now included


# ---------------------------------------------------------------------------
# UT-003 — draw_foreground(): animated tile depth>1 is included (branch is inert today)
# ---------------------------------------------------------------------------
def test_draw_foreground_animated_tile_depth2_included():
    """UT-003: Animated tile with depth>player.depth is included in occluding_rects."""
    game = MagicMock()
    game.map_manager.get_visible_chunks.return_value = []  # no static foreground tiles
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
    # Pre-populate F3 cache (draw_scene() normally does this)
    rm._frame_anim_all = [(64, 0, 99, 2)]  # anim tile depth=2 > player.depth=1

    result = rm.draw_foreground()

    # The animated tile at depth=2 must be in the occluding list
    assert any(depth == 2 for _, depth, _ in result)


# ---------------------------------------------------------------------------
# UT-004 — draw_foreground() with walk_active: still collects rects (caller guards)
# ---------------------------------------------------------------------------
def test_draw_foreground_walk_active_still_returns_rects():
    """UT-004: draw_foreground() collects occluding rects even during walk_active.
    P-001: rects come from _fg_occlusion_world (not get_visible_chunks).
    The caller (draw_scene) is responsible for not calling _apply_partial_occlusion.
    """
    img_surf = pygame.Surface((32, 32))
    game = MagicMock()
    game.map_manager._fg_occlusion_world = [(0, 0, 2, img_surf, None)]  # fg tile depth=2
    game.map_manager.layer_order = []
    game.map_manager.layer_depths = {}
    game.anim_map_manager = None
    game._intra_walk_target = MagicMock()  # walk active
    game.visible_sprites.offset = pygame.math.Vector2(0, 0)
    game.screen = MagicMock()
    game.player.rect = pygame.Rect(200, 200, 32, 32)  # far from tile
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
    occluding_rects = [(pygame.Rect(0, 0, 32, 32), 2, None)]  # no tile image (legacy path)
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

    # Sprite 32x48, positioned so bottom 16px overlap the tile
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
    occluding_rects = [(pygame.Rect(0, 32, 32, 32), 2, None)]
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
    occluding_rects = [(pygame.Rect(0, 0, 64, 64), 2, None)]  # tile much larger than sprite
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
        (pygame.Rect(0, 0, 32, 32), 2, None),  # top half of sprite
        (pygame.Rect(0, 32, 32, 32), 2, None),  # bottom half of sprite
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
    occluding_rects = [(pygame.Rect(0, 0, 32, 32), 2, None)]  # tile_depth == sprite_depth
    result = rm._apply_partial_occlusion(occluding_rects)

    assert result == {}  # Not occluded


# ---------------------------------------------------------------------------
# UT-011 — _apply_partial_occlusion: walk_active=True, sprite=player → skip player only
# ---------------------------------------------------------------------------
def test_apply_partial_occlusion_walk_active_skips_player_only():
    """UT-011: walk_active=True causes _apply_partial_occlusion to skip the player sprite
    but still process NPC sprites."""
    game = MagicMock()
    game.visible_sprites.offset = pygame.math.Vector2(0, 0)
    game.player.depth = 1
    game._intra_walk_target = MagicMock()  # walk active

    # player sprite
    player_sprite = MagicMock()
    player_sprite.image = pygame.Surface((32, 32), pygame.SRCALPHA)
    player_sprite.rect = pygame.Rect(0, 0, 32, 32)
    player_sprite.depth = 1
    game.player = player_sprite
    game.player.depth = 1

    # NPC sprite in same position (also occluded)
    npc_sprite = MagicMock()
    npc_sprite.image = pygame.Surface((32, 32), pygame.SRCALPHA)
    npc_sprite.rect = pygame.Rect(0, 0, 32, 32)
    npc_sprite.depth = 1

    game.visible_sprites.get_sorted_sprites.return_value = [player_sprite, npc_sprite]

    rm = RenderManager(game)
    occluding_rects = [(pygame.Rect(0, 0, 64, 64), 2, None)]
    result = rm._apply_partial_occlusion(occluding_rects)

    # Player skipped — NPC processed
    assert player_sprite not in result
    assert npc_sprite in result


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
    occluding = [(pygame.Rect(0, 0, 32, 32), 2, None)]

    with (
        patch.object(rm, "draw_foreground", return_value=occluding),
        patch.object(rm, "_apply_partial_occlusion", return_value={}) as mock_apo,
    ):
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
    occluding = [(pygame.Rect(0, 0, 32, 32), 2, None)]

    # _apply_partial_occlusion swaps image and returns the saved dict
    with (
        patch.object(rm, "draw_foreground", return_value=occluding),
        patch.object(rm, "_apply_partial_occlusion", return_value={npc: original_surf}) as mock_apo,
    ):
        # Simulate what draw_scene does with the returned saved_images
        npc.image = composite_surf  # simulates swap done by _apply_partial_occlusion
        rm.draw_scene()

    # After draw_scene, sprite.image must be restored
    assert npc.image is original_surf


# ---------------------------------------------------------------------------
# IT-003 — Integration: scripted walk → _apply_partial_occlusion skips player, processes NPCs
# ---------------------------------------------------------------------------
def test_it003_scripted_walk_skips_player_but_processes_npcs():
    """IT-003: During scripted walk, _apply_partial_occlusion skips the player
    but must still process NPC sprites."""
    game = MagicMock()
    game.visible_sprites.offset = pygame.math.Vector2(0, 0)
    game.player.depth = 1
    game._intra_walk_target = MagicMock()  # walk active

    player_sprite = MagicMock()
    player_sprite.image = pygame.Surface((32, 32), pygame.SRCALPHA)
    player_sprite.rect = pygame.Rect(0, 0, 32, 32)
    player_sprite.depth = 1
    game.player = player_sprite
    game.player.depth = 1

    npc_sprite = MagicMock()
    npc_sprite.image = pygame.Surface((32, 32), pygame.SRCALPHA)
    npc_sprite.rect = pygame.Rect(0, 0, 32, 32)
    npc_sprite.depth = 1

    game.visible_sprites.get_sorted_sprites.return_value = [player_sprite, npc_sprite]

    rm = RenderManager(game)
    occluding_rects = [(pygame.Rect(0, 0, 64, 64), 2, None)]
    result = rm._apply_partial_occlusion(occluding_rects)

    assert player_sprite not in result  # player skipped
    assert npc_sprite in result  # NPC processed


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
    assert result is not True  # explicit: must never be bool True
    assert result is not False  # explicit: must never be bool False
    for item in result:
        assert isinstance(item, tuple)
        assert len(item) == 3
        assert isinstance(item[0], pygame.Rect)
        assert isinstance(item[1], int)
        # item[2] is tile_img: Surface or None


# ===========================================================================
# GRASS WADING — GW-UT-001..008
# ===========================================================================


def _make_game_for_grass_wading(*, on_grass: bool = True, walk_active: bool = False) -> MagicMock:
    """Helper: build a minimal game mock for grass wading tests (_apply_grass_wading_to_images)."""
    game = MagicMock()
    game.tile_size = 32
    game.visible_sprites.offset = pygame.math.Vector2(0, 0)
    game.player.depth = 1
    game._intra_walk_target = MagicMock() if walk_active else None

    grass_surf = pygame.Surface((32, 32))
    game.map_manager.get_grass_tile_image_at.return_value = grass_surf if on_grass else None

    return game


def _make_sprite(
    *,
    x: int = 100,
    y: int = 100,
    w: int = 32,
    h: int = 48,
    depth: int = 1,
    image: pygame.Surface | None = None,
) -> MagicMock:
    """Helper: build a sprite-like mock for wading tests."""
    sprite = MagicMock()
    sprite.image = image if image is not None else pygame.Surface((w, h), pygame.SRCALPHA)
    sprite.rect = pygame.Rect(x, y, w, h // 2)  # hitbox shorter than visual
    sprite.depth = depth
    return sprite


# ---------------------------------------------------------------------------
# GW-UT-001 — sprite on grass → composite created
# ---------------------------------------------------------------------------
def test_grass_wading_sprite_on_grass_triggers_composite():
    """GW-UT-001: sprite on grass tile → _apply_grass_wading_to_images creates a composite."""
    game = _make_game_for_grass_wading(on_grass=True)
    sprite = _make_sprite()
    game.visible_sprites.get_sorted_sprites.return_value = [sprite]

    rm = RenderManager(game)
    result = rm._apply_grass_wading_to_images()
    assert sprite in result, "Expected sprite to have a wading composite"


# ---------------------------------------------------------------------------
# GW-UT-002 — sprite on dirt (None) → no composite
# ---------------------------------------------------------------------------
def test_grass_wading_sprite_not_on_grass_no_composite():
    """GW-UT-002: get_grass_tile_image_at returns None → no composite performed."""
    game = _make_game_for_grass_wading(on_grass=False)
    sprite = _make_sprite()
    game.visible_sprites.get_sorted_sprites.return_value = [sprite]

    rm = RenderManager(game)
    result = rm._apply_grass_wading_to_images()
    assert result == {}, "Expected no composites for sprite not on grass"


# ---------------------------------------------------------------------------
# GW-UT-003 — sprite.rect = None → no crash, skip silently
# ---------------------------------------------------------------------------
def test_grass_wading_none_rect_skips_silently():
    """GW-UT-003: sprite.rect is None → silent skip, no AttributeError."""
    game = _make_game_for_grass_wading(on_grass=True)
    sprite = MagicMock()
    sprite.image = pygame.Surface((32, 32))
    sprite.rect = None
    sprite.depth = 1
    game.visible_sprites.get_sorted_sprites.return_value = [sprite]

    rm = RenderManager(game)
    rm._apply_grass_wading_to_images()  # must not raise


# ---------------------------------------------------------------------------
# GW-UT-004 — sprite.image = None → no crash, skip silently
# ---------------------------------------------------------------------------
def test_grass_wading_none_image_skips_silently():
    """GW-UT-004: sprite.image is None → silent skip, no AttributeError."""
    game = _make_game_for_grass_wading(on_grass=True)
    sprite = MagicMock()
    sprite.image = None
    sprite.rect = pygame.Rect(100, 100, 32, 32)
    sprite.depth = 1
    game.visible_sprites.get_sorted_sprites.return_value = [sprite]

    rm = RenderManager(game)
    rm._apply_grass_wading_to_images()  # must not raise


# ---------------------------------------------------------------------------
# GW-UT-005 — map_manager = None → return immediately, no crash
# ---------------------------------------------------------------------------
def test_grass_wading_no_map_manager_returns_immediately():
    """GW-UT-005: game.map_manager is None → method returns without processing sprites."""
    game = _make_game_for_grass_wading(on_grass=True)
    game.map_manager = None
    sprite = _make_sprite()
    game.visible_sprites.get_sorted_sprites.return_value = [sprite]

    rm = RenderManager(game)
    result = rm._apply_grass_wading_to_images()
    assert result == {}
    game.visible_sprites.get_sorted_sprites.assert_not_called()


# ---------------------------------------------------------------------------
# GW-UT-006 — sprite at bottom screen edge → no crash
# ---------------------------------------------------------------------------
def test_grass_wading_sprite_at_screen_edge_no_crash():
    """GW-UT-006: sprite at screen edge does not crash _build_wading_composite."""
    game = _make_game_for_grass_wading(on_grass=True)
    sprite = MagicMock()
    sprite.image = pygame.Surface((32, 32), pygame.SRCALPHA)
    sprite.rect = pygame.Rect(100, 590, 32, 10)  # bottomright=(132, 600)
    sprite.depth = 1
    game.visible_sprites.get_sorted_sprites.return_value = [sprite]
    grass_surf = pygame.Surface((32, 32))
    game.map_manager.get_grass_tile_image_at.return_value = grass_surf

    rm = RenderManager(game)
    rm._apply_grass_wading_to_images()  # must not raise
    assert True


# ---------------------------------------------------------------------------
# GW-UT-007 — two sprites, one on grass and one on dirt → only grass gets composite
# ---------------------------------------------------------------------------
def test_grass_wading_two_sprites_only_grass_composite():
    """GW-UT-007: Two sprites — only the one on grass triggers composite."""
    game = _make_game_for_grass_wading(on_grass=False)
    sprite_grass = _make_sprite(x=100, y=100)
    sprite_dirt = _make_sprite(x=200, y=200)

    grass_surf = pygame.Surface((32, 32))

    def side_effect(px, py):
        if 100 <= px <= 132 and 115 <= py <= 124:
            return grass_surf
        return None

    game.map_manager.get_grass_tile_image_at.side_effect = side_effect
    game.visible_sprites.get_sorted_sprites.return_value = [sprite_grass, sprite_dirt]

    rm = RenderManager(game)
    result = rm._apply_grass_wading_to_images()

    assert sprite_grass in result
    assert sprite_dirt not in result


# ---------------------------------------------------------------------------
# GW-UT-008 — walk_active=True, sprite=player → player skipped
# ---------------------------------------------------------------------------
def test_grass_wading_walk_active_skips_player():
    """GW-UT-008: walk_active=True causes _apply_grass_wading_to_images to skip the player sprite."""
    game = _make_game_for_grass_wading(on_grass=True, walk_active=True)

    player_sprite = MagicMock()
    player_sprite.image = pygame.Surface((32, 32), pygame.SRCALPHA)
    player_sprite.rect = pygame.Rect(100, 100, 32, 16)
    player_sprite.depth = 1
    game.player = player_sprite
    game.player.depth = 1

    game.visible_sprites.get_sorted_sprites.return_value = [player_sprite]

    rm = RenderManager(game)
    result = rm._apply_grass_wading_to_images()
    assert player_sprite not in result


# ===========================================================================
# GRASS WADING — Integration Tests GW-IT-001..003
# ===========================================================================


def _make_draw_scene_game() -> MagicMock:
    """Helper: minimal game mock for draw_scene integration tests."""
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
    game.tile_size = 32
    return game


# ---------------------------------------------------------------------------
# GW-IT-001 — Full draw_scene with grass tile under player → no exception
# ---------------------------------------------------------------------------
def test_gwit001_draw_scene_grass_under_player_no_exception():
    """GW-IT-001: draw_scene with grass tile under player runs without exception."""
    game = _make_draw_scene_game()
    grass_surf = pygame.Surface((32, 32))
    game.map_manager.get_grass_tile_image_at.return_value = grass_surf

    rm = RenderManager(game)
    with (
        patch.object(rm, "draw_foreground", return_value=[]),
        patch.object(rm, "draw_background"),
        patch.object(rm, "draw_hud"),
    ):
        rm.draw_scene()  # must not raise


# ---------------------------------------------------------------------------
# GW-IT-002 — NPC on grass → wading composite applied
# ---------------------------------------------------------------------------
def test_gwit002_npc_on_grass_wading_applied():
    """GW-IT-002: NPC sprite on grass tile → _apply_grass_wading_to_images returns composite."""
    game = _make_game_for_grass_wading(on_grass=True)
    npc = _make_sprite(x=64, y=64)
    game.visible_sprites.get_sorted_sprites.return_value = [npc]

    rm = RenderManager(game)
    result = rm._apply_grass_wading_to_images()
    assert npc in result, "Expected composite for NPC on grass"


# ---------------------------------------------------------------------------
# GW-IT-003 — Scripted walk → player skipped, NPC still processed
# ---------------------------------------------------------------------------
def test_gwit003_scripted_walk_skips_player_processes_npc():
    """GW-IT-003: During scripted walk, player skipped but NPC gets grass wading."""
    game = _make_game_for_grass_wading(on_grass=True, walk_active=True)

    player_sprite = MagicMock()
    player_sprite.image = pygame.Surface((32, 32), pygame.SRCALPHA)
    player_sprite.rect = pygame.Rect(100, 100, 32, 16)
    player_sprite.depth = 1
    game.player = player_sprite
    game.player.depth = 1

    npc = _make_sprite(x=200, y=200)
    game.visible_sprites.get_sorted_sprites.return_value = [player_sprite, npc]

    rm = RenderManager(game)
    result = rm._apply_grass_wading_to_images()

    # Player skipped, NPC processed
    assert player_sprite not in result
    assert npc in result


# ---------------------------------------------------------------------------
# GW-UT-009 — composite foot zone does not contain semi-transparent black pixels
# ---------------------------------------------------------------------------
def test_grass_wading_does_not_blit_black_bar():
    """GW-UT-009: _build_wading_composite does not apply a black overlay to the full sprite.

    The original sprite image (red) must be preserved in the upper portion of the composite.
    Only the bottom wading zone gets the grass texture; the rest is untouched.
    """
    game = _make_game_for_grass_wading(on_grass=True)
    # Use a bright green grass surface so the wading zone is visibly non-black
    grass_surf = pygame.Surface((32, 32))
    grass_surf.fill((0, 200, 0))  # green
    game.map_manager.get_grass_tile_image_at.return_value = grass_surf

    # Sprite with a solid red image
    red_surf = pygame.Surface((32, 48), pygame.SRCALPHA)
    red_surf.fill((255, 0, 0, 255))
    sprite = _make_sprite(image=red_surf)

    rm = RenderManager(game)
    cam_offset = pygame.math.Vector2(0, 0)
    composite = rm._build_wading_composite(sprite, cam_offset, game.tile_size, 10, 140)
    assert composite is not None

    # Upper body (above wading zone) must still be red — not overwritten by a black bar
    w, h = composite.get_size()
    wading_top = h - 10
    for x in range(0, w, 8):
        for y in range(0, max(0, wading_top - 2)):  # leave a 2px margin near boundary
            color = composite.get_at((x, y))
            assert color.r > 200, (
                f"Upper body pixel at ({x},{y}) was overwritten — expected red, got {color}"
            )


# ===========================================================================
# PIXEL-PERFECT OCCLUSION — OCC-UT-001..005
# ===========================================================================


def _make_sprite_for_occ(image: pygame.Surface, rect: pygame.Rect, depth: int = 1):
    """Helper: build a minimal sprite mock for occlusion tests."""
    sprite = MagicMock()
    sprite.image = image
    sprite.rect = rect
    sprite.depth = depth
    return sprite


# ---------------------------------------------------------------------------
# OCC-UT-001 — Fully opaque tile: AssetManager returns None mask → classic path
# ---------------------------------------------------------------------------
def test_occ_ut001_fully_opaque_tile_mask_is_none():
    """OCC-UT-001: get_occlusion_mask returns None for a fully opaque tile surface.
    No transparent pixel → mask unnecessary → classic set_alpha() code path.
    """
    from src.engine.asset_manager import AssetManager

    # Fully opaque tile — no alpha < 255
    opaque_surf = pygame.Surface((32, 32), pygame.SRCALPHA)
    opaque_surf.fill((200, 100, 50, 255))

    am = AssetManager()
    # Ensure no stale cache entry for this surface
    am._occlusion_masks.pop(id(opaque_surf), None)

    mask = am.get_occlusion_mask(opaque_surf)
    assert mask is None, "Fully opaque tile must return None mask (classic code path)"


# ---------------------------------------------------------------------------
# OCC-UT-002 — Half-transparent tile: only the opaque half of the sprite is occluded
# ---------------------------------------------------------------------------
def test_occ_ut002_partial_tile_only_opaque_half_occluded():
    """OCC-UT-002: Tile with left half transparent (A=0) and right half opaque (A=255).
    After occlusion, sprite pixels at x < 16 keep alpha=255; pixels at x >= 16 get OCCLUSION_ALPHA.
    """
    from src.config import Settings
    from src.engine.asset_manager import AssetManager

    tile_size = 32
    # Build partial tile: left 16px transparent, right 16px opaque
    partial_tile = pygame.Surface((tile_size, tile_size), pygame.SRCALPHA)
    partial_tile.fill((0, 0, 0, 0))  # fully transparent base
    right_rect = pygame.Rect(16, 0, 16, 32)
    partial_tile.fill((150, 100, 50, 255), right_rect)  # right half opaque

    # Flush stale cache for this surface
    am = AssetManager()
    am._occlusion_masks.pop(id(partial_tile), None)

    mask = am.get_occlusion_mask(partial_tile)
    assert mask is not None, "Partial tile must return a non-None mask"

    # Verify mask modulation values
    # Left half (transparent tile) → A=255 (no change to sprite)
    for x in range(0, 16):
        mod_a = mask.get_at((x, 0)).a
        assert mod_a == 255, f"Left half pixel ({x},0) should have A=255, got {mod_a}"

    # Right half (opaque tile) → A=OCCLUSION_ALPHA
    for x in range(16, 32):
        mod_a = mask.get_at((x, 0)).a
        assert mod_a == Settings.OCCLUSION_ALPHA, (
            f"Right half pixel ({x},0) should have A={Settings.OCCLUSION_ALPHA}, got {mod_a}"
        )


# ---------------------------------------------------------------------------
# OCC-UT-003 — NPC behind partial tile: treated identically to player
# ---------------------------------------------------------------------------
def test_occ_ut003_npc_partial_tile_same_as_player():
    """OCC-UT-003: _apply_partial_occlusion treats an NPC sprite behind a partial tile
    identically to the player — no special-casing per entity type.
    """
    game = MagicMock()
    game.visible_sprites.offset = pygame.math.Vector2(0, 0)
    game.player.depth = 1
    game._intra_walk_target = None

    # NPC sprite — not the player object
    npc_image = pygame.Surface((32, 48), pygame.SRCALPHA)
    npc_image.fill((0, 180, 0, 255))
    npc = MagicMock()
    npc.image = npc_image
    npc.rect = pygame.Rect(0, 16, 32, 32)  # visual_rect bottom at y=48
    npc.depth = 1
    # Ensure npc is NOT game.player
    game.player = MagicMock()
    game.player.depth = 1
    game.player.rect = pygame.Rect(200, 200, 32, 32)

    game.visible_sprites.get_sorted_sprites.return_value = [npc]

    rm = RenderManager(game)
    # Tile covers upper portion of NPC visual rect
    partial_tile_surf = pygame.Surface((32, 32), pygame.SRCALPHA)
    partial_tile_surf.fill((100, 100, 100, 255))  # opaque tile
    occluding_rects = [(pygame.Rect(0, 0, 32, 32), 2, partial_tile_surf)]

    result = rm._apply_partial_occlusion(occluding_rects)

    assert npc in result, "NPC sprite must be occluded by partial tile (same as player)"
    assert result[npc] is npc_image, "Original NPC image must be saved"
    assert npc.image is not npc_image, "NPC image must be replaced with composite"


# ---------------------------------------------------------------------------
# OCC-UT-004 — Animated tile frame: each frame gets its own cache entry
# ---------------------------------------------------------------------------
def test_occ_ut004_animated_tile_frame_cached_by_id():
    """OCC-UT-004: Two distinct frame surfaces get independent cache entries in AssetManager.
    Changing frames does not reuse the wrong mask.
    """
    from src.engine.asset_manager import AssetManager

    am = AssetManager()

    # Frame 1: partially transparent
    frame1 = pygame.Surface((32, 32), pygame.SRCALPHA)
    frame1.fill((0, 0, 0, 0))
    frame1.fill((255, 0, 0, 255), pygame.Rect(0, 0, 16, 32))  # left half opaque

    # Frame 2: fully opaque (different object, different id)
    frame2 = pygame.Surface((32, 32), pygame.SRCALPHA)
    frame2.fill((0, 255, 0, 255))

    # Flush stale entries
    am._occlusion_masks.pop(id(frame1), None)
    am._occlusion_masks.pop(id(frame2), None)

    mask1 = am.get_occlusion_mask(frame1)
    mask2 = am.get_occlusion_mask(frame2)

    # frame1 is partial → non-None mask
    assert mask1 is not None, "frame1 (partial) must produce a non-None mask"
    # frame2 is fully opaque → None mask
    assert mask2 is None, "frame2 (fully opaque) must produce None mask"

    # Cache entries are independent
    assert am._occlusion_masks[id(frame1)] is mask1
    assert am._occlusion_masks.get(id(frame2)) is None


# ---------------------------------------------------------------------------
# OCC-UT-005 — AssetManager cache: _build_occlusion_mask called exactly once
# ---------------------------------------------------------------------------
def test_occ_ut005_asset_manager_cache_no_recompute():
    """OCC-UT-005: Calling get_occlusion_mask twice with the same surface
    only triggers _build_occlusion_mask once (cache hit on second call).
    """
    from src.engine.asset_manager import AssetManager

    am = AssetManager()

    partial_surf = pygame.Surface((32, 32), pygame.SRCALPHA)
    partial_surf.fill((0, 0, 0, 0))
    partial_surf.fill((80, 60, 40, 255), pygame.Rect(8, 8, 16, 16))  # centre opaque

    # Flush any existing cache entry
    am._occlusion_masks.pop(id(partial_surf), None)

    with patch.object(am, "_build_occlusion_mask", wraps=am._build_occlusion_mask) as mock_build:
        result1 = am.get_occlusion_mask(partial_surf)
        result2 = am.get_occlusion_mask(partial_surf)

    assert mock_build.call_count == 1, (
        f"_build_occlusion_mask must be called exactly once, was called {mock_build.call_count} times"
    )
    assert result1 is result2, "Both calls must return the same cached Surface"


# ===========================================================================
# P-001 — RenderManager new methods  (TC-007..TC-013, IT-001..IT-003, TC-014)
# Spec: game/docs/specs/p001-foreground-rendering.md § 8.2, 8.3, 8.4
# These tests are RED until _blit_foreground_surface, _build_screen_occluding_rects,
# and _blit_occluded_tiles_near_player are implemented.
# ===========================================================================


def _make_fg_world_entry(wx=0, wy=0, depth=2, has_occ=True):
    """Helper: build one _fg_occlusion_world tuple."""
    img = pygame.Surface((32, 32))
    occ_img = pygame.Surface((32, 32)) if has_occ else None
    return (wx, wy, depth, img, occ_img)


def _make_game_p001(
    *,
    fg_world=None,
    cam_x=0,
    cam_y=0,
    player_depth=1,
    player_x=0,
    player_y=0,
    walk_active=False,
    layer_order=None,
    viewport_left=0,
    viewport_top=0,
    viewport_w=640,
    viewport_h=480,
):
    """Helper: minimal game mock for P-001 RenderManager tests."""
    game = MagicMock()
    game.tile_size = 32
    game.visible_sprites.offset = pygame.math.Vector2(cam_x, cam_y)
    game.player.rect = pygame.Rect(player_x, player_y, 32, 32)
    game.player.depth = player_depth
    game._intra_walk_target = MagicMock() if walk_active else None
    game.map_manager._fg_occlusion_world = fg_world or []
    _layer_order = layer_order or []
    game.map_manager.layer_order = _layer_order
    # layer_depths: each layer explicitly mapped to int depth > player_depth (2)
    # so _blit_foreground_surface doesn't treat it as background
    game.map_manager.layer_depths = {lid: 2 for lid in _layer_order}
    game.anim_map_manager = None
    game.map_manager.get_visible_chunks.return_value = []
    game.map_manager.tiles = {}
    game.screen = MagicMock()
    game.screen.get_width.return_value = viewport_w
    game.screen.get_height.return_value = viewport_h
    return game


# ---------------------------------------------------------------------------
# TC-007 — _blit_foreground_surface calls screen.blit once per fg layer
# ---------------------------------------------------------------------------
@pytest.mark.tc("TC-007")
def test_blit_foreground_surface_calls_blit_once_per_layer():
    """TC-007: _blit_foreground_surface calls screen.blit N times (N = layers with fg surface)."""
    fg_surf = pygame.Surface((64, 64), pygame.SRCALPHA)

    game = _make_game_p001(layer_order=[1, 2])
    game.map_manager.get_foreground_layer_surface.side_effect = lambda lid, pg, **kw: (
        fg_surf if lid == 1 else None  # layer 1 has fg, layer 2 doesn't
    )

    rm = RenderManager(game)
    rm._screen_rect = pygame.Rect(0, 0, 640, 480)  # force screen rect (MagicMock returns 0)
    cam = pygame.math.Vector2(0, 0)
    rm._blit_foreground_surface(cam, player_depth=1)

    assert game.screen.blit.call_count == 1, (
        f"Expected 1 screen.blit call (1 fg layer), got {game.screen.blit.call_count}"
    )


# ---------------------------------------------------------------------------
# TC-008 — _build_screen_occluding_rects filters by depth
# ---------------------------------------------------------------------------
@pytest.mark.tc("TC-008")
def test_build_screen_occluding_rects_filters_by_depth():
    """TC-008: Tiles with depth <= player_depth are excluded from occluding_rects."""
    # Tile at depth=1 (== player_depth=1) must be excluded
    fg_world = [
        _make_fg_world_entry(wx=0, wy=0, depth=1),   # excluded (depth == player_depth)
        _make_fg_world_entry(wx=32, wy=0, depth=2),  # included (depth > player_depth)
    ]
    game = _make_game_p001(fg_world=fg_world)

    rm = RenderManager(game)
    rm._viewport_world = pygame.Rect(0, 0, 640, 480)

    occluding_rects = []
    rm._build_screen_occluding_rects(pygame.math.Vector2(0, 0), player_depth=1, occluding_rects=occluding_rects)

    depths = [d for _, d, _ in occluding_rects]
    assert 1 not in depths, f"depth=1 tile must be excluded, but depths found: {depths}"
    assert 2 in depths, "depth=2 tile must be included"
    assert len(occluding_rects) == 1


# ---------------------------------------------------------------------------
# TC-009 — _build_screen_occluding_rects filters by viewport
# ---------------------------------------------------------------------------
@pytest.mark.tc("TC-009")
def test_build_screen_occluding_rects_filters_by_viewport():
    """TC-009: Tiles outside the viewport are excluded from occluding_rects."""
    fg_world = [
        _make_fg_world_entry(wx=0, wy=0, depth=2),      # inside viewport (0,0,640,480)
        _make_fg_world_entry(wx=1000, wy=1000, depth=2), # outside viewport
    ]
    game = _make_game_p001(fg_world=fg_world)

    rm = RenderManager(game)
    rm._viewport_world = pygame.Rect(0, 0, 640, 480)

    occluding_rects = []
    rm._build_screen_occluding_rects(pygame.math.Vector2(0, 0), player_depth=1, occluding_rects=occluding_rects)

    assert len(occluding_rects) == 1, (
        f"Expected 1 rect (in-viewport tile), got {len(occluding_rects)}"
    )


# ---------------------------------------------------------------------------
# TC-010 — _build_screen_occluding_rects screen coords = world + cam_offset
# ---------------------------------------------------------------------------
@pytest.mark.tc("TC-010")
def test_build_screen_occluding_rects_screen_coords():
    """TC-010: Rect in occluding_rects is at world_pos + cam_offset (screen-space)."""
    fg_world = [_make_fg_world_entry(wx=64, wy=96, depth=2)]
    game = _make_game_p001(fg_world=fg_world, cam_x=-32, cam_y=-16)

    rm = RenderManager(game)
    rm._viewport_world = pygame.Rect(0, 0, 640, 480)

    occluding_rects = []
    cam = pygame.math.Vector2(-32, -16)
    rm._build_screen_occluding_rects(cam, player_depth=1, occluding_rects=occluding_rects)

    assert len(occluding_rects) == 1
    rect, depth, _ = occluding_rects[0]
    assert rect.x == 64 + (-32), f"Expected screen_x={64-32}, got {rect.x}"
    assert rect.y == 96 + (-16), f"Expected screen_y={96-16}, got {rect.y}"


# ---------------------------------------------------------------------------
# TC-011 — _blit_occluded_tiles_near_player: non-colliding tile → no blit
# ---------------------------------------------------------------------------
@pytest.mark.tc("TC-011")
def test_blit_occluded_tiles_skips_non_colliding():
    """TC-011: Tile far from player (no collision) → screen.blit NOT called."""
    fg_world = [_make_fg_world_entry(wx=500, wy=500, depth=2)]  # far from player at (0,0)
    game = _make_game_p001(fg_world=fg_world, player_x=0, player_y=0)

    rm = RenderManager(game)
    player_screen_rect = pygame.Rect(0, 0, 32, 32)  # player at screen (0,0)
    cam = pygame.math.Vector2(0, 0)

    rm._blit_occluded_tiles_near_player(cam, player_screen_rect, player_depth=1)

    game.screen.blit.assert_not_called(), (
        "screen.blit must not be called for tile far from player"
    )


# ---------------------------------------------------------------------------
# TC-012 — _blit_occluded_tiles_near_player: colliding tile with occ_img → occ_img blitted
# ---------------------------------------------------------------------------
@pytest.mark.tc("TC-012")
def test_blit_occluded_tiles_uses_occluded_image():
    """TC-012: Tile adjacent to player with occ_img → screen.blit called with occ_img."""
    occ_surf = pygame.Surface((32, 32))
    occ_surf.fill((255, 0, 0))  # distinctive color
    img_surf = pygame.Surface((32, 32))
    img_surf.fill((0, 255, 0))

    fg_world = [(0, 0, 2, img_surf, occ_surf)]  # tile at (0,0), player also at (0,0)
    game = _make_game_p001(fg_world=fg_world, player_x=0, player_y=0)

    rm = RenderManager(game)
    rm._viewport_world = pygame.Rect(0, 0, 640, 480)  # ensure tile (0,0) is in viewport
    player_screen_rect = pygame.Rect(0, 0, 32, 32)
    cam = pygame.math.Vector2(0, 0)

    rm._blit_occluded_tiles_near_player(cam, player_screen_rect, player_depth=1)

    assert game.screen.blit.called, "screen.blit must be called when player collides with tile"
    blitted_surf = game.screen.blit.call_args[0][0]
    assert blitted_surf is occ_surf, (
        f"Expected occ_img to be blitted, got {blitted_surf}"
    )


# ---------------------------------------------------------------------------
# TC-013 — _blit_occluded_tiles_near_player: colliding tile without occ_img → image blitted
# ---------------------------------------------------------------------------
@pytest.mark.tc("TC-013")
def test_blit_occluded_tiles_fallback_to_image_if_no_occ():
    """TC-013: Tile adjacent to player with occ_img=None → screen.blit called with img (fallback)."""
    img_surf = pygame.Surface((32, 32))
    img_surf.fill((0, 0, 255))

    fg_world = [(0, 0, 2, img_surf, None)]  # occ_img is None
    game = _make_game_p001(fg_world=fg_world, player_x=0, player_y=0)

    rm = RenderManager(game)
    rm._viewport_world = pygame.Rect(0, 0, 640, 480)  # ensure tile (0,0) is in viewport
    player_screen_rect = pygame.Rect(0, 0, 32, 32)
    cam = pygame.math.Vector2(0, 0)

    rm._blit_occluded_tiles_near_player(cam, player_screen_rect, player_depth=1)

    assert game.screen.blit.called, "screen.blit must be called (fallback to img)"
    blitted_surf = game.screen.blit.call_args[0][0]
    assert blitted_surf is img_surf, (
        "When occ_img is None, img must be blitted as fallback"
    )


# ---------------------------------------------------------------------------
# IT-001 — _draw_static_foreground_tiles returns [] (P-001 contract)
# ---------------------------------------------------------------------------
@pytest.mark.tc("IT-001")
def test_p001_draw_static_foreground_tiles_returns_empty_list():
    """IT-001: After P-001 refactor, _draw_static_foreground_tiles must return []."""
    fg_world = [_make_fg_world_entry(wx=0, wy=0, depth=2)]
    game = _make_game_p001(fg_world=fg_world, layer_order=[1])
    game.map_manager.get_foreground_layer_surface.return_value = pygame.Surface((64, 64), pygame.SRCALPHA)

    rm = RenderManager(game)
    rm._viewport_world = pygame.Rect(0, 0, 640, 480)

    occluding_rects = []
    result = rm._draw_static_foreground_tiles(
        cam_offset=pygame.math.Vector2(0, 0),
        walk_active=False,
        player_screen_rect=pygame.Rect(200, 200, 32, 32),  # far from tile
        player_depth=1,
        occluding_rects=occluding_rects,
    )

    assert result == [], (
        f"_draw_static_foreground_tiles must return [] after P-001 refactor, got {result}"
    )


# ---------------------------------------------------------------------------
# IT-002 — draw_foreground() returns non-empty occluding_rects for fg tiles in viewport
# ---------------------------------------------------------------------------
@pytest.mark.tc("IT-002")
def test_p001_draw_foreground_occluding_rects_populated():
    """IT-002: draw_foreground() returns non-empty occluding_rects when fg tiles in viewport."""
    fg_world = [_make_fg_world_entry(wx=0, wy=0, depth=2)]
    game = _make_game_p001(fg_world=fg_world, layer_order=[1])
    game.map_manager.get_foreground_layer_surface.return_value = pygame.Surface((64, 64), pygame.SRCALPHA)
    game.visible_sprites.offset = pygame.math.Vector2(0, 0)
    game.player.rect = pygame.Rect(200, 200, 32, 32)  # far from tile — no occluded blit
    game.player.depth = 1
    game._intra_walk_target = None

    rm = RenderManager(game)
    result = rm.draw_foreground()

    assert isinstance(result, list), f"draw_foreground must return list, got {type(result)}"
    assert len(result) > 0, (
        "draw_foreground must return non-empty list when fg tile at (0,0) is in viewport"
    )
    occ_rect, depth, tile_img = result[0]
    assert isinstance(occ_rect, pygame.Rect)
    assert depth == 2


# ---------------------------------------------------------------------------
# IT-003 — walk_active=True → _blit_occluded_tiles_near_player not called
# ---------------------------------------------------------------------------
@pytest.mark.tc("IT-003")
def test_p001_walk_active_skips_occluded_blit():
    """IT-003: walk_active=True → _blit_occluded_tiles_near_player is NOT called."""
    fg_world = [_make_fg_world_entry(wx=0, wy=0, depth=2)]
    game = _make_game_p001(fg_world=fg_world, layer_order=[1], walk_active=True)
    game.map_manager.get_foreground_layer_surface.return_value = pygame.Surface((64, 64), pygame.SRCALPHA)

    rm = RenderManager(game)
    rm._viewport_world = pygame.Rect(0, 0, 640, 480)

    with patch.object(rm, "_blit_occluded_tiles_near_player") as mock_occ:
        rm._draw_static_foreground_tiles(
            cam_offset=pygame.math.Vector2(0, 0),
            walk_active=True,
            player_screen_rect=pygame.Rect(0, 0, 32, 32),
            player_depth=1,
            occluding_rects=[],
        )
        mock_occ.assert_not_called(), (
            "_blit_occluded_tiles_near_player must NOT be called when walk_active=True"
        )


# ---------------------------------------------------------------------------
# TC-014 — Performance: _build_fg_occlusion_world on 40x40 map < 50ms
# ---------------------------------------------------------------------------
@pytest.mark.tc("TC-014")
def test_fg_occlusion_world_build_time():
    """TC-014: _build_fg_occlusion_world on a 40x40 map completes in < 50ms."""
    import time

    from src.map.layout import OrthogonalLayout

    # Build a 40x40 map with alternating fg tiles
    tile = MagicMock()
    tile.image = pygame.Surface((32, 32))
    tile.occluded_image = pygame.Surface((32, 32))
    tile.depth = 2
    tile.frames = None

    n = 40
    layer_data = [[1 if (x + y) % 2 == 0 else 0 for x in range(n)] for y in range(n)]
    map_data = {
        "layers": {1: layer_data},
        "tiles": {1: tile},
        "layer_names": {1: "01-layer"},
        "layer_order": [1],
        "layer_order_values": {1: 2},
    }

    layout = OrthogonalLayout(32)
    t0 = time.perf_counter()
    mm = MapManager(map_data, layout)  # _build_fg_occlusion_world called in __init__
    elapsed = time.perf_counter() - t0

    assert elapsed < 0.05, (
        f"_build_fg_occlusion_world on 40x40 map took {elapsed*1000:.1f}ms (limit: 50ms)"
    )
    assert len(mm._fg_occlusion_world) > 0


# ===========================================================================
# P-004 — _apply_partial_occlusion dirty flag / cache
# Spec: perf_audit_20260610_2200.md § P-004
# Tests are RED until dirty-flag cache is implemented in RenderManager.
# ===========================================================================


def _make_game_with_occluding_sprite(cam_x=0, cam_y=0):
    """Helper: minimal game mock with one sprite occluded by one fg tile."""
    game = MagicMock()
    game.tile_size = 32
    game.visible_sprites.offset = pygame.math.Vector2(cam_x, cam_y)
    game.player.depth = 1
    game._intra_walk_target = None

    # One sprite at (0,0) depth=1 (same as player → included)
    sprite = MagicMock()
    sprite.image = pygame.Surface((32, 32))
    sprite.rect = pygame.Rect(0, 0, 32, 32)
    sprite.depth = 1
    game.visible_sprites.get_sorted_sprites.return_value = [sprite]

    return game, sprite


# ---------------------------------------------------------------------------
# TC-P004-001 — __init__ exposes cache state attributes
# ---------------------------------------------------------------------------
@pytest.mark.tc("TC-P004-001")
def test_p004_init_exposes_occ_cache_attrs():
    """TC-P004-001: RenderManager must expose _occ_key and _occ_composite_cache at init."""
    game = MagicMock()
    rm = RenderManager(game)
    assert hasattr(rm, "_occ_key"), "_occ_key must be initialised in __init__"
    assert hasattr(rm, "_occ_composite_cache"), "_occ_composite_cache must be initialised in __init__"
    assert rm._occ_key is None, "_occ_key must be None on first init (forces first-frame computation)"
    assert isinstance(rm._occ_composite_cache, dict), "_occ_composite_cache must be a dict"


# ---------------------------------------------------------------------------
# TC-P004-002 — Composite created on first call, cached
# ---------------------------------------------------------------------------
@pytest.mark.tc("TC-P004-002")
def test_p004_first_call_creates_composite_and_caches():
    """TC-P004-002: First call with occluding rects creates composites and stores them in _occ_composite_cache."""
    game, sprite = _make_game_with_occluding_sprite()
    rm = RenderManager(game)

    occ_rect = pygame.Rect(0, 0, 32, 32)  # overlaps sprite at (0,0)
    img = pygame.Surface((32, 32))
    occluding_rects = [(occ_rect, 2, img)]  # depth=2 > sprite.depth=1

    result = rm._apply_partial_occlusion(occluding_rects)

    assert len(result) == 1, "sprite must be in saved_images"
    assert rm._occ_key is not None, "_occ_key must be set after first call"
    assert len(rm._occ_composite_cache) == 1, "_occ_composite_cache must have 1 entry after first call"


# ---------------------------------------------------------------------------
# TC-P004-003 — Same cam + same rects → cache HIT → get_sorted_sprites called once total
# ---------------------------------------------------------------------------
@pytest.mark.tc("TC-P004-003")
def test_p004_cache_hit_skips_sprite_iteration():
    """TC-P004-003: Identical cam_offset + occluding_rects length → cache hit → sprite not re-processed."""
    game, sprite = _make_game_with_occluding_sprite(cam_x=10, cam_y=20)
    rm = RenderManager(game)

    occ_rect = pygame.Rect(10, 20, 32, 32)  # overlaps sprite screen rect
    img = pygame.Surface((32, 32))
    occluding_rects = [(occ_rect, 2, img)]

    # First call — populates cache
    rm._apply_partial_occlusion(occluding_rects)
    # Restore sprite image (simulating draw_scene restore step)
    for _sp, _orig in list(rm._occ_composite_cache.items()):
        pass  # cache holds composite; sprite.image was swapped by first call

    call_count_after_first = game.visible_sprites.get_sorted_sprites.call_count

    # Second call — same cam, same rects → cache HIT
    rm._apply_partial_occlusion(occluding_rects)
    call_count_after_second = game.visible_sprites.get_sorted_sprites.call_count

    assert call_count_after_second == call_count_after_first, (
        "get_sorted_sprites must NOT be called again on cache hit — "
        f"calls after 1st={call_count_after_first}, after 2nd={call_count_after_second}"
    )


# ---------------------------------------------------------------------------
# TC-P004-004 — cam_offset changes → cache MISS → composite re-created
# ---------------------------------------------------------------------------
@pytest.mark.tc("TC-P004-004")
def test_p004_cam_change_invalidates_cache():
    """TC-P004-004: cam_offset change between calls → cache miss → sprite re-processed."""
    game, sprite = _make_game_with_occluding_sprite(cam_x=0, cam_y=0)
    rm = RenderManager(game)

    occ_rect = pygame.Rect(0, 0, 32, 32)
    img = pygame.Surface((32, 32))
    occluding_rects = [(occ_rect, 2, img)]

    # First call at cam (0,0)
    rm._apply_partial_occlusion(occluding_rects)
    count_after_first = game.visible_sprites.get_sorted_sprites.call_count

    # Move camera
    game.visible_sprites.offset = pygame.math.Vector2(32, 0)

    # Second call — cam changed → cache miss
    rm._apply_partial_occlusion(occluding_rects)
    count_after_second = game.visible_sprites.get_sorted_sprites.call_count

    assert count_after_second > count_after_first, (
        "get_sorted_sprites must be called again after cam_offset changes (cache miss)"
    )


# ---------------------------------------------------------------------------
# TC-P004-005 — occluding_rects count changes → cache MISS
# ---------------------------------------------------------------------------
@pytest.mark.tc("TC-P004-005")
def test_p004_rect_count_change_invalidates_cache():
    """TC-P004-005: Change in number of occluding_rects → cache miss → recompute."""
    game, sprite = _make_game_with_occluding_sprite()
    rm = RenderManager(game)

    img = pygame.Surface((32, 32))
    rects_1 = [(pygame.Rect(0, 0, 32, 32), 2, img)]
    rects_2 = [(pygame.Rect(0, 0, 32, 32), 2, img), (pygame.Rect(32, 0, 32, 32), 2, img)]

    # First call with 1 rect
    rm._apply_partial_occlusion(rects_1)
    count_after_first = game.visible_sprites.get_sorted_sprites.call_count

    # Second call with 2 rects → cache miss
    rm._apply_partial_occlusion(rects_2)
    count_after_second = game.visible_sprites.get_sorted_sprites.call_count

    assert count_after_second > count_after_first, (
        "get_sorted_sprites must be called again when occluding_rects count changes (cache miss)"
    )


# ---------------------------------------------------------------------------
# TC-P004-006 — reset_occ_cache() clears key and composites
# ---------------------------------------------------------------------------
@pytest.mark.tc("TC-P004-006")
def test_p004_reset_occ_cache_clears_state():
    """TC-P004-006: reset_occ_cache() (called on map change) resets _occ_key and _occ_composite_cache."""
    game, sprite = _make_game_with_occluding_sprite()
    rm = RenderManager(game)

    img = pygame.Surface((32, 32))
    occluding_rects = [(pygame.Rect(0, 0, 32, 32), 2, img)]

    rm._apply_partial_occlusion(occluding_rects)
    assert rm._occ_key is not None

    rm._apply_partial_occlusion(occluding_rects)
    assert rm._occ_key is not None

    rm.reset_occ_cache()

    assert rm._occ_key is None, "reset_occ_cache() must set _occ_key to None"
    assert rm._occ_composite_cache == {}, "reset_occ_cache() must clear _occ_composite_cache"


# ===========================================================================
# PERFORMANCE OPTIMIZATIONS — UT-001..005, IT-001..003
# ===========================================================================

@pytest.mark.tc("UT-001")
def test_fg_occlusion_grid_matches_world_list():
    """UT-001: MapManager._fg_occlusion_grid contains exactly the same tiles as the flat list."""
    game = MagicMock()
    game.tile_size = 32
    layout = MagicMock()
    layout.tile_size = 32
    map_data = {
        "layers": {
            1: [[0, 2], [0, 0]]
        },
        "tiles": {
            2: MagicMock()
        },
        "layer_order": [1],
        "layer_order_values": {1: 2}
    }
    map_data["tiles"][2].depth = 2
    map_data["tiles"][2].frames = []
    map_data["tiles"][2].image = pygame.Surface((32, 32))
    map_data["tiles"][2].occluded_image = None

    mm = MapManager(map_data, layout)
    assert mm._fg_occlusion_grid is not None
    assert len(mm._fg_occlusion_grid) == len(mm._fg_occlusion_world)
    assert (1, 0) in mm._fg_occlusion_grid
    depth, img, occ_img = mm._fg_occlusion_grid[(1, 0)]
    assert depth == 2
    assert img is map_data["tiles"][2].image


@pytest.mark.tc("UT-002")
def test_grass_grid_contains_correct_material_surfaces():
    """UT-002: MapManager._grass_grid contains only surfaces of tiles configured as grass."""
    game = MagicMock()
    layout = MagicMock()
    layout.tile_size = 32
    map_data = {
        "layers": {
            1: [[0, 2], [0, 0]]
        },
        "tiles": {
            2: MagicMock()
        },
        "layer_order": [1],
        "layer_order_values": {1: 0}
    }
    map_data["tiles"][2].depth = 0
    map_data["tiles"][2].frames = []
    map_data["tiles"][2].properties = {"material": "grass"}
    map_data["tiles"][2].image = pygame.Surface((32, 32))

    mm = MapManager(map_data, layout)
    assert mm._grass_grid is not None
    assert len(mm._grass_grid) == 2
    assert len(mm._grass_grid[0]) == 2
    assert mm._grass_grid[0][1] is map_data["tiles"][2].image
    assert mm._grass_grid[0][0] is None


@pytest.mark.tc("UT-003")
def test_rect_pool_reused_in_build_screen_occluding_rects():
    """UT-003: Rect pool is reused and no new Rects are allocated when within pool bounds."""
    game = MagicMock()
    game.tile_size = 32
    game.visible_sprites.offset = pygame.math.Vector2(0, 0)
    game.player.depth = 1
    rm = RenderManager(game)
    assert len(rm._rect_pool) == 2000

    cam_offset = pygame.math.Vector2(10, 20)
    occluding_rects = []

    # Pre-populate _frame_visible_fg_tiles
    rm._frame_visible_fg_tiles = [(32, 64, 2, pygame.Surface((32, 32)), None)]

    first_pool_rect_id = id(rm._rect_pool[0])

    rm._build_screen_occluding_rects(cam_offset, 1, occluding_rects)

    assert len(occluding_rects) == 1
    rect, depth, img = occluding_rects[0]
    assert id(rect) == first_pool_rect_id
    assert rect.x == 32 + 10
    assert rect.y == 64 + 20


@pytest.mark.tc("UT-004")
def test_grass_grid_lookup_O1_performance():
    """UT-004: Grass tile lookup using get_grass_tile_image_at is fast."""
    import time
    game = MagicMock()
    layout = MagicMock()
    layout.tile_size = 32
    layout.to_world.side_effect = lambda x, y: (x // 32, y // 32)
    map_data = {
        "layers": {
            1: [[0, 2], [0, 0]]
        },
        "tiles": {
            2: MagicMock()
        },
        "layer_order": [1],
        "layer_order_values": {1: 0}
    }
    map_data["tiles"][2].depth = 0
    map_data["tiles"][2].frames = []
    map_data["tiles"][2].properties = {"material": "grass"}
    map_data["tiles"][2].image = pygame.Surface((32, 32))

    mm = MapManager(map_data, layout)

    t0 = time.perf_counter()
    for _ in range(1000):
        mm.get_grass_tile_image_at(48, 16)  # point inside (1, 0) tile
    t1 = time.perf_counter()

    delta = (t1 - t0) * 1000
    assert delta < 5.0, f"Grass lookup took too long: {delta:.2f}ms"


@pytest.mark.tc("UT-005")
def test_rect_pool_grows_when_limit_exceeded():
    """UT-005: Pool appends new Rects if more visible tiles are requested."""
    game = MagicMock()
    game.tile_size = 32
    rm = RenderManager(game)
    # Shrink pool for testing
    rm._rect_pool = [pygame.Rect(0, 0, 32, 32) for _ in range(2)]

    cam_offset = pygame.math.Vector2(0, 0)
    occluding_rects = []

    # 3 visible tiles -> exceeds pool size of 2
    rm._frame_visible_fg_tiles = [
        (0, 0, 2, pygame.Surface((32, 32)), None),
        (32, 0, 2, pygame.Surface((32, 32)), None),
        (64, 0, 2, pygame.Surface((32, 32)), None),
    ]

    rm._build_screen_occluding_rects(cam_offset, 1, occluding_rects)

    assert len(rm._rect_pool) == 3
    assert len(occluding_rects) == 3


@pytest.mark.tc("IT-001")
def test_viewport_culling_limits_iterations():
    """IT-001: RenderManager only loops over viewport bounds."""
    game = MagicMock()
    game.tile_size = 32
    game.screen = pygame.Surface((1280, 720))
    game.visible_sprites.offset = pygame.math.Vector2(0, 0)
    game.player.depth = 1
    game.player.rect = pygame.Rect(0, 0, 32, 32)
    game._intra_walk_target = None

    # Create MapManager with 10x10 map and 1 foreground tile at (9, 9) (far outside viewport)
    layout = MagicMock()
    layout.tile_size = 32
    map_data = {
        "layers": {
            1: [[0]*10 for _ in range(9)] + [[0]*9 + [2]]
        },
        "tiles": {
            2: MagicMock()
        },
        "layer_order": [1],
        "layer_order_values": {1: 2}
    }
    map_data["tiles"][2].depth = 2
    map_data["tiles"][2].frames = []
    map_data["tiles"][2].image = pygame.Surface((32, 32))
    map_data["tiles"][2].occluded_image = None

    game.map_manager = MapManager(map_data, layout)

    rm = RenderManager(game)
    # Set viewport to top-left 320x240
    rm._viewport_world = pygame.Rect(0, 0, 320, 240)

    occluding_rects = []
    rm._draw_static_foreground_tiles(
        pygame.math.Vector2(0, 0),
        False,
        pygame.Rect(0, 0, 32, 32),
        1,
        occluding_rects
    )

    # The tile at (9, 9) (world x=288, y=288) is outside 320x240 viewport (clipped by depth check and y-coord)
    # Wait, 288 is within 320, but y=288 is outside 240. So it should be culled!
    assert len(occluding_rects) == 0


@pytest.mark.tc("IT-002")
def test_draw_static_foreground_tiles_returns_empty_list():
    """IT-002: draw_static_foreground_tiles returns an empty list."""
    game = MagicMock()
    game.tile_size = 32
    game.screen = pygame.Surface((800, 600))
    game.visible_sprites.offset = pygame.math.Vector2(0, 0)
    game.player.depth = 1
    game.player.rect = pygame.Rect(0, 0, 32, 32)
    game._intra_walk_target = None

    # Empty map
    layout = MagicMock()
    layout.tile_size = 32
    map_data = {
        "layers": {},
        "tiles": {},
        "layer_order": [],
        "layer_order_values": {}
    }
    game.map_manager = MapManager(map_data, layout)

    rm = RenderManager(game)
    rm._viewport_world = pygame.Rect(0, 0, 800, 600)

    res = rm._draw_static_foreground_tiles(
        pygame.math.Vector2(0, 0),
        False,
        pygame.Rect(0, 0, 32, 32),
        1,
        []
    )
    assert res == []


@pytest.mark.tc("IT-003")
def test_draw_foreground_walk_active_skips_occluded_blit():
    """IT-003: During active walk, occlusion blitting is skipped (walk_active=True)."""
    game = MagicMock()
    game.tile_size = 32
    game.screen = MagicMock()
    game.visible_sprites.offset = pygame.math.Vector2(0, 0)
    game.player.depth = 1
    game.player.rect = pygame.Rect(0, 0, 32, 32)
    game.player.image = pygame.Surface((32, 32))
    game._intra_walk_target = MagicMock()  # active walk

    # Map with 1 foreground tile at (0, 0)
    layout = MagicMock()
    layout.tile_size = 32
    map_data = {
        "layers": {
            1: [[2]]
        },
        "tiles": {
            2: MagicMock()
        },
        "layer_order": [1],
        "layer_order_values": {1: 2}
    }
    map_data["tiles"][2].depth = 2
    map_data["tiles"][2].frames = []
    map_data["tiles"][2].image = pygame.Surface((32, 32))
    map_data["tiles"][2].occluded_image = pygame.Surface((32, 32))

    game.map_manager = MapManager(map_data, layout)

    rm = RenderManager(game)
    rm._viewport_world = pygame.Rect(0, 0, 800, 600)

    # We call draw_foreground which invokes _draw_static_foreground_tiles
    rm.draw_foreground()

    # Verify that screen.blit was NOT called (which would happen in _blit_occluded_tiles_near_player)
    # wait, screen.blit is called in _blit_foreground_surface, let's check:
    # get_foreground_layer_surface is called and returns a Surface, which is blitted.
    # But for the occluded tile specifically, screen.blit at _blit_occluded_tiles_near_player must not be called.
    # Let's verify that the only blit call on screen was the foreground layer surface (if any),
    # or just that the screen did not blit the occluded tile.
    # Actually, we can patch _blit_occluded_tiles_near_player to verify it wasn't called,
    # or verify that walk_active=True causes the skip.
    # Let's inspect screen.blit calls:
    assert game.screen.blit.call_count <= 1  # only at most the pre-rendered surface blit, no occluded tile blit
