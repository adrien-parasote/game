"""
Tests for the new autotile converter GUI (asset_convertor.gui.app.App).

Replaces old procedural generator GUI tests which tested
lbl_preview_3x3, palettes, etc. — no longer valid after the
app.py replacement documented in autotile_converter_spec.md.
"""

import pytest
from asset_convertor.gui.app import App, AppState


@pytest.mark.integration
def test_app_initialization():
    """Ensure the new App can be instantiated and has its 3-panel attributes."""
    app = App()
    assert hasattr(app, "btn_export")
    assert hasattr(app, "btn_convert")
    assert hasattr(app, "btn_open")
    assert hasattr(app, "lbl_source")
    assert hasattr(app, "lbl_output")
    assert hasattr(app, "canvas")
    app.update()
    app.destroy()


@pytest.mark.unit
def test_app_state_defaults():
    """AppState initializes with expected defaults."""
    state = AppState()
    assert state.source_path is None
    assert state.source_img is None
    assert state.mode == "MV"
    assert state.tiles is None
    assert state.tile_size == 32
    assert state.output_dir is not None


@pytest.mark.unit
def test_validate_dimensions_xp_valid():
    """XP validation: 96x128 -> no error."""
    from PIL import Image
    app = App()
    img = Image.new("RGBA", (96, 128))
    result = app._validate_dimensions(img, "XP")
    assert result is None
    app.destroy()


@pytest.mark.unit
def test_validate_dimensions_xp_invalid():
    """XP validation: wrong size → error message in French."""
    from PIL import Image
    app = App()
    img = Image.new("RGBA", (64, 64))
    result = app._validate_dimensions(img, "XP")
    assert result is not None
    assert "XP" in result
    assert "96" in result
    app.destroy()


@pytest.mark.unit
def test_validate_dimensions_mv_valid_32px():
    """MV validation: 64x96 -> no error."""
    from PIL import Image
    app = App()
    img = Image.new("RGBA", (64, 96))
    result = app._validate_dimensions(img, "MV")
    assert result is None
    app.destroy()


@pytest.mark.unit
def test_validate_dimensions_mv_valid_48px():
    """MV validation: 96x144 -> no error."""
    from PIL import Image
    app = App()
    img = Image.new("RGBA", (96, 144))
    result = app._validate_dimensions(img, "MV")
    assert result is None
    app.destroy()
