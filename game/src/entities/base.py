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
        self.current_stair_clip: float = 0.0
        self.stair_start_clip: float = 0.0
        self.stair_target_clip: float = 0.0

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
        if not isinstance(current_vm, dict):
            current_vm = None

        # 3. Always assign current_vm to clear stale state
        self._vertical_move = current_vm

        if current_vm is not None and isinstance(current_vm, dict):
            logger.info(
                f"[DEBUG_MOVE] Vertical move tile detected at ({tx}, {ty}) | current_vm={current_vm}"
            )

        # 4. Normal vs Vertical move dispatch
        if current_vm is None or not isinstance(current_vm, dict):
            self._start_normal_move(tx, ty)
        else:
            self._start_vertical_move(tx, ty, current_vm)

    def _init_stair_clip_properties(self, target_vm: dict | None):
        """Initialize clip properties for moving to a target tile."""
        self.stair_start_clip = self.current_stair_clip
        if target_vm and target_vm.get("clip"):
            raw_offset = target_vm.get("visual_y_offset", 8)
            if raw_offset >= 0:
                clip_amount = 8 if raw_offset == 0 else raw_offset
                sprite_height = self.image.get_height() if self.image else 32
                self.stair_target_clip = float(min(clip_amount, sprite_height))
            else:
                self.stair_target_clip = 0.0
        else:
            self.stair_target_clip = 0.0

    def _start_normal_move(self, tx: int, ty: int):
        """Handle starting movement on a normal (non-vertical) tile."""
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
            if not isinstance(target_vm, dict):
                target_vm = None
            self.stair_target_offset = float(target_vm.get("visual_y_offset", 0.0)) if target_vm else 0.0
            self._vertical_move = target_vm

            self._init_stair_clip_properties(target_vm)

    def _start_vertical_move(self, tx: int, ty: int, current_vm: dict):
        """Handle starting movement on a vertical (stair/ladder) tile."""
        # 5. Look up behavior
        behavior = Settings.MOVEMENT_BEHAVIORS.get(current_vm.get("movement_type", "stair"))
        if behavior is None:
            return
        input_dir = (int(round(self.direction.x)), int(round(self.direction.y)))
        if behavior.allowed_axes == "horizontal":
            input_dir = (input_dir[0], 0)
        elif behavior.allowed_axes == "vertical":
            input_dir = (0, input_dir[1])
        if input_dir == (0, 0):
            self.direction = pygame.math.Vector2(0, 0)
            return

        intercepted_dir = behavior.move_map.get((input_dir, current_vm.get("stair_direction", "")))
        if intercepted_dir is None:
            self.direction = pygame.math.Vector2(0, 0)
            return

        predicted_dir = self._get_vertical_predicted_dir(tx, ty, current_vm)
        if predicted_dir is None:
            self.direction = pygame.math.Vector2(0, 0)
            return

        # 10. Step-off handling
        final_dir, target_vm = self._handle_vertical_step_off(
            tx, ty, predicted_dir, intercepted_dir, current_vm
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

            self._init_stair_clip_properties(target_vm)

            logger.info(
                f"[DEBUG_MOVE] Move initialized. target_pos={self.target_pos} | "
                f"offset: {self.stair_start_offset} -> {self.stair_target_offset}"
            )

    def _get_vertical_predicted_dir(self, tx: int, ty: int, current_vm: dict) -> tuple[int, int] | None:
        """Calculate the predicted move direction on a vertical movement tile."""
        behavior = Settings.MOVEMENT_BEHAVIORS.get(current_vm.get("movement_type", "stair"))
        if behavior is None:
            logger.warning(
                f"Unknown movement_type '{current_vm.get('movement_type', 'stair')}' at ({tx},{ty})"
            )
            return None

        input_dir = (int(round(self.direction.x)), int(round(self.direction.y)))
        if behavior.allowed_axes == "horizontal":
            input_dir = (input_dir[0], 0)
        elif behavior.allowed_axes == "vertical":
            input_dir = (0, input_dir[1])

        if input_dir == (0, 0):
            return None

        intercepted_dir = behavior.move_map.get((input_dir, current_vm.get("stair_direction", "")))
        if intercepted_dir is None:
            logger.warning(
                f"Unknown stair_direction '{current_vm.get('stair_direction', '')}' at ({tx},{ty})"
            )
            return None

        half = current_vm.get("half", False)
        is_diag = behavior.is_diagonal(half, intercepted_dir[1])
        logger.info(
            f"[DEBUG_MOVE] Interception: input={input_dir} -> intercepted={intercepted_dir} | "
            f"half={half} -> is_diagonal={is_diag}"
        )

        if is_diag:
            return intercepted_dir

        if behavior.fallback_axis == "horizontal":
            return (intercepted_dir[0], 0)
        if behavior.fallback_axis == "vertical":
            return (0, intercepted_dir[1])
        return intercepted_dir

    def _handle_vertical_step_off(
        self,
        tx: int,
        ty: int,
        predicted_dir: tuple[int, int],
        intercepted_dir: tuple[int, int],
        current_vm: dict,
    ) -> tuple[tuple[int, int], dict | None]:
        """Adjust movement direction and target properties for step-off scenarios."""
        target_tx = tx + predicted_dir[0]
        target_ty = ty + predicted_dir[1]
        target_vm = (
            self.game.map_manager.get_vertical_move_props(target_tx, target_ty)
            if (self.game and hasattr(self.game, "map_manager"))
            else None
        )
        if not isinstance(target_vm, dict):
            target_vm = None

        final_dir = predicted_dir
        if target_vm is None:
            if current_vm.get("movement_type") == "stair":
                # Step-off decision: choose flat or diagonal exit based on minimizing visual Y jump in pixels.
                current_offset = float(self.current_stair_offset)
                flat_jump = -current_offset
                diag_jump = intercepted_dir[1] * Settings.TILE_SIZE - current_offset

                if abs(flat_jump) <= abs(diag_jump):
                    final_dir = (intercepted_dir[0], 0)
                    target_tx = tx + final_dir[0]
                    target_ty = ty + final_dir[1]
                    target_vm = (
                        self.game.map_manager.get_vertical_move_props(target_tx, target_ty)
                        if (self.game and hasattr(self.game, "map_manager"))
                        else None
                    )
                    if not isinstance(target_vm, dict):
                        target_vm = None
                    logger.info(
                        f"[DEBUG_MOVE] Step-off detected. Visual Y jump minimizes to flat: {final_dir} | target_vm={target_vm}"
                    )
                else:
                    logger.info(
                        f"[DEBUG_MOVE] Step-off detected. Visual Y jump minimizes to diagonal: {final_dir} | target_vm={target_vm}"
                    )
        return final_dir, target_vm



    def interact(self, initiator) -> Any:
        """Called when another entity interacts with this one. To be overridden."""
        return None

    def update(self, dt: float):
        self.move(dt)
        self.update_stair_offset()

    def update_stair_offset(self):
        if not self.is_moving:
            vm = self._vertical_move
            if not isinstance(vm, dict):
                vm = None
            self.current_stair_offset = float(vm.get("visual_y_offset", 0.0)) if vm else 0.0
            if vm and vm.get("clip"):
                raw_offset = vm.get("visual_y_offset", 8)
                if raw_offset >= 0:
                    clip_amount = 8 if raw_offset == 0 else raw_offset
                    sprite_height = self.image.get_height() if self.image else 32
                    self.current_stair_clip = float(min(clip_amount, sprite_height))
                else:
                    self.current_stair_clip = 0.0
            else:
                self.current_stair_clip = 0.0
        else:
            if self.stair_move_distance > 0:
                curr_dist = (self.target_pos - self.pos).magnitude()
                progress = max(0.0, min(1.0, 1.0 - curr_dist / self.stair_move_distance))
                self.current_stair_offset = (
                    self.stair_start_offset
                    + (self.stair_target_offset - self.stair_start_offset) * progress
                )
                self.current_stair_clip = (
                    self.stair_start_clip
                    + (self.stair_target_clip - self.stair_start_clip) * progress
                )
            else:
                self.current_stair_offset = self.stair_target_offset
                self.current_stair_clip = self.stair_target_clip
