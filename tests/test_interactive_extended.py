import pygame
import pytest
import json
from unittest.mock import patch, MagicMock
from src.entities.interactive import InteractiveEntity

@pytest.fixture
def mock_spritesheet():
    def make_mock_sheet(filename):
        m = MagicMock()
        m.valid = True
        mock_surface = MagicMock()
        mock_surface.get_size.return_value = (128, 128)
        m.sheet = mock_surface
        m.last_cols = 4
        m.load_grid_by_size.side_effect = lambda w, h: [pygame.Surface((w, h)) for _ in range(16)]
        return m
    
    with patch('src.graphics.spritesheet.SpriteSheet', side_effect=make_mock_sheet):
        yield

def test_interactive_proximity_check(mock_spritesheet):
    """TC-I-01: Proximity check at 45px."""
    pygame.init()
    pygame.display.set_mode((1, 1), pygame.HIDDEN)
    
    obj = InteractiveEntity(
        pos=(100, 100), groups=[], sub_type="lamp", 
        sprite_sheet="test.png", tiled_width=32, tiled_height=32
    )
    
    # Mock player
    player = MagicMock()
    
    # Case 1: Within 45px (Close)
    player.pos = pygame.math.Vector2(100+16, 100+16+10) # 10px below footprint center
    assert player.pos.distance_to(obj.pos) < 45.0
    
    # Case 2: Outside 45px (Far)
    player.pos = pygame.math.Vector2(100, 100+100)
    assert player.pos.distance_to(obj.pos) > 45.0
    
    pygame.quit()

def test_interactive_animation_loop(mock_spritesheet):
    """TC-I-11: Verify is_animated loops continuously when ON."""
    pygame.init()
    pygame.display.set_mode((1, 1), pygame.HIDDEN)
    
    obj = InteractiveEntity(
        pos=(0, 0), groups=[], sub_type="lamp", 
        sprite_sheet="test.png", start_row=0, end_row=2,
        is_animated=True
    )
    obj.animation_speed = 10.0
    
    # Start interaction (Toggle ON)
    obj.interact(None)
    assert obj.is_on == True
    assert obj.is_animating == True
    
    # Update to reach end_row + 1
    # end_row=2, so it loops when >= 3.0
    obj.update(0.3) # 10 * 0.3 = 3.0 frames
    assert int(obj.frame_index) == 0 # Looped back
    
    # Toggle OFF
    obj.interact(None)
    assert obj.is_on == False
    obj.update(0.1)
    assert obj.is_animating == False
    assert obj.frame_index == 0.0 # Resets to start
    
    pygame.quit()

def test_interactive_linear_animation(mock_spritesheet):
    """Verify non-animated objects play once."""
    pygame.init()
    pygame.display.set_mode((1, 1), pygame.HIDDEN)
    
    obj = InteractiveEntity(
        pos=(0, 0), groups=[], sub_type="chest", 
        sprite_sheet="test.png", start_row=0, end_row=2,
        is_animated=False
    )
    obj.animation_speed = 10.0
    
    # Toggle ON
    obj.interact(None)
    assert obj.is_on == True
    
    # Update to end
    obj.update(0.2)
    assert obj.frame_index == 2.0
    obj.update(0.1)
    assert obj.frame_index == 2.0 # Stops at end_row
    assert obj.is_animating == False
    
    pygame.quit()

def test_interactive_halo_generation(mock_spritesheet):
    """TC-I-12: Verify halo surface generation and color parsing."""
    pygame.init()
    pygame.display.set_mode((1, 1), pygame.HIDDEN)
    
    obj = InteractiveEntity(
        pos=(0, 0), groups=[], sub_type="lamp", 
        sprite_sheet="test.png", halo_size=20, 
        halo_color="[255, 204, 0]", halo_alpha=130
    )
    
    assert obj.light_mask is not None
    assert obj.light_mask.get_size() == (40, 40)
    assert obj.halo_color == [255, 204, 0]
    
    # Check center alpha
    center_color = obj.light_mask.get_at((20, 20))
    assert center_color.a == 130
    
    # Check edge alpha (should be 0 or very close)
    edge_color = obj.light_mask.get_at((0, 20))
    assert edge_color.a == 0
    
    pygame.quit()

def test_interactive_collision_logic(mock_spritesheet):
    """Verify is_passable interaction with obstacles_group."""
    pygame.init()
    pygame.display.set_mode((1, 1), pygame.HIDDEN)
    
    obs_group = pygame.sprite.Group()
    
    # Case 1: Door (Passable=True) -> Solid at spawn, traversable when ON
    door = InteractiveEntity(
        pos=(0, 0), groups=[], sub_type="door", 
        sprite_sheet="test.png", obstacles_group=obs_group,
        is_passable=True
    )
    assert door in obs_group
    
    door.interact(None)
    door.update(1.0) # Finish opening
    assert door.is_on == True
    assert door not in obs_group
    
    # Case 2: Floor Decor (Passable=True) -> Never solid
    decor = InteractiveEntity(
        pos=(0, 0), groups=[], sub_type="decor", 
        sprite_sheet="test.png", obstacles_group=obs_group,
        is_passable=True
    )
    assert decor not in obs_group
    
    # Case 3: Chest (Passable=False) -> Always solid
    chest = InteractiveEntity(
        pos=(0, 0), groups=[], sub_type="chest", 
        sprite_sheet="test.png", obstacles_group=obs_group,
        is_passable=False
    )
    assert chest in obs_group
    chest.interact(None)
    chest.update(1.0)
    assert chest in obs_group # Still solid
    
    pygame.quit()
