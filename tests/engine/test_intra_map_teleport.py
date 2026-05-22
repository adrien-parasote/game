"""RED tests — Intra-Map Teleport & Walk Transition.

Spec: docs/specs/intra-map-teleport.md
Tests: TC-001..TC-010 (unit) + IT-001..IT-003 (integration)

These tests MUST fail (RED) before any implementation is written.
"""

import logging
from unittest.mock import MagicMock, call, patch

import pygame
import pytest

from src.engine.interaction import InteractionManager

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _make_game():
    """Construct a Game instance with _load_map patched out."""
    with patch("src.engine.game.Game._load_map"):
        from src.engine.game import Game
        return Game()


def _make_map_loader(entities=None):
    """Build a MapLoader with a minimal game context."""
    from src.engine.map_loader import MapLoader

    game = MagicMock()
    game.tile_size = 32
    game.map_manager._entities = entities or []
    return MapLoader(game)


def _spawn_entity(spawn_id: str, x: int, y: int) -> dict:
    """Helper: build a minimal spawn_point entity dict as TmjParser would produce."""
    return {
        "type": "14-spawn_point",
        "x": x,
        "y": y,
        "properties": {"spawn_id": spawn_id},
    }


# ===========================================================================
# TC-001 — instant teleport repositions player, no _load_map call
# ===========================================================================


@patch("src.engine.game.Game._load_map")
@pytest.mark.tc("TC-001")
def test_intra_map_teleport_instant_repositions_player(mock_load):
    """TC-001: intra_map_teleport("spawn_a", "instant") moves player to spawn_a coords
    and does NOT call _load_map (no map reload).
    """
    game = _make_game()

    # Patch resolve_spawn_by_id to return a known pixel position
    spawn_px = (128, 256)
    game._map_loader.resolve_spawn_by_id = MagicMock(return_value=spawn_px)
    mock_load.reset_mock()

    game.intra_map_teleport("spawn_a", "instant")

    # Player must be at the spawn position
    assert game.player.pos == pygame.math.Vector2(spawn_px)
    # _load_map must NOT have been called
    mock_load.assert_not_called()


# ===========================================================================
# TC-002 — walk teleport sets _intra_walk_target, target_pos, is_moving
# ===========================================================================


@patch("src.engine.game.Game._load_map")
@pytest.mark.tc("TC-002")
def test_intra_map_teleport_walk_sets_walk_state(mock_load):
    """TC-002: intra_map_teleport("spawn_b", "walk") sets _intra_walk_target,
    updates player.target_pos to the destination, and sets player.is_moving = True.
    """
    game = _make_game()

    spawn_px = (200, 300)
    game._map_loader.resolve_spawn_by_id = MagicMock(return_value=spawn_px)

    game.intra_map_teleport("spawn_b", "walk")

    # Walk state must be armed
    assert game._intra_walk_target == pygame.math.Vector2(spawn_px)
    # player.target_pos and is_moving set by _start_intra_walk
    assert game.player.target_pos == pygame.math.Vector2(spawn_px)
    assert game.player.is_moving is True


# ===========================================================================
# TC-003 — unknown spawn_id: logs error, player pos unchanged
# ===========================================================================


@patch("src.engine.game.Game._load_map")
@pytest.mark.tc("TC-003")
def test_intra_map_teleport_unknown_spawn_logs_error_and_returns(mock_load, caplog):
    """TC-003: When resolve_spawn_by_id returns None, intra_map_teleport logs an error
    and does NOT move the player or set the walk state.
    """
    game = _make_game()
    game._map_loader.resolve_spawn_by_id = MagicMock(return_value=None)

    original_pos = pygame.math.Vector2(game.player.pos)

    with caplog.at_level(logging.ERROR):
        game.intra_map_teleport("nonexistent", "walk")

    # Player position must be unchanged
    assert game.player.pos == original_pos
    # Walk state must NOT be armed
    assert getattr(game, "_intra_walk_target", None) is None
    # Error must be logged
    assert any("nonexistent" in r.message for r in caplog.records)


# ===========================================================================
# TC-004 — resolve_spawn_by_id finds correct entity by spawn_id
# ===========================================================================


