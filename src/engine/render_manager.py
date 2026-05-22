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

    def draw_foreground(self) -> bool:
        """Draw foreground tiles: all tiles from layers with order > player depth,
        plus tiles with depth > player depth from mixed-depth layers.
        Applies occluded image when the player overlaps a depth > player.depth tile.
        Returns:
            bool: True if any tile is actively occluding the player, False otherwise.
        """
        player_occluded = False
        cam_offset = self.game.visible_sprites.offset
        self._viewport_world.update(
            -cam_offset.x,
            -cam_offset.y,
            self._screen_rect.width,
            self._screen_rect.height,
        )

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

            if depth > player_depth:
                # Depth-occlusion: use semi-transparent image when player overlaps
                self._tile_rect.topleft = screen_pos
                if player_screen_rect.colliderect(self._tile_rect):
                    screen.blit(tile_data.occluded_image or tile_data.image, screen_pos)
                    player_occluded = True
                else:
                    normal_blits.append((tile_data.image, screen_pos))
            else:
                # Foreground-order layer tile with depth <= player: no occlusion needed
                normal_blits.append((tile_data.image, screen_pos))

        if normal_blits:
            screen.fblits(normal_blits)

        # Draw animated foreground tiles
        if self.game.anim_map_manager:
            anim_fg_blits = []
            for px, py, tile_id, depth in self.game.map_manager.get_visible_animated_chunks(self._viewport_world):
                if depth > player_depth:
                    img = self.game.anim_map_manager.get_current_frame_image(tile_id)
                    if img:
                        anim_fg_blits.append((img, (px + cam_offset.x, py + cam_offset.y)))
            if anim_fg_blits:
                screen.fblits(anim_fg_blits)

        return player_occluded



    def draw_hud(self):
        """Draw time and season HUD overlay (top-right, fixed to screen)."""
        self.game.hud.draw(self.game.screen)

    def draw_scene(self):
        """A helper representing the entire scene rendering logic."""
        self.game.screen.fill(Settings.COLOR_BG)
        self.game.visible_sprites.calculate_offset(self.game.player)
        self.draw_background()
        self.game.visible_sprites.custom_draw(self.game.screen, max_depth=self.game.player.depth - 1)

        is_occluded = self.draw_foreground()

        # Apply occlusion transparency to the player if they are occluded by foreground
        original_alpha = None
        if is_occluded and self.game.player.image:
            original_alpha = self.game.player.image.get_alpha()
            if original_alpha is None:
                original_alpha = 255
            self.game.player.image.set_alpha(Settings.OCCLUSION_ALPHA)

        self.game.visible_sprites.custom_draw(self.game.screen, min_depth=self.game.player.depth)

        # Restore the player's alpha
        if original_alpha is not None and self.game.player.image:
            self.game.player.image.set_alpha(original_alpha)

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
