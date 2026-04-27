import pygame
from .base import BaseEntity
from src.config import Settings
from src.graphics.spritesheet import SpriteSheet
import os
from src.entities.emote import EmoteManager

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
        
        self.image = self.frames[0]
        # Ensure physical hitbox remains exactly 32x32 regardless of image size
        self.rect = pygame.Rect(0, 0, Settings.TILE_SIZE, Settings.TILE_SIZE)
        self.rect.center = pos
        
        # Stats
        self.level = 1
        self.hp = 100
        self.max_hp = 100
        self.gold = 0

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
        
        if self.is_moving:
            self.frame_index += self.animation_speed * dt
            self.frame_index %= 4
        else:
            self.frame_index = 0.0
            
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

