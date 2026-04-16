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
    # We use the real map for integration-level parsing testing
    map_path = os.path.join(os.path.dirname(__file__), '..', 'assets', 'maps', '00-castel.tmj')
    data = parser.load_map(map_path)
    
    assert "layers" in data
    assert "spawn_player" in data
    
    # Check player coords based on 00-castel.tmj (x=32, y=704)
    assert data["spawn_player"]["x"] == 32
    assert data["spawn_player"]["y"] == 704
    
def test_missing_file(parser):
    with pytest.raises(FileNotFoundError):
        parser.load_map("invalid/path/to/missing.tmj")
