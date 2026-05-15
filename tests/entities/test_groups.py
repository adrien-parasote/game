import json
import logging
from unittest.mock import MagicMock, patch

import pygame
import pytest

from src.config import Settings


class TestCameraGroupCoverage:

    def test_init_no_display(self):
        from src.entities.groups import CameraGroup
        with patch.object(pygame.display, "get_surface", return_value=None):
            cg = CameraGroup()
        assert cg.half_width == 0

    def test_calculate_offset_no_rect(self):
        from src.entities.groups import CameraGroup
        cg = CameraGroup()
        sprite = MagicMock(rect=None)
        assert cg.calculate_offset(sprite) == cg.offset

    def test_calculate_offset_small_world_centers(self):
        """When world is smaller than screen, offset should center the map (>= 0).

        Force explicit screen dimensions so the test is independent of pygame
        display state across the test session.
        """
        from src.entities.groups import CameraGroup
        cg = CameraGroup()
        # Force deterministic screen size — avoids dependency on pygame display state
        cg.half_width = 640
        cg.half_height = 360
        cg.display_surface = pygame.Surface((1280, 720))
        cg.world_size = (100, 100)
        sprite = MagicMock()
        sprite.rect = pygame.Rect(50, 50, 32, 32)
        cg.calculate_offset(sprite)
        assert cg.offset.x >= 0

    def test_calculate_offset_large_world_clamps(self):
        from src.entities.groups import CameraGroup
        cg = CameraGroup()
        cg.world_size = (9000, 9000)
        sprite = MagicMock()
        sprite.rect = pygame.Rect(4500, 4500, 32, 32)
        result = cg.calculate_offset(sprite)
        assert isinstance(result, pygame.math.Vector2)

    def test_set_world_size(self):
        from src.entities.groups import CameraGroup
        cg = CameraGroup()
        cg.set_world_size(1920, 1080)
        assert cg.world_size == (1920, 1080)

    def test_custom_draw_moving_sprite_invalidates_cache(self):
        from src.entities.groups import CameraGroup
        cg = CameraGroup()
        cg._cache_dirty = False
        moving = MagicMock()
        moving.is_moving = True
        surf = pygame.Surface((800, 600))
        with patch.object(cg, "sprites", return_value=[moving]):
            with patch.object(cg, "get_sorted_sprites", return_value=[]):
                cg.custom_draw(surf)
        assert cg._cache_dirty

    def test_debug_rect_drawn_for_onscreen_sprite(self):
        from src.entities.groups import CameraGroup
        cg = CameraGroup()
        sprite = MagicMock()
        sprite.is_moving = False
        sprite.image = pygame.Surface((32, 32))
        sprite.rect = pygame.Rect(0, 0, 32, 32)
        original = Settings.DEBUG
        Settings.DEBUG = True
        try:
            with patch.object(cg, "sprites", return_value=[]):
                with patch.object(cg, "get_sorted_sprites", return_value=[sprite]):
                    with patch("pygame.draw.rect") as mock_rect:
                        cg.custom_draw(pygame.Surface((800, 600)))
                        assert mock_rect.called
        finally:
            Settings.DEBUG = original

