"""Asset Creator V3 — Dear PyGui application shell.

Main window with controls, tile preview, paint canvas, and log panel.
Generation pipeline logic is in gui.pipeline (testable without DPG).
"""
from __future__ import annotations

import dataclasses
import random
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import dearpygui.dearpygui as dpg
from PIL import Image

from tools.asset_creator.core.minimap import (
    compute_bitmask,
    find_closest_bitmask_index,
)
from tools.asset_creator.core.terrain import get_builtin_presets
from tools.asset_creator.gui.canvas import CanvasState, grid_to_canvas_coords
from tools.asset_creator.gui.pipeline import (
    do_export_autotile,
    do_export_standalone,
    generate_standalone_tile,
    regenerate_tileset,
)
from tools.asset_creator.gui.preview import pil_to_dpg_rgba, scale_nearest
from tools.asset_creator.gui.state import AppState, state_from_preset

# ── Constants ────────────────────────────────────────────────────────────────

CELL_SIZE = 32
PREVIEW_SCALE = 4  # 32 -> 128
CANVAS_COLS = 16
CANVAS_ROWS = 12
LEFT_PANEL_WIDTH = 280
HISTORY_PANEL_WIDTH = 280
DEBOUNCE_SECONDS = 0.3

# French labels <-> internal values for edge style
_EDGE_LABELS = {"Organique": "organic", "Droit": "straight", "Trame": "dithered"}
_EDGE_REVERSE = {v: k for k, v in _EDGE_LABELS.items()}

# ── History entry ────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class HistoryEntry:
    """A snapshot of app state at a point in time."""
    index: int
    state: AppState
    mode: str
    timestamp: str
    description: str


# ── Module-level mutable state (GUI singletons) ─────────────────────────────

_state: AppState | None = None
_canvas: CanvasState | None = None
_tiles: list[Image.Image] = []  # autotile mode: 47 tiles
_standalone_tile: Image.Image | None = None  # standalone mode: single 32x32
_presets: dict[str, Any] = {}
_cell_textures: dict[tuple[int, int], str] = {}
_last_change_time: float = 0.0
_pending_regen: bool = False
_log_lines: list[str] = []
_history: list[HistoryEntry] = []
_restoring_history: bool = False  # prevents re-adding while restoring


# ── Logging ──────────────────────────────────────────────────────────────────

def _log(msg: str) -> None:
    """Append a message to the log panel."""
    timestamp = time.strftime("%H:%M:%S")
    line = f"[{timestamp}] {msg}"
    _log_lines.append(line)
    # Keep last 200 lines
    if len(_log_lines) > 200:
        _log_lines.pop(0)
    if dpg.does_item_exist("log_text"):
        dpg.set_value("log_text", "\n".join(_log_lines))
        # Auto-scroll
        if dpg.does_item_exist("log_window"):
            dpg.set_y_scroll("log_window", dpg.get_y_scroll_max("log_window"))


# ── Color picker helpers ─────────────────────────────────────────────────────

def _dpg_color_to_rgb(tag: str) -> tuple[int, int, int]:
    """Read a DPG color picker value and return (r, g, b) ints 0-255."""
    val = dpg.get_value(tag)  # [r, g, b, a] floats 0-255
    return (int(val[0]), int(val[1]), int(val[2]))


def _set_dpg_color(tag: str, rgb: tuple[int, int, int]) -> None:
    """Set a DPG color picker to an (r, g, b) value."""
    dpg.set_value(tag, [rgb[0], rgb[1], rgb[2], 255])


# ── Slider helpers ───────────────────────────────────────────────────────────

def _make_empty_cell_rgba(size: int) -> list[float]:
    """Create a solid dark fill for empty canvas cells."""
    data: list[float] = []
    # Subtle dark tone to distinguish empty from painted
    r, g, b, a = 0.14, 0.14, 0.16, 1.0
    for _ in range(size * size):
        data.extend((r, g, b, a))
    return data


def _composite_on_dark(img: Image.Image) -> Image.Image:
    """Composite RGBA image onto a dark background so colors are visible."""
    bg = Image.new("RGBA", img.size, (40, 40, 48, 255))
    bg.paste(img, (0, 0), img)
    return bg


