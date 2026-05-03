import pygame
import os
import random
from .base import BaseEntity
from src.config import Settings
from src.graphics.spritesheet import SpriteSheet

class NPC(BaseEntity):
    """Non-Playable Character with basic wandering and interaction."""
    
    def __init__(self, pos: tuple, groups: pygame.sprite.Group = None, 
                 wander_radius: int = 1, sheet_name: str = "01-character.png",
                 element_id: str = None):
        super().__init__(pos, groups, element_id=element_id)
        self.spawn_pos = pygame.math.Vector2(pos)
        self.wander_radius = wander_radius
        self.state = 'idle'  # 'idle', 'wander', 'interact'
        self.speed = getattr(Settings, "NPC_SPEED", 40)
        
        # Load Spritesheet
        sheet_path = os.path.join(os.path.dirname(__file__), "..", "..", "assets", "images", "characters", sheet_name)
        sheet = SpriteSheet(sheet_path)
        self.frames = sheet.load_grid(4, 4)
        
        self.frame_index = 0.0
        # Scale animation to movement speed so frames-per-tile matches the player's ratio:
        # player uses 1.0/0.15 fps at PLAYER_SPEED → same ratio applied to NPC speed.
        _player_anim = 1.0 / 0.15
        self.animation_speed = _player_anim * self.speed / Settings.PLAYER_SPEED
        self.current_facing = 'down'
        self._was_moving = False   # tracks previous frame's movement to avoid per-tile reset
        
        self.image = self.frames[0]
        # Strict physical hitbox
        self.rect = pygame.Rect(0, 0, Settings.TILE_SIZE, Settings.TILE_SIZE)
        self.rect.center = pos
        
        # CPU freeze management
        self.is_visible = True
        
        # Timer for wandering
        self._action_timer = 0
        self._action_cooldown = random.uniform(1.0, 3.0)

    def interact(self, initiator: BaseEntity) -> str:
        """Called when Player interacts with this NPC. Returns element_id for dialogue."""
        self.state = 'interact'
        # Face the initiator
        diff = initiator.pos - self.pos
        if abs(diff.x) > abs(diff.y):
            self.current_facing = 'right' if diff.x > 0 else 'left'
        else:
            self.current_facing = 'down' if diff.y > 0 else 'up'
            
        # Reset movement direction to prevent chaining, but do NOT set is_moving = False
        # so that the NPC finishes its current grid tile transition smoothly.
        self.direction = pygame.math.Vector2(0, 0)
        
        return self.element_id

    def start_move(self):
        """Override to strictly strictly enforce wander_radius constraint and handle state reversion."""
        if self.direction.magnitude() == 0:
            return
            
        target = self.pos + self.direction * Settings.TILE_SIZE
        dist_from_spawn = target.distance_to(self.spawn_pos) / Settings.TILE_SIZE
        
        if dist_from_spawn > self.wander_radius:
            self.direction = pygame.math.Vector2(0, 0)
            self.state = 'idle'
            return
            
        # Call base move logic (which handles collisions)
        super().start_move()
        
        # If move was blocked by collision, revert state
        if not self.is_moving:
            self.state = 'idle'

    def process_ai(self, dt: float):
        """Process wandering AI restricted by radius."""
        if self.state == 'interact':
            return # Frozen during interaction
            
        self._action_timer += dt
        if self._action_timer >= self._action_cooldown and not self.is_moving:
            self._action_timer = 0
            self._action_cooldown = random.uniform(2.0, 5.0)
            
            # Simple grid wander randomizer
            choices = [
                pygame.math.Vector2(1, 0),
                pygame.math.Vector2(-1, 0),
                pygame.math.Vector2(0, 1),
                pygame.math.Vector2(0, -1),
                pygame.math.Vector2(0, 0) # Stay idle
            ]
            
            chosen_dir = random.choice(choices)
            
            if chosen_dir.magnitude() > 0:
                # Check radius constraint before allowing move
                next_target = self.pos + chosen_dir * Settings.TILE_SIZE
                dist_from_spawn = next_target.distance_to(self.spawn_pos) / Settings.TILE_SIZE
                
                if dist_from_spawn <= self.wander_radius:
                    self.direction = chosen_dir
                    self.state = 'wander'
                    
                    if self.direction.x > 0: self.current_facing = 'right'
                    elif self.direction.x < 0: self.current_facing = 'left'
                    elif self.direction.y > 0: self.current_facing = 'down'
                    elif self.direction.y < 0: self.current_facing = 'up'
                else:
                    self.direction = pygame.math.Vector2(0, 0)
                    self.state = 'idle'
                    
    def _update_animation(self, dt: float):
        row_offsets = {'down': 0, 'left': 4, 'right': 8, 'up': 12}
        offset = row_offsets.get(self.current_facing, 0)
        
        if self.is_moving:
            self.frame_index += self.animation_speed * dt
            self.frame_index %= 4
        elif not self._was_moving:
            # Only reset to idle after 2+ consecutive stopped frames (absorbs tile-arrival frame).
            self.frame_index = 0.0

        self._was_moving = self.is_moving
            
        current_frame = int(self.frame_index) % 4
        self.image = self.frames[offset + current_frame]

    def update(self, dt: float):
        if not self.is_visible:
            return # CPU Freeze optimization
            
        if self.state != 'interact':
            self.process_ai(dt)
            
        if self.state == 'interact':
            self._action_timer += dt
            if self._action_timer >= self._action_cooldown:
                self.state = 'idle'
                
        self.move(dt)
        self._update_animation(dt)
