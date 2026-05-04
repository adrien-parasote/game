import json
import os
from unittest.mock import MagicMock, patch

import pytest

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
        "width": 10,
        "height": 10,
        "layers": [
            {"type": "tilelayer", "id": 1, "name": "Ground", "data": [0] * 100},
            {
                "type": "group",
                "name": "Sub",
                "layers": [{"type": "tilelayer", "id": 2, "name": "Walls", "data": [0] * 100}],
            },
            {
                "type": "objectgroup",
                "name": "Entities",
                "objects": [{"id": 1, "name": "player", "type": "player", "x": 32, "y": 32}],
            },
        ],
        "tilesets": [{"firstgid": 1, "source": "tiles.tsx"}],
        "properties": [{"name": "bgm", "value": "forest"}],
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

    import io

    with patch("builtins.open") as mock_open:
        # Side effect to return TMJ first, then TSX
        mock_open.side_effect = [io.StringIO(json.dumps(tmj_data)), io.StringIO(tsx_content)]

        with patch("json.load", return_value=tmj_data):
            with patch("xml.etree.ElementTree.parse") as mock_xml:
                # Mock XML tree
                mock_tree = MagicMock()
                mock_root = MagicMock()
                mock_root.get.side_effect = lambda k, d=None: {
                    "tilewidth": "32",
                    "tileheight": "32",
                    "columns": "1",
                    "tilecount": "1",
                }.get(k, d)
                mock_xml.return_value = mock_tree
                mock_tree.getroot.return_value = mock_root

                # Mock image loading
                with patch("src.engine.asset_manager.AssetManager.get_image") as mock_img:
                    mock_img.return_value = MagicMock()  # pygame Surface

                    result = parser.load_map("dummy.tmj")
                    assert result["width"] == 10
                    assert len(result["layer_order"]) == 2
                    assert result["spawn_player"]["name"] == "player"


@patch("src.map.tmj_parser.os.path.exists", return_value=True)
def test_tmj_parser_tsx_errors_and_properties(mock_exists):
    parser = TmjParser()

    # 1. Missing image tag in TSX
    bad_tsx_no_image = '<?xml version="1.0" encoding="UTF-8"?>\n<tileset name="test" tilewidth="32" tileheight="32" tilecount="1" columns="1">\n</tileset>'

    # Mock TMJ data
    tmj_data = {
        "width": 1,
        "height": 1,
        "layers": [
            {
                "type": "objectgroup",
                "objects": [{"id": 1, "properties": [{"name": "hp", "value": 10}]}],
            }
        ],
        "tilesets": [{"firstgid": 1, "source": "tiles.tsx"}],
    }

    import io

    with patch("builtins.open") as mock_open:
        mock_open.side_effect = [
            io.StringIO(json.dumps(tmj_data)),
            io.StringIO(bad_tsx_no_image.strip()),
        ]
        with patch("json.load", return_value=tmj_data):
            with pytest.raises(ValueError, match="No <image> tag found"):
                parser.load_map("dummy.tmj")

    # 2. Properties (bool, int) and depth occlusion
    good_tsx = '<?xml version="1.0" encoding="UTF-8"?>\n<tileset name="test" tilewidth="32" tileheight="32" tilecount="1" columns="1">\n<image source="tiles.png" width="32" height="32"/>\n<properties>\n<property name="global_bool" type="bool" value="true"/>\n<property name="global_int" type="int" value="42"/>\n</properties>\n<tile id="0">\n<properties>\n<property name="collidable" type="bool" value="true"/>\n<property name="depth" type="int" value="1"/>\n<property name="custom_str" type="string" value="hello"/>\n</properties>\n</tile>\n</tileset>'

    import io

    with patch("builtins.open") as mock_open:
        mock_open.side_effect = [io.StringIO(json.dumps(tmj_data)), io.StringIO(good_tsx.strip())]
        with patch("json.load", return_value=tmj_data):
            with patch("src.engine.asset_manager.AssetManager.get_image") as mock_img:
                mock_surf = MagicMock()
                mock_img.return_value = mock_surf
                mock_surf.copy.return_value = MagicMock()

                result = parser.load_map("dummy.tmj")

                # Check object properties
                assert result["entities"][0]["properties"]["hp"] == 10

                # Check tile properties
                tile_data = result["tiles"][1]  # firstgid is 1
                assert tile_data.depth == 1
                assert tile_data.collidable is True
                assert tile_data.properties["global_bool"] is True
                assert tile_data.properties["global_int"] == 42
                assert tile_data.properties["custom_str"] == "hello"


def test_tmj_parser_tsx_file_not_found():
    parser = TmjParser()
    tmj_data = {
        "width": 1,
        "height": 1,
        "layers": [],
        "tilesets": [{"firstgid": 1, "source": "tiles.tsx"}],
    }

    def exists_side_effect(path):
        if path == "dummy.tmj":
            return True
        if "tiles.tsx" in path:
            return False
        return True

    import io

    with patch("src.map.tmj_parser.os.path.exists", side_effect=exists_side_effect):
        with patch("builtins.open") as mock_open:
            mock_open.return_value = io.StringIO(json.dumps(tmj_data))
            with patch("json.load", return_value=tmj_data):
                with pytest.raises(FileNotFoundError, match="Tileset file not found"):
                    parser.load_map("dummy.tmj")


def test_tmj_parser_image_not_found():
    parser = TmjParser()
    tmj_data = {
        "width": 1,
        "height": 1,
        "layers": [],
        "tilesets": [{"firstgid": 1, "source": "tiles.tsx"}],
    }

    tsx_content = '<?xml version="1.0" encoding="UTF-8"?>\n<tileset name="test" tilewidth="32" tileheight="32" tilecount="1" columns="1">\n<image source="missing.png" width="32" height="32"/>\n</tileset>'

    def exists_side_effect(path):
        if "missing.png" in path:
            return False
        return True

    import io

    with patch("src.map.tmj_parser.os.path.exists", side_effect=exists_side_effect):
        with patch("builtins.open") as mock_open:
            mock_open.side_effect = [
                io.StringIO(json.dumps(tmj_data)),
                io.StringIO(tsx_content.strip()),
            ]
            with patch("json.load", return_value=tmj_data):
                with pytest.raises(FileNotFoundError, match="Tileset image not found"):
                    parser.load_map("dummy.tmj")
