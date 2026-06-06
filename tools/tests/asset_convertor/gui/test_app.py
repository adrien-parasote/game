"""
Tests for the new autotile converter GUI (asset_convertor.gui.app.App).

Replaces old procedural generator GUI tests which tested
lbl_preview_3x3, palettes, etc. — no longer valid after the
app.py replacement documented in autotile_converter_spec.md.
"""

import pytest
from asset_convertor.gui.app import App
from asset_convertor.gui.state import AppState


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
    """AppState v2 initializes with expected defaults."""
    state = AppState()
    assert state.source_path is None
    assert state.source_img is None
    assert state.format == "MV"        # renamed from .mode
    assert state.resource_type == "A2"
    assert state.tiles is None
    assert state.tile_size == 48       # v2 default is 48, not 32
    assert state.output_dir is not None


@pytest.mark.unit
def test_validate_dimensions_xp_valid():
    """XP validation: 96x128 -> no error."""
    from PIL import Image
    app = App()
    img = Image.new("RGBA", (96, 128))
    result = app._validate_dimensions(img, "A2", "XP")  # v2 signature: (img, resource_type, fmt)
    assert result is None
    app.destroy()


@pytest.mark.unit
def test_validate_dimensions_xp_invalid():
    """XP validation: wrong size → error message in French."""
    from PIL import Image
    app = App()
    img = Image.new("RGBA", (64, 64))
    result = app._validate_dimensions(img, "A2", "XP")
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
    result = app._validate_dimensions(img, "A2", "MV")
    assert result is None
    app.destroy()


@pytest.mark.unit
def test_validate_dimensions_mv_valid_48px():
    """MV validation: 96x144 -> no error."""
    from PIL import Image
    app = App()
    img = Image.new("RGBA", (96, 144))
    result = app._validate_dimensions(img, "A2", "MV")
    assert result is None
    app.destroy()


@pytest.mark.unit
def test_animation_controls_state_toggle():
    """Animation controls are enabled by default in A1 secondary toolbar context."""
    app = App()

    # Switch to A1 mode to get animation controls
    app._tiled_type_var.set("🎮 Animé")
    app._on_type_change_internal("A1")

    # By default in A1 mode, controls should be enabled (animated=True)
    assert hasattr(app, "menu_anim_type")
    assert hasattr(app, "menu_speed")
    assert app.menu_anim_type.cget("state") == "normal"
    assert app.menu_speed.cget("state") == "normal"

    app.destroy()


@pytest.mark.unit
def test_stop_animation():
    """Test that stop_animation clears timers and sequences."""
    app = App()
    app._timer_id = "after#1"
    app._current_frame_idx = 2
    app._frame_sequence = [0, 1, 2, 1]

    app._stop_animation()
    assert app._timer_id is None
    assert app._current_frame_idx == 0
    assert app._frame_sequence == [0]
    app.destroy()


@pytest.mark.unit
def test_focus_window_method_exists_and_is_callable():
    """_focus_window must exist and not crash when called.

    lift(), focus_force(), and AppKit activation are all silenced
    in headless/test mode — this test just ensures the method is present
    and doesn't raise.
    """
    from unittest.mock import patch

    app = App()
    with (
        patch.object(app, "lift"),
        patch.object(app, "focus_force"),
    ):
        app._focus_window()  # must not raise
    app.destroy()


@pytest.mark.unit
def test_zoomed_and_focus_scheduled_on_init():
    """after() calls for zoomed state and _focus_window are registered at init.

    We cannot assert the exact Tk after-ID, but we can verify that both
    callbacks are registered by checking that after() is called with the
    expected delay arguments during App.__init__.
    """
    from unittest.mock import call, patch

    with patch("customtkinter.CTk.after", return_value="after#mock") as mock_after:
        app = App()
        delays = [c.args[0] for c in mock_after.call_args_list]
        assert 0 in delays, "zoomed state must be scheduled with after(0, ...)"
        assert 50 in delays, "_focus_window must be scheduled with after(50, ...)"
        app.destroy()


@pytest.mark.unit
def test_a1_conversion_preserves_2d_tiles():
    """Test that A1 mode conversion stores a 2D list of tiles by frame in AppState."""
    import dataclasses

    from PIL import Image

    app = App()
    app._tiled_type_var.set("🎮 Animé")
    app._on_type_change_internal("A1")

    img = Image.new("RGBA", (192, 144))
    app._state = dataclasses.replace(
        app._state,
        source_img=img,
    )

    app._convert_a2()

    assert app._state.tiles is not None
    assert isinstance(app._state.tiles, list)
    assert len(app._state.tiles) == 2
    assert isinstance(app._state.tiles[0], list)
    assert len(app._state.tiles[0]) == 47

    app.destroy()



# ── A4 canvas 4-neighbor tests ──────────────────────────────────────────────


@pytest.mark.unit
def test_a4_conversion_populates_tiles_for_canvas():
    """TC-007: A4 conversion must store 16 wall-side tiles in AppState.tiles.

    After the canvas-4N refactor, _convert_a4 extracts tiles from sides_img
    (16 shapes, WALL_AUTOTILE_TABLE) instead of 47 wall-top tiles.
    """
    import dataclasses

    from PIL import Image

    app = App()
    app._tiled_type_var.set("🧱 Mur")
    app._on_type_change_internal("A4")

    # Minimum valid A4 source: 96x120 px, non-transparent
    img = Image.new("RGBA", (96, 120), color=(128, 64, 32, 255))
    app._state = dataclasses.replace(app._state, source_img=img)

    app._convert_a4()

    assert app._state.tiles is not None, "tiles must not be None after A4 conversion"
    assert isinstance(app._state.tiles, list), "tiles must be a list"
    assert len(app._state.tiles) == 16, (
        "must have 16 wall-side tiles (WALL_AUTOTILE_TABLE), got "
        f"{len(app._state.tiles)}"
    )
    assert hasattr(app._state.tiles[0], "size"), "each tile must be a PIL Image"

    app.destroy()


@pytest.mark.unit
def test_compute_wall_bitmask_4n_isolated():
    """TC-001: isolated cell (no neighbors) → bitmask 0."""
    from asset_convertor.gui.app import _compute_wall_bitmask_4n

    grid = [[False, False, False], [False, True, False], [False, False, False]]
    assert _compute_wall_bitmask_4n(grid, 1, 1) == 0


@pytest.mark.unit
def test_compute_wall_bitmask_4n_north_only():
    """TC-002: N neighbor present, others absent → bitmask 2."""
    from asset_convertor.gui.app import _compute_wall_bitmask_4n

    grid = [[False, True, False], [False, True, False], [False, False, False]]
    # cell (1,1): N=(0,1) is True → bitmask = 2
    assert _compute_wall_bitmask_4n(grid, 1, 1) == 2


