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
        self.current_stair_offset: float = 0.0
        self.stair_start_offset: float = 0.0
        self.stair_target_offset: float = 0.0
        self.stair_move_distance: float = 0.0
        self.stair_start_pos: pygame.math.Vector2 = pygame.math.Vector2(pos)

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
            # Transition _vertical_move to the target tile properties
            if self.game and hasattr(self.game, "map_manager"):
                tx = int(self.pos.x // Settings.TILE_SIZE)
                ty = int(self.pos.y // Settings.TILE_SIZE)
                self._vertical_move = self.game.map_manager.get_vertical_move_props(tx, ty)
            else:
                self._vertical_move = None
        else:
            # Step towards target
            step = move_vector.normalize() * self.speed * dt
            self.pos += step

        if self.rect:
            self.rect.center = (round(self.pos.x), round(self.pos.y))

    def _apply_stair_interception(self, current_tx: int, current_ty: int) -> bool:
        """Apply stair direction interception if standing on a stair tile.

        Checks whether the current tile has stair properties and adjusts
        self.direction to the correct diagonal — or resets it to (0, 0) for
        unmapped inputs (silent block).

        Returns:
            True  — movement should continue (direction may have been rewritten).
            False — movement is silently blocked (caller must return immediately).

        Side effect: sets self._vertical_move from the current tile.
        """
        if not (self.game and hasattr(self.game, "map_manager")):
            self._vertical_move = None
            return True

        vm = self.game.map_manager.get_vertical_move_props(current_tx, current_ty)
        if not (vm and isinstance(vm, dict)):
            self._vertical_move = None
            return True

        self._vertical_move = vm
        stair_dir = vm["stair_direction"]
        dx = 1 if self.direction.x > 0.01 else (-1 if self.direction.x < -0.01 else 0)
        dy = 1 if self.direction.y > 0.01 else (-1 if self.direction.y < -0.01 else 0)
        map_key = ((dx, dy), stair_dir)

        if map_key not in Settings.VERTICAL_MOVE_MAP:
            # Input non-mappé sur escalier -> Blocage silencieux complet
            self.direction = pygame.math.Vector2(0, 0)
            return False

        dir_diag = Settings.VERTICAL_MOVE_MAP[map_key]
        diag_tx, diag_ty = current_tx + dir_diag[0], current_ty + dir_diag[1]
        ortho_tx, ortho_ty = current_tx + dx, current_ty + dy

        diag_vm = self.game.map_manager.get_vertical_move_props(diag_tx, diag_ty)
        next_vm = self.game.map_manager.get_vertical_move_props(ortho_tx, ortho_ty)
        diag_is_stair = diag_vm is not None and isinstance(diag_vm, dict)
        ortho_is_stair = next_vm is not None and isinstance(next_vm, dict)

        is_diag_walkable = False
        is_ortho_walkable = True
        if hasattr(self.game.map_manager, "is_walkable"):
            is_diag_walkable = self.game.map_manager.is_walkable(diag_tx, diag_ty)
            is_ortho_walkable = self.game.map_manager.is_walkable(ortho_tx, ortho_ty)

        # Interception decision:
        # 1. Next flat tile is stair  2. Diagonal target is stair
        # 3. Both normal but diagonal walkable and orthogonal blocked (step-boundary)
        if ortho_is_stair or diag_is_stair or (is_diag_walkable and not is_ortho_walkable):
            self.direction = pygame.math.Vector2(dir_diag)
        # else: step-off — keep original orthogonal direction
        return True

    def _clamp_target_to_world(self) -> None:
        """Clamp self.target_pos to world boundaries based on entity size."""
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

    def start_move(self):
        """Initialize a move to the next tile."""
        if self.direction.magnitude() == 0:
            return

        current_tx = int(self.pos.x // Settings.TILE_SIZE)
        current_ty = int(self.pos.y // Settings.TILE_SIZE)

        if not self._apply_stair_interception(current_tx, current_ty):
            return

        if self.game and hasattr(self.game, "map_manager"):
            allowed_directions = self.game.map_manager.get_direction_flags(current_tx, current_ty)
            if abs(self.direction.x) > abs(self.direction.y):
                requested_dir = "right" if self.direction.x > 0 else "left"
            else:
                requested_dir = "down" if self.direction.y > 0 else "up"
            if "any" not in allowed_directions and requested_dir not in allowed_directions:
                return  # Movement blocked by current tile's exit constraints

        # Calculate target and clamp to world
        self.target_pos = self.pos + self.direction * Settings.TILE_SIZE
        self._clamp_target_to_world()

        # Check custom collisions (e.g. MapManager wall tiles)
        if self.walkable_func is not None:  # noqa: SIM102
            if not self.walkable_func(self.target_pos.x, self.target_pos.y, requester=self):
                self.target_pos = pygame.math.Vector2(self.pos)
                return

        # Only start if target isn't current pos
        if self.target_pos != self.pos:
            self.is_moving = True
            # Setup interpolation caching
            self.stair_start_pos = pygame.math.Vector2(self.pos)
            self.stair_start_offset = self.current_stair_offset
            if self.game and hasattr(self.game, "map_manager"):
                target_tx = int(self.target_pos.x // Settings.TILE_SIZE)
                target_ty = int(self.target_pos.y // Settings.TILE_SIZE)
                target_vm = self.game.map_manager.get_vertical_move_props(target_tx, target_ty)
                self.stair_target_offset = target_vm["visual_y_offset"] if target_vm else 0.0
            else:
                self.stair_target_offset = 0.0
            self.stair_move_distance = (self.target_pos - self.pos).magnitude()

    def interact(self, initiator) -> Any:
        """Called when another entity interacts with this one. To be overridden."""
        return None

    def update(self, dt: float):
        self.move(dt)
        self.update_stair_offset()

    def update_stair_offset(self):
        if not self.is_moving:
            # Standing still: read cached _vertical_move
            vm = self._vertical_move
            self.current_stair_offset = vm["visual_y_offset"] if vm else 0.0
        else:
            # Moving: interpolate offset based on movement progress
            total_dist = (self.target_pos - self.stair_start_pos).magnitude()
            if total_dist > 0:
                curr_dist = (self.target_pos - self.pos).magnitude()
                progress = max(0.0, min(1.0, 1.0 - curr_dist / total_dist))
                self.current_stair_offset = self.stair_start_offset + (self.stair_target_offset - self.stair_start_offset) * progress
            else:
                self.current_stair_offset = self.stair_target_offset
