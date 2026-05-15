"""Regression tests for NPC stuck-and-spinning bug (debug room, Tiled ID=23).

Root causes identified:
  BUG-1: entity_factory.spawn_npc() never sets npc.game = self.game
          → BaseEntity.start_move() falls back to MAP_SIZE (32) boundary
          → NPC at y=1168 in a 40-tile-high map has every target clamped to
            y=1008, which lands on non-walkable wall tiles → NPC cannot move.

  BUG-2: NPC.start_move() does not clear self.direction when the move is
          blocked by walkable_func or boundary clamping
          → BaseEntity.move() retries start_move() every frame
          → visual "spinning" (current_facing changes, no actual movement).
"""

from unittest.mock import MagicMock, patch

import pygame
import pytest

from src.config import Settings


@pytest.fixture(autouse=True)
def pygame_init(setup_pygame):
    yield


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_npc(pos=(100, 100), wander_radius=1):
    from src.entities.npc import NPC

    with patch("src.entities.npc.SpriteSheet") as mock_ss:
        mock_ss.return_value.load_grid.return_value = [
            pygame.Surface((32, 32)) for _ in range(16)
        ]
        npc = NPC(pos=pos, wander_radius=wander_radius)
    return npc


def _make_ef_with_game():
    """Build an EntityFactory backed by a minimal mock Game."""
    from src.engine.entity_factory import EntityFactory

    game = MagicMock()
    game.visible_sprites = MagicMock()
    game.npcs = pygame.sprite.Group()
    game.obstacles_group = pygame.sprite.Group()
    game.world_state.get.return_value = None
    game.tile_size = 32
    game._current_map_name = "test.tmj"
    game.interaction_manager.is_walkable = lambda x, y, **kw: True
    return EntityFactory(game), game


# ---------------------------------------------------------------------------
# BUG-1 : spawn_npc must set npc.game
# ---------------------------------------------------------------------------

class TestSpawnNpcSetsGame:
    """BUG-1: EntityFactory.spawn_npc() must assign npc.game = self.game."""

    def test_spawn_npc_sets_game_reference(self):
        """npc.game must reference the game instance after spawning."""
        ef, game = _make_ef_with_game()
        ent = {"x": 100, "y": 100, "id": 7, "name": "TestNpc"}
        props = {"sprite_sheet": "01-character.png", "element_id": "test_npc"}

        with patch("src.engine.entity_factory.NPC") as MockNPC:
            inst = MagicMock()
            inst.rect = pygame.Rect(0, 0, 32, 32)
            inst.pos = pygame.math.Vector2(116, 116)
            inst.target_pos = pygame.math.Vector2(116, 116)
            inst._world_state_key = None
            MockNPC.return_value = inst

            ef.spawn_npc(ent, props)

        # BUG-1: this assertion currently FAILS — game is never set
        assert inst.game is game, (
            "spawn_npc() must set npc.game = self.game; "
            "without it, boundary clamping uses MAP_SIZE instead of actual map size."
        )

    def test_npc_without_game_clamps_y_to_wrong_boundary(self):
        """Regression: npc.game=None causes boundary = MAP_SIZE*TILE_SIZE = 1024.

        A NPC placed at y=1168 (valid in a 40-tile-high map) has ALL movement
        targets clamped to y ≤ 1008, which lands on non-walkable tiles.
        """
        npc = _make_npc(pos=(208, 1168), wander_radius=5)
        npc.game = None  # simulate the bug: game not set

        blocked_calls = []

        def tracking_walkable(x, y, **kw):
            blocked_calls.append((x, y))
            return False  # always block to surface the clamping issue

        npc.walkable_func = tracking_walkable
        npc.direction = pygame.math.Vector2(0, 1)  # try moving down

        npc.start_move()

        assert blocked_calls, "walkable_func should have been called"
        # With the bug, y is clamped: checked y must be ≤ MAP_SIZE*TILE_SIZE-half = 1008
        checked_y = blocked_calls[0][1]
        wrong_boundary = Settings.MAP_SIZE * Settings.TILE_SIZE - Settings.TILE_SIZE // 2
        assert checked_y <= wrong_boundary, (
            f"y={checked_y} exceeds wrong boundary {wrong_boundary}: "
            "NPC movement target was NOT clamped as expected by the bug"
        )
        # And the original target y=1200 should NOT have been checked
        assert checked_y != 1200, (
            "The correct target y=1200 was checked — bug may already be fixed"
        )


# ---------------------------------------------------------------------------
# BUG-2 : NPC.start_move() must clear direction on blocked move
# ---------------------------------------------------------------------------

class TestNpcStartMoveClearsDirectionWhenBlocked:
    """BUG-2: direction must be zeroed when walkable_func blocks movement."""

    def test_direction_cleared_when_walkable_func_blocks(self):
        """After a blocked walkable_func, direction must be Vector2(0,0).

        Without this fix, BaseEntity.move() retries start_move() every frame,
        causing visual spinning (current_facing changes each AI cooldown).
        """
        npc = _make_npc(pos=(208, 1168), wander_radius=5)
        npc.walkable_func = lambda x, y, **kw: False  # always block
        npc.direction = pygame.math.Vector2(1, 0)
        # Ensure radius check passes
        npc.spawn_pos = pygame.math.Vector2(208, 1168)

        npc.start_move()

        # BUG-2: currently FAILS — direction is not cleared on blocked move
        assert npc.direction.magnitude() == 0, (
            "direction must be cleared after a blocked move so that "
            "BaseEntity.move() does not retry start_move() every frame."
        )
        assert not npc.is_moving
        assert npc.state == "idle"

    def test_move_does_not_retry_start_move_after_blocked(self):
        """After a blocked move, calling move() should NOT retry start_move()."""
        npc = _make_npc(pos=(208, 1168), wander_radius=5)
        npc.spawn_pos = pygame.math.Vector2(208, 1168)
        call_count = {"n": 0}

        original_start = npc.start_move

        def counting_start():
            call_count["n"] += 1
            original_start()

        npc.walkable_func = lambda x, y, **kw: False  # block all moves
        npc.direction = pygame.math.Vector2(1, 0)

        # First call: blocks and (with fix) clears direction
        npc.start_move = counting_start
        npc.start_move()

        # If direction was cleared, move() should NOT call start_move again
        count_before = call_count["n"]
        npc.move(0.016)
        assert call_count["n"] == count_before, (
            "move() must NOT retry start_move() after a blocked move "
            "(direction was not cleared — BUG-2 still present)."
        )
