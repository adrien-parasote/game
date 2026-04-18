import pygame
import os
import logging
import json
from .base import BaseEntity
from src.config import Settings
from src.graphics.spritesheet import SpriteSheet

class InteractiveEntity(BaseEntity):
    """
    Fixed interactive object (chest, switch, lamp, etc.) with animation 
    and optional lighting halo.
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
                 is_passable: bool = False, is_animated: bool = False,
                 halo_size: int = 0, halo_color: str = "[255, 255, 255]",
                 halo_alpha: int = 130):
        # Default tiled dimensions to sprite dimensions if not provided
        t_w = tiled_width if tiled_width is not None else width
        t_h = tiled_height if tiled_height is not None else height
        
        super().__init__((pos[0] + t_w // 2, pos[1] + t_h // 2), groups)
        self.sub_type = sub_type
        self.direction_str = direction.lower()
        self.depth = depth
        self.start_row = start_row
        self.end_row = end_row
        self.is_animated = is_animated
        self.obstacles_group = obstacles_group
        
        # Sprite dimensions (for slicing)
        self.sprite_width = width
        self.sprite_height = height
        # Logical dimensions (for alignment)
        self.tiled_width = t_w
        self.tiled_height = t_h
        
        # Halo / Light Logic
        self.halo_size = halo_size
        self.halo_alpha = halo_alpha
        try:
            self.halo_color = json.loads(halo_color)
        except (json.JSONDecodeError, TypeError):
            self.halo_color = [255, 255, 255]
        
        self.halo_surf = None
        if self.halo_size > 0:
            self.halo_surf = self._create_halo_surf()
        
        # Load spritesheet using sprite pixel width; compute real frame height from sheet
        sheet_path = os.path.join(os.path.dirname(__file__), "..", "..", "assets", "images", "sprites", sprite_sheet)
        sheet = SpriteSheet(sheet_path)
        
        if sheet.valid and sheet.sheet is not None:
            _, sheet_h = sheet.sheet.get_size()
            total_rows = self.end_row + 1 
            real_frame_h = sheet_h // total_rows if total_rows > 0 else self.sprite_height
        else:
            real_frame_h = self.sprite_height
        
        self.frames = sheet.load_grid_by_size(self.sprite_width, real_frame_h)
        self._sheet_cols = getattr(sheet, 'last_cols', 4)
        
        # Select column
        self.col_index = self.DIRECTION_MAP.get(self.direction_str, 0)
        
        # State
        self.frame_index = float(self.start_row)
        self.animation_speed = 10.0
        self.is_on = False  # Matches User request: ON/OFF
        self.is_animating = False
        self.is_closing = False
        
        self.image = self._get_frame(int(self.frame_index))
        # Visual Alignment: Center-X on Tiled rect, Bottom on Tiled rect
        self.rect = self.image.get_rect()
        self.rect.midbottom = (pos[0] + self.tiled_width // 2, pos[1] + self.tiled_height)
        # Interaction Position: center of the bottom 32x32 footprint
        self.pos = pygame.math.Vector2(self.rect.centerx, self.rect.bottom - 16)
        
        # Initial Collision State
        self.is_passable = is_passable
        if self.obstacles_group is not None:
            # Floor decor (decor sub_type or others with is_passable=True and not door-like) 
            # should be traversable permanently.
            # Doors start solid regardless of is_passable.
            if self.sub_type == 'door':
                self.obstacles_group.add(self)
            elif not self.is_passable:
                self.obstacles_group.add(self)
        
        logging.info(f"Spawned InteractiveEntity '{sub_type}' at {pos} (is_animated={is_animated}, halo={halo_size})")

    def _create_halo_surf(self) -> pygame.Surface:
        """Generate a radial gradient surface for the light halo."""
        size = self.halo_size * 2
        surf = pygame.Surface((size, size), pygame.SRCALPHA)
        center = pygame.math.Vector2(self.halo_size, self.halo_size)
        
        for x in range(size):
            for y in range(size):
                dist = center.distance_to((x, y))
                if dist <= self.halo_size:
                    # Radial transition: center (alpha_max) to edge (0)
                    alpha = int(self.halo_alpha * (1 - dist / self.halo_size))
                    color = list(self.halo_color) + [alpha]
                    surf.set_at((x, y), color)
        return surf

    def _get_frame(self, row_index: int) -> pygame.Surface:
        """Get frame for current column and specific row."""
        cols = self._sheet_cols
        col = min(self.col_index, cols - 1)
        idx = (row_index * cols) + col
        if 0 <= idx < len(self.frames):
            return self.frames[idx]
        return self.frames[0] if self.frames else pygame.Surface((32, 32))

    def interact(self, initiator):
        """Toggle ON/OFF state and start animation."""
        if not self.is_animating or self.is_animated:
            self.is_on = not self.is_on
            self.is_animating = True
            
            # Doors/Linear logic uses is_closing to track direction
            if not self.is_animated:
                self.is_closing = not self.is_on
            
            logging.info(f"Object {self.sub_type} toggled to {'ON' if self.is_on else 'OFF'}")

    def update(self, dt: float):
        """Handle animation progression and dynamic collision."""
        if self.is_animating:
            if self.is_animated:
                # Looping behavior: only animates when ON
                if self.is_on:
                    self.frame_index += self.animation_speed * dt
                    if self.frame_index >= self.end_row + 1:
                        self.frame_index = float(self.start_row)
                else:
                    self.frame_index = float(self.start_row)
                    self.is_animating = False
            else:
                # Linear behavior (doors, chests)
                if self.is_closing:
                    self.frame_index -= self.animation_speed * dt
                    if self.frame_index <= self.start_row:
                        self.frame_index = float(self.start_row)
                        self.is_animating = False
                        # Re-add to obstacles if door closed
                        if self.sub_type == 'door' and self.obstacles_group:
                            self.obstacles_group.add(self)
                else:
                    self.frame_index += self.animation_speed * dt
                    if self.frame_index >= self.end_row:
                        self.frame_index = float(self.end_row)
                        self.is_animating = False
                        # Remove from obstacles if door open and passable
                        if self.sub_type == 'door' and self.is_passable and self.obstacles_group:
                            self.obstacles_group.remove(self)
            
            self.image = self._get_frame(int(self.frame_index))
