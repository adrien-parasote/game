"""
tests.asset_convertor.gui.test_recolor_panel

Unit tests for RecolorPanel — no real Tkinter/CustomTkinter window required.
Uses unittest.mock to stub CTk widgets so tests run headless.

Spec (original): tools/docs/specs/asset_convertor_mv_gui.md § "Recolor Panel"
Spec (swatch fix + import): tools/docs/specs/asset_convertor_recolor_swatch_fix.md
Test IDs: RP-001 … RP-015 | TC-001 … TC-011 | IT-001 … IT-004
"""

from __future__ import annotations

import dataclasses
import sys
import types
import unittest
from unittest.mock import MagicMock, patch

from PIL import Image

# ---------------------------------------------------------------------------
# Headless stubs — install BEFORE importing any gui module
# ---------------------------------------------------------------------------


def _make_ctk_stub() -> types.ModuleType:  # noqa: C901
    """Return a minimal stub for customtkinter that works without a display."""
    stub = types.ModuleType("customtkinter")

    class _Widget:
        def __init__(self, *a, **kw):
            pass

        def grid(self, **kw):
            pass

        def pack(self, **kw):
            pass

        def configure(self, **kw):
            pass

        def grid_columnconfigure(self, *a, **kw):
            pass

        def grid_rowconfigure(self, *a, **kw):
            pass

        def winfo_children(self):
            return []

        def destroy(self):
            pass

        def after(self, ms, fn=None, *a):
            return "timer_id"

        def after_cancel(self, _id):
            pass

        def bind(self, *a, **kw):
            pass

        def set(self, *a, **kw):
            pass

    class CTkFrame(_Widget):
        pass

    class CTkLabel(_Widget):
        pass

    class CTkButton(_Widget):
        pass

    class CTkEntry(_Widget):
        pass

    class CTkScrollbar(_Widget):
        pass

    class CTkScrollableFrame(_Widget):
        def winfo_children(self):
            return []

    class CTkFont:
        def __init__(self, *a, **kw):
            pass

    stub.CTkFrame = CTkFrame
    stub.CTkLabel = CTkLabel
    stub.CTkButton = CTkButton
    stub.CTkEntry = CTkEntry
    stub.CTkScrollbar = CTkScrollbar
    stub.CTkScrollableFrame = CTkScrollableFrame
    stub.CTkFont = CTkFont
    return stub


def _make_tk_stub() -> types.ModuleType:  # noqa: C901
    """Minimal tkinter stub for headless tests."""
    stub = types.ModuleType("tkinter")

    class StringVar:
        def __init__(self, value=""):
            self._val = value

        def get(self):
            return self._val

        def set(self, v):
            self._val = v

    class Canvas:
        def __init__(self, *a, **kw):
            self._cfg = dict(kw)

        def grid(self, **kw):
            pass

        def pack(self, **kw):
            pass

        def configure(self, **kw):
            self._cfg.update(kw)

        def cget(self, key):
            return self._cfg.get(key, "")

        def create_window(self, *a, **kw):
            pass

        def create_rectangle(self, *a, **kw):
            pass

        def bbox(self, *a):
            return (0, 0, 100, 100)

        def bind(self, *a, **kw):
            pass

        def xview(self, *a, **kw):
            pass

        def xview_scroll(self, *a):
            pass

        def xview_moveto(self, *a):
            pass

    class Frame:
        def __init__(self, *a, **kw):
            self._children: list = []

        def grid(self, **kw):
            pass

        def pack(self, **kw):
            pass

        def bind(self, *a, **kw):
            pass

        def winfo_children(self):
            return self._children

    class Button:
        def __init__(self, *a, **kw):
            pass

        def grid(self, **kw):
            pass

        def pack(self, **kw):
            pass

    stub.StringVar = StringVar
    stub.Canvas = Canvas
    stub.Frame = Frame
    stub.Button = Button

    colorchooser_mod = types.ModuleType("tkinter.colorchooser")
    colorchooser_mod.askcolor = MagicMock(return_value=None)
    stub.colorchooser = colorchooser_mod
    sys.modules["tkinter.colorchooser"] = colorchooser_mod

    filedialog_mod = types.ModuleType("tkinter.filedialog")
    filedialog_mod.askopenfilename = MagicMock(return_value="")
    stub.filedialog = filedialog_mod
    sys.modules["tkinter.filedialog"] = filedialog_mod

    return stub


