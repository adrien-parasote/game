import pytest
import pygame
from unittest.mock import MagicMock, patch
from src.engine.interaction import InteractionManager
from src.config import Settings

@pytest.fixture
def interaction_setup():
    game = MagicMock()
    im = InteractionManager(game)
    im._interaction_cooldown = 0
    
    # Mock player
    game.player.pos = pygame.math.Vector2(100, 100)
    game.player.current_state = 'down'
    game.player.is_moving = False
    game.player.inventory.add_item.return_value = 0 
    
    return game, im

def test_pickup_diagonal_rejection(interaction_setup):
    game, im = interaction_setup
    
    with patch('pygame.key.get_pressed', return_value={Settings.INTERACT_KEY: True}):
        # Mock pickup item at a diagonal position (e.g., 120, 120)
        # Distance = sqrt(20^2 + 20^2) = approx 28.28 (well within 48px range)
        pickup = MagicMock()
        pickup.pos = pygame.math.Vector2(120, 120)
        pickup.item_id = "potion_red"
        pickup.quantity = 1
        game.pickups = [pickup]
        
        # Player facing down
        game.player.current_state = 'down'
        
        im.handle_interactions()
        # Should NOT be picked up because it's diagonal (abs(dx)=20, abs(dy)=20)
        assert not game.player.inventory.add_item.called
        assert not pickup.kill.called

def test_pickup_orthogonal_acceptance(interaction_setup):
    game, im = interaction_setup
    
    with patch('pygame.key.get_pressed', return_value={Settings.INTERACT_KEY: True}):
        # Mock pickup item at an orthogonal position (100, 120)
        pickup = MagicMock()
        pickup.pos = pygame.math.Vector2(100, 120)
        pickup.item_id = "potion_red"
        pickup.quantity = 1
        game.pickups = [pickup]
        
        # Player facing down
        game.player.current_state = 'down'
        
        im.handle_interactions()
        # Should be picked up because it's orthogonal (dx=0, dy=20) and facing down
        assert game.player.inventory.add_item.called
        assert pickup.kill.called

def test_anywhere_object_diagonal_rejection(interaction_setup):
    game, im = interaction_setup
    
    with patch('pygame.key.get_pressed', return_value={Settings.INTERACT_KEY: True}):
        # Mock interactive object with activate_from_anywhere=True
        obj = MagicMock()
        obj.pos = pygame.math.Vector2(120, 120) # Diagonal
        obj.activate_from_anywhere = True
        obj.is_on = False
        game.interactives = [obj]
        
        # Player facing down
        game.player.current_state = 'down'
        
        im.handle_interactions()
        # Should NOT be activated because it's diagonal
        assert not obj.interact.called

def test_anywhere_object_orthogonal_acceptance(interaction_setup):
    game, im = interaction_setup
    
    with patch('pygame.key.get_pressed', return_value={Settings.INTERACT_KEY: True}):
        # Mock interactive object with activate_from_anywhere=True
        obj = MagicMock()
        obj.pos = pygame.math.Vector2(100, 120) # Orthogonal
        obj.activate_from_anywhere = True
        obj.is_on = False
        game.interactives = [obj]
        
        # Player facing down
        game.player.current_state = 'down'
        
        im.handle_interactions()
        # Should be activated
        assert obj.interact.called

def test_pickup_proximity_emote_diagonal_rejection(interaction_setup):
    game, im = interaction_setup
    
    # Mock pickup item at a diagonal position
    pickup = MagicMock()
    pickup.pos = pygame.math.Vector2(120, 120)
    game.pickups = [pickup]
    
    # Player facing down
    game.player.pos = pygame.math.Vector2(100, 100)
    game.player.current_state = 'down'
    
    im._check_proximity_emotes()
    # Should NOT trigger emote because it's diagonal
    assert not game.player.playerEmote.called

def test_pickup_proximity_emote_orthogonal_acceptance(interaction_setup):
    game, im = interaction_setup
    
    # Mock pickup item at an orthogonal position
    pickup = MagicMock()
    pickup.pos = pygame.math.Vector2(100, 120)
    game.pickups = [pickup]
    
    # Player facing down
    game.player.pos = pygame.math.Vector2(100, 100)
    game.player.current_state = 'down'
    
    im._check_proximity_emotes()
    # Should trigger emote
    assert game.player.playerEmote.called

def test_pickup_on_top_acceptance(interaction_setup):
    game, im = interaction_setup
    
    with patch('pygame.key.get_pressed', return_value={Settings.INTERACT_KEY: True}):
        # Mock pickup item at the exact same position
        pickup = MagicMock()
        pickup.pos = pygame.math.Vector2(100, 100)
        pickup.item_id = "potion_red"
        pickup.quantity = 1
        game.pickups = [pickup]
        
        # Player facing up (away from default 'down' if we were below it, but here we are ON it)
        game.player.current_state = 'up'
        
        im.handle_interactions()
        # Should be picked up because we are ON it (dist < 16)
        assert game.player.inventory.add_item.called
        assert pickup.kill.called

def test_passable_object_on_top_acceptance(interaction_setup):
    game, im = interaction_setup
    
    with patch('pygame.key.get_pressed', return_value={Settings.INTERACT_KEY: True}):
        # Mock passable interactive object
        obj = MagicMock()
        obj.pos = pygame.math.Vector2(100, 100)
        obj.is_passable = True
        obj.is_on = False
        game.interactives = [obj]
        
        # Player facing away
        game.player.current_state = 'up'
        
        im.handle_interactions()
        # Should be activated
        assert obj.interact.called
