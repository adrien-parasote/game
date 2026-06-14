import math

import pygame
from src.config import Settings
from src.engine.lighting_constants import INDOOR_ATTENUATION
from src.engine.render_occlusion import OccludingRect, OcclusionRenderer
from src.engine.render_wading import WadingRenderer

# Python 3.12 type aliases — replace inline annotations used across multiple methods
type BlitSequence = list[tuple[pygame.Surface, tuple[int, int]]]


class RenderManager:
    """Handles all visual rendering logic for the game scene, decoupling it from the main event loop."""

    def __init__(self, game):
        self.game = game
        # Pre-allocated reusable Rects — updated in-place to avoid per-frame allocations
        self._tile_rect = pygame.Rect(0, 0, game.tile_size, game.tile_size)
        self._screen_rect = pygame.Rect(0, 0, game.screen.get_width(), game.screen.get_height())
        self._viewport_world = pygame.Rect(0, 0, 0, 0)
        # F3: Pre-computed animated tile caches — populated once per frame in draw_scene()
        self._frame_anim_all: list[tuple[int, int, int, int]] = []
        self._frame_anim_by_layer: dict[int, list[tuple[int, int, int, int]]] = {}
        # Frame-level viewport-culled foreground cache to optimize loops
        self._frame_visible_fg_tiles: (
            list[tuple[int, int, int, pygame.Surface, pygame.Surface | None]] | None
        ) = None
        # Pool size 2000 is sufficient to cover standard viewport bounds (40x22 tiles)
        self._rect_pool = [pygame.Rect(0, 0, game.tile_size, game.tile_size) for _ in range(2000)]

        self.occlusion_renderer = OcclusionRenderer(game)
        self.wading_renderer = WadingRenderer(game)

    def draw_background(self):
        """Draw tiles with depth <= player depth (behind player).
        Static and animated tiles are rendered per-layer in order so that
        a higher-order layer always appears on top regardless of animation.
        """
        cam_offset = self.game.visible_sprites.offset

        for layer_id in self.game.map_manager.layer_order:
            layer_order_val = self.game.map_manager.layer_depths.get(layer_id, 0)
            if layer_order_val > self.game.player.depth:
                continue

            # 1. Static tiles for this layer
            surface = self.game.map_manager.get_layer_surface(
                layer_id, pygame, max_bg_depth=self.game.player.depth
            )
            if surface:
                self.game.screen.blit(surface, (cam_offset.x, cam_offset.y))

            # 2. Animated tiles for this layer — F3: read from pre-computed cache
            # Cache pre-populated by draw_scene() — tests must set self._frame_anim_by_layer (A-PERF-002)
            if self.game.anim_map_manager:
                anim_blits = []
                for px, py, tile_id, depth in self._frame_anim_by_layer.get(layer_id, []):
                    if depth <= self.game.player.depth:
                        img = self.game.anim_map_manager.get_current_frame_image(tile_id)
                        if img:
                            anim_blits.append((img, (px + cam_offset.x, py + cam_offset.y)))
                if anim_blits:
                    self.game.screen.fblits(anim_blits)

    def _blit_foreground_surface(
        self,
        cam_offset: pygame.Vector2,
        player_depth: int,
    ) -> None:
        """P-001: Blit the pre-rendered foreground WorldSurface for each layer.

        One screen.blit call per layer (vs N blits in the old loop).
        The source rect clips the surface to the current viewport so only the
        visible portion is sent to the renderer — no overdraw outside the screen.

        Anti-pattern: never call get_foreground_layer_surface() per-frame without
        the lazy-cache guard inside MapManager (it allocates a Surface on first call).
        Error: if the layer surface is None (build failed), this layer is silently
        skipped — logged by MapManager, not re-raised here.
        """
        screen_w = self._screen_rect.width
        screen_h = self._screen_rect.height

        for layer_id in self.game.map_manager.layer_order:
            layer_order_val = self.game.map_manager.layer_depths.get(layer_id, 0)
            if layer_order_val <= player_depth:
                continue  # background layer — skip

            surface = self.game.map_manager.get_foreground_layer_surface(
                layer_id, pygame, min_depth=player_depth
            )
            if surface is None:
                continue

            # Viewport clip in world-space: what portion of the WorldSurface is visible?
            src_rect = pygame.Rect(int(-cam_offset.x), int(-cam_offset.y), screen_w, screen_h)
            # Clamp to surface bounds — avoid blit errors when camera near map edge
            surf_w, surf_h = surface.get_size()
            src_rect = src_rect.clip(pygame.Rect(0, 0, surf_w, surf_h))
            if src_rect.width <= 0 or src_rect.height <= 0:
                continue

            dest_x = int(cam_offset.x) + src_rect.x
            dest_y = int(cam_offset.y) + src_rect.y
            self.game.screen.blit(surface, (dest_x, dest_y), src_rect)

    def _build_screen_occluding_rects(
        self,
        cam_offset: pygame.Vector2,
        player_depth: int,
        occluding_rects: OccludingRect,
    ) -> None:
        """P-001: Build screen-space occluding rects from the world-space cache.

        Uses the pre-filtered self._frame_visible_fg_tiles if present (optimized path).
        Otherwise falls back to iterating over the full map cache (compatibility path).
        """
        cam_x = int(cam_offset.x)
        cam_y = int(cam_offset.y)
        tile_size = self.game.tile_size

        visible_tiles = getattr(self, "_frame_visible_fg_tiles", None)
        pool = getattr(self, "_rect_pool", None)
        if visible_tiles is not None and pool is not None:
            pool_len = len(pool)
            for i, (wx, wy, depth, img, _occ) in enumerate(visible_tiles):
                if i < pool_len:
                    rect = pool[i]
                    rect.x = wx + cam_x
                    rect.y = wy + cam_y
                    rect.width = tile_size
                    rect.height = tile_size
                else:
                    rect = pygame.Rect(wx + cam_x, wy + cam_y, tile_size, tile_size)
                    pool.append(rect)
                occluding_rects.append((rect, depth, img))
        else:
            # Fallback path for unit tests calling this method directly
            vp = self._viewport_world
            for wx, wy, depth, img, _occ in self.game.map_manager._fg_occlusion_world:
                if depth <= player_depth:
                    continue
                if wx + tile_size <= vp.left or wx >= vp.right:
                    continue
                if wy + tile_size <= vp.top or wy >= vp.bottom:
                    continue
                occluding_rects.append(
                    (
                        pygame.Rect(wx + cam_x, wy + cam_y, tile_size, tile_size),
                        depth,
                        img,
                    )
                )

    def _blit_occluded_tiles_near_player(  # noqa: C901
        self,
        cam_offset: pygame.Vector2,
        player_screen_rect: pygame.Rect,
        player_depth: int,
    ) -> None:
        """P-001: Blit semi-transparent occluded tile images only for tiles adjacent to the player.

        Uses the pre-filtered self._frame_visible_fg_tiles if present (optimized path).
        Otherwise falls back to iterating over the full map cache (compatibility path).
        """
        cam_x = int(cam_offset.x)
        cam_y = int(cam_offset.y)
        tile_size = self.game.tile_size
        screen = self.game.screen

        visible_tiles = getattr(self, "_frame_visible_fg_tiles", None)
        grid = getattr(self.game.map_manager, "_fg_occlusion_grid", None)
        if visible_tiles is not None and isinstance(grid, dict):
            # Optimized path: scan only the 3x3 area around player
            player_col = int(self.game.player.rect.centerx // tile_size)
            player_row = int(self.game.player.rect.centery // tile_size)

            for r in range(player_row - 1, player_row + 2):
                for c in range(player_col - 1, player_col + 2):
                    tile_info = grid.get((c, r))
                    if tile_info:
                        depth, img, occ_img = tile_info
                        if depth > player_depth:
                            self._tile_rect.x = c * tile_size + cam_x
                            self._tile_rect.y = r * tile_size + cam_y
                            if player_screen_rect.colliderect(self._tile_rect):
                                screen.blit(
                                    occ_img if occ_img is not None else img,
                                    (self._tile_rect.x, self._tile_rect.y),
                                )
        else:
            # Fallback compatibility path for unit tests
            vp = self._viewport_world
            for wx, wy, depth, img, occ_img in self.game.map_manager._fg_occlusion_world:
                if depth <= player_depth:
                    continue
                if wx + tile_size <= vp.left or wx >= vp.right:
                    continue
                if wy + tile_size <= vp.top or wy >= vp.bottom:
                    continue
                self._tile_rect.x = wx + cam_x
                self._tile_rect.y = wy + cam_y
                if player_screen_rect.colliderect(self._tile_rect):
                    screen.blit(
                        occ_img if occ_img is not None else img,
                        (self._tile_rect.x, self._tile_rect.y),
                    )

    def _draw_static_foreground_tiles(
        self,
        cam_offset: pygame.Vector2,
        walk_active: bool,
        player_screen_rect: pygame.Rect,
        player_depth: int,
        occluding_rects: OccludingRect,
    ) -> BlitSequence:
        """P-001: Static foreground tile rendering — delegates to 3 focused sub-methods.

        Optimized pipeline:
          1. _blit_foreground_surface      — single WorldSurface blit per layer
          2. Compile viewport-culled list  — O(N_fg_world) list comprehension
          3. _build_screen_occluding_rects — O(visible_fg) translation
          4. _blit_occluded_tiles_near_player — sparse blit only near player
        """
        self._blit_foreground_surface(cam_offset, player_depth)

        tile_size = self.game.tile_size
        vp = self._viewport_world
        mm = self.game.map_manager
        grid = getattr(mm, "_fg_occlusion_grid", None)

        if isinstance(grid, dict):
            width = getattr(mm, "width", 0)
            height = getattr(mm, "height", 0)
            if not isinstance(width, int):
                width = int(math.ceil(vp.right / tile_size))
            if not isinstance(height, int):
                height = int(math.ceil(vp.bottom / tile_size))

            start_col = max(0, int(vp.left // tile_size))
            end_col = min(width, int(math.ceil(vp.right / tile_size)))
            start_row = max(0, int(vp.top // tile_size))
            end_row = min(height, int(math.ceil(vp.bottom / tile_size)))

            self._frame_visible_fg_tiles = []
            for y in range(start_row, end_row):
                wy = y * tile_size
                for x in range(start_col, end_col):
                    tile_info = grid.get((x, y))
                    if tile_info:
                        depth, img, occ_img = tile_info
                        if depth > player_depth:
                            self._frame_visible_fg_tiles.append(
                                (x * tile_size, wy, depth, img, occ_img)
                            )
        else:
            # Fallback path for unit tests using mocks
            self._frame_visible_fg_tiles = [
                (wx, wy, depth, img, occ_img)
                for wx, wy, depth, img, occ_img in getattr(mm, "_fg_occlusion_world", [])
                if depth > player_depth
                and wx + tile_size > vp.left
                and wx < vp.right
                and wy + tile_size > vp.top
                and wy < vp.bottom
            ]

        self._build_screen_occluding_rects(cam_offset, player_depth, occluding_rects)
        if not walk_active:
            self._blit_occluded_tiles_near_player(cam_offset, player_screen_rect, player_depth)

        self._frame_visible_fg_tiles = None
        return []

    def _draw_animated_foreground_tiles(
        self,
        cam_offset: pygame.Vector2,
        player_depth: int,
        occluding_rects: OccludingRect,
    ) -> None:
        """Process and blit animated foreground tiles, collecting occluding rects."""
        if not (self.game.anim_map_manager and self._frame_anim_all):
            return
        anim_fg_blits = []
        tile_size = self.game.tile_size
        for px, py, tile_id, depth in self._frame_anim_all:
            if depth > player_depth:
                img = self.game.anim_map_manager.get_current_frame_image(tile_id)
                if img:
                    screen_pos = (px + cam_offset.x, py + cam_offset.y)
                    anim_fg_blits.append((img, screen_pos))
                    # Current frame passed in tuple so pixel-perfect mask is resolved
                    # per-frame by AssetManager (each frame Surface has a unique id).
                    occluding_rects.append(
                        (
                            pygame.Rect(screen_pos, (tile_size, tile_size)),
                            depth,
                            img,
                        )
                    )
        if anim_fg_blits:
            self.game.screen.fblits(anim_fg_blits)

    def draw_foreground(self) -> OccludingRect:
        """Draw foreground tiles: all tiles from layers with order > player depth,
        plus tiles with depth > player depth from mixed-depth layers.
        Applies occluded image when the player overlaps a depth > player.depth tile.
        Returns:
            list[tuple[pygame.Rect, int]]: screen-space rects and depths of all active
            occluding tiles (depth > player.depth). Empty list if none.

        Note: During intra-map scripted walk (_intra_walk_target is set), occlusion is
        skipped entirely — the player is invisible, so making tiles transparent would
        create a visible artifact (tiles flickering alpha as the player rect moves).
        """
        occluding_rects: OccludingRect = []
        cam_offset = self.game.visible_sprites.offset
        self._viewport_world.update(
            -cam_offset.x,
            -cam_offset.y,
            self._screen_rect.width,
            self._screen_rect.height,
        )

        # During scripted walk the player is hidden — skip occlusion to prevent
        # foreground tiles from flickering alpha as the invisible player rect moves.
        walk_active = getattr(self.game, "_intra_walk_target", None) is not None

        # Use physical hitbox for occlusion detection — visual rect extends upward and
        # would produce lag when the player exits a tile area (top of sprite still overlaps)
        player_screen_rect = self.game.player.rect.move(cam_offset.x, cam_offset.y)
        player_depth = self.game.player.depth

        normal_blits = self._draw_static_foreground_tiles(
            cam_offset, walk_active, player_screen_rect, player_depth, occluding_rects
        )

        if normal_blits:
            self.game.screen.fblits(normal_blits)

        self._draw_animated_foreground_tiles(cam_offset, player_depth, occluding_rects)

        return occluding_rects

    def draw_hud(self):
        """Draw time and season HUD overlay (top-right, fixed to screen)."""
        self.game.hud.draw(self.game.screen)

    def _update_animated_tile_cache(self, cam_offset: pygame.Vector2) -> None:
        """Pre-compute animated tile cache once per frame for the current viewport."""
        self._viewport_world.update(
            -cam_offset.x,
            -cam_offset.y,
            self._screen_rect.width,
            self._screen_rect.height,
        )
        self._frame_anim_all = []
        self._frame_anim_by_layer = {lid: [] for lid in self.game.map_manager.layer_order}
        if self.game.anim_map_manager:
            tile_size = self.game.tile_size
            for px, py, tile_id, depth in self.game.map_manager.get_visible_animated_chunks(
                self._viewport_world
            ):
                self._frame_anim_all.append((px, py, tile_id, depth))
                # Resolve layer membership from pre-computed map (O(1))
                col = px // tile_size
                row = py // tile_size
                lid = self.game.map_manager._anim_tile_layer_map.get((col, row))
                if lid is not None:
                    self._frame_anim_by_layer[lid].append((px, py, tile_id, depth))

    def _compute_effective_night_alpha(self) -> int:
        """Compute the darkness overlay alpha for the current map's lighting mode.

        Spec: lighting-system.md § 8.3
          outdoor    : time_system.night_alpha (unchanged behaviour)
          indoor     : min(255, ambient + int(night_alpha * INDOOR_ATTENUATION))
          underground: ambient_dark_alpha (fixed, no time dependency)
        Unknown mode falls back to outdoor via getattr default.
        """
        mode = getattr(self.game, "_map_lighting_mode", "outdoor")
        ambient = getattr(self.game, "_map_ambient_dark_alpha", 0)
        night_alpha = self.game.time_system.night_alpha

        if mode == "underground":
            return ambient
        if mode == "indoor":
            return min(255, ambient + int(night_alpha * INDOOR_ATTENUATION))
        # outdoor (default)
        return night_alpha

    def _render_lighting_and_effects(
        self, night_alpha: float, window_positions: list, cam_offset: pygame.Vector2
    ) -> None:
        """Render additive window beams, dynamic lighting, and active interactive effects."""
        # Window beams require a sky source — skip for underground maps (spec § 8.4).
        if getattr(self.game, "_map_lighting_mode", "outdoor") != "underground":
            self.game.lighting_manager.draw_additive_window_beams(
                self.game.screen, window_positions, cam_offset
            )

        # Render dynamic lighting on darkness overlay
        if night_alpha > 0:
            active_torches = [
                obj
                for obj in self.game.interactives
                if getattr(obj, "is_on", False) and getattr(obj, "halo_size", 0) > 0
            ]

            overlay = self.game.lighting_manager.create_overlay(
                window_positions, active_torches, cam_offset, alpha_override=night_alpha
            )
            self.game.screen.blit(overlay, (0, 0))

        for obj in self.game.interactives:
            if hasattr(obj, "draw_effects"):
                obj.draw_effects(self.game.screen, cam_offset, night_alpha)

    def _render_ui_overlays(self, cam_offset: pygame.Vector2) -> None:
        """Render fixed HUD overlay, Emotes, Dialogue Managers, Speech bubbles, and UI views."""
        if not self.game.inventory_ui.is_open:
            self.draw_hud()

        # Draw Emotes (after HUD, with camera offset)
        for sprite in self.game.emote_group:
            screen_pos = (sprite.rect.x + cam_offset.x, sprite.rect.y + cam_offset.y)
            self.game.screen.blit(sprite.image, screen_pos)

        if self.game.dialogue_manager.is_active:
            self.game.dialogue_manager.draw(self.game.screen)

        # NPC speech bubble — drawn above NPC in screen-space
        if getattr(self.game, "_npc_bubble", None) is not None:
            npc = self.game._npc_bubble["npc"]
            # Build a screen-space rect from the NPC world rect
            npc_screen_rect = npc.rect.move(cam_offset.x, cam_offset.y)
            self.game.speech_bubble.draw(
                self.game.screen,
                npc_screen_rect,
                self.game._npc_bubble["text"],
                page=self.game._npc_bubble["page"],
                speaker_name=getattr(npc, "name", "") or npc.element_id.capitalize(),
            )

        if self.game.inventory_ui.is_open:
            self.game.inventory_ui.draw(self.game.screen)
        if self.game.chest_ui.is_open:
            self.game.chest_ui.draw(self.game.screen)

    def draw_scene(self):
        """A helper representing the entire scene rendering logic."""
        self.game.screen.fill(Settings.COLOR_BG)
        self.game.visible_sprites.calculate_offset(self.game.player)
        cam_offset = self.game.visible_sprites.offset

        # F3: Pre-compute animated tile cache once per frame for the current viewport.
        # draw_background() reads _frame_anim_by_layer; draw_foreground() reads _frame_anim_all.
        # Order: calculate_offset() → update _viewport_world → populate caches → draw passes.
        self._update_animated_tile_cache(cam_offset)

        self.draw_background()
        self.game.visible_sprites.custom_draw(
            self.game.screen, max_depth=self.game.player.depth - 1
        )

        occluding_rects = self.draw_foreground()

        # Pass 3b: Partial occlusion — replace each sprite image with a composite where only
        # the zone behind a foreground tile is semi-transparent.
        # Pass 3c: Grass wading — compose wading pixels into each sprite image BEFORE draw.
        # Both passes use the same pre-blit image swap pattern so rendering order (Y-sort)
        # governs visibility naturally — no wading bleed onto adjacent sprites.
        # saved_images tracks the PRE-OCCLUSION originals. _apply_grass_wading_to_images
        # receives it so that wading stacks on the occlusion composite while saving the
        # true original (pre-occlusion), giving a single restore step.
        saved_images = self.occlusion_renderer.apply_partial_occlusion(occluding_rects)
        wading_saved = self.wading_renderer.apply_grass_wading_to_images(cam_offset, saved_images)

        self.game.visible_sprites.custom_draw(self.game.screen, min_depth=self.game.player.depth)

        # Restore all sprites to their original images in one pass.
        # saved_images already contains pre-occlusion originals; wading_saved contains the
        # originals for sprites that only needed wading (not occlusion).
        for sprite, original_image in saved_images.items():
            sprite.image = original_image
        for sprite, original_image in wading_saved.items():
            sprite.image = original_image

        night_alpha = self._compute_effective_night_alpha()
        window_positions = self.game.map_manager.get_window_positions()

        self._render_lighting_and_effects(night_alpha, window_positions, cam_offset)
        self._render_ui_overlays(cam_offset)

    def reset_render_caches(self) -> None:
        """Invalidate all render caches on map change.

        Called by game.py in transition_map(), after _load_map().
        """
        self.occlusion_renderer.reset_cache()
        self.wading_renderer.reset_cache()
