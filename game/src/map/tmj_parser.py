import json
import os
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pygame
from src.engine.engine_constants import TILED_PROJECT_PATH
from src.map.project_schema import TiledProject


@dataclass
class TileMapData:
    image: pygame.Surface
    depth: int
    walkable: bool
    direction_flags: set[str] | None = None
    frames: list[tuple[int, int]] | None = None
    occluded_image: pygame.Surface | None = None
    properties: dict[str, Any] | None = None


class TmjParser:
    """Parser for Tiled (.tmj) map files and their associated external (.tsx) tilesets."""

    def __init__(self):
        self.project: TiledProject | None = None
        # Attempt to load project from standard location
        project_path = TILED_PROJECT_PATH
        if os.path.exists(project_path):
            self.project = TiledProject(project_path)

    def load_map(self, tmj_path: str) -> dict[str, Any]:
        """Loads a .tmj file and resolves all local and external dependencies recursively."""
        if not os.path.exists(tmj_path):
            if not tmj_path.startswith("assets"):
                # Fallback to absolute if needed but try relative first
                tmj_path = str(Path.cwd() / tmj_path)
            if not os.path.exists(tmj_path):
                raise FileNotFoundError(f"Map file not found: {tmj_path}")

        with open(tmj_path, encoding="utf-8") as f:
            data = json.load(f)

        # Boundary validation
        if "layers" not in data or "tilesets" not in data:
            raise ValueError("Invalid TMJ format: Missing 'layers' or 'tilesets' keys.")

        map_result = {
            "width": data["width"],
            "height": data["height"],
            "layers": {},
            "tiles": {},
            "layer_names": {},  # Store ID -> Name mapping
            "layer_order": [],  # Store IDs in parsing order
            "layer_order_values": {},  # Store ID -> order property value
            "spawn_player": None,
            "entities": [],  # All objects from Sprites group
            "properties": {p["name"]: p["value"] for p in data.get("properties", [])},
        }

        # 1. Parse tilesets
        for ts in data["tilesets"]:
            firstgid = ts["firstgid"]
            source = ts["source"]
            # Join relative to map file
            tsx_path = str((Path(tmj_path).parent / source).resolve())
            self._parse_tsx(tsx_path, firstgid, map_result["tiles"])

        # 2. Parse layers recursively
        self._process_layers(data["layers"], data["width"], map_result)

        return map_result

    def _process_layers(self, layers: list, map_width: int, map_result: dict[str, Any]):
        """Recursively walk through groups and parse layers/objects."""
        for layer in layers:
            l_type = layer.get("type")
            l_name = layer.get("name")

            if l_type == "tilelayer":
                l_id = layer.get("id")
                map_result["layer_names"][l_id] = l_name
                map_result["layer_order"].append(l_id)
                # Extract the `order` property (int) — authoritative render order
                layer_props = {p["name"]: p["value"] for p in layer.get("properties", [])}
                map_result.setdefault("layer_order_values", {})[l_id] = layer_props.get("order", 0)
                self._parse_tilelayer(layer, map_width, map_result["layers"])
            elif l_type == "group":
                self._process_layers(layer.get("layers", []), map_width, map_result)
            elif l_type == "objectgroup":
                # Collect entities from any objectgroup
                self._parse_objects(layer, map_result)

    def _parse_objects(self, layer_data: dict[str, Any], map_result: dict[str, Any]):
        """Parse all objects in an objectgroup and identify specific targets like player spawn."""
        for obj in layer_data.get("objects", []):
            # Parse custom properties
            props = {}
            for p in obj.get("properties", []):
                props[p.get("name")] = p.get("value")

            # Resolve properties via Tiled Project if enabled
            obj_type = obj.get("type", obj.get("class", ""))

            if self.project and obj_type:
                # Use project defaults as base, override with map properties
                props = self.project.resolve(obj_type, props)

            # Map object data for easier consumption
            obj_info = {
                "id": obj.get("id"),
                "name": obj.get("name"),
                "type": obj_type,
                "x": obj.get("x", 0),
                "y": obj.get("y", 0),
                "width": obj.get("width", 0),
                "height": obj.get("height", 0),
                "properties": props,
            }

            # Check for player spawn property or class
            if props.get("spawn_player") is True or obj_info["type"] == "player":
                map_result["spawn_player"] = obj_info

            # Add to general entity list if it's not just a metadata object
            map_result["entities"].append(obj_info)

    def _parse_tsx(self, tsx_path: str, firstgid: int, tile_dict: dict[int, TileMapData]):
        """Parses an external XML tileset (.tsx) and loads images."""
        if not os.path.exists(tsx_path):
            raise FileNotFoundError(f"Tileset file not found: {tsx_path}")

        with open(tsx_path, encoding="utf-8") as f:
            tree = ET.parse(f)
        root = tree.getroot()

        tw_str = root.get("tilewidth")
        th_str = root.get("tileheight")
        if tw_str is None or th_str is None:
            raise ValueError(f"TSX missing tilewidth or tileheight: {tsx_path}")

        tilewidth = int(tw_str)
        tileheight = int(th_str)
        columns = int(root.get("columns", "1"))

        # Load associated image
        image_elem = root.find("image")
        if image_elem is None:
            raise ValueError(f"No <image> tag found in TSX: {tsx_path}")

        img_source = image_elem.get("source")
        if img_source is None:
            raise ValueError(f"Image tag missing source in TSX: {tsx_path}")

        img_path = str((Path(tsx_path).parent / img_source).resolve())
        if not os.path.exists(img_path):
            raise FileNotFoundError(f"Tileset image not found: {img_path}")

        from src.engine.asset_manager import AssetManager

        sheet = AssetManager().get_image(img_path)

        tileset_props = self._parse_tileset_properties(root)
        custom_props, animations = self._parse_tile_properties_and_anims(
            root, firstgid, tileset_props
        )

        tilecount = int(
            root.get(
                "tilecount", (sheet.get_width() // tilewidth) * (sheet.get_height() // tileheight)
            )
        )

        for i in range(tilecount):
            self._process_single_tile(
                i,
                columns,
                tilewidth,
                tileheight,
                firstgid,
                sheet,
                tileset_props,
                custom_props,
                animations,
                tile_dict,
            )

    def _parse_tileset_properties(self, root: ET.Element) -> dict[str, Any]:  # noqa: C901
        tileset_props = {}
        ts_properties_node = root.find("properties")
        if ts_properties_node is None:
            return tileset_props

        for p in ts_properties_node.findall("property"):
            name = p.get("name")
            type_str = p.get("type", "string")

            if type_str == "class":
                # Flatten child properties — do not overwrite already-set flat props
                child_props_node = p.find("properties")
                if child_props_node is not None:
                    for child in child_props_node.findall("property"):
                        child_name = child.get("name")
                        child_val = child.get("value")
                        if child_name is None or child_val is None:
                            continue
                        child_type = child.get("type", "string")
                        if child_name not in tileset_props:
                            if child_type == "bool":
                                tileset_props[child_name] = child_val.lower() == "true"
                            elif child_type == "int":
                                tileset_props[child_name] = int(child_val)
                            else:
                                tileset_props[child_name] = child_val
                continue  # class property itself is not a flat value

            val = p.get("value")
            if name is None or val is None:
                continue
            if type_str == "bool":
                tileset_props[name] = val.lower() == "true"
            elif type_str == "int":
                tileset_props[name] = int(val)
            else:
                tileset_props[name] = val

        return tileset_props

    def _parse_tile_properties_and_anims(  # noqa: C901
        self, root: ET.Element, firstgid: int, tileset_props: dict[str, Any]
    ) -> tuple[dict[int, dict], dict[int, list]]:
        custom_props = {}
        animations = {}
        for tile in root.findall("tile"):
            local_id_str = tile.get("id")
            if local_id_str is None:
                continue
            local_id = int(local_id_str)
            props = {
                "walkable": tileset_props.get("walkable", True),
                "depth": tileset_props.get("depth", 0),
                "direction": tileset_props.get("direction", "any"),
            }

            properties_node = tile.find("properties")
            if properties_node is not None:
                for p in properties_node.findall("property"):
                    name = p.get("name")
                    val = p.get("value")
                    if name is None or val is None:
                        continue
                    type_str = p.get("type", "string")
                    if type_str == "bool":
                        props[name] = val.lower() == "true"
                    elif type_str == "int":
                        props[name] = int(val)
                    else:
                        props[name] = val
            custom_props[local_id] = props

            anim_node = tile.find("animation")
            if anim_node is not None:
                frames = []
                for frame in anim_node.findall("frame"):
                    frames.append(
                        (
                            firstgid + int(frame.get("tileid") or "0"),
                            int(frame.get("duration") or "0"),
                        )
                    )
                if frames:
                    animations[local_id] = frames
        return custom_props, animations

    def _process_single_tile(
        self,
        i: int,
        columns: int,
        tilewidth: int,
        tileheight: int,
        firstgid: int,
        sheet: pygame.Surface,
        tileset_props: dict,
        custom_props: dict,
        animations: dict,
        tile_dict: dict,
    ):
        global_id = firstgid + i
        x = (i % columns) * tilewidth
        y = (i // columns) * tileheight
        rect = pygame.Rect(x, y, tilewidth, tileheight)
        surface = sheet.subsurface(rect).copy()

        props = tileset_props.copy()
        props.update(custom_props.get(i, {}))
        props.setdefault("walkable", True)
        props.setdefault("depth", 0)
        props["tile_id"] = i

        occluded = None
        if props["depth"] > 0:
            from src.config import Settings

            occluded = surface.copy()
            occluded.set_alpha(Settings.OCCLUSION_ALPHA)

        direction_str = str(props.get("direction", "any")).strip() or "any"
        direction_flags = set(d.strip() for d in direction_str.split(",") if d.strip()) or {"any"}

        tile_dict[global_id] = TileMapData(
            image=surface,
            depth=props["depth"],
            walkable=props["walkable"],
            direction_flags=direction_flags,
            frames=animations.get(i),
            occluded_image=occluded,
            properties=props,
        )

    def _parse_tilelayer(
        self, layer_data: dict[str, Any], map_width: int, layers_dict: dict[int, list]
    ):
        """Convert a 1D layer data array into a 2D matrix directly and append to layers_dict."""
        layer_id = layer_data.get("id")
        if layer_id is None:
            return
        raw_data = layer_data.get("data", [])

        # Create 2D chunk equivalent
        matrix = []
        for i in range(0, len(raw_data), map_width):
            matrix.append(raw_data[i : i + map_width])

        layers_dict[layer_id] = matrix
