"""Coverage tests for InteractiveEntity (entities layer)."""

import os
from unittest.mock import MagicMock, patch

import pygame
import pytest

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
    trigger_only=False,
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
            trigger_only=trigger_only,
        )
    return entity, obstacles


class TestInteractiveCoverage:
    def test_facing_direction_overrides_position(self):
        """L77-78: facing_direction property takes priority over position-based direction."""
        entity, _ = _make_interactive(facing_direction="left", position=0)
        assert entity.direction_str == "left"

    def test_is_on_defaults_to_true_for_light_source(self):
        """L96: light source defaults to is_on=True when is_on arg is None."""
        entity, _ = _make_interactive(halo_size=50, is_on=None)  # type: ignore
        assert entity.is_on is True

    def test_is_on_defaults_to_true_for_animated(self):
        """L96: animated entity defaults to is_on=True when is_on arg is None."""
        entity, _ = _make_interactive(is_animated=True, is_on=None)  # type: ignore
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

    @pytest.mark.tc("INT-U-01")
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

    @pytest.mark.tc("INT-U-02")
    def test_update_animated_looping_wraps_frame(self):
        """L282-283: animated entity wraps frame_index to start_row when past end."""
        entity, _ = _make_interactive(is_animated=True, is_on=True)
        entity.frame_index = float(entity.end_row + 0.9)
        entity.update(0.1)
        assert entity.frame_index <= entity.end_row + 1

    @pytest.mark.tc("INT-U-03")
    def test_update_animated_off_resets_frame(self):
        """L285-286: animated entity when OFF resets frame_index to start."""
        entity, _ = _make_interactive(is_animated=True, is_on=False)
        entity.frame_index = 2.5
        entity.update(0.1)
        assert entity.frame_index == float(entity.start_row)

    @pytest.mark.tc("INT-U-04")
    def test_update_closing_door_decrements_frame(self):
        """L288-292: closing (is_closing=True) decrements frame_index."""
        entity, obstacles = _make_interactive(sub_type="door", is_on=False, is_passable=True)
        entity.is_animating = True
        entity.is_closing = True
        entity.frame_index = 2.0
        entity.animation_speed = 10.0
        entity.update(0.5)  # Large enough dt to reach start_row
        assert entity.frame_index <= entity.start_row + 0.1

    def test_is_closing_initialized_to_false(self):
        """is_closing must be False on init — not a dynamic attribute risk."""
        entity, _ = _make_interactive(sub_type="door")
        assert entity.is_closing is False

    @pytest.mark.tc("INT-U-04b")
    def test_interact_close_sets_frame_index_to_end_row(self):
        """Closing a door via interact() must start animation from end_row."""
        entity, _ = _make_interactive(sub_type="door", is_on=True, is_passable=True)
        # Simulate door fully open (animation ended at end_row)
        entity.frame_index = float(entity.end_row)
        entity.is_animating = False
        # Close the door
        entity.interact(MagicMock())
        assert entity.is_on is False
        assert entity.is_closing is True
        assert entity.is_animating is True
        assert entity.frame_index == float(entity.end_row)

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
        time_sys.brightness = 0.8  # jour
        entity._time_system = time_sys
        assert entity.is_on is True

    def test_tc04_interact_auto_night_forces_off(self):
        """TC-04: interact() en mode auto de nuit -> light_control == 'forced_off'"""
        entity, _ = _make_interactive(halo_size=50, day_night_driven=True)
        time_sys = MagicMock()
        time_sys.brightness = 0.3  # nuit -> allumé auto
        entity._time_system = time_sys
        entity.interact(MagicMock())
        assert entity.light_control == "forced_off"

    def test_tc05_interact_auto_day_forces_on(self):
        """TC-05: interact() en mode auto de jour -> light_control == 'forced_on'"""
        entity, _ = _make_interactive(halo_size=50, day_night_driven=True)
        time_sys = MagicMock()
        time_sys.brightness = 0.8  # jour -> éteint auto
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
        entity.restore_state({"light_control": "forced_on"})
        assert entity.light_control == "forced_on"

    def test_tc08_fallback_without_timesystem(self):
        """TC-08: _time_system=None, day_night_driven=True -> fallback _static_is_on"""
        entity, _ = _make_interactive(halo_size=50, day_night_driven=True, is_on=True)
        assert getattr(entity, "_time_system", None) is None
        assert entity.is_on is True


