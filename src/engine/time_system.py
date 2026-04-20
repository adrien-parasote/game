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
MAX_DT_CLAMP: float = 10.0                 # Clamp large dt gaps (debugger pauses)
MAX_NIGHT_ALPHA: int = 180                 # 70% opacity max at midnight


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
    hour: int    # 0–23
    minute: int  # 0–59
    day: int     # 0–N total days elapsed


class TimeSystem:
    """
    Tracks the in-game world clock, brightness and season.

    Usage:
        ts = TimeSystem()
        # In game loop:
        ts.update(dt)
        brightness = ts.brightness
        label      = ts.time_label
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
            Settings.INITIAL_SEASON * Settings.DAYS_PER_SEASON * GAME_HOURS_PER_DAY * GAME_MINUTES_PER_HOUR
        ) + (safe_hour * GAME_MINUTES_PER_HOUR)
        
        self._total_minutes: float = float(initial_minutes)

    def update(self, dt: float) -> None:
        """Advance world time by `dt` real seconds. Guards against negative / huge jumps."""
        if dt <= 0:
            return
        dt = min(dt, MAX_DT_CLAMP)
        # 1 real second = (1 / MINUTE_DURATION) game minutes
        self._total_minutes += dt / Settings.MINUTE_DURATION

    # ------------------------------------------------------------------
    # Derived state (computed from _total_minutes)
    # ------------------------------------------------------------------

    @property
    def world_time(self) -> WorldTime:
        """Current immutable time snapshot."""
        total_minutes_int = int(self._total_minutes)
        minute = total_minutes_int % GAME_MINUTES_PER_HOUR
        total_hours = total_minutes_int // GAME_MINUTES_PER_HOUR
        hour = total_hours % GAME_HOURS_PER_DAY
        day = total_hours // GAME_HOURS_PER_DAY
        return WorldTime(hour=hour, minute=minute, day=day)

    @property
    def brightness(self) -> float:
        """
        Sinusoidal day/night brightness factor in [0.0, 1.0].
        0.0 = full dark (midnight), 1.0 = full bright (noon).

        Formula: 0.5 + 0.5 * sin(2π * hour/24 - π/2)
        """
        wt = self.world_time
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