@pytest.mark.unit
def test_compute_wall_bitmask_4n_all_cardinal():
    """TC-003: all four cardinal neighbors → bitmask 15."""
    from asset_convertor.gui.app import _compute_wall_bitmask_4n

    grid = [[False, True, False], [True, True, True], [False, True, False]]
    # cell (1,1): N=(0,1) S=(2,1) W=(1,0) E=(1,2) all True
    # N=2, W=8, E=4, S=1 → 2+8+4+1 = 15
    assert _compute_wall_bitmask_4n(grid, 1, 1) == 15


@pytest.mark.unit
def test_compute_wall_bitmask_4n_ignores_diagonals():
    """TC-004: diagonal neighbor present but N and W absent → bitmask 0."""
    from asset_convertor.gui.app import _compute_wall_bitmask_4n

    # Only (0,0) is True — diagonal of (1,1); N=(0,1) and W=(1,0) are False
    grid = [[True, False, False], [False, True, False], [False, False, False]]
    assert _compute_wall_bitmask_4n(grid, 1, 1) == 0


@pytest.mark.unit
def test_wall_4n_bitmask_to_idx_completeness():
    """TC-005: _WALL_4N_BITMASK_TO_IDX keys cover exactly bitmask values 0–15."""
    from asset_convertor.gui.app import _WALL_4N_BITMASK_TO_IDX

    assert set(_WALL_4N_BITMASK_TO_IDX.keys()) == set(range(16))


@pytest.mark.unit
def test_wall_4n_bitmask_to_idx_bijection():
    """TC-006: _WALL_4N_BITMASK_TO_IDX is a bijection — values also cover 0–15."""
    from asset_convertor.gui.app import _WALL_4N_BITMASK_TO_IDX

    assert set(_WALL_4N_BITMASK_TO_IDX.values()) == set(range(16))


@pytest.mark.unit
def test_wall_4n_bitmask_isolated_maps_to_shape_15():
    """TC-008: bitmask 0 (isolated, no neighbors) must map to shape 15.

    Shape 15 uses all-corner quadrants [[0,0],[3,0],[0,3],[3,3]] — all 4 open edges.
    An isolated tile shows all open edges → shape_idx=15.
    """
    from asset_convertor.gui.app import _WALL_4N_BITMASK_TO_IDX

    assert _WALL_4N_BITMASK_TO_IDX[0] == 15, (
        f"Isolated (bitmask 0) must map to shape 15, got {_WALL_4N_BITMASK_TO_IDX[0]}"
    )


@pytest.mark.unit
def test_wall_4n_bitmask_fully_surrounded_maps_to_shape_0():
    """TC-009: bitmask 15 (N+W+E+S all present) must map to shape 0.

    Shape 0 uses all-interior quadrants [[2,2],[1,2],[2,1],[1,1]] — no visible edges.
    A fully-surrounded tile has no open edges → shape_idx=0.
    """
    from asset_convertor.gui.app import _WALL_4N_BITMASK_TO_IDX

    assert _WALL_4N_BITMASK_TO_IDX[15] == 0, (
        f"Fully surrounded (bitmask 15) must map to shape 0, got {_WALL_4N_BITMASK_TO_IDX[15]}"
    )


@pytest.mark.unit
def test_wall_4n_bitmask_north_only_maps_to_shape_13():
    """TC-010: bitmask 2 (N only) must map to shape 13.

    Shape 13 [[0,2],[3,2],[0,3],[3,3]]: qsy=2/3 (bottom-half interior for N),
    qsx=0 (left open) and qsx=3 (right open) → W and E absent → N only.
    """
    from asset_convertor.gui.app import _WALL_4N_BITMASK_TO_IDX

    assert _WALL_4N_BITMASK_TO_IDX[2] == 13, (
        f"N-only (bitmask 2) must map to shape 13, got {_WALL_4N_BITMASK_TO_IDX[2]}"
    )


@pytest.mark.integration
def test_a4_conversion_canvas_tiles_count():
    """IT-001: Full A4 conversion → AppState.tiles has 16 Image objects."""
    import dataclasses

    from PIL import Image

    app = App()
    app._tiled_type_var.set("🧱 Mur")
    app._on_type_change_internal("A4")

    img = Image.new("RGBA", (96, 120), color=(100, 100, 100, 255))
    app._state = dataclasses.replace(app._state, source_img=img)
    app._convert_a4()

    tiles = app._state.tiles
    assert tiles is not None
    assert len(tiles) == 16
    for t in tiles:
        assert hasattr(t, "size"), "each tile must be a PIL Image"

    app.destroy()


@pytest.mark.integration
def test_redraw_canvas_grid_a4_uses_4n_path():
    """IT-002: _redraw_canvas_grid for A4 with 16 tiles draws without IndexError."""
    import dataclasses

    from PIL import Image

    app = App()
    app._tiled_type_var.set("🧱 Mur")
    app._on_type_change_internal("A4")

    # Inject 16 fake tiles into state
    fake_tiles: list[Image.Image] = [
        Image.new("RGBA", (48, 48), color=(i * 10, 0, 0, 255)) for i in range(16)
    ]
    app._state = dataclasses.replace(
        app._state,
        resource_type="A4",
        tiles=fake_tiles,
        tile_size=48,
    )
    # All cells filled — tests all 16 possible bitmask values
    app._canvas_grid = [[True] * 5 for _ in range(5)]

    # Must not raise
    app._redraw_canvas_grid()

    app.destroy()


# ── _scale_to_fit static helper ───────────────────────────────────────────────

@pytest.mark.unit
def test_scale_to_fit_no_scale_needed():
    """Image already smaller than max — returned as-is or up to max (scale fits)."""
    from PIL import Image
    img = Image.new("RGBA", (100, 100))
    result = App._scale_to_fit(img, 200, 200)
    # Result fits within max bounds
    assert result.width <= 200
    assert result.height <= 200


@pytest.mark.unit
def test_scale_to_fit_scales_down():
    """Large image is scaled to fit within max bounds."""
    from PIL import Image
    img = Image.new("RGBA", (400, 200))
    result = App._scale_to_fit(img, 100, 100)
    assert result.width <= 100
    assert result.height <= 100


@pytest.mark.unit
def test_build_sheet_image_flat_list():
    """_build_sheet_image wraps flat list of tiles in a single-frame sheet."""
    from PIL import Image
    tiles = [Image.new("RGBA", (48, 48), color=(i * 5, 0, 0, 255)) for i in range(47)]
    sheet = App._build_sheet_image(tiles, 48)
    assert sheet is not None
    assert sheet.width > 0


@pytest.mark.unit
def test_build_sheet_image_2d_list():
    """_build_sheet_image with 2D list of tiles produces a multi-frame sheet."""
    from PIL import Image
    frame = [Image.new("RGBA", (48, 48), color=(0, 0, 0, 255)) for _ in range(47)]
    tiles_2d = [frame, frame, frame]
    sheet = App._build_sheet_image(tiles_2d, 48)
    assert sheet.height >= 48


# ── _set_status and _log ──────────────────────────────────────────────────────

