import pygame
import pytest
from src.entities.base import BaseEntity
from src.config import Settings

@pytest.fixture
def setup_settings():
    Settings.TILE_SIZE = 32
    Settings.MAP_SIZE = 10
    pygame.init()
    pygame.display.set_mode((1280, 720), pygame.HIDDEN)

def test_grid_centering(setup_settings):
    """TC-B-01: Entities must be aligned to tile centers (half-tile offset)."""
    # Spawn at (0,0) index -> should resolve to (16, 16)
    tile_x, tile_y = 0, 0
    half_tile = Settings.TILE_SIZE // 2
    spawn_pos = (tile_x * Settings.TILE_SIZE + half_tile, tile_y * Settings.TILE_SIZE + half_tile)
    
    entity = BaseEntity(spawn_pos)
    assert entity.pos.x == 16
    assert entity.pos.y == 16
    assert entity.rect.center == (16, 16)

def test_world_boundaries_clamping(setup_settings):
    """TC-B-02: Entities clamped to world dimensions."""
    # World width = 32 * 10 = 320
    # Center pos clamped between 16 and 304
    
    entity = BaseEntity((16, 16))
    entity.speed = 1000
    
    # Try to move LEFT (out of bounds)
    entity.direction = pygame.math.Vector2(-1, 0)
    entity.start_move()
    # Target should be clamped to (16, 16)
    assert entity.target_pos.x == 16
    assert entity.is_moving == False
    
    # Move RIGHT to opposite edge
    entity.direction = pygame.math.Vector2(1, 0)
    # Perform 10 steps to reach the end
    for _ in range(20):
        entity.start_move()
        entity.move(0.1) # Simulate movement
        if not entity.is_moving:
            entity.direction = pygame.math.Vector2(1, 0)
            
    # Max center is 320 - 16 = 304
    assert entity.pos.x <= 304
    
    # Try to move RIGHT again
    entity.direction = pygame.math.Vector2(1, 0)
    entity.start_move()
    assert entity.is_moving == False
    assert entity.pos.x == 304
