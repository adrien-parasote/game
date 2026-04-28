import pytest
import pygame
from unittest.mock import MagicMock, patch
from src.engine.interaction import InteractionManager
from src.config import Settings

@pytest.fixture
def mock_game():
    game = MagicMock()
    game.player.pos = pygame.math.Vector2(100, 100)
    game.player.current_state = 'down'
    game.player.is_moving = False
    game.npcs = pygame.sprite.Group()
    game.interactives = pygame.sprite.Group()
    game.pickups = pygame.sprite.Group()
    game.emote_group = pygame.sprite.Group()
    return game

def test_interaction_manager_failed_emote(mock_game):
    im = InteractionManager(mock_game)
    # Mock no interactions found
    im._check_npc_interactions = MagicMock(return_value=False)
    im._check_object_interactions = MagicMock(return_value=False)
    im._check_pickup_interactions = MagicMock(return_value=False)
    
    with patch('pygame.key.get_pressed', return_value={Settings.INTERACT_KEY: True}):
        Settings.ENABLE_FAILED_INTERACTION_EMOTE = True
        im.handle_interactions()
        assert mock_game.player.playerEmote.called

def test_interaction_manager_npc_interaction(mock_game):
    im = InteractionManager(mock_game)
    npc = MagicMock()
    # Set rect explicitly to ensure collision
    # Player at (100, 100) facing down (0, 1) -> check at (100, 132)
    npc.rect = pygame.Rect(90, 120, 32, 32) 
    mock_game.npcs = [npc] # Use list if it's iterated or Group
    
    with patch('pygame.key.get_pressed', return_value={Settings.INTERACT_KEY: True}):
        im.handle_interactions()
        assert npc.interact.called

def test_interaction_manager_proximity_emotes(mock_game):
    im = InteractionManager(mock_game)
    obj = MagicMock()
    obj.pos = pygame.math.Vector2(100, 110) # Directly below player
    obj.direction_str = 'up' # Front is up
    obj.sub_type = 'chest'
    obj.is_on = False
    mock_game.interactives = [obj]
    
    im.update(0.1)
    # Should trigger 'interact' emote
    assert mock_game.player.playerEmote.called
