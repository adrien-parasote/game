import pygame
from src.config import Settings

class BaseEntity(pygame.sprite.Sprite):
    """Base class for all game entities (Player, NPCs, Obstacles)."""
    
    def __init__(self, pos: tuple, groups: pygame.sprite.Group = None, element_id: str = None):
        if groups is not None:
            super().__init__(groups)
        else:
            super().__init__()
        self.element_id = element_id
        self.image = pygame.Surface((Settings.PLAYER_SIZE, Settings.PLAYER_SIZE))
        self.image.fill('white') # Placeholder
        self.rect = self.image.get_rect(center=pos)
        self.pos = pygame.math.Vector2(pos)
        self.direction = pygame.math.Vector2()
        self.speed = 0
        
        # Grid movement
        self.is_moving = False
        self.target_pos = pygame.math.Vector2(pos)
        self.collision_func = None
        self.depth = 1

    def move(self, dt: float):
        """Move towards target_pos if is_moving, else start move if direction exists."""
        if not self.is_moving:
            if self.direction.magnitude() != 0:
                # Start new move
                self.start_move()
            else:
                return

        # Move towards target
        move_vector = self.target_pos - self.pos
        if move_vector.magnitude() <= self.speed * dt:
            # Reached target
            self.pos = pygame.math.Vector2(self.target_pos)
            self.is_moving = False
        else:
            # Step towards target
            step = move_vector.normalize() * self.speed * dt
            self.pos += step

        self.rect.center = (round(self.pos.x), round(self.pos.y))

    def start_move(self):
        """Initialize a move to the next tile."""
        if self.direction.magnitude() == 0:
            return

        # Calculate target
        self.target_pos = self.pos + self.direction * Settings.TILE_SIZE
        
        # World boundary clamping
        world_width = Settings.MAP_SIZE * Settings.TILE_SIZE
        world_height = Settings.MAP_SIZE * Settings.TILE_SIZE
        half_w, half_h = self.rect.width / 2, self.rect.height / 2
        
        self.target_pos.x = max(half_w, min(self.target_pos.x, world_width - half_w))
        self.target_pos.y = max(half_h, min(self.target_pos.y, world_height - half_h))
        
        # Check custom collisions (e.g. MapManager wall tiles)
        if self.collision_func is not None:
            if self.collision_func(self.target_pos.x, self.target_pos.y):
                self.target_pos = pygame.math.Vector2(self.pos)
                return
        
        # Only start if target isn't current pos
        if self.target_pos != self.pos:
            self.is_moving = True

    def interact(self, initiator):
        """Called when another entity interacts with this one. To be overridden."""
        pass

    def update(self, dt: float):
        self.move(dt)
