import pygame
import pytest
from unittest.mock import patch, MagicMock
from src.entities.npc import NPC
from src.config import Settings

@pytest.fixture
def setup_pygame():
    pygame.init()
    pygame.display.set_mode((1, 1), pygame.HIDDEN)
    yield
    pygame.quit()

@pytest.fixture
def npc_instance(setup_pygame):
    # Mock SpriteSheet initialization to return blank surfaces
    with patch('src.graphics.spritesheet.SpriteSheet.load_grid', return_value=[pygame.Surface((32, 48)) for _ in range(16)]):
        with patch('src.graphics.spritesheet.SpriteSheet.__init__', return_value=None):
            return NPC((16, 16), wander_radius=2, sheet_name="01-character.png")

def test_npc_initialization(npc_instance):
    """TC-N-01: NPC Init and physical dimensions."""
    # Physical hitbox must be 32x32
    assert npc_instance.rect.size == (32, 32)
    # Visual rect is 32x48
    assert npc_instance.image.get_size() == (32, 48)
    # Default state is idle
    assert npc_instance.state == 'idle'
    # Start coordinates match spawn
    assert npc_instance.spawn_pos == pygame.math.Vector2(16, 16)

def test_npc_wander_radius(npc_instance):
    """TC-N-02: NPC does not wander beyond wander_radius."""
    npc_instance.speed = 1000 # Instant movement

    # Override internal random state for predictability if needed, 
    # but here we can just command it to move far right and see if it cancels.
    npc_instance.direction = pygame.math.Vector2(1, 0)
    
    # Base position is 16, 16. Radius is 2 tiles (64px). Max X = 16 + 64 = 80.
    # Move exactly 2 tiles
    for _ in range(2):
        npc_instance.start_move()
        npc_instance.move(0.1) # Move right
        assert not npc_instance.is_moving
        
    assert npc_instance.pos.x == 80
    
    # Try moving another tile (out of radius)
    npc_instance.direction = pygame.math.Vector2(1, 0)
    npc_instance.start_move()
    # It shouldn't move because it's at the boundary
    assert npc_instance.is_moving == False
    assert npc_instance.pos.x == 80
    assert npc_instance.target_pos.x == 80

def test_npc_cpu_freeze(npc_instance):
    """TC-N-03: NPC skips behavior processing when is_visible=False."""
    npc_instance.is_visible = False
    
    # Mock the internal logic
    npc_instance.process_ai = MagicMock()
    
    npc_instance.update(0.16)
    
    # process_ai should NOT be called if not visible
    npc_instance.process_ai.assert_not_called()
    
    # Set to visible and verify it runs
    npc_instance.is_visible = True
    npc_instance.update(0.16)
    npc_instance.process_ai.assert_called_once()
