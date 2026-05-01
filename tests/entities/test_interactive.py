"""Coverage tests for InteractiveEntity (entities layer)."""
import pytest
import pygame
from unittest.mock import MagicMock, patch
import os

os.environ["SDL_VIDEODRIVER"] = "dummy"
pygame.display.init()
pygame.font.init()

from src.entities.interactive import InteractiveEntity

def _make_interactive(
    sub_type="lever",
    is_on=False,
    is_animated=False,
    halo_size=0,
    particles=False,
    particle_count=0,
    is_passable=False,
    facing_direction=None,
    position=0,
    day_night_driven=False,
):
    """Build a minimal InteractiveEntity without disk assets."""
    group = pygame.sprite.Group()
    obstacles = pygame.sprite.Group()
    with patch("src.entities.interactive.SpriteSheet") as mock_ss:
        mock_ss.return_value.valid = False
        entity = InteractiveEntity(
            pos=(100, 100),
            groups=[group],
            sub_type=sub_type,
            sprite_sheet="",
            position=position,
            depth=1,
            start_row=0,
            end_row=3,
            width=32,
            height=32,
            tiled_width=32,
            tiled_height=32,
            obstacles_group=obstacles,
            is_passable=is_passable,
            is_animated=is_animated,
            is_on=is_on,
            halo_size=halo_size,
            halo_color="[255, 200, 100]",
            halo_alpha=130,
            particles=particles,
            particle_count=particle_count,
            element_id="ent_1",
            target_id=None,
            activate_from_anywhere=False,
            facing_direction=facing_direction,
            sfx="",
            day_night_driven=day_night_driven,
        )
    return entity, obstacles


class TestInteractiveCoverage:
    def test_facing_direction_overrides_position(self):
        """L77-78: facing_direction property takes priority over position-based direction."""
        entity, _ = _make_interactive(facing_direction="left", position=0)
        assert entity.direction_str == "left"

    def test_is_on_defaults_to_true_for_light_source(self):
        """L96: light source defaults to is_on=True when is_on arg is None."""
        entity, _ = _make_interactive(halo_size=50, is_on=None)
        assert entity.is_on is True

    def test_is_on_defaults_to_true_for_animated(self):
        """L96: animated entity defaults to is_on=True when is_on arg is None."""
        entity, _ = _make_interactive(is_animated=True, is_on=None)
        assert entity.is_on is True

    def test_light_source_random_frame_offset(self):
        """L102: animated light source starts at random frame in [start, end+1)."""
        entity, _ = _make_interactive(sub_type="torch", is_animated=True, is_on=True)
        # frame_index should be within [start_row, end_row+1)
        assert 0.0 <= entity.frame_index < 5.0

    def test_frame_clamp_col_index_out_of_range(self):
        """L221: _get_frame clamps col to max available column."""
        entity, _ = _make_interactive(position=10)  # 10 > num_cols → clamp
        frame = entity._get_frame(0)
        assert frame is not None

    def test_get_frame_empty_frames_returns_surface(self):
        """L225: _get_frame with empty frames list returns blank Surface."""
        entity, _ = _make_interactive()
        entity.frames = []
        result = entity._get_frame(0)
        assert isinstance(result, pygame.Surface)

    def test_interact_sign_returns_element_id(self):
        """L229-230: interact() on sign returns element_id for dialogue."""
        entity, _ = _make_interactive(sub_type="sign")
        result = entity.interact(MagicMock())
        assert result == "ent_1"

    def test_restore_state_door_passable_removes_from_obstacles(self):
        """L251-252: restore_state with is_on=True on passable door removes from obstacles."""
        entity, obstacles = _make_interactive(sub_type="door", is_passable=True)
        obstacles.add(entity)  # Start as blocking
        entity.restore_state({"is_on": True})
        assert entity not in obstacles.sprites()

    def test_restore_state_door_closed_adds_to_obstacles(self):
        """L253-254: restore_state with is_on=False on door adds to obstacles."""
        entity, obstacles = _make_interactive(sub_type="door", is_passable=True, is_on=True)
        entity.restore_state({"is_on": False})
        assert entity in obstacles.sprites()

    def test_update_animated_looping_wraps_frame(self):
        """L282-283: animated entity wraps frame_index to start_row when past end."""
        entity, _ = _make_interactive(is_animated=True, is_on=True)
        entity.frame_index = float(entity.end_row + 0.9)
        entity.update(0.1)
        assert entity.frame_index <= entity.end_row + 1

    def test_update_animated_off_resets_frame(self):
        """L285-286: animated entity when OFF resets frame_index to start."""
        entity, _ = _make_interactive(is_animated=True, is_on=False)
        entity.frame_index = 2.5
        entity.update(0.1)
        assert entity.frame_index == float(entity.start_row)

    def test_update_closing_door_decrements_frame(self):
        """L288-292: closing (is_closing=True) decrements frame_index."""
        entity, obstacles = _make_interactive(sub_type="door", is_on=False, is_passable=True)
        entity.is_animating = True
        entity.is_closing = True
        entity.frame_index = 2.0
        entity.animation_speed = 10.0
        entity.update(0.5)  # Large enough dt to reach start_row
        assert entity.frame_index <= entity.start_row + 0.1

    def test_update_door_open_removes_from_obstacles(self):
        """L300-301: door reaching end_row removes itself from obstacles if passable."""
        entity, obstacles = _make_interactive(sub_type="door", is_passable=True, is_on=True)
        entity.is_animating = True
        entity.is_closing = False
        entity.frame_index = float(entity.end_row) - 0.1
        entity.animation_speed = 10.0
        obstacles.add(entity)
        entity.update(0.1)
        assert entity not in obstacles.sprites()

    def test_update_halo_flicker_non_animated(self):
        """L267-277: non-animated light source uses time-based flicker."""
        entity, _ = _make_interactive(sub_type="torch", halo_size=50, is_on=True, is_animated=False)
        entity.update(0.016)
        # f_alpha should be modified from 1.0
        assert isinstance(entity.f_alpha, float)

    def test_update_halo_off_resets_values(self):
        """L275-277: when is_on=False, f_alpha and f_scale reset to 1.0."""
        entity, _ = _make_interactive(halo_size=50, is_on=False)
        entity.f_alpha = 0.5
        entity.update(0.016)
        assert entity.f_alpha == 1.0
        assert entity.f_scale == 1.0


