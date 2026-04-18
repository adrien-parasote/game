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
    
    # Initial state for 'lamp' with is_animated=True is ON
    assert obj.is_on == True
    assert obj.is_animating == True
    
    # Check looping behavior (end_row=2, so idx 3.0 loops)
    obj.update(0.301) 
    assert int(obj.frame_index) == 0 # Should have looped
    
    # Toggle OFF
    obj.interact(None)
    assert obj.is_on == False
    
    # Update to reset state
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
    
    # In the new RGB intensity model, alpha is Always 255 (non-SRCALPHA surface)
    # The halo effect is achieved by modulating RGB values on a black background
    center_color = obj.light_mask.get_at((20, 20))
    edge_color = obj.light_mask.get_at((0, 20))
    
    # Requirement: center is bright, edge is dark (black)
    assert center_color.r > 0
    assert edge_color.r == 0
    assert edge_color.g == 0
    assert edge_color.b == 0
    
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

def test_selective_animation_speed(mock_spritesheet):
    """TC-I-13: Verify chest is 10FPS, lamp is organic 1.5FPS, and animated_decor with halo is also 1.5FPS."""
    pygame.init()
    pygame.display.set_mode((1, 1), pygame.HIDDEN)
    
    chest = InteractiveEntity(
        (0, 0), [], "chest", "test.png"
    )
    assert chest.animation_speed == 10.0
    
    lamp = InteractiveEntity(
        (0, 0), [], "lamp", "test.png"
    )
    assert lamp.animation_speed == 1.5
    
    # Inclusive detection test: animated_decor with a halo should also be slow
    decor_light = InteractiveEntity(
        (0, 0), [], "animated_decor", "test.png", halo_size=80
    )
    assert decor_light.animation_speed == 1.5
    
    pygame.quit()

def test_light_desynchronization(mock_spritesheet):
    """TC-I-15: Verify that two animated light sources start at different frame indices (desync)."""
    pygame.init()
    pygame.display.set_mode((1, 1), pygame.HIDDEN)
    
    # Create two lamps with identical stats
    # We use a set to check for unique values over several iterations to account for random collisions
    frame_indices = set()
    for _ in range(20):
        lamp = InteractiveEntity(
            (0, 0), [], "lamp", "test.png", start_row=0, end_row=5, is_animated=True
        )
        frame_indices.add(lamp.frame_index)
    
    # With 20 samples and a range of [0, 6), we expect more than 1 unique value
    assert len(frame_indices) > 1
    
    pygame.quit()

def test_light_source_frame_sync(mock_spritesheet):
    """TC-I-14: Verify halo intensity modulation is tethered directly to the sprite frame."""
    pygame.init()
    pygame.display.set_mode((1, 1), pygame.HIDDEN)
    
    lamp = InteractiveEntity(
        (0, 0), [], "lamp", "test.png", halo_size=20, start_row=0, end_row=3, is_animated=True
    )
    lamp.is_on = True
    
    # We will freeze time and manually advance the frame_index to prove time independent logic
    with patch('pygame.time.get_ticks', return_value=0):
        lamp.frame_index = 0.0
        lamp.update(0.1) # DT doesn't matter for our static frame_index override
        alpha_start = lamp.f_alpha
        
        lamp.frame_index = 1.5 # Half-way through a 3-frame 
        lamp.update(0.1)
        alpha_mid = lamp.f_alpha
        
        # Alpha should meaningfully diverge due to frames, despite time being perfectly 0
        # If it doesn't, it implies it's still running on ticks
        assert abs(alpha_start - alpha_mid) > 0.05
    
    pygame.quit()