@pytest.mark.unit
def test_set_status_ok():
    """_set_status with no error sets gray text color."""
    app = App()
    app._set_status("Prêt.")
    assert "Prêt." in app.lbl_status.cget("text")
    app.destroy()


@pytest.mark.unit
def test_set_status_error():
    """_set_status with error=True uses error color."""
    app = App()
    app._set_status("Erreur !", error=True)
    assert "Erreur" in app.lbl_status.cget("text")
    app.destroy()


@pytest.mark.unit
def test_log_writes_entry():
    """_log inserts a timestamped entry into txt_log."""
    app = App()
    app._log("test message", level="INFO")
    content = app.txt_log.get("1.0", "end")
    assert "test message" in content
    app.destroy()


# ── _on_type_change — Recolor path ────────────────────────────────────────────

@pytest.mark.unit
def test_on_type_change_to_recolor():
    """Switching to Recolor mode disables TSX export and swaps panel to RecolorPanel."""
    app = App()
    app._on_type_change_internal("Recolor")
    # TSX checkbox should be disabled
    assert app.cb_export_tsx.cget("state") == "disabled"
    app.destroy()


@pytest.mark.unit
def test_on_type_change_back_to_a2():
    """Switching from Recolor back to A2 re-enables TSX export."""
    app = App()
    app._on_type_change_internal("Recolor")
    app._on_type_change_internal("A2")
    assert app.cb_export_tsx.cget("state") == "normal"
    app.destroy()


# ── _on_format_change ─────────────────────────────────────────────────────────

@pytest.mark.unit
def test_on_format_change_to_xp():
    """_on_format_change updates state.format to XP."""
    app = App()
    # Switch to A2 to get format radio buttons
    app._tiled_type_var.set("🌱 Sol")
    app._on_type_change_internal("A2")
    app._format_var.set("XP")
    app._on_format_change()
    assert app._state.format == "XP"
    app.destroy()


@pytest.mark.unit
def test_on_format_change_mz_rejected():
    """_on_format_change reverts MZ selection back to current format."""
    app = App()
    app._tiled_type_var.set("🌱 Sol")
    app._on_type_change_internal("A2")
    original_fmt = app._state.format
    app._format_var.set("MZ")
    app._on_format_change()
    assert app._state.format == original_fmt  # MZ rejected
    app.destroy()


# ── _validate_xp_dimensions — animated branches ───────────────────────────────

@pytest.mark.unit
def test_validate_xp_animated_horizontal_valid():
    """XP animated horizontal: width multiple of 96, height 128 → valid."""
    from PIL import Image
    import tkinter as tk
    app = App()
    app._animated_var = tk.BooleanVar(value=True)
    app._anim_type_var = __import__("customtkinter").StringVar(value="Horizontale (Eau/Sol)")
    result = app._validate_xp_dimensions(192, 128, is_anim=True, anim_mode="Horizontale")
    assert result is None
    app.destroy()


@pytest.mark.unit
def test_validate_xp_animated_vertical_rejected():
    """XP animated vertical is unsupported → error message."""
    app = App()
    result = app._validate_xp_dimensions(96, 128, is_anim=True, anim_mode="Verticale")
    assert result is not None
    assert "vertical" in result.lower() or "Verticale" in result
    app.destroy()


@pytest.mark.unit
def test_validate_mv_animated_horizontal_invalid_height():
    """MV animated horizontal: wrong height → error."""
    app = App()
    # Height not in (96, 144)
    result = app._validate_mv_dimensions(64, 100, is_anim=True, anim_mode="Horizontale", mode="MV")
    assert result is not None
    assert "96" in result or "144" in result
    app.destroy()


@pytest.mark.unit
def test_validate_mv_animated_horizontal_wrong_width():
    """MV animated horizontal: height=96 but width not multiple of 64 → error."""
    app = App()
    result = app._validate_mv_dimensions(70, 96, is_anim=True, anim_mode="Horizontale", mode="MV")
    assert result is not None
    app.destroy()


@pytest.mark.unit
def test_validate_mv_animated_vertical_valid():
    """MV animated vertical: width=64, height multiple of 32 → valid."""
    app = App()
    result = app._validate_mv_dimensions(64, 128, is_anim=True, anim_mode="Verticale", mode="MV")
    assert result is None
    app.destroy()


@pytest.mark.unit
def test_validate_mv_animated_vertical_bad_width():
    """MV animated vertical: width not 64 or 96 → error."""
    app = App()
    result = app._validate_mv_dimensions(50, 128, is_anim=True, anim_mode="Verticale", mode="MV")
    assert result is not None
    app.destroy()


# ── Canvas click and pattern controls ────────────────────────────────────────

@pytest.mark.unit
def test_on_canvas_click_toggles_cell():
    """Clicking on a canvas cell toggles the grid boolean."""
    import tkinter as tk
    app = App()
    # Set grid to all False, then simulate click at (0, 0)
    app._canvas_grid = [[False] * 5 for _ in range(5)]

    # Simulate a click event at pixel (0, 0) — should toggle grid[0][0]
    evt = tk.Event()
    evt.x = 0
    evt.y = 0
    app._on_canvas_click(evt)

    assert app._canvas_grid[0][0] is True
    app.destroy()


@pytest.mark.unit
def test_load_test_pattern_resets_to_default():
    """_load_test_pattern resets canvas grid to _GRID_DEFAULT."""
    from asset_convertor.gui.app import _GRID_DEFAULT
    app = App()
    app._canvas_grid = [[False] * 5 for _ in range(5)]
    app._load_test_pattern()
    assert app._canvas_grid == _GRID_DEFAULT
    app.destroy()


@pytest.mark.unit
def test_clear_canvas_grid_sets_all_false():
    """_clear_canvas_grid resets all cells to False."""
    app = App()
    app._canvas_grid = [[True] * 5 for _ in range(5)]
    app._clear_canvas_grid()
    for row in app._canvas_grid:
        assert all(not cell for cell in row)
    app.destroy()


# ── Export guards ─────────────────────────────────────────────────────────────

@pytest.mark.unit
def test_export_recolor_no_state_shows_error():
    """_export_recolor with no result_img shows error status (covers line 1044-1046)."""
    import dataclasses
    from asset_convertor.gui.state import RecolorState
    app = App()
    rs = RecolorState(result_img=None)
    app._state = dataclasses.replace(app._state, recolor=rs, source_path="/fake/test.png")
    app._export_recolor("/tmp/out", "test")
    assert "error" in app.lbl_status.cget("text").lower() or \
           "Appliquez" in app.lbl_status.cget("text") or \
           "recolor" in app.lbl_status.cget("text").lower()
    app.destroy()


@pytest.mark.unit
def test_export_standard_no_result_img_is_noop():
    """_export_standard with no result_img returns silently (covers line 946-947)."""
    import dataclasses
    app = App()
    app._state = dataclasses.replace(app._state, result_img=None, source_path="/fake/x.png")
    # Should not raise
    app._export_standard("/tmp/out", "x")
    app.destroy()


