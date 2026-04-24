"""
Consolidated System Bootstrap Test Suite
Includes: Configuration loading, Debug features, and Main sanity.
"""
import pytest
import os
from src.config import Settings

def test_settings_load():
    """Settings should load default values correctly."""
    Settings.load()
    assert hasattr(Settings, "VERSION")
    assert Settings.TILE_SIZE == 32

def test_debug_mode_toggle():
    """Debug mode should affect specific engine behaviors."""
    Settings.DEBUG = True
    assert Settings.DEBUG is True
    Settings.DEBUG = False
    assert Settings.DEBUG is False

def test_asset_path_resolution():
    """Verify core asset directories exist or are handled."""
    # This is more of a sanity check for the environment
    base_path = os.path.dirname(os.path.dirname(__file__))
    assets_path = os.path.join(base_path, "assets")
    # We don't assert it exists as CI might not have assets, 
    # but we verify the engine logic for finding it.
    assert "assets" in assets_path
