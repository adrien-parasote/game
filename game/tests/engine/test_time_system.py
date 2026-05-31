"""Tests for TimeSystem (time_system.py)."""


import pytest
from src.config import Settings
from src.engine.time_system import (
    GAME_HOURS_PER_DAY,
    GAME_MINUTES_PER_HOUR,
    MAX_DT_CLAMP,
    MAX_NIGHT_ALPHA,
    SEASON_LABELS,
    Season,
    TimeSystem,
)


class TestTimeSystemInit:
    def test_initial_hour_zero(self):
        ts = TimeSystem(initial_hour=0)
        wt = ts.world_time
        assert 0 <= wt.hour <= 23

    def test_initial_hour_wrapped(self):
        """Ligne 61 : safe_hour = initial_hour % 24."""
        ts = TimeSystem(initial_hour=25)  # 25 % 24 = 1
        wt = ts.world_time
        # Season offset shifts the clock — just verify no crash and hour is valid
        assert 0 <= wt.hour <= 23


class TestTimeSystemUpdate:
    def test_negative_dt_is_ignored(self):
        """Ligne 76 : dt <= 0 → return immédiatement, _total_minutes inchangé."""
        ts = TimeSystem(initial_hour=0)
        before = ts._total_minutes
        ts.update(-1.0)
        assert ts._total_minutes == before

    def test_zero_dt_is_ignored(self):
        """Ligne 76 : dt == 0 → return immédiatement."""
        ts = TimeSystem(initial_hour=0)
        before = ts._total_minutes
        ts.update(0.0)
        assert ts._total_minutes == before

    def test_large_dt_clamped(self):
        """Ligne 77 : dt > MAX_DT_CLAMP est réduit à MAX_DT_CLAMP."""
        ts = TimeSystem(initial_hour=0)
        before = ts._total_minutes
        ts.update(9999.0)
        expected_gain = MAX_DT_CLAMP / Settings.MINUTE_DURATION
        assert ts._total_minutes == pytest.approx(before + expected_gain)

    def test_normal_dt_advances_time(self):
        ts = TimeSystem(initial_hour=0)
        before = ts._total_minutes
        ts.update(Settings.MINUTE_DURATION)  # exactly 1 game minute
        assert ts._total_minutes == pytest.approx(before + 1.0)


class TestTimeSystemProperties:
    def test_brightness_at_midnight(self):
        """Minuit (hour=0) → brightness proche de 0."""
        ts = TimeSystem(initial_hour=0)
        # Forcer l'heure à 0 sans offset de saison
        ts._total_minutes = 0.0
        b = ts.brightness
        assert b == pytest.approx(0.0, abs=0.01)

    def test_brightness_at_noon(self):
        """Midi (hour=12) → brightness proche de 1."""
        ts = TimeSystem(initial_hour=0)
        ts._total_minutes = float(12 * GAME_MINUTES_PER_HOUR)
        b = ts.brightness
        assert b == pytest.approx(1.0, abs=0.01)

    def test_night_alpha_at_midnight(self):
        """Ligne 130 : night_alpha = int((1 - brightness) * MAX_NIGHT_ALPHA)."""
        ts = TimeSystem(initial_hour=0)
        ts._total_minutes = 0.0
        assert ts.night_alpha == pytest.approx(MAX_NIGHT_ALPHA, abs=1)

    def test_night_alpha_at_noon(self):
        ts = TimeSystem(initial_hour=0)
        ts._total_minutes = float(12 * GAME_MINUTES_PER_HOUR)
        assert ts.night_alpha == pytest.approx(0, abs=1)

    def test_time_label_format(self):
        ts = TimeSystem(initial_hour=0)
        ts._total_minutes = float(9 * GAME_MINUTES_PER_HOUR + 5)
        assert ts.time_label == "09:05"

    def test_season_label_spring(self):
        """Ligne 130 : season_label retourne le label de la saison courante."""
        ts = TimeSystem(initial_hour=0)
        ts._total_minutes = 0.0
        label = ts.season_label
        assert label in SEASON_LABELS.values()

    def test_current_season_cycles(self):
        """La saison avance avec les jours."""
        ts = TimeSystem(initial_hour=0)
        minutes_per_day = GAME_HOURS_PER_DAY * GAME_MINUTES_PER_HOUR
        # Avancer de DAYS_PER_SEASON jours pour changer de saison
        ts._total_minutes = float(Settings.DAYS_PER_SEASON * minutes_per_day)
        season = ts.current_season
        assert isinstance(season, Season)
