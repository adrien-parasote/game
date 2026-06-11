import pygame
from src.config import Settings

class WadingRenderer:
    """Helper class managing grass wading compositing for RenderManager."""

    def __init__(self, game):
        self.game = game
        self._wading_composite: pygame.Surface | None = None
        self._wading_alpha_surf: pygame.Surface | None = None

    def reset_cache(self) -> None:
        """TC-RPERF-U-004: reset_render_caches sets _wading_composite to None."""
        self._wading_composite = None
        self._wading_alpha_surf = None

    def _blit_grass_tile_intersections(
        self,
        wading_surf: pygame.Surface,
        grass_img: pygame.Surface,
        cam_offset: pygame.Vector2,
        tile_size: int,
        wading_screen_left: int,
        wading_screen_right: int,
        wading_screen_top: int,
        wading_screen_bottom: int,
        col_start: int,
        col_end: int,
        row_start: int,
        row_end: int,
    ) -> None:
        for col in range(col_start, col_end + 1):
            for row in range(row_start, row_end + 1):
                tile_world_x = col * tile_size
                tile_world_y = row * tile_size
                tile_screen_x = tile_world_x + cam_offset.x
                tile_screen_y = tile_world_y + cam_offset.y

                isect_left = max(wading_screen_left, tile_screen_x)
                isect_top = max(wading_screen_top, tile_screen_y)
                isect_right = min(wading_screen_right, tile_screen_x + tile_size)
                isect_bottom = min(wading_screen_bottom, tile_screen_y + tile_size)
                isect_w = isect_right - isect_left
                isect_h = isect_bottom - isect_top
                if isect_w <= 0 or isect_h <= 0:
                    continue

                crop_x = int(isect_left - tile_screen_x)
                crop_y = int(isect_top - tile_screen_y)
                grass_crop = pygame.Rect(crop_x, crop_y, int(isect_w), int(isect_h))

                dest_x = int(isect_left - wading_screen_left)
                dest_y = int(isect_top - wading_screen_top)
                wading_surf.blit(grass_img, (dest_x, dest_y), area=grass_crop)

    def _build_wading_composite(
        self,
        sprite,
        cam_offset: pygame.Vector2,
        tile_size: int,
        wading_depth: int,
        wading_alpha: int,
    ) -> pygame.Surface | None:
        foot_world_x = sprite.rect.centerx
        foot_world_y = sprite.rect.bottom - 2

        grass_img = self.game.map_manager.get_grass_tile_image_at(foot_world_x, foot_world_y)
        if not isinstance(grass_img, pygame.Surface):
            return None

        visual_size = sprite.image.get_size()
        img_w, img_h = visual_size

        local_wading_top = max(0, img_h - wading_depth)
        local_wading_h = img_h - local_wading_top
        if local_wading_h <= 0:
            return None

        if self._wading_composite is None or self._wading_composite.get_size() != visual_size:
            self._wading_composite = pygame.Surface(visual_size, pygame.SRCALPHA)

        composite = self._wading_composite.copy()
        
        composite.fill((0, 0, 0, 0))
        composite.blit(sprite.image, (0, 0))

        visual_rect = sprite.image.get_rect(bottomright=sprite.rect.bottomright)
        stair_y_offset = getattr(sprite, 'current_stair_offset', 0.0)
        if not isinstance(stair_y_offset, (int, float)):
            stair_y_offset = 0.0

        sprite_screen_left = visual_rect.left + cam_offset.x
        sprite_screen_top = visual_rect.top + cam_offset.y + stair_y_offset

        wading_screen_top = sprite_screen_top + local_wading_top
        wading_screen_left = sprite_screen_left
        wading_screen_right = sprite_screen_left + img_w
        wading_screen_bottom = sprite_screen_top + img_h

        col_start = int((wading_screen_left - cam_offset.x) // tile_size)
        col_end = int((wading_screen_right - cam_offset.x - 1) // tile_size)
        row_start = int((wading_screen_top - cam_offset.y) // tile_size)
        row_end = int((wading_screen_bottom - cam_offset.y - 1) // tile_size)

        wading_size = (img_w, local_wading_h)
        if getattr(self, "_wading_alpha_surf", None) is None or self._wading_alpha_surf.get_size() != wading_size:
            self._wading_alpha_surf = pygame.Surface(wading_size, pygame.SRCALPHA)
        self._wading_alpha_surf.fill((0, 0, 0, 0))
        wading_surf = self._wading_alpha_surf

        self._blit_grass_tile_intersections(
            wading_surf,
            grass_img,
            cam_offset,
            tile_size,
            wading_screen_left,
            wading_screen_right,
            wading_screen_top,
            wading_screen_bottom,
            col_start,
            col_end,
            row_start,
            row_end,
        )

        wading_surf.set_alpha(wading_alpha)
        composite.blit(wading_surf, (0, local_wading_top))
        return composite

    def apply_grass_wading_to_images(
        self,
        cam_offset: pygame.Vector2 | None = None,
        pre_occlusion_originals: dict[object, pygame.Surface] | None = None,
    ) -> dict[object, pygame.Surface]:
        if not self.game.map_manager:
            empty_res: dict[object, pygame.Surface] = {}
            return empty_res

        if not getattr(self.game.map_manager, "_map_has_grass", False):
            empty_res2: dict[object, pygame.Surface] = {}
            return empty_res2

        if cam_offset is None:
            cam_offset = self.game.visible_sprites.offset
        assert cam_offset is not None
        pre_occ = pre_occlusion_originals or {}
        tile_size = self.game.tile_size
        wading_depth = Settings.GRASS_WADING_DEPTH
        wading_alpha = Settings.GRASS_WADING_ALPHA
        player_depth = self.game.player.depth
        walk_active = getattr(self.game, "_intra_walk_target", None) is not None
        wading_only_originals: dict[object, pygame.Surface] = {}

        for sprite in self.game.visible_sprites.get_sorted_sprites():
            if not sprite.image or not sprite.rect:
                continue
            if getattr(sprite, "depth", 1) < player_depth:
                continue
            if walk_active and sprite == self.game.player:
                continue

            composite = self._build_wading_composite(
                sprite, cam_offset, tile_size, wading_depth, wading_alpha
            )
            if composite is not None:
                if sprite not in pre_occ:
                    wading_only_originals[sprite] = sprite.image
                sprite.image = composite

        return wading_only_originals