def _update_preview_texture() -> None:
    """Update the 128x128 tile preview.

    In autotile mode: shows the center tile (all neighbors, index 46).
    In standalone mode: shows the single generated tile.
    """
    mode = _canvas.mode if _canvas else "autotile"
    if mode == "standalone" and _standalone_tile is not None:
        tile = _standalone_tile.copy()
    elif _tiles:
        # Show center tile (all neighbors) for a cleaner preview
        center_idx = min(46, len(_tiles) - 1)
        tile = _tiles[center_idx].copy()
    else:
        _log("No tile to preview")
        return
    composited = _composite_on_dark(tile)
    preview_img = scale_nearest(composited, PREVIEW_SCALE)
    data = pil_to_dpg_rgba(preview_img)
    dpg.set_value("preview_texture", data)
    px = composited.getpixel((16, 16))
    _log(f"Preview updated - mode={mode}, sample_px={px}")


def _tile_for_cell(x: int, y: int) -> list[float]:
    """Get the RGBA data for a canvas cell based on current mode."""
    if _canvas is None:
        return _make_empty_cell_rgba(CELL_SIZE)

    if _canvas.mode == "autotile":
        if not _canvas.grid[y][x]:
            return _make_empty_cell_rgba(CELL_SIZE)
        bitmask = compute_bitmask(_canvas.grid, x, y)
        idx = find_closest_bitmask_index(bitmask)
        if idx < len(_tiles):
            composited = _composite_on_dark(_tiles[idx].copy())
            return pil_to_dpg_rgba(composited)
        return _make_empty_cell_rgba(CELL_SIZE)

    # standalone mode — paint the single tile everywhere
    if not _canvas.grid[y][x]:
        return _make_empty_cell_rgba(CELL_SIZE)
    if _standalone_tile is not None:
        composited = _composite_on_dark(_standalone_tile.copy())
        return pil_to_dpg_rgba(composited)
    return _make_empty_cell_rgba(CELL_SIZE)


def _update_cell(x: int, y: int) -> None:
    """Refresh the DPG texture for a single canvas cell."""
    tag = _cell_textures.get((x, y))
    if tag is None:
        return
    data = _tile_for_cell(x, y)
    dpg.set_value(tag, data)


def _update_canvas_region(cx: int, cy: int) -> None:
    """Update the cell and its 8 neighbors (for bitmask recalc)."""
    if _canvas is None:
        return
    for dy in range(-1, 2):
        for dx in range(-1, 2):
            nx, ny = cx + dx, cy + dy
            if 0 <= nx < _canvas.cols and 0 <= ny < _canvas.rows:
                _update_cell(nx, ny)


def _update_all_canvas() -> None:
    """Redraw every cell in the canvas."""
    if _canvas is None:
        return
    for y in range(_canvas.rows):
        for x in range(_canvas.cols):
            _update_cell(x, y)


# ── Callbacks ────────────────────────────────────────────────────────────────

def _push_history() -> None:
    """Save current state to history (unless restoring)."""
    if _restoring_history or _state is None:
        return
    mode = _canvas.mode if _canvas else "autotile"
    ts = time.strftime("%H:%M:%S")
    desc = f"{_state.terrain_name} | s={_state.seed} | sc={_state.scale:.2f}"
    entry = HistoryEntry(
        index=len(_history),
        state=_state,
        mode=mode,
        timestamp=ts,
        description=desc,
    )
    _history.append(entry)
    _rebuild_history_panel()
    _log(f"Historique #{entry.index}: {desc}")


def _rebuild_history_panel() -> None:
    """Recreate the history list UI from _history."""
    if not dpg.does_item_exist("history_list"):
        return
    dpg.delete_item("history_list", children_only=True)
    # Show newest first
    for entry in reversed(_history):
        idx = entry.index
        label = f"#{idx}  [{entry.timestamp}]  {entry.description}  ({entry.mode})"
        dpg.add_selectable(
            label=label,
            parent="history_list",
            callback=_on_history_select,
            user_data=idx,
            tag=f"hist_sel_{idx}",
        )


def _on_history_select(sender: Any = None, app_data: Any = None, user_data: Any = None) -> None:
    """Restore a state from history."""
    global _state, _restoring_history
    if user_data is None or _canvas is None:
        return
    idx = int(user_data)
    if idx < 0 or idx >= len(_history):
        return
    entry = _history[idx]
    _log(f"Restauration historique #{idx}: {entry.description}")
    _restoring_history = True
    # Deselect all history items, then select the clicked one
    for h in _history:
        tag = f"hist_sel_{h.index}"
        if dpg.does_item_exist(tag):
            dpg.set_value(tag, h.index == idx)
    _state = entry.state
    _canvas.mode = entry.mode
    _sync_widgets_from_state()
    # Sync mode radio
    if dpg.does_item_exist("radio_mode"):
        dpg.set_value("radio_mode", entry.mode)
    # Show/hide edge
    if dpg.does_item_exist("edge_header"):
        dpg.configure_item("edge_header", show=(entry.mode == "autotile"))
    # Update export button
    if dpg.does_item_exist("btn_export"):
        lbl = "Exporter Tile PNG" if entry.mode == "standalone" else "Exporter PNG + TSX"
        dpg.configure_item("btn_export", label=lbl)
    _do_regenerate()
    _restoring_history = False


