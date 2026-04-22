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
    
    # Mock spritesheet to avoid needing real assets
    def make_mock_sheet(filename):
        m = MagicMock()
        m.valid = True
        mock_surface = MagicMock()
        mock_surface.get_size.return_value = (128, 192)
        m.sheet = mock_surface
        m.last_cols = 4
        m.load_grid_by_size.side_effect = lambda w, h, **kwargs: [pygame.Surface((w, h)) for _ in range(16)]
        return m
    
    # Minimal map data to satisfy Game initialization
    fake_map = {
        "width": 10, "height": 10,
        "layers": {"grounds": [[0]*10]*10},
        "tiles": {},
        "entities": [],
        "spawn_player": {"x": 16, "y": 16}
    }
    
    with patch('src.graphics.spritesheet.SpriteSheet', side_effect=make_mock_sheet), \
         patch('src.entities.interactive.SpriteSheet', side_effect=make_mock_sheet), \
         patch('src.map.tmj_parser.TmjParser.load_map', return_value=fake_map), \
         patch('src.engine.game.os.path.exists', return_value=True):
        game = Game()
        yield game
        
    pygame.quit()

def test_interactive_proximity_success(test_game):
    """TC-I-01: Proximity < 80px should succeed."""
    test_game.interactives.empty()
    obj = InteractiveEntity((100, 100), [], "chest", "chest.png", position=0)
    test_game.interactives.add(obj)
    
    # Player is at distance 40px south 
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
    """TC-I-02: Proximity > 80px should fail."""
    test_game.interactives.empty()
    obj = InteractiveEntity((100, 100), [], "chest", "chest.png", position=0)
    test_game.interactives.add(obj)
    
    # Player is at distance > 80px south.
    # obj.pos footprint is about (116, 116). Player needs to be > 80px away.
    test_game.player.pos = pygame.math.Vector2(116, 200)  # 84px away
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
    test_game.interactives.empty()
    # Chest facing UP (opening from south)
    obj = InteractiveEntity((100, 100), [], "chest", "chest.png", position=0, is_passable=False)
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
    test_game.interactives.empty()
    # Chest facing UP
    obj = InteractiveEntity((100, 100), [], "chest", "chest.png", position=0, is_passable=False)
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

def test_chest_remains_solid_when_open(test_game):
    """Verify that a chest (is_passable=False) stays in obstacles even when open."""
    obstacles = pygame.sprite.Group()
    obj = InteractiveEntity((100, 100), [], "chest", "chest.png", 
                            obstacles_group=obstacles, is_passable=False)
    
    assert obj in obstacles
    
    obj.interact(None)
    obj.update(1.0)
    
    assert obj.is_on is True
    # Non-passable non-door object stays in obstacles
    assert obj in obstacles

def test_explicitly_passable_object(test_game):
    """Verify that a non-door object marked passable is NOT added to obstacles."""
    obstacles = pygame.sprite.Group()
    obj = InteractiveEntity((100, 100), [], "sign", "sign.png", 
                            obstacles_group=obstacles, is_passable=True)
    
    assert obj not in obstacles

def test_interactive_animation_trigger(test_game):
    """TC-I-05: Triggering interaction starts animation on correct column."""
    test_game.interactives.empty()
    obj = InteractiveEntity((100, 100), [], "chest", "chest.png", position=1, is_passable=False)
    # Column 1 directly from position
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
                "entity_type": "interactive",
                "sub_type": "chest",
                "sprite_sheet": "chest.png",
                "position": 0
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

def test_door_dynamic_collision(test_game):
    """Verify that a door (is_passable=True) blocks when closed, allows when open."""
    test_game.obstacles_group.empty()
    # Door with is_passable=True: blocks when closed, traversable when opened
    door = InteractiveEntity((100, 100), [test_game.interactives], "door", "door.png", 
                             position=0, obstacles_group=test_game.obstacles_group, is_passable=True)
    
    # Initially closed -> always in obstacles regardless of passable
    assert door in test_game.obstacles_group
    assert test_game._is_collidable(116, 116) is True
    
    # Open the door
    door.interact(test_game.player)
    door.update(1.0)  # 10.0 * 1.0 = 10, reaches end_frame
    
    assert door.is_on is True
    # is_passable=True -> removed from obstacles when open
    assert door not in test_game.obstacles_group
    assert test_game._is_collidable(116, 116) is False

