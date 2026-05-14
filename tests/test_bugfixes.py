import pytest
import pygame
from unittest.mock import MagicMock, patch
from src.engine.game_state_manager import GameStateManager
from src.engine.game import Game
from src.entities.player import Player

@patch("pygame.mouse.set_visible")
def test_cursor_is_hidden_during_gameplay(mock_mouse):
    # Init GSM
    gsm = GameStateManager()
    # Transition to playing
    gsm._transition_to_playing(slot_id=None)
    
    # It should set cursor to False
    mock_mouse.assert_called_with(False)

@patch("pygame.display.toggle_fullscreen")
@patch("pygame.display.set_mode")
def test_lighting_manager_uses_actual_screen_size(mock_set_mode, mock_toggle_fullscreen):
    # Mock set_mode to return a surface of specific size
    mock_set_mode.return_value = pygame.Surface((1920, 1080))
    
    game = Game(skip_map_load=True)
    # The lighting manager should have the actual screen size (1920, 1080)
    assert game.lighting_manager.screen_size == (1920, 1080)
    
    mock_toggle_fullscreen.side_effect = pygame.error("Failed")
    mock_set_mode.return_value = pygame.Surface((2560, 1440))
    game.toggle_fullscreen()
    assert game.lighting_manager.screen_size == (2560, 1440)

def test_player_can_move_on_large_map():
    # Mock game map manager with large dimensions
    game_mock = MagicMock()
    game_mock.map_manager.width = 50
    game_mock.map_manager.height = 50
    game_mock.map_manager.get_direction_flags.return_value = {"any"}
    
    player = Player((0, 0))
    player.game = game_mock
    
    # Try to move past the hardcoded 32x32 tiles (32*32=1024)
    player.pos = pygame.math.Vector2(1010, 1010)
    player.direction = pygame.math.Vector2(1, 0)
    player.start_move()
    
    # Target pos should not be clamped to 1024
    assert player.target_pos.x > 1024

def test_tile_depth_overrides_layer_depth():
    from src.map.manager import MapManager
    from src.map.layout import OrthogonalLayout
    
    # Create a mock map where layer '00-ground' (depth 0) contains a tile with depth 2
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
            2: MockTile(depth=2),  # This tile should act as foreground!
        }
    }
    
    layout = OrthogonalLayout(32)
    manager = MapManager(map_data, layout)
    
    # 1. get_visible_chunks with min_depth=1 should yield tile 2, despite layer depth being 0
    chunks = list(manager.get_visible_chunks(pygame.Rect(0, 0, 100, 100), min_depth=1))
    assert len(chunks) == 1
    assert chunks[0][2] == 2  # tile_id
    assert chunks[0][3] == 2  # depth
    
    # 2. get_layer_surface should NOT include tile 2 (since its depth > 1)
    # The mock surface for get_layer_surface will have a dummy mock object,
    # but since our mock tiles' images are pygame.Surface, we can't easily assert blit on them without mocking pygame.
    # We can mock the surface returned by pygame_module.Surface
    mock_pygame = MagicMock()
    mock_surface = MagicMock()
    mock_pygame.Surface.return_value = mock_surface
    mock_pygame.SRCALPHA = 1
    
    manager.get_layer_surface(1, mock_pygame, max_bg_depth=1)
    
    # It should have called blit for tile 1 (depth=0) but not for tile 2 (depth=2)
    assert mock_surface.blit.call_count == 1
    # Check that it was called with tile 1's image
    mock_surface.blit.assert_called_with(map_data["tiles"][1].image, (32, 0))
