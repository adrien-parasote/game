"""
Tests for InteractionManager logic.
"""
import pytest
import pygame
from unittest.mock import MagicMock, patch
from src.engine.interaction import InteractionManager
from src.config import Settings
from src.entities.player import Player
from src.entities.npc import NPC
from src.entities.interactive import InteractiveEntity

@pytest.fixture(scope="module", autouse=True)
def interaction_env():
    pygame.init()
    pygame.display.set_mode((1, 1), pygame.HIDDEN)
    Settings.load()
    yield
    pygame.quit()

@pytest.fixture
def mock_game():
    game = MagicMock()
    game.player = MagicMock(spec=Player)
    game.player.pos = pygame.math.Vector2(100, 100)
    game.player.current_state = 'down'
    game.player.is_moving = False
    game.npcs = pygame.sprite.Group()
    game.interactives = pygame.sprite.Group()
    return game

def test_interaction_cooldown(mock_game):
    """InteractionManager should respect cooldown timer."""
    im = InteractionManager(mock_game)
    im._interaction_cooldown = 0.5
    
    with patch('pygame.key.get_pressed', return_value={Settings.INTERACT_KEY: True}):
        im.handle_interactions()
        # Should not trigger anything because of cooldown
        mock_game._trigger_dialogue.assert_not_called()
    
    im.update(0.6)
    assert im._interaction_cooldown == 0

def test_npc_interaction_trigger(mock_game):
    """Interacting with NPC in front of player should trigger dialogue."""
    im = InteractionManager(mock_game)
    npc = MagicMock(spec=NPC)
    npc.rect = pygame.Rect(100, 132, 32, 32) # Directly below player
    npc.interact.return_value = "npc_msg"
    npc.name = "Test NPC"
    mock_game.npcs.add(npc)
    
    with patch('pygame.key.get_pressed', return_value={Settings.INTERACT_KEY: True}):
        im.handle_interactions()
        
    npc.interact.assert_called_once_with(mock_game.player)
    mock_game._trigger_dialogue.assert_called_once_with("npc_msg", title="Test NPC")

def test_object_interaction_facing(mock_game):
    """Interaction with object should require correct orientation."""
    im = InteractionManager(mock_game)
    obj = MagicMock(spec=InteractiveEntity)
    obj.pos = pygame.math.Vector2(100, 140) # Close to player
    obj.direction_str = 'down'
    obj.sub_type = 'chest'
    obj.interact.return_value = None
    mock_game.interactives.add(obj)
    
    # Player facing down, obj is down -> OK
    mock_game.player.current_state = 'down'
    with patch('pygame.key.get_pressed', return_value={Settings.INTERACT_KEY: True}):
        im.handle_interactions()
    assert obj.interact.call_count == 1
    
    # Player facing up, obj is down -> NO
    obj.interact.reset_mock()
    mock_game.player.current_state = 'up'
    im._interaction_cooldown = 0 # reset cooldown
    with patch('pygame.key.get_pressed', return_value={Settings.INTERACT_KEY: True}):
        im.handle_interactions()
    assert obj.interact.call_count == 0

def test_door_relaxation_logic(mock_game):
    """Open doors can be closed from the 'wrong' side."""
    im = InteractionManager(mock_game)
    door = MagicMock(spec=InteractiveEntity)
    door.pos = pygame.math.Vector2(100, 80) # Above player
    door.direction_str = 'up'
    door.sub_type = 'door'
    door.is_on = True # Door is open
    mock_game.interactives.add(door)
    
    # Player is below door, facing DOWN (wrong side but it's open) -> OK
    mock_game.player.current_state = 'down'
    mock_game.player.pos = pygame.math.Vector2(100, 100)
    
    with patch('pygame.key.get_pressed', return_value={Settings.INTERACT_KEY: True}):
        im.handle_interactions()
        
    assert door.interact.call_count == 1