# ── _on_convert_success_a2 — non-animated branch ─────────────────────────────

@pytest.mark.unit
def test_on_convert_success_a2_flat_no_animation():
    """_on_convert_success_a2 with flat (non-animated) tiles does not start animation."""
    from PIL import Image
    import dataclasses
    import tkinter as tk
    from unittest.mock import patch

    app = App()
    # Flat tile list (not 2D) → no animation
    fake_tiles = [Image.new("RGBA", (48, 48), (0, 0, 0, 255)) for _ in range(47)]
    app._animated_var = tk.BooleanVar(value=False)
    app._state = dataclasses.replace(app._state, result_img=Image.new("RGBA", (48, 48)))

    with patch.object(app, "_display_result_image"), patch.object(app, "_redraw_canvas_grid"):
        app._on_convert_success_a2(fake_tiles, 48)

    assert app._timer_id is None  # no animation started
    app.destroy()


# ── _on_convert_error ─────────────────────────────────────────────────────────

@pytest.mark.unit
def test_on_convert_error_sets_error_status():
    """_on_convert_error re-enables convert button and shows error in status."""
    app = App()
    app.btn_convert.configure(state="disabled")
    app._on_convert_error("test error")
    assert app.btn_convert.cget("state") == "normal"
    assert "test error" in app.lbl_status.cget("text")
    app.destroy()


# ── _on_convert_success_single ────────────────────────────────────────────────

@pytest.mark.unit
def test_on_convert_success_single_shows_dimensions():
    """_on_convert_success_single displays image dimensions in output info label."""
    from PIL import Image
    from unittest.mock import patch
    app = App()
    img = Image.new("RGBA", (320, 240))
    with patch.object(app, "_display_result_image"):
        app._on_convert_success_single(img, "A3", 48)
    assert "320x240" in app.lbl_output_info.cget("text")
    app.destroy()


# ── Recolor state callbacks ───────────────────────────────────────────────────

@pytest.mark.unit
def test_on_recolor_state_change_updates_state():
    """_on_recolor_state_change propagates new AppState."""
    import dataclasses
    app = App()
    new_state = dataclasses.replace(app._state, tile_size=32)
    app._on_recolor_state_change(new_state)
    assert app._state.tile_size == 32
    app.destroy()


@pytest.mark.unit
def test_on_recolor_preview_ready_displays_image():
    """_on_recolor_preview_ready calls _display_result_image without error."""
    from PIL import Image
    from unittest.mock import patch
    app = App()
    img = Image.new("RGBA", (64, 64), (200, 100, 50, 255))
    with patch.object(app, "_display_result_image"):
        app._on_recolor_preview_ready(img)  # must not raise
    app.destroy()


# ── _on_type_change extra branches ────────────────────────────────────────────

@pytest.mark.unit
def test_on_type_change_non_recolor_switches_to_canvas():
    """_on_type_change to non-Recolor switches right panel to canvas."""
    app = App()
    # 🌱 Sol maps to A2
    app._on_type_change_internal("A2")
    assert app._state.resource_type == "A2"
    app.destroy()


@pytest.mark.unit
def test_on_type_change_recolor_with_source_img():
    """_on_type_change to Recolor with source_img extracts palette."""
    import dataclasses
    from PIL import Image
    app = App()
    src_img = Image.new("RGBA", (4, 4), (100, 150, 200, 255))
    app._state = dataclasses.replace(app._state, source_img=src_img)
    app._on_type_change_internal("Recolor")
    assert app._state.resource_type == "Recolor"
    app.destroy()


@pytest.mark.unit
def test_on_type_change_recolor_already_has_state():
    """_on_type_change to Recolor when recolor state already exists preserves it."""
    import dataclasses
    from asset_convertor.gui.state import RecolorState
    app = App()
    rs = RecolorState(source_palette=[(10, 20, 30, 255)])
    app._state = dataclasses.replace(app._state, recolor=rs)
    app._on_type_change_internal("Recolor")
    assert app._state.resource_type == "Recolor"
    assert app._state.recolor is not None
    app.destroy()



@pytest.mark.unit
def test_on_format_change_mv_accepted():
    """_on_format_change accepts valid MV format."""
    import dataclasses
    app = App()
    app._format_var.set("MV")
    app._on_format_change()
    assert app._state.format == "MV"
    app.destroy()


# ── _on_anim_type_change ──────────────────────────────────────────────────────

@pytest.mark.unit
def test_on_anim_type_change_updates_state():
    """_on_anim_type_change stores new anim_type in state."""
    app = App()
    app._on_anim_type_change("Verticale")
    assert app._state.anim_type == "Verticale"
    app.destroy()


# ── _on_speed_change ──────────────────────────────────────────────────────────

@pytest.mark.unit
def test_on_speed_change_valid_value():
    """_on_speed_change parses ms value and updates state."""
    app = App()
    app._on_speed_change("200 ms")
    assert app._state.anim_speed_ms == 200
    app.destroy()


@pytest.mark.unit
def test_on_speed_change_invalid_falls_back_to_150():
    """_on_speed_change falls back to 150ms on parse error."""
    app = App()
    app._on_speed_change("invalid")
    assert app._state.anim_speed_ms == 150
    app.destroy()


# ── _on_convert_success_a2 ────────────────────────────────────────────────────

@pytest.mark.unit
def test_on_convert_success_a2_enables_export():
    """_on_convert_success_a2 enables export button."""
    from PIL import Image
    from unittest.mock import patch
    app = App()
    tile = Image.new("RGBA", (48, 48), (100, 100, 100, 255))
    tiles_flat = [tile, tile, tile, tile]
    # Mock the display methods to avoid TclError with pyimage
    with (
        patch.object(app, "_display_output_sheet"),
        patch.object(app, "_draw_canvas_pattern"),
    ):
        app._on_convert_success_a2(tiles_flat, 48)
    assert app.btn_export.cget("state") == "normal"
    app.destroy()


# ── _export_standard with result_img set ─────────────────────────────────────

@pytest.mark.unit
def test_export_standard_with_result_img(tmp_path):
    """_export_standard exports a simple image to disk when result_img is set."""
    import dataclasses
    from PIL import Image
    app = App()
    img = Image.new("RGBA", (96, 48))
    app._state = dataclasses.replace(
        app._state,
        result_img=img,
        resource_type="A3",
        tile_size=48,
    )
    app._export_tsx_var.set(False)
    app._export_standard(str(tmp_path), "test_export")
    # File should be written
    assert (tmp_path / "test_export.png").exists()
    app.destroy()


# ── _compute_cell_bitmask (pure function, lines 101-116) ─────────────────────

from asset_convertor.gui.app import _compute_cell_bitmask


@pytest.mark.unit
def test_bitmask_isolated_cell():
    """Cell with no neighbors → bitmask = 0."""
    grid = [[False, False, False],
            [False, True,  False],
            [False, False, False]]
    assert _compute_cell_bitmask(grid, 1, 1) == 0


