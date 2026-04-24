"""
Consolidated World Infrastructure Test Suite
Includes: TmjParser and MapManager logic.
"""
import pytest
import pygame
import os
import json
from unittest.mock import patch, MagicMock
from src.map.tmj_parser import TmjParser, TileMapData
from src.map.manager import MapManager
from src.map.layout import OrthogonalLayout
from src.config import Settings

@pytest.fixture(scope="module", autouse=True)
def world_env():
    pygame.init()
    Settings.load()
    yield
    pygame.quit()

@pytest.fixture
def mock_tmj_data():
    return {
        "width": 10,
        "height": 10,
        "tilewidth": 32,
        "tileheight": 32,
        "layers": [
            {
                "id": 1,
                "name": "ground",
                "type": "tilelayer",
                "data": [1] * 100,
                "properties": [{"name": "depth", "type": "int", "value": 0}]
            },
            {
                "name": "objects",
                "type": "objectgroup",
                "layers": [],
                "objects": [
                    {
                        "id": 1,
                        "name": "test_npc",
                        "type": "npc",
                        "x": 32,
                        "y": 32,
                        "width": 32,
                        "height": 32,
                        "properties": [{"name": "entity_type", "type": "string", "value": "npc"}]
                    }
                ]
            }
        ],
        "tilesets": [
            {
                "firstgid": 1,
                "source": "../tilesets/test.tsj"
            }
        ],
        "properties": []
    }

# --- TMJ PARSER TESTS ---

@patch("builtins.open", new_callable=MagicMock)
def test_tmj_parser_load(mock_open, mock_tmj_data):
    """TmjParser should load and structure map data from JSON."""
    parser = TmjParser()
    with patch('json.load', return_value=mock_tmj_data):
        with patch('os.path.exists', return_value=True):
            # We skip actual file IO and tileset loading for unit test
            with patch.object(TmjParser, '_parse_tsx'):
                res = parser.load_map("dummy.tmj")
                assert res["width"] == 10
                assert len(res["entities"]) == 1

# --- MAP MANAGER TESTS ---

def test_map_manager_collision():
    """MapManager should correctly identify collidable tiles."""
    layout = OrthogonalLayout(32)
    # Mock map result with one collidable tile at GID 2
    # layers must be a dict of matrices
    map_result = {
        "width": 2, "height": 2,
        "layers": {
            1: [[1, 2], [1, 1]]
        },
        "tiles": {
            1: TileMapData(image=MagicMock(), depth=0, collidable=False),
            2: TileMapData(image=MagicMock(), depth=0, collidable=True)
        }
    }
    mm = MapManager(map_result, layout)
    # Check tile at (1, 0) -> x=1, y=0
    assert mm.is_collidable(1, 0) is True
    assert mm.is_collidable(0, 0) is False

def test_map_manager_viewport_culling():
    """MapManager should only return visible chunks."""
    layout = OrthogonalLayout(32)
    map_result = {
        "width": 10, "height": 10,
        "layers": {1: [[1] * 10] * 10},
        "tiles": {1: TileMapData(image=MagicMock(), depth=0, collidable=False)}
    }
    mm = MapManager(map_result, layout)
    viewport = pygame.Rect(0, 0, 64, 64) # 2x2 tiles
    visible = list(mm.get_visible_chunks(viewport))
    # Should be 4 tiles (2x2)
    assert len(visible) == 4
