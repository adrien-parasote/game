import logging
from typing import Any

import pygame
from src.config import Settings

logger = logging.getLogger(__name__)


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
        self._vertical_move: dict | None = None  # 25-vertical-move properties of the current tile
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
        else:
            # Step towards target
            step = move_vector.normalize() * self.speed * dt
            self.pos += step

        if self.rect:
            self.rect.center = (round(self.pos.x), round(self.pos.y))

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

        # 1. Compute grid position
        tx = int(self.pos.x // Settings.TILE_SIZE)
        ty = int(self.pos.y // Settings.TILE_SIZE)

        logger.info(
            f"[DEBUG_MOVE] {self.__class__.__name__} starting move at ({tx}, {ty}) | pos={self.pos} | dir={self.direction}"
        )

        # 2. Call get_vertical_move_props
        current_vm = (
            self.game.map_manager.get_vertical_move_props(tx, ty)
            if (self.game and hasattr(self.game, "map_manager"))
            else None
        )

        # 3. Always assign current_vm to clear stale state
        self._vertical_move = current_vm

        if current_vm is not None and isinstance(current_vm, dict):
            logger.info(
                f"[DEBUG_MOVE] Vertical move tile detected at ({tx}, {ty}) | current_vm={current_vm}"
            )

        # 4. If current_vm is None or not a dict -> normal floor movement, exit
        if current_vm is None or not isinstance(current_vm, dict):
            if self.game and hasattr(self.game, "map_manager"):
                allowed_directions = self.game.map_manager.get_direction_flags(tx, ty)
                if abs(self.direction.x) > abs(self.direction.y):
                    requested_dir = "right" if self.direction.x > 0 else "left"
                else:
                    requested_dir = "down" if self.direction.y > 0 else "up"
                if "any" not in allowed_directions and requested_dir not in allowed_directions:
                    return

            self.target_pos = self.pos + self.direction * Settings.TILE_SIZE
            self._clamp_target_to_world()

            if self.walkable_func is not None:
                if not self.walkable_func(self.target_pos.x, self.target_pos.y, requester=self):
                    self.target_pos = pygame.math.Vector2(self.pos)
                    return

            if self.target_pos != self.pos:
                self.is_moving = True
                self.stair_start_pos = pygame.math.Vector2(self.pos)
                self.stair_move_distance = (self.target_pos - self.pos).magnitude()
                self.stair_start_offset = self.current_stair_offset
                target_tx = int(self.target_pos.x // Settings.TILE_SIZE)
                target_ty = int(self.target_pos.y // Settings.TILE_SIZE)
                target_vm = (
                    self.game.map_manager.get_vertical_move_props(target_tx, target_ty)
                    if (self.game and hasattr(self.game, "map_manager"))
                    else None
                )
                self.stair_target_offset = float(target_vm.get("visual_y_offset", 0.0)) if target_vm else 0.0
                self._vertical_move = target_vm
            return

        # 5. Look up behavior
        behavior = Settings.MOVEMENT_BEHAVIORS.get(current_vm.get("movement_type", "stair"))
        if behavior is None:
            logger.warning(
                f"Unknown movement_type '{current_vm.get('movement_type', 'stair')}' at ({tx},{ty})"
            )
            return

        # 6. Filter input_dir by behavior.allowed_axes
        input_dir = (int(round(self.direction.x)), int(round(self.direction.y)))
        if behavior.allowed_axes == "horizontal":
            input_dir = (input_dir[0], 0)
        elif behavior.allowed_axes == "vertical":
            input_dir = (0, input_dir[1])

        if input_dir == (0, 0):
            self.direction = pygame.math.Vector2(0, 0)
            return

        # 7. Look up intercepted direction
        intercepted_dir = behavior.move_map.get((input_dir, current_vm.get("stair_direction", "")))
        if intercepted_dir is None:
            logger.warning(
                f"Unknown stair_direction '{current_vm.get('stair_direction', '')}' at ({tx},{ty})"
            )
            self.direction = pygame.math.Vector2(0, 0)
            return

        # 8. Slope alternation check
        half = current_vm.get("half", False)
        is_diag = behavior.is_diagonal(half, intercepted_dir[1])
        logger.info(
            f"[DEBUG_MOVE] Interception: input={input_dir} -> intercepted={intercepted_dir} | "
            f"half={half} -> is_diagonal={is_diag}"
        )

        if is_diag:
            predicted_dir = intercepted_dir
        else:
            if behavior.fallback_axis == "horizontal":
                predicted_dir = (intercepted_dir[0], 0)
            elif behavior.fallback_axis == "vertical":
                predicted_dir = (0, intercepted_dir[1])
            else:
                predicted_dir = intercepted_dir

        # 9. Boundary check
        target_tx = tx + predicted_dir[0]
        target_ty = ty + predicted_dir[1]
        target_vm = (
            self.game.map_manager.get_vertical_move_props(target_tx, target_ty)
            if (self.game and hasattr(self.game, "map_manager"))
            else None
        )

        # 10. Step-off handling
        final_dir = predicted_dir
        if target_vm is None:
            if intercepted_dir[1] > 0:  # descending
                final_dir = (intercepted_dir[0], 0)
                target_tx = tx + final_dir[0]
                target_ty = ty + final_dir[1]
                target_vm = (
                    self.game.map_manager.get_vertical_move_props(target_tx, target_ty)
                    if (self.game and hasattr(self.game, "map_manager"))
                    else None
                )
                logger.info(
                    f"[DEBUG_MOVE] Step-off (descending) detected. Forced flat: {final_dir} | target_vm={target_vm}"
                )
            else:
                logger.info(
                    f"[DEBUG_MOVE] Step-off (climbing) detected. Keeping diagonal: {final_dir} | target_vm={target_vm}"
                )

        # 11. Walkable check
        self.target_pos = self.pos + pygame.math.Vector2(final_dir) * Settings.TILE_SIZE
        self._clamp_target_to_world()

        if self.walkable_func is not None:
            if not self.walkable_func(self.target_pos.x, self.target_pos.y, requester=self):
                self.target_pos = pygame.math.Vector2(self.pos)
                self.direction = pygame.math.Vector2(0, 0)
                logger.info(
                    f"[DEBUG_MOVE] Target position {self.target_pos} not walkable. Aborting."
                )
                return

        # 12. Update target pos and initialize offset tracking
        if self.target_pos != self.pos:
            self.is_moving = True
            self.direction = pygame.math.Vector2(final_dir)
            self.stair_start_pos = pygame.math.Vector2(self.pos)
            self.stair_move_distance = (self.target_pos - self.pos).magnitude()
            self.stair_start_offset = self.current_stair_offset
            self.stair_target_offset = float(target_vm.get("visual_y_offset", 0.0)) if target_vm else 0.0
            self._vertical_move = target_vm
            logger.info(
                f"[DEBUG_MOVE] Move initialized. target_pos={self.target_pos} | target_grid=({target_tx}, {target_ty}) | "
                f"offset: {self.stair_start_offset} -> {self.stair_target_offset}"
            )


    def interact(self, initiator) -> Any:
        """Called when another entity interacts with this one. To be overridden."""
        return None

    def update(self, dt: float):
        self.move(dt)
        self.update_stair_offset()

    def update_stair_offset(self):
        if not self.is_moving:
            vm = self._vertical_move
            self.current_stair_offset = float(vm.get("visual_y_offset", 0.0)) if vm else 0.0
        else:
            if self.stair_move_distance > 0:
                curr_dist = (self.target_pos - self.pos).magnitude()
                progress = max(0.0, min(1.0, 1.0 - curr_dist / self.stair_move_distance))
                self.current_stair_offset = (
                    self.stair_start_offset
                    + (self.stair_target_offset - self.stair_start_offset) * progress
                )
            else:
                self.current_stair_offset = self.stair_target_offset
