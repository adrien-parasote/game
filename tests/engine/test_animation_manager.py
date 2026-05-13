import pygame
import pytest
from unittest.mock import MagicMock, patch

from src.map.animation import AnimationMapManager

@pytest.fixture
def map_manager_mock():
    mm = MagicMock()
    
    # Mock some animated tiles
    tile_data = MagicMock()
    tile_data.image = pygame.Surface((32, 32))
    tile_data.frames = [(101, 150), (102, 150)]
    
    frame1 = MagicMock()
    frame1.image = pygame.Surface((32, 32))
    frame1.image.fill((255, 0, 0)) # Red
    
    frame2 = MagicMock()
    frame2.image = pygame.Surface((32, 32))
    frame2.image.fill((0, 255, 0)) # Green
    
    mm.tiles = {
        100: tile_data,
        101: frame1,
        102: frame2,
    }
    
    return mm

@patch('pygame.time.get_ticks')
def test_animation_map_manager_frame_cycle(mock_get_ticks, map_manager_mock):
    """IT-003: Frame Cycle Accuracy"""
    anim_manager = AnimationMapManager(map_manager_mock)
    
    # Time 0: Should be first frame (101)
    mock_get_ticks.return_value = 0
    img = anim_manager.get_current_frame_image(100)
    assert img == map_manager_mock.tiles[101].image
    
    # Time 149: Still first frame
    mock_get_ticks.return_value = 149
    img = anim_manager.get_current_frame_image(100)
    assert img == map_manager_mock.tiles[101].image
    
    # Time 150: Should be second frame (102)
    mock_get_ticks.return_value = 150
    img = anim_manager.get_current_frame_image(100)
    assert img == map_manager_mock.tiles[102].image
    
    # Time 299: Still second frame
    mock_get_ticks.return_value = 299
    img = anim_manager.get_current_frame_image(100)
    assert img == map_manager_mock.tiles[102].image
    
    # Time 300: Back to first frame (300 % 300 == 0)
    mock_get_ticks.return_value = 300
    img = anim_manager.get_current_frame_image(100)
    assert img == map_manager_mock.tiles[101].image

def test_animation_map_manager_static_fallback(map_manager_mock):
    """Verify fallback to base image if frames list is missing or empty."""
    anim_manager = AnimationMapManager(map_manager_mock)
    
    # Add a static tile
    static_tile = MagicMock()
    static_tile.image = pygame.Surface((32, 32))
    static_tile.frames = None
    map_manager_mock.tiles[200] = static_tile
    
    img = anim_manager.get_current_frame_image(200)
    assert img == static_tile.image
