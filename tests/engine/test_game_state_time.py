"""
Tests for GameStateManager time reset and load behavior.
Ensures that:
* Starting a new game after returning to the title resets the time/season.
* Loading a saved game restores the saved time/season.
"""

import os
import pytest
import pygame
from unittest.mock import patch

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
    # TimeSystem stub: initial_hour=6, advance by 120 game-minutes
    ts = TimeSystem(initial_hour=6)
    # update() takes real seconds: 120 game-minutes * MINUTE_DURATION sec/min = 12 real seconds
    ts.update(120 * Settings.MINUTE_DURATION)
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
    # Advance time by 120 game-minutes
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
    expected_initial = (
        Settings.INITIAL_SEASON * Settings.DAYS_PER_SEASON * 24 * 60
        + Settings.INITIAL_HOUR * 60
    )
    assert reset_minutes == expected_initial

def test_load_game_time_restored(manager, tmp_saves_dir):
    """Regression TC-GF-031: loaded game time must exactly match saved time."""
    # Build and save a mock game with known time
    mock_game = _make_mock_game(tmp_saves_dir)
    saved_minutes = mock_game.time_system._total_minutes
    manager.save(1, mock_game)

    # Load via GameStateManager — patch its internal SaveManager to use tmp_saves_dir
    gsm = GameStateManager()
    gsm._transition_to_title()

    with patch.object(gsm._save_manager, "load", side_effect=manager.load):
        gsm._transition_to_playing(slot_id=1)

    loaded_minutes = gsm._game.time_system._total_minutes

    # loaded_minutes must exactly equal what was serialised
    assert loaded_minutes == pytest.approx(saved_minutes, rel=1e-5), (
        f"Time mismatch: loaded={loaded_minutes}, saved={saved_minutes}"
    )