def _do_regenerate() -> None:
    """Regenerate based on current mode (autotile or standalone)."""
    global _tiles, _standalone_tile
    if _state is None:
        _log("ERREUR: Pas d'etat pour regenerer")
        return
    mode = _canvas.mode if _canvas else "autotile"
    start = time.time()

    if mode == "standalone":
        _standalone_tile = generate_standalone_tile(_state, _presets)
        _tiles = []
        elapsed = time.time() - start
        _log(f"Tile standalone generee en {elapsed:.2f}s")
        _update_preview_texture()
        _update_all_canvas()
        if dpg.does_item_exist("status_text"):
            dpg.set_value("status_text", "Tile standalone prete")
    else:
        _tiles = regenerate_tileset(_state, _presets)
        _standalone_tile = None
        elapsed = time.time() - start
        _log(f"{len(_tiles)} autotiles generes en {elapsed:.2f}s")
        _update_preview_texture()
        _update_all_canvas()
        if dpg.does_item_exist("status_text"):
            dpg.set_value("status_text", f"Regenere ({len(_tiles)} tiles)")

    _push_history()


def _read_state_from_widgets() -> AppState:
    """Build a new AppState from current widget values."""
    if _state is None:
        msg = "State not initialised"
        raise RuntimeError(msg)
    return dataclasses.replace(
        _state,
        terrain_name=dpg.get_value("combo_terrain"),
        quality="v2",
        scale=dpg.get_value("slider_scale"),
        octaves=dpg.get_value("slider_octaves"),
        persistence=dpg.get_value("slider_persistence"),
        lacunarity=dpg.get_value("slider_lacunarity"),
        use_smooth_ramp=dpg.get_value("check_smooth_ramp"),
        detail_scale=dpg.get_value("slider_detail_scale"),
        detail_strength=dpg.get_value("slider_detail_strength"),
        use_dithering=dpg.get_value("check_dithering"),
        detail_density=dpg.get_value("slider_detail_density"),
        detail_max_height=dpg.get_value("slider_detail_height"),
        detail_max_length=dpg.get_value("slider_detail_length"),
        edge_style=_EDGE_LABELS.get(dpg.get_value("combo_edge_style"), dpg.get_value("combo_edge_style")),
        edge_width=dpg.get_value("slider_edge_width"),
        edge_noise_scale=dpg.get_value("slider_edge_noise"),
        seed=dpg.get_value("input_seed"),
        output_dir=dpg.get_value("input_output_dir"),
        tsx_dir=dpg.get_value("input_tsx_dir"),
        name=dpg.get_value("combo_terrain"),
        color_shadow=_dpg_color_to_rgb("picker_shadow"),
        color_base=_dpg_color_to_rgb("picker_base"),
        color_highlight=_dpg_color_to_rgb("picker_highlight"),
        color_accent=_dpg_color_to_rgb("picker_accent"),
    )


def _on_param_change(sender: Any = None, app_data: Any = None, _user: Any = None) -> None:
    """Widget value changed -> update state + schedule debounced regen."""
    global _state, _last_change_time, _pending_regen
    try:
        new_state = _read_state_from_widgets()
        # Log what changed
        if _state is not None:
            tag = str(sender) if sender else "?"
            _log(f"Param changed: widget={tag}, value={app_data}")
        _state = new_state
        _last_change_time = time.time()
        _pending_regen = True
    except Exception as exc:
        _log(f"ERROR in param change: {exc}")


def _on_preset_change(sender: Any = None, app_data: Any = None, _user: Any = None) -> None:
    """Preset combo changed -> load preset defaults, update widgets, regen."""
    global _state
    terrain_name = dpg.get_value("combo_terrain")
    _log(f"Preset changed to: {terrain_name}")
    _state = state_from_preset(terrain_name, _presets, "v2")
    _sync_widgets_from_state()
    _do_regenerate()


