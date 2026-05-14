import pygame
import pytest
from unittest.mock import MagicMock
from src.entities.base import BaseEntity
from src.config import Settings

@pytest.fixture
def entity():
    ent = BaseEntity(pos=(48, 48))
    ent.speed = 100
    
    # Mock game, map_manager, layout
    mock_game = MagicMock()
    mock_map_manager = MagicMock()
    mock_layout = MagicMock()
    
    mock_game.map_manager = mock_map_manager
    mock_game.map_manager.width = 50
    mock_game.map_manager.height = 50
    mock_game.layout = mock_layout
    ent.game = mock_game
    
    # By default, everywhere is walkable
    ent.walkable_func = lambda x, y, requester: True
    
    return ent

def test_start_move_direction_any(entity):
    """TC-005: Try moving 'up' on tile with direction: 'any'"""
    # entity is at (48,48), which is tx=1, ty=1
    entity.game.map_manager.get_direction_flags.return_value = {"any"}
    entity.direction = pygame.math.Vector2(0, -1) # up
    
    entity.start_move()
    
    # Should move up
    assert entity.is_moving is True
    assert entity.target_pos.y == 48 - Settings.TILE_SIZE
    entity.game.map_manager.get_direction_flags.assert_called_once_with(1, 1)

def test_start_move_direction_constrained_blocked(entity):
    """TC-003: Try moving 'left' on tile with direction: 'up' -> Blocked"""
    entity.game.map_manager.get_direction_flags.return_value = {"up"}
    entity.direction = pygame.math.Vector2(-1, 0) # left
    
    entity.start_move()
    
    # Movement blocked by exit constraint
    assert entity.is_moving is False
    assert entity.target_pos.x == 48
    entity.game.map_manager.get_direction_flags.assert_called_once_with(1, 1)

def test_start_move_direction_constrained_allowed(entity):
    """TC-003 subset: Try moving 'up' on tile with direction: 'up' -> Allowed"""
    entity.game.map_manager.get_direction_flags.return_value = {"up"}
    entity.direction = pygame.math.Vector2(0, -1) # up
    
    entity.start_move()
    
    # Movement allowed by exit constraint
    assert entity.is_moving is True
    assert entity.target_pos.y == 48 - Settings.TILE_SIZE

def test_start_move_cardinal_priority(entity):
    """IT-001 subset: Cardinal priority logic resolves diagonals properly."""
    # Diagonal up-left, but x magnitude is greater
    entity.direction = pygame.math.Vector2(-0.8, -0.6)
    entity.game.map_manager.get_direction_flags.return_value = {"up"}
    
    entity.start_move()
    
    # Requested dir will be evaluated as "left" because abs(-0.8) > abs(-0.6)
    # Since allowed is only "up", movement is blocked.
    assert entity.is_moving is False
    
    # Diagonal up-left, but y magnitude is greater
    entity.direction = pygame.math.Vector2(-0.6, -0.8)
    entity.start_move()
    
    # Requested dir will be evaluated as "up" because abs(-0.8) > abs(-0.6)
    # Since allowed is "up", movement is allowed.
    assert entity.is_moving is True
    assert entity.target_pos.y == 48 - 0.8 * Settings.TILE_SIZE
