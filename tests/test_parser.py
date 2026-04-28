import pytest
import os
import json
from src.map.tmj_parser import TmjParser

def test_parser_load_invalid_file():
    parser = TmjParser()
    with pytest.raises(FileNotFoundError):
        parser.load_map("non_existent.tmj")

def test_parser_load_valid_mock_map(tmp_path):
    map_file = tmp_path / "test.tmj"
    map_data = {
        "width": 10,
        "height": 10,
        "tilewidth": 32,
        "tileheight": 32,
        "infinite": True,
        "properties": [
            {"name": "bgm", "type": "string", "value": "test_bgm"},
            {"name": "custom_int", "type": "int", "value": 42},
            {"name": "custom_bool", "type": "bool", "value": True},
            {"name": "custom_color", "type": "color", "value": "#ff0000ff"}
        ],
        "layers": [
            {
                "name": "ground",
                "type": "tilelayer",
                "chunks": [
                    {
                        "data": [1] * 256,
                        "height": 16,
                        "width": 16,
                        "x": 0,
                        "y": 0
                    }
                ]
            },
            {
                "name": "objects",
                "type": "objectgroup",
                "objects": [
                    {
                        "id": 1,
                        "name": "chest",
                        "type": "chest",
                        "x": 32,
                        "y": 32,
                        "width": 32,
                        "height": 32,
                        "properties": [
                            {"name": "is_on", "type": "bool", "value": True}
                        ]
                    }
                ]
            }
        ],
        "tilesets": []
    }
    with open(map_file, "w") as f:
        json.dump(map_data, f)
        
    parser = TmjParser()
    result = parser.load_map(str(map_file))
    assert result["width"] == 10
    assert result["properties"]["bgm"] == "test_bgm"
    assert result["properties"]["custom_int"] == 42
    assert result["properties"]["custom_color"] == "#ff0000ff"
    assert len(result["entities"]) == 1
    assert result["entities"][0]["name"] == "chest"
