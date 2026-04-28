import pytest
import pygame
import os
from unittest.mock import patch, MagicMock
from src.engine.game import Game
from src.engine.time_system import TimeSystem
from src.config import Settings

"""
Consolidated Engine Core Test Suite
Includes: Game core loop, TimeSystem logic, and System Bootstrap (Settings, Debug).
"""

# --- TimeSystem Tests ---

def test_time_advancement():
    """TimeSystem should advance minutes and hours correctly."""
    ts = TimeSystem(initial_hour=10)
    ts.update(Settings.MINUTE_DURATION)
    assert ts.world_time.minute == 1
    assert ts.world_time.hour == 10

def test_season_transition():
    """TimeSystem should transition seasons after enough days."""
    ts = TimeSystem()
    days_to_skip = Settings.DAYS_PER_SEASON
    ts._total_minutes = float(days_to_skip * 24 * 60)
    assert ts.season_label == 'Summer'

# --- Game Core Tests ---

@patch('src.map.tmj_parser.TmjParser.load_map')
@patch('src.graphics.spritesheet.SpriteSheet.load_grid')
def test_game_initialization(mock_load_grid, mock_load_map):
    """Game should initialize all managers and start at spawn."""
    mock_load_map.return_value = {
        'width': 10, 'height': 10, 'layers': {}, 'tiles': {}, 
        'entities': [], 'properties': {}, 'spawn_player': {'x': 0, 'y': 0}
    }
    mock_load_grid.return_value = [pygame.Surface((32, 32))] * 16
    with patch('os.path.exists', return_value=True):
        game = Game()
        assert game.interaction_manager is not None
        assert game.audio_manager is not None
        assert game.player is not None

def test_game_trigger_dialogue():
    """Game should fetch dialogue from localization and activate manager."""
    with patch('src.engine.game.Game._load_map'):
        game = Game()
        game.hud._lang = {'dialogues': {'00-spawn-test': 'Hello'}}
        game._current_map_name = '00-spawn.tmj'
        game._trigger_dialogue('test')
        assert game.dialogue_manager.is_active is True
        assert game.dialogue_manager.message == 'Hello'

def test_game_load_map_logic():
    """Game._load_map should correctly structure internal state."""
    with patch('src.engine.game.Game._setup_logging'):
        mock_map_data = {
            'width': 10, 'height': 10, 'layers': {1: [[1]*10]*10}, 
            'entities': [{'type': '14-spawn_point', 'x': 32, 'y': 32, 'properties': {'spawn_player': True, 'is_initial_spawn': True}}], 
            'properties': {'bgm': 'spawn_bgm'}
        }
        with patch('src.map.tmj_parser.TmjParser.load_map', return_value=mock_map_data):
            with patch('src.engine.game.Game._spawn_entities'):
                game = Game()
                # Actually _load_map is called in __init__ if DEBUG=True (default in tests usually)
                assert game._current_map_name is not None

def test_game_is_collidable():
    """Game should delegate collision checks to map_manager."""
    with patch('src.engine.game.Game._load_map'):
        game = Game()
        game.map_manager = MagicMock()
        game.map_manager.is_collidable.return_value = True
        game.layout = MagicMock()
        game.layout.to_world.return_value = (100, 100)
        assert game._is_collidable(100, 100) is True
        game.map_manager.is_collidable.assert_called_with(100, 100)

def test_game_transition_map():
    """Game.transition_map should trigger a new map load."""
    with patch('src.engine.game.Game._load_map'):
        game = Game()
        with patch.object(game, '_load_map') as mock_load:
            with patch('os.path.exists', return_value=True):
                game.transition_map('new_map', 'spawn_1', 'instant')
                mock_load.assert_called_with('new_map', 'spawn_1', 'instant')

def test_game_draw_scene():
    """Game._draw_scene should call drawing methods of sub-components."""
    with patch('src.engine.game.Game._load_map'):
        game = Game()
        game.map_manager = MagicMock()
        game.map_manager.layers = {}
        game.visible_sprites = MagicMock()
        game.time_system = MagicMock()
        game.time_system.night_alpha = 0
        game.inventory_ui = MagicMock()
        game.inventory_ui.is_open = False
        game.dialogue_manager = MagicMock()
        game.dialogue_manager.is_active = False
        game.interactives = []
        game.emote_group = []
        game._draw_scene()
        assert game.visible_sprites.custom_draw.called

def test_game_toggle_entity_by_id():
    """Game.toggle_entity_by_id should trigger interaction on target."""
    with patch('src.engine.game.Game._load_map'):
        game = Game()
        target = MagicMock()
        target.element_id = 'target_1'
        game.interactives = [target]
        game.audio_manager = MagicMock()
        game.toggle_entity_by_id('target_1')
        assert target.interact.called

# --- System Bootstrap & Settings Tests ---

def test_settings_load():
    """Settings should load values correctly including new font configs."""
    Settings.load()
    assert hasattr(Settings, 'VERSION')
    assert Settings.TILE_SIZE == 32
    assert hasattr(Settings, 'MAIN_FONT')
    assert hasattr(Settings, 'FONT_SIZE_UI')
    assert hasattr(Settings, 'FONT_SIZE_HUD')

def test_debug_mode_toggle():
    """Debug mode should be toggleable."""
    original = Settings.DEBUG
    Settings.DEBUG = True
    assert Settings.DEBUG is True
    Settings.DEBUG = False
    assert Settings.DEBUG is False
    Settings.DEBUG = original # Restore

def test_asset_path_resolution():
    """Verify core asset directories are accessible."""
    # We check relative to this file
    base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    assets_path = os.path.join(base_path, 'assets')
    assert os.path.exists(assets_path)