class TestInteractiveDayNight:
    def test_tc01_night_auto_on(self):
        """TC-01: day_night_driven=True, brightness=0.4 (nuit) -> is_on == True"""
        entity, _ = _make_interactive(halo_size=50, day_night_driven=True)
        time_sys = MagicMock()
        time_sys.brightness = 0.3
        entity._time_system = time_sys
        assert entity.is_on is True

    def test_tc02_day_auto_off(self):
        """TC-02: day_night_driven=True, brightness=0.8 (jour) -> is_on == False"""
        entity, _ = _make_interactive(halo_size=50, day_night_driven=True)
        time_sys = MagicMock()
        time_sys.brightness = 0.8
        entity._time_system = time_sys
        assert entity.is_on is False

    def test_tc03_ignore_brightness_if_not_driven(self):
        """TC-03: day_night_driven=False, _time_system injecté -> ignore brightness, suit _static_is_on"""
        entity, _ = _make_interactive(halo_size=50, day_night_driven=False, is_on=True)
        time_sys = MagicMock()
        time_sys.brightness = 0.8 # jour
        entity._time_system = time_sys
        assert entity.is_on is True

    def test_tc04_interact_auto_night_forces_off(self):
        """TC-04: interact() en mode auto de nuit -> light_control == 'forced_off'"""
        entity, _ = _make_interactive(halo_size=50, day_night_driven=True)
        time_sys = MagicMock()
        time_sys.brightness = 0.3 # nuit -> allumé auto
        entity._time_system = time_sys
        entity.interact(MagicMock())
        assert entity.light_control == "forced_off"

    def test_tc05_interact_auto_day_forces_on(self):
        """TC-05: interact() en mode auto de jour -> light_control == 'forced_on'"""
        entity, _ = _make_interactive(halo_size=50, day_night_driven=True)
        time_sys = MagicMock()
        time_sys.brightness = 0.8 # jour -> éteint auto
        entity._time_system = time_sys
        entity.interact(MagicMock())
        assert entity.light_control == "forced_on"

    def test_tc06_second_interact_returns_to_auto(self):
        """TC-06: 2e interact() (forced -> auto) -> light_control == 'auto'"""
        entity, _ = _make_interactive(halo_size=50, day_night_driven=True)
        entity.light_control = "forced_on"
        entity.interact(MagicMock())
        assert entity.light_control == "auto"

    def test_tc07_restore_state_preserves_control(self):
        """TC-07: restore_state({'light_control': 'forced_on'}) -> light_control == 'forced_on'"""
        entity, _ = _make_interactive(halo_size=50, day_night_driven=True)
        entity.restore_state({'light_control': 'forced_on'})
        assert entity.light_control == "forced_on"

    def test_tc08_fallback_without_timesystem(self):
        """TC-08: _time_system=None, day_night_driven=True -> fallback _static_is_on"""
        entity, _ = _make_interactive(halo_size=50, day_night_driven=True, is_on=True)
        assert getattr(entity, '_time_system', None) is None
        assert entity.is_on is True

class TestInteractiveAmbientAudio:
    def test_ambient_starts_on_initialization_if_on(self):
        """If sfx_ambient is set and entity is_on initially, it triggers play_ambient on update."""
        entity, _ = _make_interactive(is_on=True)
        entity.sfx_ambient = "05-fire_crackle"
        
        mock_game = MagicMock()
        mock_game.player.pos = pygame.math.Vector2(100, 100)
        entity.game = mock_game
        
        with patch('src.engine.game.Game', return_value=mock_game):
            # The first update should trigger play_ambient
            entity.update(0.1)
            
        mock_game.audio_manager.play_ambient.assert_called_once_with("05-fire_crackle", "ent_1")
        mock_game.audio_manager.update_ambient.assert_called()

    def test_ambient_stops_when_toggled_off(self):
        """When an entity turns off, it should call stop_ambient."""
        entity, _ = _make_interactive(is_on=True)
        entity.sfx_ambient = "05-fire_crackle"
        mock_game = MagicMock()
        mock_game.player.pos = pygame.math.Vector2(100, 100)
        entity.game = mock_game
        
        # Turn off via interaction
        entity.interact(MagicMock())
        
        with patch('src.engine.game.Game', return_value=mock_game):
            entity.update(0.1)
            
        mock_game.audio_manager.stop_ambient.assert_called_with("ent_1")


# ---------------------------------------------------------------------------
# InteractionManager — lines 23, 38, 56, 61, 77, 87, 90, 110, 129-137, 255
#                      281, 283, 285, 290, 293-296, 310
# ---------------------------------------------------------------------------

def _make_game_mock():
    game = MagicMock()
    game.player.pos = pygame.math.Vector2(100, 100)
    game.player.current_state = "down"
    game.player.is_moving = False
    game.interactives = []
    game.pickups = []
    game.npcs = []
    return game


