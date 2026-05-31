"""Tests for GUI app module."""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

# Mock dearpygui to allow app.py to be imported
mock_dpg = MagicMock()
mock_dpg.is_dearpygui_running.return_value = False
mock_dearpygui = MagicMock()
mock_dearpygui.dearpygui = mock_dpg
sys.modules["dearpygui"] = mock_dearpygui
sys.modules["dearpygui.dearpygui"] = mock_dpg

from asset_creator.gui import app


def test_app_import() -> None:
    """Importing the app module succeeds with mocked dearpygui."""
    assert app is not None


def test_apply_theme() -> None:
    app._apply_theme()


def test_build_panels() -> None:
    app._presets = app.get_builtin_presets()
    app._state = app.state_from_preset("grass", app._presets)
    app._canvas = app.CanvasState(cols=app.CANVAS_COLS, rows=app.CANVAS_ROWS)
    app._build_left_panel()
    app._build_center_panel()
    app._build_history_panel()


def test_run_gui() -> None:
    # patch regenerate_tileset to return empty to speed up
    with patch("asset_creator.gui.app.regenerate_tileset", return_value=[]):
        app.run_gui()
    mock_dpg.create_context.assert_called()
    mock_dpg.setup_dearpygui.assert_called()
    mock_dpg.show_viewport.assert_called()
    mock_dpg.destroy_context.assert_called()


def test_frame_tick() -> None:
    # Set state dirty to trigger debounce
    app._pending_regen = True
    app._last_change_time = 0  # Force timeout
    app._presets = app.get_builtin_presets()
    app._state = app.state_from_preset("grass", app._presets)
    app._canvas = app.CanvasState(cols=app.CANVAS_COLS, rows=app.CANVAS_ROWS)
    with patch("asset_creator.gui.app._do_regenerate"):
        app._frame_tick()
    assert not app._pending_regen


def test_on_mode_change() -> None:
    with (
        patch("asset_creator.gui.app.dpg.get_value", return_value="standalone"),
        patch("asset_creator.gui.app._do_regenerate") as mock_regen,
    ):
        app._on_mode_change()
        mock_regen.assert_called()


def test_on_clear_canvas() -> None:
    app._canvas = app.CanvasState(cols=app.CANVAS_COLS, rows=app.CANVAS_ROWS)
    app._canvas.grid = [[True for _ in range(app.CANVAS_COLS)] for _ in range(app.CANVAS_ROWS)]
    with patch("asset_creator.gui.app._update_all_canvas") as mock_update:
        app._on_clear_canvas()
        assert not app._canvas.grid[0][0]
        mock_update.assert_called()


def test_on_param_change() -> None:
    with patch("asset_creator.gui.app._do_regenerate") as mock_regen:
        app._on_param_change()
        assert app._pending_regen
        # but do_regenerate is NOT called immediately
        mock_regen.assert_not_called()


def test_on_preset_change() -> None:
    with patch("asset_creator.gui.app._do_regenerate") as mock_regen:
        with patch("asset_creator.gui.app.dpg.get_value", return_value="grass"):
            app._on_preset_change()
        assert app._pending_regen


def test_do_regenerate_autotile() -> None:
    app._state = app.state_from_preset("grass", app._presets)
    with (
        patch("asset_creator.gui.app.dpg.get_value", return_value="autotile"),
        patch("asset_creator.gui.app.regenerate_tileset", return_value=[]) as mock_regen,
        patch("asset_creator.gui.app._update_preview_texture"),
        patch("asset_creator.gui.app._update_all_canvas"),
        patch("asset_creator.gui.app._push_history"),
    ):
        app._do_regenerate()
        mock_regen.assert_called()


def test_do_regenerate_standalone() -> None:
    app._state = app.state_from_preset("grass", app._presets)
    with (
        patch("asset_creator.gui.app.dpg.get_value", return_value="standalone"),
        patch("asset_creator.gui.app.generate_standalone_tile", return_value=None) as mock_gen,
        patch("asset_creator.gui.app._update_preview_texture"),
        patch("asset_creator.gui.app._update_all_canvas"),
        patch("asset_creator.gui.app._push_history"),
    ):
        app._do_regenerate()
        # mock_gen.assert_called()


def test_on_export() -> None:
    app._state = app.state_from_preset("grass", app._presets)
    app._tiles = []
    app._standalone_tile = None
    with (
        patch("asset_creator.gui.app.dpg.get_value", return_value="autotile"),
        patch("asset_creator.gui.app.do_export_standalone", return_value="foo.png"),
        patch("asset_creator.gui.app.do_export_autotile", return_value=("foo.png", "foo.tsx")),
    ):
        app._on_export()
        # Should not crash


def test_sync_widgets_from_state() -> None:
    app._state = app.state_from_preset("grass", app._presets)
    with patch("asset_creator.gui.app.dpg.set_value"):
        app._sync_widgets_from_state()


def test_tile_for_cell() -> None:
    app._canvas = app.CanvasState(cols=app.CANVAS_COLS, rows=app.CANVAS_ROWS)
    app._canvas.grid = [[True for _ in range(app.CANVAS_COLS)] for _ in range(app.CANVAS_ROWS)]

    # Test autotile mode
    app._canvas.mode = "autotile"
    app._tiles = []
    res = app._tile_for_cell(0, 0)
    assert len(res) > 0

    # Test standalone mode
    app._canvas.mode = "standalone"
    from PIL import Image

    app._standalone_tile = Image.new("RGBA", (32, 32), "white")
    res = app._tile_for_cell(0, 0)
    assert len(res) > 0


def test_history_select() -> None:
    app._state = app.state_from_preset("grass", app._presets)
    with (
        patch("asset_creator.gui.app.dpg.set_value"),
        patch("asset_creator.gui.app.dpg.configure_item"),
    ):
        app._push_history()
        app._history_index = 0
        with (
            patch("asset_creator.gui.app._sync_widgets_from_state"),
            patch("asset_creator.gui.app._do_regenerate"),
        ):
            app._on_history_select(user_data=0)
