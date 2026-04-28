import pytest
import pygame
from unittest.mock import MagicMock, patch
from src.engine.interaction import InteractionManager
from src.config import Settings
from src.entities.player import Player

def test_interaction_cooldown():
    game = MagicMock()
    im = InteractionManager(game)
    im._interaction_cooldown = 0.5
    im.update(0.1)
    assert im._interaction_cooldown == pytest.approx(0.4)

def test_emote_interruption():
    """Verify that a second emote interrupts the first one."""
    game = MagicMock()
    game.player = MagicMock(spec=Player)
    game.emote_group = MagicMock()
    game.emote_group.__len__.return_value = 1 # One emote active
    
    im = InteractionManager(game)
    im._emote_cooldown = 0
    
    obj = MagicMock()
    obj.pos = pygame.math.Vector2(100, 110)
    obj.direction_str = 'up'
    obj.sub_type = 'chest'
    obj.is_on = False
    game.interactives = [obj]
    game.player.pos = pygame.math.Vector2(100, 100)
    game.player.current_state = 'down'
    
    im._check_proximity_emotes()
    assert game.player.playerEmote.called

def test_interaction_orientation():
    """Check orientation verification logic."""
    im = InteractionManager(MagicMock())
    obj = MagicMock()
    obj.pos = pygame.math.Vector2(100, 120)
    obj.direction_str = 'up'
    obj.sub_type = 'chest'
    
    # Player ABOVE object, facing down -> Correct
    assert im._verify_orientation(obj, 'down', pygame.math.Vector2(100, 100)) is True
    # Player BELOW object, facing up -> Wrong (chest front is at top)
    assert im._verify_orientation(obj, 'up', pygame.math.Vector2(100, 140)) is False
