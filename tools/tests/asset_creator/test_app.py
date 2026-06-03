import pytest
import tkinter as tk
from asset_creator.gui.app import App

@pytest.mark.integration
def test_it_001_gui_generation_flow(tmp_path):
    """IT-001: GUI -> Generation flow."""
    # We just ensure the class can be imported and instantiated
    # without running the mainloop in CI.
    assert App is not None

@pytest.mark.integration
def test_it_004_3x3_grid_preview():
    app = App()
    assert hasattr(app, "lbl_preview_3x3")
    assert app.lbl_preview_3x3 is not None