@pytest.mark.unit
def test_bitmask_north_neighbor():
    """North neighbor present → bit 2 set (N=2)."""
    grid = [[False, True,  False],
            [False, True,  False],
            [False, False, False]]
    result = _compute_cell_bitmask(grid, 1, 1)
    assert result & 2  # N bit


@pytest.mark.unit
def test_bitmask_all_cardinal_neighbors():
    """All 4 cardinals present, no diagonals → bits N+S+E+W = 2+64+16+8 = 90."""
    grid = [[False, True,  False],
            [True,  True,  True],
            [False, True,  False]]
    result = _compute_cell_bitmask(grid, 1, 1)
    assert result & (2 | 64 | 16 | 8)


@pytest.mark.unit
def test_bitmask_full_neighborhood():
    """Full 3x3 neighborhood filled → all bits set = 255."""
    grid = [[True, True, True],
            [True, True, True],
            [True, True, True]]
    assert _compute_cell_bitmask(grid, 1, 1) == 255


@pytest.mark.unit
def test_bitmask_edge_cell_no_out_of_bounds():
    """Edge cell — function must not raise on boundary access."""
    grid = [[True, True, True],
            [True, True, True],
            [True, True, True]]
    result = _compute_cell_bitmask(grid, 0, 0)  # top-left corner
    assert isinstance(result, int)


@pytest.mark.unit
def test_bitmask_empty_grid():
    """Empty grid → bitmask = 0 (no neighbors)."""
    grid = []
    result = _compute_cell_bitmask(grid, 0, 0)
    assert result == 0


# ── _toggle_log (lines 224-228) ──────────────────────────────────────────────

@pytest.mark.unit
def test_toggle_log_show():
    """_toggle_log shows log frame when _log_visible_var is True."""
    app = App()
    app._log_visible_var.set(True)
    app._toggle_log()  # must not raise
    app.destroy()


@pytest.mark.unit
def test_toggle_log_hide():
    """_toggle_log hides log frame when _log_visible_var is False."""
    app = App()
    app._log_visible_var.set(False)
    app._toggle_log()  # must not raise
    app.destroy()


# ── _switch_right_panel_to_recolor early return (line 481) ───────────────────

@pytest.mark.unit
def test_switch_right_panel_to_recolor_already_installed():
    """_switch_right_panel_to_recolor is a no-op if panel already installed."""
    from unittest.mock import MagicMock
    app = App()
    # Simulate already-installed panel
    app._recolor_panel = MagicMock()
    app._switch_right_panel_to_recolor()  # must return early without error
    app.destroy()


# ── _run_conversion guard paths (lines 735-742) ──────────────────────────────

@pytest.mark.unit
def test_run_conversion_no_source_is_noop():
    """_run_conversion logs warning and returns when no source image."""
    import dataclasses
    app = App()
    app._state = dataclasses.replace(app._state, source_img=None)
    app._run_conversion()  # must not start a thread
    app.destroy()


@pytest.mark.unit
def test_run_conversion_recolor_no_remap_is_noop():
    """_run_conversion logs warning when Recolor mode but remap_table is empty."""
    import dataclasses
    from PIL import Image
    from asset_convertor.gui.state import RecolorState
    app = App()
    src = Image.new("RGBA", (4, 4))
    rs = RecolorState(source_palette=[], remap_table={})
    app._state = dataclasses.replace(
        app._state, source_img=src, resource_type="Recolor", recolor=rs
    )
    app._run_conversion()  # must not start a thread (remap_table is empty)
    app.destroy()


# ── _on_convert_success_a4 (lines 886-900) ───────────────────────────────────

@pytest.mark.unit
def test_on_convert_success_a4_enables_export():
    """_on_convert_success_a4 enables export button."""
    from PIL import Image
    from unittest.mock import patch
    app = App()
    result_img = Image.new("RGBA", (192, 48))
    wall_tiles = [Image.new("RGBA", (48, 48)) for _ in range(16)]
    with (
        patch.object(app, "_display_result_image"),
        patch.object(app, "_draw_canvas_pattern"),
    ):
        app._on_convert_success_a4(result_img, wall_tiles, 48)
    assert app.btn_export.cget("state") == "normal"
    app.destroy()


# ── _export (lines 929-942) ──────────────────────────────────────────────────

@pytest.mark.unit
def test_export_no_source_path_is_noop(tmp_path):
    """_export returns early when source_path is None."""
    import dataclasses
    app = App()
    app._state = dataclasses.replace(app._state, source_path=None)
    app._export()  # must not raise
    app.destroy()


@pytest.mark.unit
def test_export_dispatches_to_export_a3(tmp_path):
    """_export calls _export_a3 for A3 resource type."""
    import dataclasses
    from PIL import Image
    from unittest.mock import patch
    app = App()
    img = Image.new("RGBA", (96, 48))
    app._state = dataclasses.replace(
        app._state,
        source_path=str(tmp_path / "test.png"),
        resource_type="A3",
        result_img=img,
        tile_size=48,
    )
    app._output_dir_var.set(str(tmp_path))
    app._export_tsx_var.set(False)

    with patch.object(app, "_export_a3") as mock_export:
        app._export()

    mock_export.assert_called_once()
    app.destroy()


@pytest.mark.unit
def test_export_standard_with_tiles_a2(tmp_path):
    """_export_standard for A2 with tiles calls the export pipeline."""
    import dataclasses
    from PIL import Image
    from unittest.mock import patch
    app = App()
    tile = Image.new("RGBA", (48, 48))
    tiles = [[tile, tile], [tile, tile]]
    img = Image.new("RGBA", (96, 96))
    app._state = dataclasses.replace(
        app._state,
        result_img=img,
        resource_type="A2",
        tile_size=48,
        tiles=tiles,
    )
    app._export_tsx_var.set(False)
    # Mock the export function to avoid disk I/O
    with patch("asset_convertor.gui.app.export", return_value=("/tmp/out.png", None)):
        app._export_standard(str(tmp_path), "test_a2")
    app.destroy()


# ── _run_conversion with source (lines 744-757) ──────────────────────────────

@pytest.mark.unit
def test_run_conversion_starts_thread_with_source():
    """_run_conversion launches a thread when source image is present."""
    import dataclasses
    import threading
    from PIL import Image
    from unittest.mock import patch

    app = App()
    src = Image.new("RGBA", (192, 192))
    app._state = dataclasses.replace(
        app._state, source_img=src, resource_type="A3"
    )

    started_threads = []
    original_start = threading.Thread.start

    def mock_start(self):
        started_threads.append(self)
        # Don't actually start — just record it

    with patch.object(threading.Thread, "start", mock_start):
        app._run_conversion()

    assert len(started_threads) == 1
    app.destroy()


# ── _export_recolor (lines 843-867) ──────────────────────────────────────────

@pytest.mark.unit
def test_export_recolor_no_result_is_noop(tmp_path):
    """_export_recolor is a no-op when result_img is None."""
    import dataclasses
    app = App()
    app._state = dataclasses.replace(app._state, result_img=None, resource_type="Recolor")
    app._export_recolor(str(tmp_path), "recolor_test")  # must not raise
    app.destroy()


