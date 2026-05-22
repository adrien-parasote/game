import pygame

from src.config import Settings


class RenderManager:
    """Handles all visual rendering logic for the game scene, decoupling it from the main event loop."""

    def __init__(self, game):
        self.game = game
        # Pre-allocated reusable Rects — updated in-place to avoid per-frame allocations
        self._tile_rect = pygame.Rect(0, 0, game.tile_size, game.tile_size)
        self._screen_rect = pygame.Rect(0, 0, game.screen.get_width(), game.screen.get_height())
        self._viewport_world = pygame.Rect(0, 0, 0, 0)

    def draw_background(self):
        """Draw tiles with depth <= player depth (behind player).
        Static and animated tiles are rendered per-layer in order so that
        a higher-order layer always appears on top regardless of animation.
        """
        cam_offset = self.game.visible_sprites.offset

        if self.game.anim_map_manager:
            self._viewport_world.update(
                -cam_offset.x, -cam_offset.y,
                self._screen_rect.width, self._screen_rect.height,
            )

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

            # 2. Animated tiles for this layer (drawn on top of static)
            if self.game.anim_map_manager:
                anim_blits = []
                for px, py, tile_id, depth in self.game.map_manager.get_visible_animated_chunks(
                    self._viewport_world, layer_id=layer_id
                ):
                    if depth <= self.game.player.depth:
                        img = self.game.anim_map_manager.get_current_frame_image(tile_id)
                        if img:
                            anim_blits.append((img, (px + cam_offset.x, py + cam_offset.y)))
                if anim_blits:
                    self.game.screen.fblits(anim_blits)

    def draw_foreground(self) -> list[tuple[pygame.Rect, int]]:
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
        occluding_rects: list[tuple[pygame.Rect, int]] = []
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

        # Split tiles: occluded tiles (need per-tile colliderect) vs normal tiles (batch)
        normal_blits = []
        player_depth = self.game.player.depth
        tiles = self.game.map_manager.tiles
        screen = self.game.screen

        for px, py, tile_id, depth in self.game.map_manager.get_visible_chunks(
            self._viewport_world, min_depth=player_depth
        ):
            tile_data = tiles[tile_id]
            screen_pos = (px + cam_offset.x, py + cam_offset.y)

            # Collect rect for ALL tiles depth > player — NPCs may be behind tiles
            # that the player doesn't touch, so we can't filter by player collision here.
            if depth > player_depth:
                occluding_rects.append((
                    pygame.Rect(screen_pos, (self.game.tile_size, self.game.tile_size)),
                    depth,
                ))

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

        if normal_blits:
            screen.fblits(normal_blits)

        # Draw animated foreground tiles + collect their rects if depth > player
        if self.game.anim_map_manager:
            anim_fg_blits = []
            for px, py, tile_id, depth in self.game.map_manager.get_visible_animated_chunks(self._viewport_world):
                if depth > player_depth:
                    img = self.game.anim_map_manager.get_current_frame_image(tile_id)
                    if img:
                        screen_pos = (px + cam_offset.x, py + cam_offset.y)
                        anim_fg_blits.append((img, screen_pos))
                        # Also add to occluding list — inert today (no anim tile has depth>1)
                        # but will fire automatically when animated foreground tiles are created.
                        occluding_rects.append((
                            pygame.Rect(screen_pos, (self.game.tile_size, self.game.tile_size)),
                            depth,
                        ))
            if anim_fg_blits:
                screen.fblits(anim_fg_blits)

        return occluding_rects



    def draw_hud(self):
        """Draw time and season HUD overlay (top-right, fixed to screen)."""
        self.game.hud.draw(self.game.screen)

    def _apply_partial_occlusion(
        self, occluding_rects: list[tuple[pygame.Rect, int]]
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
            return {}

        cam_offset = self.game.visible_sprites.offset
        saved_images: dict[object, pygame.Surface] = {}
        player_depth = self.game.player.depth

        for sprite in self.game.visible_sprites.get_sorted_sprites():
            if not sprite.image or not sprite.rect:
                continue
            # Only pass-3b sprites (depth >= player.depth) are rendered behind foreground tiles.
            sprite_depth = getattr(sprite, "depth", 1)
            if sprite_depth < player_depth:
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
                sprite_screen_rect.clip(occ_rect)
                for occ_rect, tile_depth in occluding_rects
                if tile_depth > sprite_depth and sprite_screen_rect.colliderect(occ_rect)
            ]
            if not intersections:
                continue  # sprite not occluded — skip

            # Build composite: start with full opaque copy, then paint occluded zones in alpha.
            composite = pygame.Surface(visual_rect.size, pygame.SRCALPHA)
            composite.blit(sprite.image, (0, 0))  # full opaque copy

            for isect in intersections:
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

                # Clear the destination zone before blitting the alpha version.
                # Without this, the existing opaque pixels would survive the blit.
                composite.fill((0, 0, 0, 0), local_rect)

                # Blit the source zone at reduced alpha.
                alpha_surface = pygame.Surface(local_rect.size, pygame.SRCALPHA)
                alpha_surface.blit(sprite.image, (0, 0), local_rect)
                alpha_surface.set_alpha(Settings.OCCLUSION_ALPHA)
                composite.blit(alpha_surface, local_rect.topleft)

            # Swap: save original, install composite. Caller restores after custom_draw.
            saved_images[sprite] = sprite.image
            sprite.image = composite

        return saved_images

    def draw_scene(self):
        """A helper representing the entire scene rendering logic."""
        self.game.screen.fill(Settings.COLOR_BG)
        self.game.visible_sprites.calculate_offset(self.game.player)
        self.draw_background()
        self.game.visible_sprites.custom_draw(self.game.screen, max_depth=self.game.player.depth - 1)

        occluding_rects = self.draw_foreground()

        # Partial occlusion: replace each sprite's image with a composite where only
        # the zone behind a foreground tile is semi-transparent. Guarded by walk check:
        # during scripted walk the player is already invisible (_player_transparent),
        # so _apply_partial_occlusion must not be called (UT-011 / IT-003).
        walk_active = getattr(self.game, "_intra_walk_target", None) is not None
        saved_images: dict[object, pygame.Surface] = {}
        if not walk_active:
            saved_images = self._apply_partial_occlusion(occluding_rects)

        self.game.visible_sprites.custom_draw(self.game.screen, min_depth=self.game.player.depth)

        # Restore original sprite images immediately after rendering.
        for sprite, original_image in saved_images.items():
            sprite.image = original_image

        night_alpha = self.game.time_system.night_alpha
        window_positions = self.game.map_manager.get_window_positions()

        # Render additive window beams (always visible during day and night)
        self.game.lighting_manager.draw_additive_window_beams(
            self.game.screen, window_positions, self.game.visible_sprites.offset
        )

        # Render dynamic lighting on darkness overlay
        if night_alpha > 0:
            active_torches = [
                obj
                for obj in self.game.interactives
                if getattr(obj, "is_on", False) and getattr(obj, "halo_size", 0) > 0
            ]

            overlay = self.game.lighting_manager.create_overlay(
                window_positions, active_torches, self.game.visible_sprites.offset
            )
            self.game.screen.blit(overlay, (0, 0))

        cam_offset = self.game.visible_sprites.offset
        for obj in self.game.interactives:
            if hasattr(obj, "draw_effects"):
                obj.draw_effects(self.game.screen, cam_offset, night_alpha)

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
            cam = self.game.visible_sprites.offset
            # Build a screen-space rect from the NPC world rect
            npc_screen_rect = npc.rect.move(cam.x, cam.y)
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
