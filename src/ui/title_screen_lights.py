# src/ui/title_screen_lights.py
"""Light halo mixin for TitleScreen — handles pre-scaled bucket init and rendering."""

import math

import pygame

from src.ui.title_screen_constants import (
    BACKGROUND_LIGHTS,
    BG_LIGHT_COLOR,
    HALO_DEBUG,
    MUSHROOM_LIGHTS,
)


class TitleLightsMixin:
    """Mixin handling pre-scaled light halo bucket setup and frame-time rendering."""

    def _init_light_halos(self) -> None:
        """P1+P2: Pre-scale halo surfaces into N_BUCKETS buckets covering flicker range.

        Avoids rotozoom() per frame — pure lookup at draw time.
        """
        _N_BUCKETS = 10
        _SCALE_MIN = 0.80  # matches max(0.80, ...) in candle flicker
        _SCALE_MAX = 1.05  # slight headroom above 1.0
        self._halo_n_buckets = _N_BUCKETS
        self._halo_scale_min = _SCALE_MIN
        self._halo_scale_max = _SCALE_MAX

        # P1: Bucket lookup for fire/candle halos
        self._light_halos_scaled: dict[int, list[pygame.Surface]] = {}
        for r in {entry[2] for entry in BACKGROUND_LIGHTS}:
            base = self._create_radial_gradient(r, BG_LIGHT_COLOR)
            avg_scale = (self._light_scale_x + self._light_scale_y) / 2
            self._light_halos_scaled[r] = self._build_buckets(
                base, r, avg_scale, _N_BUCKETS, _SCALE_MIN, _SCALE_MAX
            )

        # P2: Bucket lookup for mushroom bioluminescent halos
        self._mushroom_halos_scaled: dict[tuple, dict[int, list[pygame.Surface]]] = {}
        for _lx, _ly, r, color in MUSHROOM_LIGHTS:
            ck = tuple(color)
            if ck not in self._mushroom_halos_scaled:
                self._mushroom_halos_scaled[ck] = {}
            if r not in self._mushroom_halos_scaled[ck]:
                base = self._create_radial_gradient(r, ck)
                avg_scale = (self._light_scale_x + self._light_scale_y) / 2
                self._mushroom_halos_scaled[ck][r] = self._build_buckets(
                    base, r, avg_scale, _N_BUCKETS, _SCALE_MIN, _SCALE_MAX
                )

    @staticmethod
    def _create_radial_gradient(radius: int, color: tuple) -> pygame.Surface:
        """Generate a radial gradient surface for a given radius and color."""
        base = pygame.Surface((radius * 2, radius * 2))
        base.fill((0, 0, 0))
        for ri in range(radius, 0, -1):
            intensity = (1.0 - (ri / radius)) ** 2
            c = (int(color[0] * intensity), int(color[1] * intensity), int(color[2] * intensity))
            pygame.draw.circle(base, c, (radius, radius), ri)
        return base

    @staticmethod
    def _build_buckets(
        base: pygame.Surface,
        radius: int,
        avg_scale: float,
        n_buckets: int,
        scale_min: float,
        scale_max: float,
    ) -> list[pygame.Surface]:
        """Build pre-scaled bucket copies for the display scale range."""
        buckets: list[pygame.Surface] = []
        for b in range(n_buckets):
            t = b / max(n_buckets - 1, 1)
            s = (scale_min + t * (scale_max - scale_min)) * avg_scale
            new_r = max(1, int(radius * s))
            buckets.append(pygame.transform.smoothscale(base, (new_r * 2, new_r * 2)))
        return buckets

    def _draw_background_lights(self) -> None:
        """P1: Draw fire/candle lights via pre-scaled bucket lookup (no rotozoom)."""
        for i, (lx, ly, hr) in enumerate(BACKGROUND_LIGHTS):
            sx = int(lx * self._light_scale_x)
            sy = int(ly * self._light_scale_y)
            flicker = (
                math.sin(self._light_time * 0.4 + i * 1.1) * 0.06
                + math.sin(self._light_time * 0.9 + i * 2.3) * 0.04
            ) + 0.92
            flicker = max(0.80, min(1.0, flicker))

            buckets = self._light_halos_scaled.get(hr)
            if buckets:
                t = (flicker - self._halo_scale_min) / (self._halo_scale_max - self._halo_scale_min)
                idx = max(0, min(self._halo_n_buckets - 1, int(t * (self._halo_n_buckets - 1))))
                rendered = buckets[idx]
                offset = rendered.get_width() // 2
                self._screen.blit(
                    rendered, (sx - offset, sy - offset), special_flags=pygame.BLEND_RGB_ADD
                )

            if HALO_DEBUG:
                pygame.draw.line(self._screen, (255, 0, 0), (sx - 10, sy), (sx + 10, sy), 1)
                pygame.draw.line(self._screen, (255, 0, 0), (sx, sy - 10), (sx, sy + 10), 1)
                pygame.draw.circle(self._screen, (255, 0, 0), (sx, sy), 4)

    def _draw_mushroom_lights(self) -> None:
        """P2: Draw mushroom glows via pre-scaled bucket lookup (no rotozoom)."""
        for i, (lx, ly, hr, color) in enumerate(MUSHROOM_LIGHTS):
            sx = int(lx * self._light_scale_x)
            sy = int(ly * self._light_scale_y)
            flicker = (
                math.sin(self._light_time * 0.15 + i * 1.3) * 0.10
                + math.sin(self._light_time * 0.37 + i * 2.1) * 0.06
            ) + 0.84
            flicker = max(0.72, min(1.0, flicker))
            ck = tuple(color)
            halos_for_color = self._mushroom_halos_scaled.get(ck, {})
            buckets_m = halos_for_color.get(hr)
            if buckets_m:
                t = (flicker - self._halo_scale_min) / (self._halo_scale_max - self._halo_scale_min)
                idx = max(0, min(self._halo_n_buckets - 1, int(t * (self._halo_n_buckets - 1))))
                rendered = buckets_m[idx]
                offset = rendered.get_width() // 2
                self._screen.blit(
                    rendered, (sx - offset, sy - offset), special_flags=pygame.BLEND_RGB_ADD
                )

            if HALO_DEBUG:
                pygame.draw.line(self._screen, (0, 255, 200), (sx - 8, sy), (sx + 8, sy), 1)
                pygame.draw.line(self._screen, (0, 255, 200), (sx, sy - 8), (sx, sy + 8), 1)
                pygame.draw.circle(self._screen, (0, 255, 200), (sx, sy), 3)
