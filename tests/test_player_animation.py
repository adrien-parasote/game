import pygame
import pytest
import os
from src.graphics.spritesheet import SpriteSheet
from src.entities.player import Player

# Need pygame display for surface creation in tests
@pytest.fixture(scope="module", autouse=True)
def setup_pygame():
    pygame.init()
    pygame.display.set_mode((1, 1), pygame.HIDDEN)
    yield
    pygame.quit()

def test_spritesheet_fallback():
    """TC-ANIM-04 part 1: Test fallback when image doesn't exist."""
    sheet = SpriteSheet("nonexistent.png")
    frames = sheet.load_grid(4, 4)
    assert len(frames) == 16
    assert isinstance(frames[0], pygame.Surface)
    assert frames[0].get_size() == (32, 32) # Default fallback size

def test_spritesheet_grid_extraction(tmp_path):
    """TC-ANIM-04 part 2: Test proper grid extraction."""
    # Create a dummy image
    test_img_path = tmp_path / "test_sheet.png"
    surf = pygame.Surface((100, 100))
    pygame.image.save(surf, str(test_img_path))
    
    sheet = SpriteSheet(str(test_img_path))
    frames = sheet.load_grid(4, 4)
    
    assert len(frames) == 16
    # 100 / 4 = 25
    assert frames[0].get_size() == (25, 25)

def test_player_animation_idle():
    """TC-ANIM-01: Idle state resets to first frame."""
    player = Player((0, 0))
    player.current_state = 'down'
    player.is_moving = False
    player._update_animation(0.15)
    
    # Needs to match the first frame (index 0)
    assert player.frame_index == 0.0

def test_player_animation_moving():
    """TC-ANIM-02: Moving state progresses animation."""
    player = Player((0, 0))
    player.current_state = 'down'
    player.is_moving = True
    player.frame_index = 0.0
    
    # Speed is 1/0.15 ~= 6.66 frames per sec. 
    # With dt=0.075 (half interval), we should be at 0.5
    player._update_animation(0.075)
    assert 0.4 < player.frame_index < 0.6
    
    # Walk another 0.075 = full frame advance
    player._update_animation(0.075)
    assert 0.9 < player.frame_index < 1.1

def test_player_animation_wrapping():
    """TC-ANIM-03: Frame index wraps properly."""
    player = Player((0, 0))
    player.current_state = 'up' # row 3 (offset 12)
    player.is_moving = True
    player.frame_index = 3.5
    
    # Add enough time to go over 4.0
    player._update_animation(0.15)
    
    # Should wrap back to something less than 1.0
    assert 0.0 <= player.frame_index < 1.0
