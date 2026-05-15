"""RED tests for Phase 1.5 — CollisionChecker.

TC-CC-01..TC-CC-07, IT-CC-01 from docs/specs/phase-1.5-interaction-refactoring.md
"""

from unittest.mock import MagicMock

import pygame
import pytest

from src.engine.collision_checker import CollisionChecker

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_game():
    game = MagicMock()
    game.layout.to_world.return_value = (5, 5)
    game.map_manager.is_walkable.return_value = True
    game.obstacles_group = []
    game.npcs = []
    game.player.rect = None
    return game


def _make_rect_obj(x=64, y=64, size=32):
    obj = MagicMock()
    obj.rect = pygame.Rect(x, y, size, size)
    return obj


# ---------------------------------------------------------------------------
# TC-CC-01 — tile collidable → True
# ---------------------------------------------------------------------------


@pytest.mark.tc("TC-CC-01")
def test_tile_not_walkable_returns_true():
    game = _make_game()
    game.map_manager.is_walkable.return_value = False
    cc = CollisionChecker(game)
    assert cc.check(80, 80) is True


# ---------------------------------------------------------------------------
# TC-CC-02 — obstacle at position → True
# ---------------------------------------------------------------------------


@pytest.mark.tc("TC-CC-02")
def test_obstacle_blocks():
    game = _make_game()
    obstacle = _make_rect_obj(64, 64, 32)
    game.obstacles_group = [obstacle]
    cc = CollisionChecker(game)
    # px_center=80, py_center=80 → inside rect (64..96, 64..96)
    assert cc.check(80, 80) is True


# ---------------------------------------------------------------------------
# TC-CC-03 — obstacle skipped if requester
# ---------------------------------------------------------------------------


@pytest.mark.tc("TC-CC-03")
def test_obstacle_skipped_if_requester():
    game = _make_game()
    obstacle = _make_rect_obj(64, 64, 32)
    game.obstacles_group = [obstacle]
    cc = CollisionChecker(game)
    # Obstacle IS the requester → skipped → not collidable
    assert cc.check(80, 80, requester=obstacle) is False


# ---------------------------------------------------------------------------
# TC-CC-04 — NPC at position → True
# ---------------------------------------------------------------------------


@pytest.mark.tc("TC-CC-04")
def test_npc_blocks():
    game = _make_game()
    npc = _make_rect_obj(64, 64, 32)
    game.npcs = [npc]
    cc = CollisionChecker(game)
    assert cc.check(80, 80) is True


# ---------------------------------------------------------------------------
# TC-CC-05 — NPC skipped if requester
# ---------------------------------------------------------------------------


@pytest.mark.tc("TC-CC-05")
def test_npc_skipped_if_requester():
    game = _make_game()
    npc = _make_rect_obj(64, 64, 32)
    game.npcs = [npc]
    cc = CollisionChecker(game)
    assert cc.check(80, 80, requester=npc) is False


# ---------------------------------------------------------------------------
# TC-CC-06 — player blocks NPC (requester != player)
# ---------------------------------------------------------------------------


@pytest.mark.tc("TC-CC-06")
def test_player_blocks_npc():
    game = _make_game()
    npc = MagicMock()  # requester is this NPC
    game.player.rect = pygame.Rect(64, 64, 32, 32)
    cc = CollisionChecker(game)
    assert cc.check(80, 80, requester=npc) is True


# ---------------------------------------------------------------------------
# TC-CC-07 — nothing blocks → False
# ---------------------------------------------------------------------------


@pytest.mark.tc("TC-CC-07")
def test_nothing_blocks_returns_false():
    game = _make_game()
    cc = CollisionChecker(game)
    # No obstacles, no npcs, player.rect=None → False
    assert cc.check(80, 80) is False


# ---------------------------------------------------------------------------
# IT-CC-01 — CollisionChecker.check called via is_collidable wrapper
# ---------------------------------------------------------------------------


@pytest.mark.tc("IT-CC-01")
def test_is_walkable_delegates_to_collision_checker():
    """InteractionManager.is_walkable must delegate to CollisionChecker.check."""
    from src.engine.interaction import InteractionManager

    game = _make_game()
    im = InteractionManager(game)

    # Patch the internal collision checker
    im._collision_checker = MagicMock()
    im._collision_checker.check.return_value = True

    result = im.is_walkable(80, 80, requester=None)

    im._collision_checker.check.assert_called_once_with(80, 80, None)
    assert result is False
