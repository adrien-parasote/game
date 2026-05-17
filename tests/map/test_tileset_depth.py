"""
TC-BRIDGE-001 : La tile de pont (local_id=75 dans 02-decorations.tsx, y=6 x=3)
  doit avoir depth=0 (joueur au-dessus) et walkable=true.
  Note : local_id = x + y * columns = 3 + 6*12 = 75

TC-WATER-001 : Le parseur Python doit flattener les class properties Tiled
  imbriquées dans <property type="class">. La prop walkable=false du tileset
  01-water.tsx est stockée dans une class property — sans flattening, le
  hard default walkable=True s'applique à toutes les tiles eau.

TC-PARSER-CLASS-001 : _parse_tileset_properties doit lire les propriétés
  imbriquées dans des <property type="class"> et les flattener dans le dict résultat.
"""

import io
import json
import xml.etree.ElementTree as ET
from unittest.mock import MagicMock, patch

import pytest

from src.map.tmj_parser import TmjParser

DECORATIONS_TSX = "assets/tiled/tiles/02-decorations.tsx"
WATER_TSX = "assets/tiled/autotiles/01-water.tsx"

BRIDGE_TILE_X = 3   # column 3 (0-indexed)
BRIDGE_TILE_Y = 6   # row 6
COLUMNS = 12


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _effective_depth(tsx_path: str, local_id: int) -> int:
    tree = ET.parse(tsx_path)
    root = tree.getroot()
    tileset_depth = 0
    for p in root.findall("./properties/property"):
        if p.get("name") == "depth" and p.get("type") == "int":
            tileset_depth = int(p.get("value", "0"))
    for tile in root.findall("tile"):
        if tile.get("id") == str(local_id):
            for p in tile.findall("./properties/property"):
                if p.get("name") == "depth" and p.get("type") == "int":
                    return int(p.get("value", "0"))
            return tileset_depth  # tile found but no depth override
    return tileset_depth  # tile not in XML


def _effective_walkable(tsx_path: str, local_id: int) -> bool:
    tree = ET.parse(tsx_path)
    root = tree.getroot()
    ts_walkable = True
    for p in root.findall("./properties/property"):
        if p.get("name") == "walkable" and p.get("type") == "bool":
            ts_walkable = p.get("value", "true").lower() == "true"
    for tile in root.findall("tile"):
        if tile.get("id") == str(local_id):
            for p in tile.findall("./properties/property"):
                if p.get("name") == "walkable" and p.get("type") == "bool":
                    return p.get("value", "true").lower() == "true"
            return ts_walkable
    return ts_walkable


# ---------------------------------------------------------------------------
# TC-BRIDGE-001
# ---------------------------------------------------------------------------

class TestBridgeTile:
    """TC-BRIDGE-001: tile de pont (x+3, y+6 = local_id=75) doit avoir depth=0, walkable=True."""

    def test_bridge_tile_local_id_is_75(self):
        """Coordinate check: x=3, y=6, columns=12 → local_id = 3 + 6*12 = 75."""
        local_id = BRIDGE_TILE_X + BRIDGE_TILE_Y * COLUMNS
        assert local_id == 75

    def test_bridge_tile_depth_is_zero(self):
        """TC-BRIDGE-001a RED: tile 75 doit avoir depth=0 pour que le joueur soit au-dessus."""
        local_id = BRIDGE_TILE_X + BRIDGE_TILE_Y * COLUMNS
        depth = _effective_depth(DECORATIONS_TSX, local_id)
        assert depth == 0, (
            f"Tile local_id={local_id} dans 02-decorations.tsx a depth={depth}, "
            f"attendu depth=0. Le joueur passe derrière le pont."
        )

    def test_bridge_tile_is_walkable(self):
        """TC-BRIDGE-001b RED: tile 75 doit être walkable=True."""
        local_id = BRIDGE_TILE_X + BRIDGE_TILE_Y * COLUMNS
        walkable = _effective_walkable(DECORATIONS_TSX, local_id)
        assert walkable is True, (
            f"Tile local_id={local_id} dans 02-decorations.tsx est walkable={walkable}, "
            f"attendu True."
        )


