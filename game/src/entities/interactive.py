import ast
import logging
import math
import random
from pathlib import Path

import pygame
from src.entities.interactive_constants import (
    ANIM_SPEED_LIGHT_SOURCE,
    ANIM_SPEED_OBJECT,
    HALO_DEFAULT_ALPHA,
    HALO_DEFAULT_COLOR,
    INTERACTIVE_DUMMY_FRAME_COUNT,
    INTERACTIVE_POS_Y_OFFSET,
    INTERACTIVE_SHEET_COLS,
)
from src.entities.interactive_lighting import InteractiveLightingMixin
from src.entities.interactive_particles import InteractiveParticleMixin
from src.graphics.spritesheet import SpriteSheet

from .base import BaseEntity


class InteractiveEntity(InteractiveLightingMixin, InteractiveParticleMixin, BaseEntity):
    """
    Fixed interactive object (chest, switch, lamp, etc.) with animation
    and optional lighting halo.
    Lighting logic provided by InteractiveLightingMixin.
    Particle logic provided by InteractiveParticleMixin.
    """

    # Position to Direction mapping for interaction validation
    # Standard RPG spritesheet layout: 0=Down, 1=Left, 2=Right, 3=Up
    POSITION_TO_DIR = {0: "down", 1: "left", 2: "right", 3: "up"}  # noqa: RUF012

    def __init__(
        self,
        pos: tuple,
        groups: list[pygame.sprite.Group],
        sub_type: str,
        sprite_sheet: str,
        position: int = 3,
        depth: int = 1,
        start_row: int = 0,
        end_row: int = 3,
        width: int = 32,
        height: int = 32,
        obstacles_group: pygame.sprite.Group | None = None,
        tiled_width: int | None = None,
        tiled_height: int | None = None,
        is_passable: bool = False,
        is_animated: bool = False,
        is_on: bool | None = None,
        off_position: int = -1,
        halo_size: int = 0,
        halo_color: str = "[255, 255, 255]",
        halo_alpha: int = HALO_DEFAULT_ALPHA,
        particles: bool = False,
        particle_count: int = 0,
        element_id: str | None = None,
        target_id: str | None = None,
        activate_from_anywhere: bool = False,
        facing_direction: str | None = None,
        sfx: str = "",
        sfx_open: str = "",
        sfx_close: str = "",
        sfx_ambient: str = "",
        material: str = "",
        day_night_driven: bool = False,
        trigger_only: bool = False,
    ):
        # 1. Properties & State Initialization
        self.target_id = target_id

        self._parse_properties(
            sub_type,
            start_row,
            end_row,
            is_on,
            is_animated,
            depth,
            position,
            off_position,
            halo_size,
            halo_color,
            halo_alpha,
            particles,
            particle_count,
            activate_from_anywhere,
            sprite_sheet,
            facing_direction,
            sfx,
            sfx_open,
            sfx_close,
            sfx_ambient,
            material,
            day_night_driven,
            trigger_only,
        )

        # 2. Asset Loading
        self._load_assets(sprite_sheet, width, height)

        # 3. Physics & Layout Setup
        t_w = tiled_width if tiled_width is not None else width
        t_h = tiled_height if tiled_height is not None else height
        self._setup_physics(pos, t_w, t_h, is_passable, obstacles_group, groups, element_id)

        # Restore depth from Tiled: BaseEntity.__init__ (called inside _setup_physics via
        # super().__init__) resets self.depth = 1. We must re-apply the Tiled value here.
        self.depth = depth

        # Bridge Y-sort override: sort by rect.top instead of rect.bottom so that any
        # sprite whose rect.bottom is south of the bridge top (i.e. standing on or past
        # the bridge) renders after (in front of) the bridge sprite.
        if self.sub_type == "bridge" and self.rect:
            self.sort_y = self.rect.top

        # 4. Lighting Initialization
        self.light_mask_cache = []
        if self.halo_size > 0:
            self._setup_lighting()

        # Chest contents (populated externally by LootTable for sub_type='chest')
        self.contents: list[dict] = []

        self.image = self._get_frame(int(self.frame_index))
        logging.info(f"Spawned InteractiveEntity '{sub_type}' at {pos} (is_on={self.is_on})")

    @property
    def is_on(self) -> bool:
        if not self.day_night_driven:
            return getattr(self, "_static_is_on", False)
        # For day_night_driven with no time_system: fallback to _static_is_on (not yet updated)
        # Direct access to __time_system (name-mangled) avoids re-entering the @property getter.
        # Both self.__time_system and self._time_system are equivalent in value — this is intentional.
        if self.__time_system is None:
            return getattr(self, "_static_is_on", False)
        # For day_night_driven: return pre-computed cache (updated in update())
        return self._is_on_cache

    def _compute_is_on(self) -> bool:
        """Compute is_on state for day_night_driven entities. Called only in update()."""
        if self.light_control == "forced_on":
            return True
        if self.light_control == "forced_off":
            return False
        # "auto": follows night
        if self._time_system is None:
            return getattr(self, "_static_is_on", False)
        return self._time_system.brightness < 0.4

    @is_on.setter
    def is_on(self, value: bool) -> None:
        self._static_is_on = value

    def _parse_properties(
        self,
        sub_type,
        start_row,
        end_row,
        is_on,
        is_animated,
        depth,
        position,
        off_position,
        halo_size,
        halo_color,
        halo_alpha,
        particles,
        particle_count,
        activate_from_anywhere,
        sprite_sheet,
        facing_direction,
        sfx,
        sfx_open,
        sfx_close,
        sfx_ambient,
        material,
        day_night_driven,
        trigger_only,
    ):
        """Parse raw properties and initialize basic state."""
        self.sub_type = sub_type
        self.start_row = start_row
        self.end_row = end_row
        self.is_animated = is_animated
        self.depth = depth
        self.on_position = position
        self.off_position = off_position
        self.col_index = position

        self._parse_day_night(day_night_driven)
        self._parse_direction(facing_direction, position)
        self._parse_state(is_on, is_animated, halo_size)
        self._parse_halo(halo_size, halo_color, halo_alpha)
        self._parse_misc(
            particles,
            particle_count,
            activate_from_anywhere,
            sfx,
            sfx_open,
            sfx_close,
            sfx_ambient,
            material,
            trigger_only,
        )

    def _parse_day_night(self, day_night_driven):
        self.day_night_driven = day_night_driven
        # _is_on_cache sentinel and light_control must be set BEFORE _time_system setter fires
        # (setter calls _compute_is_on() which reads both light_control and _is_on_cache)
        self._is_on_cache: bool = False
        self.light_control = "auto" if day_night_driven else "none"
        self._time_system = None  # setter auto-refreshes cache using light_control above

    @property
    def _time_system(self):
        return self.__time_system

    @_time_system.setter
    def _time_system(self, value) -> None:
        """Auto-refresh _is_on_cache when time_system is injected — keeps tests that set
        _time_system directly (without calling update()) working correctly.
        Guard: skip refresh when value is None (init phase — _static_is_on not yet set)."""
        self.__time_system = value
        if self.day_night_driven and value is not None:
            self._is_on_cache = self._compute_is_on()

    def _parse_direction(self, facing_direction, position):
        if facing_direction:
            self.direction_str = facing_direction
        else:
            self.direction_str = self.POSITION_TO_DIR.get(position, "down")

    def _parse_state(self, is_on, is_animated, halo_size):
        if is_on and not is_animated:
            self.frame_index = float(self.end_row)
        else:
            self.frame_index = float(self.start_row)

        self.is_light_source = halo_size > 0
        if is_on is not None:
            self._static_is_on = is_on
        else:
            self._static_is_on = self.is_animated or self.is_light_source

        self._update_col_index()

        if self.is_light_source:
            self.animation_speed = ANIM_SPEED_LIGHT_SOURCE
            if self.is_animated:
                self.frame_index = random.uniform(float(self.start_row), float(self.end_row + 1))
        else:
            self.animation_speed = ANIM_SPEED_OBJECT

        self.is_animating = self.is_on and self.is_animated
        self.is_closing = False

    def _parse_halo(self, halo_size, halo_color, halo_alpha):
        self.halo_size = halo_size
        self.halo_alpha = halo_alpha
        try:
            self.halo_color = ast.literal_eval(halo_color)
        except (ValueError, SyntaxError, TypeError):
            self.halo_color = HALO_DEFAULT_COLOR

        if self.halo_size > 0:
            logging.debug(
                f"InteractiveEntity {self.sub_type} halo: alpha={self.halo_alpha}, size={self.halo_size}"
            )

        self.flicker_phase = random.uniform(0, 2 * math.pi)
        self.f_alpha = 1.0
        self.f_scale = 1.0

    def _parse_misc(
        self,
        particles,
        particle_count,
        activate_from_anywhere,
        sfx,
        sfx_open,
        sfx_close,
        sfx_ambient,
        material,
        trigger_only,
    ):
        self.particles = particles
        self.particle_count = particle_count
        self.particles_list = []
        self.activate_from_anywhere = activate_from_anywhere
        self.sfx = sfx
        self.sfx_open = sfx_open
        self.sfx_close = sfx_close
        self.sfx_ambient = sfx_ambient
        self.material = material
        self.trigger_only = trigger_only

    def _load_assets(self, sprite_sheet, width, height):
        """Load spritesheet and compute frame dimensions.

        Frame height is derived from the sheet (sheet_h // (end_row + 1)), not
        the Tiled-declared height, because spritesheets are the authoritative
        source for frame dimensions. The Tiled `height` property is used only
        as fallback when no sheet is available.
        """
        self.sprite_width = width
        self.sprite_height = height

        sheet_path = ""
        if sprite_sheet and sprite_sheet.strip():
            sheet_path = str(
                (
                    Path(__file__).parent
                    / ".."
                    / ".."
                    / ".."
                    / "assets"
                    / "images"
                    / "sprites"
                    / sprite_sheet
                ).resolve()
            )

        sheet = SpriteSheet(sheet_path) if sheet_path else None

        # Signs are invisible if they have no sprite sheet
        is_transparent = self.sub_type == "sign" and (
            not sprite_sheet or not sheet or not sheet.valid
        )

        if sheet and sheet.valid and sheet.sheet is not None:
            _, sheet_h = sheet.sheet.get_size()
            total_rows = self.end_row + 1
            # Authoritative frame height = sheet height divided by total row count.
            # This is always correct regardless of what Tiled declares as height.
            real_frame_h = sheet_h // total_rows if total_rows > 0 else height
            # Update sprite_height so _setup_physics builds the correct-sized rect.
            self.sprite_height = real_frame_h
            self.frames = sheet.load_grid_by_size(
                self.sprite_width, real_frame_h, transparent=is_transparent
            )
            self._sheet_cols = getattr(sheet, "last_cols", 4)
        else:
            real_frame_h = self.sprite_height
            # Fallback for invisible or missing sprites (like signs)
            dummy_count = INTERACTIVE_DUMMY_FRAME_COUNT
            self.frames = [
                pygame.Surface((self.sprite_width, real_frame_h), pygame.SRCALPHA)
                for _ in range(dummy_count)
            ]
            for f in self.frames:
                if pygame.display.get_surface() is not None:
                    f.convert_alpha()
                f.fill((0, 0, 0, 0))
            self._sheet_cols = INTERACTIVE_SHEET_COLS

    def _setup_physics(self, pos, t_w, t_h, is_passable, obstacles_group, groups, element_id):
        """Initialize sprite rect, world position and collision state."""
        dummy_rect = pygame.Rect(0, 0, self.sprite_width, self.sprite_height)
        dummy_rect.midbottom = (pos[0] + t_w // 2, pos[1] + t_h)

        center_pos = dummy_rect.center
        super().__init__(center_pos, groups, element_id=element_id)

        self.tiled_width = t_w
        self.tiled_height = t_h
        self.is_passable = is_passable
        self.obstacles_group = obstacles_group
        self.rect = dummy_rect
        self.pos = pygame.math.Vector2(
            self.rect.centerx, self.rect.bottom - INTERACTIVE_POS_Y_OFFSET
        )

        if self.obstacles_group is not None and self._should_start_in_obstacles():
            self.obstacles_group.add(self)

    def _should_start_in_obstacles(self) -> bool:
        """Return True if this entity must be in obstacles_group at spawn.

        bridge: never in obstacles — water tiles handle blocking when raised.
        door:   in obstacles unless already open and passable.
        other:  in obstacles only if not passable.
        """
        if self.sub_type == "bridge":
            return False
        if self.sub_type == "door":
            return not (self.is_on and self.is_passable)
        return not self.is_passable

    def _get_frame(self, row_index: int) -> pygame.Surface:
        """Get frame for current animation state."""
        cols = self._sheet_cols
        col = min(self.col_index, cols - 1)
        idx = (row_index * cols) + col
        if 0 <= idx < len(self.frames):
            return self.frames[idx]
        return self.frames[0] if self.frames else pygame.Surface((32, 32))

    def _update_col_index(self):
        """Sync col_index with current is_on state and off_position."""
        if not self.is_on and self.off_position >= 0:
            self.col_index = self.off_position
        else:
            self.col_index = self.on_position

    def _sync_walkable_override(self) -> None:
        """Register or unregister self in game.walkable_override_entities.

        An entity is a walkable override when it is passable (is_passable=True)
        and currently open (is_on=True). This lets CollisionChecker skip the
        tile walkability check beneath the entity's rect — enabling bridges and
        drawbridges to allow crossing non-walkable tiles such as water.

        Safe to call before self.game is set (entity_factory assigns it after
        __init__); in that case the call is a no-op.
        """
        game = getattr(self, "game", None)
        override_set = getattr(game, "walkable_override_entities", None)
        if override_set is None:
            return
        if self.is_passable and self.is_on:
            override_set.add(self)
        else:
            override_set.discard(self)

    def interact(self, initiator) -> str | None:
        """Toggle state or return dialogue key."""
        if self.sub_type == "sign":
            return self.element_id

        if getattr(self, "day_night_driven", False):
            if getattr(self, "light_control", "auto") == "auto":
                self.light_control = "forced_off" if self.is_on else "forced_on"
            else:
                self.light_control = "auto"
            self._update_col_index()
            logging.info(f"Light '{self.sub_type}' control -> {self.light_control}")
        else:
            if not getattr(self, "is_animating", False) or getattr(self, "is_animated", False):
                self.is_on = not self.is_on
                self._update_col_index()
                self._sync_walkable_override()
                self.is_animating = True
                if not getattr(self, "is_animated", False):
                    self.is_closing = not self.is_on
                    if self.is_closing:
                        # Closing: play animation in reverse starting from end_row
                        self.frame_index = float(self.end_row)
                logging.info(f"Object {self.sub_type} toggled to {'ON' if self.is_on else 'OFF'}")

        return None

    def restore_state(self, state: dict):
        """Restore state from WorldState."""
        if "is_on" in state:
            is_on = state["is_on"]
            self.is_on = is_on
            self._update_col_index()
            self._sync_walkable_override()
            if is_on and not getattr(self, "is_animated", False):
                self.frame_index = float(self.end_row)
            elif not is_on:
                self.frame_index = float(self.start_row)
            if self.sub_type == "bridge" and getattr(self, "obstacles_group", None) is not None:
                # Defensive: bridge must never be in obstacles_group regardless of state
                if self in self.obstacles_group:
                    self.obstacles_group.remove(self)
            elif self.sub_type == "door" and getattr(self, "obstacles_group", None) is not None:
                if is_on and getattr(self, "is_passable", False):
                    self.obstacles_group.remove(self)
                else:
                    self.obstacles_group.add(self)
        if "light_control" in state:
            self.light_control = state["light_control"]
            self._update_col_index()
        self.image = self._get_frame(int(self.frame_index))

    def update(self, dt: float, ticks_ms: int | None = None):
        """Update animation and flicker.

        Args:
            dt: Delta time in seconds.
            ticks_ms: Current pygame.time.get_ticks() value (passed from Game to avoid
                      one get_ticks() call per entity). Falls back to get_ticks() if None.
        """
        if self.day_night_driven:
            # F2: Rebuild cache first (ADR-PERF-002) — must precede any read of self.is_on in this tick
            self._is_on_cache = self._compute_is_on()
            self._update_col_index()

        # Ambient Audio
        has_ambient = bool(self.sfx_ambient)
        if has_ambient and self.game and self.game.audio_manager:  # noqa: SIM102
            if self.is_on and self.game.player:
                dist = self.pos.distance_to(self.game.player.pos)
                self.game.audio_manager.propose_ambient(self.sfx_ambient, dist)

        if self.is_on and self.halo_size > 0:
            self._update_flicker(dt, ticks_ms)
        else:
            self.f_alpha = 1.0
            self.f_scale = 1.0

        self._update_animation(dt)
        self._update_particles(dt)

    def _update_animation(self, dt: float):
        if self.is_animated:
            if self.is_on:
                self.frame_index += self.animation_speed * dt
                if self.frame_index >= self.end_row + 1:
                    self.frame_index = float(self.start_row)
            else:
                self.frame_index = float(self.start_row)
                self.is_animating = False
        elif self.is_animating:
            if self.is_closing:
                self.frame_index -= self.animation_speed * dt
                if self.frame_index <= self.start_row:
                    self.frame_index = float(self.start_row)
                    self.is_animating = False
                    if self.sub_type == "door" and self.obstacles_group:
                        self.obstacles_group.add(self)
            else:
                self.frame_index += self.animation_speed * dt
                if self.frame_index >= self.end_row:
                    self.frame_index = float(self.end_row)
                    self.is_animating = False
                    if self.sub_type == "door" and self.is_passable and self.obstacles_group:
                        self.obstacles_group.remove(self)

        self.image = self._get_frame(int(self.frame_index))

    def draw_effects(
        self, surface: pygame.Surface, cam_offset: pygame.math.Vector2, global_darkness: int
    ):
        """Draw particles and light halo effects."""
        if not self.is_on:
            return

        self._draw_particles(surface, cam_offset)
        self._draw_halo(surface, cam_offset, global_darkness)
