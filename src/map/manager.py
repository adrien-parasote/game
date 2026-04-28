from typing import List, Optional, Tuple, Iterator
import math
from .layout import LayoutStrategy

class MapManager:
    """Manages map data, tile access, and coordinate transformations."""
    
    def __init__(self, map_data: dict, layout: LayoutStrategy):
        self.layers = map_data.get("layers", {})
        self.tiles = map_data.get("tiles", {})
        self.layer_names = map_data.get("layer_names", {})
        
        # Sort layer_order: prioritize name-based ordering (00-, 01-, etc.)
        # This ensures '00-layer' is always rendered first (at the bottom)
        raw_order = map_data.get("layer_order", [])
        self.layer_order = sorted(
            raw_order,
            key=lambda lid: (self.layer_names.get(lid, ""))
        )
        
        self.layout = layout
        
        first_layer = next(iter(self.layers.values()), [])
        self.height = len(first_layer)
        self.width = len(first_layer[0]) if self.height > 0 else 0

        
        self.cached_surfaces = {}
        
    def get_layer_surface(self, layer_id: int, pygame_module) -> "pygame.Surface":
        """Get or create a pre-rendered surface for a specific layer."""
        if layer_id in self.cached_surfaces:
            return self.cached_surfaces[layer_id]
            
        tile_size = getattr(self.layout, "tile_size", 32)
        width_px = self.width * tile_size
        height_px = self.height * tile_size
        
        try:
            surface = pygame_module.Surface((width_px, height_px), pygame_module.SRCALPHA)
            layer_data = self.layers[layer_id]
            
            for y in range(self.height):
                for x in range(self.width):
                    tile_id = layer_data[y][x]
                    if tile_id != 0 and tile_id in self.tiles:
                        tile_img = self.tiles[tile_id].image
                        px, py = self.layout.to_screen(x, y)
                        surface.blit(tile_img, (px, py))
            
            self.cached_surfaces[layer_id] = surface
            return surface
        except Exception as e:
            import logging
            logging.error(f"Failed to pre-render layer {layer_id}: {e}")
            return None

    def is_collidable(self, x: int, y: int) -> bool:
        """Check if any layer at the given (x,y) coordinates contains a collidable tile."""
        if not (0 <= y < self.height and 0 <= x < self.width):
            return True # Out of bounds blocks movement
            
        for layer_data in self.layers.values():
            tile_id = layer_data[y][x]
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
        
        for layer_id in self.layer_order:
            layer_data = self.layers[layer_id]
            for y in range(start_row, end_row):
                for x in range(start_col, end_col):
                    tile_id = layer_data[y][x]
                    if tile_id != 0:
                        depth = getattr(self.tiles.get(tile_id), "depth", 0)
                        px, py = self.layout.to_screen(x, y)
                        yield (int(px), int(py), tile_id, depth)
