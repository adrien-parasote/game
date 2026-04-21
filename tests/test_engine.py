import pygame
import pytest
from unittest.mock import patch, MagicMock
from src.engine.game import Game
from src.config import Settings

@pytest.fixture(autouse=True)
def mock_engine_deps():
    """Globally mock expensive engine dependencies for test_engine.py."""
    fake_map = {
        "width": 16, "height": 16,
        "layers": {"grounds": [[0]*16]*16},
        "tiles": {},
        "entities": [],
        "spawn_player": {"x": 256, "y": 256}
    }
    
    # We target specific mocks to avoid breaking logging or other os-dependent logic
    with patch('src.map.tmj_parser.TmjParser.load_map', return_value=fake_map), \
         patch('src.graphics.spritesheet.SpriteSheet'), \
         patch('pygame.image.load', return_value=pygame.Surface((32, 32))), \
         patch('src.engine.game.os.path.exists', return_value=True):
        yield

def test_game_map_initialization():
    # Initialize pygame for surface creation
    pygame.init()
    pygame.display.set_mode((1, 1), pygame.HIDDEN)
    
    game = Game()
    
    # Check map size (should be 16 based on our mock)
    assert game.map_size == 16
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
    # Ensure real surface is created for drawing tests
    screen = pygame.display.set_mode((1280, 720), pygame.HIDDEN)
    game = Game()
    
    # Ensure visible_sprites is a real CameraGroup with real Vector2 offset
    from src.entities.groups import CameraGroup
    game.visible_sprites = CameraGroup()
    game.visible_sprites.offset = pygame.math.Vector2(0, 0)
    
    # Calling draw methods should not crash
    # These internal calls use self.screen, self.visible_sprites.offset, etc.
    game._draw_background()
    game._draw_foreground()
    game._draw_hud()
    
    pygame.quit()

def test_game_title_version():
    """Verify the window title contains the version."""
    pygame.init()
    # Crucial: set_mode must be called for set_caption to have an effect
    pygame.display.set_mode((1, 1), pygame.HIDDEN)
    game = Game()
    
    # Check caption
    caption_tuple = pygame.display.get_caption()
    if caption_tuple:
        title = caption_tuple[0]
        assert f"v{Settings.VERSION}" in title
    
    pygame.quit()
