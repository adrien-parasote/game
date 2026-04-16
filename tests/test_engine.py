import pygame
import pytest
from src.engine.game import Game

def test_game_map_initialization():
    # Initialize pygame for surface creation
    pygame.init()
    pygame.display.set_mode((1, 1), pygame.HIDDEN)
    
    game = Game()
    
    # Check map size (should be 25x25 based on 00-castel.tmj)
    assert game.map_size == 25
    assert hasattr(game, 'map_manager')
    
    # Verify map manager is initialized
    assert game.map_manager is not None
    
    pygame.quit()

def test_game_fps_settings():
    pygame.init()
    pygame.display.set_mode((1, 1), pygame.HIDDEN)
    game = Game()
    
    # In run(), tick(60) is used. We can't easily test the loop 
    # but we can verify dependencies are set.
    assert game.clock is not None
    
    pygame.quit()

def test_game_fullscreen_logic():
    pygame.init()
    pygame.display.set_mode((1280, 720), pygame.HIDDEN)
    game = Game()
    initial_fs = game.is_fullscreen
    
    # Toggle once
    game.toggle_fullscreen()
    assert game.is_fullscreen != initial_fs
    
    # Toggle back
    game.toggle_fullscreen()
    assert game.is_fullscreen == initial_fs
    
    pygame.quit()

def test_game_draw():
    pygame.init()
    pygame.display.set_mode((1280, 720), pygame.HIDDEN)
    game = Game()
    
    # Manually set offset to (0, 0)
    game.visible_sprites.offset = pygame.math.Vector2(0, 0)
    
    # Calling new draw methods should not crash
    game._draw_background()
    game._draw_foreground()
    game._draw_hud()
    
    pygame.quit()
