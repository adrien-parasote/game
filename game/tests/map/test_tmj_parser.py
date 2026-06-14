"""Tests for TmjParser (src/map/tmj_parser.py).

Covers: missing file raises FileNotFoundError, invalid JSON format raises ValueError,
        map properties parsed correctly, layer depth/order property, path resolution.
"""
# TC traceability: engine-core.md §TMJ (TmjParser)
# TC IDs to be assigned when spec test case table is added.

import json
import os
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import MagicMock, patch

import pygame
import pytest

# ── Helpers ────────────────────────────────────────────────────────────────────


def _make_parser():
    """Build a TmjParser without loading any real Tiled project."""
    from src.map.tmj_parser import TmjParser

    with patch("os.path.exists", return_value=False):
        parser = TmjParser()
    parser.project = None
    return parser


def _write_minimal_tmj(tmp_path: Path, properties: list | None = None) -> Path:
    """Write the absolute minimum valid .tmj file for tests."""
    data = {
        "width": 10,
        "height": 10,
        "layers": [],
        "tilesets": [],
        "properties": properties or [],
    }
    p = tmp_path / "test.tmj"
    p.write_text(json.dumps(data), encoding="utf-8")
    return p


# ── Error handling ─────────────────────────────────────────────────────────────


def test_load_map_missing_file_raises():
    """load_map() on a non-existent path → FileNotFoundError."""
    parser = _make_parser()
    with pytest.raises(FileNotFoundError, match="Map file not found"):
        parser.load_map("/nonexistent/path/map.tmj")


def test_load_map_missing_layers_key_raises(tmp_path):
    """load_map() on JSON missing 'layers' key → ValueError."""
    bad = tmp_path / "bad.tmj"
    bad.write_text(json.dumps({"tilesets": []}), encoding="utf-8")
    parser = _make_parser()
    with pytest.raises(ValueError, match="Invalid TMJ format"):
        parser.load_map(str(bad))


def test_load_map_missing_tilesets_key_raises(tmp_path):
    """load_map() on JSON missing 'tilesets' key → ValueError."""
    bad = tmp_path / "bad2.tmj"
    bad.write_text(json.dumps({"layers": []}), encoding="utf-8")
    parser = _make_parser()
    with pytest.raises(ValueError, match="Invalid TMJ format"):
        parser.load_map(str(bad))


# ── Successful parse ───────────────────────────────────────────────────────────


def test_load_map_returns_dimensions(tmp_path):
    """load_map() on a valid file returns correct width/height."""
    tmj = _write_minimal_tmj(tmp_path)
    parser = _make_parser()
    result = parser.load_map(str(tmj))
    assert result["width"] == 10
    assert result["height"] == 10


def test_load_map_top_level_properties_parsed(tmp_path):
    """Map-level properties list is converted to a flat dict."""
    props = [{"name": "ambient", "value": "forest"}]
    tmj = _write_minimal_tmj(tmp_path, properties=props)
    parser = _make_parser()
    result = parser.load_map(str(tmj))
    assert result["properties"]["ambient"] == "forest"


def test_load_map_no_properties_returns_empty_dict(tmp_path):
    """Map with no properties key → result['properties'] is an empty dict."""
    tmj = _write_minimal_tmj(tmp_path, properties=[])
    parser = _make_parser()
    result = parser.load_map(str(tmj))
    assert result["properties"] == {}


def test_load_map_tilelayer_order_property(tmp_path):
    """Tilelayer 'order' custom property is stored in layer_order_values."""
    data = {
        "width": 5,
        "height": 5,
        "tilesets": [],
        "properties": [],
        "layers": [
            {
                "id": 1,
                "name": "Ground",
                "type": "tilelayer",
                "width": 5,
                "height": 5,
                "data": [0] * 25,
                "properties": [{"name": "order", "value": 3, "type": "int"}],
            }
        ],
    }
    p = tmp_path / "ordered.tmj"
    p.write_text(json.dumps(data), encoding="utf-8")

    parser = _make_parser()
    result = parser.load_map(str(p))
    assert result["layer_order_values"][1] == 3


def test_load_map_spawn_player_detected(tmp_path):
    """Object with spawn_player=true property is recorded in result['spawn_player']."""
    data = {
        "width": 5,
        "height": 5,
        "tilesets": [],
        "properties": [],
        "layers": [
            {
                "id": 2,
                "name": "Sprites",
                "type": "objectgroup",
                "objects": [
                    {
                        "id": 1,
                        "name": "player",
                        "type": "",
                        "x": 64,
                        "y": 64,
                        "width": 32,
                        "height": 48,
                        "properties": [{"name": "spawn_player", "value": True}],
                    }
                ],
            }
        ],
    }
    p = tmp_path / "spawn.tmj"
    p.write_text(json.dumps(data), encoding="utf-8")

    parser = _make_parser()
    result = parser.load_map(str(p))
    assert result["spawn_player"] is not None
    assert result["spawn_player"]["x"] == 64
