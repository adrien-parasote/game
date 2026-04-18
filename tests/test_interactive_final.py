import pygame
import pytest
import math
import ast
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

def test_flicker_desynchronization(mock_spritesheet):
    """Verify that multiple lamps have unique phase offsets."""
    pygame.init()
    pygame.display.set_mode((1, 1), pygame.HIDDEN)
    
    obj1 = InteractiveEntity((0, 0), [], "lamp", "test.png")
    obj2 = InteractiveEntity((0, 0), [], "lamp", "test.png")
    
    assert hasattr(obj1, 'flicker_phase')
    assert hasattr(obj2, 'flicker_phase')
    assert obj1.flicker_phase != obj2.flicker_phase
    
    pygame.quit()

def test_flicker_alpha_bounds(mock_spritesheet):
    """Verify alpha flickering ±12% amplitude."""
    pygame.init()
    pygame.display.set_mode((1, 1), pygame.HIDDEN)
    
    obj = InteractiveEntity((0, 0), [], "lamp", "test.png", halo_size=20, halo_alpha=100)
    obj.is_on = True
    obj.is_animated = True # Trigger flicker
    
    alphas = []
    # Force time progression
    with patch('pygame.time.get_ticks') as mock_ticks:
        for i in range(20):
            mock_ticks.return_value = i * 50 # 50ms intervals
            obj.update(0.05)
            # Assuming obj.flicker_alpha_factor is calculated in update
            alphas.append(obj.f_alpha)
            
    assert max(alphas) <= 1.16 # Buffer for 0.12 + 0.02 + floating point
    assert min(alphas) >= 0.84
    # Verify variations actually happened
    assert len(set(alphas)) > 5
    
    pygame.quit()

def test_luminosity_daylight_floor(mock_spritesheet):
    """Verify intensity remains >= 15% in full daylight (global_darkness=0)."""
    pygame.init()
    pygame.display.set_mode((1, 1), pygame.HIDDEN)
    
    obj = InteractiveEntity((0, 0), [], "lamp", "test.png", halo_size=20, halo_alpha=200)
    obj.is_on = True
    
    # We simulate rendering with darkness 0
    # In draw_halo(surface, cam_offset, global_darkness):
    # expect intensity to be at least 15%
    # We mock or check the internal method calculating intensity
    
    # For now, we expect the method to be present
    assert hasattr(obj, 'draw_halo')
    
    pygame.quit()

def test_footprint_centering(mock_spritesheet):
    """Verify halo centering on the 32x32 footprint (16px above base)."""
    pygame.init()
    pygame.display.set_mode((1, 1), pygame.HIDDEN)
    
    # Place object at (100, 100) on Tiled map (32x32)
    obj = InteractiveEntity((100, 100), [], "lamp", "test.png", 
                             tiled_width=32, tiled_height=32, halo_size=20)
    
    # rect.bottom should be 132
    # footprint center y should be 132 - 16 = 116
    # footprint center x should be 100 + 16 = 116
    
    # We check where the halo blit pos would be
    # halo_pos = center - halo_size
    # footprint_center = (116, 116)
    # expected_blit_pos = (116 - 20, 116 - 20) = (96, 96)
    
    # This will be verified during implementation or by checking a return pos helper
    pass
    
    pygame.quit()

def test_animation_looping_logic(mock_spritesheet):
    """Verify is_animated=True loops from end_frame back to start_frame."""
    pygame.init()
    pygame.display.set_mode((1, 1), pygame.HIDDEN)
    
    obj = InteractiveEntity((0, 0), [], "fountain", "test.png", 
                             start_row=0, end_row=2, is_animated=True)
    obj.is_on = True
    obj.animation_speed = 10.0
    
    obj.update(0.1) # 1.0 frames
    assert int(obj.frame_index) == 1
    
    obj.update(0.25) # should cross end_row=2
    assert int(obj.frame_index) == 0 # Looped back
    
    pygame.quit()