# ---------------------------------------------------------------------------
# TC-PARSER-CLASS-001 : flattening des class properties Tiled
# ---------------------------------------------------------------------------

class TestClassPropertyFlattening:
    """TC-PARSER-CLASS-001: _parse_tileset_properties doit flattener les class properties."""

    def _make_parser(self) -> TmjParser:
        with patch("src.map.tmj_parser.os.path.exists", return_value=False):
            return TmjParser()

    def _parse_props(self, xml_str: str) -> dict:
        root = ET.fromstring(xml_str)
        parser = self._make_parser()
        return parser._parse_tileset_properties(root)

    def test_flat_bool_property_still_works(self):
        """TC-PARSER-CLASS-001a: regression — les props flat existantes ne sont pas cassées."""
        xml = (
            '<tileset>'
            '  <properties>'
            '    <property name="walkable" type="bool" value="false"/>'
            '  </properties>'
            '</tileset>'
        )
        props = self._parse_props(xml)
        assert props["walkable"] is False

    def test_class_property_children_are_flattened(self):
        """
        TC-PARSER-CLASS-001b RED:
        Une <property type="class"> contient des enfants <properties><property .../>.
        Ces enfants doivent être flattened dans le dict résultat.
        """
        xml = (
            '<tileset>'
            '  <properties>'
            '    <property name="material" value="water"/>'
            '    <property name="tileset" type="class" propertytype="00-tileset">'
            '      <properties>'
            '        <property name="walkable" type="bool" value="false"/>'
            '        <property name="depth" type="int" value="0"/>'
            '      </properties>'
            '    </property>'
            '  </properties>'
            '</tileset>'
        )
        props = self._parse_props(xml)
        assert props.get("walkable") is False, (
            "walkable=false dans une class property n'est pas flattené. "
            "Le parseur doit lire les <properties> enfants d'un <property type='class'>."
        )
        assert props.get("depth") == 0
        assert props.get("material") == "water"

    def test_class_property_does_not_override_flat_property(self):
        """
        TC-PARSER-CLASS-001c: si une prop flat et une class prop ont le même nom,
        la prop flat (déclarée avant) a priorité.
        """
        xml = (
            '<tileset>'
            '  <properties>'
            '    <property name="walkable" type="bool" value="true"/>'
            '    <property name="container" type="class" propertytype="foo">'
            '      <properties>'
            '        <property name="walkable" type="bool" value="false"/>'
            '      </properties>'
            '    </property>'
            '  </properties>'
            '</tileset>'
        )
        props = self._parse_props(xml)
        # Flat prop declared first → its value is set, class child should not overwrite it
        assert props.get("walkable") is True


# ---------------------------------------------------------------------------
# TC-WATER-001 : eau non-walkable via le parseur Python
# ---------------------------------------------------------------------------

class TestWaterTileset:
    """TC-WATER-001: le parseur Python doit lire walkable=false du tileset eau."""

    def _load_water_tileset_props(self) -> dict:
        """Parse le tileset water via TmjParser._parse_tileset_properties."""
        with patch("src.map.tmj_parser.os.path.exists", return_value=False):
            parser = TmjParser()
        tree = ET.parse(WATER_TSX)
        root = tree.getroot()
        return parser._parse_tileset_properties(root)

    def test_parser_reads_walkable_false_from_water_tileset(self):
        """
        TC-WATER-001a RED: le parseur doit extraire walkable=False
        depuis la class property imbriquée du tileset 01-water.tsx.
        """
        props = self._load_water_tileset_props()
        assert props.get("walkable") is False, (
            "Le parseur Python ne lit pas walkable=false depuis la class property "
            "imbriquée du tileset 01-water.tsx. "
            "Sans flattening, le hard default walkable=True s'applique."
        )
