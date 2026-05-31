"""Tests for directional SFX: sfx_open / sfx_close on chest, door, lever, and _close_chest().

Spec: game/docs/specs/sfx-migration-spec.md
Tests: TC-001, TC-002, IT-001, IT-002, IT-003
"""

from unittest.mock import ANY, MagicMock, patch

import pygame
import pytest
from src.engine.interaction import InteractionManager

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _ChestSprite(pygame.sprite.Sprite):
    """Minimal chest entity that mimics post-toggle is_on change."""

    def __init__(self, sfx_open="", sfx_close="", sfx="", initial_is_on=False):
        super().__init__()
        self.element_id = "test_chest"
        self.sfx = sfx
        self.sfx_open = sfx_open
        self.sfx_close = sfx_close
        self.is_on = initial_is_on
        self.sub_type = "chest"
        self.direction_str = "up"
        self.pos = pygame.math.Vector2(100, 120)
        self.rect = pygame.Rect(84, 104, 32, 32)
        self._world_state_key = "test_chest_key"
        self.target_id = None

    def interact(self, player=None):
        self.is_on = not self.is_on


class _DoorSprite(pygame.sprite.Sprite):
    """Minimal door entity."""

    def __init__(self, sfx_open="", sfx_close="", sfx="", initial_is_on=False):
        super().__init__()
        self.element_id = "test_door"
        self.sfx = sfx
        self.sfx_open = sfx_open
        self.sfx_close = sfx_close
        self.is_on = initial_is_on
        self.sub_type = "door"
        self.direction_str = "up"
        self.pos = pygame.math.Vector2(100, 120)
        self.rect = pygame.Rect(84, 104, 32, 32)
        self._world_state_key = "test_door_key"
        self.target_id = None
        self.is_passable = True

    def interact(self, player=None):
        self.is_on = not self.is_on


def _make_game_with_player_at(pos: tuple, facing: str = "down") -> MagicMock:
    game = MagicMock()
    game.player.pos = pygame.math.Vector2(*pos)
    game.player.current_state = facing
    game.player.is_moving = False
    game.npcs = pygame.sprite.Group()
    return game


# ---------------------------------------------------------------------------
# TC-001 — Auto-close chest plays sfx_close
# ---------------------------------------------------------------------------


@pytest.mark.tc("TC-001")
def test_close_chest_plays_sfx_close():
    """TC-001: _close_chest() uses _resolve_sfx() → returns sfx_close (is_on=False after interact)."""
    game = _make_game_with_player_at((500, 500))  # player far away → out of range
    chest = _ChestSprite(sfx_open="02-open_chest", sfx_close="02-open_chest", initial_is_on=True)

    im = InteractionManager(game)
    im._open_chest_entity = chest
    game.chest_ui.is_open = True
    game.player.pos = pygame.math.Vector2(500, 500)  # triggers out_of_range

    im._check_chest_auto_close()

    # chest.interact() flips is_on to False → _resolve_sfx must return sfx_close
    game.audio_manager.play_sfx.assert_called_once_with(
        "02-open_chest", "test_chest", volume_multiplier=ANY
    )


@pytest.mark.tc("TC-001")
def test_close_chest_does_not_use_sfx_attr_directly():
    """TC-001 regression: _close_chest() must NOT read chest.sfx directly — sfx attr is ''."""
    game = _make_game_with_player_at((500, 500))
    # sfx is empty (migrated), only sfx_close is set
    chest = _ChestSprite(sfx_open="02-open_chest", sfx_close="02-open_chest", sfx="", initial_is_on=True)

    im = InteractionManager(game)
    im._open_chest_entity = chest
    game.chest_ui.is_open = True

    im._check_chest_auto_close()

    # Must still play sound even though chest.sfx == ""
    assert game.audio_manager.play_sfx.called, (
        "_close_chest() is reading chest.sfx directly (always '') instead of calling _resolve_sfx()"
    )


@pytest.mark.tc("TC-001")
def test_close_chest_silent_when_no_sfx_set():
    """TC-001 edge: no sfx properties set → auto-close is silent, no exception."""
    game = _make_game_with_player_at((500, 500))
    chest = _ChestSprite(sfx_open="", sfx_close="", sfx="", initial_is_on=True)

    im = InteractionManager(game)
    im._open_chest_entity = chest
    game.chest_ui.is_open = True

    im._check_chest_auto_close()

    game.audio_manager.play_sfx.assert_not_called()


# ---------------------------------------------------------------------------
# TC-002 — Manual open chest plays sfx_open
# ---------------------------------------------------------------------------


@pytest.mark.tc("TC-002")
def test_open_chest_plays_sfx_open():
    """TC-002: Player opens chest → _trigger_object_interaction calls _resolve_sfx → sfx_open."""
    game = _make_game_with_player_at((100, 100))
    chest = _ChestSprite(sfx_open="02-open_chest", sfx_close="02-open_chest", initial_is_on=False)
    game.interactives = [chest]

    im = InteractionManager(game)

    with patch("pygame.key.get_pressed", return_value={__import__("src.config", fromlist=["Settings"]).Settings.INTERACT_KEY: True}):
        im.handle_interactions()

    # After interact(), is_on=True → _resolve_sfx returns sfx_open
    call_args = game.audio_manager.play_sfx.call_args
    assert call_args is not None, "play_sfx was not called — sfx_open not played on chest open"
    assert call_args[0][0] == "02-open_chest"
    assert call_args[0][1] == "test_chest"
    assert "volume_multiplier" in call_args[1]


