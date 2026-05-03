import pygame
import logging
from src.config import Settings

class RenderManager:
    """Handles all visual rendering logic for the game scene, decoupling it from the main event loop."""
    
    def __init__(self, game):
        self.game = game

    def draw_background(self):
        """Draw tiles with depth <= player depth (behind player) using pre-rendered surfaces."""
        cam_offset = self.game.visible_sprites.offset
        
        # Get all layers that should be behind the player
        for layer_id in self.game.map_manager.layer_order:
            depth = self.game.map_manager.layer_depths.get(layer_id, 0)
            
            if depth <= self.game.player.depth:
                surface = self.game.map_manager.get_layer_surface(layer_id, pygame)
                if surface:
                    self.game.screen.blit(surface, (cam_offset.x, cam_offset.y))

    def draw_foreground(self):
        """Draw tiles with depth > player depth (in front of player). Use cached occluded versions if needed."""
        cam_offset = self.game.visible_sprites.offset
        screen_rect = self.game.screen.get_rect()
        viewport_world = pygame.Rect(-cam_offset.x, -cam_offset.y, screen_rect.width, screen_rect.height)
        
        # Get visual rect anchored bottomright to physical rect for correct occlusion testing
        visual_rect = self.game.player.image.get_rect(bottomright=self.game.player.rect.bottomright)
        player_screen_rect = visual_rect.move(cam_offset.x, cam_offset.y)
        
        for px, py, tile_id, depth in self.game.map_manager.get_visible_chunks(viewport_world, min_depth=self.game.player.depth):
            if depth > self.game.player.depth:
                tile_data = self.game.map_manager.tiles[tile_id]
                screen_pos = (px + cam_offset.x, py + cam_offset.y)
                dest_rect = pygame.Rect(screen_pos[0], screen_pos[1], self.game.tile_size, self.game.tile_size)
                
                if player_screen_rect.colliderect(dest_rect):
                    # Use pre-cached occluded image
                    self.game.screen.blit(tile_data.occluded_image or tile_data.image, screen_pos)
                else:
                    self.game.screen.blit(tile_data.image, screen_pos)

    def draw_hud(self):
        """Draw time and season HUD overlay (top-right, fixed to screen)."""
        self.game.hud.draw(self.game.screen)

    def draw_scene(self):
        """A helper representing the entire scene rendering logic."""
        self.game.screen.fill(Settings.COLOR_BG)
        self.game.visible_sprites.calculate_offset(self.game.player)
        self.draw_background()
        self.game.visible_sprites.custom_draw(self.game.screen)
        self.draw_foreground()
        
        night_alpha = self.game.time_system.night_alpha
        window_positions = self.game.map_manager.get_window_positions()
        
        # Render additive window beams (always visible during day and night)
        self.game.lighting_manager.draw_additive_window_beams(self.game.screen, window_positions, self.game.visible_sprites.offset)
        
        # Render dynamic lighting on darkness overlay
        if night_alpha > 0:
            active_torches = [obj for obj in self.game.interactives if getattr(obj, 'is_on', False) and getattr(obj, 'halo_size', 0) > 0]
            
            overlay = self.game.lighting_manager.create_overlay(
                window_positions, 
                active_torches, 
                self.game.visible_sprites.offset
            )
            self.game.screen.blit(overlay, (0, 0))
            
        cam_offset = self.game.visible_sprites.offset
        for obj in self.game.interactives:
            if hasattr(obj, 'draw_effects'):
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
        if getattr(self.game, '_npc_bubble', None) is not None:
            npc = self.game._npc_bubble["npc"]
            cam = self.game.visible_sprites.offset
            # Build a screen-space rect from the NPC world rect
            npc_screen_rect = npc.rect.move(cam.x, cam.y)
            self.game.speech_bubble.draw(
                self.game.screen,
                npc_screen_rect,
                self.game._npc_bubble["text"],
                page=self.game._npc_bubble["page"],
                speaker_name=getattr(npc, 'name', '') or npc.element_id.capitalize()
            )
            
        if self.game.inventory_ui.is_open:
            self.game.inventory_ui.draw(self.game.screen)
        if self.game.chest_ui.is_open:
            self.game.chest_ui.draw(self.game.screen)
