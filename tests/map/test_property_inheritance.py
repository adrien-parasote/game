"""
TC-PROP-001 à TC-PROP-007 : Héritage de propriétés tileset → tile.

Règles spécifiées :
- Les propriétés du tileset sont les valeurs par défaut (fallback).
- Les propriétés définies explicitement sur une tile surchargent celles du tileset.
- Les propriétés absentes de la tile héritent de la valeur du tileset.
- Les propriétés arbitraires (custom) du tileset sont héritées par toutes les tiles.
- Les propriétés custom définies uniquement sur une tile s'ajoutent aux props tileset.
- Si ni tileset ni tile ne définissent une prop, les hard defaults s'appliquent
  (depth=0, walkable=True, direction="any").
"""

import io
import json
from unittest.mock import MagicMock, patch

import pytest

from src.map.tmj_parser import TmjParser

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_parser() -> TmjParser:
    """Create a TmjParser with no project file."""
    with patch("src.map.tmj_parser.os.path.exists", return_value=False):
        return TmjParser()


def _load_with_tsx(tsx_content: str, tmj_data: dict | None = None) -> dict:
    """Parse a minimal map with a single tileset defined inline via tsx_content."""
    if tmj_data is None:
        tmj_data = {
            "width": 1,
            "height": 1,
            "layers": [],
            "tilesets": [{"firstgid": 1, "source": "tiles.tsx"}],
        }
    parser = _make_parser()

    mock_surf = MagicMock()
    mock_surf.subsurface.return_value.copy.return_value = MagicMock()

    with patch("src.map.tmj_parser.os.path.exists", return_value=True):
        with patch("builtins.open") as mock_open:
            mock_open.side_effect = [
                io.StringIO(json.dumps(tmj_data)),
                io.StringIO(tsx_content),
            ]
            with patch("json.load", return_value=tmj_data):
                with patch("src.engine.asset_manager.AssetManager.get_image", return_value=mock_surf):
                    return parser.load_map("dummy.tmj")


# ---------------------------------------------------------------------------
# TSX builders
# ---------------------------------------------------------------------------

def _tsx(tileset_props: str = "", tile_entries: str = "") -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<tileset name="test" tilewidth="32" tileheight="32" tilecount="4" columns="2">'
        f"{tileset_props}"
        '<image source="tiles.png" width="64" height="64"/>'
        f"{tile_entries}"
        "</tileset>"
    )


def _ts_props(**kwargs) -> str:
    lines = []
    for name, (type_, value) in kwargs.items():
        lines.append(f'<property name="{name}" type="{type_}" value="{value}"/>')
    return f"<properties>{''.join(lines)}</properties>"


def _tile(tid: int, **kwargs) -> str:
    if not kwargs:
        return f'<tile id="{tid}"/>'
    lines = []
    for name, (type_, value) in kwargs.items():
        lines.append(f'<property name="{name}" type="{type_}" value="{value}"/>')
    return f'<tile id="{tid}"><properties>{"".join(lines)}</properties></tile>'


# ---------------------------------------------------------------------------
# TC-PROP-001 : tile NOT in XML → hérite toutes les props du tileset
# ---------------------------------------------------------------------------

class TestTileNotInXML:
    """TC-PROP-001: tile absente du XML hérite depth, walkable, et props custom du tileset."""

    def test_inherits_depth_from_tileset(self):
        tsx = _tsx(
            tileset_props=_ts_props(depth=("int", "2"), walkable=("bool", "false")),
        )
        result = _load_with_tsx(tsx)
        # global_id = firstgid(1) + local_id(0) = 1
        tile = result["tiles"][1]
        assert tile.depth == 2

    def test_inherits_walkable_from_tileset(self):
        tsx = _tsx(
            tileset_props=_ts_props(depth=("int", "2"), walkable=("bool", "false")),
        )
        result = _load_with_tsx(tsx)
        tile = result["tiles"][1]
        assert tile.walkable is False

    def test_inherits_custom_string_prop_from_tileset(self):
        """TC-PROP-001c: prop custom du tileset (material) héritée par tile sans XML."""
        tsx = _tsx(
            tileset_props=_ts_props(
                depth=("int", "0"),
                walkable=("bool", "true"),
                material=("string", "wood"),
            ),
        )
        result = _load_with_tsx(tsx)
        tile = result["tiles"][1]
        assert tile.properties.get("material") == "wood"


# ---------------------------------------------------------------------------
# TC-PROP-002 : tile dans le XML avec AUCUNE propriété → hérite tileset
# ---------------------------------------------------------------------------

class TestTileInXMLNoProperties:
    """TC-PROP-002: tile déclarée dans XML mais sans <properties> hérite tileset."""

    def test_inherits_depth_when_no_properties_node(self):
        tsx = _tsx(
            tileset_props=_ts_props(depth=("int", "2"), walkable=("bool", "false")),
            tile_entries='<tile id="0"/>',  # déclarée mais sans props
        )
        result = _load_with_tsx(tsx)
        tile = result["tiles"][1]
        assert tile.depth == 2

    def test_inherits_walkable_when_no_properties_node(self):
        tsx = _tsx(
            tileset_props=_ts_props(depth=("int", "2"), walkable=("bool", "false")),
            tile_entries='<tile id="0"/>',
        )
        result = _load_with_tsx(tsx)
        tile = result["tiles"][1]
        assert tile.walkable is False


