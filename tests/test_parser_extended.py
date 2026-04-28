import pytest
import json
from unittest.mock import MagicMock, patch
from src.map.tmj_parser import TmjParser

def test_parser_chunked_map():
    parser = TmjParser()
    # Mock data for an infinite map with chunks
    map_data = {
        "width": 10, "height": 10, "tilewidth": 32, "tileheight": 32,
        "layers": [
            {
                "id": 1,
                "type": "tilelayer",
                "name": "Ground",
                "chunks": [
                    {"x": 0, "y": 0, "width": 5, "height": 5, "data": [1]*25}
                ],
                "properties": [{"name": "collidable", "type": "bool", "value": True}]
            }
        ],
        "tilesets": []
    }
    
    with patch('os.path.exists', return_value=True):
        with patch('builtins.open', MagicMock()):
            with patch('json.load', return_value=map_data):
                result = parser.load_map("dummy.tmj")
                # result["layers"] is a dict of ID -> data
                assert 1 in result["layers"]

def test_parser_object_layer():
    parser = TmjParser()
    map_data = {
        "width": 10, "height": 10, "tilewidth": 32, "tileheight": 32,
        "layers": [
            {
                "id": 2,
                "type": "objectgroup",
                "name": "Entities",
                "objects": [
                    {
                        "id": 1, "name": "hero", "type": "player",
                        "x": 32, "y": 64, "width": 32, "height": 32,
                        "properties": [{"name": "hp", "type": "int", "value": 100}]
                    }
                ]
            }
        ],
        "tilesets": []
    }
    
    with patch('os.path.exists', return_value=True):
        with patch('builtins.open', MagicMock()):
            with patch('json.load', return_value=map_data):
                result = parser.load_map("dummy.tmj")
                assert "entities" in result
                assert len(result["entities"]) == 1
                assert result["entities"][0]["name"] == "hero"
                assert result["entities"][0]["properties"]["hp"] == 100
