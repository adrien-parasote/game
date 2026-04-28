import pytest
import pygame
from unittest.mock import MagicMock, patch
from src.map.tmj_parser import TmjParser
from src.map.manager import MapManager
from src.map.layout import OrthogonalLayout

def test_layer_recursive_order():
    """Verify that nested group layers are found and sorted by name prefix."""
    parser = TmjParser()
    # Mock TMJ with nested groups
    mock_data = {
        "width": 2, "height": 2, "tilewidth": 32, "tileheight": 32,
        "layers": [
            {
                "type": "group", "name": "Sprites",
                "layers": []
            },
            {
                "type": "group", "name": "Layers",
                "layers": [
                    {"id": 3, "name": "02-layer", "type": "tilelayer", "data": [0,0,0,0], "width": 2, "height": 2, "opacity": 1, "visible": True},
                    {"id": 2, "name": "01-layer", "type": "tilelayer", "data": [0,0,0,0], "width": 2, "height": 2, "opacity": 1, "visible": True},
                    {"id": 1, "name": "00-layer", "type": "tilelayer", "data": [0,0,0,0], "width": 2, "height": 2, "opacity": 1, "visible": True}
                ]
            }
        ],
        "tilesets": []
    }
    
    result = {
        "layers": {},
        "layer_order": [],
        "layer_names": {},
        "tiles": {},
        "width": 2, "height": 2, "tile_size": 32
    }
    
    parser._process_layers(mock_data["layers"], 2, result)
    
    # Check if all found
    assert 1 in result["layer_names"]
    assert 2 in result["layer_names"]
    assert 3 in result["layer_names"]
    
    # Check name-based sorting in MapManager
    manager = MapManager(result, OrthogonalLayout(32))
    # Should be sorted by name: 00-layer (1), 01-layer (2), 02-layer (3)
    assert manager.layer_order == [1, 2, 3]

def test_map_manager_collision():
    """Verify collision detection works across layers using tile coordinates."""
    map_data = {
        "layers": {
            1: [[1, 0], [0, 0]]
        },
        "tiles": {
            1: MagicMock(collidable=True)
        },
        "width": 2, "height": 2, "tile_size": 32
    }
    manager = MapManager(map_data, OrthogonalLayout(32))
    assert manager.is_collidable(0, 0) is True
    assert manager.is_collidable(1, 0) is False