# ---------------------------------------------------------------------------
# TC-PROP-003 : tile avec seulement depth → walkable hérite du tileset
# ---------------------------------------------------------------------------

class TestPartialTileOverride:
    """TC-PROP-003: override partiel — seul depth est défini, walkable hérite du tileset."""

    def test_depth_overridden_walkable_inherited(self):
        tsx = _tsx(
            tileset_props=_ts_props(depth=("int", "2"), walkable=("bool", "false")),
            tile_entries=_tile(0, depth=("int", "0")),
        )
        result = _load_with_tsx(tsx)
        tile = result["tiles"][1]
        assert tile.depth == 0, "depth doit être overridé par la tile"
        assert tile.walkable is False, "walkable doit fallback sur le tileset"

    def test_walkable_overridden_depth_inherited(self):
        tsx = _tsx(
            tileset_props=_ts_props(depth=("int", "2"), walkable=("bool", "false")),
            tile_entries=_tile(0, walkable=("bool", "true")),
        )
        result = _load_with_tsx(tsx)
        tile = result["tiles"][1]
        assert tile.walkable is True, "walkable doit être overridé par la tile"
        assert tile.depth == 2, "depth doit fallback sur le tileset"


# ---------------------------------------------------------------------------
# TC-PROP-004 : tile avec prop custom supplémentaire → s'ajoute aux props tileset
# ---------------------------------------------------------------------------

class TestTileAdditionalProperties:
    """TC-PROP-004: prop custom uniquement sur la tile → présente dans properties."""

    def test_tile_only_prop_is_captured(self):
        tsx = _tsx(
            tileset_props=_ts_props(depth=("int", "0"), walkable=("bool", "true")),
            tile_entries=_tile(0, depth=("int", "0"), walkable=("bool", "true"), material=("string", "stone")),
        )
        result = _load_with_tsx(tsx)
        tile = result["tiles"][1]
        assert tile.properties.get("material") == "stone"

    def test_tileset_custom_prop_plus_tile_custom_prop(self):
        """TC-PROP-004b: tileset a 'biome', tile ajoute 'material' → les deux dans properties."""
        tsx = _tsx(
            tileset_props=_ts_props(
                depth=("int", "0"),
                walkable=("bool", "true"),
                biome=("string", "forest"),
            ),
            tile_entries=_tile(0, material=("string", "grass")),
        )
        result = _load_with_tsx(tsx)
        tile = result["tiles"][1]
        assert tile.properties.get("biome") == "forest", "biome doit être hérité du tileset"
        assert tile.properties.get("material") == "grass", "material doit être ajouté par la tile"


# ---------------------------------------------------------------------------
# TC-PROP-005 : ni tileset ni tile → hard defaults (depth=0, walkable=True)
# ---------------------------------------------------------------------------

class TestHardDefaults:
    """TC-PROP-005: aucune prop nulle part → hard defaults appliqués."""

    def test_depth_defaults_to_zero(self):
        tsx = _tsx()  # pas de props tileset, pas de tile XML
        result = _load_with_tsx(tsx)
        tile = result["tiles"][1]
        assert tile.depth == 0

    def test_walkable_defaults_to_true(self):
        tsx = _tsx()
        result = _load_with_tsx(tsx)
        tile = result["tiles"][1]
        assert tile.walkable is True

    def test_direction_defaults_to_any(self):
        tsx = _tsx()
        result = _load_with_tsx(tsx)
        tile = result["tiles"][1]
        assert tile.direction_flags == {"any"}


# ---------------------------------------------------------------------------
# TC-PROP-006 : tile override complet → toutes les props tileset surchargées
# ---------------------------------------------------------------------------

class TestFullTileOverride:
    """TC-PROP-006: tile définit toutes les props → aucune inheritance du tileset."""

    def test_all_props_overridden(self):
        tsx = _tsx(
            tileset_props=_ts_props(depth=("int", "2"), walkable=("bool", "false")),
            tile_entries=_tile(0, depth=("int", "0"), walkable=("bool", "true")),
        )
        result = _load_with_tsx(tsx)
        tile = result["tiles"][1]
        assert tile.depth == 0
        assert tile.walkable is True


# ---------------------------------------------------------------------------
# TC-PROP-007 : tileset a direction, tile sans direction → héritage direction
# ---------------------------------------------------------------------------

class TestDirectionInheritance:
    """TC-PROP-007: direction définie au niveau tileset héritée par la tile."""

    def test_tileset_direction_inherited_by_tile_without_direction(self):
        tsx = _tsx(
            tileset_props=_ts_props(direction=("string", "up,down")),
            tile_entries='<tile id="0"/>',
        )
        result = _load_with_tsx(tsx)
        tile = result["tiles"][1]
        assert tile.direction_flags == {"up", "down"}

    def test_tile_direction_overrides_tileset(self):
        tsx = _tsx(
            tileset_props=_ts_props(direction=("string", "up,down")),
            tile_entries=_tile(0, direction=("string", "left")),
        )
        result = _load_with_tsx(tsx)
        tile = result["tiles"][1]
        assert tile.direction_flags == {"left"}