@pytest.mark.tc("TC-004")
def test_resolve_spawn_by_id_finds_correct_entity():
    """TC-004: resolve_spawn_by_id("door_exit") reads map_manager._entities,
    finds the spawn_point with spawn_id="door_exit", and returns (x + half_tile, y + half_tile).
    """
    ml = _make_map_loader(entities=[
        _spawn_entity("wrong_spawn", 0, 0),
        _spawn_entity("door_exit", 64, 96),
    ])

    result = ml.resolve_spawn_by_id("door_exit")

    # half_tile = 32 // 2 = 16
    assert result == (64 + 16, 96 + 16)


# ===========================================================================
# TC-005 — resolve_spawn_by_id returns None on miss, logs warning
# ===========================================================================


@pytest.mark.tc("TC-005")
def test_resolve_spawn_by_id_returns_none_on_miss(caplog):
    """TC-005: No entity with the matching spawn_id → returns None and logs a warning."""
    ml = _make_map_loader(entities=[
        _spawn_entity("other_spawn", 10, 10),
    ])

    with caplog.at_level(logging.WARNING):
        result = ml.resolve_spawn_by_id("missing_spawn")

    assert result is None
    assert any("missing_spawn" in r.message for r in caplog.records)


# ===========================================================================
# TC-006 — _tick_intra_walk updates player.current_state (facing direction)
# ===========================================================================


@patch("src.engine.game.Game._load_map")
@pytest.mark.tc("TC-006")
def test_tick_intra_walk_updates_facing_direction(mock_load):
    """TC-006: _tick_intra_walk(dt) updates player.current_state based on the
    remaining delta vector to _intra_walk_target (G4 — facing follows walk direction).
    """
    game = _make_game()
    # Place player at (100, 100), target due-right at (200, 100)
    game.player.pos = pygame.math.Vector2(100, 100)
    game._intra_walk_target = pygame.math.Vector2(200, 100)
    game.player.is_moving = True

    game._tick_intra_walk(0.016)

    assert game.player.current_state == "right"


# ===========================================================================
# TC-007 — _tick_intra_walk terminates when player.is_moving is False
# ===========================================================================


@patch("src.engine.game.Game._load_map")
@pytest.mark.tc("TC-007")
def test_tick_intra_walk_terminates_on_arrival(mock_load):
    """TC-007: When player.is_moving becomes False (player.move() reached target_pos),
    _tick_intra_walk clears _intra_walk_target and resets player.direction to (0, 0).
    """
    game = _make_game()
    target = pygame.math.Vector2(300, 200)
    game._intra_walk_target = target
    # Simulate arrival: player.move() already set is_moving = False
    game.player.is_moving = False
    game.player.pos = pygame.math.Vector2(target)

    game._tick_intra_walk(0.016)

    assert game._intra_walk_target is None
    assert game.player.direction == pygame.math.Vector2(0, 0)


# ===========================================================================
# TC-008 — facing horizontal: walk left → current_state == "left"
# ===========================================================================


@patch("src.engine.game.Game._load_map")
@pytest.mark.tc("TC-008")
def test_tick_intra_walk_updates_facing_horizontal(mock_load):
    """TC-008: Player walking left (target.x < player.x) → current_state = "left"."""
    game = _make_game()
    game.player.pos = pygame.math.Vector2(200, 100)
    game._intra_walk_target = pygame.math.Vector2(50, 100)  # left
    game.player.is_moving = True

    game._tick_intra_walk(0.016)

    assert game.player.current_state == "left"


# ===========================================================================
# TC-009 — facing vertical: walk up → current_state == "up"
# ===========================================================================


@patch("src.engine.game.Game._load_map")
@pytest.mark.tc("TC-009")
def test_tick_intra_walk_updates_facing_vertical(mock_load):
    """TC-009: Player walking up (target.y < player.y) → current_state = "up"."""
    game = _make_game()
    game.player.pos = pygame.math.Vector2(100, 300)
    game._intra_walk_target = pygame.math.Vector2(100, 50)  # up
    game.player.is_moving = True

    game._tick_intra_walk(0.016)

    assert game.player.current_state == "up"


# ===========================================================================
# TC-010 — _update_core_state blocks player.input() during walk
# ===========================================================================


