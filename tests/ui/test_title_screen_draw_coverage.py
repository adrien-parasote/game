import pygame
import pytest
from unittest.mock import MagicMock, patch
from src.ui.title_screen_draw import TitleDrawMixin
from src.ui.title_screen_lights import TitleLightsMixin

class MockTitleScreen(TitleDrawMixin, TitleLightsMixin):
    def __init__(self):
        # Using a mock for screen, but we must mock all drawing functions that use it
        self._screen = MagicMock(spec=pygame.Surface)
        self._menu_item_font = MagicMock(spec=pygame.font.Font)
        self._back_label_font = MagicMock(spec=pygame.font.Font)
        
        # Use real Surface for return values to avoid blit/unpacking issues
        mock_surf = pygame.Surface((100, 30), pygame.SRCALPHA)
        self._menu_item_font.render.return_value = mock_surf
        self._menu_item_font.size.return_value = (100, 30)
        self._back_label_font.render.return_value = mock_surf
        
        # Light scales
        self._light_scale_x = 1.0
        self._light_scale_y = 1.0
        self._light_time = 0.0
        self._halo_scale_min = 0.80
        self._halo_scale_max = 1.05
        self._halo_n_buckets = 10

def test_title_draw_mixin_halo_fallback():
    """Test fallback when gaussian_blur is missing or fails (L75-76, L124-129)."""
    ts = MockTitleScreen()
    
    with patch("pygame.transform.gaussian_blur", side_effect=AttributeError):
        # Test _render_halo_text
        surf = ts._render_halo_text("Test", ts._menu_item_font, (255, 255, 255), (0, 0, 0))
        assert isinstance(surf, pygame.Surface)
        
        # Test _blit_halo_text
        ts._blit_halo_text("Test", 100, 100, ts._menu_item_font, (255, 255, 255), (0, 0, 0))
        assert ts._screen.blit.called

def test_title_draw_mixin_blit_engraved_fallback():
    """Test _blit_engraved fallback (L144-151)."""
    ts = MockTitleScreen()
    ts._blit_engraved("Test", 100, 100) # Uses self._menu_item_font
    assert ts._screen.blit.call_count == 3
    
    ts._blit_engraved("Test", 100, 100, font=ts._back_label_font) # Uses explicit font
    assert ts._screen.blit.call_count == 6

def test_title_lights_mixin_debug_and_clamping():
    """Test lights mixin with HALO_DEBUG and extreme flicker clamping."""
    ts = MockTitleScreen()
    
    # Mock BACKGROUND_LIGHTS and MUSHROOM_LIGHTS to have items
    with patch("src.ui.title_screen_lights.BACKGROUND_LIGHTS", [(10, 10, 20)]), \
         patch("src.ui.title_screen_lights.MUSHROOM_LIGHTS", [(20, 20, 15, (255, 0, 0))]), \
         patch("src.ui.title_screen_lights.HALO_DEBUG", True):
        
        # Init halos first
        ts._init_light_halos()
        
        # Test background lights (L104-106)
        ts._light_time = 1000.0 # Force flicker variance
        with patch("pygame.draw.line"), patch("pygame.draw.circle"):
            ts._draw_background_lights()
            ts._draw_mushroom_lights()
        
        assert ts._screen.blit.called
