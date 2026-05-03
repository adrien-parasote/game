"""
Tests unitaires pour PauseScreen.
"""
import pytest
import pygame
from unittest.mock import MagicMock, patch

from src.ui.pause_screen import PauseScreen
from src.engine.game_events import GameEvent, GameEventType
from src.ui.pause_screen_constants import PANEL_W, PANEL_H, _BUTTON_DEFAULTS

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
    with patch("pygame.image.load") as mock_load, \
         patch("pygame.font.Font") as mock_font, \
         patch("src.engine.asset_manager.AssetManager") as mock_am:
         
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
        
def test_pause_screen_load_cursor_fallback(pause_screen):
    # Tester _load_cursor en forçant une erreur
    with patch("pygame.image.load", side_effect=pygame.error("Test error")):
        surf = pause_screen._load_cursor("missing.png")
        assert surf.get_size() == (32, 32)

def test_pause_screen_load_assets_no_fallback(mock_screen, mock_save_manager):
    with patch("pygame.image.load") as mock_load, \
         patch("pygame.font.Font") as mock_font, \
         patch("src.engine.asset_manager.AssetManager") as mock_am:
         
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

@pytest.mark.tc("IT-002")
def test_pause_screen_handle_event_click_sauvegarder(pause_screen):
    event = MagicMock()
    event.type = pygame.MOUSEBUTTONDOWN
    event.button = 1
    event.pos = pause_screen.button_rects[2].center
    
    result = pause_screen.handle_event(event)
    assert result is None
    assert pause_screen.state == "SAVE_MENU"

def test_pause_screen_handle_event_ignore_wrong_button(pause_screen):
    event = MagicMock()
    event.type = pygame.MOUSEBUTTONDOWN
    event.button = 3 # Right click
    
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
    pause_screen._confirm_timer = 1.0 # Afficher "Partie sauvegardée !"
    
    with patch("pygame.mouse.get_pos", return_value=(0, 0)), \
         patch("pygame.mouse.get_pressed", return_value=(False, False, False)):
        pause_screen.draw()
        
    assert pause_screen._screen.blit.call_count > 0

def test_pause_screen_font_fallback(mock_screen, mock_save_manager):
    # Tester le fallback des polices (OSError et Exception sur AssetManager)
    with patch("pygame.image.load") as mock_load, \
         patch("pygame.font.Font", side_effect=OSError), \
         patch("pygame.font.SysFont") as mock_sysfont, \
         patch("src.engine.asset_manager.AssetManager", side_effect=Exception):
         
        mock_surf = pygame.Surface((32, 32), pygame.SRCALPHA)
        mock_load.return_value = mock_surf
        
        ps = PauseScreen(mock_screen, mock_save_manager)
        assert mock_sysfont.call_count >= 3 # title, item, small fonts fallbacks
