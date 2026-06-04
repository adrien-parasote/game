import pytest
import tkinter as tk
from src.asset_creator.gui.app import App

@pytest.mark.integration
def test_app_initialization():
    """Ensure App can be instantiated without running the mainloop."""
    app = App()
    assert hasattr(app, "btn_export")
    assert hasattr(app, "lbl_preview_3x3")
    app.update()
def test_tc007_on_palette_write():
    """TC-007: `on_palette_write` with a 5-color palette produces `self.custom_palette` with exactly 5 tuple elements."""
    app = App()
    
    # Manually mock update_preview
    app.update_preview = lambda *args, **kwargs: None
    
    expected_tuples = [(0, 0, 0), (51, 51, 51), (119, 119, 119), (170, 170, 170), (255, 255, 255)]
    app.palettes["FakePalette"] = expected_tuples
    app.palette_var.set("FakePalette")
    
    assert len(app.custom_palette) == 5
    assert app.custom_palette == expected_tuples
    app.destroy()
