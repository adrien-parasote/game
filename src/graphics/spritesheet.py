import pygame
import os
import logging

class SpriteSheet:
    """Utility class to extract images from a spritesheet."""
    
    def __init__(self, filename: str):
        self.filename = filename
        try:
            self.sheet = pygame.image.load(filename).convert_alpha()
            self.valid = True
        except (pygame.error, FileNotFoundError) as e:
            logging.error(f"Unable to load spritesheet image: {filename}. Error: {e}")
            self.sheet = None
            self.valid = False

    def load_grid(self, cols: int, rows: int) -> list[pygame.Surface]:
        """
        Slice the spritesheet into a grid of images.
        Returns a 1D list of surfaces mapped row by row.
        """
        if not self.valid or self.sheet is None:
            # Fallback returning a list of plain colored dummy surfaces
            return [self._create_dummy_surface((32, 32)) for _ in range(cols * rows)]
            
        sheet_w, sheet_h = self.sheet.get_size()
        frame_w = sheet_w // cols
        frame_h = sheet_h // rows
        
        return self._slice_sheet(cols, rows, frame_w, frame_h)

    def load_grid_by_size(self, frame_w: int, frame_h: int) -> list[pygame.Surface]:
        """
        Slice the spritesheet into a grid based on fixed frame dimensions.
        Calculates cols/rows automatically.
        """
        if not self.valid or self.sheet is None:
            # Fallback with dummy surfaces
            return [self._create_dummy_surface((frame_w, frame_h)) for _ in range(16)]
            
        sheet_w, sheet_h = self.sheet.get_size()
        cols = sheet_w // frame_w
        rows = sheet_h // frame_h
        
        return self._slice_sheet(cols, rows, frame_w, frame_h)

    def _slice_sheet(self, cols: int, rows: int, frame_w: int, frame_h: int) -> list[pygame.Surface]:
        """Internal helper to slice the sheet once dimensions are known."""
        frames = []
        for row in range(rows):
            for col in range(cols):
                rect = pygame.Rect(col * frame_w, row * frame_h, frame_w, frame_h)
                image = pygame.Surface(rect.size, pygame.SRCALPHA).convert_alpha()
                image.blit(self.sheet, (0, 0), rect)
                frames.append(image)
        return frames

    def _create_dummy_surface(self, size: tuple) -> pygame.Surface:
        """Internal helper to create a fallback surface."""
        surf = pygame.Surface(size)
        surf.fill((0, 0, 255)) # Blue default
        return surf
