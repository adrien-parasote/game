"""
Tests for asset_convertor.__main__.

Covers:
  - main() function calls App() and app.mainloop()
  - __main__ guard line (import coverage)

Strategy: mock both App and mainloop so no Tk window is opened.
"""
from __future__ import annotations

import importlib
import sys
from unittest.mock import MagicMock, patch


def test_main_creates_and_runs_app():
    """main() must instantiate App and call mainloop() exactly once."""
    fake_app = MagicMock()

    with (
        patch("asset_convertor.gui.app.App", return_value=fake_app) as mock_app_cls,
        patch.object(fake_app, "mainloop", return_value=None) as mock_loop,
    ):
        from asset_convertor.__main__ import main
        main()

    mock_app_cls.assert_called_once()
    mock_loop.assert_called_once()


def test_main_module_guard():
    """Importing __main__ under __name__ != '__main__' must not call mainloop."""
    fake_app = MagicMock()

    with (
        patch("asset_convertor.gui.app.App", return_value=fake_app),
        patch.object(fake_app, "mainloop", return_value=None) as mock_loop,
    ):
        # Force reimport to run module-level code with __name__ != '__main__'
        if "asset_convertor.__main__" in sys.modules:
            del sys.modules["asset_convertor.__main__"]
        importlib.import_module("asset_convertor.__main__")

    mock_loop.assert_not_called()
