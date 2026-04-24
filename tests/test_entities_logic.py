"""
Consolidated Entity Logic Test Suite
Includes: BaseEntity, Player, NPC, and AI logic.
"""
import pytest
import pygame
from unittest.mock import patch, MagicMock
from src.entities.player import Player
from src.entities.npc import NPC
from src.entities.base import BaseEntity
from src.config import Settings

@pytest.fixture(scope="module", autouse=True)
def entity_env():
    """Shared environment for all entity tests."""
    pygame.init()
    pygame.display.set_mode((1, 1), pygame.HIDDEN)
    Settings.load()
    yield
    pygame.quit()

@pytest.fixture
def mock_spritesheet():
    with patch('src.graphics.spritesheet.SpriteSheet.load_grid', return_value=[pygame.Surface((32, 48)) for _ in range(16)]):
        with patch('src.graphics.spritesheet.SpriteSheet.__init__', return_value=None):
            yield

# --- BASE ENTITY & MOVEMENT ---

def test_entity_initialization():
    """Entity should start at correct position with fixed size."""
    ent = BaseEntity((16, 16))
    assert ent.pos == pygame.math.Vector2(16, 16)
    assert ent.rect.size == (32, 32)

def test_grid_movement_logic():
    """Entity should snap to grid targets."""
    ent = BaseEntity((16, 16))
    ent.speed = 1000
    ent.direction = pygame.math.Vector2(1, 0)
    ent.move(0.01) # Start move
    assert ent.is_moving is True
    assert ent.target_pos == pygame.math.Vector2(48, 16)
    ent.move(1.0) # Complete move
    assert ent.is_moving is False
    assert ent.pos == pygame.math.Vector2(48, 16)

def test_boundary_clamping():
    """Entity should not move outside map boundaries."""
    Settings.MAP_SIZE = 32
    # West Boundary
    ent = BaseEntity((16, 100))
    ent.direction = pygame.math.Vector2(-1, 0)
    ent.move(1.0)
    assert ent.pos.x == 16
    # East Boundary (1024 - 16 = 1008)
    ent = BaseEntity((1008, 100))
    ent.direction = pygame.math.Vector2(1, 0)
    ent.move(1.0)
    assert ent.pos.x == 1008

# --- PLAYER SPECIFIC ---

def test_player_input_priority(mock_spritesheet):
    """Player input should prioritize vertical movement."""
    player = Player((16, 16))
    class MockKeys:
        def __getitem__(self, k): return k in (Settings.MOVE_UP, Settings.MOVE_RIGHT)
    
    with patch('pygame.key.get_pressed', return_value=MockKeys()):
        player.input()
        player.update(0.01)
    
    assert player.direction.y == -1
    assert player.direction.x == 0

def test_player_hitbox_visual_offset(mock_spritesheet):
    """Player physical rect (32x32) vs visual image (32x48)."""
    player = Player((16, 16))
    assert player.rect.size == (32, 32)
    assert player.image.get_height() == 48

# --- NPC & AI ---

def test_npc_initialization(mock_spritesheet):
    """NPC initializes with wander radius and idle state."""
    npc = NPC((48, 48), wander_radius=1)
    assert npc.state == 'idle'
    assert npc.wander_radius == 1

def test_npc_ai_state_machine(mock_spritesheet):
    """NPC transitions between idle and wandering."""
    npc = NPC((48, 48), wander_radius=5)
    # Mock timer to force move
    npc._action_timer = 10.0
    npc._action_cooldown = 0
    
    # Force a movement direction in random.choice
    with patch('random.choice', return_value=pygame.math.Vector2(1, 0)):
        npc.update(0.01)
    
    assert npc.state == 'wander'
    assert npc.is_moving is True

def test_npc_collision_avoidance(mock_spritesheet):
    """NPC should not move if collision function returns True."""
    npc = NPC((48, 48))
    # Collision function must accept 'requester' keyword argument
    npc.collision_func = lambda x, y, requester=None: True
    npc._action_timer = 10.0
    npc._action_cooldown = 0
    
    with patch('random.choice', return_value=pygame.math.Vector2(1, 0)):
        npc.update(0.01)
        
    # Should stay idle if move is blocked
    assert npc.is_moving is False
    assert npc.state == 'idle'
