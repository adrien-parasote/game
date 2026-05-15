import pygame
import pytest
from unittest.mock import MagicMock, patch
from src.ui.save_menu import SaveMenuOverlay

@pytest.fixture
def mock_screen():
    surf = MagicMock(spec=pygame.Surface)
    surf.get_size.return_value = (1280, 720)
    return surf

@pytest.fixture
def mock_save_manager():
    sm = MagicMock()
    sm.list_slots.return_value = [None, None, None]
    return sm

def test_save_menu_load_assets_error_fallback(mock_screen, mock_save_manager):
    """Test fallback when back icon image fails to load."""
    with patch("pygame.image.load", side_effect=pygame.error("Simulated load error")):
        # We need to bypass compute_layout or mock objects it uses
        with patch("src.ui.save_menu.SaveMenuOverlay._compute_layout"):
            overlay = SaveMenuOverlay(mock_screen, mock_save_manager, "Test Title")
            
            assert overlay._back_btn_icon is not None
            assert overlay._back_btn_icon.get_size() == (28, 25) # BACK_ICON_W/H defaults
            assert overlay._back_btn_icon_hover.get_size() == (32, 29)

def test_save_menu_refresh_with_missing_small_font(mock_screen, mock_save_manager):
    """Test refresh when _font_small is missing (coverage for L206, 217)."""
    sm = mock_save_manager
    from src.engine.save_manager import SlotInfo
    sm.list_slots.return_value = [
        SlotInfo(1, "2026-05-15", 3600.0, "map", "Map Display", "Hero", 5),
        None,
        None
    ]
    
    with patch("src.ui.save_menu.SaveMenuOverlay._compute_layout"):
        overlay = SaveMenuOverlay(mock_screen, sm, "Title")
        # Ensure _font_small is NOT present
        if hasattr(overlay, "_font_small"):
            delattr(overlay, "_font_small")
            
        overlay.refresh()
        assert overlay._cached_level_surfs[0] is None
        assert overlay._cached_time_surfs[0] is None
