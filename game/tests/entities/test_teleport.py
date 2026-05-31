"""Behavioural tests for Teleport entity (teleport.py)."""

import pygame


class TestTeleportInit:
    def test_stores_target_map(self):
        """Teleport stores target_map on creation."""
        from src.entities.teleport import Teleport
        group = pygame.sprite.Group()
        tp = Teleport(
            rect=pygame.Rect(0, 0, 32, 32),
            groups=[group],
            target_map="01-castel.tmj",
            target_spawn_id="spawn_0",
        )
        assert tp.target_map == "01-castel.tmj"

    def test_stores_target_spawn_id(self):
        """Teleport stores target_spawn_id on creation."""
        from src.entities.teleport import Teleport
        group = pygame.sprite.Group()
        tp = Teleport(
            rect=pygame.Rect(0, 0, 32, 32),
            groups=[group],
            target_map="01-castel.tmj",
            target_spawn_id="spawn_42",
        )
        assert tp.target_spawn_id == "spawn_42"

    def test_default_transition_type(self):
        """Default transition_type is 'instant'."""
        from src.entities.teleport import Teleport
        group = pygame.sprite.Group()
        tp = Teleport(
            rect=pygame.Rect(0, 0, 32, 32),
            groups=[group],
            target_map="01-castel.tmj",
            target_spawn_id="spawn_0",
        )
        assert tp.transition_type == "instant"

    def test_default_required_direction(self):
        """Default required_direction is 'any' (no constraint)."""
        from src.entities.teleport import Teleport
        group = pygame.sprite.Group()
        tp = Teleport(
            rect=pygame.Rect(0, 0, 32, 32),
            groups=[group],
            target_map="01-castel.tmj",
            target_spawn_id="spawn_0",
        )
        assert tp.required_direction == "any"

    def test_image_is_transparent(self):
        """The teleport image is transparent (not rendered)."""
        from src.entities.teleport import Teleport
        group = pygame.sprite.Group()
        tp = Teleport(
            rect=pygame.Rect(0, 0, 32, 32),
            groups=[group],
            target_map="01-castel.tmj",
            target_spawn_id="spawn_0",
        )
        assert tp.image.get_alpha() == 0

    def test_in_group_after_creation(self):
        """Teleport sprite registers itself in the given group."""
        from src.entities.teleport import Teleport
        group = pygame.sprite.Group()
        tp = Teleport(
            rect=pygame.Rect(0, 0, 32, 32),
            groups=[group],
            target_map="01-castel.tmj",
            target_spawn_id="spawn_0",
        )
        assert tp in group.sprites()

    def test_rect_matches_input(self):
        """Teleport rect matches the provided Rect."""
        from src.entities.teleport import Teleport
        group = pygame.sprite.Group()
        r = pygame.Rect(64, 128, 32, 32)
        tp = Teleport(rect=r, groups=[group], target_map="x.tmj", target_spawn_id="s0")
        assert tp.rect == r
