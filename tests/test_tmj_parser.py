import pytest
import os
import pygame
from src.map.tmj_parser import TmjParser, TileMapData

@pytest.fixture
def parser():
    pygame.init()
    pygame.display.set_mode((1, 1), pygame.HIDDEN)
    yield TmjParser()
    pygame.quit()

def test_load_valid_map(parser):
    # TC-TMJ-01: parser returns layers containing IDs and a valid player coords
    # Updated for new 00-castel.tmj (spawn_player property x=448, y=864)
    map_path = os.path.join(os.path.dirname(__file__), '..', 'assets', 'maps', '00-castel.tmj')
    data = parser.load_map(map_path)
    
    assert "layers" in data
    assert "spawn_player" in data
    
    # Check player coords based on new 00-castel.tmj
    assert data["spawn_player"]["x"] == 448
    assert data["spawn_player"]["y"] == 864

def test_recursive_layer_parsing(parser):
    # Verify that layers nested in groups (e.g. 'Layers') are extracted correctly
    map_path = os.path.join(os.path.dirname(__file__), '..', 'assets', 'maps', '00-castel.tmj')
    data = parser.load_map(map_path)
    
    # Layer 3 should be '03-indoor' inside the 'Layers' group
    # We check if it exists in the result dictionary
    assert 3 in data["layers"]
    assert len(data["layers"][3]) > 0

def test_entity_collection(parser):
    # Verify that objects in objectgroups are collected into map_result["entities"]
    map_path = os.path.join(os.path.dirname(__file__), '..', 'assets', 'maps', '00-castel.tmj')
    data = parser.load_map(map_path)
    
    assert "entities" in data
    assert len(data["entities"]) > 0
    # The spawn_player object should be in entities
    player_entity = next((e for e in data["entities"] if e["properties"].get("spawn_player") is True), None)
    assert player_entity is not None
    assert player_entity["x"] == 448

def test_missing_file(parser):
    with pytest.raises(FileNotFoundError):
        parser.load_map("invalid/path/to/missing.tmj")
