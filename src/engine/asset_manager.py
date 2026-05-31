import logging
import os

import pygame

from src.engine.engine_constants import COLOR_PLACEHOLDER_MAGENTA


class AssetManager:
    """
    Centralized cache for game assets (images, tilesets, sounds).
    Implements a singleton-like pattern to ensure assets are loaded once.
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init_manager()
        return cls._instance

    def _init_manager(self):
        self._images: dict = {}
        self._tilesets: dict = {}
        self._sounds: dict = {}
        self._fonts: dict = {}
        # Maps id(tile_surface) → BLEND_RGBA_MULT modulation mask (or None for fully opaque tiles)
        self._occlusion_masks: dict[int, pygame.Surface | None] = {}

    def get_image(self, path: str, fallback: bool = False) -> pygame.Surface:
        """Load, convert and cache an image."""
        if path in self._images:
            return self._images[path]

        if not os.path.exists(path):
            if fallback:
                logging.error(f"Asset not found: {path}. Using placeholder.")
                placeholder = pygame.Surface((32, 32))
                placeholder.fill(COLOR_PLACEHOLDER_MAGENTA)  # Magenta placeholder
                self._images[path] = placeholder
                return placeholder
            raise FileNotFoundError(f"Asset not found: {path}")

        try:
            # Detect transparency requirement based on extension or path
            # For simplicity, we use convert_alpha() for all unless optimized later
            image = pygame.image.load(path).convert_alpha()
            self._images[path] = image
            return image
        except pygame.error as e:
            logging.error(f"Failed to load image {path}: {e}")
            if fallback:
                placeholder = pygame.Surface((32, 32))
                placeholder.fill(COLOR_PLACEHOLDER_MAGENTA)
                return placeholder
            raise

    def get_font(self, path: str, size: int) -> pygame.font.Font:
        """Load and cache a font."""
        key = (path, size)
        if key in self._fonts:
            return self._fonts[key]

        try:
            # If path is None or empty, use default system font
            if path and os.path.exists(path):
                font = pygame.font.Font(path, size)
            else:
                # Fallback to system font if the file doesn't exist
                font = pygame.font.SysFont("Arial", size)
            self._fonts[key] = font
            return font
        except Exception as e:
            logging.error(f"Failed to load font {path}: {e}")
            try:
                return pygame.font.SysFont("Arial", size)
            except Exception:
                return pygame.font.Font(None, size)

    def get_occlusion_mask(self, tile_surf: pygame.Surface) -> pygame.Surface | None:
        """Return the BLEND_RGBA_MULT modulation mask for a tile surface.

        The mask is a SRCALPHA Surface where:
        - RGB = (255, 255, 255) everywhere (neutral for BLEND_RGBA_MULT on colour channels)
        - A = OCCLUSION_ALPHA for opaque tile pixels
        - A = 255 for transparent tile pixels (no change to sprite)

        Returns None if the tile is fully opaque (use classic set_alpha() code path).
        Cache key: id(tile_surf) — stable because AssetManager caches image objects.
        """
        key = id(tile_surf)
        if key not in self._occlusion_masks:
            self._occlusion_masks[key] = self._build_occlusion_mask(tile_surf)
        return self._occlusion_masks[key]

    def _build_occlusion_mask(self, tile_surf: pygame.Surface) -> pygame.Surface | None:
        """Compute the BLEND_RGBA_MULT modulation mask for a tile surface.

        Pure pygame — uses get_at/set_at (load time only, never called at runtime).
        Returns None if no transparent pixel is found (fully opaque tile).
        """
        from src.config import Settings  # local import to avoid circular deps

        w, h = tile_surf.get_size()
        has_transparency = False
        mask = pygame.Surface((w, h), pygame.SRCALPHA)
        for x in range(w):
            for y in range(h):
                tile_a = tile_surf.get_at((x, y)).a
                if tile_a < 255:
                    has_transparency = True
                # Modulation: opaque tile pixel → darken sprite; transparent → preserve sprite
                mod_a = Settings.OCCLUSION_ALPHA if tile_a > 0 else 255
                mask.set_at((x, y), (255, 255, 255, mod_a))
        return mask if has_transparency else None

    def clear_cache(self):
        """Clear all cached assets."""
        self._images.clear()
        self._tilesets.clear()
        self._sounds.clear()
        self._fonts.clear()
        self._occlusion_masks.clear()
