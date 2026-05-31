"""
Tests for UT-005: GameHUD caches I18nManager at __init__ and does not
construct it during draw().

Spec: game/docs/specs/perf-constants-spec.md#feature-p-perf-01a--i18nmanager-cache-in-hud
"""

from unittest.mock import MagicMock, patch

import pygame
import pytest
from src.ui.hud import GameHUD


@pytest.fixture
def mock_time_system():
    ts = MagicMock()
    ts.current_season = MagicMock()
    ts.time_label = "08:00"
    world_time = MagicMock()
    world_time.day = 0
    ts.world_time = world_time
    return ts


@pytest.fixture
def hud(mock_time_system):
    with (
        patch("pygame.image.load") as mock_load,
        patch("pygame.transform.smoothscale") as mock_scale,
        patch("src.engine.asset_manager.AssetManager") as mock_am,
    ):
        surf = pygame.Surface((10, 10))
        mock_load.return_value = surf
        mock_scale.return_value = surf
        mock_am.return_value.get_font.return_value = MagicMock()
        hud = GameHUD(mock_time_system)
        return hud


# ── UT-005a: __init__ stores _i18n attribute ──────────────────────────────


def test_hud_init_stores_i18n(hud):
    """UT-005: GameHUD.__init__ must cache I18nManager as self._i18n."""
    assert hasattr(hud, "_i18n"), "_i18n attribute must be set at __init__"


# ── UT-005b: draw() does NOT construct a new I18nManager ─────────────────


def test_hud_draw_does_not_construct_i18n(mock_time_system):
    """UT-005: draw() must reuse self._i18n, never call I18nManager()."""
    with (
        patch("pygame.image.load") as mock_load,
        patch("pygame.transform.smoothscale") as mock_scale,
        patch("src.engine.asset_manager.AssetManager") as mock_am,
        patch("src.ui.hud.I18nManager") as mock_i18n_cls,
    ):
        surf = pygame.Surface((10, 10))
        mock_load.return_value = surf
        mock_scale.return_value = surf
        mock_am.return_value.get_font.return_value = MagicMock()
        mock_i18n_cls.return_value.get.return_value = "Day"

        hud = GameHUD(mock_time_system)
        # Record call count after __init__
        calls_after_init = mock_i18n_cls.call_count

        screen = MagicMock()
        screen.get_width.return_value = 1280
        hud._season_surfs = {mock_time_system.current_season: surf}

        hud.draw(screen)

        # No additional constructions must have occurred in draw()
        assert mock_i18n_cls.call_count == calls_after_init, (
            "I18nManager() must not be constructed inside draw(). "
            "Use self._i18n cached at __init__."
        )