def _on_random_seed(sender: Any = None, app_data: Any = None, _user: Any = None) -> None:
    """Randomize seed and regenerate."""
    global _state
    new_seed = random.randint(0, 99999)
    dpg.set_value("input_seed", new_seed)
    _log(f"Graine aleatoire: {new_seed}")
    if _state is not None:
        _state = dataclasses.replace(_state, seed=new_seed)
    _do_regenerate()


def _on_clear_canvas(sender: Any = None, app_data: Any = None, _user: Any = None) -> None:
    """Clear the canvas grid."""
    if _canvas is not None:
        _canvas.clear()
        _update_all_canvas()
        _log("Canvas efface")


def _on_mode_change(sender: Any = None, app_data: Any = None, _user: Any = None) -> None:
    """Switch between autotile and standalone mode."""
    if _canvas is None:
        return
    mode = dpg.get_value("radio_mode")
    _canvas.mode = mode
    _canvas.clear()
    # Show/hide edge controls (not relevant for standalone)
    if dpg.does_item_exist("edge_header"):
        dpg.configure_item("edge_header", show=(mode == "autotile"))
    # Update export button label
    if dpg.does_item_exist("btn_export"):
        if mode == "standalone":
            dpg.configure_item("btn_export", label="Exporter Tile PNG")
        else:
            dpg.configure_item("btn_export", label="Exporter PNG + TSX")
    _log(f"Mode: {mode}")
    _do_regenerate()


def _on_export(sender: Any = None, app_data: Any = None, _user: Any = None) -> None:
    """Export based on current mode."""
    if _state is None:
        _log("ERROR: Nothing to export")
        return
    mode = _canvas.mode if _canvas else "autotile"
    try:
        if mode == "standalone" and _standalone_tile is not None:
            png_path = do_export_standalone(_state, _standalone_tile)
            msg = f"Exporte: {png_path.name}"
        elif _tiles:
            png_path, tsx_path = do_export_autotile(_state, _tiles)
            msg = f"Exporte: {png_path.name}, {tsx_path.name}"
        else:
            _log("ERREUR: Rien a exporter")
            return
        _log(msg)
        if dpg.does_item_exist("status_text"):
            dpg.set_value("status_text", msg)
    except (OSError, ValueError) as exc:
        _log(f"Erreur export: {exc}")
        if dpg.does_item_exist("status_text"):
            dpg.set_value("status_text", f"Erreur export: {exc}")


def _sync_widgets_from_state() -> None:
    """Push current _state values into DPG widgets."""
    if _state is None:
        return
    dpg.set_value("combo_terrain", _state.terrain_name)
    dpg.set_value("slider_scale", _state.scale)
    dpg.set_value("slider_octaves", _state.octaves)
    dpg.set_value("slider_persistence", _state.persistence)
    dpg.set_value("slider_lacunarity", _state.lacunarity)
    dpg.set_value("check_smooth_ramp", _state.use_smooth_ramp)
    dpg.set_value("slider_detail_scale", _state.detail_scale)
    dpg.set_value("slider_detail_strength", _state.detail_strength)
    dpg.set_value("check_dithering", _state.use_dithering)
    dpg.set_value("slider_detail_density", _state.detail_density)
    dpg.set_value("slider_detail_height", _state.detail_max_height)
    dpg.set_value("slider_detail_length", _state.detail_max_length)
    dpg.set_value("combo_edge_style", _EDGE_REVERSE.get(_state.edge_style, _state.edge_style))
    dpg.set_value("slider_edge_width", _state.edge_width)
    dpg.set_value("slider_edge_noise", _state.edge_noise_scale)
    dpg.set_value("input_seed", _state.seed)
    dpg.set_value("input_output_dir", _state.output_dir)
    dpg.set_value("input_tsx_dir", _state.tsx_dir)
    # Sync color pickers
    _set_dpg_color("picker_shadow", _state.color_shadow)
    _set_dpg_color("picker_base", _state.color_base)
    _set_dpg_color("picker_highlight", _state.color_highlight)
    _set_dpg_color("picker_accent", _state.color_accent)
    _log("Widgets synced from preset")


# ── Mouse handler ────────────────────────────────────────────────────────────

