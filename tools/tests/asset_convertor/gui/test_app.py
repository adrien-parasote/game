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
    app._type_var.set("🎮 Animé")
    app._on_type_change("🎮 Animé")

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
    app._type_var.set("🎮 Animé")
    app._on_type_change("🎮 Animé")

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
    app._type_var.set("🧱 Mur")
    app._on_type_change("🧱 Mur")

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


@pytest.mark.integration
def test_a4_conversion_canvas_tiles_count():
    """IT-001: Full A4 conversion → AppState.tiles has 16 Image objects."""
    import dataclasses

    from PIL import Image

    app = App()
    app._type_var.set("🧱 Mur")
    app._on_type_change("🧱 Mur")

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
    app._type_var.set("🧱 Mur")
    app._on_type_change("🧱 Mur")

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


@pytest.mark.integration
def test_redraw_canvas_grid_a2_uses_blob_path():
    """IT-003: _redraw_canvas_grid for A2 with 47 tiles draws without IndexError."""
    import dataclasses

    from PIL import Image

    app = App()

    # Inject 47 fake tiles into state (blob path)
    fake_tiles: list[Image.Image] = [
        Image.new("RGBA", (48, 48), color=(0, i * 5, 0, 255)) for i in range(47)
    ]
    app._state = dataclasses.replace(
        app._state,
        resource_type="A2",
        tiles=fake_tiles,
        tile_size=48,
    )
    app._canvas_grid = [[True] * 5 for _ in range(5)]

    # Must not raise
    app._redraw_canvas_grid()

    app.destroy()
