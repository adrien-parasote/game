import logging
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
        self._vertical_move: dict | None = None  # 25-vertical-move properties of the current tile
        self.current_stair_offset: float = 0.0
        self.stair_start_offset: float = 0.0
        self.stair_target_offset: float = 0.0
        self.current_stair_clip: float = 0.0
        self.stair_start_clip: float = 0.0
        self.stair_target_clip: float = 0.0
        self.stair_move_distance: float = 0.0
        self.stair_start_pos: pygame.math.Vector2 = pygame.math.Vector2(pos)

    def _max_stair_clip(self) -> float:
        """Return maximum clip amount for this entity."""
        return float(Settings.TILE_SIZE // 2)

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
        # Intentionally ignore dy: VERTICAL_MOVE_MAP keys always use (dx, 0).
        # A residual dy from the previous diagonal step would cause a silent block.
        map_key = ((dx, 0), stair_dir)

        if map_key not in Settings.VERTICAL_MOVE_MAP:
            # Non-mappable input on stair (e.g. UP/DOWN) → silent block
            self.direction = pygame.math.Vector2(0, 0)
            return False

        # Determine if the character is ascending the stairs
        if stair_dir in ("up,right", "down,left", "right"):
            # UP is Right, DOWN is Left
            is_going_up = (dx == 1)
        elif stair_dir in ("up,left", "down,right", "left"):
            # UP is Left, DOWN is Right
            is_going_up = (dx == -1)
        else:
            is_going_up = False
        stair_half = bool(vm.get("stair_half", False))

        # Ascending: diagonal move happens on the 'stair_half=True' tile
        # Descending: diagonal move happens on the 'stair_half=False' tile
        should_move_diagonally = stair_half if is_going_up else (not stair_half)

        target_dir = Settings.VERTICAL_MOVE_MAP[map_key] if should_move_diagonally else (dx, 0)

        target_tx = current_tx + target_dir[0]
        target_ty = current_ty + target_dir[1]
        target_vm = self.game.map_manager.get_vertical_move_props(target_tx, target_ty)
        if target_vm is None:
            # Step-off boundary: if the diagonal target is not a stair tile,
            # force flat movement to exit the stairs correctly onto the floor.
            target_dir = (dx, 0)

        self.direction = pygame.math.Vector2(target_dir)
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
            self.stair_start_clip = self.current_stair_clip
            if self.game and hasattr(self.game, "map_manager"):
                target_tx = int(self.target_pos.x // Settings.TILE_SIZE)
                target_ty = int(self.target_pos.y // Settings.TILE_SIZE)
                target_vm = self.game.map_manager.get_vertical_move_props(target_tx, target_ty)
                self._vertical_move = target_vm
                self.stair_target_offset = target_vm["visual_y_offset"] if target_vm else 0.0
                max_clip = self._max_stair_clip()
                self.stair_target_clip = max_clip if target_vm and target_vm.get("stair_clip") else 0.0
            else:
                self.stair_target_offset = 0.0
                self.stair_target_clip = 0.0
            self.stair_move_distance = (self.target_pos - self.pos).magnitude()

    def interact(self, initiator) -> Any:
        """Called when another entity interacts with this one. To be overridden."""
        return None

    def update(self, dt: float):
        self.move(dt)
        self.update_stair_offset()

    def update_stair_offset(self):
        if getattr(self, 'stair_clip_exempt', False):
            self.current_stair_clip = 0.0

        if not self.is_moving:
            # Standing still: read cached _vertical_move
            vm = self._vertical_move
            self.current_stair_offset = vm["visual_y_offset"] if vm else 0.0
            if not getattr(self, 'stair_clip_exempt', False):
                self.current_stair_clip = self._max_stair_clip() if vm and vm.get("stair_clip") else 0.0
        else:
            # Moving: interpolate offset based on movement progress
            total_dist = (self.target_pos - self.stair_start_pos).magnitude()
            if total_dist > 0:
                curr_dist = (self.target_pos - self.pos).magnitude()
                progress = max(0.0, min(1.0, 1.0 - curr_dist / total_dist))
                self.current_stair_offset = self.stair_start_offset + (self.stair_target_offset - self.stair_start_offset) * progress
                if not getattr(self, 'stair_clip_exempt', False):
                    self.current_stair_clip = self.stair_start_clip + (self.stair_target_clip - self.stair_start_clip) * progress
            else:
                self.current_stair_offset = self.stair_target_offset
                if not getattr(self, 'stair_clip_exempt', False):
                    self.current_stair_clip = self.stair_target_clip