def _handle_mouse_input() -> None:
    """Check canvas hover + mouse buttons for paint/erase each frame."""
    if _canvas is None or not dpg.does_item_exist("canvas_drawlist"):
        return
    if not dpg.is_item_hovered("canvas_drawlist"):
        return

    mouse_pos = dpg.get_mouse_pos(local=False)
    canvas_rect = dpg.get_item_rect_min("canvas_drawlist")
    rel_x = mouse_pos[0] - canvas_rect[0]
    rel_y = mouse_pos[1] - canvas_rect[1]
    gx, gy = grid_to_canvas_coords(rel_x, rel_y, CELL_SIZE)

    if gx >= _canvas.cols or gy >= _canvas.rows:
        return

    if dpg.is_mouse_button_down(dpg.mvMouseButton_Left):
        _paint_cell(gx, gy)
    elif dpg.is_mouse_button_down(dpg.mvMouseButton_Right):
        _erase_cell(gx, gy)


def _paint_cell(gx: int, gy: int) -> None:
    """Fill a cell. Both modes use the boolean grid."""
    if _canvas is None:
        return
    if _canvas.grid[gy][gx]:
        return
    _canvas.grid[gy][gx] = True
    if _canvas.mode == "autotile":
        _update_canvas_region(gx, gy)
    else:
        _update_cell(gx, gy)


def _erase_cell(gx: int, gy: int) -> None:
    """Clear a cell. Both modes use the boolean grid."""
    if _canvas is None:
        return
    if not _canvas.grid[gy][gx]:
        return
    _canvas.grid[gy][gx] = False
    if _canvas.mode == "autotile":
        _update_canvas_region(gx, gy)
    else:
        _update_cell(gx, gy)


# ── Debounce render callback ────────────────────────────────────────────────

def _frame_tick() -> None:
    """Called each frame — handles debounced regeneration."""
    global _pending_regen
    if _pending_regen and (time.time() - _last_change_time) >= DEBOUNCE_SECONDS:
        _pending_regen = False
        _do_regenerate()


# ── Theme ────────────────────────────────────────────────────────────────────

