import pygame
from typing import List

class CameraGroup(pygame.sprite.Group):
    """
    A specialized sprite group that handles Y-sorting (Depth Sorting)
    and camera offset displacement during drawing.
    """
    
    def __init__(self):
        super().__init__()
        self.display_surface = pygame.display.get_surface()
        self.offset = pygame.math.Vector2()
        self.half_width = self.display_surface.get_size()[0] // 2
        self.half_height = self.display_surface.get_size()[1] // 2
        self.world_size = (0, 0)

    def set_world_size(self, width: int, height: int):
        """Set the boundaries of the world in pixels."""
        self.world_size = (width, height)

    def calculate_offset(self, target: pygame.sprite.Sprite) -> pygame.math.Vector2:
        """Calculate and clamp the camera offset relative to a target sprite."""
        # Standard centering offset
        off_x = self.half_width - target.rect.centerx
        off_y = self.half_height - target.rect.centery

        # Screen dimensions
        sw, sh = self.display_surface.get_size()
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

    def get_sorted_sprites(self) -> List[pygame.sprite.Sprite]:
        """Return sprites sorted by their Y-coordinate (bottom)."""
        return sorted(self.sprites(), key=lambda sprite: sprite.rect.bottom)

    def custom_draw(self, surface: pygame.Surface):
        """Draw sprites with already calculated camera offset and Y-sorting."""
        # Get screen rect for culling
        screen_rect = surface.get_rect()
        
        # Sort and draw
        for sprite in self.get_sorted_sprites():
            # Align bottom-right of sprite image to bottom-right of logical hitbox
            visual_rect = sprite.image.get_rect(bottomright=sprite.rect.bottomright)
            
            # Calculate world visual rect in screen space
            offset_pos = visual_rect.topleft + self.offset
            
            # Simple Frustum Culling: check if sprite overlaps screen
            screen_sprite_rect = pygame.Rect(offset_pos, visual_rect.size)
            if screen_rect.colliderect(screen_sprite_rect):
                surface.blit(sprite.image, offset_pos)
                
                # Debug Hitbox Rendering
                from src.config import Settings
                if Settings.DEBUG:
                    debug_rect = sprite.rect.move(self.offset.x, self.offset.y)
                    pygame.draw.rect(surface, (255, 0, 0), debug_rect, 1)
