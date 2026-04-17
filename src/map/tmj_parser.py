import os
import json
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Dict, Any, Optional
import pygame

@dataclass
class TileMapData:
    image: pygame.Surface
    depth: int
    collidable: bool

class TmjParser:
    """Parser for Tiled (.tmj) map files and their associated external (.tsx) tilesets."""
    
    def load_map(self, tmj_path: str) -> Dict[str, Any]:
        """Loads a .tmj file and resolves all local and external dependencies recursively."""
        if not os.path.exists(tmj_path):
            if not tmj_path.startswith("assets"):
                # Fallback to absolute if needed but try relative first
                tmj_path = os.path.join(os.getcwd(), tmj_path)
            if not os.path.exists(tmj_path):
                raise FileNotFoundError(f"Map file not found: {tmj_path}")
            
        with open(tmj_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        # Boundary validation
        if "layers" not in data or "tilesets" not in data:
            raise ValueError("Invalid TMJ format: Missing 'layers' or 'tilesets' keys.")
            
        map_result = {
            "layers": {},
            "tiles": {},
            "spawn_player": None,
            "entities": [] # All objects from Sprites group
        }
        
        # 1. Parse tilesets
        for ts in data["tilesets"]:
            firstgid = ts["firstgid"]
            source = ts["source"]
            # Join relative to map file
            tsx_path = os.path.normpath(os.path.join(os.path.dirname(tmj_path), source))
            self._parse_tsx(tsx_path, firstgid, map_result["tiles"])
            
        # 2. Parse layers recursively
        self._process_layers(data["layers"], data["width"], map_result)
        
        return map_result

    def _process_layers(self, layers: list, map_width: int, map_result: Dict[str, Any]):
        """Recursively walk through groups and parse layers/objects."""
        for layer in layers:
            l_type = layer.get("type")
            l_name = layer.get("name")
            
            if l_type == "tilelayer":
                self._parse_tilelayer(layer, map_width, map_result["layers"])
            elif l_type == "group":
                self._process_layers(layer.get("layers", []), map_width, map_result)
            elif l_type == "objectgroup":
                # Collect entities from any objectgroup
                self._parse_objects(layer, map_result)

    def _parse_objects(self, layer_data: Dict[str, Any], map_result: Dict[str, Any]):
        """Parse all objects in an objectgroup and identify specific targets like player spawn."""
        for obj in layer_data.get("objects", []):
            # Parse custom properties
            props = {}
            for p in obj.get("properties", []):
                props[p.get("name")] = p.get("value")
            
            # Map object data for easier consumption
            obj_info = {
                "id": obj.get("id"),
                "name": obj.get("name"),
                "type": obj.get("type", obj.get("class", "")), # 'class' in 1.10+, 'type' in older
                "x": obj.get("x", 0),
                "y": obj.get("y", 0),
                "width": obj.get("width", 0),
                "height": obj.get("height", 0),
                "properties": props
            }
            
            # Check for player spawn property or class
            if props.get("spawn_player") is True or obj_info["type"] == "player":
                map_result["spawn_player"] = obj_info
            
            # Add to general entity list if it's not just a metadata object
            map_result["entities"].append(obj_info)

    def _parse_tsx(self, tsx_path: str, firstgid: int, tile_dict: Dict[int, TileMapData]):
        """Parses an external XML tileset (.tsx) and loads images."""
        if not os.path.exists(tsx_path):
            raise FileNotFoundError(f"Tileset file not found: {tsx_path}")
            
        with open(tsx_path, 'r', encoding='utf-8') as f:
            tree = ET.parse(f)
        root = tree.getroot()
        
        tilewidth = int(root.get("tilewidth"))
        tileheight = int(root.get("tileheight"))
        columns = int(root.get("columns", 1)) # Fallback 1 if missing
        
        # Load associated image
        image_elem = root.find("image")
        if image_elem is None:
            raise ValueError(f"No <image> tag found in TSX: {tsx_path}")
            
        img_source = image_elem.get("source")
        img_path = os.path.normpath(os.path.join(os.path.dirname(tsx_path), img_source))
        
        if not os.path.exists(img_path):
            raise FileNotFoundError(f"Tileset image not found: {img_path}")
            
        sheet = pygame.image.load(img_path).convert_alpha()
        
        # Find explicit custom properties for tiles if any
        custom_props = {}
        for tile in root.findall("tile"):
            local_id = int(tile.get("id"))
            props = {"collidable": False, "depth": 0}
            
            properties_node = tile.find("properties")
            if properties_node is not None:
                for p in properties_node.findall("property"):
                    name = p.get("name")
                    val = p.get("value")
                    type_str = p.get("type", "string")
                    
                    if type_str == "bool":
                        props[name] = val.lower() == "true"
                    elif type_str == "int":
                        props[name] = int(val)
                    else:
                        props[name] = val
            custom_props[local_id] = props
                        
        # Slice image into single tiles based on tilecount.
        # TSX tilecount is present, or inferred
        tilecount = int(root.get("tilecount", (sheet.get_width() // tilewidth) * (sheet.get_height() // tileheight)))
        
        for i in range(tilecount):
            global_id = firstgid + i
            # Calculate rect bounds
            x = (i % columns) * tilewidth
            y = (i // columns) * tileheight
            
            rect = pygame.Rect(x, y, tilewidth, tileheight)
            surface = sheet.subsurface(rect).copy() # isolated copy
            
            # Fetch properties or defaults
            props = custom_props.get(i, {"collidable": False, "depth": 0})
            
            tile_dict[global_id] = TileMapData(
                image=surface,
                depth=props["depth"],
                collidable=props["collidable"]
            )
            
    def _parse_tilelayer(self, layer_data: Dict[str, Any], map_width: int, layers_dict: Dict[int, list]):
        """Convert a 1D layer data array into a 2D matrix directly and append to layers_dict."""
        layer_id = layer_data.get("id")
        raw_data = layer_data.get("data", [])
        
        # Create 2D chunk equivalent
        matrix = []
        for i in range(0, len(raw_data), map_width):
            matrix.append(raw_data[i:i+map_width])
            
        layers_dict[layer_id] = matrix
        
    def _parse_player_spawn(self, sub_layer: Dict[str, Any], map_result: Dict[str, Any]):
        """Find the spawn_player object."""
        for obj in sub_layer.get("objects", []):
            if obj.get("name") == "spawn_player":
                map_result["spawn_player"] = {
                    "x": obj.get("x", 0),
                    "y": obj.get("y", 0)
                }
                break