@patch("src.engine.game.Game._load_map")
@pytest.mark.tc("TC-010")
def test_update_core_state_blocks_input_during_walk(mock_load):
    """TC-010: When _intra_walk_target is set, the normal update path is skipped —
    player.input() must NOT be called (G2: all inputs blocked during scripted walk).
    """
    game = _make_game()
    # Arm the walk state
    game._intra_walk_target = pygame.math.Vector2(200, 200)
    game.player.is_moving = True
    game.player.input = MagicMock()

    # Replace tick with a no-op so the test isolates only the routing logic
    game._tick_intra_walk = MagicMock()
    game.visible_sprites = MagicMock()
    game.interaction_manager = MagicMock()

    game._update_core_state(0.016)

    game.player.input.assert_not_called()
    game._tick_intra_walk.assert_called_once_with(0.016)


# ===========================================================================
# IT-001 — check_teleporters routes intra-map to intra_map_teleport()
# ===========================================================================


@pytest.mark.tc("IT-001")
def test_check_teleporters_routes_intra_map():
    """IT-001: When teleport.target_map == game._current_map_name,
    check_teleporters() calls game.intra_map_teleport(), NOT game.transition_map().
    """
    game = MagicMock()
    game._current_map_name = "castle.tmj"
    game.player.rect = pygame.Rect(0, 0, 32, 32)
    game.player.is_moving = False
    game.player.current_state = "up"

    im = InteractionManager(game)

    # Build a teleport that overlaps with the player and targets the SAME map
    tp = MagicMock()
    tp.rect = pygame.Rect(0, 0, 32, 32)  # collides with player
    tp.target_map = "castle.tmj"         # SAME as _current_map_name
    tp.target_spawn_id = "inner_door"
    tp.transition_type = "walk"
    tp.required_direction = "any"
    tp.sfx = None

    game.teleports_group = [tp]

    im.check_teleporters(was_moving=True)

    game.intra_map_teleport.assert_called_once_with("inner_door", "walk")
    game.transition_map.assert_not_called()


# ===========================================================================
# IT-002 — check_teleporters routes cross-map to transition_map() (regression)
# ===========================================================================


@pytest.mark.tc("IT-002")
def test_check_teleporters_routes_cross_map():
    """IT-002 (regression): When target_map != _current_map_name,
    check_teleporters() still calls game.transition_map() as before.
    """
    game = MagicMock()
    game._current_map_name = "village.tmj"
    game.player.rect = pygame.Rect(0, 0, 32, 32)
    game.player.is_moving = False
    game.player.current_state = "up"

    im = InteractionManager(game)

    tp = MagicMock()
    tp.rect = pygame.Rect(0, 0, 32, 32)
    tp.target_map = "dungeon.tmj"        # DIFFERENT map
    tp.target_spawn_id = "spawn_1"
    tp.transition_type = "fade"
    tp.required_direction = "any"
    tp.sfx = None

    game.teleports_group = [tp]

    im.check_teleporters(was_moving=True)

    game.transition_map.assert_called_once_with("dungeon.tmj", "spawn_1", "fade")
    game.intra_map_teleport.assert_not_called()


# ===========================================================================
# IT-003 — full walk cycle terminates: _intra_walk_target cleared after arrival
# ===========================================================================


@patch("src.engine.game.Game._load_map")
@pytest.mark.tc("IT-003")
def test_full_walk_cycle_terminates(mock_load):
    """IT-003: Simulating a complete walk cycle — after player.is_moving becomes False,
    _intra_walk_target is cleared and the walk ends cleanly.

    This exercises the pipeline: _start_intra_walk → _tick_intra_walk (arrival) → terminated.
    """
    game = _make_game()
    spawn_px = (160, 192)
    target_vec = pygame.math.Vector2(spawn_px)

    # Simulate _start_intra_walk being called
    game._intra_walk_target = target_vec
    game.player.target_pos = target_vec
    game.player.is_moving = True

    # Now simulate that in this same frame, player.move() finishes (is_moving → False)
    game.player.is_moving = False
    game.player.pos = pygame.math.Vector2(spawn_px)

    game._tick_intra_walk(0.016)

    # Walk must be terminated
    assert game._intra_walk_target is None
    # Player direction must be cleared (A-GAME-003)
    assert game.player.direction == pygame.math.Vector2(0, 0)