@pytest.mark.unit
def test_export_recolor_saves_png(tmp_path):
    """_export_recolor writes a PNG when RecolorState.result_img is set."""
    import dataclasses
    from PIL import Image
    from asset_convertor.gui.state import RecolorState
    app = App()
    img = Image.new("RGBA", (32, 32), (200, 100, 50, 255))
    rs = RecolorState(result_img=img)
    app._state = dataclasses.replace(
        app._state, recolor=rs, resource_type="Recolor"
    )
    app._export_recolor(str(tmp_path), "recolor_out")
    # The method saves as {name}_recolor.png
    assert (tmp_path / "recolor_out_recolor.png").exists()
    app.destroy()


# ── _setup_animation (lines 1182-1196) ───────────────────────────────────────

@pytest.mark.unit
def test_setup_animation_not_animated_does_not_schedule():
    """_setup_animation is a no-op when _animated_var is False."""
    app = App()
    app._animated_var = __import__("tkinter").BooleanVar(value=False)
    app._setup_animation(3)
    assert app._timer_id is None
    app.destroy()


@pytest.mark.unit
def test_setup_animation_horizontal_3_frames():
    """_setup_animation 3 horizontal frames → frame_sequence [0,1,2,1]."""
    import tkinter as tk
    import customtkinter as ctk
    app = App()
    app._animated_var = tk.BooleanVar(value=True)
    app._anim_type_var = ctk.StringVar(value="Horizontale")
    # Cancel any timer immediately to avoid callback after destroy
    from unittest.mock import patch
    with patch.object(app, "after", return_value=None):
        app._setup_animation(3)
    assert app._frame_sequence == [0, 1, 2, 1]
    app.destroy()


@pytest.mark.unit
def test_setup_animation_vertical_3_frames():
    """_setup_animation 3 vertical frames → frame_sequence [0,1,2]."""
    import tkinter as tk
    import customtkinter as ctk
    app = App()
    app._animated_var = tk.BooleanVar(value=True)
    app._anim_type_var = ctk.StringVar(value="Verticale")
    from unittest.mock import patch
    with patch.object(app, "after", return_value=None):
        app._setup_animation(3)
    assert app._frame_sequence == [0, 1, 2]
    app.destroy()


@pytest.mark.unit
def test_setup_animation_4_frames():
    """_setup_animation 4 frames → frame_sequence [0,1,2,3]."""
    import tkinter as tk
    import customtkinter as ctk
    app = App()
    app._animated_var = tk.BooleanVar(value=True)
    app._anim_type_var = ctk.StringVar(value="Horizontale")
    from unittest.mock import patch
    with patch.object(app, "after", return_value=None):
        app._setup_animation(4)
    assert app._frame_sequence == [0, 1, 2, 3]
    app.destroy()


@pytest.mark.unit
def test_setup_animation_5_frames_fallback():
    """_setup_animation 5 frames → frame_sequence [0,1,2,3,4]."""
    import tkinter as tk
    import customtkinter as ctk
    app = App()
    app._animated_var = tk.BooleanVar(value=True)
    app._anim_type_var = ctk.StringVar(value="Horizontale")
    from unittest.mock import patch
    with patch.object(app, "after", return_value=None):
        app._setup_animation(5)
    assert app._frame_sequence == [0, 1, 2, 3, 4]
    app.destroy()


# ── _stop_animation (lines 1198-1203) ────────────────────────────────────────

@pytest.mark.unit
def test_stop_animation_cancels_timer():
    """_stop_animation cancels pending after() timer."""
    from unittest.mock import patch, MagicMock
    app = App()
    app._timer_id = "fake_timer_id"
    with patch.object(app, "after_cancel") as mock_cancel:
        app._stop_animation()
    mock_cancel.assert_called_once_with("fake_timer_id")
    assert app._timer_id is None
    app.destroy()


@pytest.mark.unit
def test_stop_animation_no_timer_is_noop():
    """_stop_animation is safe when no timer is scheduled."""
    app = App()
    app._timer_id = None
    app._stop_animation()  # must not raise
    assert app._frame_sequence == [0]
    app.destroy()


# ── Thread target: _convert_a3 (lines 790-807) ───────────────────────────────

@pytest.mark.unit
def test_convert_a3_calls_success_callback():
    """_convert_a3 calls _on_convert_success_a3 via after() on success."""
    import dataclasses
    from PIL import Image
    from unittest.mock import patch, MagicMock
    app = App()
    src = Image.new("RGBA", (192, 192), (128, 128, 128, 255))
    app._state = dataclasses.replace(app._state, source_img=src)

    captured_callbacks = []
    # Mock after to capture the lambda, NOT execute it yet
    def capture_after(delay, callback):
        captured_callbacks.append(callback)
        return "timer"

    with patch.object(app, "after", side_effect=capture_after):
        app._convert_a3()

    assert len(captured_callbacks) == 1
    # Run the captured callback to cover _on_convert_success_a3 path
    with (
        patch.object(app, "_display_result_image"),
        patch.object(app, "_redraw_canvas_grid"),
    ):
        captured_callbacks[0]()
    app.destroy()


@pytest.mark.unit
def test_convert_a3_calls_error_callback_on_failure():
    """_convert_a3 calls _on_convert_error via after() when conversion fails."""
    import dataclasses
    from PIL import Image
    from unittest.mock import patch
    from asset_convertor.core import converter_mv_a3

    app = App()
    src = Image.new("RGBA", (192, 192))
    app._state = dataclasses.replace(app._state, source_img=src)

    captured_error_callbacks = []

    def capture_after(delay, callback):
        captured_error_callbacks.append(callback)
        return "timer"

    with (
        patch.object(app, "after", side_effect=capture_after),
        patch("asset_convertor.gui.app.convert_mv_a3", side_effect=RuntimeError("boom")),
    ):
        app._convert_a3()

    assert len(captured_error_callbacks) == 1
    captured_error_callbacks[0]()  # this triggers _on_convert_error
    app.destroy()


# ── Thread target: _apply_recolor (lines 851-867) ────────────────────────────

@pytest.mark.unit
def test_apply_recolor_calls_success_callback():
    """_apply_recolor calls _on_convert_success_single via after() on success."""
    import dataclasses
    from PIL import Image
    from asset_convertor.gui.state import RecolorState
    from unittest.mock import patch

    app = App()
    src = Image.new("RGBA", (32, 32), (200, 100, 50, 255))
    rs = RecolorState(
        source_palette=[(200, 100, 50, 255)],
        remap_table={(200, 100, 50, 255): (100, 200, 150, 255)},
    )
    app._state = dataclasses.replace(app._state, source_img=src, recolor=rs)

    captured = []

    def capture_after(delay, callback):
        captured.append(callback)
        return "timer"

    with patch.object(app, "after", side_effect=capture_after):
        app._apply_recolor()

    assert len(captured) == 1
    with patch.object(app, "_display_result_image"):
        captured[0]()
    app.destroy()


