import pygame
import pytest
from unittest.mock import patch, MagicMock, PropertyMock
from src.entities.interactive import InteractiveEntity
from src.engine.game import Game
from src.config import Settings

@pytest.fixture
def test_game():
    pygame.init()
    pygame.display.set_mode((1, 1), pygame.HIDDEN)
    
    # Mock spritesheet loading
    with patch('src.graphics.spritesheet.SpriteSheet') as mock_sheet_class:
        mock_sheet = mock_sheet_class.return_value
        mock_sheet.valid = True
        mock_sheet.load_grid_by_size.side_effect = lambda w, h: [pygame.Surface((w, h)) for _ in range(16)]
        
        game = Game()
        yield game
            
    pygame.quit()

def test_sign_interaction_sets_active_dialogue(test_game):
    """Verify that interacting with a sign sets the game's active_dialogue."""
    # Create a sign with text
    sign = InteractiveEntity((100, 100), [], "sign", "sign.png", direction="up", text="Hello World")
    test_game.interactives.add(sign)
    
    # Player at South facing UP
    test_game.player.pos = pygame.math.Vector2(100, 132)
    test_game.player.current_state = 'up'
    test_game.player.is_moving = False
    test_game._interaction_cooldown = 0
    
    class MockKeys(dict):
        def __getitem__(self, key): return self.get(key, False)
    keys = MockKeys({Settings.INTERACT_KEY: True})
    
    with patch('pygame.key.get_pressed', return_value=keys):
        test_game._handle_interactions()
    
    # EXPECTED: active_dialogue should be set to "Hello World"
    # INITIAL: active_dialogue doesn't exist or isn't set
    assert hasattr(test_game, 'active_dialogue')
    assert test_game.active_dialogue == "Hello World"

def test_close_dialogue_clears_text(test_game):
    """Verify that pressing interact again clears the active dialogue."""
    test_game.active_dialogue = "Some Text"
    test_game._interaction_cooldown = 0
    
    class MockKeys(dict):
        def __getitem__(self, key): return self.get(key, False)
    keys = MockKeys({Settings.INTERACT_KEY: True})
    
    with patch('pygame.key.get_pressed', return_value=keys):
        test_game._handle_interactions()
        
    assert test_game.active_dialogue is None

def test_player_input_blocked_during_dialogue(test_game):
    """Verify that player movement input is ignored when dialogue is active."""
    test_game.active_dialogue = "Blocking Text"
    
    # Try to move DOWN
    class MockKeys(dict):
        def __getitem__(self, key): return self.get(key, False)
    keys = MockKeys({pygame.K_DOWN: True})
    
    with patch('pygame.key.get_pressed', return_value=keys):
        test_game.player.input()
        
    # Player should NOT start moving
    assert test_game.player.is_moving is False
    assert test_game.player.target_pos == test_game.player.pos
