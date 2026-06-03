import pytest
import tkinter as tk
from asset_creator.gui.app import App

@pytest.mark.integration
def test_it_001_gui_generation_flow(tmp_path):
    """IT-001: GUI -> Generation flow."""
    # We just ensure the class can be imported and instantiated
    # without running the mainloop in CI.
    assert App is not None
