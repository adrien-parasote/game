"""
Tests unitaires pour PauseScreen.
"""

from unittest.mock import MagicMock, patch

import pygame
import pytest
from src.engine.game_events import GameEventType
from src.ui.pause_screen import PauseScreen
from src.ui.pause_screen_constants import _BUTTON_DEFAULTS


@pytest.fixture
def mock_screen():
    surf = MagicMock(spec=pygame.Surface)
    surf.get_size.return_value = (1280, 720)
    surf.get_rect.return_value = pygame.Rect(0, 0, 1280, 720)
    return surf


@pytest.fixture
def mock_save_manager():
    sm = MagicMock()
    return sm


@pytest.fixture
def pause_screen(mock_screen, mock_save_manager):
    # Mock des chargements d'assets pour éviter les accès disques
    with (
        patch("pygame.image.load") as mock_load,
        patch("pygame.font.Font") as mock_font,
        patch("src.engine.asset_manager.AssetManager") as mock_am,
    ):
        mock_surf = pygame.Surface((600, 600), pygame.SRCALPHA)
        mock_load.return_value = mock_surf

        real_surf = pygame.Surface((10, 10), pygame.SRCALPHA)
        mock_font.return_value.render.return_value = real_surf
        mock_am.return_value.get_font.return_value.render.return_value = real_surf

        ps = PauseScreen(mock_screen, mock_save_manager)
        return ps


def test_pause_screen_init(pause_screen):
    assert pause_screen._sw == 1280
    assert pause_screen._sh == 720
    assert len(pause_screen.button_rects) == len(_BUTTON_DEFAULTS)
    assert pause_screen._hovered_btn is None


def test_pause_screen_load_asset_fallback(pause_screen):
    # Tester _load_asset en forçant une erreur
    with patch("pygame.image.load", side_effect=pygame.error("Test error")):
        surf = pause_screen._load_asset("missing.png")
        assert surf.get_size() == (32, 32)


def test_pause_screen_load_cursor_fallback(pause_screen, caplog):
    """_load_cursor returns a Surface from AssetManager fallback (not necessarily 32x32)."""
    surf = pause_screen._load_cursor("assets/images/ui/missing.png")
    assert isinstance(surf, pygame.Surface)
    # AssetManager logs a warning about the missing asset
    assert any("asset not found" in rec.message.lower() for rec in caplog.records)


def test_pause_screen_load_assets_no_fallback(mock_screen, mock_save_manager):
    with (
        patch("pygame.image.load") as mock_load,
        patch("pygame.font.Font") as mock_font,
        patch("src.engine.asset_manager.AssetManager") as mock_am,
    ):
        mock_surf = pygame.Surface((32, 32), pygame.SRCALPHA)
        mock_load.return_value = mock_surf

        real_surf = pygame.Surface((10, 10), pygame.SRCALPHA)
        mock_font.return_value.render.return_value = real_surf
        mock_am.return_value.get_font.return_value.render.return_value = real_surf

        ps = PauseScreen(mock_screen, mock_save_manager)
        # Panel devrait être créé de manière algorithmique si l'image fait 32x32
        assert ps._panel.get_size() == (480, 480)


def test_pause_screen_handle_event_click_retour(pause_screen):
    event = MagicMock()
    event.type = pygame.MOUSEBUTTONDOWN
    event.button = 1
    event.pos = pause_screen.button_rects[0].center

    result = pause_screen.handle_event(event)
    assert result is not None
    assert result.type == GameEventType.GOTO_TITLE


def test_pause_screen_handle_event_click_reprendre(pause_screen):
    event = MagicMock()
    event.type = pygame.MOUSEBUTTONDOWN
    event.button = 1
    event.pos = pause_screen.button_rects[1].center

    result = pause_screen.handle_event(event)
    assert result is not None
    assert result.type == GameEventType.RESUME


@pytest.mark.tc("SAVE-I-002")
def test_pause_screen_handle_event_click_sauvegarder(pause_screen):
    event = MagicMock()
    event.type = pygame.MOUSEBUTTONDOWN
    event.button = 1
    event.pos = pause_screen.button_rects[2].center

    # Mock _save_menu on the existing instance (patch won't affect already-created attr)
    pause_screen._save_menu = MagicMock()
    result = pause_screen.handle_event(event)
    assert result is None
    assert pause_screen.state == "SAVE_MENU"
    pause_screen._save_menu.refresh.assert_called_once()



def test_pause_screen_handle_event_ignore_wrong_button(pause_screen):
    event = MagicMock()
    event.type = pygame.MOUSEBUTTONDOWN
    event.button = 3  # Right click

    result = pause_screen.handle_event(event)
    assert result is None


def test_pause_screen_update(pause_screen):
    # Tester le hover
    with patch("pygame.mouse.get_pos", return_value=pause_screen.button_rects[1].center):
        pause_screen.update(0.16)
        assert pause_screen._hovered_btn == 1

    with patch("pygame.mouse.get_pos", return_value=(0, 0)):
        pause_screen.update(0.16)
        assert pause_screen._hovered_btn is None


def test_pause_screen_notify_save(pause_screen):
    pause_screen.notify_save_result(True)
    assert pause_screen._confirm_timer == 2.0

    # Tester la diminution du timer
    with patch("pygame.mouse.get_pos", return_value=(0, 0)):
        pause_screen.update(0.5)
    assert pause_screen._confirm_timer == 1.5


