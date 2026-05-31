"""Tests for the main entrypoint module."""

from __future__ import annotations

import runpy
from unittest.mock import patch


@patch("sys.argv", ["asset_creator"])
def test_main_execution() -> None:
    """Executing __main__ triggers cli.main()."""
    with patch("asset_creator.cli.main") as mock_main:
        # runpy.run_module executes the module as if it were __main__
        runpy.run_module("asset_creator.__main__", run_name="__main__")
        mock_main.assert_called_once()
