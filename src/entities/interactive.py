import pygame
import os
import logging
import ast
import math
import random
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
                 is_on: bool = None,
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
            # ast.literal_eval is safer than json.loads for literal structures
            self.halo_color = ast.literal_eval(halo_color)
        except (ValueError, SyntaxError, TypeError):
            self.halo_color = (255, 255, 255)
            
        self.flicker_phase = random.uniform(0, 2 * math.pi)
        self.f_alpha = 1.0
        self.f_scale = 1.0
        
        self.light_mask = None
        if self.halo_size > 0:
            self.light_mask = self._create_halo_surf()
        
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
        
        # Determine default state
        light_sources = ['lamp', 'lantern', 'torch', 'fire', 'candle']
        if is_on is not None:
            self.is_on = is_on
        else:
            # Default to ON for animated objects or specific light subtypes
            self.is_on = self.is_animated or self.sub_type in light_sources
            
        self.is_animating = self.is_on and self.is_animated
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
        """Generate a high-quality radial gradient surface using concentric circles."""
        size = self.halo_size * 2
        surf = pygame.Surface((size, size), pygame.SRCALPHA)
        center = (self.halo_size, self.halo_size)
        
        # Draw concentric circles from outside in for smoother blending
        for r in range(self.halo_size, 0, -1):
            # Linearly alpha falloff
            alpha = int(self.halo_alpha * (1.0 - r / self.halo_size))
            color = list(self.halo_color) + [alpha]
            pygame.draw.circle(surf, color, center, r)
            
        # Guarantee the center pixel reaches full alpha
        center_color = list(self.halo_color) + [self.halo_alpha]
        surf.set_at(center, center_color)
        
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
        """Handle animation progression and dynamic flicker calculations."""
        # 1. Flicker Logic (2Hz sinusoidal + noise)
        if self.is_animated and self.halo_size > 0:
            time_val = pygame.time.get_ticks() / 1000.0
            # 2Hz = 4 * pi * time
            self.f_alpha = 1.0 + 0.12 * math.sin(time_val * 4 * math.pi + self.flicker_phase)
            self.f_alpha += random.uniform(-0.02, 0.02) # Subtle noise
            
            # Scale fluctuation (slower/out of sync)
            self.f_scale = 1.0 + 0.03 * math.sin(time_val * 3 * math.pi + self.flicker_phase + 0.5)
        else:
            self.f_alpha = 1.0
            self.f_scale = 1.0

        # 2. Animation Logic
        if self.is_animated:
            if self.is_on:
                self.frame_index += self.animation_speed * dt
                if self.frame_index >= self.end_row + 1:
                    self.frame_index = float(self.start_row)
            else:
                self.frame_index = float(self.start_row)
                self.is_animating = False
        elif self.is_animating:
            # Linear behavior (doors, chests)
            if self.is_closing:
                self.frame_index -= self.animation_speed * dt
                if self.frame_index <= self.start_row:
                    self.frame_index = float(self.start_row)
                    self.is_animating = False
                    if self.sub_type == 'door' and self.obstacles_group:
                        self.obstacles_group.add(self)
            else:
                self.frame_index += self.animation_speed * dt
                if self.frame_index >= self.end_row:
                    self.frame_index = float(self.end_row)
                    self.is_animating = False
                    if self.sub_type == 'door' and self.is_passable and self.obstacles_group:
                        self.obstacles_group.remove(self)
        
        self.image = self._get_frame(int(self.frame_index))

    def draw_halo(self, surface: pygame.Surface, cam_offset: pygame.math.Vector2, global_darkness: int):
        """Render the modulated light halo with additive blending."""
        if not self.is_on or not self.light_mask or self.halo_size <= 0:
            return

        # Intensity modulation: scales with darkness, min 15% floor
        # Normalize by MAX_NIGHT_ALPHA (180) to reach full halo_alpha at midnight
        dark_factor = global_darkness / 180.0 
        global_factor = max(0.15, dark_factor)
        
        final_alpha = int(255 * global_factor * self.f_alpha)
        final_alpha = max(0, min(255, final_alpha))
        
        # Apply scaling if needed
        if self.f_scale != 1.0:
            new_size = int(self.halo_size * 2 * self.f_scale)
            render_surf = pygame.transform.scale(self.light_mask, (new_size, new_size))
        else:
            render_surf = self.light_mask
            new_size = self.halo_size * 2

        # Modulation
        render_surf.set_alpha(final_alpha)
        
        # Centering on FOOTPRINT (16px above rect.bottom)
        # footprint_center = (self.rect.centerx, self.rect.bottom - 16)
        # cam_offset is added in Game, so we just calculate screen position
        screen_center_x = self.rect.centerx + cam_offset.x
        screen_center_y = (self.rect.bottom - 16) + cam_offset.y
        
        halo_pos = (screen_center_x - new_size // 2, screen_center_y - new_size // 2)
        surface.blit(render_surf, halo_pos, special_flags=pygame.BLEND_RGB_ADD)
