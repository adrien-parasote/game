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
    """NPC fixture with a proper SpriteSheet mock."""
    frames = [pygame.Surface((32, 48)) for _ in range(16)]
    with patch('src.graphics.spritesheet.SpriteSheet.load_grid', return_value=frames):
        with patch('src.graphics.spritesheet.SpriteSheet.__init__', return_value=None):
            npc = NPC((16, 16), wander_radius=2, sheet_name="01-character.png")
            npc.frames = frames  # Ensure frames are accessible for animation tests
            return npc

def test_npc_initialization(npc_instance):
    """TC-N-01: NPC Init and physical dimensions."""
    assert npc_instance.rect.size == (32, 32)
    assert npc_instance.image.get_size() == (32, 48)
    assert npc_instance.state == 'idle'
    assert npc_instance.spawn_pos == pygame.math.Vector2(16, 16)

def test_npc_wander_radius(npc_instance, monkeypatch):
    """TC-N-02: NPC does not wander beyond wander_radius."""
    monkeypatch.setattr(Settings, "MAP_SIZE", 100)
    npc_instance.speed = 1000

    npc_instance.direction = pygame.math.Vector2(1, 0)

    # Base position is 16, 16. Radius is 2 tiles (64px). Max X = 16 + 64 = 80.
    for _ in range(2):
        npc_instance.start_move()
        npc_instance.move(0.1)
        assert not npc_instance.is_moving

    assert npc_instance.pos.x == 80

    # Try moving another tile (out of radius)
    npc_instance.direction = pygame.math.Vector2(1, 0)
    npc_instance.start_move()
    assert npc_instance.is_moving == False
    assert npc_instance.pos.x == 80
    assert npc_instance.target_pos.x == 80

def test_npc_cpu_freeze(npc_instance):
    """TC-N-03: NPC skips behavior processing when is_visible=False."""
    npc_instance.is_visible = False
    npc_instance.process_ai = MagicMock()

    npc_instance.update(0.16)
    npc_instance.process_ai.assert_not_called()

    npc_instance.is_visible = True
    npc_instance.update(0.16)
    npc_instance.process_ai.assert_called_once()

def test_npc_interact_facing_from_east(npc_instance):
    """NPC faces player when player is to the east (diff.x > diff.y)."""
    initiator = MagicMock()
    initiator.pos = pygame.math.Vector2(100, 16)  # Player far to the right
    npc_instance.pos = pygame.math.Vector2(16, 16)

    npc_instance.interact(initiator)

    assert npc_instance.state == 'interact'
    assert npc_instance.current_facing == 'right'
    assert npc_instance.is_moving is False
    assert npc_instance._action_cooldown == 2.0

def test_npc_interact_facing_from_north(npc_instance):
    """NPC faces player when player is to the north (diff.y dominates, up)."""
    initiator = MagicMock()
    initiator.pos = pygame.math.Vector2(16, -50)  # Player above
    npc_instance.pos = pygame.math.Vector2(16, 16)

    npc_instance.interact(initiator)

    assert npc_instance.current_facing == 'up'

def test_npc_interact_releases_after_timeout(npc_instance):
    """NPC returns to idle state after interact cooldown expires."""
    initiator = MagicMock()
    initiator.pos = pygame.math.Vector2(100, 16)
    npc_instance.interact(initiator)

    assert npc_instance.state == 'interact'

    # Advance time past the interaction cooldown (2.0s)
    npc_instance.update(2.1)

    assert npc_instance.state == 'idle'

def test_npc_process_ai_frozen_during_interact(npc_instance):
    """process_ai returns immediately when state is 'interact'."""
    npc_instance.state = 'interact'
    npc_instance._action_timer = 0.0
    initial_timer = npc_instance._action_timer

    npc_instance.process_ai(1.0)

    # Timer should not have advanced (early return)
    assert npc_instance._action_timer == initial_timer

def test_npc_animation_update_moving(npc_instance):
    """frame_index advances when NPC is moving."""
    npc_instance.is_moving = True
    npc_instance.current_facing = 'right'
    npc_instance.frame_index = 0.0

    npc_instance._update_animation(0.16)

    assert npc_instance.frame_index > 0.0

def test_npc_animation_update_idle(npc_instance):
    """frame_index resets to 0 when NPC is idle."""
    npc_instance.is_moving = False
    npc_instance.current_facing = 'down'
    npc_instance.frame_index = 2.5

    npc_instance._update_animation(0.16)

    assert npc_instance.frame_index == 0.0

def test_npc_update_full_cycle(npc_instance):
    """update(dt) correctly composes process_ai, move, and animation."""
    npc_instance.is_visible = True
    npc_instance.state = 'idle'
    npc_instance.process_ai = MagicMock()
    npc_instance._update_animation = MagicMock()

    npc_instance.update(0.16)

    npc_instance.process_ai.assert_called_once_with(0.16)
    npc_instance._update_animation.assert_called_once_with(0.16)
