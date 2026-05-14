"""Behavioural tests for NPC entity (npc.py)."""

import random
from unittest.mock import MagicMock, patch

import pygame
import pytest

from src.config import Settings


@pytest.fixture(autouse=True)
def pygame_init(setup_pygame):
    yield


def _make_npc(pos=(100, 100), wander_radius=2):
    """Build an NPC without real disk assets."""
    from src.entities.npc import NPC

    with patch("src.entities.npc.SpriteSheet") as mock_ss:
        mock_ss.return_value.load_grid.return_value = [pygame.Surface((32, 32)) for _ in range(16)]
        npc = NPC(pos=pos, wander_radius=wander_radius)
    return npc


class TestNPCInit:
    def test_initial_state_is_idle(self):
        """NPC starts in the 'idle' state."""
        npc = _make_npc()
        assert npc.state == "idle"

    def test_spawn_pos_stored(self):
        """NPC stores its spawn position for wander radius enforcement."""
        npc = _make_npc(pos=(200, 300))
        assert npc.spawn_pos == pygame.math.Vector2(200, 300)

    def test_hitbox_is_tile_size(self):
        """NPC hitbox is exactly TILE_SIZE regardless of sprite."""
        npc = _make_npc()
        assert npc.rect.width == Settings.TILE_SIZE
        assert npc.rect.height == Settings.TILE_SIZE


class TestNPCInteract:
    def test_interact_returns_element_id(self):
        """interact() returns element_id for the dialogue system."""
        npc = _make_npc()
        npc.element_id = "npc_01"
        initiator = MagicMock()
        initiator.pos = pygame.math.Vector2(132, 100)  # to the right
        result = npc.interact(initiator)
        assert result == "npc_01"

    def test_interact_sets_state_to_interact(self):
        """interact() sets NPC state to 'interact'."""
        npc = _make_npc()
        initiator = MagicMock()
        initiator.pos = pygame.math.Vector2(132, 100)
        npc.interact(initiator)
        assert npc.state == "interact"

    def test_interact_faces_player_right(self):
        """NPC faces right when player is to the right."""
        npc = _make_npc(pos=(100, 100))
        initiator = MagicMock()
        initiator.pos = pygame.math.Vector2(200, 100)
        npc.interact(initiator)
        assert npc.current_facing == "right"

    def test_interact_faces_player_left(self):
        """NPC faces left when player is to the left."""
        npc = _make_npc(pos=(100, 100))
        initiator = MagicMock()
        initiator.pos = pygame.math.Vector2(0, 100)
        npc.interact(initiator)
        assert npc.current_facing == "left"

    def test_interact_faces_player_down(self):
        """NPC faces down when player is below."""
        npc = _make_npc(pos=(100, 100))
        initiator = MagicMock()
        initiator.pos = pygame.math.Vector2(100, 200)
        npc.interact(initiator)
        assert npc.current_facing == "down"


class TestNPCWanderRadius:
    def test_start_move_blocked_outside_radius(self):
        """NPC refuses to move if target exceeds wander_radius."""
        npc = _make_npc(pos=(100, 100), wander_radius=1)
        # Force NPC far from spawn so any move exceeds radius
        npc.pos = pygame.math.Vector2(100 + Settings.TILE_SIZE * 2, 100)
        npc.direction = pygame.math.Vector2(1, 0)
        npc.start_move()
        assert npc.state == "idle"


class TestNPCUpdate:
    def test_invisible_npc_skips_update(self):
        """NPC with is_visible=False skips update (CPU freeze)."""
        npc = _make_npc()
        npc.is_visible = False
        original_timer = npc._action_timer
        npc.update(1.0)
        assert npc._action_timer == original_timer  # timer not incremented

    def test_interact_state_expires_after_cooldown(self):
        """NPC leaves 'interact' state after _action_cooldown expires."""
        npc = _make_npc()
        npc.state = "interact"
        npc._action_timer = 0.0
        npc._action_cooldown = 0.1
        npc.update(0.5)
        assert npc.state == "idle"
