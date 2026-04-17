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
                 tiled_width: int = None, tiled_height: int = None,
                 is_passable: bool = False):
        # Default tiled dimensions to sprite dimensions if not provided
        t_w = tiled_width if tiled_width is not None else width
        t_h = tiled_height if tiled_height is not None else height
        
        super().__init__((pos[0] + t_w // 2, pos[1] + t_h // 2), groups)
        self.sub_type = sub_type
        self.direction_str = direction.lower()
        self.depth = depth
        self.start_row = start_row
        self.end_row = end_row
        self.obstacles_group = obstacles_group
        
        # Sprite dimensions (for slicing)
        self.sprite_width = width
        self.sprite_height = height
        # Logical dimensions (for alignment)
        self.tiled_width = t_w
        self.tiled_height = t_h
        
        # Load spritesheet using sprite pixel width; compute real frame height from sheet
        sheet_path = os.path.join(os.path.dirname(__file__), "..", "..", "assets", "images", "sprites", sprite_sheet)
        sheet = SpriteSheet(sheet_path)
        
        # Compute real frame height: sheet_height / total_expected_rows
        # This avoids off-by-one errors when Tiled spec and real image dimensions diverge
        if sheet.valid and sheet.sheet is not None:
            sheet_w, sheet_h = sheet.sheet.get_size()
            total_rows = self.end_row + 1  # end_row is the last frame index (0-indexed)
            real_frame_h = sheet_h // total_rows if total_rows > 0 else self.sprite_height
        else:
            real_frame_h = self.sprite_height
        
        self.frames = sheet.load_grid_by_size(self.sprite_width, real_frame_h)
        # Real cols from actual sheet layout (may differ from assumed 4-directional grid)
        self._sheet_cols = getattr(sheet, 'last_cols', 4)
        
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
        self.rect = self.image.get_rect()
        self.rect.midbottom = (pos[0] + self.tiled_width // 2, pos[1] + self.tiled_height)
        # Interaction Position: center of the bottom 32x32 footprint
        self.pos = pygame.math.Vector2(self.rect.centerx, self.rect.bottom - 16)
        
        # Initial Collision State
        # - Doors are ALWAYS solid at spawn (they start in the closed state)
        # - Other objects: only solid if not passable
        self.is_passable = is_passable
        if self.obstacles_group is not None:
            if self.sub_type == 'door' or not self.is_passable:
                self.obstacles_group.add(self)
        
        logging.info(f"Spawned InteractiveEntity '{sub_type}' ({width}x{height}) at {pos} facing {direction}")

    def _get_frame(self, row_index: int) -> pygame.Surface:
        """Get the specific frame for the current direction and row."""
        # Use real cols from the loaded sheet, not a hardcoded 4
        cols = self._sheet_cols
        col = min(self.col_index, cols - 1)  # Clamp to available columns
        idx = (row_index * cols) + col
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
                    # Re-enable collision when door is closed (always blocks regardless of passable)
                    if self.sub_type == 'door' and self.obstacles_group:
                        self.obstacles_group.add(self)
            else:
                self.frame_index += self.animation_speed * dt
                if self.frame_index >= self.end_row:
                    self.frame_index = float(self.end_row)
                    self.is_animating = False
                    self.is_open = True
                    # Remove from obstacles when fully open, ONLY if the door is passable
                    if self.sub_type == 'door' and self.is_passable and self.obstacles_group:
                        self.obstacles_group.remove(self)
            
            self.image = self._get_frame(int(self.frame_index))
