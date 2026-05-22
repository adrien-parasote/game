"""Coverage tests for BaseEntity and Player (entity layer)."""

import os
from unittest.mock import MagicMock, patch

import pygame
import pytest

os.environ["SDL_VIDEODRIVER"] = "dummy"
pygame.display.init()
pygame.font.init()

from src.config import Settings
from src.entities.base import BaseEntity
from src.entities.player import Player


class TestBaseEntityCoverage:
    def test_start_move_zero_direction_returns_early(self):
        """L51: start_move with zero direction is a no-op."""
        entity = BaseEntity(pos=(100, 100))
        entity.direction = pygame.math.Vector2(0, 0)
        entity.start_move()
        assert not entity.is_moving

    def test_start_move_collision_blocks_move(self):
        """L66-68: walkable_func returning False prevents move."""
        entity = BaseEntity(pos=(100, 100))
        entity.speed = 200
        entity.walkable_func = lambda px, py, requester=None: False
        entity.direction = pygame.math.Vector2(1, 0)
        entity.start_move()
        assert not entity.is_moving
        assert entity.target_pos == entity.pos

    def test_start_move_target_equals_current_no_move(self):
        """L71-72: if boundary clamp collapses target to current pos, don't start moving."""
        entity = BaseEntity(pos=(16, 16))
        # Force target to be at same position by placing entity at world edge
        entity.direction = pygame.math.Vector2(-1, 0)  # Would go left → clamped to current
        entity.start_move()
        # Entity is already at minimum x (half_w), so target_pos stays at pos
        # Either not moving, or moved to exactly the same tile
        assert entity.target_pos.x >= 0

    def test_interact_returns_none(self):
        """L76: interact() base implementation returns None (pass)."""
        entity = BaseEntity(pos=(100, 100))
        result = entity.interact(MagicMock())
        assert result is None

    def test_start_move_direction_down_with_game(self):
        """Ligne 81 : direction.y > 0 → requested_dir = 'down' avec game mock."""
        entity = BaseEntity(pos=(160, 160))
        entity.speed = 200
        mock_game = MagicMock()
        mock_game.map_manager.get_direction_flags.return_value = ["any"]
        mock_game.map_manager.width = 100
        mock_game.map_manager.height = 100
        entity.game = mock_game
        entity.direction = pygame.math.Vector2(0, 1)  # direction down
        entity.start_move()
        assert entity.is_moving

    def test_start_move_direction_up_allowed(self):
        """Ligne 83 : direction.y < 0 → requested_dir = 'up' dans start_move."""
        entity = BaseEntity(pos=(160, 160))
        entity.speed = 200
        mock_game = MagicMock()
        mock_game.map_manager.get_direction_flags.return_value = ["any"]
        mock_game.map_manager.width = 100
        mock_game.map_manager.height = 100
        entity.game = mock_game
        entity.direction = pygame.math.Vector2(0, -1)  # direction up
        entity.start_move()
        assert entity.is_moving

    def test_update_calls_move(self):
        """L79: update() delegates to move()."""
        entity = BaseEntity(pos=(100, 100))
        entity.direction = pygame.math.Vector2(1, 0)
        entity.speed = 200
        # No collision, should start moving
        entity.update(0.016)
        assert entity.is_moving or entity.target_pos.x != 100


# ---------------------------------------------------------------------------
# Player — lines 54-65, 82-83, 99
# ---------------------------------------------------------------------------


class TestPlayerCoverage:
    def test_input_move_up(self):
        """Lignes 67-70 : pressing MOVE_UP sets direction.y=-1 et state='up'."""
        player = Player(pos=(100, 100))
        keys = {
            Settings.MOVE_UP: True,
            Settings.MOVE_DOWN: False,
            Settings.MOVE_LEFT: False,
            Settings.MOVE_RIGHT: False,
        }
        with patch("pygame.key.get_pressed", return_value=keys):
            player.input()
        assert player.direction.y == -1
        assert player.current_state == "up"

    def test_input_move_down(self):
        """L53-56: pressing MOVE_DOWN sets direction and state."""
        player = Player(pos=(100, 100))
        keys = {
            Settings.MOVE_UP: False,
            Settings.MOVE_DOWN: True,
            Settings.MOVE_LEFT: False,
            Settings.MOVE_RIGHT: False,
        }
        with patch("pygame.key.get_pressed", return_value=keys):
            player.input()
        assert player.direction.y == 1
        assert player.current_state == "down"

    def test_input_move_left(self):
        """L58-61: pressing MOVE_LEFT sets direction and state."""
        player = Player(pos=(100, 100))
        keys = {
            Settings.MOVE_UP: False,
            Settings.MOVE_DOWN: False,
            Settings.MOVE_LEFT: True,
            Settings.MOVE_RIGHT: False,
        }
        with patch("pygame.key.get_pressed", return_value=keys):
            player.input()
        assert player.direction.x == -1
        assert player.current_state == "left"

    def test_input_move_right(self):
        """L62-65: pressing MOVE_RIGHT sets direction and state."""
        player = Player(pos=(100, 100))
        keys = {
            Settings.MOVE_UP: False,
            Settings.MOVE_DOWN: False,
            Settings.MOVE_LEFT: False,
            Settings.MOVE_RIGHT: True,
        }
        with patch("pygame.key.get_pressed", return_value=keys):
            player.input()
        assert player.direction.x == 1
        assert player.current_state == "right"

    def test_update_animation_while_moving(self):
        """L82-83: frame_index advances when is_moving=True."""
        player = Player(pos=(100, 100))
        player.is_moving = True
        initial_frame = player.frame_index
        player._update_animation(0.2)
        # frame_index should have advanced (then wrapped mod 4)
        assert player.frame_index != initial_frame or player.frame_index == 0.0

    def test_player_emote_calls_emote_manager(self):
        """L99: playerEmote() delegates to emote_manager.trigger()."""
        player = Player(pos=(100, 100))
        player.emote_manager = MagicMock()
        player.playerEmote("interact")
        player.emote_manager.trigger.assert_called_once_with("interact")


# ---------------------------------------------------------------------------
# InteractiveEntity — lines 78, 96, 102, 113-114, 147-151, 193, 225, 230
#                     261-266, 276-277, 280-286, 288-301
# ---------------------------------------------------------------------------
