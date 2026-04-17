import pygame
import pytest
from unittest.mock import patch, MagicMock
from src.entities.player import Player
from src.entities.interactive import InteractiveEntity
from src.engine.game import Game
from src.config import Settings

@pytest.fixture
def test_game():
    pygame.init()
    pygame.display.set_mode((1, 1), pygame.HIDDEN)
    
    # Mock spritesheet loading to avoid needing real assets
    with patch('src.graphics.spritesheet.SpriteSheet.load_grid', return_value=[pygame.Surface((32, 32)) for _ in range(16)]):
        with patch('src.graphics.spritesheet.SpriteSheet.__init__', return_value=None):
            game = Game()
            yield game
            
    pygame.quit()

def test_interactive_proximity_success(test_game):
    """TC-I-01: Proximity < 45px should succeed."""
    obj = InteractiveEntity((100, 100), [], "chest", "chest.png", direction="up")
    test_game.interactives.add(obj)
    
    # Player is at distance 40px south (100, 140)
    test_game.player.pos = pygame.math.Vector2(100, 140)
    test_game.player.current_state = 'up'
    test_game.player.is_moving = False
    
    # Need to bypass interaction cooldown
    test_game._interaction_cooldown = 0
    
    class MockKeys(dict):
        def __getitem__(self, key):
            return self.get(key, False)
            
    keys = MockKeys({Settings.INTERACT_KEY: True})
    
    with patch('pygame.key.get_pressed', return_value=keys):
        test_game._handle_interactions()
    
    assert obj.is_animating is True

def test_interactive_proximity_failure(test_game):
    """TC-I-02: Proximity > 45px should fail."""
    obj = InteractiveEntity((100, 100), [], "chest", "chest.png", direction="up")
    test_game.interactives.add(obj)
    
    # Player is at distance 50px south (100, 150)
    test_game.player.pos = pygame.math.Vector2(100, 150)
    test_game.player.current_state = 'up'
    test_game.player.is_moving = False
    test_game._interaction_cooldown = 0
    
    class MockKeys(dict):
        def __getitem__(self, key):
            return self.get(key, False)
    
    keys = MockKeys({Settings.INTERACT_KEY: True})
    
    with patch('pygame.key.get_pressed', return_value=keys):
        test_game._handle_interactions()
    
    assert obj.is_animating is False

def test_interactive_orientation_opposite_success(test_game):
    """TC-I-03: Correct orientation (Opposite Rule) should succeed."""
    # Chest facing UP (opening from south)
    obj = InteractiveEntity((100, 100), [], "chest", "chest.png", direction="up")
    test_game.interactives.add(obj)
    
    # Player at South (100, 130), facing UP
    test_game.player.pos = pygame.math.Vector2(100, 130)
    test_game.player.current_state = 'up'
    test_game.player.is_moving = False
    test_game._interaction_cooldown = 0
    
    class MockKeys(dict):
        def __getitem__(self, key):
            return self.get(key, False)
    
    keys = MockKeys({Settings.INTERACT_KEY: True})
    
    with patch('pygame.key.get_pressed', return_value=keys):
        test_game._handle_interactions()
    
    assert obj.is_animating is True

def test_interactive_orientation_opposite_failure(test_game):
    """TC-I-04: Incorrect orientation (at North while chest faces UP) should fail."""
    # Chest facing UP
    obj = InteractiveEntity((100, 100), [], "chest", "chest.png", direction="up")
    test_game.interactives.add(obj)
    
    # Player at North (100, 70), facing UP (looking away)
    test_game.player.pos = pygame.math.Vector2(100, 70)
    test_game.player.current_state = 'up'
    test_game.player.is_moving = False
    test_game._interaction_cooldown = 0
    
    class MockKeys(dict):
        def __getitem__(self, key):
            return self.get(key, False)
    
    keys = MockKeys({Settings.INTERACT_KEY: True})
    
    with patch('pygame.key.get_pressed', return_value=keys):
        test_game._handle_interactions()
    
    assert obj.is_animating is False

def test_interactive_animation_trigger(test_game):
    """TC-I-05: Triggering interaction starts animation on correct column."""
    obj = InteractiveEntity((100, 100), [], "chest", "chest.png", direction="right")
    # Column 1 for 'right' according to new DIRECTION_MAP
    assert obj.col_index == 1 
    
    obj.interact(test_game.player)
    assert obj.is_animating is True

def test_spawning_from_properties(test_game):
    """Verify that an object with type in properties is correctly spawned."""
    entities_data = [
        {
            "x": 480,
            "y": 96,
            "type": "",
            "properties": {
                "type": "interactive_object",
                "sub_type": "chest",
                "sprite_sheet": "chest.png",
                "direction": "up"
            }
        }
    ]
    
    # We need to manually call _spawn_entities
    # Reset group first
    test_game.interactives.empty()
    test_game._spawn_entities(entities_data)
    
    assert len(test_game.interactives) == 1
    obj = test_game.interactives.sprites()[0]
    assert obj.sub_type == "chest"
