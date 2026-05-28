"""
RED tests for the performance & constants hardening spec.

Covers:
  UT-001 — PauseScreen pre-renders _rendered_idle at __init__
  UT-002 — PauseScreen.draw() blits pre-rendered surface, no new Surface alloc
  UT-003 — _make_halo_surface() works when gaussian_blur raises AttributeError

Spec: docs/game/specs/perf-constants-spec.md#feature-p-perf-01c--pre-render-pause-menu-items
"""
from unittest.mock import MagicMock, patch

import pygame
import pytest

from src.ui.pause_screen import PauseScreen
from src.ui.pause_screen_constants import _BUTTON_DEFAULTS


@pytest.fixture
def _surfaces():
    """Return a real 10×10 Surface for mock renders."""
    pygame.font.init()
    return pygame.Surface((10, 10), pygame.SRCALPHA)


@pytest.fixture
def pause_screen(_surfaces):
    with (
        patch("pygame.image.load") as mock_load,
        patch("pygame.font.Font") as mock_font,
        patch("src.engine.asset_manager.AssetManager") as mock_am,
        patch("src.ui.pause_screen.I18nManager") as mock_i18n,
    ):
        mock_load.return_value = pygame.Surface((600, 600), pygame.SRCALPHA)
        mock_font.return_value.render.return_value = _surfaces
        mock_font.return_value.get_height.return_value = 10
        mock_font.return_value.get_width.return_value = 80
        mock_am.return_value.get_font.return_value = mock_font.return_value
        mock_i18n.return_value.get.side_effect = lambda k, d: d

        screen = MagicMock(spec=pygame.Surface)
        screen.get_size.return_value = (1280, 720)
        sm = MagicMock()
        ps = PauseScreen(screen, sm)
        return ps


# ── UT-001 ─────────────────────────────────────────────────────────────────

def test_pause_screen_has_pre_rendered_idle(pause_screen):
    """UT-001: _rendered_idle must be populated at __init__ with len == button count."""
    assert hasattr(pause_screen, "_rendered_idle"), (
        "PauseScreen must have _rendered_idle list pre-rendered at __init__"
    )
    assert len(pause_screen._rendered_idle) == len(_BUTTON_DEFAULTS), (
        f"Expected {len(_BUTTON_DEFAULTS)} pre-rendered idle surfaces, "
        f"got {len(pause_screen._rendered_idle)}"
    )
    for surf in pause_screen._rendered_idle:
        assert isinstance(surf, pygame.Surface), (
            "Each _rendered_idle entry must be a pygame.Surface"
        )


def test_pause_screen_has_pre_rendered_hover(pause_screen):
    """UT-001 (hover): _rendered_hover must be populated at __init__."""
    assert hasattr(pause_screen, "_rendered_hover"), (
        "PauseScreen must have _rendered_hover list pre-rendered at __init__"
    )
    assert len(pause_screen._rendered_hover) == len(_BUTTON_DEFAULTS)
    for surf in pause_screen._rendered_hover:
        assert isinstance(surf, pygame.Surface)


# ── UT-002 ─────────────────────────────────────────────────────────────────

def test_pause_screen_draw_uses_cached_surfaces(pause_screen):
    """UT-002: draw() must blit pre-rendered surfaces — no new Surface alloc."""
    pause_screen._hovered_btn = 0

    with (
        patch("pygame.Surface") as mock_surf_cls,
        patch("pygame.mouse.get_pos", return_value=(0, 0)),
        patch("pygame.mouse.get_pressed", return_value=(False, False, False)),
    ):
        # Capture Surface() calls happening INSIDE draw (not at module level)
        mock_surf_cls.side_effect = lambda *a, **kw: pygame.Surface(*a, **kw)
        before = mock_surf_cls.call_count
        pause_screen.draw()
        after = mock_surf_cls.call_count

    # draw() should not construct any new Surface objects
    assert after == before, (
        f"draw() called pygame.Surface() {after - before} times. "
        "All surfaces must be pre-rendered at __init__."
    )


# ── UT-003 ─────────────────────────────────────────────────────────────────

def test_make_halo_surface_fallback_when_no_gaussian_blur(_surfaces):
    """UT-003: _make_halo_surface must work even if gaussian_blur raises AttributeError."""
    pygame.font.init()

    with (
        patch("pygame.image.load") as mock_load,
        patch("pygame.font.Font") as mock_font,
        patch("src.engine.asset_manager.AssetManager") as mock_am,
        patch("src.ui.pause_screen.I18nManager") as mock_i18n,
    ):
        mock_load.return_value = pygame.Surface((600, 600), pygame.SRCALPHA)
        mock_font.return_value.render.return_value = _surfaces
        mock_font.return_value.get_height.return_value = 10
        mock_am.return_value.get_font.return_value = mock_font.return_value
        mock_i18n.return_value.get.side_effect = lambda k, d: d

        screen = MagicMock(spec=pygame.Surface)
        screen.get_size.return_value = (1280, 720)

        # Patch gaussian_blur to raise AttributeError (standard pygame, not CE)
        with patch("pygame.transform.gaussian_blur", side_effect=AttributeError):
            ps = PauseScreen(screen, MagicMock())

        # Must still have pre-rendered hover surfaces via fallback path
        assert len(ps._rendered_hover) == len(_BUTTON_DEFAULTS)
        for surf in ps._rendered_hover:
            assert isinstance(surf, pygame.Surface)
