"""
TC-TIME-01 to TC-TIME-05: TDD tests for TimeSystem module.
All tests must be RED before implementation.
"""
import math
import pytest
from src.config import Settings
from src.engine.time_system import TimeSystem, Season, WorldTime

# --- Helper ---
def get_seconds_per_hour() -> float:
    return Settings.MINUTE_DURATION * 60.0


@pytest.fixture
def ts() -> TimeSystem:
    """Fresh TimeSystem starting at 00:00, day 0."""
    return TimeSystem()


def advance_time(ts: TimeSystem, total_dt: float):
    """Helper to bypass the 10s clamp by updating in chunks."""
    while total_dt > 0:
        chunk = min(total_dt, 10.0)
        ts.update(chunk)
        total_dt -= chunk


# TC-TIME-01: Advance 1 real minute → 1 game hour elapsed
def test_update_one_real_minute(ts):
    # Add a tiny epsilon (0.1s) to ensure we cross the integer threshold 
    # even if there's floating point jitter from the 1.5s/min scale
    advance_time(ts, get_seconds_per_hour() + 0.1)
    wt = ts.world_time
    assert wt.hour == 1
    assert wt.day == 0


# TC-TIME-01b: dt=0 → no state change
def test_update_zero_dt_no_change(ts):
    ts.update(0.0)
    wt = ts.world_time
    assert wt.hour == 0
    assert wt.minute == 0


# TC-TIME-01c: Negative dt → no state change (guard)
def test_update_negative_dt_no_change(ts):
    ts.update(-5.0)
    wt = ts.world_time
    assert wt.hour == 0
    assert wt.minute == 0


# TC-TIME-02: Advance 24 real minutes → 1 full day elapsed, hour resets to 0
def test_update_full_day(ts):
    advance_time(ts, get_seconds_per_hour() * 24)
    wt = ts.world_time
    assert wt.day == 1
    assert wt.hour == 0
    assert wt.minute == 0


# TC-TIME-02b: Large dt clamp (> 10s) — prevent time-jumps from debugger pauses
def test_update_large_dt_clamp(ts):
    # 999 seconds clamped to MAX_DT_CLAMP (10s)
    # 10s / (Settings.MINUTE_DURATION) = game minutes
    ts.update(999.0)
    wt = ts.world_time
    expected_mins = int(10.0 / Settings.MINUTE_DURATION)
    assert wt.minute == expected_mins


# TC-TIME-03: Brightness at noon ≈ 1.0
def test_brightness_at_noon(ts):
    advance_time(ts, get_seconds_per_hour() * 12)  # advance to hour 12
    assert abs(ts.brightness - 1.0) < 0.01


# TC-TIME-03b: Brightness at midnight ≈ 0.0
def test_brightness_at_midnight(ts):
    # Already at hour 0 on start
    assert ts.brightness < 0.1


# TC-TIME-03c: Brightness at hour 6 (dawn) ≈ 0.5
def test_brightness_at_dawn(ts):
    advance_time(ts, get_seconds_per_hour() * 6)
    assert abs(ts.brightness - 0.5) < 0.05


# TC-TIME-04: Season cycles correctly
def test_season_spring(ts):
    assert ts.current_season == Season.SPRING


def test_season_summer(ts):
    # Advance 30 game days
    # Add epsilon (1 real sec) to ensure we cross the threshold
    advance_time(ts, (get_seconds_per_hour() * 24 * Settings.DAYS_PER_SEASON) + 1.0)
    assert ts.current_season == Season.SUMMER


def test_season_cycle_reset(ts):
    # Advance exactly 4 seasons
    # Use a tiny epsilon to avoid float precision issues during the long loop
    advance_time(ts, (get_seconds_per_hour() * 24 * Settings.DAYS_PER_SEASON * 4) + 1.0)
    assert ts.current_season == Season.SPRING


# TC-TIME-05: time_label formatting
def test_time_label_padded(ts):
    # 9 real hours worth of game hours + 5 game minutes
    # game_hour = Settings.MINUTE_DURATION * 60
    # game_min = Settings.MINUTE_DURATION
    advance_time(ts, 9 * (Settings.MINUTE_DURATION * 60) + 5 * Settings.MINUTE_DURATION)
    assert ts.time_label == "09:05"


def test_time_label_midnight(ts):
    assert ts.time_label == "00:00"


# TC-TIME-06: season_label matches enum
def test_season_label_spring(ts):
    assert ts.season_label == "Spring"


def test_season_label_winter(ts):
    # 3 seasons = 90 days if DAYS_PER_SEASON=30
    advance_time(ts, 3 * Settings.DAYS_PER_SEASON * 24 * get_seconds_per_hour())
    assert ts.season_label == "Winter"


def test_initial_hour_start():
    """TC-TIME-07: Verify TimeSystem starts at the specified hour."""
    ts_16 = TimeSystem(initial_hour=16)
    assert ts_16.world_time.hour == 16
    assert ts_16.time_label == "16:00"
