import pytest
from src.config import Settings

def test_settings_load():
    """Verify settings load defaults and handles missing files."""
    Settings.load()
    assert Settings.VERSION != ""
    assert Settings.WINDOW_WIDTH > 0
    assert Settings.TILE_SIZE == 32

def test_font_centralization():
    """Verify font path is configurable and exists in settings."""
    assert hasattr(Settings, "MAIN_FONT")
    assert "Pixel.ttf" in Settings.MAIN_FONT
