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

    def __init__(self, pos: tuple, groups: list[pygame.sprite.Group], 
                 sub_type: str, sprite_sheet: str, direction: str = 'down', 
                 depth: int = 1, start_row: int = 0, end_row: int = 3,
                 width: int = 32, height: int = 32, obstacles_group: pygame.sprite.Group = None,
                 text: str = None):
        super().__init__((pos[0] + width // 2, pos[1] + height // 2), groups)
        self.sub_type = sub_type
        self.direction_str = direction.lower()
        self.depth = depth
        self.start_row = start_row
        self.end_row = end_row
        self.obstacles_group = obstacles_group
        self.text = text
        
        # Load spritesheet using pixel dimensions
        sheet_path = os.path.join(os.path.dirname(__file__), "..", "..", "assets", "images", "sprites", sprite_sheet)
        sheet = SpriteSheet(sheet_path)
        self.frames = sheet.load_grid_by_size(width, height)
        
        # Select column
        self.col_index = self.DIRECTION_MAP.get(self.direction_str, 0)
        
        # Animation State
        self.frame_index = float(self.start_row)
        self.animation_speed = 10.0
        self.is_animating = False
        self.is_open = False
        self.is_closing = False
        
        self.image = self._get_frame(int(self.frame_index))
        # Visual Alignment: Center-X on Tiled rect, Bottom on Tiled rect
        # pos here is (X, Y) of top-left corner
        self.rect = self.image.get_rect()
        self.rect.midbottom = (pos[0] + width // 2, pos[1] + height)
        # Interaction Position: center of the bottom 32x32 footprint
        self.pos = pygame.math.Vector2(self.rect.centerx, self.rect.bottom - 16)
        
        # Initial Collision State
        if self.sub_type == 'door' and self.obstacles_group is not None:
            self.obstacles_group.add(self)
        
        logging.info(f"Spawned InteractiveEntity '{sub_type}' ({width}x{height}) at {pos} facing {direction}")

    def _get_frame(self, row_index: int) -> pygame.Surface:
        """Get the specific frame for the current direction and row."""
        # Calculate total columns automatically from sheet (safe fallback)
        cols = 4 # Default for our directional system
        idx = (row_index * cols) + self.col_index
        if 0 <= idx < len(self.frames):
            return self.frames[idx]
        return self.frames[0] if self.frames else pygame.Surface((32, 32))

    def interact(self, initiator):
        """Toggle animation (Open/Close) on interaction."""
        if not self.is_animating:
            self.is_animating = True
            if self.is_open:
                # Close logic
                self.is_closing = True
                logging.info(f"Closing triggered on {self.sub_type}")
            else:
                # Open logic
                self.is_closing = False
                logging.info(f"Opening triggered on {self.sub_type}")

    def update(self, dt: float):
        """Handle animation progression and dynamic collision."""
        if self.is_animating:
            if self.is_closing:
                self.frame_index -= self.animation_speed * dt
                if self.frame_index <= self.start_row:
                    self.frame_index = float(self.start_row)
                    self.is_animating = False
                    self.is_open = False
                    self.is_closing = False
                    # Re-enable collision when closed
                    if self.sub_type == 'door' and self.obstacles_group:
                        self.obstacles_group.add(self)
            else:
                self.frame_index += self.animation_speed * dt
                if self.frame_index >= self.end_row:
                    self.frame_index = float(self.end_row)
                    self.is_animating = False
                    self.is_open = True
                    # Disable collision when fully open
                    if self.sub_type == 'door' and self.obstacles_group:
                        self.obstacles_group.remove(self)
            
            self.image = self._get_frame(int(self.frame_index))
