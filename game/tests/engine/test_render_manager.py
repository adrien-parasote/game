"""Tests for RenderManager - rendering background, foreground, scene and HUD."""

from unittest.mock import MagicMock, patch

import pygame
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
    occ_rect, depth, tile_img = result[0]
    assert isinstance(occ_rect, pygame.Rect)
    assert depth == 2
    assert occ_rect == pygame.Rect(0, 0, 32, 32)  # screen_pos=(0,0), tile_size=32
    assert isinstance(tile_img, pygame.Surface)  # tile image now included


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
