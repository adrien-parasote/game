"""Tests for InteractionEmoteMixin (src/engine/interaction_emote.py).

Covers: cooldown gate, interactive emote triggered/skipped, pickup emote,
        NPC emote triggered/skipped, trigger_only exclusion, emote cooldown reset.
"""
# TC traceability: entities-system.md §InteractionEmoteMixin
# TC IDs to be assigned when spec test case table is added.

from unittest.mock import MagicMock

import pygame
import pytest
from src.engine.interaction_emote import InteractionEmoteMixin

# ── Minimal concrete class ─────────────────────────────────────────────────────


class _FakeMgr(InteractionEmoteMixin):
    """Minimal concrete implementation to test the mixin."""

    def __init__(self, game):
        self.game = game
        self._emote_cooldown = 0
        self._last_proximity_target = None


def _make_game(player_pos=(100, 100), player_state="down"):
    game = MagicMock()
    game.player.pos = pygame.math.Vector2(*player_pos)
    game.player.current_state = player_state
    game.player.is_moving = False
    game.interactives = []
    game.pickups = []
    game.npcs = []
    return game


def _make_obj(
    pos=(100, 110),
    is_on=False,
    is_passable=False,
    activate_from_anywhere=False,
    sub_type="lever",
    trigger_only=False,
):
    """Build a minimal interactive object at a given position."""
    obj = MagicMock()
    obj.pos = pygame.math.Vector2(*pos)
    obj.is_on = is_on
    obj.is_passable = is_passable
    obj.activate_from_anywhere = activate_from_anywhere
    obj.sub_type = sub_type
    obj.trigger_only = trigger_only
    return obj


# ── Cooldown gate ──────────────────────────────────────────────────────────────


def test_check_proximity_emotes_skips_when_cooldown_active():
    """_check_proximity_emotes() must return immediately when _emote_cooldown > 0."""
    game = _make_game()
    mgr = _FakeMgr(game)
    mgr._emote_cooldown = 1  # active cooldown

    # Put an object in range
    obj = _make_obj()
    game.interactives = [obj]

    mgr._check_proximity_emotes()

    # playerEmote must NOT be called
    game.player.playerEmote.assert_not_called()


# ── Interactive emote ──────────────────────────────────────────────────────────


def test_interactive_emote_triggered_when_in_range():
    """Player within 48px of a valid interactive → playerEmote('interact') called."""
    game = _make_game(player_pos=(100, 100))
    mgr = _FakeMgr(game)

    # Object 10px below player — well within 48px range
    obj = _make_obj(pos=(100, 110), is_on=False, activate_from_anywhere=True)
    game.interactives = [obj]

    mgr._check_interactive_emote()

    game.player.playerEmote.assert_called_once_with("interact")


def test_interactive_emote_not_triggered_when_out_of_range():
    """Player >48px away → no emote triggered."""
    game = _make_game(player_pos=(0, 0))
    mgr = _FakeMgr(game)

    obj = _make_obj(pos=(500, 500))
    game.interactives = [obj]

    result = mgr._check_interactive_emote()

    assert result is False
    game.player.playerEmote.assert_not_called()


def test_trigger_only_object_skipped():
    """trigger_only=True objects are excluded from interactive emote logic."""
    game = _make_game(player_pos=(100, 100))
    mgr = _FakeMgr(game)

    obj = _make_obj(pos=(100, 110), trigger_only=True, activate_from_anywhere=True)
    game.interactives = [obj]

    result = mgr._check_interactive_emote()

    assert result is False
    game.player.playerEmote.assert_not_called()


def test_open_chest_or_door_skipped():
    """is_on=True chest/door must not trigger the interact emote (already open)."""
    game = _make_game(player_pos=(100, 100))
    mgr = _FakeMgr(game)

    obj = _make_obj(pos=(100, 110), is_on=True, sub_type="chest", activate_from_anywhere=True)
    game.interactives = [obj]

    result = mgr._check_interactive_emote()

    # Open chest → skipped
    assert result is False


# ── Pickup emote ───────────────────────────────────────────────────────────────


def test_pickup_emote_triggered_when_in_range():
    """Player within 48px of a pickup → playerEmote('question') called."""
    game = _make_game(player_pos=(100, 100))
    mgr = _FakeMgr(game)

    pickup = MagicMock()
    pickup.pos = pygame.math.Vector2(100, 110)  # 10px below
    game.pickups = [pickup]

    result = mgr._check_pickup_emote()

    assert result is True
    game.player.playerEmote.assert_called_once_with("question")


def test_pickup_emote_not_triggered_when_out_of_range():
    """Pickup >48px away → no emote."""
    game = _make_game(player_pos=(0, 0))
    mgr = _FakeMgr(game)

    pickup = MagicMock()
    pickup.pos = pygame.math.Vector2(500, 500)
    game.pickups = [pickup]

    result = mgr._check_pickup_emote()

    assert result is False
    game.player.playerEmote.assert_not_called()


# ── NPC emote ─────────────────────────────────────────────────────────────────


def test_npc_emote_resets_target_when_nothing_in_range():
    """_check_npc_emote() must reset _last_proximity_target when no NPC in range."""
    game = _make_game(player_pos=(0, 0))
    mgr = _FakeMgr(game)
    old_target = MagicMock()
    mgr._last_proximity_target = old_target

    npc = MagicMock()
    npc.pos = pygame.math.Vector2(500, 500)  # far away
    game.npcs = [npc]

    mgr._check_npc_emote()

    assert mgr._last_proximity_target is None