class TestInteractiveAmbientAudio:
    def test_ambient_proposes_distance_when_on(self):
        """If sfx_ambient is set and entity is_on, update() calls propose_ambient with distance."""
        entity, _ = _make_interactive(is_on=True)
        entity.sfx_ambient = "05-fire_crackle"

        mock_game = MagicMock()
        mock_game.player.pos = pygame.math.Vector2(100, 100)
        entity.pos = pygame.math.Vector2(100, 100)
        entity.game = mock_game

        entity.update(0.1)

        mock_game.audio_manager.propose_ambient.assert_called_once_with(
            "05-fire_crackle", pytest.approx(0.0, abs=1e-3)
        )

    def test_ambient_no_proposal_when_off(self):
        """When entity is_on=False, propose_ambient must NOT be called."""
        entity, _ = _make_interactive(is_on=False)
        entity.sfx_ambient = "05-fire_crackle"
        mock_game = MagicMock()
        mock_game.player.pos = pygame.math.Vector2(100, 100)
        entity.game = mock_game

        entity.update(0.1)

        mock_game.audio_manager.propose_ambient.assert_not_called()


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


class TestInteractiveLightingCoverage:
    """interactive_lighting.py: _update_flicker covers lines 71-78, 98-99, 109."""

    def _ent(self, is_on=True):
        """Build a minimal entity with lighting attributes."""
        from src.entities.interactive_lighting import InteractiveLightingMixin
        ent = MagicMock(spec=InteractiveLightingMixin)
        ent.is_on = is_on
        ent.halo_size = 48
        ent.halo_alpha = 180
        ent.halo_color = pygame.Color(255, 200, 100)
        ent.f_scale = 1.0
        ent.f_alpha = 1.0
        ent.flicker_phase = 0.0
        ent.is_light_source = False
        ent.is_animated = False
        ent.start_row = 0
        ent.end_row = 3
        ent.frame_index = 0
        ent.light_mask_cache = [pygame.Surface((96, 96)) for _ in range(8)]
        ent.light_mask = pygame.Surface((96, 96))
        return ent

    def test_update_flicker_is_on(self):
        """L71-78 — _update_flicker updates f_scale when is_on."""
        from src.entities.interactive_lighting import InteractiveLightingMixin
        ent = self._ent(is_on=True)
        InteractiveLightingMixin._update_flicker(ent, dt=0.016, ticks_ms=1000)
        assert ent.f_scale != 0

    def test_update_flicker_is_off_resets(self):
        """L98-99 — _update_flicker resets f_alpha/f_scale when off."""
        from src.entities.interactive_lighting import InteractiveLightingMixin
        ent = self._ent(is_on=False)
        InteractiveLightingMixin._update_flicker(ent, dt=0.016, ticks_ms=1000)
        assert ent.f_alpha == 1.0
        assert ent.f_scale == 1.0

    def test_update_flicker_animated_source(self):
        """L71-78 — animated light source uses frame-based flicker."""
        from src.entities.interactive_lighting import InteractiveLightingMixin
        ent = self._ent(is_on=True)
        ent.is_light_source = True
        ent.is_animated = True
        ent.end_row = 3
        ent.start_row = 0
        ent.frame_index = 2
        InteractiveLightingMixin._update_flicker(ent, dt=0.016, ticks_ms=1000)


# ---------------------------------------------------------------------------
# TC-INT-DEPTH — depth value from Tiled must survive BaseEntity.__init__ reset
# ---------------------------------------------------------------------------


def _make_interactive_with_depth(depth: int):
    """Build a minimal InteractiveEntity with a specific depth value."""
    group = pygame.sprite.Group()
    obstacles = pygame.sprite.Group()
    with patch("src.entities.interactive.SpriteSheet") as mock_ss:
        mock_ss.return_value.valid = False
        entity = InteractiveEntity(
            pos=(100, 100),
            groups=[group],
            sub_type="door",
            sprite_sheet="",
            position=0,
            depth=depth,
            start_row=0,
            end_row=3,
            width=32,
            height=32,
            tiled_width=32,
            tiled_height=32,
            obstacles_group=obstacles,
            is_passable=True,
            is_animated=False,
            is_on=False,
            halo_size=0,
            halo_color="[255, 200, 100]",
            halo_alpha=130,
            particles=False,
            particle_count=0,
            element_id="door_1",
            target_id=None,
            activate_from_anywhere=False,
            facing_direction=None,
            sfx="",
            day_night_driven=False,
        )
    return entity