def _apply_theme() -> None:
    """Apply macOS Sonoma dark mode theme following Apple HIG."""
    # ── macOS system colors (dark mode) ──
    # Backgrounds
    bg_window = (30, 30, 30, 255)        # NSColor.windowBackgroundColor
    bg_sidebar = (44, 44, 46, 255)       # NSColor.controlBackgroundColor
    bg_elevated = (58, 58, 60, 255)      # elevated surface
    bg_control = (72, 72, 74, 255)       # NSColor.tertiarySystemFill
    bg_control_hover = (84, 84, 86, 255)
    bg_control_active = (99, 99, 102, 255)  # NSColor.systemGray

    # Accent (system blue)
    accent = (10, 132, 255, 255)          # NSColor.systemBlue
    accent_hover = (40, 152, 255, 255)
    accent_active = (64, 169, 255, 255)

    # Text
    text_primary = (235, 235, 240, 255)   # NSColor.labelColor
    text_secondary = (174, 174, 178, 255)  # NSColor.secondaryLabelColor

    # Separators & scrollbars
    separator = (68, 68, 70, 120)         # NSColor.separatorColor
    scrollbar_bg = (30, 30, 30, 0)        # transparent (macOS overlay style)
    scrollbar_grab = (110, 110, 115, 140)
    scrollbar_hover = (140, 140, 145, 180)

    # Selection / headers
    header_bg = (44, 44, 46, 255)
    header_hover = (58, 58, 60, 255)
    header_active = (72, 72, 74, 255)

    with dpg.theme() as global_theme:
        with dpg.theme_component(dpg.mvAll):
            # Backgrounds
            dpg.add_theme_color(dpg.mvThemeCol_WindowBg, bg_window)
            dpg.add_theme_color(dpg.mvThemeCol_ChildBg, bg_sidebar)
            dpg.add_theme_color(dpg.mvThemeCol_PopupBg, bg_elevated)
            dpg.add_theme_color(dpg.mvThemeCol_MenuBarBg, bg_sidebar)

            # Controls
            dpg.add_theme_color(dpg.mvThemeCol_FrameBg, bg_control)
            dpg.add_theme_color(dpg.mvThemeCol_FrameBgHovered, bg_control_hover)
            dpg.add_theme_color(dpg.mvThemeCol_FrameBgActive, bg_control_active)

            # Accent elements
            dpg.add_theme_color(dpg.mvThemeCol_SliderGrab, accent)
            dpg.add_theme_color(dpg.mvThemeCol_SliderGrabActive, accent_active)
            dpg.add_theme_color(dpg.mvThemeCol_CheckMark, accent)
            dpg.add_theme_color(dpg.mvThemeCol_Button, accent)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, accent_hover)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, accent_active)

            # Headers (collapsing, selectable)
            dpg.add_theme_color(dpg.mvThemeCol_Header, header_bg)
            dpg.add_theme_color(dpg.mvThemeCol_HeaderHovered, header_hover)
            dpg.add_theme_color(dpg.mvThemeCol_HeaderActive, header_active)

            # Tab (if used)
            dpg.add_theme_color(dpg.mvThemeCol_Tab, bg_sidebar)
            dpg.add_theme_color(dpg.mvThemeCol_TabHovered, bg_elevated)
            dpg.add_theme_color(dpg.mvThemeCol_TabActive, bg_elevated)

            # Text
            dpg.add_theme_color(dpg.mvThemeCol_Text, text_primary)
            dpg.add_theme_color(dpg.mvThemeCol_TextDisabled, text_secondary)

            # Separators & borders
            dpg.add_theme_color(dpg.mvThemeCol_Separator, separator)
            dpg.add_theme_color(dpg.mvThemeCol_Border, separator)

            # Scrollbars (overlay style)
            dpg.add_theme_color(dpg.mvThemeCol_ScrollbarBg, scrollbar_bg)
            dpg.add_theme_color(dpg.mvThemeCol_ScrollbarGrab, scrollbar_grab)
            dpg.add_theme_color(dpg.mvThemeCol_ScrollbarGrabHovered, scrollbar_hover)
            dpg.add_theme_color(dpg.mvThemeCol_ScrollbarGrabActive, scrollbar_hover)

            # Title bar
            dpg.add_theme_color(dpg.mvThemeCol_TitleBg, bg_sidebar)
            dpg.add_theme_color(dpg.mvThemeCol_TitleBgActive, bg_elevated)

            # ── Geometry (macOS HIG) ──
            dpg.add_theme_style(dpg.mvStyleVar_WindowRounding, 10)
            dpg.add_theme_style(dpg.mvStyleVar_ChildRounding, 7)
            dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 5)
            dpg.add_theme_style(dpg.mvStyleVar_PopupRounding, 7)
            dpg.add_theme_style(dpg.mvStyleVar_ScrollbarRounding, 5)
            dpg.add_theme_style(dpg.mvStyleVar_GrabRounding, 5)
            dpg.add_theme_style(dpg.mvStyleVar_TabRounding, 5)
            dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 8, 5)
            dpg.add_theme_style(dpg.mvStyleVar_ItemSpacing, 8, 6)
            dpg.add_theme_style(dpg.mvStyleVar_ItemInnerSpacing, 6, 4)
            dpg.add_theme_style(dpg.mvStyleVar_ScrollbarSize, 8)
            dpg.add_theme_style(dpg.mvStyleVar_WindowPadding, 10, 10)
            dpg.add_theme_style(dpg.mvStyleVar_ChildBorderSize, 1)
    dpg.bind_theme(global_theme)


# ── Layout: labeled sliders ─────────────────────────────────────────────────

def _add_slider_f(label: str, tag: str, val: float, lo: float, hi: float) -> None:
    """Label on line 1, slider on line 2."""
    dpg.add_text(label)
    dpg.add_slider_float(
        default_value=val, min_value=lo, max_value=hi,
        tag=tag, callback=_on_param_change, width=-1,
    )

def _add_slider_i(label: str, tag: str, val: int, lo: int, hi: int) -> None:
    """Label on line 1, slider on line 2."""
    dpg.add_text(label)
    dpg.add_slider_int(
        default_value=val, min_value=lo, max_value=hi,
        tag=tag, callback=_on_param_change, width=-1,
    )


# ── Layout builders ─────────────────────────────────────────────────────────

