# src/entities/interactive_particles.py
"""Particle mixin for InteractiveEntity — handles spawning, physics, and rendering."""

import math
import random

import pygame
from src.entities.interactive_constants import PARTICLE_DEFAULT_COLOR


class InteractiveParticleMixin:
    """Mixin handling particle spawning, physics update, and drawing."""

    def _update_particles(self, dt: float) -> None:
        """Spawn and update particle physics."""
        if self.particles and self.is_on and len(self.particles_list) < self.particle_count:
            expected_spawns = (self.particle_count / 1.5) * dt
            spawns = int(expected_spawns)
            if random.random() < (expected_spawns - spawns):
                spawns += 1
            if spawns == 0 and random.random() < 0.3:
                spawns = 1
            for _ in range(spawns):
                if self.rect:
                    life = random.uniform(1.0, 2.0)
                    self.particles_list.append(
                        {
                            "x": self.rect.centerx + random.uniform(-4, 4),
                            "y": self.rect.top + (self.rect.height * 0.33) + random.uniform(-2, 2),
                            "vx": random.uniform(-2.0, 2.0),
                            "vy": random.uniform(-10.0, -5.0),
                            "life": life,
                            "max_life": life,
                            "size": 1 if random.random() < 0.9 else 2,
                            "phase": random.uniform(0, math.pi * 2),
                        }
                    )

        if self.particles_list:
            alive = []
            for p in self.particles_list:
                p["life"] -= dt
                if p["life"] > 0:
                    p["x"] += (p["vx"] + math.sin(p["phase"] + p["life"] * 3.0) * 5.0) * dt
                    p["y"] += p["vy"] * dt
                    alive.append(p)
            self.particles_list = alive

    def _draw_particles(
        self,
        surface: pygame.Surface,
        cam_offset: pygame.math.Vector2,
    ) -> None:
        """Draw particle effects."""
        if not self.particles_list:
            return

        base_color = getattr(self, "halo_color", PARTICLE_DEFAULT_COLOR)
        for p in self.particles_list:
            alpha = (p["life"] / p["max_life"]) ** 0.6
            color = (
                int(base_color[0] * alpha),
                int(base_color[1] * alpha),
                int(base_color[2] * alpha),
            )
            # P14: removed useless Surface alloc — draw.circle is sufficient
            pygame.draw.circle(
                surface,
                color,
                (int(p["x"] + cam_offset.x), int(p["y"] + cam_offset.y)),
                p["size"],
            )
