"""
tests.asset_convertor.gui.test_recolor_panel

Unit tests for RecolorPanel — no real Tkinter/CustomTkinter window required.
Uses unittest.mock to stub CTk widgets so tests run headless.

Spec: tools/docs/specs/asset_convertor_mv_gui.md § "Recolor Panel"
Test IDs: RP-001 … RP-015
"""

from __future__ import annotations

import dataclasses
import sys
import threading
import time
import types
import unittest
from unittest.mock import MagicMock, patch

from PIL import Image

# ---------------------------------------------------------------------------
# Headless stub — install BEFORE importing any gui module
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
            self._cfg = {}

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
            pass

        def grid(self, **kw):
            pass

        def pack(self, **kw):
            pass

        def bind(self, *a, **kw):
            pass

        def winfo_children(self):
            return []

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

    return stub


# Unconditionally install stubs so that gui modules import them instead of real tk/ctk
orig_ctk = sys.modules.get("customtkinter")
orig_tk = sys.modules.get("tkinter")
orig_panel = sys.modules.get("asset_convertor.gui.recolor_panel")

sys.modules["customtkinter"] = _make_ctk_stub()
sys.modules["tkinter"] = _make_tk_stub()
if "asset_convertor.gui.recolor_panel" in sys.modules:
    del sys.modules["asset_convertor.gui.recolor_panel"]

# Now safe to import gui modules
import tkinter as tk

from asset_convertor.core.palettes import get_palette, get_palette_names
from asset_convertor.core.recolor import Color, RemapTable
from asset_convertor.gui.recolor_panel import RecolorPanel, _rgb_hex
from asset_convertor.gui.state import AppState, RecolorState

# Restore original modules in sys.modules so subsequent tests are not affected
if orig_ctk is not None:
    sys.modules["customtkinter"] = orig_ctk
else:
    del sys.modules["customtkinter"]

if orig_tk is not None:
    sys.modules["tkinter"] = orig_tk
else:
    del sys.modules["tkinter"]

if orig_panel is not None:
    sys.modules["asset_convertor.gui.recolor_panel"] = orig_panel
else:
    if "asset_convertor.gui.recolor_panel" in sys.modules:
        del sys.modules["asset_convertor.gui.recolor_panel"]


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
) -> RecolorPanel:
    """Create a RecolorPanel with mock parent and capture callbacks."""
    if state is None:
        state = AppState(recolor=RecolorState())
    if on_state is None:
        on_state = []
    if on_preview is None:
        on_preview = []

    parent = MagicMock()
    panel = RecolorPanel(
        parent,
        state,
        on_state_change=lambda s: on_state.append(s),
        on_preview_update=lambda img: on_preview.append(img),
    )
    return panel


# ---------------------------------------------------------------------------
# RP-001 … RP-005  Internal helper tests (pure functions, no GUI)
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
        # Alpha channel is not part of CSS hex — must be stripped
        assert _rgb_hex((16, 32, 48, 0)) == "#102030"


# ---------------------------------------------------------------------------
# RP-002 … RP-005  Panel construction
# ---------------------------------------------------------------------------

class TestPanelConstruction(unittest.TestCase):
    """RP-002 — Panel instantiates without error."""

    def test_creates_without_source_image(self):
        """Panel with no source image must not raise."""
        state = AppState(recolor=RecolorState())
        panel = _make_panel(state)
        assert isinstance(panel, RecolorPanel)

    def test_creates_with_source_image(self):
        """Panel with source image must call extract+show palette without error."""
        img = _make_image([(255, 0, 0), (0, 255, 0)])
        rs = RecolorState()
        state = AppState(source_img=img, recolor=rs)
        captured: list[AppState] = []
        panel = _make_panel(state, on_state=captured)
        # State change must have been called (palette extracted)
        assert len(captured) >= 1

    def test_palette_populated_in_state(self):
        """RP-003 — source_palette is set in RecolorState after construction with img."""
        img = _make_image([(10, 20, 30), (40, 50, 60), (70, 80, 90)])
        state = AppState(source_img=img, recolor=RecolorState())
        captured: list[AppState] = []
        _make_panel(state, on_state=captured)
        # Last captured state must have source_palette set
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
# RP-006 — Preset selection
# ---------------------------------------------------------------------------

class TestPresetSelection(unittest.TestCase):
    """RP-005/006 — Preset click updates remap_table and active_preset."""

    def setUp(self):
        img = _make_image([(10, 20, 30), (40, 50, 60)])
        rs = RecolorState(source_palette=[(10, 20, 30, 255), (40, 50, 60, 255)])
        self.state = AppState(source_img=img, recolor=rs)
        self.captured: list[AppState] = []
        self.panel = _make_panel(self.state, on_state=self.captured)
        self.captured.clear()  # Reset after init

    def test_preset_click_updates_active_preset(self):
        """_on_preset_click must set active_preset."""
        name = get_palette_names()[0]
        self.panel._on_preset_click(name)
        assert len(self.captured) >= 1
        last = self.captured[-1]
        assert last.recolor is not None
        assert last.recolor.active_preset == name

    def test_preset_click_populates_remap_table(self):
        """_on_preset_click must populate remap_table keys matching source_palette."""
        name = get_palette_names()[0]
        self.panel._on_preset_click(name)
        last = self.captured[-1]
        assert last.recolor is not None
        # Each source color must have a mapping
        for src in last.recolor.source_palette:
            assert src in last.recolor.remap_table

    def test_preset_click_no_crash_when_no_source_palette(self):
        """_on_preset_click must be a no-op when source_palette is empty."""
        state = AppState(recolor=RecolorState())  # empty palette
        panel = _make_panel(state)
        panel._on_preset_click("GameBoy")  # must not raise


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
        """After update, panel schedules a preview refresh (debounce timer)."""
        with patch.object(self.panel, "_schedule_preview_refresh") as mock_refresh:
            self.panel._update_remap_entry(self.src, (1, 2, 3, 255))
            mock_refresh.assert_called_once()

    def test_update_remap_entry_no_crash_without_recolor_state(self):
        """_update_remap_entry is a no-op when recolor state is None."""
        state = AppState()  # no recolor
        panel = _make_panel(state)
        panel._update_remap_entry((0, 0, 0, 255), (255, 255, 255, 255))  # must not raise


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
        dst_canvas = MagicMock()
        entry = MagicMock()
        panel._on_hex_commit(src, hex_var, dst_canvas, entry)
        assert len(captured) == 0

    def test_short_hex_rejected(self):
        panel, _ = self._make_panel_with_remap()
        hex_var = tk.StringVar(value="ff00")  # only 4 chars
        panel._on_hex_commit((10, 20, 30, 255), hex_var, MagicMock(), MagicMock())
        # No crash, state unchanged


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

        panel.update_state(new_state)  # must not raise
        assert panel._state == new_state

    def test_update_state_with_none_recolor(self):
        state = AppState()
        panel = _make_panel(state)
        new_state = AppState(source_img=_make_image([(1, 2, 3)]))
        panel.update_state(new_state)  # must not raise


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
# RP-011 — Debounce: multiple rapid updates produce one callback
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
            # Must have cancelled the existing timer
            assert "existing_id" in cancel_calls
            # And set a new one at 300ms
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

        # Simulate user closing colorchooser (returns None)
        with patch("asset_convertor.gui.recolor_panel.colorchooser.askcolor", return_value=None):
            panel._open_color_picker((10, 20, 30, 255), dst_canvas)

        assert len(captured) == 0


if __name__ == "__main__":
    unittest.main()