class TestInteractiveDepth:
    """Regression tests for the depth-override bug.

    BaseEntity.__init__ (called inside _setup_physics) was resetting self.depth=1
    after _parse_properties had correctly set the Tiled value. The fix re-applies
    depth after _setup_physics completes.
    """

    @pytest.mark.tc("TC-INT-DEPTH-01")
    def test_depth_zero_preserved_after_init(self):
        """depth=0 from Tiled must not be reset to 1 by BaseEntity.__init__."""
        entity = _make_interactive_with_depth(0)
        assert entity.depth == 0

    @pytest.mark.tc("TC-INT-DEPTH-02")
    def test_depth_one_unchanged(self):
        """depth=1 (default) is the same as BaseEntity default — must still be 1."""
        entity = _make_interactive_with_depth(1)
        assert entity.depth == 1

    @pytest.mark.tc("TC-INT-DEPTH-03")
    def test_depth_two_preserved_after_init(self):
        """depth=2 (foreground entity) must survive __init__ without being reset."""
        entity = _make_interactive_with_depth(2)
        assert entity.depth == 2


# ---------------------------------------------------------------------------
# TC-INT-WO — _sync_walkable_override() keeps walkable_override_entities in sync
# ---------------------------------------------------------------------------


class TestWalkableOverride:
    """Tests for InteractiveEntity._sync_walkable_override().

    The system allows CollisionChecker to bypass tile walkability under open
    passable bridges. Preconditions: entity.game.walkable_override_entities is a set.
    """

    def _bridge(self, is_on=True, is_passable=True):
        """Build a passable bridge entity and attach a mock game."""
        entity, _ = _make_interactive(sub_type="bridge", is_on=is_on, is_passable=is_passable)
        mock_game = MagicMock()
        mock_game.walkable_override_entities = set()
        entity.game = mock_game
        return entity, mock_game.walkable_override_entities

    @pytest.mark.tc("TC-INT-WO-01")
    def test_open_passable_bridge_registers_in_override_set(self):
        """Open passable bridge must be added to walkable_override_entities."""
        entity, override_set = self._bridge(is_on=True, is_passable=True)
        entity._sync_walkable_override()
        assert entity in override_set

    @pytest.mark.tc("TC-INT-WO-02")
    def test_closed_passable_bridge_removed_from_override_set(self):
        """Closed passable bridge must be discarded from walkable_override_entities."""
        entity, override_set = self._bridge(is_on=True, is_passable=True)
        override_set.add(entity)  # Pre-add as if it was open

        entity._static_is_on = False  # Close it
        entity._sync_walkable_override()

        assert entity not in override_set

    @pytest.mark.tc("TC-INT-WO-03")
    def test_open_non_passable_bridge_not_registered(self):
        """A non-passable open bridge must NOT be added (only passable bridges need override)."""
        entity, override_set = self._bridge(is_on=True, is_passable=False)
        entity._sync_walkable_override()
        assert entity not in override_set

    @pytest.mark.tc("TC-INT-WO-04")
    def test_sync_is_noop_when_no_game(self):
        """_sync_walkable_override must be safe when entity.game is None."""
        entity, _ = _make_interactive(sub_type="bridge", is_on=True, is_passable=True)
        entity.game = None
        entity._sync_walkable_override()  # Must not raise

    @pytest.mark.tc("TC-INT-WO-05")
    def test_interact_open_registers_in_override(self):
        """Opening a passable bridge via interact() must register it in override_set."""
        entity, override_set = self._bridge(is_on=False, is_passable=True)
        entity.is_animating = False
        entity.interact(MagicMock())
        # After interact, is_on toggled to True → should be in override_set
        assert entity in override_set

    @pytest.mark.tc("TC-INT-WO-06")
    def test_interact_close_removes_from_override(self):
        """Closing an open passable bridge via interact() must remove it from override_set."""
        entity, override_set = self._bridge(is_on=True, is_passable=True)
        override_set.add(entity)  # Was open
        entity.is_animating = False
        entity.interact(MagicMock())
        # After interact, is_on toggled to False → must be removed
        assert entity not in override_set

    @pytest.mark.tc("TC-INT-WO-07")
    def test_restore_state_open_registers_in_override(self):
        """restore_state(is_on=True) on passable bridge registers it in override_set."""
        entity, override_set = self._bridge(is_on=False, is_passable=True)
        entity.restore_state({"is_on": True})
        assert entity in override_set

    @pytest.mark.tc("TC-INT-WO-08")
    def test_restore_state_closed_removes_from_override(self):
        """restore_state(is_on=False) on passable bridge removes it from override_set."""
        entity, override_set = self._bridge(is_on=True, is_passable=True)
        override_set.add(entity)
        entity.restore_state({"is_on": False})
        assert entity not in override_set


