from typing import List, Optional, Tuple, Iterator
import math
from .layout import LayoutStrategy

class MapManager:
    """Manages map data, tile access, and coordinate transformations."""
    
    def __init__(self, map_data: dict, layout: LayoutStrategy):
        self.layers = map_data.get("layers", {})
        self.tiles = map_data.get("tiles", {})
        self.layout = layout
        
        first_layer = next(iter(self.layers.values()), [])
        self.height = len(first_layer)
        self.width = len(first_layer[0]) if self.height > 0 else 0

    def get_tile(self, layer_id: int, x: int, y: int) -> Optional[int]:
        """Get tile value at tile coordinates (x, y) on a specific layer."""
        if layer_id in self.layers and 0 <= y < self.height and 0 <= x < self.width:
            return self.layers[layer_id][y][x]
        return None

    def get_tile_at_px(self, layer_id: int, px: float, py: float) -> Optional[int]:
        """Get tile value at screen pixel coordinates (px, py) on a specific layer."""
        wx, wy = self.layout.to_world(px, py)
        # We use floor to get the tile index
        return self.get_tile(layer_id, int(wx), int(wy))
        
    def is_collidable(self, x: int, y: int) -> bool:
        """Check if any layer at the given (x,y) coordinates contains a collidable tile."""
        if not (0 <= y < self.height and 0 <= x < self.width):
            return True # Out of bounds blocks movement
            
        for layer_id in self.layers.values():
            tile_id = layer_id[y][x]
            if tile_id in self.tiles and getattr(self.tiles[tile_id], "collidable", False):
                return True
        return False

    def get_visible_chunks(self, viewport_rect: "pygame.Rect") -> Iterator[Tuple[int, int, int, int]]:
        """
        Calculate and return an iterator of (x_px, y_px, tile_id, depth) 
        that are currently visible within the viewport_rect (world pixels).
        """
        tile_size = getattr(self.layout, "tile_size", 32) # Fallback to 32

        # Calculate start and end indices using math boundaries (O(1) range calculation)
        start_col = max(0, int(viewport_rect.left // tile_size))
        end_col = min(self.width, int(math.ceil(viewport_rect.right / tile_size)))
        
        start_row = max(0, int(viewport_rect.top // tile_size))
        end_row = min(self.height, int(math.ceil(viewport_rect.bottom / tile_size)))
        
        for layer_id in sorted(self.layers.keys()):
            layer_data = self.layers[layer_id]
            for y in range(start_row, end_row):
                for x in range(start_col, end_col):
                    tile_id = layer_data[y][x]
                    if tile_id != 0:
                        depth = getattr(self.tiles.get(tile_id), "depth", 0)
                        px, py = self.layout.to_screen(x, y)
                        yield (int(px), int(py), tile_id, depth)