def _build_left_panel() -> None:
    """Build controls panel with collapsible sections."""
    if _state is None:
        return
    preset_names = sorted(_presets.keys())
    with dpg.child_window(width=LEFT_PANEL_WIDTH, tag="left_panel"):
        # ── Terrain Preset (always visible) ──
        dpg.add_text("Preset terrain")
        dpg.add_combo(
            preset_names, default_value=_state.terrain_name,
            tag="combo_terrain", callback=_on_preset_change, width=-1,
        )
        dpg.add_spacer(height=4)

        # ── Texture ──
        with dpg.collapsing_header(label="Texture", default_open=True):
            _add_slider_f("Scale", "slider_scale", _state.scale, 0.01, 1.0)
            _add_slider_i("Octaves", "slider_octaves", _state.octaves, 1, 8)
            _add_slider_f("Persistence", "slider_persistence", _state.persistence, 0.0, 1.0)
            _add_slider_f("Lacunarite", "slider_lacunarity", _state.lacunarity, 1.0, 4.0)
            dpg.add_checkbox(
                label="Rampe lisse", default_value=_state.use_smooth_ramp,
                tag="check_smooth_ramp", callback=_on_param_change,
            )
            dpg.add_checkbox(
                label="Tramage", default_value=_state.use_dithering,
                tag="check_dithering", callback=_on_param_change,
            )

        # ── Couleurs de palette ──
        with dpg.collapsing_header(label="Couleurs", default_open=True):
            _color_labels = [
                ("Ombre", "picker_shadow", _state.color_shadow),
                ("Base", "picker_base", _state.color_base),
                ("Lumiere", "picker_highlight", _state.color_highlight),
                ("Accent", "picker_accent", _state.color_accent),
            ]
            for label, tag, rgb in _color_labels:
                dpg.add_text(label)
                dpg.add_color_edit(
                    default_value=[rgb[0], rgb[1], rgb[2], 255],
                    tag=tag,
                    no_alpha=True,
                    callback=_on_param_change,
                    width=-1,
                )

        # ── Detail Overlay ──
        with dpg.collapsing_header(label="Detail", default_open=False):
            _add_slider_f("Echelle detail", "slider_detail_scale", _state.detail_scale, 0.0, 2.0)
            _add_slider_f("Intensite", "slider_detail_strength", _state.detail_strength, 0.0, 0.3)
            _add_slider_f("Densite", "slider_detail_density", _state.detail_density, 0.0, 1.0)
            _add_slider_i("Hauteur max", "slider_detail_height", _state.detail_max_height, 1, 16)
            _add_slider_i("Longueur max", "slider_detail_length", _state.detail_max_length, 1, 16)

        # ── Edge (autotile only) ──
        with dpg.collapsing_header(label="Bordure", default_open=False, tag="edge_header"):
            dpg.add_text("Style de bordure")
            dpg.add_combo(
                list(_EDGE_LABELS.keys()),
                default_value=_EDGE_REVERSE.get(_state.edge_style, _state.edge_style),
                tag="combo_edge_style", callback=_on_param_change, width=-1,
            )
            _add_slider_i("Largeur", "slider_edge_width", _state.edge_width, 1, 8)
            _add_slider_f("Echelle bruit", "slider_edge_noise", _state.edge_noise_scale, 0.0, 1.0)

        # ── Seed ──
        with dpg.collapsing_header(label="Graine", default_open=True):
            with dpg.group(horizontal=True):
                dpg.add_input_int(
                    default_value=_state.seed,
                    tag="input_seed", callback=_on_param_change, width=-60,
                )
                dpg.add_button(label="Alea", callback=_on_random_seed, width=50)

        # ── Output ──
        with dpg.collapsing_header(label="Sortie", default_open=False):
            dpg.add_text("Dossier PNG")
            dpg.add_input_text(
                default_value=_state.output_dir,
                tag="input_output_dir", width=-1,
            )
            dpg.add_text("Dossier TSX")
            dpg.add_input_text(
                default_value=_state.tsx_dir,
                tag="input_tsx_dir", width=-1,
            )

        dpg.add_spacer(height=8)
        dpg.add_button(
            label="Regenerer", callback=lambda: _do_regenerate(),
            width=-1, height=30,
        )
        dpg.add_spacer(height=4)
        dpg.add_button(
            label="Exporter PNG + TSX", callback=_on_export,
            width=-1, height=30, tag="btn_export",
        )
        dpg.add_spacer(height=4)
        dpg.add_text("", tag="status_text", color=(180, 220, 200, 255))


