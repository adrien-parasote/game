"""
TimeSystem — Internal world clock for the RPG engine.
"""

import math
from dataclasses import dataclass
from enum import IntEnum

from src.config import Settings

# --- Constants ---
GAME_MINUTES_PER_HOUR: int = 60
GAME_HOURS_PER_DAY: int = 24
GAME_SEASONS_PER_YEAR: int = 4
MAX_DT_CLAMP: float = 10.0  # Clamp large dt gaps (debugger pauses)
MAX_NIGHT_ALPHA: int = 180  # 70% opacity max at midnight


class Season(IntEnum):
    SPRING = 0
    SUMMER = 1
    AUTUMN = 2
    WINTER = 3


SEASON_LABELS: dict = {
    Season.SPRING: "Spring",
    Season.SUMMER: "Summer",
    Season.AUTUMN: "Autumn",
    Season.WINTER: "Winter",
}


@dataclass
class WorldTime:
    """Immutable snapshot of the current in-game time."""

    hour: int  # 0–23
    minute: int  # 0–59
    day: int  # 0–N total days elapsed


class TimeSystem:
    """
    Tracks the in-game world clock, brightness and season.

    Usage:
        ts = TimeSystem()
        # In game loop:
        ts.update(dt)
        brightness = ts.brightness
        label      = ts.time_label

    Performance (ADR-PERF-001):
        WorldTime is computed exactly once per frame in update() and cached
        as _cached_world_time. All @property accessors read the cache — zero
        NamedTuple allocations outside of update().
    """

    def __init__(self, initial_hour: int = 0) -> None:
        """
        Initialize the time system.
        :param initial_hour: The in-game hour to start at (0-23).
        """
        # Ensure hour is within [0, 23]
        safe_hour = initial_hour % GAME_HOURS_PER_DAY

        # Calculate starting minutes based on initial season and hour
        initial_minutes = (
            Settings.INITIAL_SEASON
            * Settings.DAYS_PER_SEASON
            * GAME_HOURS_PER_DAY
            * GAME_MINUTES_PER_HOUR
        ) + (safe_hour * GAME_MINUTES_PER_HOUR)

        # Initialize cache sentinel before _total_minutes setter fires (setter calls _compute_world_time)
        self._cached_world_time: WorldTime = WorldTime(hour=0, minute=0, day=0)
        self._total_minutes = float(initial_minutes)  # setter auto-refreshes cache

    @property
    def _total_minutes(self) -> float:
        return self.__total_minutes

    @_total_minutes.setter
    def _total_minutes(self, value: float) -> None:
        """Auto-refresh cache on any write — keeps tests that set _total_minutes directly working."""
        self.__total_minutes = value
        self._cached_world_time = self._compute_world_time()

    def _compute_world_time(self) -> WorldTime:
        """Compute WorldTime from _total_minutes. Called by update() and the _total_minutes setter."""
        total_minutes_int = int(self._total_minutes)
        minute = total_minutes_int % GAME_MINUTES_PER_HOUR
        total_hours = total_minutes_int // GAME_MINUTES_PER_HOUR
        hour = total_hours % GAME_HOURS_PER_DAY
        day = total_hours // GAME_HOURS_PER_DAY
        return WorldTime(hour=hour, minute=minute, day=day)

    def update(self, dt: float) -> None:
        """Advance world time by `dt` real seconds. Guards against negative / huge jumps."""
        if dt <= 0:
            return
        dt = min(dt, MAX_DT_CLAMP)
        # 1 real second = (1 / MINUTE_DURATION) game minutes
        self._total_minutes += dt / Settings.MINUTE_DURATION
        # Rebuild cache exactly once per frame tick (ADR-PERF-001)
        self._cached_world_time = self._compute_world_time()

    # ------------------------------------------------------------------
    # Derived state (computed from _cached_world_time)
    # ------------------------------------------------------------------

    @property
    def world_time(self) -> WorldTime:
        """Current immutable time snapshot (cached from last update())."""
        return self._cached_world_time

    @property
    def brightness(self) -> float:
        """
        Sinusoidal day/night brightness factor in [0.0, 1.0].
        0.0 = full dark (midnight), 1.0 = full bright (noon).

        Formula: 0.5 + 0.5 * sin(2π * hour/24 - π/2)
        Reads _cached_world_time directly — no double allocation.
        """
        wt = self._cached_world_time
        fractional_hour = wt.hour + wt.minute / GAME_MINUTES_PER_HOUR
        angle = 2 * math.pi * (fractional_hour / GAME_HOURS_PER_DAY) - (math.pi / 2)
        return 0.5 + 0.5 * math.sin(angle)

    @property
    def current_season(self) -> Season:
        """Current season derived from total elapsed days."""
        day = self.world_time.day
        days_per_year = Settings.DAYS_PER_SEASON * GAME_SEASONS_PER_YEAR
        season_index = (day % days_per_year) // Settings.DAYS_PER_SEASON
        return Season(season_index)

    @property
    def night_alpha(self) -> int:
        """Overlay alpha for night darkness: 0 at noon, MAX_NIGHT_ALPHA at midnight."""
        return int((1.0 - self.brightness) * MAX_NIGHT_ALPHA)

    @property
    def time_label(self) -> str:
        """Formatted HH:MM string."""
        wt = self.world_time
        return f"{wt.hour:02d}:{wt.minute:02d}"

    @property
    def season_label(self) -> str:
        """Human-readable season name."""
        return SEASON_LABELS[self.current_season]
