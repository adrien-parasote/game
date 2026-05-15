"""
Tests for GameStateManager time reset and load behavior.
Ensures that:
* Starting a new game after returning to the title resets the time/season.
* Loading a saved game restores the saved time/season.
"""

import os
import pytest
import pygame

from src.engine.game_state_manager import GameStateManager
from src.engine.game import Game
from src.engine.time_system import TimeSystem
from src.engine.save_manager import SaveManager
from src.config import Settings

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session", autouse=True)
def pygame_init():
    """Initialize pygame once for all tests."""
    pygame.init()
    yield
    pygame.quit()

@pytest.fixture
def tmp_saves_dir(tmp_path):
    return str(tmp_path / "saves")

@pytest.fixture
def manager(tmp_saves_dir):
    return SaveManager(saves_dir=tmp_saves_dir)

def _make_mock_game(tmp_saves_dir):
    """Create a minimal mock Game with required attributes for saving."""
    from unittest.mock import MagicMock
    game = MagicMock()
    game.map_manager = MagicMock()
    game.map_manager.name = "Mocked Map"
    game._current_map_name = "00-spawn.tmj"
    # Player stub
    game.player = MagicMock()
    game.player.name = "Hero"
    game.player.pos = pygame.math.Vector2(320.0, 480.0)
    game.player.current_state = "down"
    game.player.level = 1
    game.player.hp = 100
    game.player.max_hp = 100
    game.player.gold = 0
    # Inventory stub (reuse real class for simplicity)
    from src.engine.inventory_system import Inventory, Item
    inv = Inventory(capacity=28)
    inv.slots[3] = Item(id="sword_iron", name="Épée", description="", quantity=1, stack_max=1)
    inv.equipment["LEFT_HAND"] = Item(id="sword_iron", name="Épée", description="", quantity=1, stack_max=1)
    game.player.inventory = inv
    # TimeSystem stub
    ts = TimeSystem(initial_hour=6)
    # advance time to a known value (e.g., 2 hours)
    ts.update(120 * Settings.MINUTE_DURATION)  # 120 minutes
    game.time_system = ts
    # WorldState stub
    from src.engine.world_state import WorldState
    ws = WorldState()
    ws.set("castle_hall_chest_01", {"is_on": True})
    game.world_state = ws
    return game

# ---------------------------------------------------------------------------
# Test cases
# ---------------------------------------------------------------------------

def test_new_game_time_reset(manager, tmp_saves_dir):
    gsm = GameStateManager()
    # Start a new game (should load default map)
    gsm._transition_to_playing(slot_id=None)
    # Advance time by 120 minutes (2 hours)
    gsm._game.time_system.update(120 * Settings.MINUTE_DURATION)
    # Capture time after advancement
    advanced_minutes = gsm._game.time_system._total_minutes
    assert advanced_minutes > 0
    # Return to title, which should create a fresh Game instance
    gsm._transition_to_title()
    # Start another new game
    gsm._transition_to_playing(slot_id=None)
    # Time should be reset to the initial value defined by Settings
    reset_minutes = gsm._game.time_system._total_minutes
    # The initial total minutes is based on Settings.INITIAL_SEASON and hour
    expected_initial = (
        Settings.INITIAL_SEASON * Settings.DAYS_PER_SEASON * 24 * 60
        + Settings.INITIAL_HOUR * 60
    )
    assert reset_minutes == expected_initial

def test_load_game_time_restored(manager, tmp_saves_dir):
    # Save a mock game with a known time value
    mock_game = _make_mock_game(tmp_saves_dir)
    manager.save(1, mock_game)
    # Capture expected time from the mock (accounts for MAX_DT_CLAMP)
    expected = mock_game.time_system._total_minutes
    # Load the saved data via GameStateManager transition
    gsm = GameStateManager()
    # Redirect GSM's save manager to the tmp dir so load finds our save
    gsm._save_manager = manager
    # Transition to title first to ensure fresh state before loading
    gsm._transition_to_title()
    # Load slot 1
    gsm._transition_to_playing(slot_id=1)
    # Verify that the loaded game's time matches the saved time
    loaded_minutes = gsm._game.time_system._total_minutes
    # Use approx because of float arithmetic
    assert loaded_minutes == pytest.approx(expected, rel=1e-5)

