import pygame
from .base import BaseEntity
from src.config import Settings
from src.graphics.spritesheet import SpriteSheet
import os
from src.entities.emote import EmoteManager
from src.engine.inventory_system import Inventory

class Player(BaseEntity):
    """Player entity with keyboard input handling."""
    
    def __init__(self, pos: tuple, groups: pygame.sprite.Group = None, 
                 speed: int = Settings.PLAYER_SPEED, element_id: str = None):
        super().__init__(pos, groups, element_id=element_id)
        self.speed = speed
        
        # Load Spritesheet
        sheet_path = os.path.join(os.path.dirname(__file__), "..", "..", "assets", "images", "characters", "01-character.png")
        sheet = SpriteSheet(sheet_path)
        self.frames = sheet.load_grid(4, 4)
        
        # Animation State
        self.frame_index = 0.0
        self.animation_speed = 1.0 / 0.15  # frames per second (150ms per frame)
        self.current_state = 'down' # default facing
        self._was_moving = False   # tracks previous frame's movement to avoid per-tile reset
        
        self.image = self.frames[0]
        # Ensure physical hitbox remains exactly 32x32 regardless of image size
        self.rect = pygame.Rect(0, 0, Settings.TILE_SIZE, Settings.TILE_SIZE)
        self.rect.center = pos
        
        # Stats
        self.level = 1
        self.hp = 100
        self.max_hp = 100
        self.gold = 0
        self.inventory = Inventory()

        # Emote System
        self.audio_manager = None # Set by Game
        self.emote_manager = EmoteManager(self)


    def input(self):
        """Get keyboard input and set direction."""
        keys = pygame.key.get_pressed()
        
        # Vertical Priority
        if keys[Settings.MOVE_UP]:
            self.direction.y = -1
            self.direction.x = 0
            self.current_state = 'up'
        elif keys[Settings.MOVE_DOWN]:
            self.direction.y = 1
            self.direction.x = 0
            self.current_state = 'down'
        # Horizontal (only if no vertical)
        elif keys[Settings.MOVE_LEFT]:
            self.direction.x = -1
            self.direction.y = 0
            self.current_state = 'left'
        elif keys[Settings.MOVE_RIGHT]:
            self.direction.x = 1
            self.direction.y = 0
            self.current_state = 'right'
        else:
            self.direction.x = 0
            self.direction.y = 0

    def _update_animation(self, dt: float):
        """Update sprite animation based on state and dt."""
        # Row offset based on direction state
        row_offsets = {
            'down': 0,
            'left': 4,
            'right': 8,
            'up': 12
        }
        offset = row_offsets.get(self.current_state, 0)
        
        prev_int_frame = int(self.frame_index)
        
        if self.is_moving:
            self.frame_index += self.animation_speed * dt
            self.frame_index %= 4
        elif not self._was_moving:
            # Only reset to idle frame after 2+ consecutive stopped frames.
            # Absorbs the single is_moving=False tile-arrival frame during continuous movement.
            self.frame_index = 0.0

        self._was_moving = self.is_moving

        current_int_frame = int(self.frame_index)
        
        # Trigger footstep on frames 1 and 3
        if self.is_moving and current_int_frame != prev_int_frame and current_int_frame in (1, 3):
            # Resolve material from map
            material = None
            if hasattr(self, 'game') and hasattr(self.game, 'map_manager') and self.game.map_manager:
                material = self.game.map_manager.get_terrain_material_at(int(self.pos.x), int(self.pos.y))
            
            sfx_name = f"04-footstep_{material}" if material else "04-footstep"
            
            if self.audio_manager:
                success = self.audio_manager.play_sfx(sfx_name, source_id="player", volume_multiplier=0.8)
                if not success and material:
                    self.audio_manager.play_sfx("04-footstep", source_id="player", volume_multiplier=0.6)
            
        # Get integer index to select frame (0 to 3) + offset
        current_frame = int(self.frame_index) % 4
        self.image = self.frames[offset + current_frame]

    def update(self, dt: float):
        # We don't call self.input() here to keep it testable with manual direction set
        # But in the game loop we would
        self.move(dt)
        self._update_animation(dt)

    def playerEmote(self, name: str):
        """Trigger an emote on the player."""
        self.emote_manager.trigger(name)

