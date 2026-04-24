"""
Consolidated World Persistence Test Suite
Includes: WorldState, AudioManager, and Teleport logic.
"""
import pytest
import pygame
import os
from unittest.mock import MagicMock, patch
from src.engine.world_state import WorldState
from src.engine.audio import AudioManager
from src.config import Settings

@pytest.fixture(scope="module", autouse=True)
def persistence_env():
    pygame.init()
    pygame.display.set_mode((1, 1), pygame.HIDDEN)
    Settings.load()
    yield
    pygame.quit()

# --- WORLD STATE TESTS ---

def test_world_state_set_and_get():
    """WorldState should persist data correctly within the same instance."""
    ws = WorldState()
    ws.set("map1_lever1", {"is_on": True})
    assert ws.get("map1_lever1")["is_on"] is True

def test_world_state_default():
    """WorldState.get should return default when key missing."""
    ws = WorldState()
    assert ws.get("nonexistent_key") is None
    assert ws.get("nonexistent_key", {"is_on": False})["is_on"] is False

def test_world_state_key_generation():
    """WorldState should generate consistent keys using underscore separator."""
    key = WorldState.make_key("spawn.tmj", 123)
    assert key == "spawn_123"

def test_world_state_clear():
    """WorldState.clear should reset all state."""
    ws = WorldState()
    ws.set("map1_key", {"is_on": True})
    ws.clear()
    assert ws.get("map1_key") is None

# --- AUDIO MANAGER TESTS ---

def test_audio_manager_initialization():
    """AudioManager should load without crashing."""
    am = AudioManager()
    assert am is not None

@patch('pygame.mixer.Sound')
def test_audio_sfx_play(mock_sound):
    """AudioManager should attempt to play SFX when path exists."""
    am = AudioManager()
    with patch('os.path.exists', return_value=True):
        am.play_sfx("test.wav")
        mock_sound.assert_called()

# --- TELEPORT TESTS ---

def test_teleport_trigger():
    """Teleport entity should store target map and spawn id."""
    from src.entities.teleport import Teleport
    groups = [pygame.sprite.Group()]
    # Teleport takes rect as first argument
    tp = Teleport(
        rect=pygame.Rect(0, 0, 32, 32),
        groups=groups,
        target_map="target.tmj",
        target_spawn_id="spawn1"
    )
    assert tp.target_map == "target.tmj"
    assert tp.target_spawn_id == "spawn1"
