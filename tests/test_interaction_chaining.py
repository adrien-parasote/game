import pygame
import pytest
from unittest.mock import patch, MagicMock
from src.entities.interactive import InteractiveEntity
from src.engine.game import Game

@pytest.fixture
def test_game():
    pygame.init()
    pygame.display.set_mode((1, 1), pygame.HIDDEN)

    def make_mock_sheet(filename):
        m = MagicMock()
        m.valid = True
        mock_surface = pygame.Surface((128, 192))
        m.sheet = mock_surface
        m.last_cols = 4
        m.load_grid_by_size.side_effect = lambda w, h: [pygame.Surface((w, h)) for _ in range(16)]
        return m

    with patch('src.graphics.spritesheet.SpriteSheet', side_effect=make_mock_sheet):
        game = Game()
        # Clean entities for isolated testing
        game.interactives.empty()
        game.visible_sprites.empty()
        game.obstacles_group.empty()
        yield game

    pygame.quit()

def test_interaction_chaining_lever_to_door(test_game):
    """TC-001 & IT-001: Lever toggles another entity (Door) via target_id."""
    # 1. Create Door (Target)
    door = InteractiveEntity(
        pos=(100, 100),
        groups=[test_game.visible_sprites, test_game.interactives],
        sub_type='door',
        sprite_sheet='door.png',
        element_id='door_main',
        target_id=None,
        is_on=False,
        is_animated=True,
        position=3 # facing down
    )
    
    # 2. Create Lever (Trigger)
    lever = InteractiveEntity(
        pos=(50, 50),
        groups=[test_game.visible_sprites, test_game.interactives],
        sub_type='lever',
        sprite_sheet='lever.png',
        element_id='lever_1',
        target_id='door_main', # Targets the door!
        is_on=False,
        is_animated=True,
        position=3 # facing down
    )

    # Place player ABOVE the lever, facing down, because lever position=3 means 'down'
    test_game.player.pos = pygame.math.Vector2(lever.pos.x, lever.pos.y - 20)
    test_game.player.current_state = 'down'

    # Initial state assertions
    assert door.is_on is False
    assert lever.is_on is False

    # Simulate 'E' key press to interact with Lever
    class MockKeys(dict):
        def __getitem__(self, key):
            from src.config import Settings
            if key == Settings.INTERACT_KEY:
                return True
            return self.get(key, False)
            
    keys = MockKeys()
    
    with patch('pygame.key.get_pressed', return_value=keys):
        test_game._handle_interactions()
        
    # Lever should be toggled
    assert lever.is_on is True
    # Door should be toggled by the engine chaining mechanism
    assert door.is_on is True
