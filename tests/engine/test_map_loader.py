"""Tests for MapLoader._save_interactive_states — regression coverage for the
chest/lever state reset bug (PR: fix interactive states not persisted on teleport).

TC-ML-01: Interactive entity states are written to world_state before map unload.
TC-ML-02: Entities without _world_state_key are silently skipped.
TC-ML-03: light_control is included in the persisted state when present.
TC-ML-04: NPC states are still persisted alongside interactive states (no regression).
"""

from unittest.mock import MagicMock, call

import pytest

from src.engine import map_loader
from src.engine.map_loader import MapLoader


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_interactive(is_on: bool, key: str | None = "map::42", light_control: str | None = None):
    """Build a minimal mock interactive entity."""
    entity = MagicMock()
    entity.is_on = is_on
    entity._world_state_key = key
    if light_control is not None:
        entity.light_control = light_control
    else:
        # Remove light_control so getattr(..., None) returns None
        del entity.light_control
    return entity


def _make_game_with_interactives(interactives: list, npcs: list | None = None) -> MagicMock:
    game = MagicMock()
    game.interactives = interactives
    game.npcs = npcs or []
    return game


# ---------------------------------------------------------------------------
# TC-ML-01: basic persistence
# ---------------------------------------------------------------------------


@pytest.mark.tc("TC-ML-01")
def test_save_interactive_states_persists_is_on():
    """_save_interactive_states writes is_on for every entity that has a key."""
    chest = _make_interactive(is_on=False, key="map::chest_1")
    lever = _make_interactive(is_on=True, key="map::lever_1")

    game = _make_game_with_interactives([chest, lever])
    loader = MapLoader(game)

    loader._save_interactive_states()

    game.world_state.set.assert_any_call("map::chest_1", {"is_on": False})
    game.world_state.set.assert_any_call("map::lever_1", {"is_on": True})


# ---------------------------------------------------------------------------
# TC-ML-02: entities without world_state_key are skipped
# ---------------------------------------------------------------------------


@pytest.mark.tc("TC-ML-02")
def test_save_interactive_states_skips_entities_without_key():
    """Entities with _world_state_key=None must not trigger a world_state.set call."""
    entity = _make_interactive(is_on=True, key=None)

    game = _make_game_with_interactives([entity])
    loader = MapLoader(game)

    loader._save_interactive_states()

    game.world_state.set.assert_not_called()


# ---------------------------------------------------------------------------
# TC-ML-03: light_control included when present
# ---------------------------------------------------------------------------


@pytest.mark.tc("TC-ML-03")
def test_save_interactive_states_includes_light_control():
    """light_control should be included in persisted state when the attribute exists."""
    lamp = _make_interactive(is_on=True, key="map::lamp_5", light_control="forced_on")

    game = _make_game_with_interactives([lamp])
    loader = MapLoader(game)

    loader._save_interactive_states()

    game.world_state.set.assert_called_once_with(
        "map::lamp_5", {"is_on": True, "light_control": "forced_on"}
    )


# ---------------------------------------------------------------------------
# TC-ML-04: NPC states still saved (no regression)
# ---------------------------------------------------------------------------


@pytest.mark.tc("TC-ML-04")
def test_save_npc_states_not_broken_by_interactive_save():
    """_save_npc_states must still write NPC pos/facing alongside interactive states."""
    import pygame

    npc = MagicMock()
    npc._world_state_key = "map::npc_1"
    npc.pos = pygame.math.Vector2(128, 256)
    npc.current_facing = "right"

    game = _make_game_with_interactives(interactives=[], npcs=[npc])
    loader = MapLoader(game)

    loader._save_npc_states()

    game.world_state.set.assert_called_once_with(
        "map::npc_1", {"pos": (128.0, 256.0), "facing": "right"}
    )


# ---------------------------------------------------------------------------
# Smoke import test (kept for CI completeness)
# ---------------------------------------------------------------------------


def test_map_loader_import():
    assert True
