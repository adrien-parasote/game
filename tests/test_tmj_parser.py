import json
import pytest
import pygame
from src.map.tmj_parser import TmjParser

# Ensure pygame dummy driver for headless testing
import os
os.environ["SDL_VIDEODRIVER"] = "dummy"
pygame.init()
pygame.display.set_mode((1, 1))

def test_tmj_parser_load_basic(monkeypatch, tmp_path):
    # Create a dummy .tmj file
    map_data = {
        "width": 10,
        "height": 10,
        "tilesets": [],
        "layers": [
            {
                "name": "ground",
                "type": "tilelayer",
                "data": [0] * 100,
                "properties": [{"name": "depth", "value": 0}]
            },
            {
                "name": "entities",
                "type": "objectgroup",
                "objects": [
                    {
                        "name": "spawn",
                        "type": "player",
                        "x": 32,
                        "y": 32,
                        "width": 32,
                        "height": 32
                    },
                    {
                        "name": "door",
                        "type": "interactive_object",
                        "x": 64,
                        "y": 64,
                        "width": 32,
                        "height": 32,
                        "properties": [
                            {"name": "sub_type", "value": "door"},
                            {"name": "is_passable", "value": True}
                        ]
                    }
                ]
            }
        ]
    }
    
    map_file = tmp_path / "test_map.tmj"
    map_file.write_text(json.dumps(map_data))
    
    parser = TmjParser()
    result = parser.load_map(str(map_file))
    
    assert result["width"] == 10
    assert result["height"] == 10
    assert "spawn_player" in result
    assert result["spawn_player"]["x"] == 32
    assert len(result["entities"]) == 2
    # Find the door in entities
    door = next(e for e in result["entities"] if e["name"] == "door")
    assert door["properties"]["sub_type"] == "door"

def test_tmj_parser_handles_invalid_file():
    parser = TmjParser()
    with pytest.raises(Exception):
        parser.load_map("non_existent_file.tmj")

def test_tmj_parser_validation_errors(tmp_path):
    parser = TmjParser()
    
    # Missing layers
    map_file = tmp_path / "no_layers.tmj"
    map_file.write_text('{"tilesets": []}')
    with pytest.raises(ValueError):
        parser.load_map(str(map_file))
        
    # Missing tilesets
    map_file = tmp_path / "no_tilesets.tmj"
    map_file.write_text('{"layers": []}')
    with pytest.raises(ValueError):
        parser.load_map(str(map_file))

def test_tmj_parser_parse_player_spawn():
    # Test the standalone helper (currently isolated in parser)
    parser = TmjParser()
    sub_layer = {
        "objects": [
            {"name": "spawn_player", "x": 100, "y": 200}
        ]
    }
    map_result = {"spawn_player": None}
    parser._parse_player_spawn(sub_layer, map_result)
    assert map_result["spawn_player"] == {"x": 100, "y": 200}

def test_tmj_parser_parse_tsx(monkeypatch, tmp_path):
    # Ensure display is initialized for convert_alpha
    if not pygame.display.get_init():
        pygame.display.init()
    if pygame.display.get_surface() is None:
        pygame.display.set_mode((1, 1))
    
    # Mock XML tree
    import xml.etree.ElementTree as ET
    tsx_content = """<tileset name="test" tilewidth="32" tileheight="32" columns="1" tilecount="1">
        <image source="test.png" width="32" height="32"/>
        <tile id="0">
            <properties>
                <property name="collidable" type="bool" value="true"/>
                <property name="depth" type="int" value="1"/>
            </properties>
        </tile>
    </tileset>"""
    tsx_file = tmp_path / "test.tsx"
    tsx_file.write_text(tsx_content)
    
    # Mock pygame.image.load
    mock_surface = pygame.Surface((32, 32))
    # Create the dummy image file on disk
    pygame.image.save(mock_surface, str(tmp_path / "test.png"))
    monkeypatch.setattr(pygame.image, "load", lambda path: mock_surface)

    
    parser = TmjParser()
    tile_dict = {}
    parser._parse_tsx(str(tsx_file), 1, tile_dict)
    
    assert 1 in tile_dict
    assert tile_dict[1].collidable is True
    assert tile_dict[1].depth == 1