@pytest.mark.tc("TC-002")
def test_open_chest_silent_when_no_sfx_open():
    """TC-002 edge: chest with no sfx properties → opening is silent."""
    game = _make_game_with_player_at((100, 100))
    chest = _ChestSprite(sfx_open="", sfx_close="", sfx="", initial_is_on=False)
    game.interactives = [chest]

    im = InteractionManager(game)

    with patch("pygame.key.get_pressed", return_value={__import__("src.config", fromlist=["Settings"]).Settings.INTERACT_KEY: True}):
        im.handle_interactions()

    game.audio_manager.play_sfx.assert_not_called()


# ---------------------------------------------------------------------------
# IT-001 — Open then auto-close plays sfx_open then sfx_close
# ---------------------------------------------------------------------------


@pytest.mark.tc("IT-001")
def test_chest_open_then_autoclose_plays_both_sfx():
    """IT-001: Open (sfx_open) then auto-close (sfx_close) — two calls in sequence."""
    from src.config import Settings

    game = _make_game_with_player_at((100, 100))
    chest = _ChestSprite(sfx_open="02-open_chest", sfx_close="02-open_chest", initial_is_on=False)
    game.interactives = [chest]
    game.chest_ui.is_open = False

    im = InteractionManager(game)

    # Step 1: Player opens chest
    with patch("pygame.key.get_pressed", return_value={Settings.INTERACT_KEY: True}):
        im.handle_interactions()

    # chest is now open (is_on=True), UI open
    game.chest_ui.is_open = True
    im._open_chest_entity = chest

    # Step 2: Player walks away → auto-close
    game.player.pos = pygame.math.Vector2(500, 500)
    im._check_chest_auto_close()

    assert game.audio_manager.play_sfx.call_count == 2, (
        f"Expected 2 play_sfx calls (open + close), got {game.audio_manager.play_sfx.call_count}"
    )
    calls = game.audio_manager.play_sfx.call_args_list
    assert calls[0][0][0] == "02-open_chest"  # sfx_open on open
    assert calls[1][0][0] == "02-open_chest"  # sfx_close on auto-close


# ---------------------------------------------------------------------------
# IT-002 — toggle_entity_by_id on chest plays correct sfx
# ---------------------------------------------------------------------------


@pytest.mark.tc("IT-002")
def test_toggle_chest_via_id_plays_sfx_open():
    """IT-002: Lever triggers chest via toggle_entity_by_id → chest plays sfx_open."""
    game = MagicMock()
    game.player.rect = pygame.Rect(0, 0, 32, 32)  # player away from chest

    chest = _ChestSprite(sfx_open="02-open_chest", sfx_close="02-open_chest", initial_is_on=False)

    game.interactives = pygame.sprite.Group(chest)
    game.npcs = pygame.sprite.Group()

    im = InteractionManager(game)
    im.toggle_entity_by_id("test_chest")

    # chest.is_on flipped to True → sfx_open
    game.audio_manager.play_sfx.assert_called_once_with("02-open_chest", "test_chest")


@pytest.mark.tc("IT-002")
def test_toggle_chest_via_id_plays_sfx_close():
    """IT-002: toggle_entity_by_id on open chest → chest plays sfx_close."""
    game = MagicMock()
    game.player.rect = pygame.Rect(0, 0, 32, 32)

    chest = _ChestSprite(sfx_open="02-open_chest", sfx_close="02-open_chest", initial_is_on=True)

    game.interactives = pygame.sprite.Group(chest)
    game.npcs = pygame.sprite.Group()

    im = InteractionManager(game)
    im.toggle_entity_by_id("test_chest")

    # chest.is_on flipped to False → sfx_close
    game.audio_manager.play_sfx.assert_called_once_with("02-open_chest", "test_chest")


# ---------------------------------------------------------------------------
# IT-003 — Door open/close plays correct sfx
# ---------------------------------------------------------------------------


@pytest.mark.tc("IT-003")
def test_door_open_plays_sfx_open():
    """IT-003a: Player triggers door → is_on=True → sfx_open played."""
    from src.config import Settings

    game = _make_game_with_player_at((100, 100))
    door = _DoorSprite(sfx_open="00-wooden_door", sfx_close="00-wooden_door", initial_is_on=False)
    game.interactives = [door]

    im = InteractionManager(game)

    with patch("pygame.key.get_pressed", return_value={Settings.INTERACT_KEY: True}):
        im.handle_interactions()

    call_args = game.audio_manager.play_sfx.call_args
    assert call_args is not None, "play_sfx not called on door open"
    assert call_args[0][0] == "00-wooden_door"
    assert call_args[0][1] == "test_door"


@pytest.mark.tc("IT-003")
def test_door_close_plays_sfx_close():
    """IT-003b: Player closes open door → is_on=False → sfx_close played."""
    from src.config import Settings

    game = _make_game_with_player_at((100, 100))
    door = _DoorSprite(sfx_open="00-wooden_door", sfx_close="00-wooden_door", initial_is_on=True)
    game.interactives = [door]

    im = InteractionManager(game)

    with patch("pygame.key.get_pressed", return_value={Settings.INTERACT_KEY: True}):
        im.handle_interactions()

    call_args = game.audio_manager.play_sfx.call_args
    assert call_args is not None, "play_sfx not called on door close"
    assert call_args[0][0] == "00-wooden_door"
    assert call_args[0][1] == "test_door"