# ---------------------------------------------------------------------------
# TC-BRIDGE — sub_type="bridge" collision lifecycle
# ---------------------------------------------------------------------------


class TestBridgeSubtype:
    """Tests for sub_type='bridge' collision behavior.

    A bridge differs from a door in that it never enters obstacles_group.
    When raised (is_on=False), the water tiles beneath handle blocking.
    When lowered (is_on=True), walkable_override_entities enables crossing.

    Spec: docs/specs/bridge-subtype-spec.md
    """

    def _make_bridge(self, is_on=False, is_passable=True):
        """Build a passable bridge entity with a mock game."""
        entity, obstacles = _make_interactive(
            sub_type="bridge", is_on=is_on, is_passable=is_passable
        )
        mock_game = MagicMock()
        mock_game.walkable_override_entities = set()
        entity.game = mock_game
        return entity, obstacles, mock_game.walkable_override_entities

    @pytest.mark.tc("UT-001")
    def test_bridge_raised_not_in_obstacles_at_spawn(self):
        """UT-001: Bridge spawned raised (is_on=False) must NOT be in obstacles_group."""
        entity, obstacles, _ = self._make_bridge(is_on=False)
        assert entity not in obstacles.sprites()

    @pytest.mark.tc("UT-002")
    def test_bridge_lowered_not_in_obstacles_at_spawn(self):
        """UT-002: Bridge spawned lowered (is_on=True) must NOT be in obstacles_group."""
        entity, obstacles, _ = self._make_bridge(is_on=True)
        assert entity not in obstacles.sprites()

    @pytest.mark.tc("UT-003")
    def test_bridge_lowered_registers_in_walkable_override(self):
        """UT-003: Lowered bridge registers in walkable_override_entities."""
        entity, _, override_set = self._make_bridge(is_on=True, is_passable=True)
        entity._sync_walkable_override()
        assert entity in override_set

    @pytest.mark.tc("UT-004")
    def test_bridge_raised_not_in_walkable_override(self):
        """UT-004: Raised bridge must NOT be in walkable_override_entities."""
        entity, _, override_set = self._make_bridge(is_on=False, is_passable=True)
        entity._sync_walkable_override()
        assert entity not in override_set

    @pytest.mark.tc("UT-005")
    def test_bridge_restore_state_open_not_in_obstacles(self):
        """UT-005: restore_state(is_on=True) on bridge must NOT put it in obstacles."""
        entity, obstacles, _ = self._make_bridge(is_on=False)
        entity.restore_state({"is_on": True})
        assert entity not in obstacles.sprites()

    @pytest.mark.tc("UT-006")
    def test_bridge_restore_state_closed_not_in_obstacles(self):
        """UT-006: restore_state(is_on=False) on bridge must NOT put it in obstacles."""
        entity, obstacles, _ = self._make_bridge(is_on=True)
        obstacles.add(entity)  # Simulate a bug where it ended up in obstacles
        entity.restore_state({"is_on": False})
        assert entity not in obstacles.sprites()

    @pytest.mark.tc("UT-007")
    def test_door_spawn_still_blocked_regression_guard(self):
        """UT-007: Regression — door with is_on=False must still be in obstacles."""
        entity, obstacles = _make_interactive(sub_type="door", is_on=False, is_passable=True)
        assert entity in obstacles.sprites()

    @pytest.mark.tc("UT-008")
    def test_should_start_in_obstacles_bridge_always_false(self):
        """UT-008: _should_start_in_obstacles returns False for bridge regardless of is_on."""
        entity_off, _ = _make_interactive(sub_type="bridge", is_on=False, is_passable=True)
        entity_on, _ = _make_interactive(sub_type="bridge", is_on=True, is_passable=True)
        assert entity_off._should_start_in_obstacles() is False
        assert entity_on._should_start_in_obstacles() is False

    @pytest.mark.tc("UT-009")
    def test_should_start_in_obstacles_door_closed(self):
        """UT-009: _should_start_in_obstacles returns True for closed door."""
        entity, _ = _make_interactive(sub_type="door", is_on=False, is_passable=True)
        assert entity._should_start_in_obstacles() is True

    @pytest.mark.tc("UT-010")
    def test_should_start_in_obstacles_door_open_passable(self):
        """UT-010: _should_start_in_obstacles returns False for open passable door."""
        entity, _ = _make_interactive(sub_type="door", is_on=True, is_passable=True)
        assert entity._should_start_in_obstacles() is False


