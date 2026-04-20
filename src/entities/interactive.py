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
    
    # Position to Direction mapping for interaction validation (Opposite Rule)
    # 0=Up, 1=Right, 2=Left, 3=Down
    POSITION_TO_DIR = {
        0: 'up',
        1: 'right',
        2: 'left',
        3: 'down'
    }

    def __init__(self, pos: tuple, groups: list[pygame.sprite.Group], 
                 sub_type: str, sprite_sheet: str, position: int = 3, 
                 depth: int = 1, start_row: int = 0, end_row: int = 3,
                 width: int = 32, height: int = 32, obstacles_group: pygame.sprite.Group = None,
                 tiled_width: int = None, tiled_height: int = None,
                 is_passable: bool = False, is_animated: bool = False,
                 is_on: bool = None,
                 halo_size: int = 0, halo_color: str = "[255, 255, 255]",
                 halo_alpha: int = 130, particles: bool = False, particle_count: int = 0,
                 target_id: str = None, target: str = None):
        
        # 1. Properties & State Initialization
        self.target_id = target_id
        self.target = target
        
        self._parse_properties(sub_type, start_row, end_row, is_on, is_animated, 
                             depth, position, halo_size, halo_color, halo_alpha,
                             particles, particle_count)
        
        # 2. Asset Loading
        self._load_assets(sprite_sheet, width, height)
        
        # 3. Physics & Layout Setup
        t_w = tiled_width if tiled_width is not None else width
        t_h = tiled_height if tiled_height is not None else height
        self._setup_physics(pos, t_w, t_h, is_passable, obstacles_group, groups)
        
        # 4. Lighting Initialization
        self.light_mask_cache = []
        if self.halo_size > 0:
            self._setup_lighting()
            
        self.image = self._get_frame(int(self.frame_index))
        logging.info(f"Spawned InteractiveEntity '{sub_type}' at {pos} (is_on={self.is_on})")

    def _parse_properties(self, sub_type, start_row, end_row, is_on, is_animated, 
                          depth, position, halo_size, halo_color, halo_alpha,
                          particles, particle_count):
        """Parse raw properties and initialize basic state."""
        self.sub_type = sub_type
        self.start_row = start_row
        self.end_row = end_row
        self.is_animated = is_animated
        self.depth = depth
        self.col_index = position
        self.direction_str = self.POSITION_TO_DIR.get(position, 'down')
        
        # State
        self.frame_index = float(self.start_row)
        # Determine is_on and specific behaviors (Inclusive Detection)
        self.light_sources = ['lamp', 'lantern', 'torch', 'fire', 'candle']
        self.is_light_source = (self.sub_type in self.light_sources) or (halo_size > 0)
        
        if is_on is not None:
            self.is_on = is_on
        else:
            self.is_on = self.is_animated or self.is_light_source
            
        # Selective Animation Speed
        if self.is_light_source:
            # Atmospheric flame rhythm (1.5 FPS)
            self.animation_speed = 1.5
            # Desynchronize starting frames for organic multiple-light vacillation
            if self.is_animated:
                self.frame_index = random.uniform(float(self.start_row), float(self.end_row + 1))
        else:
            # Standard objects (chests, doors) get 10.0 FPS
            self.animation_speed = 10.0
            
        self.is_animating = self.is_on and self.is_animated
        
        # Halo Props
        self.halo_size = halo_size
        self.halo_alpha = halo_alpha
        try:
            self.halo_color = ast.literal_eval(halo_color)
        except (ValueError, SyntaxError, TypeError):
            self.halo_color = (255, 255, 255)
            
        self.flicker_phase = random.uniform(0, 2 * math.pi)
        self.f_alpha = 1.0
        self.f_scale = 1.0
        
        # Particle System
        self.particles = particles
        self.particle_count = particle_count
        self.particles_list = []

    def _load_assets(self, sprite_sheet, width, height):
        """Load spritesheet and compute frame dimensions."""
        self.sprite_width = width
        self.sprite_height = height
        
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

    def _setup_physics(self, pos, t_w, t_h, is_passable, obstacles_group, groups):
        """Initialize sprite rect, world position and collision state."""
        # Visual Position: midbottom alignment
        dummy_rect = pygame.Rect(0, 0, self.sprite_width, self.sprite_height)
        dummy_rect.midbottom = (pos[0] + t_w // 2, pos[1] + t_h // 2 + t_h // 2) # Equivalent to pos[1] + t_h
        
        # Center position for BaseEntity (used for movement syncing)
        center_pos = dummy_rect.center
        super().__init__(center_pos, groups)
        
        self.tiled_width = t_w
        self.tiled_height = t_h
        self.is_passable = is_passable
        self.obstacles_group = obstacles_group
        
        # Re-set rect to correct size and position
        self.rect = dummy_rect
        
        # CRITICAL: Interaction point (self.pos) must be the footprint center (bottom-16)
        # This matches Game's distance check logic for both tall and regular objects
        self.pos = pygame.math.Vector2(self.rect.centerx, self.rect.bottom - 16)
        
        if self.obstacles_group is not None:
            if self.sub_type == 'door' or not self.is_passable:
                self.obstacles_group.add(self)

    def _setup_lighting(self):
        """Pre-generate light mask and its 10-step scaling cache for fluidity."""
        self.light_mask = self._create_halo_surf(self.halo_size)
        
        # 10-step Cache: 0.97 to 1.03 (fine increments for smooth transition)
        self.light_mask_cache = []
        for i in range(10):
            scale = 0.97 + (i * 0.0066)
            scaled_size = int(round(self.halo_size * scale))
            # Cache the base surfaces (intensity-based on black background)
            if scaled_size > 0:
                self.light_mask_cache.append(self._create_halo_surf(scaled_size))
            else:
                self.light_mask_cache.append(self.light_mask)

    def _create_halo_surf(self, radius) -> pygame.Surface:
        """Generate high-precision radial gradient using RGB intensity on black."""
        size = int(radius * 2)
        # Use standard surface (No SRCALPHA) for reliable BLEND_RGB_ADD
        surf = pygame.Surface((size, size))
        surf.fill((0, 0, 0))
        center = (radius, radius)
        
        base_color = pygame.Color(*self.halo_color)
        alpha_factor = self.halo_alpha / 255.0
        
        # Pixel-by-pixel sweep for maximum smoothness
        for r in range(radius, 0, -1):
            ratio = r / radius
            # Quadratic falloff for a much softer "natural light" look
            intensity = (1.0 - ratio) ** 2
            
            # Modulate RGB by both distance intensity and the master halo_alpha
            final_intensity = intensity * alpha_factor
            color = (
                int(base_color.r * final_intensity),
                int(base_color.g * final_intensity),
                int(base_color.b * final_intensity)
            )
            pygame.draw.circle(surf, color, center, r)
            
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
            if not self.is_animated:
                self.is_closing = not self.is_on
            logging.info(f"Object {self.sub_type} toggled to {'ON' if self.is_on else 'OFF'}")

    def update(self, dt: float):
        """Handle animation progression and high-precision flicker calculations."""
        # 1. Flicker Logic
        if self.is_on and self.halo_size > 0:
            if self.is_light_source and self.is_animated:
                # Organic Animation-Driven Flicker
                # Tie the light intensity directly to the visual frame
                num_frames = max(1, self.end_row - self.start_row + 1)
                # Map the frame index inside the loop to a phase [0, 2π]
                frame_progress = (self.frame_index - self.start_row) % num_frames
                animation_phase = (frame_progress / num_frames) * 2 * math.pi
                
                # Base intensity derived from animation frame, plus minor noise
                self.f_alpha = 1.0 + 0.12 * math.sin(animation_phase - math.pi/2) 
                self.f_alpha += random.uniform(-0.02, 0.02)
                
                # Scale pulse delayed slightly from alpha
                self.f_scale = 1.0 + 0.03 * math.sin(animation_phase)
            else:
                # Fallback: Time-based flicker for non-animated or non-light objects with halos
                ticks = pygame.time.get_ticks()
                time_sec = ticks / 1000.0
                
                # High-Frequency jitter removed, keep slow rhythmic phase
                main_wave = math.sin(time_sec * 1.5 * math.pi + self.flicker_phase)
                jitter_wave = 0.3 * math.sin(time_sec * 4.2 * math.pi + self.flicker_phase * 0.5)
                
                self.f_alpha = 1.0 + 0.12 * main_wave + 0.02 * jitter_wave
                self.f_alpha += random.uniform(-0.01, 0.01)
                
                self.f_scale = 1.0 + 0.03 * math.sin(time_sec * 1.2 * math.pi + self.flicker_phase + 0.5)
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

        # 3. Particle System Logic
        if self.particles and self.is_on:
            if len(self.particles_list) < self.particle_count:
                # Target an average spawn rate that maintains particle_count
                expected_spawns = (self.particle_count / 1.5) * dt  # 1.5s average life
                # Spawn guaranteed integer count + chance for fractional remainder
                spawns = int(expected_spawns)
                if random.random() < (expected_spawns - spawns):
                    spawns += 1
                
                # Minimum 30% chance frame threshold for visual randomness when count is small
                if spawns == 0 and random.random() < 0.30:
                    spawns = 1
                    
                for _ in range(spawns):
                    life = random.uniform(1.0, 2.0)
                    self.particles_list.append({
                        'x': self.rect.centerx + random.uniform(-4, 4),
                        'y': self.rect.top + (self.rect.height * 0.33) + random.uniform(-2, 2),
                        'vx': random.uniform(-2.0, 2.0),
                        'vy': random.uniform(-10.0, -5.0),
                        'life': life,
                        'max_life': life,
                        'size': 1 if random.random() < 0.9 else 2,
                        'phase': random.uniform(0, math.pi * 2)
                    })

        # Update existing particles
        if self.particles_list:
            alive_particles = []
            for p in self.particles_list:
                p['life'] -= dt
                if p['life'] > 0:
                    p['x'] += (p['vx'] + math.sin(p['phase'] + p['life'] * 3.0) * 5.0) * dt
                    p['y'] += p['vy'] * dt
                    alive_particles.append(p)
            self.particles_list = alive_particles

    def draw_effects(self, surface: pygame.Surface, cam_offset: pygame.math.Vector2, global_darkness: int):
        """Render high-precision modulated light halo AND particles from 10-step cache."""
        if not self.is_on or not self.light_mask_cache or self.halo_size <= 0:
            return

        # Calculate final modulation factor precisely
        dark_factor = global_darkness / 180.0 
        global_factor = max(0.15, dark_factor)
        
        # Select cached surface (10 steps)
        scale_idx = int(round((self.f_scale - 0.97) / 0.0066))
        scale_idx = max(0, min(9, scale_idx))
        render_surf = self.light_mask_cache[scale_idx].copy() # Copy to modulate
        
        # Modulate the entire surface brightness (Flicker + Time of day)
        # This replaces set_alpha for standard RGB surfaces
        m = int(round(255 * global_factor * self.f_alpha))
        m = max(0, min(255, m))
        if m < 255:
            render_surf.fill((m, m, m), special_flags=pygame.BLEND_RGB_MULT)
        
        # Position mapping: screen center of DO (Visual Middle)
        # Using rect.center instead of self.pos ensures tall objects (doors, decors)
        # have their light emanating from their visual middle.
        screen_center_x = self.rect.centerx + cam_offset.x
        screen_center_y = self.rect.centery + cam_offset.y
        new_size = render_surf.get_width()
        halo_pos = (screen_center_x - new_size // 2, screen_center_y - new_size // 2)
        
        surface.blit(render_surf, halo_pos, special_flags=pygame.BLEND_RGB_ADD)

        # Draw particles if any
        if self.particles_list:
            base_color = getattr(self, 'halo_color', (250, 250, 250))
            for p in self.particles_list:
                # Power-falloff alpha keeps particles bright longer before fading out
                alpha = (p['life'] / p['max_life']) ** 0.6
                # Fading by multiplying RGB by alpha for BLEND_RGB_ADD
                color = (
                    int(base_color[0] * alpha),
                    int(base_color[1] * alpha),
                    int(base_color[2] * alpha)
                )
                px = int(p['x'] + cam_offset.x)
                py = int(p['y'] + cam_offset.y)
                pygame.draw.circle(surface, color, (px, py), p['size'])