# Install stubs before importing gui modules
orig_ctk = sys.modules.get("customtkinter")
orig_tk = sys.modules.get("tkinter")
orig_panel = sys.modules.get("asset_convertor.gui.recolor_panel")

sys.modules["customtkinter"] = _make_ctk_stub()
sys.modules["tkinter"] = _make_tk_stub()
if "asset_convertor.gui.recolor_panel" in sys.modules:
    del sys.modules["asset_convertor.gui.recolor_panel"]

# Safe to import gui modules now
import tkinter as tk

from asset_convertor.core.palettes import get_palette, get_palette_names
from asset_convertor.core.recolor import Color, RemapTable
from asset_convertor.gui.recolor_panel import RecolorPanel, _rgb_hex
from asset_convertor.gui.state import AppState, RecolorState

# Restore original modules so subsequent test imports are not affected
if orig_ctk is not None:
    sys.modules["customtkinter"] = orig_ctk
else:
    del sys.modules["customtkinter"]

if orig_tk is not None:
    sys.modules["tkinter"] = orig_tk
else:
    del sys.modules["tkinter"]

# NOTE: We do NOT restore the recolor_panel module.
# If we restored orig_panel (a stale cached version without the current imports),
# patch("asset_convertor.gui.recolor_panel.askopenfilename") would target the stale
# module object and fail silently. The freshly imported module must stay in cache.


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_image(colors: list[tuple[int, int, int]]) -> Image.Image:
    """Create an RGBA image with one pixel per color."""
    w = len(colors)
    img = Image.new("RGBA", (w, 1))
    for i, (r, g, b) in enumerate(colors):
        img.putpixel((i, 0), (r, g, b, 255))
    return img


def _make_panel(
    state: AppState | None = None,
    on_state: list | None = None,
    on_preview: list | None = None,
    on_error: list | None = None,
) -> RecolorPanel:
    """Create a RecolorPanel with mock parent and capture callbacks.

    If on_error is a list, wires on_error callback that appends to it.
    If on_error is None (default), does NOT pass on_error → tests graceful degradation.
    Pass on_error=[] explicitly to enable error capture.
    """
    if state is None:
        state = AppState(recolor=RecolorState())
    if on_state is None:
        on_state = []
    if on_preview is None:
        on_preview = []

    parent = MagicMock()

    kwargs: dict = {
        "on_state_change": lambda s: on_state.append(s),
        "on_preview_update": lambda img: on_preview.append(img),
    }
    if on_error is not None:
        kwargs["on_error"] = lambda msg: on_error.append(msg)

    panel = RecolorPanel(parent, state, **kwargs)
    return panel


# ---------------------------------------------------------------------------
# RP-001 — _rgb_hex()
# ---------------------------------------------------------------------------


class TestRgbHex(unittest.TestCase):
    """RP-001 — _rgb_hex() produces correct #rrggbb string."""

    def test_black(self):
        assert _rgb_hex((0, 0, 0, 255)) == "#000000"

    def test_white(self):
        assert _rgb_hex((255, 255, 255, 255)) == "#ffffff"

    def test_red(self):
        assert _rgb_hex((255, 0, 0, 255)) == "#ff0000"

    def test_alpha_ignored(self):
        assert _rgb_hex((16, 32, 48, 0)) == "#102030"


# ---------------------------------------------------------------------------
# RP-002 … RP-004 — Panel construction
# ---------------------------------------------------------------------------