# ── _build_secondary_a3 via type change (lines 327-332) ──────────────────────

@pytest.mark.unit
def test_on_type_change_a3_builds_secondary():
    """_on_type_change to A3 triggers _build_secondary_a3."""
    app = App()
    app._on_type_change_internal("A3")  # A3
    assert app._state.resource_type == "A3"
    app.destroy()


# ── Recolor: extract_palette ValueError fallback (lines 660-664) ─────────────

@pytest.mark.unit
def test_on_type_change_recolor_palette_extraction_fails():
    """_on_type_change Recolor: when extract_palette raises, falls back to empty RecolorState."""
    import dataclasses
    from PIL import Image
    from unittest.mock import patch

    app = App()
    src = Image.new("RGBA", (4, 4), (100, 150, 200, 255))
    app._state = dataclasses.replace(app._state, source_img=src)

    with patch("asset_convertor.gui.app.extract_palette", side_effect=ValueError("too many")):
        app._on_type_change_internal("Recolor")

    assert app._state.resource_type == "Recolor"
    assert app._state.recolor is not None
    app.destroy()


# ── _on_speed_change with active timer (lines 711-712) ───────────────────────

@pytest.mark.unit
def test_on_speed_change_restarts_active_timer():
    """_on_speed_change restarts the animation timer when one is already running."""
    import dataclasses
    from PIL import Image
    from unittest.mock import patch

    app = App()
    tile = Image.new("RGBA", (48, 48))
    app._state = dataclasses.replace(app._state, tiles=[tile, tile, tile])
    app._timer_id = "existing_timer"

    with (
        patch.object(app, "after_cancel") as mock_cancel,
        patch.object(app, "after", return_value="new_timer"),
    ):
        app._on_speed_change("300 ms")

    mock_cancel.assert_called_once_with("existing_timer")
    assert app._state.anim_speed_ms == 300
    app.destroy()


# ── _export dispatch A4 and Recolor (lines 938, 940) ─────────────────────────

@pytest.mark.unit
def test_export_dispatches_to_export_a4(tmp_path):
    """_export calls _export_a4 when resource_type is A4."""
    import dataclasses
    from PIL import Image
    from unittest.mock import patch

    app = App()
    app._state = dataclasses.replace(
        app._state,
        source_path=str(tmp_path / "wall.png"),
        resource_type="A4",
        result_img=Image.new("RGBA", (192, 48)),
    )
    app._output_dir_var.set(str(tmp_path))

    with patch.object(app, "_export_a4") as mock_export:
        app._export()

    mock_export.assert_called_once()
    app.destroy()


@pytest.mark.unit
def test_export_dispatches_to_export_recolor(tmp_path):
    """_export calls _export_recolor when resource_type is Recolor."""
    import dataclasses
    from PIL import Image
    from unittest.mock import patch

    app = App()
    app._state = dataclasses.replace(
        app._state,
        source_path=str(tmp_path / "source.png"),
        resource_type="Recolor",
        result_img=Image.new("RGBA", (32, 32)),
    )
    app._output_dir_var.set(str(tmp_path))

    with patch.object(app, "_export_recolor") as mock_export:
        app._export()

    mock_export.assert_called_once()
    app.destroy()


# ── _export_standard OSError handler (lines 989-992) ─────────────────────────

@pytest.mark.unit
def test_export_standard_oserror_sets_error_status(tmp_path):
    """_export_standard catches OSError and displays error status."""
    import dataclasses
    from PIL import Image
    from unittest.mock import patch

    app = App()
    img = Image.new("RGBA", (96, 48))
    app._state = dataclasses.replace(
        app._state,
        result_img=img,
        resource_type="A3",
        tile_size=48,
    )
    app._export_tsx_var.set(False)

    with patch("PIL.Image.Image.save", side_effect=OSError("permission denied")):
        app._export_standard(str(tmp_path), "fail_export")

    status = app.lbl_status.cget("text")
    assert "Impossible" in status or "❌" in status
    app.destroy()


# ── _on_convert_success_a2: animated path (lines 882-884) ────────────────────

@pytest.mark.unit
def test_on_convert_success_a2_animated_tiles():
    """_on_convert_success_a2 calls _setup_animation when animated with 2D tile list."""
    from PIL import Image
    from unittest.mock import patch
    import tkinter as tk

    app = App()
    tile = Image.new("RGBA", (48, 48))
    tiles_2d = [[tile, tile, tile, tile], [tile, tile, tile, tile]]
    app._animated_var = tk.BooleanVar(value=True)

    with (
        patch.object(app, "_display_output_sheet"),
        patch.object(app, "_draw_canvas_pattern"),
        patch.object(app, "_setup_animation") as mock_setup,
        patch.object(app, "after", return_value=None),
    ):
        app._on_convert_success_a2(tiles_2d, 48)

    mock_setup.assert_called_once_with(2)
    app.destroy()


# ── _apply_recolor error handler (lines 865-867) ─────────────────────────────

@pytest.mark.unit
def test_apply_recolor_error_handler():
    """_apply_recolor calls _on_convert_error when apply_remap raises."""
    import dataclasses
    from PIL import Image
    from asset_convertor.gui.state import RecolorState
    from unittest.mock import patch

    app = App()
    src = Image.new("RGBA", (32, 32))
    rs = RecolorState(remap_table={(255, 0, 0, 255): (0, 255, 0, 255)})
    app._state = dataclasses.replace(app._state, source_img=src, recolor=rs)

    captured = []

    def capture_after(delay, cb):
        captured.append(cb)
        return "timer"

    with (
        patch.object(app, "after", side_effect=capture_after),
        patch("asset_convertor.core.recolor.apply_remap", side_effect=RuntimeError("boom")),
    ):
        app._apply_recolor()

    assert len(captured) == 1
    captured[0]()
    app.destroy()


# ── _export_standard with TSX (lines 971, 979-982) ───────────────────────────

@pytest.mark.unit
def test_export_standard_a3_with_tsx(tmp_path):
    """_export_standard A3 with tsx enabled calls export_simple_sheet."""
    import dataclasses
    from PIL import Image
    from unittest.mock import patch

    app = App()
    img = Image.new("RGBA", (96, 48))
    app._state = dataclasses.replace(
        app._state, result_img=img, resource_type="A3", tile_size=48,
    )
    app._export_tsx_var.set(True)

    with patch("asset_convertor.gui.app.export_simple_sheet",
               return_value=(str(tmp_path / "out.png"), str(tmp_path / "out.tsx"))) as mock_exp:
        app._export_standard(str(tmp_path), "tsx_a3")

    mock_exp.assert_called_once()
    app.destroy()


