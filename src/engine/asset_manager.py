import pygame
import logging
import os

class AssetManager:
    """
    Centralized cache for game assets (images, tilesets, sounds).
    Implements a singleton-like pattern to ensure assets are loaded once.
    """
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AssetManager, cls).__new__(cls)
            cls._instance._init_manager()
        return cls._instance
        
    def _init_manager(self):
        self._images = {}
        self._tilesets = {}
        self._sounds = {}
        
    def get_image(self, path: str, fallback: bool = False) -> pygame.Surface:
        """Load, convert and cache an image."""
        if path in self._images:
            return self._images[path]
            
        if not os.path.exists(path):
            if fallback:
                logging.error(f"Asset not found: {path}. Using placeholder.")
                placeholder = pygame.Surface((32, 32))
                placeholder.fill((255, 0, 255)) # Magenta placeholder
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

    def clear_cache(self):
        """Clear all cached assets."""
        self._images.clear()
        self._tilesets.clear()
        self._sounds.clear()
