"""
TC-TIME-01 to TC-TIME-05: TDD tests for TimeSystem module.
All tests must be RED before implementation.
"""
import math
import pytest
from src.engine.time_system import TimeSystem, Season, WorldTime

# --- Constants ---
REAL_SECONDS_PER_GAME_HOUR = 60.0  # 1 real min = 1 game hour


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
    advance_time(ts, REAL_SECONDS_PER_GAME_HOUR)
    wt = ts.world_time
    assert wt.hour == 1
    assert wt.minute == 0
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
    advance_time(ts, REAL_SECONDS_PER_GAME_HOUR * 24)
    wt = ts.world_time
    assert wt.day == 1
    assert wt.hour == 0
    assert wt.minute == 0


# TC-TIME-02b: Large dt clamp (> 10s) — prevent time-jumps from debugger pauses
def test_update_large_dt_clamp(ts):
    # 999 seconds would be 999 game minutes = 16 hours 39 min. Clamped to 10s = 10 game minutes.
    ts.update(999.0)
    wt = ts.world_time
    # Clamped to 10 real seconds max → 10 game minutes max
    assert wt.hour == 0
    assert wt.minute == 10


# TC-TIME-03: Brightness at noon ≈ 1.0
def test_brightness_at_noon(ts):
    advance_time(ts, REAL_SECONDS_PER_GAME_HOUR * 12)  # advance to hour 12
    assert abs(ts.brightness - 1.0) < 0.01


# TC-TIME-03b: Brightness at midnight ≈ 0.0
def test_brightness_at_midnight(ts):
    # Already at hour 0 on start
    assert ts.brightness < 0.1


# TC-TIME-03c: Brightness at hour 6 (dawn) ≈ 0.5
def test_brightness_at_dawn(ts):
    advance_time(ts, REAL_SECONDS_PER_GAME_HOUR * 6)
    assert abs(ts.brightness - 0.5) < 0.05


# TC-TIME-04: Season cycles correctly
def test_season_spring(ts):
    assert ts.current_season == Season.SPRING


def test_season_summer(ts):
    # Advance 30 game days → 30 * 24 real minutes = 30*24*60 real seconds
    advance_time(ts, REAL_SECONDS_PER_GAME_HOUR * 24 * 30)
    assert ts.current_season == Season.SUMMER


def test_season_cycle_reset(ts):
    # Advance 120 game days → should cycle back to SPRING
    advance_time(ts, REAL_SECONDS_PER_GAME_HOUR * 24 * 120)
    assert ts.current_season == Season.SPRING


# TC-TIME-05: time_label formatting
def test_time_label_padded(ts):
    # 9 hours + 5 minutes = 9*60 + 5 = 545 real seconds
    advance_time(ts, 9 * 60 + 5)
    assert ts.time_label == "09:05"


def test_time_label_midnight(ts):
    assert ts.time_label == "00:00"


# TC-TIME-06: season_label matches enum
def test_season_label_spring(ts):
    assert ts.season_label == "Spring"


def test_season_label_winter(ts):
    # 90 game days = 90 * 24 * 60 real seconds
    advance_time(ts, 90 * 24 * 60)
    assert ts.season_label == "Winter"


def test_initial_hour_start():
    """TC-TIME-07: Verify TimeSystem starts at the specified hour."""
    ts_16 = TimeSystem(initial_hour=16)
    assert ts_16.world_time.hour == 16
    assert ts_16.time_label == "16:00"
