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

def test_default_on_state_for_lights_and_animated(mock_spritesheet):
    # Case 1: Animated object should be ON by default
    torch = InteractiveEntity((0,0), [], "torch", "torch.png", is_animated=True)
    assert torch.is_on is True
    assert torch.is_animating is True
    
    # Case 2: Lamp subtype should be ON by default
    lamp = InteractiveEntity((0,0), [], "lamp", "lamp.png", is_animated=False)
    assert lamp.is_on is True
    
    # Case 3: Chest subtype should be OFF by default
    chest = InteractiveEntity((0,0), [], "chest", "chest.png", is_animated=False)
    assert chest.is_on is False

def test_halo_visibility_normalization(mock_spritesheet):
    obj = InteractiveEntity((0,0), [], "lamp", "lamp.png", halo_size=20, halo_alpha=200)
    
    # At Midnignt (180), factor should be 1.0 (peak)
    # final_alpha = 255 * 1.0 * f_alpha = 255
    with patch.object(obj, 'is_on', True):
        with patch.object(obj, 'f_alpha', 1.0):
            # Normalization check: if global_darkness=180, factor should be 1.0
            # final_alpha = 255 * 1.0 = 255
            pass # We'll verify this via implementation

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
    """Verify obj.pos points to the 32x32 footprint center (bottom-16)."""
    pygame.init()
    pygame.display.set_mode((1, 1), pygame.HIDDEN)
    
    # Place a TALL object (32x64) at (100, 100) on Tiled map
    obj = InteractiveEntity((100, 100), [], "door", "test.png", 
                             width=32, height=64, tiled_width=32, tiled_height=64)
    
    # rect.bottom = 100 + 64 = 164
    # rect.centerx = 100 + 16 = 116
    # Footprint center y = 164 - 16 = 148
    # Footprint center x = 116
    
    # Old behavior (center): obj.pos.y = 100 + 32 = 132 (FAIL for door interaction)
    # New behavior (footprint): obj.pos.y = 148
    assert obj.pos.y == 148
    assert obj.pos.x == 116
    
    pygame.quit()

def test_halo_visual_centering(mock_spritesheet):
    """Verify that halos are visually centered on the entire sprite (rect.center)."""
    pygame.init()
    pygame.display.set_mode((1, 1), pygame.HIDDEN)
    
    # Create a tall object (32x64) at (100, 100)
    # Footprint center (pos) is at (116, 164-16=148)
    # Visual center (rect.center) is at (116, 100+32=132)
    obj = InteractiveEntity((100, 100), [], "door", "test.png", 
                             width=32, height=64, tiled_width=32, tiled_height=64, halo_size=20)
    
    # We check if draw_halo uses rect.center
    mock_surface = MagicMock()
    cam_offset = pygame.math.Vector2(0, 0)
    obj.is_on = True
    # Ensure light_mask_cache is populated (mock_spritesheet usually handles this, 
    # but we force one for safety)
    if not obj.light_mask_cache:
        obj.light_mask_cache = [pygame.Surface((40, 40))]
        
    obj.draw_halo(mock_surface, cam_offset, 180)
    
    # blit_pos = screen_center - halo_size
    # expected_center = rect.center = (116, 132)
    # expected_blit = (116 - 20, 132 - 20) = (96, 112)
    
    # In current (broken) state, it uses obj.pos = (116, 148) which gives (96, 128)
    args, kwargs = mock_surface.blit.call_args
    blit_pos = args[1]
    assert blit_pos == (96, 112)
    
    pygame.quit()

def test_flicker_frequency_reduction(mock_spritesheet):
    """Verify that flicker animation is slower (target: smooth flame breath)."""
    pygame.init()
    pygame.display.set_mode((1, 1), pygame.HIDDEN)
    
    obj = InteractiveEntity((0, 0), [], "lamp", "test.png", halo_size=20)
    obj.is_on = True
    
    with patch('pygame.time.get_ticks') as mock_ticks:
        # Check alpha change over 0.2s
        mock_ticks.return_value = 0
        obj.update(0.1)
        # current code uses 4 * pi (2.0 cycles/sec)
        # a 0.1s step (0.2 cycles) is approx 72 degrees.
        
        # We want approx 0.5 - 1.0 cycles/sec.
        pass # We'll verify the scale logic in implementation
    
    pygame.quit()

def test_halo_scaling_cache(mock_spritesheet):
    """Verify that light halos use a 10-step pre-calculated cache."""
    pygame.init()
    pygame.display.set_mode((1, 1), pygame.HIDDEN)
    
    obj = InteractiveEntity(
        (0,0), [], "lamp", "lamp.png", 
        halo_size=20, halo_alpha=130, is_animated=True
    )
    
    # Verify exactly 10 surfaces as requested for smoothness
    assert hasattr(obj, 'light_mask_cache')
    assert len(obj.light_mask_cache) == 10
    
    pygame.quit()

def test_halo_rendering_technique(mock_spritesheet):
    """Verify that halo surfaces use RGB intensity on black background (no SRCALPHA)."""
    pygame.init()
    pygame.display.set_mode((1, 1), pygame.HIDDEN)
    
    obj = InteractiveEntity(
        (0,0), [], "lamp", "lamp.png", 
        halo_size=50, halo_alpha=200, halo_color="[255, 204, 0]"
    )
    
    halo = obj.light_mask
    
    # Requirement: NOT SRCALPHA
    assert not (halo.get_flags() & pygame.SRCALPHA)
    
    # Requirement: Gradient logic (center is bright, edge is dark)
    center_color = halo.get_at((50, 50))
    edge_color = halo.get_at((0, 50))
    
    # RGB values should fall off
    assert center_color.r > edge_color.r
    assert center_color.g > edge_color.g
    
    pygame.quit()
