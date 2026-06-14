import pygame
from src.config import Settings
from src.engine.asset_manager import AssetManager

type OccludingRect = list[tuple[pygame.Rect, int, pygame.Surface | None]]


class OcclusionRenderer:
    """Helper class managing occlusion compositing for RenderManager."""

    def __init__(self, game):
        self.game = game
        self._occlusion_pool: list[pygame.Surface] = []
        self._alpha_surf: pygame.Surface | None = None
        self._occ_key: tuple[int, int, int] | None = None
        self._occ_composite_cache: dict[object, pygame.Surface] = {}

    def reset_cache(self) -> None:
        """P-004: Invalidate the occlusion dirty-flag cache."""
        self._occ_key = None
        self._occ_composite_cache.clear()

    def _create_composite_occlusion_surface(
        self,
        sprite,
        sprite_screen_rect: pygame.Rect,
        intersections: list[tuple[pygame.Rect, pygame.Rect, pygame.Surface | None]],
        used_composites: int,
    ) -> tuple[pygame.Surface, int]:
        visual_size = sprite.image.get_size()
        if used_composites < len(self._occlusion_pool):
            composite = self._occlusion_pool[used_composites]
            if composite.get_size() != visual_size:
                composite = pygame.Surface(visual_size, pygame.SRCALPHA)
                self._occlusion_pool[used_composites] = composite
        else:
            composite = pygame.Surface(visual_size, pygame.SRCALPHA)
            self._occlusion_pool.append(composite)
        used_composites += 1
        composite.fill((0, 0, 0, 0))
        composite.blit(sprite.image, (0, 0))

        for isect, occ_rect, tile_img in intersections:
            if isect.width <= 0 or isect.height <= 0:
                continue

            local_rect = pygame.Rect(
                isect.x - sprite_screen_rect.x,
                isect.y - sprite_screen_rect.y,
                isect.width,
                isect.height,
            )

            mask = AssetManager().get_occlusion_mask(tile_img) if tile_img is not None else None

            if mask is None:
                composite.fill((0, 0, 0, 0), local_rect)
                if self._alpha_surf is None or self._alpha_surf.get_size() != local_rect.size:
                    self._alpha_surf = pygame.Surface(local_rect.size, pygame.SRCALPHA)
                self._alpha_surf.fill((0, 0, 0, 0))
                self._alpha_surf.blit(sprite.image, (0, 0), local_rect)
                self._alpha_surf.set_alpha(Settings.OCCLUSION_ALPHA)
                composite.blit(self._alpha_surf, local_rect.topleft)
            else:
                tile_crop_rect = pygame.Rect(
                    isect.x - occ_rect.x,
                    isect.y - occ_rect.y,
                    isect.width,
                    isect.height,
                )
                if self._alpha_surf is None or self._alpha_surf.get_size() != local_rect.size:
                    self._alpha_surf = pygame.Surface(local_rect.size, pygame.SRCALPHA)
                self._alpha_surf.fill((0, 0, 0, 0))
                self._alpha_surf.blit(mask, (0, 0), area=tile_crop_rect)
                composite.blit(
                    self._alpha_surf,
                    local_rect.topleft,
                    special_flags=pygame.BLEND_RGBA_MULT,
                )

        return composite, used_composites

    def apply_partial_occlusion(
        self, occluding_rects: OccludingRect
    ) -> dict[object, pygame.Surface]:
        if not occluding_rects:
            self._occ_key = None
            self._occ_composite_cache.clear()
            return dict()

        cam_offset = self.game.visible_sprites.offset
        current_key = (int(cam_offset.x), int(cam_offset.y), len(occluding_rects))

        any_moving = any(
            getattr(sp, "is_moving", False) for sp in self.game.visible_sprites.sprites()
        )

        if not any_moving and current_key == self._occ_key and self._occ_composite_cache:
            saved_images: dict[object, pygame.Surface] = {}
            for sprite, composite in self._occ_composite_cache.items():
                saved_images[sprite] = sprite.image
                sprite.image = composite
            return saved_images

        player_depth = self.game.player.depth
        walk_active = getattr(self.game, "_intra_walk_target", None) is not None
        used_composites = 0
        saved_images = {}
        new_cache: dict[object, pygame.Surface] = {}

        for sprite in self.game.visible_sprites.get_sorted_sprites():
            if not sprite.image or not sprite.rect:
                continue
            sprite_depth = getattr(sprite, "depth", 1)
            if sprite_depth < player_depth:
                continue
            if walk_active and sprite == self.game.player:
                continue

            visual_rect = sprite.image.get_rect(bottomright=sprite.rect.bottomright)
            stair_y_offset = getattr(sprite, "current_stair_offset", 0.0)
            if not isinstance(stair_y_offset, int | float):
                stair_y_offset = 0.0

            sprite_screen_rect = pygame.Rect(
                (visual_rect.left + cam_offset.x, visual_rect.top + cam_offset.y + stair_y_offset),
                visual_rect.size,
            )

            intersections = [
                (sprite_screen_rect.clip(occ_rect), occ_rect, tile_img)
                for occ_rect, tile_depth, tile_img in occluding_rects
                if tile_depth > sprite_depth and sprite_screen_rect.colliderect(occ_rect)
            ]
            if not intersections:
                continue

            composite, used_composites = self._create_composite_occlusion_surface(
                sprite, sprite_screen_rect, intersections, used_composites
            )

            saved_images[sprite] = sprite.image
            sprite.image = composite
            new_cache[sprite] = composite

        self._occ_key = current_key
        self._occ_composite_cache = new_cache
        return saved_images
