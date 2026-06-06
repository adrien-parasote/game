import pygame
from src.config import Settings
from src.engine.asset_manager import AssetManager
from src.engine.lighting_constants import INDOOR_ATTENUATION

# Python 3.12 type aliases — replace inline annotations used across multiple methods
type BlitSequence = list[tuple[pygame.Surface, tuple[int, int]]]
type OccludingRect = list[tuple[pygame.Rect, int, pygame.Surface | None]]


class RenderManager:
    """Handles all visual rendering logic for the game scene, decoupling it from the main event loop."""

    def __init__(self, game):
        self.game = game
        # Pre-allocated reusable Rects — updated in-place to avoid per-frame allocations
        self._tile_rect = pygame.Rect(0, 0, game.tile_size, game.tile_size)
        self._screen_rect = pygame.Rect(0, 0, game.screen.get_width(), game.screen.get_height())
        self._viewport_world = pygame.Rect(0, 0, 0, 0)
        # F4: Pre-allocated SRCALPHA surface pool — reused every frame, cleared with fill()
        # Pool for composite occlusion: distinct surface per occluded sprite, avoids reference sharing
        self._occlusion_pool: list[pygame.Surface] = []
        # Alpha surface for crop blitting (sequentially used — single instance is safe)
        self._alpha_surf: pygame.Surface | None = None
        # Grass wading surface (sequentially blitted and drawn immediately)
        self._wading_surf: pygame.Surface | None = None
        # F3: Pre-computed animated tile caches — populated once per frame in draw_scene()
        self._frame_anim_all: list[tuple[int, int, int, int]] = []
        self._frame_anim_by_layer: dict[int, list[tuple[int, int, int, int]]] = {}

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

    def _draw_static_foreground_tiles(
        self,
        cam_offset: pygame.Vector2,
        walk_active: bool,
        player_screen_rect: pygame.Rect,
        player_depth: int,
        occluding_rects: OccludingRect,
    ) -> BlitSequence:
        """Process and collect static foreground tiles, updating occluding rects."""
        normal_blits = []
        tiles = self.game.map_manager.tiles
        screen = self.game.screen
        tile_size = self.game.tile_size

        for px, py, tile_id, depth in self.game.map_manager.get_visible_chunks(
            self._viewport_world, min_depth=player_depth
        ):
            tile_data = tiles[tile_id]
            screen_pos = (px + cam_offset.x, py + cam_offset.y)

            # Collect rect for ALL tiles depth > player — NPCs may be behind tiles
            # that the player doesn't touch, so we can't filter by player collision here.
            if depth > player_depth:
                occluding_rects.append(
                    (
                        pygame.Rect(screen_pos, (tile_size, tile_size)),
                        depth,
                        tile_data.image,  # pixel-perfect mask resolved from tile image
                    )
                )

            if not walk_active and depth > player_depth:
                # Depth-occlusion: use semi-transparent image when player overlaps
                self._tile_rect.topleft = screen_pos
                if player_screen_rect.colliderect(self._tile_rect):
                    screen.blit(tile_data.occluded_image or tile_data.image, screen_pos)
                else:
                    normal_blits.append((tile_data.image, screen_pos))
            else:
                # Walk active OR foreground-order layer tile with depth <= player: no occlusion
                normal_blits.append((tile_data.image, screen_pos))
        return normal_blits

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

    def _create_composite_occlusion_surface(
        self,
        sprite,
        sprite_screen_rect: pygame.Rect,
        intersections: list[tuple[pygame.Rect, pygame.Rect, pygame.Surface | None]],
        used_composites: int,
    ) -> tuple[pygame.Surface, int]:
        """Creates or reuses a composite surface from the pool for a single sprite.

        For each intersection zone:
        - If the tile image has a pixel-perfect mask (partial tile): apply BLEND_RGBA_MULT
          so only pixels covered by opaque tile pixels are semi-transparent.
        - If no mask (fully opaque tile or tile_img is None): classic uniform set_alpha().
        """
        visual_size = sprite.image.get_size()
        # F4: Reuse or allocate a distinct surface from the pool for this specific sprite
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
        composite.blit(sprite.image, (0, 0))  # full opaque copy

        for isect, occ_rect, tile_img in intersections:
            # pygame.Rect.clip() can return a zero-size rect for adjacent tiles.
            if isect.width <= 0 or isect.height <= 0:
                continue

            # Convert screen-space intersection to local composite coordinates.
            local_rect = pygame.Rect(
                isect.x - sprite_screen_rect.x,
                isect.y - sprite_screen_rect.y,
                isect.width,
                isect.height,
            )

            # Resolve pixel-perfect mask from AssetManager (cached by id(tile_img)).
            mask = AssetManager().get_occlusion_mask(tile_img) if tile_img is not None else None

            if mask is None:
                # Fully opaque tile (or no tile image): classic uniform alpha.
                # Clear zone then reblit sprite at OCCLUSION_ALPHA — unchanged from prior approach.
                composite.fill((0, 0, 0, 0), local_rect)
                # F4: Sequentially reuse _alpha_surf — resized only when intersection changes
                if self._alpha_surf is None or self._alpha_surf.get_size() != local_rect.size:
                    self._alpha_surf = pygame.Surface(local_rect.size, pygame.SRCALPHA)
                self._alpha_surf.fill((0, 0, 0, 0))
                self._alpha_surf.blit(sprite.image, (0, 0), local_rect)
                self._alpha_surf.set_alpha(Settings.OCCLUSION_ALPHA)
                composite.blit(self._alpha_surf, local_rect.topleft)
            else:
                # Pixel-perfect: apply BLEND_RGBA_MULT DIRECTLY on the composite zone.
                # composite already holds the opaque sprite pixels (A=255 for body).
                # We blit the mask crop into _alpha_surf (just as a cropping helper),
                # then BLEND_RGBA_MULT onto composite — no clear, no set_alpha juggling.
                #   composite.A = sprite.A x mask.A / 255
                #   → opaque tile pixel  (mask.A=OCCLUSION_ALPHA): sprite dims to OCCLUSION_ALPHA
                #   → transparent tile pixel (mask.A=255):          sprite stays at 255
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

    def _apply_partial_occlusion(
        self, occluding_rects: OccludingRect
    ) -> dict[object, pygame.Surface]:
        """For each visible sprite intersecting an occluding tile, replace sprite.image
        with a composite surface where only the overlapping zone is semi-transparent.

        Must be called BEFORE custom_draw() so pygame renders composites in depth order.
        Returns a dict {sprite: original_image} for the caller to restore after drawing.

        Args:
            occluding_rects: list of (screen-space Rect, depth) tuples from draw_foreground().

        Returns:
            dict mapping each modified sprite to its original image surface.
        """
        if not occluding_rects:
            return dict()

        cam_offset = self.game.visible_sprites.offset
        saved_images: dict[object, pygame.Surface] = {}
        player_depth = self.game.player.depth
        walk_active = getattr(self.game, "_intra_walk_target", None) is not None
        used_composites = 0  # F4: track pool index to avoid reference sharing between sprites

        for sprite in self.game.visible_sprites.get_sorted_sprites():
            if not sprite.image or not sprite.rect:
                continue
            # Only pass-3b sprites (depth >= player.depth) are rendered behind foreground tiles.
            sprite_depth = getattr(sprite, "depth", 1)
            if sprite_depth < player_depth:
                continue
            # During scripted walk the player is invisible (_player_transparent).
            # Skip the player sprite only — NPCs must still be occluded (UT-011 / IT-003).
            if walk_active and sprite == self.game.player:
                continue

            # Build the visual screen-space rect — identical formula to custom_draw().
            # Aligns sprite image bottom-right to hitbox bottom-right then applies camera offset.
            visual_rect = sprite.image.get_rect(bottomright=sprite.rect.bottomright)
            sprite_screen_rect = pygame.Rect(
                (visual_rect.left + cam_offset.x, visual_rect.top + cam_offset.y),
                visual_rect.size,
            )

            # Collect intersections with tiles strictly above this sprite's depth.
            # tile_depth > sprite_depth ensures same-depth tiles don't occlude.
            intersections = [
                (sprite_screen_rect.clip(occ_rect), occ_rect, tile_img)
                for occ_rect, tile_depth, tile_img in occluding_rects
                if tile_depth > sprite_depth and sprite_screen_rect.colliderect(occ_rect)
            ]
            if not intersections:
                continue  # sprite not occluded — skip

            composite, used_composites = self._create_composite_occlusion_surface(
                sprite, sprite_screen_rect, intersections, used_composites
            )

            # Swap: save original, install composite. Caller restores after custom_draw.
            saved_images[sprite] = sprite.image
            sprite.image = composite

        return saved_images

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
                # Resolve layer membership by checking tile_id at grid coordinate
                col = px // tile_size
                row = py // tile_size
                for lid in self.game.map_manager.layer_order:
                    if lid in self.game.map_manager.layers:
                        layer_data = self.game.map_manager.layers[lid]
                        if 0 <= row < len(layer_data) and 0 <= col < len(layer_data[row]):  # noqa: SIM102
                            if layer_data[row][col] == tile_id:
                                self._frame_anim_by_layer[lid].append((px, py, tile_id, depth))
                                break

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
        saved_images = self._apply_partial_occlusion(occluding_rects)
        wading_saved = self._apply_grass_wading_to_images(cam_offset, saved_images)

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
        """Helper to blit overlapping grass tile segments onto the wading surface."""
        for col in range(col_start, col_end + 1):
            for row in range(row_start, row_end + 1):
                tile_world_x = col * tile_size
                tile_world_y = row * tile_size
                tile_screen_x = tile_world_x + cam_offset.x
                tile_screen_y = tile_world_y + cam_offset.y

                # Intersection between this tile and the wading screen zone
                isect_left = max(wading_screen_left, tile_screen_x)
                isect_top = max(wading_screen_top, tile_screen_y)
                isect_right = min(wading_screen_right, tile_screen_x + tile_size)
                isect_bottom = min(wading_screen_bottom, tile_screen_y + tile_size)
                isect_w = isect_right - isect_left
                isect_h = isect_bottom - isect_top
                if isect_w <= 0 or isect_h <= 0:
                    continue

                # Crop coordinates on the grass tile image
                crop_x = int(isect_left - tile_screen_x)
                crop_y = int(isect_top - tile_screen_y)
                grass_crop = pygame.Rect(crop_x, crop_y, int(isect_w), int(isect_h))

                # Destination on the wading surface (local to the wading zone)
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
        """Build a composite of the sprite image with grass wading applied to its foot zone.

        Returns a new SRCALPHA surface with the wading pixels composited into the bottom
        wading_depth rows, or None if the sprite is not standing on a grass tile.

        The composite is built in sprite-local coordinates so that the rendering order
        (Y-sort via custom_draw) governs visibility — no screen-space bleed onto adjacent
        sprites that happen to occupy the same screen area.
        """
        # Probe grass at foot position: bottom center of hitbox, 2px up to avoid edge miss
        foot_world_x = sprite.rect.centerx
        foot_world_y = sprite.rect.bottom - 2

        grass_img = self.game.map_manager.get_grass_tile_image_at(foot_world_x, foot_world_y)
        if not isinstance(grass_img, pygame.Surface):
            return None  # Not on grass — nothing to do

        visual_size = sprite.image.get_size()
        img_w, img_h = visual_size

        # Wading zone in LOCAL sprite coordinates (bottom wading_depth rows).
        local_wading_top = max(0, img_h - wading_depth)
        local_wading_h = img_h - local_wading_top
        if local_wading_h <= 0:
            return None

        # Build the composite: full opaque sprite image + wading overlay at the bottom.
        composite = pygame.Surface(visual_size, pygame.SRCALPHA)
        composite.blit(sprite.image, (0, 0))

        # Determine screen-space position of the sprite's visual rect to look up
        # which grass tile pixels align with the wading zone.
        visual_rect = sprite.image.get_rect(bottomright=sprite.rect.bottomright)
        sprite_screen_left = visual_rect.left + cam_offset.x
        sprite_screen_top = visual_rect.top + cam_offset.y

        # Wading zone in screen space (for tile lookup only)
        wading_screen_top = sprite_screen_top + local_wading_top
        wading_screen_left = sprite_screen_left
        wading_screen_right = sprite_screen_left + img_w
        wading_screen_bottom = sprite_screen_top + img_h

        col_start = int((wading_screen_left - cam_offset.x) // tile_size)
        col_end = int((wading_screen_right - cam_offset.x - 1) // tile_size)
        row_start = int((wading_screen_top - cam_offset.y) // tile_size)
        row_end = int((wading_screen_bottom - cam_offset.y - 1) // tile_size)

        # F4: Reuse _wading_surf — resize only if wading zone changed size
        wading_size = (img_w, local_wading_h)
        if self._wading_surf is None or self._wading_surf.get_size() != wading_size:
            self._wading_surf = pygame.Surface(wading_size, pygame.SRCALPHA)
        self._wading_surf.fill((0, 0, 0, 0))
        wading_surf = self._wading_surf

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

    def _apply_grass_wading_to_images(
        self,
        cam_offset: pygame.Vector2 | None = None,
        pre_occlusion_originals: dict[object, pygame.Surface] | None = None,
    ) -> dict[object, pygame.Surface]:
        """Pass 3c: compose grass wading pixels into each sprite's image BEFORE custom_draw.

        Works like _apply_partial_occlusion: replaces sprite.image with a composite that
        has the wading pixels baked in, returns {sprite: pre-wading original} for restoration.

        If pre_occlusion_originals is provided (from _apply_partial_occlusion), sprites in
        that dict have their wading applied to the occlusion composite; their restoration
        entry is the PRE-OCCLUSION original so a single restore pass suffices.

        By modifying the image before the draw call (rather than blitting to screen after),
        the Y-sort rendering order guarantees that no sprite's wading zone can bleed over
        another sprite drawn later in the same pass.

        Preconditions:
        - map_manager must not be None (guarded at method entry)
        - Must be called BEFORE custom_draw(min_depth=player.depth).
        - walk_active guard skips the player sprite only (NPCs always processed).
        """
        if not self.game.map_manager:
            empty_res: dict[object, pygame.Surface] = {}
            return empty_res

        if cam_offset is None:
            cam_offset = self.game.visible_sprites.offset
        assert cam_offset is not None
        pre_occ = pre_occlusion_originals or {}
        tile_size = self.game.tile_size
        wading_depth = Settings.GRASS_WADING_DEPTH
        wading_alpha = Settings.GRASS_WADING_ALPHA
        player_depth = self.game.player.depth
        walk_active = getattr(self.game, "_intra_walk_target", None) is not None
        # Only sprites NOT already in pre_occ need a restore entry here.
        # Sprites in pre_occ are restored by the caller's saved_images loop.
        wading_only_originals: dict[object, pygame.Surface] = {}

        for sprite in self.game.visible_sprites.get_sorted_sprites():
            if not sprite.image or not sprite.rect:
                continue
            # Skip Pass-2 sprites (they are already below the grass layer)
            if getattr(sprite, "depth", 1) < player_depth:
                continue
            # During scripted walk, skip the player only (NPCs still get wading)
            if walk_active and sprite == self.game.player:
                continue

            composite = self._build_wading_composite(
                sprite, cam_offset, tile_size, wading_depth, wading_alpha
            )
            if composite is not None:
                if sprite not in pre_occ:
                    # Save original before wading so the caller can restore it.
                    wading_only_originals[sprite] = sprite.image
                # Stack wading on whatever image is current (may be occlusion composite).
                sprite.image = composite

        return wading_only_originals
