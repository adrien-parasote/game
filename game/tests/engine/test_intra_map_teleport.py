"""RED tests — Intra-Map Teleport & Walk Transition.

Spec: game/docs/specs/intra-map-teleport.md
Tests: TC-001..TC-010 (unit) + IT-001..IT-003 (integration)

These tests MUST fail (RED) before any implementation is written.
"""

import logging
from unittest.mock import MagicMock, patch

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


# ===========================================================================
# TC-011 — player sprite is invisible (alpha=0) during scripted walk
# ===========================================================================


@patch("src.engine.game.Game._load_map")
@pytest.mark.tc("TC-011")
def test_player_invisible_during_walk(mock_load):
    """TC-011: While _intra_walk_target is set, player.image must be fully transparent.

    Uses _update_core_state with walk armed via intra_map_teleport() — verifies
    player.image is the dedicated transparent surface (not a spritesheet frame).
    This MUST NOT contaminate spritesheet frame surfaces.
    """
    game = _make_game()
    spawn_px = (300, 300)
    game._map_loader.resolve_spawn_by_id = MagicMock(return_value=spawn_px)

    # Arm walk via the real path so _player_transparent is lazy-created
    game.intra_map_teleport("spawn_x", "walk")
    assert game._intra_walk_target is not None, "Walk must be armed"

    # Patch subsystems so _update_core_state runs only the walk branch
    game._tick_intra_walk = MagicMock()
    game.visible_sprites = MagicMock()
    game.player.is_moving = True  # still walking

    game._update_core_state(0.016)

    # player.image must now be the dedicated transparent surface
    assert game.player.image is game._player_transparent, (
        "player.image must be _player_transparent during walk"
    )
    # And it must be fully transparent (SRCALPHA fill=(0,0,0,0))
    assert game.player.image.get_at((0, 0)).a == 0, (
        "Transparent surface pixel alpha must be 0"
    )



# ===========================================================================
# TC-012 — spritesheet frames NOT contaminated after walk
# ===========================================================================


@patch("src.engine.game.Game._load_map")
@pytest.mark.tc("TC-012")
def test_spritesheet_frames_not_contaminated_after_walk(mock_load):
    """TC-012: After walk ends, player.frames surfaces retain their original alpha.

    Walks for 1 tick (is_moving=True), then arrival tick (is_moving=False).
    All frame surfaces in player.frames must still have their original alpha —
    none should be permanently transparent.
    """
    game = _make_game()
    # Record original alpha of all frames
    original_alphas = [
        (f.get_alpha(), f.get_at((0, 0)).a if f.get_alpha() is None else None)
        for f in game.player.frames
    ]

    game._intra_walk_target = pygame.math.Vector2(300, 300)
    game.player.is_moving = True
    game._tick_intra_walk = MagicMock()
    game.visible_sprites = MagicMock()

    # Tick 1: walk in progress
    game._update_core_state(0.016)

    # Simulate arrival
    game._intra_walk_target = None

    # Verify frames are unchanged
    for i, frame in enumerate(game.player.frames):
        orig_alpha, orig_pixel_a = original_alphas[i]
        if orig_alpha is None:
            # Per-pixel alpha frame — pixel alpha should be unchanged
            current_pixel_a = frame.get_at((0, 0)).a
            assert current_pixel_a == orig_pixel_a, (
                f"Frame {i} pixel alpha contaminated: expected {orig_pixel_a}, "
                f"got {current_pixel_a}"
            )
        else:
            assert frame.get_alpha() == orig_alpha, (
                f"Frame {i} surface alpha contaminated: expected {orig_alpha}, "
                f"got {frame.get_alpha()}"
            )


# ===========================================================================
# TC-013 — player sprite is visible again after walk arrival
# ===========================================================================


@patch("src.engine.game.Game._load_map")
@pytest.mark.tc("TC-013")
def test_player_visible_after_walk_arrival(mock_load):
    """TC-013: After _tick_intra_walk terminates the walk (is_moving=False),
    player.image must NOT be the transparent surface — visibility is restored.

    Simulates: walk tick (player invisible) → arrival tick (_intra_walk_target=None)
    → _update_core_state normal path → player.image is the normal animation frame.
    """
    game = _make_game()
    target = pygame.math.Vector2(200, 200)
    spawn_px = (200, 200)
    game._map_loader.resolve_spawn_by_id = MagicMock(return_value=spawn_px)

    # Arm walk
    game.intra_map_teleport("spawn_x", "walk")

    # Simulate arrival: player.move() set is_moving=False
    game.player.is_moving = False
    game.player.pos = pygame.math.Vector2(spawn_px)

    # Tick the walk — this should clear _intra_walk_target
    game._tick_intra_walk(0.016)

    assert game._intra_walk_target is None, "Walk target must be cleared on arrival"

    # Now run a normal _update_core_state tick
    game._tick_intra_walk = MagicMock()  # prevent re-arming
    game.visible_sprites = MagicMock()
    game.interaction_manager = MagicMock()
    game.player.input = MagicMock()

    game._update_core_state(0.016)

    # player.image must NOT be the transparent surface
    # get_alpha() on a real animation frame is None (per-pixel) or 255
    alpha = game.player.image.get_alpha()
    if alpha is None:
        # Per-pixel surface: pixel alpha should be > 0 (not the transparent placeholder)
        pixel_a = game.player.image.get_at((0, 0)).a
        # We can't guarantee non-zero pixel alpha for black pixels in the spritesheet,
        # but we CAN guarantee player.image is not the dedicated transparent surface
        assert game.player.image is not game._player_transparent, (
            "player.image must not be the transparent surface after walk ends"
        )
    else:
        assert alpha == 255, f"Expected alpha restored to 255, got {alpha}"
