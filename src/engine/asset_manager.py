import logging
import os

import pygame


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
        self._images = {}
        self._tilesets = {}
        self._sounds = {}
        self._fonts = {}

    def get_image(self, path: str, fallback: bool = False) -> pygame.Surface:
        """Load, convert and cache an image."""
        if path in self._images:
            return self._images[path]

        if not os.path.exists(path):
            if fallback:
                logging.error(f"Asset not found: {path}. Using placeholder.")
                placeholder = pygame.Surface((32, 32))
                placeholder.fill((255, 0, 255))  # Magenta placeholder
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
                placeholder.fill((255, 0, 255))
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
            return pygame.font.Font(None, size)

    def clear_cache(self):
        """Clear all cached assets."""
        self._images.clear()
        self._tilesets.clear()
        self._sounds.clear()
        self._fonts.clear()
