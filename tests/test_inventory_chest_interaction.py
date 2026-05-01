import pytest
import pygame
from unittest.mock import MagicMock, patch
from src.engine.game import Game
from src.config import Settings

@pytest.fixture
def mock_game_setup():
    """Setup a partially mocked Game instance for event handling tests."""
    with patch('src.engine.game.Game.__init__', return_value=None), \
         patch('src.engine.game.Game._setup_logging'):
        game = Game()
        game.inventory_ui = MagicMock()
        game.chest_ui = MagicMock()
        game.dialogue_manager = MagicMock()
        
        # Default states
        game.inventory_ui.is_open = False
        game.chest_ui.is_open = False
        game.dialogue_manager.is_active = False
        
        return game

def test_inventory_wont_open_when_chest_is_open(mock_game_setup):
    """Verify that inventory toggle is blocked when a chest is open."""
    game = mock_game_setup
    game.chest_ui.is_open = True
    
    # Simulate pressing the inventory key
    event = pygame.event.Event(pygame.KEYDOWN, {'key': Settings.INVENTORY_KEY})
    with patch('pygame.event.get', return_value=[event]):
        game._handle_events()
    
    # Verify toggle() was NOT called
    game.inventory_ui.toggle.assert_not_called()

def test_inventory_toggles_normally_when_no_chest(mock_game_setup):
    """Verify that inventory toggle works when no chest/dialogue is active."""
    game = mock_game_setup
    game.chest_ui.is_open = False
    game.dialogue_manager.is_active = False
    
    # Simulate pressing the inventory key
    event = pygame.event.Event(pygame.KEYDOWN, {'key': Settings.INVENTORY_KEY})
    with patch('pygame.event.get', return_value=[event]):
        game._handle_events()
    
    # Verify toggle() WAS called
    game.inventory_ui.toggle.assert_called_once()

def test_inventory_wont_open_during_dialogue(mock_game_setup):
    """Verify that inventory toggle is blocked during dialogue (existing behavior)."""
    game = mock_game_setup
    game.dialogue_manager.is_active = True
    
    # Simulate pressing the inventory key
    event = pygame.event.Event(pygame.KEYDOWN, {'key': Settings.INVENTORY_KEY})
    with patch('pygame.event.get', return_value=[event]):
        game._handle_events()
    
    # Verify toggle() was NOT called
    game.inventory_ui.toggle.assert_not_called()
