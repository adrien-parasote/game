from unittest.mock import MagicMock, patch

import pygame
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


class TestCameraGroupSortY:
    """Tests for the sort_y override in CameraGroup.get_sorted_sprites().

    By default sprites sort by rect.bottom (Y-sort). A sprite with a custom
    sort_y attribute overrides this key — used by bridge entities to sort by
    rect.top so that actors standing on the bridge render in front of it.
    """

    def _make_sprite(self, bottom: int, sort_y: int | None = None) -> MagicMock:
        """Return a minimal sprite mock with optional sort_y override."""
        sp = MagicMock()
        sp.image = pygame.Surface((32, 32))
        sp.rect = pygame.Rect(0, bottom - 32, 32, 32)
        sp.is_moving = False
        if sort_y is not None:
            sp.sort_y = sort_y
        else:
            # Ensure the attribute is absent so getattr falls back to rect.bottom
            if hasattr(sp, "sort_y"):
                del sp.sort_y
        return sp

    def test_default_sort_uses_rect_bottom(self):
        """Sprites without sort_y are ordered by rect.bottom ascending."""
        from src.entities.groups import CameraGroup
        cg = CameraGroup()
        sp_high = self._make_sprite(bottom=200)  # lower in scene
        sp_low = self._make_sprite(bottom=100)   # higher in scene
        with patch.object(cg, "sprites", return_value=[sp_high, sp_low]):
            cg._cache_dirty = True
            result = cg.get_sorted_sprites()
        assert result == [sp_low, sp_high]

    def test_sort_y_overrides_rect_bottom(self):
        """A sprite with sort_y uses that value instead of rect.bottom.

        Scenario: bridge (large rect.bottom=500) sets sort_y=100 so that
        a player with rect.bottom=300 renders after (in front of) the bridge.
        """
        from src.entities.groups import CameraGroup
        cg = CameraGroup()
        bridge = self._make_sprite(bottom=500, sort_y=100)
        player = self._make_sprite(bottom=300)
        with patch.object(cg, "sprites", return_value=[player, bridge]):
            cg._cache_dirty = True
            result = cg.get_sorted_sprites()
        # bridge.sort_y=100 < player.rect.bottom=300 → bridge first
        assert result[0] is bridge
        assert result[1] is player

    def test_sort_y_mixed_with_rect_bottom(self):
        """sort_y and rect.bottom are compared on the same scale.

        Three sprites: bridge (sort_y=50), npc (rect.bottom=150), player (rect.bottom=300).
        Expected render order: bridge, npc, player.
        """
        from src.entities.groups import CameraGroup
        cg = CameraGroup()
        bridge = self._make_sprite(bottom=500, sort_y=50)
        npc = self._make_sprite(bottom=150)
        player = self._make_sprite(bottom=300)
        with patch.object(cg, "sprites", return_value=[player, bridge, npc]):
            cg._cache_dirty = True
            result = cg.get_sorted_sprites()
        assert result == [bridge, npc, player]

    def test_no_rect_sprite_uses_zero(self):
        """Sprite with rect=None and no sort_y defaults to 0 (rendered first)."""
        from src.entities.groups import CameraGroup
        cg = CameraGroup()
        no_rect = MagicMock()
        no_rect.rect = None
        no_rect.is_moving = False
        # Ensure sort_y is absent — MagicMock auto-creates attrs, so spec it out
        no_rect_spec = MagicMock(spec=["rect", "image", "is_moving"])
        no_rect_spec.rect = None
        no_rect_spec.image = None
        no_rect_spec.is_moving = False
        normal = self._make_sprite(bottom=100)
        with patch.object(cg, "sprites", return_value=[normal, no_rect_spec]):
            cg._cache_dirty = True
            result = cg.get_sorted_sprites()
        assert result[0] is no_rect_spec  # key=0 < 100