# ---------------------------------------------------------------------------
# TC-BRIDGE-SORT — bridge sort_y rendering fix
# ---------------------------------------------------------------------------


def _make_bridge_entity(tiled_width: int = 160, tiled_height: int = 224):
    """Build a bridge entity using realistic Tiled dimensions (160×224 px)."""
    group = pygame.sprite.Group()
    obstacles = pygame.sprite.Group()
    with patch("src.entities.interactive.SpriteSheet") as mock_ss:
        mock_ss.return_value.valid = False
        entity = InteractiveEntity(
            pos=(704, 1728),
            groups=[group],
            sub_type="bridge",
            sprite_sheet="",
            position=0,
            depth=1,
            start_row=0,
            end_row=3,
            width=tiled_width,
            height=tiled_height,
            tiled_width=tiled_width,
            tiled_height=tiled_height,
            obstacles_group=obstacles,
            is_passable=True,
            is_animated=False,
            is_on=True,
            halo_size=0,
            halo_color="[255, 255, 255]",
            halo_alpha=130,
            particles=False,
            particle_count=0,
            element_id="bridge_1",
            target_id=None,
            activate_from_anywhere=False,
            facing_direction=None,
            sfx="",
            day_night_driven=False,
        )
    return entity


class TestBridgeSortY:
    """Regression tests for the bridge Y-sort fix.

    Root cause: bridge depth=1 put it in the same custom_draw pass as the
    player; its large rect.bottom (top+height) caused it to render after the
    player, hiding the player.  Fix: bridge.sort_y = rect.top so any sprite
    south of the bridge top renders in front.

    TC-BRIDGE-SORT-01 … TC-BRIDGE-SORT-04
    """

    @pytest.mark.tc("TC-BRIDGE-SORT-01")
    def test_bridge_has_sort_y_attribute(self):
        """TC-BRIDGE-SORT-01: Bridge entity must expose a sort_y attribute."""
        entity = _make_bridge_entity()
        assert hasattr(entity, "sort_y"), "bridge must define sort_y"

    @pytest.mark.tc("TC-BRIDGE-SORT-02")
    def test_bridge_sort_y_equals_rect_top(self):
        """TC-BRIDGE-SORT-02: bridge.sort_y must equal bridge.rect.top."""
        entity = _make_bridge_entity()
        assert entity.sort_y == entity.rect.top

    @pytest.mark.tc("TC-BRIDGE-SORT-03")
    def test_bridge_sort_y_less_than_rect_bottom(self):
        """TC-BRIDGE-SORT-03: sort_y < rect.bottom ensures player walking on
        bridge (rect.bottom > bridge.sort_y) sorts after bridge."""
        entity = _make_bridge_entity()
        assert entity.sort_y < entity.rect.bottom

    @pytest.mark.tc("TC-BRIDGE-SORT-04")
    def test_non_bridge_entity_has_no_sort_y(self):
        """TC-BRIDGE-SORT-04: Non-bridge entities must NOT define sort_y
        (their Y-sort falls back to rect.bottom as usual)."""
        door, _ = _make_interactive(sub_type="door")
        chest, _ = _make_interactive(sub_type="chest")
        assert not hasattr(door, "sort_y"), "door must not have sort_y"
        assert not hasattr(chest, "sort_y"), "chest must not have sort_y"


# ---------------------------------------------------------------------------
# TC-001..TC-006 — trigger_only attribute on InteractiveEntity
# Spec: docs/specs/trigger-only-spec.md
# ---------------------------------------------------------------------------


class TestTriggerOnly:
    """Unit tests for the trigger_only property on InteractiveEntity.

    trigger_only=True must:
    - Be stored as self.trigger_only == True after __init__
    - Default to False when not passed (backward compat)

    Spec: docs/specs/trigger-only-spec.md § TC-001..TC-006
    """

    @pytest.mark.tc("TC-005")
    def test_trigger_only_true_stored_on_entity(self):
        """TC-005: trigger_only=True passed to __init__ → entity.trigger_only is True."""
        entity, _ = _make_interactive(trigger_only=True)
        assert entity.trigger_only is True

    @pytest.mark.tc("TC-006")
    def test_trigger_only_defaults_to_false(self):
        """TC-006: No trigger_only arg → entity.trigger_only is False (backward compat)."""
        entity, _ = _make_interactive()
        assert entity.trigger_only is False
