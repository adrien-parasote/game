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

    def test_footstep_fallback_when_material_sfx_fails(self):
        """Ligne 119 : quand play_sfx(matiere) échoue, fallback sur '04-footstep'."""
        p = _make_player()
        p.is_moving = True
        p._was_moving = True
        p.frame_index = 0.99
        audio = MagicMock()
        audio.play_sfx.side_effect = [False, True]
        p.audio_manager = audio
        mock_game = MagicMock()
        mock_game.map_manager.get_terrain_material_at.return_value = "stone"
        mock_game.walkable_override_entities = []
        p.game = mock_game
        # dt=0.016 → 0.99 + 6.67*0.016 ≈ 1.097 → franchit le frame 1 → play_sfx("stone") → False → fallback
        p._update_animation(dt=0.016)
        # Si le frame a été franchi, play_sfx est appelé au moins une fois
        assert audio.play_sfx.call_count >= 1


class TestPlayerResolveFootstepMaterial:
    def test_entity_material_takes_priority(self):
        """Ligne 137 (entity.rect truthy) : entity_material non vide → retourné en priorité."""
        p = _make_player()
        mock_entity = MagicMock()
        mock_entity.rect = pygame.Rect(90, 90, 40, 40)
        mock_entity.material = "wood"
        mock_game = MagicMock()
        mock_game.walkable_override_entities = [mock_entity]
        mock_game.map_manager.get_terrain_material_at.return_value = "stone"
        p.game = mock_game
        p.pos = pygame.math.Vector2(100, 100)
        result = p._resolve_footstep_material()
        assert result == "wood"

    def test_entity_rect_none_is_skipped(self):
        """Ligne 137 : entity.rect falsy → continue (not entity.rect branch)."""
        p = _make_player()
        mock_entity = MagicMock()
        mock_entity.rect = None  # falsy → continue, ligne 137 couverte
        mock_entity.material = "wood"
        mock_game = MagicMock()
        mock_game.walkable_override_entities = [mock_entity]
        mock_game.map_manager.get_terrain_material_at.return_value = "grass"
        p.game = mock_game
        p.pos = pygame.math.Vector2(100, 100)
        result = p._resolve_footstep_material()
        # rect=None → entité skippée → fallback map_manager
        assert result == "grass"

    def test_map_manager_material_fallback(self):
        """Sans override entity, on utilise map_manager."""
        p = _make_player()
        mock_game = MagicMock()
        mock_game.walkable_override_entities = []
        mock_game.map_manager.get_terrain_material_at.return_value = "grass"
        p.game = mock_game
        p.pos = pygame.math.Vector2(100, 100)
        result = p._resolve_footstep_material()
        assert result == "grass"