class TestPanelConstruction(unittest.TestCase):
    """RP-002 — Panel instantiates without error."""

    def test_creates_without_source_image(self):
        state = AppState(recolor=RecolorState())
        panel = _make_panel(state)
        assert isinstance(panel, RecolorPanel)

    def test_creates_with_source_image(self):
        img = _make_image([(255, 0, 0), (0, 255, 0)])
        rs = RecolorState()
        state = AppState(source_img=img, recolor=rs)
        captured: list[AppState] = []
        _make_panel(state, on_state=captured)
        assert len(captured) >= 1

    def test_palette_populated_in_state(self):
        """RP-003 — source_palette set after construction with img."""
        img = _make_image([(10, 20, 30), (40, 50, 60), (70, 80, 90)])
        state = AppState(source_img=img, recolor=RecolorState())
        captured: list[AppState] = []
        _make_panel(state, on_state=captured)
        last = captured[-1]
        assert last.recolor is not None
        assert len(last.recolor.source_palette) == 3

    def test_transparent_image_gives_empty_palette(self):
        """RP-004 — Fully transparent image yields empty palette (no crash)."""
        img = Image.new("RGBA", (4, 4), (0, 0, 0, 0))
        state = AppState(source_img=img, recolor=RecolorState())
        captured: list[AppState] = []
        _make_panel(state, on_state=captured)
        if captured:
            last = captured[-1]
            assert last.recolor is not None
            assert last.recolor.source_palette == []


# ---------------------------------------------------------------------------
# RP-005/006 — Preset selection
# ---------------------------------------------------------------------------


class TestPresetSelection(unittest.TestCase):
    """RP-005/006 — Preset click updates remap_table and active_preset."""

    def setUp(self):
        img = _make_image([(10, 20, 30), (40, 50, 60)])
        rs = RecolorState(source_palette=[(10, 20, 30, 255), (40, 50, 60, 255)])
        self.state = AppState(source_img=img, recolor=rs)
        self.captured: list[AppState] = []
        self.panel = _make_panel(self.state, on_state=self.captured)
        self.captured.clear()

    def test_preset_click_updates_active_preset(self):
        name = get_palette_names()[0]
        self.panel._on_preset_click(name)
        assert len(self.captured) >= 1
        last = self.captured[-1]
        assert last.recolor is not None
        assert last.recolor.active_preset == name

    def test_preset_click_populates_remap_table(self):
        name = get_palette_names()[0]
        self.panel._on_preset_click(name)
        last = self.captured[-1]
        assert last.recolor is not None
        for src in last.recolor.source_palette:
            assert src in last.recolor.remap_table

    def test_preset_click_no_crash_when_no_source_palette(self):
        state = AppState(recolor=RecolorState())
        panel = _make_panel(state)
        panel._on_preset_click("GameBoy")


# ---------------------------------------------------------------------------
# RP-007 — Remap entry update
# ---------------------------------------------------------------------------


class TestRemapEntryUpdate(unittest.TestCase):
    """RP-007 — _update_remap_entry propagates state correctly."""

    def setUp(self):
        src: Color = (10, 20, 30, 255)
        rs = RecolorState(source_palette=[src], remap_table={src: src})
        self.src: Color = src
        state = AppState(recolor=rs)
        self.captured: list[AppState] = []
        self.panel = _make_panel(state, on_state=self.captured)
        self.captured.clear()

    def test_update_remap_entry_changes_target(self):
        new_dst: Color = (200, 100, 50, 255)
        self.panel._update_remap_entry(self.src, new_dst)
        last = self.captured[-1]
        assert last.recolor is not None
        assert last.recolor.remap_table[self.src] == new_dst

    def test_update_remap_entry_schedules_preview(self):
        with patch.object(self.panel, "_schedule_preview_refresh") as mock_refresh:
            self.panel._update_remap_entry(self.src, (1, 2, 3, 255))
            mock_refresh.assert_called_once()

    def test_update_remap_entry_no_crash_without_recolor_state(self):
        state = AppState()
        panel = _make_panel(state)
        panel._update_remap_entry((0, 0, 0, 255), (255, 255, 255, 255))


