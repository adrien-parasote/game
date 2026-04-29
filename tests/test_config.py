import pytest
from src.config import Settings

def test_settings_load():
    """Verify settings load defaults and handles missing files."""
    Settings.load()
    assert Settings.VERSION != ""
    assert Settings.WINDOW_WIDTH > 0
    assert Settings.TILE_SIZE == 32

def test_font_tiers_exist():
    """Verify the three font tiers are defined in settings."""
    assert hasattr(Settings, "FONT_NOBLE")
    assert hasattr(Settings, "FONT_NARRATIVE")
    assert hasattr(Settings, "FONT_TECH")
    
    assert "metamorphous" in Settings.FONT_NOBLE.lower()
    assert "vcr_osd" in Settings.FONT_NARRATIVE.lower()
    assert "m5x7" in Settings.FONT_TECH.lower()
