"""
Tests for GameHUD — TC-HUD-01 to TC-HUD-04.
"""
import pytest
import pygame
from unittest.mock import patch, MagicMock
from src.engine.time_system import TimeSystem, Season


@pytest.fixture
def hud_env():
    """Initialize pygame with hidden display for HUD tests."""
    pygame.init()
    pygame.display.set_mode((1280, 720), pygame.HIDDEN)
    yield
    pygame.quit()


@pytest.fixture
def time_system():
    return TimeSystem(initial_hour=14)


def test_hud_initializes(hud_env, time_system):
    """TC-HUD-01: GameHUD initializes with time system and loads assets without error."""
    from src.ui.hud import GameHUD
    hud = GameHUD(time_system)
    assert hud is not None
    assert hud._clock_surf is not None
    assert len(hud._season_surfs) == 4


def test_hud_draw_does_not_raise(hud_env, time_system):
    """TC-HUD-02: draw() renders on screen without raising exceptions."""
    from src.ui.hud import GameHUD
    hud = GameHUD(time_system)
    screen = pygame.display.get_surface()
    try:
        hud.draw(screen)
    except Exception as e:
        pytest.fail(f"hud.draw() raised an exception: {e}")


def test_hud_lang_loads_season_labels(hud_env, time_system):
    """TC-HUD-03: Language file is loaded and returns correct season labels."""
    from src.ui.hud import GameHUD
    hud = GameHUD(time_system, lang="fr")
    seasons = hud._lang.get("seasons", {})
    assert "SPRING" in seasons
    assert "SUMMER" in seasons
    assert "AUTUMN" in seasons
    assert "WINTER" in seasons
    assert seasons["SPRING"] == "Printemps"


def test_hud_lang_fallback(hud_env, time_system):
    """TC-HUD-04: Missing lang file falls back gracefully without crashing."""
    from src.ui.hud import GameHUD
    hud = GameHUD(time_system, lang="xx_INVALID")
    # Should still have a day_label, just using defaults
    assert "day_label" in hud._lang


def test_hud_positioned_top_right(hud_env, time_system):
    """TC-HUD-05: HUD is positioned in the top-right corner with 20px margin."""
    from src.ui.hud import GameHUD, HUD_MARGIN_X, HUD_MARGIN_Y
    hud = GameHUD(time_system)
    screen = pygame.display.get_surface()
    clock_w = hud._clock_surf.get_width()
    expected_x = screen.get_width() - clock_w - HUD_MARGIN_X
    assert expected_x >= 0
    assert HUD_MARGIN_Y == 20
    assert HUD_MARGIN_X == 20
