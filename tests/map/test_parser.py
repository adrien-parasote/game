import pytest
import os
import json
from unittest.mock import patch, MagicMock
from src.map.tmj_parser import TmjParser

def test_tmj_parser_file_not_found():
    parser = TmjParser()
    with pytest.raises(FileNotFoundError):
        parser.load_map("non_existent.tmj")

def test_tmj_parser_invalid_format():
    parser = TmjParser()
    # Mock open and exists
    with patch("os.path.exists", return_value=True):
        with patch("builtins.open", MagicMock()):
            with patch("json.load", return_value={"wrong_key": []}):
                with pytest.raises(ValueError):
                    parser.load_map("dummy.tmj")

@patch("src.map.tmj_parser.os.path.exists", return_value=True)
def test_tmj_parser_full_load(mock_exists):
    parser = TmjParser()
    
    # Mock TMJ data
    tmj_data = {
        "width": 10, "height": 10,
        "layers": [
            {"type": "tilelayer", "id": 1, "name": "Ground", "data": [0]*100},
            {"type": "group", "name": "Sub", "layers": [
                {"type": "tilelayer", "id": 2, "name": "Walls", "data": [0]*100}
            ]},
            {"type": "objectgroup", "name": "Entities", "objects": [
                {"id": 1, "name": "player", "type": "player", "x": 32, "y": 32}
            ]}
        ],
        "tilesets": [{"firstgid": 1, "source": "tiles.tsx"}],
        "properties": [{"name": "bgm", "value": "forest"}]
    }
    
    # Mock TSX data (XML)
    tsx_content = """<?xml version="1.0" encoding="UTF-8"?>
    <tileset name="test" tilewidth="32" tileheight="32" tilecount="1" columns="1">
        <image source="tiles.png" width="32" height="32"/>
        <tile id="0">
            <properties>
                <property name="collidable" type="bool" value="true"/>
            </properties>
        </tile>
    </tileset>
    """
    
    with patch("builtins.open") as mock_open:
        # Side effect to return TMJ first, then TSX
        mock_open.side_effect = [
            MagicMock(__enter__=lambda s: MagicMock(read=lambda: json.dumps(tmj_data))),
            MagicMock(__enter__=lambda s: MagicMock(read=lambda: tsx_content))
        ]
        
        with patch("json.load", return_value=tmj_data):
            with patch("xml.etree.ElementTree.parse") as mock_xml:
                # Mock XML tree
                mock_tree = MagicMock()
                mock_root = MagicMock()
                mock_root.get.side_effect = lambda k, d=None: {"tilewidth": "32", "tileheight": "32", "columns": "1", "tilecount": "1"}.get(k, d)
                mock_xml.return_value = mock_tree
                mock_tree.getroot.return_value = mock_root
                
                # Mock image loading
                with patch("src.engine.asset_manager.AssetManager.get_image") as mock_img:
                    mock_img.return_value = MagicMock() # pygame Surface
                    
                    result = parser.load_map("dummy.tmj")
                    assert result["width"] == 10
                    assert len(result["layer_order"]) == 2
                    assert result["spawn_player"]["name"] == "player"