def test_pause_screen_draw(pause_screen):
    # Pour atteindre _blit_engraved et tout le draw
    pause_screen._hovered_btn = 0
    pause_screen._confirm_timer = 1.0  # Afficher "Partie sauvegardée !"

    with (
        patch("pygame.mouse.get_pos", return_value=(0, 0)),
        patch("pygame.mouse.get_pressed", return_value=(False, False, False)),
    ):
        pause_screen.draw()

    assert pause_screen._screen.blit.call_count > 0


def test_pause_screen_font_fallback(mock_screen, mock_save_manager):
    # Test font fallback (OSError on Font, Exception on AssetManager)
    real_surf = pygame.Surface((10, 10), pygame.SRCALPHA)
    with (
        patch("pygame.image.load") as mock_load,
        patch("pygame.font.Font", side_effect=OSError),
        patch("pygame.font.SysFont") as mock_sysfont,
        patch("src.engine.asset_manager.AssetManager", side_effect=Exception),
        patch("src.ui.pause_screen.I18nManager") as mock_i18n,
    ):
        mock_surf = pygame.Surface((32, 32), pygame.SRCALPHA)
        mock_load.return_value = mock_surf
        mock_sysfont.return_value.render.return_value = real_surf
        mock_sysfont.return_value.get_height.return_value = 10
        mock_i18n.return_value.get.side_effect = lambda k, d: d

        ps = PauseScreen(mock_screen, mock_save_manager)
        assert mock_sysfont.call_count >= 3  # title, item, small fonts fallbacks


# ── SAVE_MENU state coverage (lines 189-200, 215-216, 230-232) ────────────────


@pytest.fixture
def pause_screen_save_menu(pause_screen):
    """PauseScreen in SAVE_MENU state with a mocked _save_menu."""
    pause_screen._save_menu = MagicMock()
    pause_screen.state = "SAVE_MENU"
    return pause_screen


def test_handle_event_escape_in_save_menu_returns_to_main(pause_screen_save_menu):
    """ESC key in SAVE_MENU state switches back to MAIN."""
    event = MagicMock()
    event.type = pygame.KEYDOWN
    event.key = pygame.K_ESCAPE
    result = pause_screen_save_menu.handle_event(event)
    assert result is None
    assert pause_screen_save_menu.state == "MAIN"


def test_handle_event_save_menu_back_click_returns_to_main(pause_screen_save_menu):
    """Back click in SAVE_MENU returns to MAIN state."""
    event = MagicMock()
    event.type = pygame.MOUSEBUTTONDOWN
    event.button = 1
    pause_screen_save_menu._save_menu.is_back_clicked.return_value = True
    pause_screen_save_menu._save_menu.get_clicked_slot.return_value = None
    result = pause_screen_save_menu.handle_event(event)
    assert result is None
    assert pause_screen_save_menu.state == "MAIN"


def test_handle_event_save_menu_slot_click_returns_save_event(pause_screen_save_menu):
    """Slot click in SAVE_MENU returns SAVE_REQUESTED GameEvent."""
    from src.engine.game_events import GameEventType

    event = MagicMock()
    event.type = pygame.MOUSEBUTTONDOWN
    event.button = 1
    pause_screen_save_menu._save_menu.is_back_clicked.return_value = False
    pause_screen_save_menu._save_menu.get_clicked_slot.return_value = 0  # slot index 0 → slot_id 1

    result = pause_screen_save_menu.handle_event(event)
    assert result is not None
    assert result.type == GameEventType.SAVE_REQUESTED
    assert result.slot_id == 1


def test_handle_event_save_menu_no_action_returns_none(pause_screen_save_menu):
    """SAVE_MENU event with no click recognized returns None."""
    event = MagicMock()
    event.type = pygame.MOUSEBUTTONDOWN
    event.button = 1
    pause_screen_save_menu._save_menu.is_back_clicked.return_value = False
    pause_screen_save_menu._save_menu.get_clicked_slot.return_value = None
    result = pause_screen_save_menu.handle_event(event)
    assert result is None


def test_update_in_save_menu_state(pause_screen_save_menu):
    """update() in SAVE_MENU delegates to save_menu.update() and returns early."""
    pause_screen_save_menu.update(0.1)
    pause_screen_save_menu._save_menu.update.assert_called_once_with(0.1)


def test_draw_in_save_menu_state(pause_screen_save_menu):
    """draw() in SAVE_MENU calls save_menu.draw() instead of panel."""
    with patch("pygame.mouse.get_pressed", return_value=(False, False, False)):
        pause_screen_save_menu.draw()
    pause_screen_save_menu._save_menu.draw.assert_called_once()


def test_on_button_click_unknown_index_returns_none(pause_screen):
    """_on_button_click with out-of-range index returns None."""
    result = pause_screen._on_button_click(99)
    assert result is None


# ── _make_halo_surface fallback (lines 154-159) ───────────────────────────────


def test_make_halo_surface_gaussian_blur_fallback(pause_screen):
    """_make_halo_surface uses offset blits when gaussian_blur is unavailable."""
    with patch("pygame.transform.gaussian_blur", side_effect=AttributeError("no blur")):
        surf = pause_screen._make_halo_surface("Test")
    assert isinstance(surf, pygame.Surface)