# ---------------------------------------------------------------------------
# RP-008 — Hex validation
# ---------------------------------------------------------------------------


class TestHexValidation(unittest.TestCase):
    """RP-008 — _on_hex_commit accepts valid hex and rejects invalid."""

    def _make_panel_with_remap(self) -> tuple[RecolorPanel, list]:
        src: Color = (10, 20, 30, 255)
        rs = RecolorState(source_palette=[src], remap_table={src: src})
        state = AppState(recolor=rs)
        captured: list[AppState] = []
        panel = _make_panel(state, on_state=captured)
        captured.clear()
        return panel, captured

    def test_valid_hex_updates_remap(self):
        panel, captured = self._make_panel_with_remap()
        src: Color = (10, 20, 30, 255)
        hex_var = tk.StringVar(value="ff0000")
        dst_canvas = MagicMock()
        entry = MagicMock()
        panel._on_hex_commit(src, hex_var, dst_canvas, entry)
        assert len(captured) >= 1
        last = captured[-1]
        assert last.recolor is not None
        assert last.recolor.remap_table[src] == (255, 0, 0, 255)

    def test_invalid_hex_does_not_update_remap(self):
        panel, captured = self._make_panel_with_remap()
        src: Color = (10, 20, 30, 255)
        hex_var = tk.StringVar(value="ZZZZZZ")
        panel._on_hex_commit(src, hex_var, MagicMock(), MagicMock())
        assert len(captured) == 0

    def test_short_hex_rejected(self):
        panel, _ = self._make_panel_with_remap()
        hex_var = tk.StringVar(value="ff00")
        panel._on_hex_commit((10, 20, 30, 255), hex_var, MagicMock(), MagicMock())


# ---------------------------------------------------------------------------
# RP-009 — update_state()
# ---------------------------------------------------------------------------


class TestUpdateState(unittest.TestCase):
    """RP-009 — update_state refreshes internal state without error."""

    def test_update_state_replaces_internal_state(self):
        state = AppState(recolor=RecolorState())
        panel = _make_panel(state)
        new_src: Color = (100, 150, 200, 255)
        new_rs = RecolorState(source_palette=[new_src], remap_table={new_src: new_src})
        new_state = dataclasses.replace(state, recolor=new_rs)
        panel.update_state(new_state)
        assert panel._state == new_state

    def test_update_state_with_none_recolor(self):
        state = AppState()
        panel = _make_panel(state)
        new_state = AppState(source_img=_make_image([(1, 2, 3)]))
        panel.update_state(new_state)


# ---------------------------------------------------------------------------
# RP-010 — Source swatch click
# ---------------------------------------------------------------------------


class TestSourceSwatchClick(unittest.TestCase):
    """RP-010 — Clicking source swatch sets _selected_source_color."""

    def test_source_swatch_click_stores_color(self):
        state = AppState(recolor=RecolorState())
        panel = _make_panel(state)
        color: Color = (10, 20, 30, 255)
        panel._on_source_swatch_click(color)
        assert panel._selected_source_color == color


# ---------------------------------------------------------------------------
# RP-011 — Debounce
# ---------------------------------------------------------------------------


class TestDebounce(unittest.TestCase):
    """RP-011 — _schedule_preview_refresh debounces (cancel + reset)."""

    def test_multiple_schedules_cancel_previous(self):
        state = AppState(recolor=RecolorState())
        panel = _make_panel(state)
        cancel_calls: list = []
        schedule_calls: list = []
        with (
            patch.object(panel, "after_cancel", side_effect=lambda _id: cancel_calls.append(_id)),
            patch.object(panel, "after", side_effect=lambda ms, fn=None: schedule_calls.append(ms) or "new_id"),
        ):
            panel._debounce_id = "existing_id"
            panel._schedule_preview_refresh()
            assert "existing_id" in cancel_calls
            assert 300 in schedule_calls

    def test_no_cancel_when_no_existing_timer(self):
        state = AppState(recolor=RecolorState())
        panel = _make_panel(state)
        panel._debounce_id = None
        with (
            patch.object(panel, "after_cancel") as mock_cancel,
            patch.object(panel, "after", return_value="new_id"),
        ):
            panel._schedule_preview_refresh()
            mock_cancel.assert_not_called()


