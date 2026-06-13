from typing import override

import pygame
from src.config import Settings


class CameraGroup(pygame.sprite.Group):
    """
    A specialized sprite group that handles Y-sorting (Depth Sorting)
    and camera offset displacement during drawing.
    """

    def __init__(self):
        super().__init__()
        self.display_surface = pygame.display.get_surface()
        self.offset = pygame.math.Vector2()
        if self.display_surface:
            self.half_width = self.display_surface.get_size()[0] // 2
            self.half_height = self.display_surface.get_size()[1] // 2
        else:
            self.half_width = 0
            self.half_height = 0
        self.world_size = (0, 0)
        self._sorted_cache: list[pygame.sprite.Sprite] = []
        self._cache_dirty: bool = True

    def set_world_size(self, width: int, height: int):
        """Set the boundaries of the world in pixels."""
        self.world_size = (width, height)

    def calculate_offset(self, target: pygame.sprite.Sprite) -> pygame.math.Vector2:
        """Calculate and clamp the camera offset relative to a target sprite."""
        if not target.rect:
            return self.offset
        # Standard centering offset
        off_x = self.half_width - target.rect.centerx
        off_y = self.half_height - target.rect.centery

        # Screen dimensions
        if self.display_surface:
            sw, sh = self.display_surface.get_size()
        else:
            sw, sh = 0, 0
        ww, wh = self.world_size

        # Clamp X logic
        if ww < sw:
            # Center the map if smaller than screen
            self.offset.x = (sw - ww) // 2
        else:
            # Bound camera between 0 and (world_size - screen_size)
            # offset.x is applied as world_pos + offset.x = screen_pos
            # so screen_pos 0 = world_pos 0 -> offset.x = 0
            # screen_pos 0 = world_pos (ww-sw) -> offset.x = -(ww-sw)
            self.offset.x = min(0, max(off_x, -(ww - sw)))

        # Clamp Y logic
        if wh < sh:
            self.offset.y = (sh - wh) // 2
        else:
            self.offset.y = min(0, max(off_y, -(wh - sh)))

        return self.offset

    def mark_dirty(self) -> None:
        """Invalidate the Y-sort cache — call after any sprite position change."""
        self._cache_dirty = True

    @override
    def add(self, *sprites) -> None:  # type: ignore[override]
        super().add(*sprites)
        self._cache_dirty = True

    @override
    def remove(self, *sprites) -> None:  # type: ignore[override]
        super().remove(*sprites)
        self._cache_dirty = True

    def get_sorted_sprites(self) -> list[pygame.sprite.Sprite]:
        """Return sprites sorted by Y-coordinate.

        Uses `sort_y` attribute when available (e.g. bridge uses rect.top so
        that sprites walking on it always render in front). Falls back to
        rect.bottom for standard depth-sorted entities.
        """
        if self._cache_dirty:
            self._sorted_cache = sorted(
                self.sprites(),
                key=lambda s: getattr(s, "sort_y", s.rect.bottom if s.rect else 0),
            )
            self._cache_dirty = False
        return self._sorted_cache

    def custom_draw(  # noqa: C901
        self, surface: pygame.Surface, min_depth: int | None = None, max_depth: int | None = None
    ):
        """Draw sprites with already calculated camera offset and Y-sorting."""
        # Invalidate sort cache if any sprite is currently moving
        if not self._cache_dirty:
            for sp in self.sprites():
                if getattr(sp, "is_moving", False):
                    self._cache_dirty = True
                    break

        # Get screen rect for culling
        screen_rect = surface.get_rect()

        # Sort and draw
        for sprite in self.get_sorted_sprites():
            if not sprite.image or not sprite.rect:
                continue

            # Depth filtering
            sprite_depth = getattr(sprite, "depth", 1)
            if min_depth is not None and sprite_depth < min_depth:
                continue
            if max_depth is not None and sprite_depth > max_depth:
                continue

            # Align bottom-right of sprite image to bottom-right of logical hitbox
            visual_rect = sprite.image.get_rect(bottomright=sprite.rect.bottomright)

            # Dynamic stair visual offset (interpolated — replaces old _vertical_move-based offset)
            stair_y_offset = getattr(sprite, 'current_stair_offset', 0.0)
            if not isinstance(stair_y_offset, int | float):
                stair_y_offset = 0.0

            # Calculate world visual rect in screen space
            offset_pos = (visual_rect.left + self.offset.x, visual_rect.top + self.offset.y + stair_y_offset)

            # Simple Frustum Culling: check if sprite overlaps screen
            screen_sprite_rect = pygame.Rect(offset_pos, visual_rect.size)
            if screen_rect.colliderect(screen_sprite_rect):
                stair_clip = getattr(sprite, 'current_stair_clip', 0.0)
                if stair_clip > 0:
                    clipped_image = pygame.Surface(visual_rect.size, pygame.SRCALPHA)
                    clipped_image.blit(sprite.image, (0, 0))
                    clip_rect = pygame.Rect(
                        0,
                        visual_rect.height - int(stair_clip),
                        visual_rect.width,
                        int(stair_clip)
                    )
                    clipped_image.fill((0, 0, 0, 0), clip_rect, pygame.BLEND_RGBA_MIN)
                    surface.blit(clipped_image, offset_pos)
                else:
                    surface.blit(sprite.image, offset_pos)

                # Debug Hitbox Rendering
                if Settings.DEBUG:
                    debug_rect = sprite.rect.move(self.offset.x, self.offset.y)
                    try:  # noqa: SIM105
                        pygame.draw.rect(surface, (255, 0, 0), debug_rect, 1)
                    except TypeError:
                        # Fallback for mock surfaces in tests where pygame.draw.rect fails
                        pass
