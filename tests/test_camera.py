import pygame
import pytest
from src.entities.groups import CameraGroup

@pytest.fixture
def camera():
    pygame.init()
    pygame.display.set_mode((1280, 720), pygame.HIDDEN)
    return CameraGroup()

def test_camera_clamp_wide_map(camera):
    """TC-C-01: Large map. Clamping offset between 0 and -(world_w - screen_w)."""
    camera.set_world_size(2000, 2000) # ww=2000, wh=2000. sw=1280, sh=720.
    
    # Target at (0,0) -> Offset should be (0,0) because of clamping (can't go positive)
    # math: half_w - target.x = 640 - 0 = 640. Clamped to 0.
    class MockSprite:
        rect = pygame.Rect(0, 0, 32, 32)
        rect.center = (0, 0)
    
    offset = camera.calculate_offset(MockSprite())
    assert offset.x == 0
    assert offset.y == 0
    
    # Target at (2000, 2000) -> Offset should be -(2000-1280) = -720
    MockSprite.rect.center = (2000, 2000)
    offset = camera.calculate_offset(MockSprite())
    assert offset.x == -720
    assert offset.y == -(2000 - 720) # -1280

def test_camera_center_small_map(camera):
    """TC-C-02: Small map. Map centered on screen (sw - ww) // 2."""
    camera.set_world_size(800, 600) # ww=800, wh=600. sw=1280, sh=720.
    
    class MockSprite:
        rect = pygame.Rect(400, 300, 32, 32)
        rect.center = (400, 300)
        
    offset = camera.calculate_offset(MockSprite())
    # x_offset = (1280 - 800) // 2 = 480 // 2 = 240
    # y_offset = (720 - 600) // 2 = 120 // 2 = 60
    assert offset.x == 240
    assert offset.y == 60
