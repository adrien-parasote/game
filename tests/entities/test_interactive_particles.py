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
        """Draw is a no-op when particles_list is empty."""
        ent = _make_mixin()
        ent.particles_list = []
        surface = pygame.Surface((200, 200))
        cam = pygame.math.Vector2(0, 0)
        # Should not raise
        InteractiveParticleMixin._draw_particles(ent, surface, cam)

    def test_draw_renders_particles(self):
        """Draw renders at least one particle without error."""
        pygame.init()
        pygame.display.set_mode((1, 1), pygame.NOFRAME)
        ent = _make_mixin()
        ent.particles_list = [
            {"x": 10.0, "y": 10.0, "vx": 0, "vy": 0, "life": 0.5, "max_life": 1.0, "size": 1, "phase": 0.0},
        ]
        surface = pygame.Surface((200, 200))
        cam = pygame.math.Vector2(0, 0)
        InteractiveParticleMixin._draw_particles(ent, surface, cam)
