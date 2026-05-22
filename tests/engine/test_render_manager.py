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


def test_render_manager_draw_foreground_occlusion():
    game = MagicMock()
    # Chunk includes tile at depth=2 (occluding) and depth=0 (background)
    game.map_manager.get_visible_chunks.return_value = [(0, 0, 1, 2), (32, 32, 2, 0)]

    mock_tile_1 = MagicMock()
    mock_tile_1.image = pygame.Surface((32, 32))
    mock_tile_1.occluded_image = None

    mock_tile_2 = MagicMock()
    mock_tile_2.image = pygame.Surface((32, 32))
    mock_tile_2.occluded_image = None

    game.map_manager.tiles = {1: mock_tile_1, 2: mock_tile_2}
    game.anim_map_manager = None

    game.visible_sprites.offset = pygame.math.Vector2(0, 0)
    game.screen = MagicMock()

    # Player rect perfectly overlaps the occluding tile at (0, 0)
    game.player.rect = pygame.Rect(0, 0, 32, 32)
    game.player.image = pygame.Surface((32, 32))
    game.player.depth = 1
    game.tile_size = 32

    rm = RenderManager(game)

    # TC-OCC-001: Should return True because player overlaps a depth=2 tile
    is_occluded = rm.draw_foreground()
    assert is_occluded is True

    # Now move player away so it doesn't overlap
    game.player.rect = pygame.Rect(100, 100, 32, 32)
    is_occluded = rm.draw_foreground()
    assert is_occluded is False


def test_render_manager_draw_scene_occlusion():
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

    # Player setup
    game.player.rect = pygame.Rect(0, 0, 32, 32)
    game.player.image = pygame.Surface((32, 32), pygame.SRCALPHA)
    game.player.image.set_alpha(255)
    game.player.depth = 1

    rm = RenderManager(game)

    with patch.object(rm, 'draw_foreground', return_value=True), \
         patch('src.config.Settings.OCCLUSION_ALPHA', 128):

        # We need to capture the alpha right before custom_draw is called
        def assert_alpha(*args, **kwargs):
            # When custom_draw is called for depth >= player, the alpha should be modified
            if kwargs.get('min_depth') == 1:
                assert game.player.image.get_alpha() == 128

        game.visible_sprites.custom_draw.side_effect = assert_alpha

        rm.draw_scene()

        # After draw_scene, alpha should be restored
        assert game.player.image.get_alpha() == 255
