"""Tests for RenderManager - rendering background, foreground, scene and HUD."""
import pytest
import pygame
from unittest.mock import MagicMock, patch
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
