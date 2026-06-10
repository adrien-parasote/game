from typing import Any

import pygame
from src.config import Settings


class BaseEntity(pygame.sprite.Sprite):
    """Base class for all game entities (Player, NPCs, Obstacles)."""

    def __init__(
        self,
        pos: tuple,
        groups: pygame.sprite.Group | list[pygame.sprite.Group] | None = None,
        element_id: str | None = None,
    ):
        if groups is not None:
            super().__init__(groups)
        else:
            super().__init__()
        self.element_id = element_id
        self.game: Any | None = None
        self.image = pygame.Surface((Settings.PLAYER_SIZE, Settings.PLAYER_SIZE))
        self.image.fill("white")  # Fallback image
        self.rect = self.image.get_rect(center=pos)
        self.pos = pygame.math.Vector2(pos)
        self.direction = pygame.math.Vector2()
        self.speed = 0

        # Grid movement
        self.is_moving = False
        self.target_pos = pygame.math.Vector2(pos)
        from collections.abc import Callable

        self.walkable_func: Callable | None = None
        self.depth = 1
        self.name: str = ""
        self._world_state_key: str | None = None
        self._vertical_move: dict | None = None  # Props 25-vertical-move de la tuile courante

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

        if self.rect:
            self.rect.center = (round(self.pos.x), round(self.pos.y))

    def start_move(self):
        """Initialize a move to the next tile."""
        if self.direction.magnitude() == 0:
            return

        current_tx = int(self.pos.x // Settings.TILE_SIZE)
        current_ty = int(self.pos.y // Settings.TILE_SIZE)

        # ── [NOUVEAU] ── Interception escalier
        if self.game and hasattr(self.game, "map_manager"):
            vm = self.game.map_manager.get_vertical_move_props(current_tx, current_ty)
            if vm and isinstance(vm, dict):
                self._vertical_move = vm
                stair_dir = vm["stair_direction"]
                # Convert direction to discrete values
                dx = 1 if self.direction.x > 0.01 else (-1 if self.direction.x < -0.01 else 0)
                dy = 1 if self.direction.y > 0.01 else (-1 if self.direction.y < -0.01 else 0)
                dir_tuple = (dx, dy)
                
                # Check mapping in VERTICAL_MOVE_MAP
                map_key = (dir_tuple, stair_dir)
                if map_key in Settings.VERTICAL_MOVE_MAP:
                    self.direction = pygame.math.Vector2(Settings.VERTICAL_MOVE_MAP[map_key])
                else:
                    # Input non-mappé sur escalier -> Blocage silencieux complet
                    self.direction = pygame.math.Vector2(0, 0)
                    return
            else:
                self._vertical_move = None
        else:
            self._vertical_move = None

        if self.game and hasattr(self.game, "map_manager"):
            allowed_directions = self.game.map_manager.get_direction_flags(current_tx, current_ty)

            requested_dir = None
            if abs(self.direction.x) > abs(self.direction.y):
                requested_dir = "right" if self.direction.x > 0 else "left"
            else:
                requested_dir = "down" if self.direction.y > 0 else "up"

            if "any" not in allowed_directions and requested_dir not in allowed_directions:
                return  # Movement blocked by current tile's exit constraints

        # Calculate target
        self.target_pos = self.pos + self.direction * Settings.TILE_SIZE

        # World boundary clamping
        if self.game and hasattr(self.game, "map_manager"):
            world_width = self.game.map_manager.width * Settings.TILE_SIZE
            world_height = self.game.map_manager.height * Settings.TILE_SIZE
        else:
            world_width = Settings.MAP_SIZE * Settings.TILE_SIZE
            world_height = Settings.MAP_SIZE * Settings.TILE_SIZE
        half_w, half_h = (
            (self.rect.width / 2, self.rect.height / 2)
            if self.rect
            else (Settings.TILE_SIZE / 2, Settings.TILE_SIZE / 2)
        )

        self.target_pos.x = max(half_w, min(self.target_pos.x, world_width - half_w))
        self.target_pos.y = max(half_h, min(self.target_pos.y, world_height - half_h))

        # Check custom collisions (e.g. MapManager wall tiles)
        if self.walkable_func is not None:  # noqa: SIM102
            if not self.walkable_func(self.target_pos.x, self.target_pos.y, requester=self):
                self.target_pos = pygame.math.Vector2(self.pos)
                return

        # Only start if target isn't current pos
        if self.target_pos != self.pos:
            self.is_moving = True

    def interact(self, initiator) -> Any:
        """Called when another entity interacts with this one. To be overridden."""
        return None

    def update(self, dt: float):
        self.move(dt)
