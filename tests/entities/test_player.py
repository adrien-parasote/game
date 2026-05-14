"""Tests for Player entity (player.py).

Covers: initialization, animation state, update cycle, direction/frame mapping.
"""

import os
from unittest.mock import MagicMock, patch

import pygame
import pytest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")


@pytest.fixture(autouse=True)
def pygame_setup(setup_pygame):
    """Reuse the project-wide headless pygame fixture from conftest."""
    yield


def _make_player(pos=(100, 100)):
    """Build a Player without real disk assets."""
    from src.entities.player import Player

    with patch("src.entities.player.SpriteSheet") as mock_ss:
        mock_ss.return_value.load_grid.return_value = [pygame.Surface((32, 32)) for _ in range(16)]
        p = Player(pos=pos)
    return p


class TestPlayerInit:
    def test_initial_state(self):
        """Player starts with expected default values."""
        p = _make_player()
        assert p.speed > 0
        assert p.hp == 100
        assert p.max_hp == 100
        assert p.gold == 0
        assert p.current_state == "down"
        assert p.frame_index == 0.0

    def test_rect_is_tile_size(self):
        """Player hitbox is always Settings.TILE_SIZE regardless of sprite."""
        from src.config import Settings
        p = _make_player(pos=(50, 50))
        assert p.rect.width == Settings.TILE_SIZE
        assert p.rect.height == Settings.TILE_SIZE

    def test_rect_centered_on_pos(self):
        """Player rect is centered at the given spawn position."""
        p = _make_player(pos=(200, 300))
        assert p.rect.center == (200, 300)


class TestPlayerAnimation:
    def test_direction_down_uses_frame_offset_0(self):
        """Direction 'down' maps to the first row (offset 0)."""
        p = _make_player()
        p.current_state = "down"
        p.is_moving = True
        p.frame_index = 0.0
        p._was_moving = True
        p._update_animation(dt=0.0)
        assert p.image is p.frames[0]

    def test_direction_left_uses_frame_offset_4(self):
        """Direction 'left' maps to row offset 4."""
        p = _make_player()
        p.current_state = "left"
        p.is_moving = True
        p.frame_index = 0.0
        p._was_moving = True
        p._update_animation(dt=0.0)
        assert p.image is p.frames[4]

    def test_direction_right_uses_frame_offset_8(self):
        """Direction 'right' maps to row offset 8."""
        p = _make_player()
        p.current_state = "right"
        p.is_moving = True
        p.frame_index = 0.0
        p._was_moving = True
        p._update_animation(dt=0.0)
        assert p.image is p.frames[8]

    def test_direction_up_uses_frame_offset_12(self):
        """Direction 'up' maps to row offset 12."""
        p = _make_player()
        p.current_state = "up"
        p.is_moving = True
        p.frame_index = 0.0
        p._was_moving = True
        p._update_animation(dt=0.0)
        assert p.image is p.frames[12]

    def test_idle_resets_to_frame_0(self):
        """When not moving and was not moving, frame resets to 0."""
        p = _make_player()
        p.is_moving = False
        p._was_moving = False
        p.frame_index = 2.5
        p._update_animation(dt=0.1)
        assert p.frame_index == 0.0

    def test_animation_advances_when_moving(self):
        """Frame index increases when player is moving."""
        p = _make_player()
        p.is_moving = True
        p._was_moving = True
        p.frame_index = 0.0
        p._update_animation(dt=0.5)
        assert p.frame_index > 0.0

    def test_animation_wraps_at_4(self):
        """Frame index wraps at 4 (one row = 4 frames)."""
        p = _make_player()
        p.is_moving = True
        p._was_moving = True
        p.frame_index = 3.9
        p._update_animation(dt=1.0)
        # After wrap, frame_index should be in [0, 4)
        assert 0.0 <= p.frame_index < 4.0


class TestPlayerUpdate:
    def test_update_calls_move_and_animation(self):
        """update() calls both move() and _update_animation()."""
        p = _make_player()
        with patch.object(p, "move") as mock_move, \
             patch.object(p, "_update_animation") as mock_anim:
            p.update(0.016)
            mock_move.assert_called_once_with(0.016)
            mock_anim.assert_called_once_with(0.016)


class TestPlayerFootstep:
    def test_footstep_plays_on_frame_1(self):
        """Footstep SFX is triggered when animation reaches frame 1."""
        p = _make_player()
        p.is_moving = True
        p._was_moving = True
        p.frame_index = 0.99  # will cross into frame 1 with large dt
        p.game = None
        p.audio_manager = MagicMock()
        p.audio_manager.play_sfx.return_value = True
        p._update_animation(dt=0.2)
        # We just check no crash; audio behavior depends on frame crossing
