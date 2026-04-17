import pygame
import os
import logging
from .base import BaseEntity
from src.config import Settings
from src.graphics.spritesheet import SpriteSheet

class InteractiveEntity(BaseEntity):
    """
    Fixed interactive object (chest, sign, etc.) with directional sprites 
    and interaction-triggered animation.
    """
    
    # Column mapping according to user instruction
    DIRECTION_MAP = {
        'up': 0,
        'right': 1,
        'left': 2,
        'down': 3
    }

    def __init__(self, pos: tuple, groups: pygame.sprite.Group, 
                 sub_type: str, sprite_sheet: str, direction: str = 'down', 
                 depth: int = 1, start_row: int = 0, end_row: int = 3):
        super().__init__(pos, groups)
        self.sub_type = sub_type
        self.direction_str = direction.lower()
        self.depth = depth
        self.start_row = start_row
        self.end_row = end_row
        
        # Load spritesheet
        # Assumes objects are in assets/images/sprites/
        sheet_path = os.path.join(os.path.dirname(__file__), "..", "..", "assets", "images", "sprites", sprite_sheet)
        sheet = SpriteSheet(sheet_path)
        
        # We expect a sheet with 4 columns (directions) and N rows (animation frames)
        # Using 4 cols as per spec. We infer rows from sheet height / frame_h
        # frame_w and frame_h are TILE_SIZE (32)
        self.frames = sheet.load_grid(4, 4) # Defaulting to 4x4 if not specified, but load_grid slices everything
        
        # Select column
        self.col_index = self.DIRECTION_MAP.get(self.direction_str, 0)
        
        # Animation State
        self.frame_index = float(self.start_row)
        self.animation_speed = 10.0 # Faster for objects
        self.is_animating = False
        self.is_open = False # Static state after animation
        
        self.image = self._get_frame(int(self.frame_index))
        self.rect = pygame.Rect(0, 0, Settings.TILE_SIZE, Settings.TILE_SIZE)
        self.rect.center = pos
        
        logging.info(f"Spawned InteractiveEntity '{sub_type}' at {pos} facing {direction}")

    def _get_frame(self, row_index: int) -> pygame.Surface:
        """Get the specific frame for the current direction and row."""
        # frames is a 1D list [row0_col0, row0_col1, ..., row1_col0, ...]
        idx = (row_index * 4) + self.col_index
        if 0 <= idx < len(self.frames):
            return self.frames[idx]
        return self.frames[self.col_index] # Fallback to first frame of column

    def interact(self, initiator):
        """Trigger the animation when correctly interacted with."""
        if not self.is_animating and not self.is_open:
            self.is_animating = True
            logging.info(f"Interaction triggered on {self.sub_type}")

    def update(self, dt: float):
        """Handle animation progression."""
        if self.is_animating:
            self.frame_index += self.animation_speed * dt
            if self.frame_index >= self.end_row:
                self.frame_index = float(self.end_row)
                self.is_animating = False
                self.is_open = True # Stay at last frame (e.g., opened chest)
            
            self.image = self._get_frame(int(self.frame_index))
