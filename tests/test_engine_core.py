"""
Consolidated Engine Core Test Suite
Includes: Game core loop and TimeSystem logic.
"""
import pytest
import pygame
from unittest.mock import patch, MagicMock
from src.engine.game import Game
from src.engine.time_system import TimeSystem
from src.config import Settings

@pytest.fixture(scope="module", autouse=True)
def engine_env():
    pygame.init()
    pygame.display.set_mode((1, 1), pygame.HIDDEN)
    Settings.load()
    yield
    pygame.quit()

# --- TIME SYSTEM TESTS ---

def test_time_advancement():
    """TimeSystem should advance minutes and hours correctly."""
    ts = TimeSystem(initial_hour=10)
    # Advance by Settings.MINUTE_DURATION real seconds = 1 game minute
    ts.update(Settings.MINUTE_DURATION)
    assert ts.world_time.minute == 1
    assert ts.world_time.hour == 10

def test_season_transition():
    """TimeSystem should transition seasons after enough days."""
    ts = TimeSystem()
    # Skip to near end of spring
    days_to_skip = Settings.DAYS_PER_SEASON
    ts._total_minutes = float(days_to_skip * 24 * 60)
    
    assert ts.season_label == "Summer"

# --- GAME CORE TESTS ---

@patch('src.map.tmj_parser.TmjParser.load_map')
@patch('src.graphics.spritesheet.SpriteSheet.load_grid')
def test_game_initialization(mock_load_grid, mock_load_map):
    """Game should initialize all managers and start at spawn."""
    mock_load_map.return_value = {
        "width": 10, "height": 10, "layers": {}, "tiles": {},
        "entities": [],
        "properties": {},
        "spawn_player": {"x": 0, "y": 0}
    }
    mock_load_grid.return_value = [pygame.Surface((32, 32))] * 16
    
    with patch('os.path.exists', return_value=True):
        game = Game()
        assert game.interaction_manager is not None
        assert game.audio_manager is not None
        assert game.player is not None

def test_game_trigger_dialogue(engine_env):
    """Game should fetch dialogue from localization and activate manager."""
    with patch('src.engine.game.Game._load_map'):
        game = Game()
        # Game._trigger_dialogue prepends map base name (00-spawn)
        game.hud._lang = {"dialogues": {"00-spawn-test": "Hello"}}
        game._current_map_name = "00-spawn.tmj"
        
        game._trigger_dialogue("test")
        assert game.dialogue_manager.is_active is True
        assert game.dialogue_manager.message == "Hello"