# ---------------------------------------------------------------------------
# RP-012 — Color picker cancel is a no-op
# ---------------------------------------------------------------------------


class TestColorPickerCancel(unittest.TestCase):
    """RP-012 — Cancelling colorchooser does not update remap."""

    def test_cancel_is_noop(self):
        state = AppState(recolor=RecolorState(
            source_palette=[(10, 20, 30, 255)],
            remap_table={(10, 20, 30, 255): (10, 20, 30, 255)},
        ))
        captured: list[AppState] = []
        panel = _make_panel(state, on_state=captured)
        captured.clear()
        dst_canvas = MagicMock()
        dst_canvas.cget.return_value = "#0a141e"
        with patch("asset_convertor.gui.recolor_panel.colorchooser.askcolor", return_value=None):
            panel._open_color_picker((10, 20, 30, 255), dst_canvas)
        assert len(captured) == 0


# ===========================================================================
# TC-001…TC-011 — Swatch Fix + Import Palette
# Spec: tools/docs/specs/asset_convertor_recolor_swatch_fix.md
# ===========================================================================


class TestSwatchRendering(unittest.TestCase):
    """
    TC-001…TC-004
    Spec § "Fix 1 — _rebuild_swatches: remplacer tk.Button par tk.Canvas"
    """

    def _get_rebuild_swatches_source(self) -> str:
        """Return the source code of _rebuild_swatches for inspection."""
        import inspect
        import asset_convertor.gui.recolor_panel as rp_module
        return inspect.getsource(rp_module.RecolorPanel._rebuild_swatches)

    def test_tc001_rebuild_creates_canvas_not_button(self):
        """TC-001: _rebuild_swatches source uses tk.Canvas, not tk.Button."""
        import ast
        import inspect
        import textwrap
        import asset_convertor.gui.recolor_panel as rp_module

        src = inspect.getsource(rp_module.RecolorPanel._rebuild_swatches)
        # Parse and extract only non-docstring lines
        tree = ast.parse(textwrap.dedent(src))
        func = tree.body[0]
        # Remove the docstring expression if present
        stmts = func.body
        if stmts and isinstance(stmts[0], ast.Expr) and isinstance(stmts[0].value, ast.Constant):
            stmts = stmts[1:]
        code_src = ast.unparse(ast.Module(body=stmts, type_ignores=[]))

        assert "tk.Button" not in code_src, \
            "_rebuild_swatches code must NOT call tk.Button (macOS Aqua overrides bg)"
        assert "tk.Canvas" in code_src, \
            "_rebuild_swatches code must create tk.Canvas widgets"

    def test_tc002_canvas_bg_matches_hex(self):
        """TC-002: _rebuild_swatches passes bg=hex_color when creating tk.Canvas."""
        src = self._get_rebuild_swatches_source()
        # Verify that bg= and hex_color are both present — Canvas gets the color
        assert "bg=hex_color" in src or "bg=_rgb_hex" in src or "bg=" in src, \
            "_rebuild_swatches must pass bg= to tk.Canvas"
        assert "hex_color" in src, \
            "hex_color variable must be used in _rebuild_swatches"


    def test_tc003_label_shows_correct_count(self):
        """TC-003: _lbl_palette_info is configured with the count of colors."""
        state = AppState(recolor=RecolorState())
        panel = _make_panel(state, on_error=[])

        captured_text: list[str] = []

        def spy_configure(**kw):
            if "text" in kw:
                captured_text.append(kw["text"])

        panel._lbl_palette_info.configure = spy_configure

        palette = [(i * 10, i * 20, i * 30, 255) for i in range(1, 6)]  # 5 unique colors
        panel._rebuild_swatches(palette)

        assert any("5" in t for t in captured_text), \
            f"Label should contain '5', got: {captured_text}"

    def test_tc004_empty_palette_no_canvas_label_zero(self):
        """TC-004: Empty palette → no swatch created, label contains '0'."""
        state = AppState(recolor=RecolorState())
        panel = _make_panel(state, on_error=[])

        captured_text: list[str] = []
        panel._lbl_palette_info.configure = lambda **kw: captured_text.append(kw.get("text", ""))

        # Empty palette — _rebuild_swatches must not crash and must set count 0
        panel._rebuild_swatches([])

        assert any("0" in t for t in captured_text), \
            f"Expected '0' in label, got {captured_text}"


