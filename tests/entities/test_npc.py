"""Behavioural tests for NPC entity (npc.py)."""

import random
from unittest.mock import MagicMock, patch

import pygame
import pytest

from src.config import Settings


@pytest.fixture(autouse=True)
def pygame_init(setup_pygame):
    yield


def _make_npc(pos=(100, 100), wander_radius=2, sub_type="npc", facing_direction=None):
    """Build an NPC without real disk assets."""
    from src.entities.npc import NPC

    with patch("src.entities.npc.SpriteSheet") as mock_ss:
        mock_ss.return_value.load_grid.return_value = [pygame.Surface((32, 32)) for _ in range(16)]
        npc = NPC(
            pos=pos,
            wander_radius=wander_radius,
            sub_type=sub_type,
            facing_direction=facing_direction,
        )
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


class TestStaticNPC:
    """TC-N-05: static_npc sub_type — NPC immobile qui reste interagissable."""

    def test_static_npc_sub_type_stored(self):
        """NPC stores sub_type passed at construction."""
        npc = _make_npc(sub_type="static_npc")
        assert npc.sub_type == "static_npc"

    def test_default_sub_type_is_npc(self):
        """Default sub_type is 'npc' when not specified."""
        npc = _make_npc()
        assert npc.sub_type == "npc"

    def test_static_npc_process_ai_skipped(self):
        """static_npc never runs AI: _action_timer must not increment."""
        npc = _make_npc(sub_type="static_npc")
        npc._action_timer = 0.0
        npc.update(2.0)
        assert npc._action_timer == 0.0

    def test_static_npc_does_not_change_state(self):
        """static_npc stays in idle after update — AI does not trigger wander."""
        npc = _make_npc(sub_type="static_npc")
        npc.update(10.0)  # force past any cooldown
        assert npc.state == "idle"

    def test_static_npc_default_facing_is_down(self):
        """static_npc starts facing down."""
        npc = _make_npc(sub_type="static_npc")
        assert npc.current_facing == "down"

    def test_static_npc_can_interact(self):
        """static_npc responds to interact() and returns element_id."""
        npc = _make_npc(sub_type="static_npc")
        npc.element_id = "castel-guard"
        initiator = MagicMock()
        initiator.pos = pygame.math.Vector2(100, 200)  # player below (approaching from down)
        result = npc.interact(initiator)
        assert result == "castel-guard"

    def test_static_npc_animates_when_idle(self):
        """TC-006: static_npc cycles frame_index even when not moving."""
        npc = _make_npc(sub_type="static_npc")
        assert npc.frame_index == 0.0
        npc.update(0.1)
        assert npc.frame_index > 0.0

    def test_static_npc_anim_continues_when_idle(self):
        """TC-007: static_npc does not reset frame_index to 0 when not moving."""
        npc = _make_npc(sub_type="static_npc")
        npc.update(0.1)
        prev_idx = npc.frame_index
        assert prev_idx > 0.0
        npc.update(0.1)
        assert npc.frame_index > prev_idx

    def test_static_npc_facing_direction_init(self):
        """TC-008: static_npc respects facing_direction at construction."""
        npc = _make_npc(sub_type="static_npc", facing_direction="left")
        assert npc.current_facing == "left"

    def test_npc_facing_direction_init(self):
        """TC-009: dynamic npc also respects facing_direction at construction."""
        npc = _make_npc(sub_type="npc", facing_direction="left")
        assert npc.current_facing == "left"

    def test_static_npc_anim_frozen_during_interaction(self):
        """TC-010: static_npc animation is frozen when state is 'interact'."""
        npc = _make_npc(sub_type="static_npc")
        npc.state = "interact"
        npc.frame_index = 1.0
        npc.update(0.1)
        assert npc.frame_index == 1.0