def test_door_not_passable_stays_solid_when_open(test_game):
    """Verify that a door (is_passable=False) blocks even when open."""
    test_game.obstacles_group.empty()
    # Door with passable=False: always solid, never lets player through
    door = InteractiveEntity((100, 100), [test_game.interactives], "door", "door.png", 
                             position=0, obstacles_group=test_game.obstacles_group, is_passable=False)
    
    assert door in test_game.obstacles_group
    
    # Open the door
    door.interact(test_game.player)
    door.update(1.0)
    
    assert door.is_on is True
    # is_passable=False -> stays in obstacles even when open
    assert door in test_game.obstacles_group

def test_variable_size_alignment(test_game):
    """Verify that a large sprite (64x62) aligns bottom on a Tiled rectangle (64x32)."""
    # Tiled rect at (100, 100) size (64, 32)
    # Sprite size is (64, 62) - matches actual 00-doors.png frames
    # The rect.bottom should be at 100 + 32 = 132
    # The rect.midbottom.x should be at 100 + 32 = 132
    # The rect.top should be at 132 - 62 = 70
    obj = InteractiveEntity((100, 100), [], "door", "door.png", 
                            width=64, height=62, 
                            tiled_width=64, tiled_height=32,
                            is_passable=False)
    
    assert obj.rect.bottom == 132
    assert obj.rect.centerx == 132
    assert obj.rect.top == 70

def test_door_interaction_from_above_when_open(test_game):
    """Verify that an open door can be closed from the 'other' side (North)."""
    # Door at (100, 100), facing 'up' (expects south interaction usually)
    door = InteractiveEntity((100, 100), [test_game.interactives], "door", "door.png", position=0)
    
    # 1. Open it first from South
    door.is_on = True
    door.is_animating = False
    
    # 2. Player is at North of the door (116, 80), facing DOWN
    # Door footprint center is (116, 116)
    test_game.player.pos = pygame.math.Vector2(116, 80)
    test_game.player.current_state = 'down'
    test_game._interaction_cooldown = 0
    
    class MockKeys(dict):
        def __getitem__(self, key): return self.get(key, False)
    keys = MockKeys({Settings.INTERACT_KEY: True})
    
    with patch('pygame.key.get_pressed', return_value=keys):
        test_game._handle_interactions()
        
    # Door should start animating to close
    assert door.is_animating is True
    assert door.is_closing is True

def test_interactive_animation_closing_loop(test_game):
    # Test the closing logic and collision re-enabling
    obstacles = pygame.sprite.Group()
    door = InteractiveEntity((100, 100), [], "door", "door.png", 
                             obstacles_group=obstacles)
    
    # Force open state
    door.is_on = True
    door.is_animating = False
    door.frame_index = 3.0
    
    # Trigger close
    door.interact(None)
    assert door.is_closing is True
    
    # Update to finish closing (animation speed 10)
    door.update(0.5) 
    
    assert door.is_on is False
    assert door.is_animating is False
    assert door in obstacles

def test_interactive_get_frame_fallback(test_game):
    # Test _get_frame with index out of bounds
    obj = InteractiveEntity((100, 100), [], "chest", "chest.png")
    # Force frames empty for testing fallback
    obj.frames = []
    # Should return a 32x32 surface
    surf = obj._get_frame(0)
    assert surf.get_size() == (32, 32)

def test_particle_spawn_cycle(test_game):
    """TC-U-06: Particle list is populated when particles=True and is_on=True, bounded by particle_count."""
    obj = InteractiveEntity((100, 100), [], "torch", "torch.png", 
                            particles=True, particle_count=10, is_on=True)
    
    assert hasattr(obj, 'particles_list')
    assert len(obj.particles_list) == 0
    
    # Update to trigger spawn over a few frames
    for _ in range(50):
        obj.update(0.1)
        
    assert len(obj.particles_list) > 0
    assert len(obj.particles_list) <= 10
    
    # Verify spawn bounds (Top 33% and centripetal X)
    for p in obj.particles_list:
        # Give a small margin for particle movement during the 50 frames
        assert p['y'] <= obj.rect.top + obj.rect.height * 0.5, f"Particle spawned too low: {p['y']} (rect bottom: {obj.rect.bottom})"
        assert obj.rect.centerx - 10 <= p['x'] <= obj.rect.centerx + 10, f"Particle spawned too far horizontally: {p['x']}"

def test_particle_cleanup(test_game):
    """TC-U-07: Particles with expired life are removed from the list."""
    obj = InteractiveEntity((100, 100), [], "torch", "torch.png", 
                            particles=True, particle_count=10, is_on=True)
    
    # Inject a dead particle manually
    obj.particles_list = [{
        'x': 100, 'y': 100, 'vx': 0, 'vy': -1,
        'life': -0.1, 'max_life': 1.0, 'size': 2.0
    }]
    
    # Turn off object so no new particles spawn during update
    obj.is_on = False
    
    obj.update(0.1)
    
    assert len(obj.particles_list) == 0
