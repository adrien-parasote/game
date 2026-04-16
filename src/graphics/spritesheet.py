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
        frames = []
        if not self.valid or self.sheet is None:
            # Fallback returning a list of plain colored dummy surfaces
            for _ in range(cols * rows):
                surf = pygame.Surface((32, 32))
                surf.fill((0, 0, 255)) # Blue default
                frames.append(surf)
            return frames
            
        sheet_w, sheet_h = self.sheet.get_size()
        frame_w = sheet_w // cols
        frame_h = sheet_h // rows
        
        for row in range(rows):
            for col in range(cols):
                rect = pygame.Rect(col * frame_w, row * frame_h, frame_w, frame_h)
                image = pygame.Surface(rect.size, pygame.SRCALPHA).convert_alpha()
                image.blit(self.sheet, (0, 0), rect)
                frames.append(image)
                
        return frames