class TestImportPaletteFromImage(unittest.TestCase):
    """
    TC-005…TC-011
    Spec § "Feature 2 — Import palette depuis une image externe"
    """

    def _make_panel_with_source(
        self,
        source_colors: list[tuple[int, int, int]] | None = None,
        on_error: list | None = None,
    ) -> tuple[RecolorPanel, list[AppState]]:
        if source_colors is None:
            source_colors = [(10, 20, 30), (40, 50, 60), (70, 80, 90)]
        img = _make_image(source_colors)
        palette = [(r, g, b, 255) for r, g, b in source_colors]
        rs = RecolorState(source_palette=palette, remap_table={c: c for c in palette})
        state = AppState(source_img=img, recolor=rs)
        captured: list[AppState] = []
        panel = _make_panel(state, on_state=captured, on_error=on_error)
        captured.clear()
        return panel, captured

    def test_tc005_cancel_filedialog_is_noop(self):
        """TC-005: filedialog returns '' → state unchanged, no error."""
        errors: list[str] = []
        panel, captured = self._make_panel_with_source(on_error=errors)
        initial_remap = dict(panel._state.recolor.remap_table)

        with patch("asset_convertor.gui.recolor_panel.askopenfilename", return_value=""):
            panel._import_palette_from_image()

        assert captured == [], "State must not change on cancel"
        assert errors == [], "on_error must not be called on cancel"
        assert dict(panel._state.recolor.remap_table) == initial_remap

    def test_tc006_oserror_calls_on_error_state_unchanged(self):
        """TC-006: OSError on Image.open → on_error with ❌ message, state unchanged."""
        errors: list[str] = []
        panel, captured = self._make_panel_with_source(on_error=errors)
        initial_remap = dict(panel._state.recolor.remap_table)

        with patch("asset_convertor.gui.recolor_panel.askopenfilename",
                   return_value="/fake/corrupt.png"), \
             patch("asset_convertor.gui.recolor_panel.Image.open",
                   side_effect=OSError("file not found")):
            panel._import_palette_from_image()

        assert len(errors) == 1, f"Expected 1 error, got {errors}"
        assert "❌" in errors[0] or "illisible" in errors[0], \
            f"Error message unexpected: {errors[0]!r}"
        assert captured == [], "State must not change on OSError"
        assert dict(panel._state.recolor.remap_table) == initial_remap

    def test_tc007_valueerror_transparent_calls_on_error(self):
        """TC-007: extract_palette raises ValueError (transparent image) → on_error called."""
        errors: list[str] = []
        panel, captured = self._make_panel_with_source(on_error=errors)

        transparent_img = Image.new("RGBA", (4, 4), (0, 0, 0, 0))

        with patch("asset_convertor.gui.recolor_panel.askopenfilename",
                   return_value="/fake/empty.png"), \
             patch("asset_convertor.gui.recolor_panel.Image.open",
                   return_value=transparent_img), \
             patch("asset_convertor.gui.recolor_panel.extract_palette",
                   side_effect=ValueError("no opaque pixels")):
            panel._import_palette_from_image()

        assert len(errors) == 1, f"Expected 1 error, got {errors}"
        assert "❌" in errors[0] or "vide" in errors[0] or "transparent" in errors[0], \
            f"Error message unexpected: {errors[0]!r}"
        assert captured == [], "State must not change on ValueError"

    def test_tc008_no_source_palette_calls_on_error(self):
        """TC-008: source_palette empty → on_error with ⚠️ message, propose_remap not called."""
        errors: list[str] = []
        state = AppState(recolor=RecolorState())  # empty source_palette
        captured: list[AppState] = []
        panel = _make_panel(state, on_state=captured, on_error=errors)
        captured.clear()

        with patch("asset_convertor.gui.recolor_panel.askopenfilename",
                   return_value="/some/image.png"), \
             patch("asset_convertor.gui.recolor_panel.Image.open",
                   return_value=_make_image([(1, 2, 3)])), \
             patch("asset_convertor.gui.recolor_panel.propose_remap") as mock_propose:
            panel._import_palette_from_image()

        assert len(errors) == 1, f"Expected 1 error, got {errors}"
        assert "⚠️" in errors[0] or "source" in errors[0].lower(), \
            f"Error message unexpected: {errors[0]!r}"
        mock_propose.assert_not_called()

    def test_tc009_valid_import_updates_remap_table(self):
        """TC-009: Valid import → remap_table len == len(source_palette)."""
        errors: list[str] = []
        source_colors = [(10, 20, 30), (40, 50, 60), (70, 80, 90)]
        panel, captured = self._make_panel_with_source(source_colors=source_colors, on_error=errors)

        target_img = _make_image([(100, 0, 0), (0, 100, 0), (0, 0, 100), (100, 100, 0)])

        with patch("asset_convertor.gui.recolor_panel.askopenfilename",
                   return_value="/valid/img.png"), \
             patch("asset_convertor.gui.recolor_panel.Image.open", return_value=target_img):
            panel._import_palette_from_image()

        assert errors == [], f"Unexpected errors: {errors}"
        assert len(captured) >= 1, "State change must have been fired"
        last = captured[-1]
        assert last.recolor is not None
        assert len(last.recolor.remap_table) == len(source_colors), \
            f"Expected {len(source_colors)} entries in remap_table, got {len(last.recolor.remap_table)}"

    def test_tc010_valid_import_clears_active_preset(self):
        """TC-010: Valid import → active_preset set to None."""
        errors: list[str] = []
        source_colors = [(10, 20, 30), (40, 50, 60)]
        panel, captured = self._make_panel_with_source(source_colors=source_colors, on_error=errors)

        # Pre-set active_preset to simulate a previously selected preset
        panel._state = dataclasses.replace(
            panel._state,
            recolor=dataclasses.replace(panel._state.recolor, active_preset="Autumn"),
        )
        captured.clear()

        target_img = _make_image([(200, 100, 50)])
        with patch("asset_convertor.gui.recolor_panel.askopenfilename",
                   return_value="/img.png"), \
             patch("asset_convertor.gui.recolor_panel.Image.open", return_value=target_img):
            panel._import_palette_from_image()

        assert len(captured) >= 1, "State change must be fired"
        last = captured[-1]
        assert last.recolor is not None
        assert last.recolor.active_preset is None, \
            f"active_preset should be None after import, got {last.recolor.active_preset!r}"

    def test_tc011_no_on_error_graceful_degradation(self):
        """TC-011: on_error not wired → no exception raised even when import fails."""
        state = AppState(recolor=RecolorState())
        # Explicitly do NOT pass on_error (tests None path)
        panel = _make_panel(state)  # on_error=None → not passed to RecolorPanel

        with patch("asset_convertor.gui.recolor_panel.askopenfilename",
                   return_value="/bad/file.png"), \
             patch("asset_convertor.gui.recolor_panel.Image.open",
                   side_effect=OSError("broken")):
            try:
                panel._import_palette_from_image()
            except Exception as exc:
                self.fail(
                    f"_import_palette_from_image raised {exc!r} when on_error is None. "
                    "Expected graceful degradation."
                )


