import pytest
import os
import json
import pygame
from unittest.mock import MagicMock, patch
from src.map.tmj_parser import TmjParser, TileMapData
from src.map.manager import MapManager
from src.map.layout import OrthogonalLayout
from src.config import Settings
from src.engine.world_state import WorldState
from src.engine.audio import AudioManager

"""
Consolidated World Infrastructure & Persistence Test Suite
Includes: TmjParser, MapManager, WorldState, and AudioManager logic.
"""

# --- TmjParser Tests ---

def test_parser_load_invalid_file():
    parser = TmjParser()
    with pytest.raises(FileNotFoundError):
        parser.load_map('non_existent.tmj')

def test_parser_load_valid_mock_map(tmp_path):
    map_file = tmp_path / 'test.tmj'
    map_data = {
        'width': 2, 'height': 2, 'tilewidth': 32, 'tileheight': 32,
        'layers': [
            {'id': 1, 'name': '00-layer', 'type': 'tilelayer', 'data': [1, 1, 1, 1]},
            {'id': 2, 'name': 'ground', 'type': 'tilelayer', 'data': [2, 2, 2, 2]}
        ],
        'tilesets': []
    }
    with open(map_file, 'w') as f:
        json.dump(map_data, f)
    
    parser = TmjParser()
    result = parser.load_map(str(map_file))
    
    # Check layer parsing (FAILS currently: it uses IDs and doesn't store names for sorting)
    assert 'layers' in result
    assert len(result['layers']) == 2
    
    # Requirement: preserve order or store names for sorting
    # We'll check if names are captured (Step 3 TDD)
    # This might fail if the current implementation doesn't return names
    # Actually TmjParser returns a dict keyed by ID.
    assert hasattr(result, 'layer_order') or isinstance(result['layers'], list) or 'layer_names' in result

def test_parser_chunked_map():
    """TmjParser should handle chunked data formats."""
    parser = TmjParser()
    map_data = {
        'width': 10, 'height': 10, 'tilewidth': 32, 'tileheight': 32,
        'layers': [{
            'id': 1, 'type': 'tilelayer', 'name': 'Ground',
            'chunks': [{'x': 0, 'y': 0, 'width': 5, 'height': 5, 'data': [1] * 25}]
        }],
        'tilesets': []
    }
    with patch('os.path.exists', return_value=True), \
         patch('builtins.open', MagicMock()), \
         patch('json.load', return_value=map_data):
        result = parser.load_map('dummy.tmj')
        assert 1 in result['layers']

# --- MapManager Tests ---

def test_map_manager_collision():
    """MapManager should correctly identify collidable tiles."""
    layout = OrthogonalLayout(32)
    map_result = {
        'width': 2, 'height': 2, 
        'layers': {1: [[1, 2], [1, 1]]}, 
        'tiles': {
            1: TileMapData(image=MagicMock(), depth=0, collidable=False),
            2: TileMapData(image=MagicMock(), depth=0, collidable=True)
        }
    }
    mm = MapManager(map_result, layout)
    assert mm.is_collidable(1, 0) is True
    assert mm.is_collidable(0, 0) is False

def test_map_manager_viewport_culling():
    """MapManager should only return visible chunks."""
    layout = OrthogonalLayout(32)
    map_result = {
        'width': 10, 'height': 10, 
        'layers': {1: [[1] * 10] * 10},
            'layer_order': [1], 
        'tiles': {1: TileMapData(image=MagicMock(), depth=0, collidable=False)}
    }
    mm = MapManager(map_result, layout)
    viewport = pygame.Rect(0, 0, 64, 64) # Should see 2x2 tiles = 4 chunks
    visible = list(mm.get_visible_chunks(viewport))
    assert len(visible) == 4

# --- World State & Audio Tests ---

def test_world_state_persistence():
    ws = WorldState()
    ws.set('map1_lever', {'is_on': True})
    assert ws.get('map1_lever')['is_on'] is True
    ws.clear()
    assert ws.get('map1_lever') is None

def test_audio_manager_load():
    am = AudioManager()
    assert am is not None

@patch('pygame.mixer.Sound')
def test_audio_sfx_play(mock_sound):
    am = AudioManager()
    with patch('os.path.exists', return_value=True):
        am.play_sfx('test.wav')
        mock_sound.assert_called()