@pytest.mark.unit
def test_export_standard_a2_with_tsx_includes_tsx_in_status(tmp_path):
    """_export_standard A2 tiles with tsx: status mentions tsx file."""
    import dataclasses
    from PIL import Image
    from unittest.mock import patch

    app = App()
    tile = Image.new("RGBA", (48, 48))
    img = Image.new("RGBA", (96, 96))
    app._state = dataclasses.replace(
        app._state,
        result_img=img,
        resource_type="A2",
        tile_size=48,
        tiles=[[tile, tile], [tile, tile]],
    )
    app._export_tsx_var.set(True)

    with patch("asset_convertor.gui.app.export",
               return_value=(str(tmp_path / "out.png"), str(tmp_path / "out.tsx"))):
        app._export_standard(str(tmp_path), "tiles_tsx")

    status = app.lbl_status.cget("text")
    assert "Exporté" in status
    app.destroy()


# ── _export_a4 (lines 1000-1039) ─────────────────────────────────────────────

@pytest.mark.unit
def test_export_a4_no_tops_attr_is_noop(tmp_path):
    """_export_a4 returns early when _a4_tops attr is not set."""
    app = App()
    app._export_a4(str(tmp_path), "wall")
    assert not list(tmp_path.iterdir())
    app.destroy()


@pytest.mark.unit
def test_export_a4_without_tsx(tmp_path):
    """_export_a4 saves two PNGs when export_tsx is False."""
    import dataclasses
    from PIL import Image
    app = App()
    app._a4_tops = Image.new("RGBA", (192, 48))
    app._a4_sides = Image.new("RGBA", (192, 48))
    app._export_tsx_var.set(False)
    app._state = dataclasses.replace(app._state, tile_size=48)
    app._export_a4(str(tmp_path), "wall")
    assert (tmp_path / "wall_tops.png").exists()
    assert (tmp_path / "wall_sides.png").exists()
    app.destroy()


@pytest.mark.unit
def test_export_a4_with_tsx(tmp_path):
    """_export_a4 calls export_simple_sheet and export_wall_sides_sheet when TSX enabled."""
    import dataclasses
    from PIL import Image
    from unittest.mock import patch
    app = App()
    app._a4_tops = Image.new("RGBA", (192, 48))
    app._a4_sides = Image.new("RGBA", (192, 48))
    app._export_tsx_var.set(True)
    app._state = dataclasses.replace(app._state, tile_size=48)
    with (
        patch("asset_convertor.gui.app.export_simple_sheet",
              return_value=(str(tmp_path / "tops.png"), str(tmp_path / "tops.tsx"))),
        patch("asset_convertor.exporters.tsx_generator.export_wall_sides_sheet",
              return_value=(str(tmp_path / "sides.png"), str(tmp_path / "sides.tsx"))),
    ):
        app._export_a4(str(tmp_path), "wall")
    app.destroy()


# ── _update_animation_controls_state (lines 717, 725-726, 730) ───────────────

@pytest.mark.unit
def test_update_animation_controls_state_animated_on():
    """_update_animation_controls_state sets controls enabled when animated."""
    import tkinter as tk
    import customtkinter as ctk
    app = App()
    app._animated_var = tk.BooleanVar(value=True)
    app._format_var = ctk.StringVar(value="MV")
    app._update_animation_controls_state()
    app.destroy()


@pytest.mark.unit
def test_update_animation_controls_state_no_var_returns():
    """_update_animation_controls_state returns early when no _animated_var."""
    app = App()
    if hasattr(app, "_animated_var"):
        del app._animated_var
    app._update_animation_controls_state()
    app.destroy()


# ── Resize integration tests (post-mortem: méthodes manquantes sur App) ───────
# Ces tests instancient App et appellent les méthodes Resize directement.
# Objectif : détecter tout AttributeError au niveau classe avant runtime.

@pytest.mark.unit
def test_validate_resize_dimensions_is_method_on_app():
    """_validate_resize_dimensions existe sur l'instance App et fonctionne."""
    from PIL import Image
    app = App()
    img_valid = Image.new("RGBA", (96, 48))
    img_invalid = Image.new("RGBA", (46, 48))
    assert app._validate_resize_dimensions(img_valid) is None
    err = app._validate_resize_dimensions(img_invalid)
    assert err is not None and "48" in err
    app.destroy()


@pytest.mark.unit
def test_convert_resize_is_method_on_app_and_dispatches():
    """_convert_resize est dans le dispatch de _run_conversion pour Resize."""
    import dataclasses
    import threading
    from PIL import Image
    from unittest.mock import patch

    app = App()
    src = Image.new("RGBA", (96, 48))
    app._state = dataclasses.replace(
        app._state, source_img=src, resource_type="Resize"
    )

    started = []
    def mock_start(self):
        started.append(self._target)

    with patch.object(threading.Thread, "start", mock_start):
        app._run_conversion()

    assert len(started) == 1
    assert started[0].__name__ == "_convert_resize"
    app.destroy()



@pytest.mark.unit
def test_convert_resize_calls_success_callback():
    """_convert_resize appelle _on_convert_success_resize via after() sur succès."""
    import dataclasses
    from PIL import Image
    from unittest.mock import patch

    app = App()
    src = Image.new("RGBA", (96, 48))
    app._state = dataclasses.replace(app._state, source_img=src)

    captured = []

    def capture_after(delay, callback):
        captured.append(callback)
        return "timer"

    with patch.object(app, "after", side_effect=capture_after):
        app._convert_resize()

    assert len(captured) == 1
    with patch.object(app, "_display_result_image"):
        captured[0]()
    assert app._state.result_img is not None
    assert app._state.result_img.size == (64, 32)  # 96*32/48=64, 48*32/48=32
    app.destroy()


@pytest.mark.unit
def test_export_resize_writes_file(tmp_path):
    """_export_resize écrit {stem}_32px.png sur le disque."""
    import dataclasses
    from PIL import Image

    app = App()
    result = Image.new("RGBA", (64, 32))
    app._state = dataclasses.replace(app._state, result_img=result)
    app._export_resize(str(tmp_path), "my_tile")
    assert (tmp_path / "my_tile_32px.png").exists()
    app.destroy()


@pytest.mark.unit
def test_export_dispatch_calls_export_resize(tmp_path):
    """_export appelle _export_resize quand resource_type == 'Resize'."""
    import dataclasses
    from PIL import Image
    from unittest.mock import patch

    app = App()
    app._state = dataclasses.replace(
        app._state,
        source_path=str(tmp_path / "source.png"),
        resource_type="Resize",
        result_img=Image.new("RGBA", (64, 32)),
    )
    app._output_dir_var.set(str(tmp_path))

    with patch.object(app, "_export_resize") as mock_export:
        app._export()

    mock_export.assert_called_once()
    app.destroy()


@pytest.mark.unit
def test_on_type_change_internal_resize_sets_export_tsx_false():
    """_on_type_change_internal('Resize') force export_tsx=False sur l'état."""
    app = App()
    app._on_type_change_internal("Resize")
    assert app._state.export_tsx is False
    assert app._state.resource_type == "Resize"
    app.destroy()
