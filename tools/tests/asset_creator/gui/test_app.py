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
    app.destroy()