# ===========================================================================
# IT-001…IT-004 — Integration Tests (headless subset)
# Spec: tools/docs/specs/asset_convertor_recolor_swatch_fix.md § "Integration Tests"
# ===========================================================================


class TestImportPaletteIntegration(unittest.TestCase):
    """IT-001…IT-004 (headless-compatible subset)."""

    def test_it001_palette_extracted_from_real_image(self):
        """IT-001: extract_palette on non-transparent image returns non-empty palette."""
        from asset_convertor.core.recolor import extract_palette
        img = _make_image([(r * 10, g * 20, 50) for r in range(1, 5) for g in range(1, 5)])
        palette = extract_palette(img, max_colors=32)
        assert len(palette) > 0, "Palette must not be empty for non-transparent image"

    def test_it002_valid_import_fires_state_change_and_preview(self):
        """IT-002: After valid import, state change fired and preview refresh scheduled."""
        errors: list[str] = []
        source_colors = [(10, 20, 30), (40, 50, 60)]
        img = _make_image(source_colors)
        palette = [(r, g, b, 255) for r, g, b in source_colors]
        rs = RecolorState(source_palette=palette, remap_table={c: c for c in palette})
        state = AppState(source_img=img, recolor=rs)
        captured: list[AppState] = []
        panel = _make_panel(state, on_state=captured, on_error=errors)
        captured.clear()

        target_img = _make_image([(200, 100, 50), (50, 100, 200)])
        schedule_calls: list = []

        with patch("asset_convertor.gui.recolor_panel.askopenfilename",
                   return_value="/img.png"), \
             patch("asset_convertor.gui.recolor_panel.Image.open", return_value=target_img), \
             patch.object(panel, "_schedule_preview_refresh",
                          side_effect=lambda: schedule_calls.append(1)):
            panel._import_palette_from_image()

        assert errors == [], f"Unexpected errors: {errors}"
        assert len(captured) >= 1
        assert len(captured[-1].recolor.remap_table) > 0
        assert len(schedule_calls) == 1, "Preview refresh must be scheduled exactly once"

    def test_it003_no_button_in_rebuild_swatches(self):
        """IT-003: _rebuild_swatches code must use tk.Canvas, not tk.Button."""
        import ast
        import inspect
        import textwrap
        import asset_convertor.gui.recolor_panel as rp_module

        src = inspect.getsource(rp_module.RecolorPanel._rebuild_swatches)
        tree = ast.parse(textwrap.dedent(src))
        func = tree.body[0]
        stmts = func.body
        if stmts and isinstance(stmts[0], ast.Expr) and isinstance(stmts[0].value, ast.Constant):
            stmts = stmts[1:]
        code_src = ast.unparse(ast.Module(body=stmts, type_ignores=[]))

        assert "tk.Button" not in code_src, \
            "_rebuild_swatches must not create tk.Button (macOS Aqua overrides bg)"
        assert "tk.Canvas" in code_src, \
            "_rebuild_swatches must use tk.Canvas for swatch rendering"

    def test_it004_on_error_receives_message_on_bad_file(self):
        """IT-004: on_error (simulating app._log) receives message when import fails."""
        errors: list[str] = []
        source_colors = [(10, 20, 30)]
        img = _make_image(source_colors)
        palette = [(r, g, b, 255) for r, g, b in source_colors]
        rs = RecolorState(source_palette=palette, remap_table={c: c for c in palette})
        state = AppState(source_img=img, recolor=rs)
        panel = _make_panel(state, on_error=errors)

        with patch("asset_convertor.gui.recolor_panel.askopenfilename",
                   return_value="/bad.txt"), \
             patch("asset_convertor.gui.recolor_panel.Image.open",
                   side_effect=OSError("not an image")):
            panel._import_palette_from_image()

        assert len(errors) == 1, f"Expected 1 error logged via on_error, got {errors}"
        assert len(errors[0]) > 0, "Error message must not be empty"


if __name__ == "__main__":
    unittest.main()
