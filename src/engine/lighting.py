import math
from typing import Any

import pygame

from src.engine.lighting_constants import (
    BEAM_BOTTOM_WIDTH,
    BEAM_HEIGHT,
    BEAM_MAX_SLANT,
    BEAM_TOP_WIDTH,
    OVERLAY_ALPHA_RANGE,
    OVERLAY_BASE_ALPHA,
    SLANT_ROUND_STEP,
    TORCH_ALPHA_QUANTIZE,
)
from src.engine.time_system import TimeSystem


class LightingManager:
    """
    Manages the dynamic lighting system: night overlay + window beam coloring.

    Rendering pipeline:
    1. draw_additive_window_beams()  — colored trapezoid on the scene (before overlay)
    2. create_overlay()              — dark overlay with holes punched for lights
    """

    def __init__(self, time_system: TimeSystem, screen_size: tuple[int, int]):
        self.time_system = time_system
        self.screen_size = screen_size
        self._overlay_cache = pygame.Surface(screen_size, pygame.SRCALPHA)
        self._torch_mask_cache: dict = {}
        self._beam_surf_cache: dict = {}

        # Beam shape defaults (pixels). Per-window widths may override BEAM_TOP_WIDTH via Tiled.
        self.beam_top_width = BEAM_TOP_WIDTH
        self.beam_bottom_width = BEAM_BOTTOM_WIDTH
        self.beam_height = BEAM_HEIGHT
        # Max horizontal drift of the beam over its full height.
        # Sun swings between -BEAM_MAX_SLANT (evening) and +BEAM_MAX_SLANT (morning).
        self.max_slant = BEAM_MAX_SLANT

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def resize(self, new_size: tuple[int, int]) -> None:
        if self.screen_size != new_size:
            self.screen_size = new_size
            self._overlay_cache = pygame.Surface(new_size, pygame.SRCALPHA)

    def draw_additive_window_beams(
        self,
        screen: pygame.Surface,
        window_positions: list[tuple],
        cam_offset: Any,
    ) -> None:
        """Blit colored window-light trapezoids onto the scene."""
        if not window_positions:
            return
        for spec in window_positions:
            if len(spec) == 3:
                cx, wy, top_w_raw = spec
                top_w = int(top_w_raw)
            else:
                cx, wy = spec
                top_w = self.beam_top_width

            beam = self._get_beam_surface_for_time(top_w)
            bw = beam.get_width()
            screen.blit(beam, (int(cx + cam_offset.x) - bw // 2, int(wy + cam_offset.y)))

    def create_overlay(
        self,
        window_positions: list[tuple],
        active_torches: list[Any],
        cam_offset: Any,
    ) -> pygame.Surface:
        """Return the full-screen darkness overlay with light holes punched in it."""
        night_alpha = self.time_system.night_alpha
        self._overlay_cache.fill((0, 0, 0, night_alpha))

        if night_alpha <= 0:
            return self._overlay_cache

        # Torches
        for torch in active_torches:
            if not getattr(torch, "is_on", False) or getattr(torch, "halo_size", 0) <= 0:
                continue
            radius = int(torch.halo_size * torch.f_scale)
            cx = int(torch.rect.centerx + cam_offset.x)
            cy = int(torch.rect.centery + cam_offset.y)
            mask = self._get_torch_mask(radius, torch.f_alpha)
            self._overlay_cache.blit(
                mask, mask.get_rect(center=(cx, cy)), special_flags=pygame.BLEND_RGBA_SUB
            )

        # Windows — punch a beam-shaped hole in the darkness
        for spec in window_positions:
            if len(spec) == 3:
                cx, wy, top_w_raw = spec
                top_w = int(top_w_raw)
            else:
                cx, wy = spec
                top_w = self.beam_top_width

            beam = self._get_beam_surface_for_time(top_w)
            bw = beam.get_width()
            self._overlay_cache.blit(
                beam,
                (int(cx + cam_offset.x) - bw // 2, int(wy + cam_offset.y)),
                special_flags=pygame.BLEND_RGBA_SUB,
            )

        return self._overlay_cache

    # ------------------------------------------------------------------
    # Beam helpers
    # ------------------------------------------------------------------

    def _get_beam_surface_for_time(self, top_w: int | None = None) -> pygame.Surface:
        """Return a cached beam surface tuned to the current time of day."""
        if top_w is None:
            top_w = self.beam_top_width
        b = self.time_system.brightness
        color = self._lerp_color(
            (160, 180, 255),  # cool moonlight
            (255, 248, 220),  # warm sunlight (soft, not too yellow)
            b,
        )
        # Max opacity: ~75% at noon, ~25% at midnight
        master_alpha = int(255 * (OVERLAY_BASE_ALPHA + OVERLAY_ALPHA_RANGE * b))

        slant = self._compute_slant()

        # Quantise so we don't rebuild every single frame
        # Round color channels to nearest multiple of 8
        color = (
            (color[0] // 8) * 8,
            (color[1] // 8) * 8,
            (color[2] // 8) * 8,
        )

        # Round slant to nearest SLANT_ROUND_STEP px to reduce cache churn
        key = (color, master_alpha >> 3, top_w, round(slant / SLANT_ROUND_STEP) * SLANT_ROUND_STEP)
        if key not in self._beam_surf_cache:
            # Scale bottom proportionally to the requested top_w
            ratio = top_w / max(1, self.beam_top_width)
            bot_w = int(self.beam_bottom_width * ratio)
            surf = self._create_beam_surface(color, master_alpha, top_w, bot_w, slant)
            self._beam_surf_cache[key] = surf
            if len(self._beam_surf_cache) > 64:
                del self._beam_surf_cache[next(iter(self._beam_surf_cache))]
        return self._beam_surf_cache[key]

    def _compute_slant(self) -> float:
        """
        Return the horizontal beam slant (pixels) — fully continuous, no jumps.

        Both sun and moon are modelled as cosine waves over 24h, blended
        by the current brightness so the transition at dawn/dusk is smooth.

        Sun  : +max at  6h (east), 0 at 12h (zenith), -max at 18h (west)
        Moon : +max/2 at 18h (east), 0 at 0h (zenith), -max/2 at 6h (west)
        Blend: slant = sun_slant * brightness + moon_slant * (1 - brightness)
        """
        wt = self.time_system.world_time
        frac_hour = wt.hour + wt.minute / 60.0  # 0.0 – 23.999
        b = self.time_system.brightness  # 0=midnight, 1=noon

        # Sun: cosine anchored at 6h
        sun_angle = 2 * math.pi * (frac_hour - 6.0) / 24.0
        sun_slant = self.max_slant * math.cos(sun_angle)

        # Moon: opposite phase (12h offset), half amplitude
        moon_angle = 2 * math.pi * (frac_hour - 18.0) / 24.0
        moon_slant = (self.max_slant * 0.5) * math.cos(moon_angle)

        # Smooth blend: full day → pure sun, full night → pure moon
        return sun_slant * b + moon_slant * (1.0 - b)

    def _create_beam_surface(
        self,
        base_color: tuple[int, int, int],
        master_alpha: int,
        top_w: int | None = None,
        bot_w: int | None = None,
        slant: float = 0,
    ) -> pygame.Surface:
        """
        Build a soft, diffuse beam with a natural oval bottom edge.

        Per-pixel alpha = master_alpha * h_fade(x) * v_fade(x, y)

          h_fade : gaussian falloff from beam center → soft lateral edges
          v_fade : standard vertical decay (trapezoid shape preserved)
          corner_fade : in the bottom 35% only, fades the corners progressively
                        without touching the center column — gives an oval bottom
                        without a spike.
          slant  : the beam center drifts horizontally (self.beam_slant px over h)
                   creating a diagonal ray effect.

        No numpy required — uses pygame.Surface.set_at() directly.
        The surface is cached so the per-pixel cost is paid only once per
        unique (color, alpha, width) combination.
        """
        if top_w is None:
            top_w = self.beam_top_width
        if bot_w is None:
            bot_w = self.beam_bottom_width

        h = self.beam_height
        # Extra width: gaussian tails + slant padding on both sides
        pad = int(abs(slant)) + 10
        w = int(bot_w * 1.8) + pad * 2
        cx = w // 2  # top of beam is always at surface center

        r, g, b = base_color
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        surf.fill((0, 0, 0, 0))

        # Bottom rounding: activates in the last (1 - round_start) fraction
        round_start = 0.65  # top 65% is pure trapezoid, bottom 35% gets rounded

        for y in range(h):
            t = y / max(1, h - 1)
            # Beam center drifts horizontally: slant * t pixels at full depth
            beam_cx = cx + slant * t
            half_w = (top_w + (bot_w - top_w) * t) / 2.0
            inv_hw = 1.0 / max(1.0, half_w)

            # Standard trapezoid vertical fade
            v_fade = (1.0 - t) ** 0.6

            # Corner fade only in the bottom zone
            if t > round_start:
                bp = (t - round_start) / (1.0 - round_start)  # 0→1 in bottom zone
                corner_w = max(1.0, half_w)
            else:
                bp = 0.0
                corner_w = 1.0

            for x in range(w):
                dist_x = abs(x - beam_cx) * inv_hw

                # Gaussian horizontal diffusion (soft lateral edges)
                h_fade = math.exp(-1.65 * dist_x * dist_x)

                # Corner fade: at center (dist=0) → no effect; at edge (dist=1) → max fade
                if bp > 0:
                    d_corner = abs(x - beam_cx) / corner_w
                    cf = max(0.0, 1.0 - bp * d_corner * 1.8)
                else:
                    cf = 1.0

                alpha = int(master_alpha * v_fade * h_fade * cf)
                if alpha > 0:
                    surf.set_at((x, y), (r, g, b, min(255, alpha)))

        return surf

    # ------------------------------------------------------------------
    # Torch helpers
    # ------------------------------------------------------------------

    def _get_torch_mask(self, radius: int, intensity: float) -> pygame.Surface:
        """Radial gradient mask (RGBA) for subtracting darkness around torches."""
        key = (radius, int(intensity * TORCH_ALPHA_QUANTIZE))
        if key in self._torch_mask_cache:
            return self._torch_mask_cache[key]

        size = radius * 2
        surf = pygame.Surface((size, size), pygame.SRCALPHA)
        surf.fill((0, 0, 0, 0))
        center = (radius, radius)

        for r in range(radius, 0, -2):
            alpha = int(255 * ((1.0 - r / radius) ** 2) * intensity)
            alpha = max(0, min(255, alpha))
            pygame.draw.circle(surf, (0, 0, 0, alpha), center, r)

        self._torch_mask_cache[key] = surf
        return surf

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    @staticmethod
    def _lerp_color(
        a: tuple[int, int, int], b: tuple[int, int, int], t: float
    ) -> tuple[int, int, int]:
        return (
            int(a[0] + (b[0] - a[0]) * t),
            int(a[1] + (b[1] - a[1]) * t),
            int(a[2] + (b[2] - a[2]) * t),
        )
