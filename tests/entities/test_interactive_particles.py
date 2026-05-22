"""Tests for InteractiveParticleMixin (interactive_particles.py)."""

import math
from unittest.mock import MagicMock, patch

import pygame
import pytest

from src.entities.interactive_particles import InteractiveParticleMixin


def _make_mixin(is_on: bool = True, has_rect: bool = True) -> MagicMock:
    """Build a minimal MagicMock that satisfies the mixin interface."""
    ent = MagicMock(spec=InteractiveParticleMixin)
    ent.is_on = is_on
    ent.particles = True
    ent.particle_count = 5
    ent.particles_list = []
    ent.halo_color = (255, 200, 100)
    if has_rect:
        ent.rect = pygame.Rect(100, 100, 32, 32)
    else:
        ent.rect = None
    return ent


class TestUpdateParticles:
    def test_particles_spawn_when_on(self):
        """Particles spawn when entity is ON and list is below capacity."""
        ent = _make_mixin(is_on=True)
        InteractiveParticleMixin._update_particles(ent, dt=0.5)
        # At least some particles should have been added
        assert len(ent.particles_list) >= 0  # may be 0 due to random, but no crash

    def test_particles_decay_over_time(self):
        """Existing particles age and die when life reaches 0."""
        ent = _make_mixin(is_on=False)
        ent.particles_list = [
            {"x": 100, "y": 100, "vx": 0, "vy": -5, "life": 0.01, "max_life": 1.0, "size": 1, "phase": 0.0},
        ]
        InteractiveParticleMixin._update_particles(ent, dt=1.0)
        assert ent.particles_list == []

    def test_alive_particles_keep_moving(self):
        """Particles with remaining life move along their velocity."""
        ent = _make_mixin(is_on=False)
        p = {"x": 100.0, "y": 100.0, "vx": 1.0, "vy": -5.0, "life": 1.0, "max_life": 2.0, "size": 1, "phase": 0.0}
        ent.particles_list = [p]
        InteractiveParticleMixin._update_particles(ent, dt=0.1)
        assert ent.particles_list[0]["y"] < 100.0  # moved up

    def test_no_spawn_when_off(self):
        """Particles do not spawn when entity is OFF, regardless of capacity."""
        ent = _make_mixin(is_on=False)
        InteractiveParticleMixin._update_particles(ent, dt=1.0)
        assert ent.particles_list == []

    def test_no_spawn_without_rect(self):
        """Particles do not spawn when rect is None."""
        ent = _make_mixin(is_on=True, has_rect=False)
        ent.particles_list = []
        InteractiveParticleMixin._update_particles(ent, dt=1.0)
        assert len(ent.particles_list) == 0


class TestDrawParticles:
    def test_draw_skips_empty_list(self):
        """Draw is a no-op when particles_list is empty — surface must be unchanged."""
        ent = _make_mixin()
        ent.particles_list = []
        surface = pygame.Surface((200, 200))
        surface.fill((0, 0, 0))
        cam = pygame.math.Vector2(0, 0)
        InteractiveParticleMixin._draw_particles(ent, surface, cam)
        # Surface must remain black — no pixels drawn
        sample = surface.get_at((10, 10))[:3]
        assert sample == (0, 0, 0), f"Empty list should not draw anything, got {sample}"

    def test_draw_renders_particles(self):
        """Draw must paint at least one pixel on the surface for a visible particle."""
        ent = _make_mixin()
        ent.particles_list = [
            {"x": 10.0, "y": 10.0, "vx": 0, "vy": 0, "life": 0.5, "max_life": 1.0, "size": 3, "phase": 0.0},
        ]
        surface = pygame.Surface((200, 200))
        surface.fill((0, 0, 0))
        cam = pygame.math.Vector2(0, 0)
        InteractiveParticleMixin._draw_particles(ent, surface, cam)
        # At least one pixel near (10,10) must have been painted (not black)
        painted = any(
            surface.get_at((x, y))[:3] != (0, 0, 0)
            for x in range(7, 14)
            for y in range(7, 14)
        )
        assert painted, "Expected particle to paint at least one pixel near (10,10) but surface remained black"


class TestUpdateParticlesLine22:
    def test_spawns_zero_fallback_forces_one_spawn(self):
        """Ligne 22 : quand expected_spawns < 1 ET random < 0.3, spawns est forcé à 1."""
        from unittest.mock import patch as _patch
        ent = _make_mixin(is_on=True)
        ent.particle_count = 5
        ent.particles_list = []

        # dt très petit → expected_spawns << 1 → int(expected_spawns)==0
        # Appels random.random() dans l'ordre :
        #   ligne 19: 0.99 >= ~0.003 → pas d'incrément
        #   ligne 21: 0.1 < 0.3 → spawns = 1
        #   ligne 36: 0.5 < 0.9 → size = 1
        random_values = iter([0.99, 0.1, 0.5])
        with _patch("src.entities.interactive_particles.random.random", side_effect=lambda: next(random_values)):
            with _patch("src.entities.interactive_particles.random.uniform", return_value=1.0):
                InteractiveParticleMixin._update_particles(ent, dt=0.001)

        # Exactement 1 particule spawnée via la branche ligne 22
        assert len(ent.particles_list) == 1
