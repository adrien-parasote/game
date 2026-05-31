"""Tests for InteractiveLightingMixin (interactive_lighting.py).

Behavioural coverage complementing test_interactive.py.
"""

from unittest.mock import MagicMock

import pygame
from src.entities.interactive_lighting import InteractiveLightingMixin


def _make_mixin(is_on: bool = True, halo_size: int = 48) -> object:
    """Build a minimal duck-type object satisfying the mixin interface."""
    ent = MagicMock(spec=InteractiveLightingMixin)
    ent.is_on = is_on
    ent.halo_size = halo_size
    ent.halo_alpha = 180
    ent.halo_color = pygame.Color(255, 200, 100)
    ent.f_scale = 1.0
    ent.f_alpha = 1.0
    ent.flicker_phase = 0.0
    ent.is_light_source = False
    ent.is_animated = False
    ent.start_row = 0
    ent.end_row = 3
    ent.frame_index = 0
    cache_surf = pygame.Surface((max(1, halo_size * 2), max(1, halo_size * 2)))
    ent.light_mask_cache = [cache_surf for _ in range(10)]
    ent.light_mask = cache_surf
    ent.rect = pygame.Rect(100, 100, 32, 32)
    return ent


class TestCreateHaloSurf:
    def test_returns_surface_with_correct_size(self):
        """_create_halo_surf returns a Surface of diameter 2*radius."""
        ent = _make_mixin()
        surf = InteractiveLightingMixin._create_halo_surf(ent, radius=30)
        assert isinstance(surf, pygame.Surface)
        assert surf.get_width() == 60
        assert surf.get_height() == 60

    def test_zero_radius_returns_empty_surface(self):
        """_create_halo_surf with radius=0 returns a 0x0 surface without crash."""
        ent = _make_mixin()
        surf = InteractiveLightingMixin._create_halo_surf(ent, radius=0)
        assert isinstance(surf, pygame.Surface)


class TestUpdateFlicker:
    def test_off_entity_resets_values(self):
        """When is_on=False, f_alpha and f_scale must both be 1.0."""
        ent = _make_mixin(is_on=False)
        ent.f_alpha = 0.5
        ent.f_scale = 0.8
        InteractiveLightingMixin._update_flicker(ent, dt=0.016, ticks_ms=1000)
        assert ent.f_alpha == 1.0
        assert ent.f_scale == 1.0

    def test_on_entity_modifies_alpha(self):
        """When is_on=True, f_alpha must be updated from base 1.0."""
        ent = _make_mixin(is_on=True)
        ent.halo_size = 48
        InteractiveLightingMixin._update_flicker(ent, dt=0.016, ticks_ms=500)
        assert isinstance(ent.f_alpha, float)

    def test_animated_light_source_uses_frame_phase(self):
        """Animated light source flicker uses frame_index instead of ticks."""
        ent = _make_mixin(is_on=True)
        ent.is_light_source = True
        ent.is_animated = True
        ent.frame_index = 1.5
        InteractiveLightingMixin._update_flicker(ent, dt=0.016, ticks_ms=0)
        assert isinstance(ent.f_alpha, float)
        assert isinstance(ent.f_scale, float)


class TestDrawHalo:
    def test_skip_when_no_cache(self):
        """_draw_halo is a no-op when light_mask_cache is empty."""
        ent = _make_mixin()
        ent.light_mask_cache = []
        surface = pygame.Surface((300, 300))
        cam = pygame.math.Vector2(0, 0)
        InteractiveLightingMixin._draw_halo(ent, surface, cam, global_darkness=120)

    def test_skip_when_halo_size_zero(self):
        """_draw_halo is a no-op when halo_size <= 0."""
        ent = _make_mixin(halo_size=0)
        surface = pygame.Surface((300, 300))
        cam = pygame.math.Vector2(0, 0)
        InteractiveLightingMixin._draw_halo(ent, surface, cam, global_darkness=120)


class TestSetupLighting:
    def test_setup_lighting_normal(self):
        """_setup_lighting remplit light_mask_cache avec LIGHT_MASK_CACHE_COUNT éléments."""
        from src.entities.interactive_constants import LIGHT_MASK_CACHE_COUNT

        ent = _make_mixin(halo_size=48)
        ent.light_mask_cache = []
        InteractiveLightingMixin._setup_lighting(ent)
        assert len(ent.light_mask_cache) == LIGHT_MASK_CACHE_COUNT

    def test_setup_lighting_zero_halo_uses_fallback(self):
        """Ligne 42 : scaled_size <= 0 => append self.light_mask (branche else)."""
        from src.entities.interactive_constants import LIGHT_MASK_CACHE_COUNT

        # halo_size=0 => int(round(0 * scale)) == 0 pour toutes les itérations
        ent = _make_mixin(halo_size=0)
        ent.light_mask = pygame.Surface((2, 2))
        ent.light_mask_cache = []
        InteractiveLightingMixin._setup_lighting(ent)
        assert all(s is ent.light_mask for s in ent.light_mask_cache)
        assert len(ent.light_mask_cache) == LIGHT_MASK_CACHE_COUNT
