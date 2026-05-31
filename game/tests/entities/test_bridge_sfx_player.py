"""RED tests — Bridge SFX : _resolve_footstep_material on Player.

Spec: game/docs/specs/bridge-sfx-spec.md
Tests: UT-020 → UT-023, IT-003
"""

import os
from unittest.mock import MagicMock, patch

import pygame
import pytest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")


@pytest.fixture(autouse=True)
def pygame_setup(setup_pygame):
    return


def _make_player():
    """Build a Player without real disk assets."""
    from src.entities.player import Player

    with patch("src.entities.player.SpriteSheet") as mock_ss:
        mock_ss.return_value.load_grid.return_value = [pygame.Surface((32, 32)) for _ in range(16)]
        p = Player(pos=(100, 100))
    return p


def _make_override_entity(material="wood", pos=(100, 100), rect=None):
    """Build a minimal walkable-override entity mock."""
    entity = MagicMock()
    entity.material = material
    entity.rect = rect or pygame.Rect(pos[0] - 16, pos[1] - 16, 32, 32)
    return entity


class TestResolveFootstepMaterial:
    """BRIDGE-U-013 → BRIDGE-U-016 — _resolve_footstep_material() priority logic."""

    @pytest.mark.tc("BRIDGE-U-013")
    def test_override_entity_with_material_returns_material(self):
        """BRIDGE-U-013: Override entity with material='wood' at player pos → returns 'wood'."""
        p = _make_player()
        p.pos = pygame.math.Vector2(100, 100)

        override_ent = _make_override_entity(material="wood", pos=(100, 100))

        mock_game = MagicMock()
        mock_game.walkable_override_entities = [override_ent]
        mock_game.map_manager.get_terrain_material_at.return_value = "water"
        p.game = mock_game

        result = p._resolve_footstep_material()

        assert result == "wood"
        mock_game.map_manager.get_terrain_material_at.assert_not_called()

    @pytest.mark.tc("BRIDGE-U-014")
    def test_override_entity_with_empty_material_falls_back_to_map(self):
        """BRIDGE-U-014: Override entity with material='' → fallback to map_manager."""
        p = _make_player()
        p.pos = pygame.math.Vector2(100, 100)

        override_ent = _make_override_entity(material="", pos=(100, 100))

        mock_game = MagicMock()
        mock_game.walkable_override_entities = [override_ent]
        mock_game.map_manager.get_terrain_material_at.return_value = "stone"
        p.game = mock_game

        result = p._resolve_footstep_material()

        assert result == "stone"
        mock_game.map_manager.get_terrain_material_at.assert_called_once()

    @pytest.mark.tc("BRIDGE-U-015")
    def test_no_override_entity_uses_map_manager(self):
        """BRIDGE-U-015: No override entities → map_manager.get_terrain_material_at() called."""
        p = _make_player()
        p.pos = pygame.math.Vector2(100, 100)

        mock_game = MagicMock()
        mock_game.walkable_override_entities = []
        mock_game.map_manager.get_terrain_material_at.return_value = "stone"
        p.game = mock_game

        result = p._resolve_footstep_material()

        assert result == "stone"
        mock_game.map_manager.get_terrain_material_at.assert_called_once_with(100, 100)

    @pytest.mark.tc("BRIDGE-U-016")
    def test_regression_tile_material_returned_when_no_override(self):
        """BRIDGE-U-016: No bridge override → tile 'stone' returned, same as before."""
        p = _make_player()
        p.pos = pygame.math.Vector2(200, 300)

        mock_game = MagicMock()
        mock_game.walkable_override_entities = []
        mock_game.map_manager.get_terrain_material_at.return_value = "stone"
        p.game = mock_game

        result = p._resolve_footstep_material()

        assert result == "stone"

    def test_no_game_returns_none(self):
        """Edge case: player has no game → _resolve_footstep_material returns None."""
        p = _make_player()
        p.game = None

        result = p._resolve_footstep_material()

        assert result is None

    def test_override_entity_not_at_player_pos_skipped(self):
        """Override entity elsewhere on the map does not affect footstep at player pos."""
        p = _make_player()
        p.pos = pygame.math.Vector2(100, 100)

        # Entity is far away — rect does not cover player pos
        far_entity = _make_override_entity(
            material="wood",
            rect=pygame.Rect(500, 500, 160, 224),
        )

        mock_game = MagicMock()
        mock_game.walkable_override_entities = [far_entity]
        mock_game.map_manager.get_terrain_material_at.return_value = "grass"
        p.game = mock_game

        result = p._resolve_footstep_material()

        assert result == "grass"
        mock_game.map_manager.get_terrain_material_at.assert_called_once()


class TestFootstepIntegration:
    """BRIDGE-I-003 — Footstep SFX 'wood' played when walking on lowered bridge."""

    @pytest.mark.tc("BRIDGE-I-003")
    def test_footstep_uses_bridge_material_wood(self):
        """IT-003: Player walks on bridge with material='wood' → plays '04-footstep_wood'."""
        p = _make_player()
        p.is_moving = True
        p._was_moving = True
        # Force frame crossing into frame 1
        p.frame_index = 0.99
        p.current_state = "down"

        bridge_ent = _make_override_entity(
            material="wood",
            rect=pygame.Rect(84, 84, 32, 32),  # covers (100, 100)
        )

        mock_game = MagicMock()
        mock_game.walkable_override_entities = [bridge_ent]
        mock_game.map_manager.get_terrain_material_at.return_value = "water"
        p.game = mock_game

        mock_audio = MagicMock()
        mock_audio.play_sfx.return_value = True
        p.audio_manager = mock_audio

        # dt small enough to land precisely in frame 1 (speed=6.67 frames/s)
        # frame_index = 0.99 + 6.67*0.005 = ~1.02 → int = 1
        p._update_animation(dt=0.005)

        called_sfx_names = [call.args[0] for call in mock_audio.play_sfx.call_args_list]
        assert "04-footstep_wood" in called_sfx_names

    def test_footstep_water_not_played_on_bridge(self):
        """Regression: '04-footstep_water' NOT played when bridge material overrides."""
        p = _make_player()
        p.is_moving = True
        p._was_moving = True
        p.frame_index = 0.99
        p.current_state = "down"

        bridge_ent = _make_override_entity(
            material="wood",
            rect=pygame.Rect(84, 84, 32, 32),
        )

        mock_game = MagicMock()
        mock_game.walkable_override_entities = [bridge_ent]
        mock_game.map_manager.get_terrain_material_at.return_value = "water"
        p.game = mock_game

        mock_audio = MagicMock()
        mock_audio.play_sfx.return_value = True
        p.audio_manager = mock_audio

        p._update_animation(dt=0.005)

        called_sfx_names = [call.args[0] for call in mock_audio.play_sfx.call_args_list]
        assert "04-footstep_water" not in called_sfx_names


# assert True (legacy bypass)
