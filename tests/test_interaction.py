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

def test_handle_interaction_pickup():
    game = MagicMock()
    im = InteractionManager(game)
    im._interaction_cooldown = 0
    
    # Mock player
    game.player.pos = pygame.math.Vector2(100, 100)
    game.player.current_state = 'down'
    game.player.is_moving = False
    game.player.inventory.add_item.return_value = 0 
    
    # Mock keyboard
    with patch('pygame.key.get_pressed', return_value={Settings.INTERACT_KEY: True}):
        # Mock pickup item (very close)
        pickup = MagicMock()
        pickup.pos = pygame.math.Vector2(100, 105)
        pickup.item_id = "potion_red"
        pickup.quantity = 1
        game.pickups = [pickup]
        
        im.handle_interactions()
        assert game.player.inventory.add_item.called
        assert pickup.kill.called

def test_handle_interaction_npc():
    game = MagicMock()
    im = InteractionManager(game)
    im._interaction_cooldown = 0
    
    # Mock player
    game.player.pos = pygame.math.Vector2(100, 100)
    game.player.current_state = 'down'
    game.player.is_moving = False
    
    # Mock keyboard
    with patch('pygame.key.get_pressed', return_value={Settings.INTERACT_KEY: True}):
        # Mock NPC (exactly in front: 100, 132)
        npc = MagicMock()
        npc.pos = pygame.math.Vector2(100, 132)
        npc.rect = pygame.Rect(100-16, 132-16, 32, 32)
        npc.element_id = "npc_1"
        
        def mock_interact(initiator):
            npc.state = "interact"
            return "hello"
        npc.interact.side_effect = mock_interact
        
        game.npcs = [npc]
        
        im.handle_interactions()
        assert game._trigger_dialogue.called
        assert npc.state == "interact"

def test_handle_interaction_pickup_partial():
    game = MagicMock()
    im = InteractionManager(game)
    im._interaction_cooldown = 0
    
    game.player.pos = pygame.math.Vector2(100, 100)
    game.player.current_state = 'down'
    game.player.is_moving = False
    
    # Inventory is full except for 2 items
    game.player.inventory.add_item.return_value = 3 
    
    with patch('pygame.key.get_pressed', return_value={Settings.INTERACT_KEY: True}):
        pickup = MagicMock()
        pickup.pos = pygame.math.Vector2(100, 105)
        pickup.item_id = "potion_red"
        pickup.quantity = 5
        game.pickups = [pickup]
        
        im.handle_interactions()
        assert game.player.inventory.add_item.called
        assert pickup.quantity == 3
        assert not pickup.kill.called
        assert game.player.playerEmote.called # Should emit frustration

def test_handle_interaction_object():
    game = MagicMock()
    im = InteractionManager(game)
    im._interaction_cooldown = 0
    
    game.player.pos = pygame.math.Vector2(100, 100)
    game.player.current_state = 'up'
    game.player.is_moving = False
    
    with patch('pygame.key.get_pressed', return_value={Settings.INTERACT_KEY: True}):
        obj = MagicMock()
        obj.pos = pygame.math.Vector2(100, 80)
        obj.direction_str = 'down'
        obj.sub_type = 'switch'
        obj.element_id = 'switch_1'
        obj.target_id = 'door_1'
        obj.sfx = 'click'
        obj._world_state_key = 'switch_1_key'
        obj.is_on = True
        obj.interact.return_value = None # Doesn't trigger dialogue
        
        game.interactives = [obj]
        
        im.handle_interactions()
        assert obj.interact.called
        game.audio_manager.play_sfx.assert_called_with('click', 'switch_1')
        game.world_state.set.assert_called_with('switch_1_key', {'is_on': True})
        game.toggle_entity_by_id.assert_called_with('door_1', depth=1)

def test_get_player_facing_vector():
    im = InteractionManager(MagicMock())
    im.game.player.current_state = 'up'
    assert im._get_player_facing_vector() == pygame.math.Vector2(0, -1)
    im.game.player.current_state = 'down'
    assert im._get_player_facing_vector() == pygame.math.Vector2(0, 1)
    im.game.player.current_state = 'left'
    assert im._get_player_facing_vector() == pygame.math.Vector2(-1, 0)
    im.game.player.current_state = 'right'
    assert im._get_player_facing_vector() == pygame.math.Vector2(1, 0)

def test_facing_toward():
    im = InteractionManager(MagicMock())
    p_pos = pygame.math.Vector2(100, 100)
    
    # Target is to the right
    assert im._facing_toward(p_pos, 'right', pygame.math.Vector2(150, 100)) is True
    assert im._facing_toward(p_pos, 'left', pygame.math.Vector2(150, 100)) is False
    
    # Target is below
    assert im._facing_toward(p_pos, 'down', pygame.math.Vector2(100, 150)) is True
    assert im._facing_toward(p_pos, 'up', pygame.math.Vector2(100, 150)) is False

def test_verify_orientation_door_relaxed():
    im = InteractionManager(MagicMock())
    door = MagicMock()
    door.pos = pygame.math.Vector2(100, 100)
    door.sub_type = 'door'
    door.direction_str = 'down'
    door.is_on = True # Door is open
    
    p_pos = pygame.math.Vector2(100, 80) # Player is ABOVE the door
    
    # Normally a down-facing object must be approached from BELOW (y > 100), facing UP
    # But because it is an OPEN door, it can be approached from ABOVE, facing DOWN
    assert im._verify_orientation(door, 'down', p_pos) is True
