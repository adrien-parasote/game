import math
from collections.abc import Iterator

import pygame

from .layout import LayoutStrategy


class MapManager:
    """Manages map data, tile access, and coordinate transformations."""

    def __init__(self, map_data: dict, layout: LayoutStrategy):
        self.layers = map_data.get("layers", {})
        self.tiles = map_data.get("tiles", {})
        self.layer_names = map_data.get("layer_names", {})
        self._entities = map_data.get("entities", [])

        # Sort layer_order by the `order` property (int) from Tiled layer properties.
        # Falls back to 0 if the property is absent (e.g., base layer with no explicit order).
        raw_order = map_data.get("layer_order", [])
        order_values = map_data.get("layer_order_values", {})
        self.layer_order = sorted(raw_order, key=lambda lid: order_values.get(lid, 0))

        self.layout = layout
        self.name = map_data.get("properties", {}).get("name", "")

        first_layer = next(iter(self.layers.values()), [])
        self.height = len(first_layer)
        self.width = len(first_layer[0]) if self.height > 0 else 0

        # layer_depths: layer_id -> order value.
        # Used to decide if the layer is rendered in the background (order <= player.depth)
        # or foreground (order > player.depth). This is the layer-level Z position.
        self.layer_depths = {
            lid: order_values.get(lid, 0) for lid in self.layer_order
        }

        # layer_max_depths: max per-tile depth within each layer.
        # Used in get_visible_chunks to skip layers that have no foreground tiles.
        # Intentionally NOT seeded from layer_depths (order) to keep the two concepts separate.
        self.layer_max_depths = {}
        for layer_id in self.layer_order:
            max_d = 0
            if layer_id in self.layers:
                for row in self.layers[layer_id]:
                    for tid in row:
                        if tid != 0 and tid in self.tiles:
                            d = self.tiles[tid].depth
                            if isinstance(d, int) and d > max_d:
                                max_d = d
            self.layer_max_depths[layer_id] = max_d

        self.cached_surfaces = {}
        self._window_cache = None

    def get_layer_surface(self, layer_id: int, pygame_module, max_bg_depth: int = 1) -> pygame.Surface | None:
        """Get or create a pre-rendered surface for a specific layer."""
        # We cache by layer_id. If max_bg_depth changes, this could be an issue, but player depth is static at 1.
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
                        if self.tiles[tile_id].frames:
                            continue
                        tile_depth = self.tiles[tile_id].depth
                        if tile_depth > max_bg_depth:
                            continue
                        tile_img = self.tiles[tile_id].image
                        px, py = self.layout.to_screen(x, y)
                        surface.blit(tile_img, (px, py))

            self.cached_surfaces[layer_id] = surface
            return surface
        except Exception as e:
            import logging

            logging.error(f"Failed to pre-render layer {layer_id}: {e}")
            return None

    def is_walkable(self, x: int, y: int) -> bool:
        """Check walkability at (x, y).

        Only depth=0 tiles (ground/floor tiles) determine walkability.
        Depth≥1 tiles are visual decorations or foreground walls; they are
        rendered above/over the player but must not influence movement collision.

        Algorithm: scan layers from highest to lowest order, find the first
        non-empty depth=0 tile, and return its walkable property.

        Returns False if out of bounds or if no depth=0 tile exists at (x, y).
        """
        if not (0 <= y < self.height and 0 <= x < self.width):
            return False

        for layer_id in reversed(self.layer_order):
            if layer_id not in self.layers:
                continue
            tile_id = self.layers[layer_id][y][x]
            if tile_id == 0 or tile_id not in self.tiles:
                continue
            tile = self.tiles[tile_id]
            if getattr(tile, "depth", 0) != 0:
                continue  # Skip visual/foreground decorations
            return bool(tile.walkable)

        return False  # No depth=0 ground tile at this position



    def get_direction_flags(self, x: int, y: int) -> set[str]:
        """Return the intersection of direction_flags across all layers at (x, y).

        Rules:
        - A layer with ``{"any"}`` imposes no constraint (neutral joker).
        - A layer with specific directions (e.g. ``{"down", "left"}``) restricts movement.
        - The result is the intersection of all constrained layers.
        - If no layer has a specific constraint, returns ``{"any"}``.
        """
        if not (0 <= y < self.height and 0 <= x < self.width):
            return {"any"}

        constrained: list[set[str]] = []
        for layer_id in self.layer_order:
            if layer_id not in self.layers:
                continue
            tile_id = self.layers[layer_id][y][x]
            if tile_id not in self.tiles:
                continue
            flags = self.tiles[tile_id].direction_flags
            if flags is not None and "any" not in flags:
                constrained.append(flags)

        if not constrained:
            return {"any"}

        result = constrained[0].copy()
        for flags in constrained[1:]:
            result &= flags
        return result if result else set()

    def get_visible_chunks(
        self, viewport_rect: pygame.Rect, min_depth: int | None = None
    ) -> Iterator[tuple[int, int, int, int]]:
        """
        Calculate and return an iterator of (x_px, y_px, tile_id, depth)
        that are currently visible within the viewport_rect (world pixels).
        Skips animated tiles (which are handled by get_visible_animated_chunks).

        When min_depth is set (used by draw_foreground):
        - Layers with order > min_depth are included entirely (all their tiles).
        - Layers with order <= min_depth are included only if they contain tiles
          with depth > min_depth (per-tile check, for multi-depth layers).
        """
        tile_size = self.layout.tile_size  # direct attr — always OrthogonalLayout
        ts = tile_size  # local alias for tight loop

        # Calculate start and end indices using math boundaries (O(1) range calculation)
        start_col = max(0, int(viewport_rect.left // tile_size))
        end_col = min(self.width, int(math.ceil(viewport_rect.right / tile_size)))

        start_row = max(0, int(viewport_rect.top // tile_size))
        end_row = min(self.height, int(math.ceil(viewport_rect.bottom / tile_size)))

        for layer_id in self.layer_order:
            layer_order_val = self.layer_depths.get(layer_id, 0)
            is_foreground_layer = False

            if min_depth is not None:
                # Pure foreground layer (order > player depth): include all its tiles
                is_foreground_layer = layer_order_val > min_depth
                # Mixed layer: include only if it has some tiles with depth > min_depth
                if not is_foreground_layer and self.layer_max_depths.get(layer_id, 0) <= min_depth:
                    continue

            layer_data = self.layers[layer_id]
            for y in range(start_row, end_row):
                py = y * ts  # inline to_screen — eliminates method call per tile
                for x in range(start_col, end_col):
                    tile_id = layer_data[y][x]
                    if tile_id != 0:
                        tile = self.tiles.get(tile_id)
                        if tile and tile.frames:
                            continue
                        depth = tile.depth if tile else 0
                        # For mixed-depth layers (order <= min_depth), skip background tiles
                        if min_depth is not None and not is_foreground_layer and depth <= min_depth:
                            continue
                        yield (x * ts, py, tile_id, depth)


    def get_visible_animated_chunks(
        self, viewport_rect: pygame.Rect, layer_id: int | None = None
    ) -> Iterator[tuple[int, int, int, int]]:
        """
        Yields (x_px, y_px, tile_id, depth) for tiles within viewport
        that have animation frames.
        If layer_id is given, only yields tiles from that specific layer.
        """
        tile_size = self.layout.tile_size
        ts = tile_size

        start_col = max(0, int(viewport_rect.left // tile_size))
        end_col = min(self.width, int(math.ceil(viewport_rect.right / tile_size)))

        start_row = max(0, int(viewport_rect.top // tile_size))
        end_row = min(self.height, int(math.ceil(viewport_rect.bottom / tile_size)))

        layers_to_scan = [layer_id] if layer_id is not None else self.layer_order
        for lid in layers_to_scan:
            if lid not in self.layers:
                continue
            layer_data = self.layers[lid]
            for y in range(start_row, end_row):
                py = y * ts
                for x in range(start_col, end_col):
                    tile_id = layer_data[y][x]
                    if tile_id != 0 and tile_id in self.tiles:
                        tile = self.tiles[tile_id]
                        if tile.frames:
                            yield (x * ts, py, tile_id, tile.depth)

    def get_window_positions(self) -> list[tuple[int, int, int]]:
        """
        Return beam-emitter specs for window light effects as (cx, y, width) tuples:
          - cx    : horizontal center of the beam origin (pixels)
          - y     : vertical start of the beam (pixels)
          - width : width of the beam top (pixels), matching the window width

        Priority:
        1. Tiled rectangle objects with type='18-light' — pixel-precise.
        2. Fallback: tiles with property type='window' (tile-grid aligned).
        """
        if self._window_cache is not None:
            return self._window_cache

        # --- Priority 1: explicit 18-light rectangle objects ---
        object_specs = [
            (int(e["x"] + e["width"] / 2), int(e["y"]), int(e["width"]))
            for e in self._entities
            if e.get("type") == "18-light"
        ]
        if object_specs:
            self._window_cache = object_specs
            return self._window_cache

        # --- Priority 2: tile property fallback ---
        tile_size = getattr(self.layout, "tile_size", 32)
        tile_positions = []
        for layer_id in self.layer_order:
            layer_data = self.layers[layer_id]
            for y in range(self.height):
                for x in range(self.width):
                    tile_id = layer_data[y][x]
                    if tile_id == 0 or tile_id not in self.tiles:
                        continue
                    props = getattr(self.tiles[tile_id], "properties", {}) or {}
                    if props.get("type") == "window":
                        px, py = self.layout.to_screen(x, y)
                        tile_positions.append(
                            (int(px + tile_size // 2), int(py + tile_size), tile_size)
                        )

        self._window_cache = tile_positions
        return self._window_cache

    def get_terrain_material_at(self, pixel_x: int, pixel_y: int) -> str | None:
        """Return the material of the highest depth≤1 tile at the given pixel position.

        Tiles with depth>1 (roofs, ceilings, elevated decorations) are ignored —
        only ground-level tiles (depth=0) and floor-level tiles (depth=1, e.g. planks,
        bridges) contribute to the terrain material used for footstep audio (BUG-SFX-001).
        """
        grid_pos = self.layout.to_world(pixel_x, pixel_y)
        tx, ty = int(grid_pos[0]), int(grid_pos[1])

        if not (0 <= ty < self.height and 0 <= tx < self.width):
            return None

        # Scan layers top-to-bottom, skip tiles with depth>1
        for layer_id in reversed(self.layer_order):
            layer_data = self.layers.get(layer_id)
            if not layer_data:
                continue

            tile_id = layer_data[ty][tx]
            if tile_id == 0 or tile_id not in self.tiles:
                continue

            tile = self.tiles[tile_id]
            if getattr(tile, "depth", 0) > 1:
                continue  # Roof/ceiling tiles don't determine the sound underfoot

            props = getattr(tile, "properties", {}) or {}
            if "material" in props:
                return props["material"]

        return None

    def get_grass_tile_image_at(self, pixel_x: int, pixel_y: int) -> "pygame.Surface | None":
        """Return the image surface of the grass tile at pixel_x, pixel_y, or None.

        Identical scan logic to get_terrain_material_at():
        - Scans layers top-to-bottom (reversed layer_order)
        - Skips tiles with depth > 1 (roofs, ceilings)
        - Returns tile.image when the topmost depth≤1 tile has material == "grass"
        - Returns None if position is out of bounds, no tile is found, or material != "grass"
        """
        grid_pos = self.layout.to_world(pixel_x, pixel_y)
        tx, ty = int(grid_pos[0]), int(grid_pos[1])

        if not (0 <= ty < self.height and 0 <= tx < self.width):
            return None

        for layer_id in reversed(self.layer_order):
            layer_data = self.layers.get(layer_id)
            if not layer_data:
                continue

            tile_id = layer_data[ty][tx]
            if tile_id == 0 or tile_id not in self.tiles:
                continue

            tile = self.tiles[tile_id]
            if getattr(tile, "depth", 0) > 1:
                continue  # Roof/ceiling tiles are not grass

            props = getattr(tile, "properties", {}) or {}
            if props.get("material") == "grass":
                return tile.image
            # A non-grass tile at depth≤1 is the visible ground — no wading here.
            return None

        return None