def _build_center_panel() -> None:
    """Build center panel: preview + canvas + journal."""
    preview_size = CELL_SIZE * PREVIEW_SCALE  # 128
    canvas_w = CANVAS_COLS * CELL_SIZE
    canvas_h = CANVAS_ROWS * CELL_SIZE

    # Wide enough for canvas + toolbar row (Canvas/mode/help/Effacer)
    CENTER_PANEL_WIDTH = max(canvas_w + 40, 620)

    with dpg.child_window(width=CENTER_PANEL_WIDTH, tag="center_panel"):
        dpg.add_text("Apercu tile (4x)")
        with dpg.drawlist(width=preview_size, height=preview_size):
            dpg.draw_image("preview_texture", (0, 0), (preview_size, preview_size))

        dpg.add_spacer(height=6)
        dpg.add_separator()
        dpg.add_spacer(height=4)

        # ── Selecteur de mode ──
        with dpg.group(horizontal=True):
            dpg.add_text("Canvas")
            dpg.add_spacer(width=12)
            dpg.add_radio_button(
                ["autotile", "standalone"], default_value="autotile",
                tag="radio_mode", callback=_on_mode_change, horizontal=True,
            )
            dpg.add_spacer(width=12)
            dpg.add_text("Gauche=peindre  Droit=effacer", color=(130, 135, 140, 255))
            dpg.add_spacer(width=12)
            dpg.add_button(label="Effacer", callback=_on_clear_canvas)

        dpg.add_spacer(height=4)

        with dpg.drawlist(
            width=canvas_w, height=canvas_h, tag="canvas_drawlist",
        ):
            for y in range(CANVAS_ROWS):
                for x in range(CANVAS_COLS):
                    tex_tag = f"cell_{x}_{y}"
                    x0 = x * CELL_SIZE
                    y0 = y * CELL_SIZE
                    dpg.draw_image(
                        tex_tag, (x0, y0),
                        (x0 + CELL_SIZE, y0 + CELL_SIZE),
                    )


        dpg.add_spacer(height=6)
        dpg.add_separator()
        dpg.add_spacer(height=4)

        # ── Journal ──
        with dpg.collapsing_header(label="Journal", default_open=False):
            with dpg.child_window(height=120, tag="log_window", border=True):
                dpg.add_text("", tag="log_text", wrap=0, color=(160, 170, 160, 255))


def _build_history_panel() -> None:
    """Build right panel: history list."""
    with dpg.child_window(width=-1, tag="history_panel"):
        dpg.add_text("Historique")
        dpg.add_spacer(height=4)
        with dpg.child_window(height=-1, tag="history_list", border=True):
            pass  # filled dynamically by _rebuild_history_panel


def _register_textures() -> None:
    """Register all DPG dynamic textures (preview + canvas cells).

    Uses add_dynamic_texture instead of add_raw_texture for macOS
    Metal backend compatibility.
    """
    preview_size = CELL_SIZE * PREVIEW_SCALE
    preview_data = _make_empty_cell_rgba(preview_size)
    empty_cell = _make_empty_cell_rgba(CELL_SIZE)

    with dpg.texture_registry():
        dpg.add_dynamic_texture(
            preview_size, preview_size, preview_data,
            tag="preview_texture",
        )
        for y in range(CANVAS_ROWS):
            for x in range(CANVAS_COLS):
                tag = f"cell_{x}_{y}"
                dpg.add_dynamic_texture(
                    CELL_SIZE, CELL_SIZE, list(empty_cell),
                    tag=tag,
                )
                _cell_textures[(x, y)] = tag


# ── Main entry point ────────────────────────────────────────────────────────

def run_gui() -> None:
    """Launch the Asset Creator V3 GUI."""
    global _state, _canvas, _tiles, _presets

    dpg.create_context()
    dpg.create_viewport(title="Createur de Tiles V3", width=1400, height=850)

    _presets = get_builtin_presets()
    _state = state_from_preset("grass", _presets, "v2")
    _canvas = CanvasState(cols=CANVAS_COLS, rows=CANVAS_ROWS)

    _apply_theme()
    _register_textures()

    _log("Demarrage Createur de Tiles V3...")
    _log(f"Presets: {sorted(_presets.keys())}")
    _log(f"Preset initial: {_state.terrain_name}, qualite: {_state.quality}")

    # Generation initiale
    _tiles = regenerate_tileset(_state, _presets)
    _log(f"Generation initiale: {len(_tiles)} tiles")
    if _tiles:
        t0 = _tiles[0]
        _log(f"Tile[0] mode={t0.mode}, taille={t0.size}, px(16,16)={t0.getpixel((16, 16))}")

    with dpg.window(tag="primary_window"):
        with dpg.group(horizontal=True):
            _build_left_panel()
            _build_center_panel()
            _build_history_panel()

    # Update preview with generated tiles
    _update_preview_texture()

    # Mouse handler
    with dpg.handler_registry():
        dpg.add_mouse_move_handler(callback=lambda s, d: _handle_mouse_input())

    dpg.setup_dearpygui()
    dpg.show_viewport()
    dpg.set_primary_window("primary_window", True)

    _log("Interface prete")

    # Main loop with debounce tick
    while dpg.is_dearpygui_running():
        _frame_tick()
        dpg.render_dearpygui_frame()

    dpg.destroy_context()
