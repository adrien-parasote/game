import pygame
import sys
import logging
import logging.handlers
import os
from src.entities.player import Player
from src.entities.groups import CameraGroup
from src.map.manager import MapManager
from src.map.layout import OrthogonalLayout
from src.engine.time_system import TimeSystem
from src.config import Settings

class Game:
    """Main game class that manages the core loop and state."""
    
    def __init__(self):
        self._setup_logging()
        pygame.init()
        logging.info("Initializing Game Engine...")
        
        # Display initialization with Fullscreen support
        display_flags = pygame.FULLSCREEN if Settings.FULLSCREEN else 0
        self.screen = pygame.display.set_mode(
            (Settings.WINDOW_WIDTH, Settings.WINDOW_HEIGHT), 
            display_flags
        )
        pygame.display.set_caption(Settings.GAME_TITLE)
        self.clock = pygame.time.Clock()
        
        # Load Constants from Settings
        self.tile_size = Settings.TILE_SIZE
        self.map_size = Settings.MAP_SIZE
        
        # Setup Groups
        self.visible_sprites = CameraGroup()
        self.npcs = pygame.sprite.Group()
        
        # Setup Map
        from src.map.tmj_parser import TmjParser
        parser = TmjParser()
        map_path = os.path.join("assets", "maps", "00-castel.tmj")
        map_result = parser.load_map(map_path)
        
        self.layout = OrthogonalLayout(self.tile_size)
        self.map_manager = MapManager(map_result, self.layout)
        
        # Override MAP_SIZE for boundary logic in BaseEntity if needed
        self.map_size = max(self.map_manager.width, self.map_manager.height)
        Settings.MAP_SIZE = self.map_size
        
        # Initialize camera bounds
        world_width_px = self.map_manager.width * self.tile_size
        world_height_px = self.map_manager.height * self.tile_size
        self.visible_sprites.set_world_size(world_width_px, world_height_px)
        
        # Local state
        self.is_fullscreen = Settings.FULLSCREEN
        self.last_fps_update = 0
        
        # Time System
        self.time_system = TimeSystem(initial_hour=Settings.INITIAL_HOUR)
        self.hud_font = pygame.font.SysFont("monospace", 18, bold=True)
        
        logging.info(f"Screen setup: {Settings.WINDOW_WIDTH}x{Settings.WINDOW_HEIGHT} (Fullscreen: {self.is_fullscreen})")
        
        # Create Player
        half_tile = self.tile_size // 2
        spawn_dict = map_result.get("spawn_player")
        
        if spawn_dict:
            # Tiled object coordinates are top-left, we center it accurately by pushing it half a tile
            spawn_pos = (spawn_dict["x"] + half_tile, spawn_dict["y"] + half_tile)
        else:
            spawn_pos = (
                self.map_size * self.tile_size // 2 + half_tile, 
                self.map_size * self.tile_size // 2 + half_tile
            )
            
        self.player = Player(spawn_pos, self.visible_sprites, speed=Settings.PLAYER_SPEED)
        self.player.collision_func = self._is_collidable

    def _is_collidable(self, px_center: float, py_center: float) -> bool:
        """Collision checking adapter for Entity target position."""
        wx, wy = self.layout.to_world(px_center, py_center)
        return self.map_manager.is_collidable(int(wx), int(wy))

    def _draw_background(self):
        """Draw tiles with depth <= player depth (behind player)"""
        cam_offset = self.visible_sprites.offset
        screen_rect = self.screen.get_rect()
        viewport_world = pygame.Rect(-cam_offset.x, -cam_offset.y, screen_rect.width, screen_rect.height)
        
        for px, py, tile_id, depth in self.map_manager.get_visible_chunks(viewport_world):
            if depth <= self.player.depth:
                surface = self.map_manager.tiles[tile_id].image
                self.screen.blit(surface, (px + cam_offset.x, py + cam_offset.y))

    def _draw_foreground(self):
        """Draw tiles with depth > player depth (in front of player). Apply 40% opacity if colliding."""
        cam_offset = self.visible_sprites.offset
        screen_rect = self.screen.get_rect()
        viewport_world = pygame.Rect(-cam_offset.x, -cam_offset.y, screen_rect.width, screen_rect.height)
        
        # Get visual rect anchored bottomright to physical rect for correct occlusion testing
        visual_rect = self.player.image.get_rect(bottomright=self.player.rect.bottomright)
        player_screen_rect = visual_rect.move(cam_offset.x, cam_offset.y)
        
        for px, py, tile_id, depth in self.map_manager.get_visible_chunks(viewport_world):
            if depth > self.player.depth:
                surface = self.map_manager.tiles[tile_id].image
                screen_pos = (px + cam_offset.x, py + cam_offset.y)
                dest_rect = pygame.Rect(screen_pos[0], screen_pos[1], self.tile_size, self.tile_size)
                
                if player_screen_rect.colliderect(dest_rect):
                    # Occlusion check: use dynamic alpha from settings
                    temp_surface = surface.copy()
                    temp_surface.set_alpha(Settings.OCCLUSION_ALPHA)
                    self.screen.blit(temp_surface, screen_pos)
                else:
                    self.screen.blit(surface, screen_pos)

    def _draw_hud(self):
        """Draw time and season HUD overlay top-left."""
        time_text = self.time_system.time_label
        season_text = self.time_system.season_label
        hud_str = f"{time_text} | {season_text}"
        
        # Render shadow first
        shadow_surf = self.hud_font.render(hud_str, True, (20, 20, 20))
        self.screen.blit(shadow_surf, (11, 11))
        
        # Render main text
        text_surf = self.hud_font.render(hud_str, True, (255, 255, 255))
        self.screen.blit(text_surf, (10, 10))

    def _handle_interactions(self):
        """Handle spatial interaction between player and world."""
        keys = pygame.key.get_pressed()
        if keys[pygame.K_SPACE] and not self.player.is_moving:
            # Prevent interaction spam
            if hasattr(self, '_interaction_cooldown') and self._interaction_cooldown > 0:
                return
            self._interaction_cooldown = 0.5
            
            # Predict interaction cell based on facing direction
            dir_vector = pygame.math.Vector2(0, 0)
            if self.player.current_state == 'down': dir_vector.y = 1
            elif self.player.current_state == 'up': dir_vector.y = -1
            elif self.player.current_state == 'left': dir_vector.x = -1
            elif self.player.current_state == 'right': dir_vector.x = 1
            
            target_pos = self.player.pos + dir_vector * self.tile_size
            target_rect = pygame.Rect(target_pos.x - 16, target_pos.y - 16, 32, 32)
            
            for npc in self.npcs:
                if npc.rect.colliderect(target_rect):
                    npc.interact(self.player)
                    break

    def run(self):
        """Main game loop optimized for 60 FPS."""
        while True:
            # Event handling
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.KEYDOWN:
                    if event.key == Settings.QUIT_KEY:
                        pygame.quit()
                        sys.exit()
                    if event.key == Settings.TOGGLE_FULLSCREEN_KEY:
                        self.toggle_fullscreen()

            # Update (Fixed 60 FPS)
            dt = self.clock.tick(Settings.FPS) / 1000.0
            
            # Update Time
            self.time_system.update(dt)
            
            # Input & Logic
            
            # Decrease interaction cooldown
            if hasattr(self, '_interaction_cooldown'):
                self._interaction_cooldown = max(0, self._interaction_cooldown - dt)
                
            self.player.input()
            self._handle_interactions()
            
            self.visible_sprites.update(dt)
            
            # CPU Freeze optimization for NPCs -> freeze if outside enlarged viewport
            screen_rect = self.screen.get_rect()
            viewport_world = screen_rect.move(-self.visible_sprites.offset.x, -self.visible_sprites.offset.y)
            viewport_world.inflate_ip(128, 128)
            
            for npc in self.npcs:
                npc.is_visible = viewport_world.colliderect(npc.rect)
                npc.update(dt)

            # Draw
            self.screen.fill(Settings.COLOR_BG)
            
            # Update camera offset BEFORE drawing anything
            self.visible_sprites.calculate_offset(self.player)
            
            # Draw layers behind the player
            self._draw_background()

            # Draw sorted sprites (Entities, etc.)
            self.visible_sprites.custom_draw(self.screen)
            
            # Draw layers in front of the player (occlusion with alpha)
            self._draw_foreground()
            
            # Apply darkness overlay
            night_alpha = self.time_system.night_alpha
            if night_alpha > 0:
                overlay = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
                overlay.fill((0, 0, 0, night_alpha))
                self.screen.blit(overlay, (0, 0))
                
            # Draw HUD
            self._draw_hud()
            
            # Dynamic Title Update (Every 1s)
            now = pygame.time.get_ticks()
            if now - self.last_fps_update > 1000:
                fps = self.clock.get_fps()
                pygame.display.set_caption(f"{Settings.GAME_TITLE} - {fps:.1f} FPS")
                self.last_fps_update = now
            
            pygame.display.update()

    def toggle_fullscreen(self):
        """Toggle between fullscreen and windowed mode."""
        try:
            pygame.display.toggle_fullscreen()
            self.is_fullscreen = not self.is_fullscreen
        except pygame.error as e:
            logging.warning(f"Native toggle_fullscreen failed: {e}. Falling back to set_mode.")
            self.is_fullscreen = not self.is_fullscreen
            display_flags = pygame.FULLSCREEN if self.is_fullscreen else 0
            self.screen = pygame.display.set_mode(
                (Settings.WINDOW_WIDTH, Settings.WINDOW_HEIGHT), 
                display_flags
            )
        logging.info(f"Fullscreen toggled: {self.is_fullscreen}")

    def _setup_logging(self):
        """Configure rotating file logging and console output."""
        log_dir = "logs"
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
            
        log_file = os.path.join(log_dir, "game.log")
        
        # Setup Logger
        logger = logging.getLogger()
        logger.setLevel(Settings.LOG_LEVEL)
        
        # Formatter
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        
        # Daily Rotating File Handler
        file_handler = logging.handlers.TimedRotatingFileHandler(
            log_file, when='D', interval=1, backupCount=7
        )
        file_handler.setFormatter(formatter)
        
        # Console Handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        
        # Avoid duplicate handlers if re-initialized
        if not logger.handlers:
            logger.addHandler(file_handler)
            logger.addHandler(console_handler)
