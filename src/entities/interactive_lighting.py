# src/entities/interactive_lighting.py
"""Lighting mixin for InteractiveEntity — handles halo setup, caching, and flicker."""

import math
import random
from typing import TYPE_CHECKING

import pygame

from src.entities.interactive_constants import (
    FLICKER_ALPHA_AMPLITUDE,
    FLICKER_ALPHA_JITTER_AMP,
    FLICKER_ALPHA_JITTER_SCALE,
    FLICKER_ALPHA_NOISE_AMP,
    FLICKER_JITTER_FREQ,
    FLICKER_MAIN_FREQ,
    FLICKER_SCALE_AMPLITUDE,
    FLICKER_SCALE_FREQ,
    FLICKER_SCALE_PHASE_OFFSET,
    LIGHT_MASK_CACHE_COUNT,
    LIGHT_MASK_SCALE_BASE,
    LIGHT_MASK_SCALE_STEP,
)
from src.ui.ui_colors import COLOR_BLACK

if TYPE_CHECKING:
    pass


class InteractiveLightingMixin:
    """Mixin handling light halo setup, caching, flicker computation, and halo rendering."""

    def _setup_lighting(self) -> None:
        """Pre-generate light mask cache."""
        self.light_mask = self._create_halo_surf(self.halo_size)
        self.light_mask_cache = []
        for i in range(LIGHT_MASK_CACHE_COUNT):
            scale = LIGHT_MASK_SCALE_BASE + (i * LIGHT_MASK_SCALE_STEP)
            scaled_size = int(round(self.halo_size * scale))
            if scaled_size > 0:
                self.light_mask_cache.append(self._create_halo_surf(scaled_size))
            else:
                self.light_mask_cache.append(self.light_mask)

    def _create_halo_surf(self, radius: int) -> pygame.Surface:
        """Generate radial gradient surface."""
        size = int(radius * 2)
        surf = pygame.Surface((size, size))
        surf.fill(COLOR_BLACK)
        center = (radius, radius)

        base_color = pygame.Color(*self.halo_color)
        alpha_factor = self.halo_alpha / 255.0

        for r in range(radius, 0, -1):
            ratio = r / radius
            intensity = (1.0 - ratio) ** 2
            final_intensity = intensity * alpha_factor
            color = (
                int(base_color.r * final_intensity),
                int(base_color.g * final_intensity),
                int(base_color.b * final_intensity),
            )
            pygame.draw.circle(surf, color, center, r)

        return surf

    def _update_flicker(self, dt: float, ticks_ms: int | None = None) -> None:
        """Update flicker alpha and scale values for the halo."""
        if self.is_on and self.halo_size > 0:
            if self.is_light_source and self.is_animated:
                num_frames = max(1, self.end_row - self.start_row + 1)
                frame_progress = (self.frame_index - self.start_row) % num_frames
                animation_phase = (frame_progress / num_frames) * 2 * math.pi
                self.f_alpha = 1.0 + FLICKER_ALPHA_AMPLITUDE * math.sin(
                    animation_phase - math.pi / 2
                )
                self.f_alpha += random.uniform(-FLICKER_ALPHA_JITTER_AMP, FLICKER_ALPHA_JITTER_AMP)
                self.f_scale = 1.0 + FLICKER_SCALE_AMPLITUDE * math.sin(animation_phase)
            else:
                ticks = ticks_ms if ticks_ms is not None else pygame.time.get_ticks()
                time_sec = ticks / 1000.0
                main_wave = math.sin(time_sec * FLICKER_MAIN_FREQ * math.pi + self.flicker_phase)
                jitter_wave = FLICKER_ALPHA_JITTER_SCALE * math.sin(
                    time_sec * FLICKER_JITTER_FREQ * math.pi + self.flicker_phase * 0.5
                )
                self.f_alpha = (
                    1.0
                    + FLICKER_ALPHA_AMPLITUDE * main_wave
                    + FLICKER_ALPHA_JITTER_AMP * jitter_wave
                )
                self.f_alpha += random.uniform(-FLICKER_ALPHA_NOISE_AMP, FLICKER_ALPHA_NOISE_AMP)
                self.f_scale = 1.0 + FLICKER_SCALE_AMPLITUDE * math.sin(
                    time_sec * FLICKER_SCALE_FREQ * math.pi
                    + self.flicker_phase
                    + FLICKER_SCALE_PHASE_OFFSET
                )
        else:
            self.f_alpha = 1.0
            self.f_scale = 1.0

    def _draw_halo(
        self,
        surface: pygame.Surface,
        cam_offset: pygame.math.Vector2,
        global_darkness: int,
    ) -> None:
        """Draw the light halo effect."""
        if not self.light_mask_cache or self.halo_size <= 0:
            return

        dark_factor = global_darkness / 180.0
        global_factor = max(0.15, dark_factor)
        scale_idx = max(0, min(9, int(round((self.f_scale - 0.97) / 0.0066))))
        # P9: set_alpha() instead of .copy() — avoids Surface allocation per frame
        render_surf = self.light_mask_cache[scale_idx]
        m = max(0, min(255, int(round(255 * global_factor * self.f_alpha))))
        render_surf.set_alpha(m)
        if self.rect:
            halo_pos = (
                self.rect.centerx + cam_offset.x - render_surf.get_width() // 2,
                self.rect.centery + cam_offset.y - render_surf.get_height() // 2,
            )
            surface.blit(render_surf, halo_pos, special_flags=pygame.BLEND_RGB_ADD)
