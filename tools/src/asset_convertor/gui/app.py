"""
Convertisseur Autotile - RPG Maker -> Tiled

Interface customtkinter — architecture dual-toolbar v2 :

  Toolbar 1 (Primaire)  : Type de ressource [🎮 Animé | 🏠 Bâtiment | 🧱 Mur | 🎨 Recolor | 🌱 Sol]
  Toolbar 2 (Secondaire): Contexte dynamique selon le type sélectionné
  Panels (3 colonnes)   : SOURCE | SORTIE | APERÇU (Canvas ou RecolorPanel selon le type)
  Log                   : Journal terminal
  Footer                : Export PNG / TSX + dossier de sortie + barre de statut

Spec : tools/docs/specs/asset_convertor_mv_gui.md
"""

from __future__ import annotations

import dataclasses
import datetime
import logging
import os
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog
from typing import cast

import customtkinter as ctk
from asset_convertor.core.constants import TILE_SIZE
from asset_convertor.core.converter_mv import convert_mv
from asset_convertor.core.converter_mv_a3 import convert_mv_a3
from asset_convertor.core.converter_mv_a4 import convert_mv_a4
from asset_convertor.core.converter_xp import BLOB_BITMASKS, convert_xp
from asset_convertor.core.recolor import extract_palette
from asset_convertor.exporters.tsx_generator import assemble_sheet, export, export_simple_sheet
from asset_convertor.gui.recolor_panel import RecolorPanel
from asset_convertor.gui.state import AppState, RecolorState
from PIL import Image, ImageTk

# ── Configuration UI ─────────────────────────────────────────────────────────

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

OUTPUT_DIR_DEFAULT = str(Path(__file__).parents[3] / "src" / "output")

_CELL_SIZE = TILE_SIZE  # interactive canvas cell size

_GRID_DEFAULT: list[list[bool]] = [
    [False, True,  True,  True,  False],
    [True,  True,  True,  True,  True ],
    [True,  True,  True,  True,  True ],
    [True,  True,  True,  True,  True ],
    [False, True,  True,  True,  False],
]

_BITMASK_TO_IDX: dict[int, int] = {bm: idx for idx, bm in enumerate(BLOB_BITMASKS)}

# 4-neighbor wall bitmask lookup (A4 canvas, WALL_AUTOTILE_TABLE, 16 shapes)
# Derived from WALL_AUTOTILE_TABLE quadrant analysis:
#   qsx=1,2 → interior pixels → neighbor PRESENT on that side
#   qsx=0   → left edge visible  → NO W neighbor
#   qsx=3   → right edge visible → NO E neighbor
#   qsy=0   → top edge visible   → NO N neighbor
#   qsy=3   → bottom edge visible→ NO S neighbor
# Convention: N=2, W=8, E=4, S=1
_WALL_4N_BITMASK_TO_IDX: dict[int, int] = {
    0:  15,  # isolated         — shape 15 [[0,0],[3,0],[0,3],[3,3]] all edges open
    1:  7,   # S                — shape  7 [[0,0],[3,0],[0,1],[3,1]]
    2:  13,  # N                — shape 13 [[0,2],[3,2],[0,3],[3,3]]
    3:  5,   # N+S              — shape  5 [[0,2],[3,2],[0,1],[3,1]]
    4:  11,  # E                — shape 11 [[0,0],[1,0],[0,3],[1,3]]
    5:  3,   # E+S              — shape  3 [[0,0],[1,0],[0,1],[1,1]]
    6:  9,   # N+E              — shape  9 [[0,2],[1,2],[0,3],[1,3]]
    7:  1,   # N+E+S            — shape  1 [[0,2],[1,2],[0,1],[1,1]]
    8:  14,  # W                — shape 14 [[2,0],[3,0],[2,3],[3,3]]
    9:  6,   # W+S              — shape  6 [[2,0],[3,0],[2,1],[3,1]]
    10: 12,  # N+W              — shape 12 [[2,2],[3,2],[2,3],[3,3]]
    11: 4,   # N+W+S            — shape  4 [[2,2],[3,2],[2,1],[3,1]]
    12: 10,  # W+E              — shape 10 [[2,0],[1,0],[2,3],[1,3]]
    13: 2,   # W+E+S            — shape  2 [[2,0],[1,0],[2,1],[1,1]]
    14: 8,   # N+W+E            — shape  8 [[2,2],[1,2],[2,3],[1,3]]
    15: 0,   # N+W+E+S (full)   — shape  0 [[2,2],[1,2],[2,1],[1,1]] all interior
}

_logger = logging.getLogger(__name__)

# Label shown in primary toolbar → internal ResourceType value
_TYPE_LABEL_MAP: dict[str, str] = {
    "🎮 Animé":     "A1",
    "🏠 Bâtiment":  "A3",
    "🧱 Mur":       "A4",
    "🎨 Recolor":   "Recolor",
    "🌱 Sol":       "A2",
}
_LABEL_BY_TYPE: dict[str, str] = {v: k for k, v in _TYPE_LABEL_MAP.items()}


def _compute_cell_bitmask(grid: list[list[bool]], row: int, col: int) -> int:
    """Compute 8-neighbor blob bitmask for a cell. NW=1,N=2,NE=4,W=8,E=16,SW=32,S=64,SE=128."""
    rows = len(grid)
    cols = len(grid[0]) if rows else 0

    def f(r: int, c: int) -> bool:
        return 0 <= r < rows and 0 <= c < cols and grid[r][c]

    n = f(row - 1, col)
    s = f(row + 1, col)
    w = f(row, col - 1)
    e = f(row, col + 1)
    nw = f(row - 1, col - 1) and n and w
    ne = f(row - 1, col + 1) and n and e
    sw = f(row + 1, col - 1) and s and w
    se = f(row + 1, col + 1) and s and e

    return (
        (1 if nw else 0) | (2 if n else 0) | (4 if ne else 0)
        | (8 if w else 0) | (16 if e else 0)
        | (32 if sw else 0) | (64 if s else 0) | (128 if se else 0)
    )


def _compute_wall_bitmask_4n(grid: list[list[bool]], row: int, col: int) -> int:
    """Compute 4-neighbor wall bitmask for A4 canvas. N=2, W=8, E=4, S=1.

    Only reads cardinal neighbors (N/S/E/W). Diagonal neighbors are ignored.
    Returns a value in [0, 15] mapping to WALL_AUTOTILE_TABLE shape index
    via _WALL_4N_BITMASK_TO_IDX.
    """
    rows = len(grid)
    cols = len(grid[0]) if rows else 0

    def f(r: int, c: int) -> bool:
        return 0 <= r < rows and 0 <= c < cols and grid[r][c]

    return (
        (2 if f(row - 1, col) else 0)   # N
        | (8 if f(row, col - 1) else 0)  # W
        | (4 if f(row, col + 1) else 0)  # E
        | (1 if f(row + 1, col) else 0)  # S
    )


# ── Main application ──────────────────────────────────────────────────────────


class App(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Convertisseur Autotile — RPG Maker → Tiled")
        self.geometry("1200x800")
        self.resizable(True, True)
        self.after(0, lambda: self.state("zoomed"))
        self.after(50, self._focus_window)

        # State
        self._state = AppState(output_dir=OUTPUT_DIR_DEFAULT)

        # Animation state
        self._timer_id: str | None = None
        self._current_frame_idx: int = 0
        self._frame_sequence: list[int] = [0]

        # Photo refs (prevent GC)
        self._photo_source: ctk.CTkImage | None = None
        self._photo_output: ctk.CTkImage | None = None
        self._canvas_photos: list[ImageTk.PhotoImage] = []
        self._canvas_grid: list[list[bool]] = [row[:] for row in _GRID_DEFAULT]

        # RecolorPanel ref (created/destroyed on type change)
        self._recolor_panel: RecolorPanel | None = None

        # Log visibility
        self._log_visible_var = tk.BooleanVar(value=True)

        self._setup_icon()
        self._build_ui()
        self._reset_panels()

        if sys.platform == "darwin":
            self._build_macos_menu()

    # ── Startup ───────────────────────────────────────────────────────────────

    def _setup_icon(self) -> None:
        try:
            import AppKit  # type: ignore[import-untyped]
            ns_app = AppKit.NSApplication.sharedApplication()
            icon_path = os.path.join(os.path.dirname(__file__), "assets", "icon.png")
            if os.path.exists(icon_path):
                ns_icon = AppKit.NSImage.alloc().initWithContentsOfFile_(icon_path)
                ns_app.setApplicationIconImage_(ns_icon)
        except (ImportError, AttributeError):
            pass

    def _focus_window(self) -> None:
        self.lift()
        self.focus_force()
        try:
            import AppKit  # type: ignore[import-untyped]
            AppKit.NSApplication.sharedApplication().activateIgnoringOtherApps_(True)
        except (ImportError, AttributeError):
            pass

    # ── macOS Menu ────────────────────────────────────────────────────────────

    def _build_macos_menu(self) -> None:
        menu = tk.Menu(self)
        self.configure(menu=menu)

        file_menu = tk.Menu(menu, tearoff=0)
        menu.add_cascade(label="Fichier", menu=file_menu)
        file_menu.add_command(label="Ouvrir…", command=self._open_file, accelerator="Cmd+O")
        file_menu.add_separator()
        file_menu.add_command(label="Quitter", command=self.quit, accelerator="Cmd+Q")

        view_menu = tk.Menu(menu, tearoff=0)
        menu.add_cascade(label="Affichage", menu=view_menu)
        view_menu.add_checkbutton(
            label="Journal", variable=self._log_visible_var,
            command=self._toggle_log,
        )

    def _toggle_log(self) -> None:
        if self._log_visible_var.get():
            self._log_frame.grid()
        else:
            self._log_frame.grid_remove()

    # ── UI Construction ───────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)  # panels row expands

        self._build_primary_toolbar()
        self._build_secondary_toolbar()
        self._build_panels()
        self._build_log()
        self._build_footer()

    # ── Primary Toolbar (row 0) ───────────────────────────────────────────────

    def _build_primary_toolbar(self) -> None:
        bar = ctk.CTkFrame(self, height=56, corner_radius=0)
        bar.grid(row=0, column=0, sticky="ew", padx=0, pady=0)
        bar.grid_columnconfigure(2, weight=1)  # spacer between seg button and convert

        # Open button
        self.btn_open = ctk.CTkButton(
            bar, text="📂 Ouvrir", width=130, command=self._open_file,
        )
        self.btn_open.grid(row=0, column=0, padx=(12, 8), pady=10)

        # Resource type selector (segmented button)
        self._type_var = ctk.StringVar(value="🌱 Sol")
        self.seg_type = ctk.CTkSegmentedButton(
            bar,
            values=list(_TYPE_LABEL_MAP.keys()),
            variable=self._type_var,
            command=self._on_type_change,
        )
        self.seg_type.grid(row=0, column=1, padx=(4, 4), pady=10)

        # Spacer
        ctk.CTkLabel(bar, text="").grid(row=0, column=2, sticky="ew")

        # Convert / Apply button
        self.btn_convert = ctk.CTkButton(
            bar, text="⚙ Convertir", width=140,
            state="disabled", command=self._run_conversion,
        )
        self.btn_convert.grid(row=0, column=3, padx=(8, 12), pady=10)

    # ── Secondary Toolbar (row 1) ─────────────────────────────────────────────

    def _build_secondary_toolbar(self) -> None:
        self._secondary_bar = ctk.CTkFrame(
            self, height=52, corner_radius=0,
            fg_color=("gray85", "gray17"),
        )
        self._secondary_bar.grid(row=1, column=0, sticky="ew", padx=0, pady=0)
        self._secondary_bar.grid_columnconfigure(0, weight=1)

        # Placeholder — will be replaced on first _swap_secondary call
        self._secondary_content: ctk.CTkFrame = ctk.CTkFrame(
            self._secondary_bar, fg_color="transparent",
        )
        self._secondary_content.grid(row=0, column=0, sticky="ew")

        # Build initial context for A2
        self._swap_secondary("A2")

    def _swap_secondary(self, resource_type: str) -> None:
        """Replace the secondary toolbar content for the given resource type."""
        self._secondary_content.destroy()
        self._secondary_content = ctk.CTkFrame(
            self._secondary_bar, fg_color="transparent",
        )
        self._secondary_content.grid(row=0, column=0, sticky="ew")

        builders = {
            "A2":     self._build_secondary_a2,
            "A3":     self._build_secondary_a3,
            "A4":     self._build_secondary_a4,
            "A1":     self._build_secondary_a1,
            "Recolor": self._build_secondary_recolor,
        }
        builder = builders.get(resource_type, self._build_secondary_a2)
        builder(self._secondary_content)

    def _build_secondary_a2(self, parent: ctk.CTkFrame) -> None:
        """A2: Format selector (MV / XP / MZ-disabled)."""
        ctk.CTkLabel(parent, text="Format :").grid(row=0, column=0, padx=(16, 4), pady=10)
        self._format_var = ctk.StringVar(value=self._state.format)
        for i, fmt in enumerate(("XP", "MV", "MZ")):
            state = "disabled" if fmt == "MZ" else "normal"
            rb = ctk.CTkRadioButton(
                parent, text=fmt, variable=self._format_var,
                value=fmt, state=state,
                command=self._on_format_change,
            )
            rb.grid(row=0, column=1 + i, padx=4)

    def _build_secondary_a3(self, parent: ctk.CTkFrame) -> None:
        """A3: MV only + hint label."""
        ctk.CTkLabel(parent, text="Format :").grid(row=0, column=0, padx=(16, 4), pady=10)
        self._format_var = ctk.StringVar(value="MV")
        ctk.CTkRadioButton(
            parent, text="MV", variable=self._format_var, value="MV",
        ).grid(row=0, column=1, padx=4)
        ctk.CTkLabel(
            parent, text="📐 Source attendue : 768x384 px",
            text_color="gray", font=ctk.CTkFont(size=11),
        ).grid(row=0, column=2, padx=(16, 4))

    def _build_secondary_a4(self, parent: ctk.CTkFrame) -> None:
        """A4: MV only + hint label (produces 2 strips)."""
        ctk.CTkLabel(parent, text="Format :").grid(row=0, column=0, padx=(16, 4), pady=10)
        self._format_var = ctk.StringVar(value="MV")
        ctk.CTkRadioButton(
            parent, text="MV", variable=self._format_var, value="MV",
        ).grid(row=0, column=1, padx=4)
        ctk.CTkLabel(
            parent, text="📐 Source attendue : 768x720 px — Produit 2 strips",
            text_color="gray", font=ctk.CTkFont(size=11),
        ).grid(row=0, column=2, padx=(16, 4))

    def _build_secondary_a1(self, parent: ctk.CTkFrame) -> None:
        """A1: Format selector + animation controls."""
        ctk.CTkLabel(parent, text="Format :").grid(row=0, column=0, padx=(16, 4), pady=10)
        self._format_var = ctk.StringVar(value=self._state.format)
        for i, fmt in enumerate(("XP", "MV", "MZ")):
            state = "disabled" if fmt == "MZ" else "normal"
            rb = ctk.CTkRadioButton(
                parent, text=fmt, variable=self._format_var,
                value=fmt, state=state,
                command=self._on_format_change,
            )
            rb.grid(row=0, column=1 + i, padx=4)

        # Animated state is always True for A1 (no checkbox widget needed)
        self._animated_var = tk.BooleanVar(value=True)

        # Anim type dropdown
        self._anim_type_var = ctk.StringVar(value=self._state.anim_type)
        self.menu_anim_type = ctk.CTkOptionMenu(
            parent, variable=self._anim_type_var,
            values=["Horizontale (Eau/Sol)", "Verticale (Cascade)"],
            width=165, command=self._on_anim_type_change,
        )
        self.menu_anim_type.grid(row=0, column=4, padx=(16, 4))

        # Speed dropdown
        self._speed_var = ctk.StringVar(value=f"{self._state.anim_speed_ms} ms")
        self.menu_speed = ctk.CTkOptionMenu(
            parent, variable=self._speed_var,
            values=["100 ms", "150 ms", "200 ms", "300 ms", "500 ms"],
            width=90, command=self._on_speed_change,
        )
        self.menu_speed.grid(row=0, column=5, padx=4)
        self._update_animation_controls_state()

    def _build_secondary_recolor(self, parent: ctk.CTkFrame) -> None:
        """Recolor: export info only (no format selector)."""
        ctk.CTkLabel(
            parent,
            text="Mode Recolor — export TSX non applicable.",
            text_color="gray", font=ctk.CTkFont(size=11),
        ).grid(row=0, column=0, padx=(16, 4), pady=10)

    # ── Panels (row 2) ────────────────────────────────────────────────────────

    def _build_panels(self) -> None:
        self._panels_container = ctk.CTkFrame(self, fg_color="transparent")
        self._panels_container.grid(row=2, column=0, sticky="nsew", padx=8, pady=4)
        self._panels_container.grid_columnconfigure((0, 1, 2), weight=1)
        self._panels_container.grid_rowconfigure(0, weight=1)

        self._build_source_panel(self._panels_container)
        self._build_output_panel(self._panels_container)
        self._build_canvas_panel(self._panels_container)

    def _build_source_panel(self, parent: ctk.CTkFrame) -> None:
        frame = ctk.CTkFrame(parent)
        frame.grid(row=0, column=0, sticky="nsew", padx=4)
        frame.grid_rowconfigure(1, weight=1)
        frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(frame, text="SOURCE", font=ctk.CTkFont(size=13, weight="bold")).grid(
            row=0, column=0, pady=(8, 4)
        )
        self.lbl_source = ctk.CTkLabel(
            frame, text="Aucun autotile chargé",
            width=220, height=220,
            fg_color=("gray85", "#2a2a2a"), corner_radius=6,
        )
        self.lbl_source.grid(row=1, column=0, padx=8, pady=4, sticky="nsew")
        self.lbl_source_info = ctk.CTkLabel(frame, text="", text_color="gray")
        self.lbl_source_info.grid(row=2, column=0, pady=(2, 8))

    def _build_output_panel(self, parent: ctk.CTkFrame) -> None:
        frame = ctk.CTkFrame(parent)
        frame.grid(row=0, column=1, sticky="nsew", padx=4)
        frame.grid_rowconfigure(1, weight=1)
        frame.grid_columnconfigure(0, weight=1)

        self._lbl_output_title = ctk.CTkLabel(
            frame, text="SORTIE TILED", font=ctk.CTkFont(size=13, weight="bold"),
        )
        self._lbl_output_title.grid(row=0, column=0, pady=(8, 4))

        self.lbl_output = ctk.CTkLabel(
            frame, text="Aucune conversion",
            width=300, height=220,
            fg_color=("gray85", "#2a2a2a"), corner_radius=6,
        )
        self.lbl_output.grid(row=1, column=0, padx=8, pady=4, sticky="nsew")
        self.lbl_output_info = ctk.CTkLabel(frame, text="", text_color="gray")
        self.lbl_output_info.grid(row=2, column=0, pady=(2, 8))

    def _build_canvas_panel(self, parent: ctk.CTkFrame) -> None:
        self._canvas_frame = ctk.CTkFrame(parent)
        self._canvas_frame.grid(row=0, column=2, sticky="nsew", padx=4)
        self._canvas_frame.grid_rowconfigure(1, weight=1)
        self._canvas_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            self._canvas_frame, text="APERÇU CANVAS",
            font=ctk.CTkFont(size=13, weight="bold"),
        ).grid(row=0, column=0, pady=(8, 4))

        canvas_bg = ctk.CTkFrame(
            self._canvas_frame, fg_color=("gray85", "#2a2a2a"), corner_radius=6,
        )
        canvas_bg.grid(row=1, column=0, padx=8, pady=4, sticky="nsew")
        canvas_bg.grid_rowconfigure(0, weight=1)
        canvas_bg.grid_columnconfigure(0, weight=1)

        self.canvas = tk.Canvas(
            canvas_bg, width=160, height=160, bg="#222222", highlightthickness=0,
        )
        self.canvas.grid(row=0, column=0, padx=4, pady=4)
        self.canvas.bind("<Button-1>", self._on_canvas_click)

        btn_frame = ctk.CTkFrame(self._canvas_frame, fg_color="transparent")
        btn_frame.grid(row=2, column=0, pady=(0, 2))
        ctk.CTkButton(
            btn_frame, text="↺ Pattern", width=90, command=self._load_test_pattern,
        ).pack(side="left", padx=2)
        ctk.CTkButton(
            btn_frame, text="✕ Effacer", width=90, command=self._clear_canvas_grid,
        ).pack(side="left", padx=2)

        # A4-only toggle: Mur (sides, 4N) vs Sol (tops, blob)
        self._a4_canvas_mode_var = tk.StringVar(value="Mur")
        self._a4_mode_toggle = ctk.CTkSegmentedButton(
            self._canvas_frame,
            values=["Mur", "Sol"],
            variable=self._a4_canvas_mode_var,
            command=self._on_a4_canvas_mode_change,
            width=180,
        )
        # Hidden by default — only shown for A4
        self._a4_mode_toggle.grid(row=4, column=0, pady=(0, 4))
        self._a4_mode_toggle.grid_remove()

        self.lbl_canvas_info = ctk.CTkLabel(self._canvas_frame, text="", text_color="gray")
        self.lbl_canvas_info.grid(row=3, column=0, pady=(2, 2))

    def _switch_right_panel_to_recolor(self) -> None:
        """Replace canvas panel with RecolorPanel."""
        if self._recolor_panel is not None:
            return  # already installed

        # Hide canvas widgets
        self._canvas_frame.grid_remove()

        # Create and show RecolorPanel in column 2
        self._recolor_panel = RecolorPanel(
            parent=self._panels_container,
            state=self._state,
            on_state_change=self._on_recolor_state_change,
            on_preview_update=self._on_recolor_preview_ready,
        )
        self._recolor_panel.grid(row=0, column=2, sticky="nsew", padx=4)

        # Update output panel title
        self._lbl_output_title.configure(text="APERÇU RECOLOR")

    def _switch_right_panel_to_canvas(self) -> None:
        """Restore canvas panel, destroy RecolorPanel."""
        if self._recolor_panel is not None:
            self._recolor_panel.destroy()
            self._recolor_panel = None
        self._canvas_frame.grid()
        self._lbl_output_title.configure(text="SORTIE TILED")

    # ── Log (row 3) ───────────────────────────────────────────────────────────

    def _build_log(self) -> None:
        self._log_frame = ctk.CTkFrame(self, corner_radius=0)
        self._log_frame.grid(row=3, column=0, sticky="ew", padx=0, pady=0)
        self._log_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            self._log_frame, text="Journal :", font=ctk.CTkFont(size=11),
        ).grid(row=0, column=0, padx=(12, 6), pady=4, sticky="w")

        self.txt_log = ctk.CTkTextbox(
            self._log_frame, height=64,
            font=ctk.CTkFont(family="Courier", size=11),
            fg_color=("gray10", "#0a0a0a"), text_color="#8fbcbb",
            activate_scrollbars=True,
        )
        self.txt_log.grid(row=0, column=1, padx=(0, 8), pady=4, sticky="ew")
        self.txt_log.configure(state="disabled")

    # ── Footer (row 4) ────────────────────────────────────────────────────────

    def _build_footer(self) -> None:
        footer = ctk.CTkFrame(self, height=44, corner_radius=0)
        footer.grid(row=4, column=0, sticky="ew", padx=0, pady=0)
        footer.grid_columnconfigure(4, weight=1)

        # Export checkboxes
        self._export_png_var = tk.BooleanVar(value=True)
        self._export_tsx_var = tk.BooleanVar(value=True)

        self.btn_export = ctk.CTkButton(
            footer, text="💾 Exporter", width=130,
            state="disabled", command=self._export,
        )
        self.btn_export.grid(row=0, column=0, padx=(12, 4), pady=8)

        self.cb_export_png = ctk.CTkCheckBox(
            footer, text="PNG",
            variable=self._export_png_var, state="disabled", width=60,
        )
        self.cb_export_png.grid(row=0, column=1, padx=4)

        self.cb_export_tsx = ctk.CTkCheckBox(
            footer, text="TSX",
            variable=self._export_tsx_var, width=60,
        )
        self.cb_export_tsx.grid(row=0, column=2, padx=4)

        ctk.CTkLabel(footer, text="Dossier :").grid(row=0, column=3, padx=(8, 2))

        self._output_dir_var = ctk.StringVar(value=self._state.output_dir)
        self.entry_output_dir = ctk.CTkEntry(
            footer, textvariable=self._output_dir_var, width=280,
        )
        self.entry_output_dir.grid(row=0, column=4, padx=(0, 4), pady=8, sticky="ew")

        ctk.CTkButton(
            footer, text="📂", width=36, command=self._pick_output_dir,
        ).grid(row=0, column=5, padx=(0, 8))

        self.lbl_status = ctk.CTkLabel(
            footer, text="État : Prêt.", text_color="gray", anchor="w",
        )
        self.lbl_status.grid(row=0, column=6, padx=(8, 12), sticky="ew")

    # ── Handlers — Primary Toolbar ────────────────────────────────────────────

    def _open_file(self) -> None:
        path = filedialog.askopenfilename(
            title="Ouvrir un autotile",
            filetypes=[("Images PNG", "*.png"), ("Tous les fichiers", "*.*")],
        )
        if not path:
            return

        try:
            img = Image.open(path).convert("RGBA")
        except OSError:
            self._set_status(
                "Impossible de lire l'image. Vérifiez que le fichier est un PNG valide.",
                error=True,
            )
            return

        self._stop_animation()

        resource_type = _TYPE_LABEL_MAP[self._type_var.get()]

        # Validate dimensions for non-Recolor types
        if resource_type != "Recolor":
            fmt = getattr(self, "_format_var", None)
            fmt_val = fmt.get() if fmt else self._state.format
            error = self._validate_dimensions(img, resource_type, fmt_val)
            if error:
                self._set_status(error, error=True)
                self.btn_convert.configure(state="disabled")
                return

        # Build new state
        new_state = dataclasses.replace(
            self._state,
            source_path=path,
            source_img=img,
            resource_type=resource_type,  # type: ignore[arg-type]
            output_dir=self._output_dir_var.get(),
        )

        # For Recolor: extract palette immediately
        if resource_type == "Recolor":
            try:
                palette = extract_palette(img)
                rs = RecolorState(source_palette=palette)
                new_state = dataclasses.replace(new_state, recolor=rs, export_tsx=False)
            except ValueError as exc:
                self._set_status(f"⚠️ Image vide — {exc}", error=True)
                return

        self._state = new_state
        self._display_source(img, Path(path).name, resource_type)
        self.btn_convert.configure(state="normal")
        self._set_status(f"Fichier chargé : {Path(path).name}")

        # Update RecolorPanel if active
        if self._recolor_panel is not None and resource_type == "Recolor":
            self._recolor_panel.update_state(self._state)

    def _on_type_change(self, label: str) -> None:
        """User selected a new resource type in the primary toolbar."""
        resource_type = _TYPE_LABEL_MAP.get(label, "A2")
        self._stop_animation()

        # Update secondary toolbar
        self._swap_secondary(resource_type)

        # Swap right panel
        if resource_type == "Recolor":
            self._switch_right_panel_to_recolor()
            self._export_tsx_var.set(False)
            self.cb_export_tsx.configure(state="disabled")
            self.btn_convert.configure(text="✨ Appliquer Recolor")
        else:
            self._switch_right_panel_to_canvas()
            self._export_tsx_var.set(True)
            self.cb_export_tsx.configure(state="normal")
            self.btn_convert.configure(text="⚙ Convertir")

        export_tsx = resource_type != "Recolor"

        # Update state — preserve source and recolor only when switching to Recolor
        if resource_type == "Recolor" and self._state.recolor is None:
            rs: RecolorState | None = RecolorState() if self._state.source_img is not None else None
            # Try palette extraction if source exists
            if self._state.source_img is not None:
                try:
                    palette = extract_palette(self._state.source_img)
                    rs = RecolorState(source_palette=palette)
                except ValueError:
                    rs = RecolorState()
        else:
            rs = self._state.recolor if resource_type == "Recolor" else None

        is_animated = (resource_type == "A1")
        self._state = dataclasses.replace(
            self._state,
            resource_type=resource_type,  # type: ignore[arg-type]
            export_tsx=export_tsx,
            recolor=rs,
            result_img=None,
            animated=is_animated,
        )

        # Disable convert if no source
        if self._state.source_img is None:
            self.btn_convert.configure(state="disabled")

        self._reset_output_panel()

        # Show/hide the A4 canvas mode toggle
        if resource_type == "A4":
            self._a4_canvas_mode_var.set("Mur")
            self._a4_mode_toggle.grid()
        else:
            self._a4_mode_toggle.grid_remove()

        # Update recolor panel if newly created and we have data
        if self._recolor_panel is not None and self._state.recolor:
            self._recolor_panel.update_state(self._state)

    def _on_format_change(self) -> None:
        new_fmt = self._format_var.get()
        if new_fmt == "MZ":
            self._log("i Format MZ non encore supporté.")
            self._format_var.set(self._state.format)
            return
        self._state = dataclasses.replace(
            self._state, format=new_fmt,  # type: ignore[arg-type]
        )
        self._stop_animation()
        self.btn_export.configure(state="disabled")

    def _on_anim_type_change(self, value: str) -> None:
        self._state = dataclasses.replace(self._state, anim_type=value)

    def _on_speed_change(self, value: str) -> None:
        try:
            ms = int(value.replace(" ms", "").strip())
        except ValueError:
            ms = 150
        self._state = dataclasses.replace(self._state, anim_speed_ms=ms)
        # Restart animation timer if running
        if self._timer_id is not None and self._state.tiles:
            self.after_cancel(self._timer_id)
            self._timer_id = self.after(ms, self._tick_animation)

    def _update_animation_controls_state(self) -> None:
        is_anim = getattr(self, "_animated_var", None)
        if is_anim is None:
            return
        anim_on = is_anim.get()
        fmt = getattr(self, "_format_var", None)
        mode = fmt.get() if fmt else "MV"
        if hasattr(self, "menu_speed"):
            self.menu_speed.configure(state="normal" if anim_on else "disabled")
        if hasattr(self, "menu_anim_type"):
            if anim_on and mode == "XP":
                getattr(self, "_anim_type_var", ctk.StringVar()).set("Horizontale (Eau/Sol)")
                self.menu_anim_type.configure(state="disabled")
            elif anim_on:
                self.menu_anim_type.configure(state="normal")
            else:
                self.menu_anim_type.configure(state="disabled")

    # ── Conversion dispatch ───────────────────────────────────────────────────

    def _run_conversion(self) -> None:
        if self._state.source_img is None:
            self._log("⚠️ Aucun fichier source chargé.")
            return
        if self._state.resource_type == "Recolor" and (
            self._state.recolor is None or not self._state.recolor.remap_table
        ):
            self._log("⚠️ Définissez d'abord un remappage (choisissez une palette).")
            return

        self._stop_animation()
        self._set_status("Conversion en cours…")
        self.btn_convert.configure(state="disabled")

        dispatch = {
            "A2":     self._convert_a2,
            "A3":     self._convert_a3,
            "A4":     self._convert_a4,
            "A1":     self._convert_a1,
            "Recolor": self._apply_recolor,
        }
        handler = dispatch.get(self._state.resource_type)
        if handler:
            threading.Thread(target=handler, daemon=True).start()

    def _convert_a2(self) -> None:
        """A2 Ground (or A1 animated) — dispatches to convert_xp or convert_mv based on format."""
        try:
            img = self._state.source_img
            assert img is not None
            fmt = getattr(self, "_format_var", None)
            fmt_val = fmt.get() if fmt else self._state.format
            is_anim = getattr(self, "_animated_var", tk.BooleanVar()).get()
            anim_str = getattr(self, "_anim_type_var", ctk.StringVar(value="Horizontale")).get()
            anim_mode = "Horizontale" if "Horizontale" in anim_str else "Verticale"

            if fmt_val == "XP":
                tiles = convert_xp(img, is_animated=is_anim, animation_mode=anim_mode)
                tile_size = 32
            else:  # MV / MZ
                tiles = convert_mv(img, is_animated=is_anim, animation_mode=anim_mode)
                tile_size = tiles[0][0].width if tiles and tiles[0] else 48

            result_img = self._build_sheet_image(tiles, tile_size)

            self._state = dataclasses.replace(
                self._state,
                result_img=result_img,
                tiles=tiles,
                tile_size=tile_size,
            )
            self.after(0, lambda: self._on_convert_success_a2(tiles, tile_size))
        except Exception as err:
            msg = str(err)
            self.after(0, lambda m=msg: self._on_convert_error(m))

    def _convert_a3(self) -> None:
        """A3 Building — convert_mv_a3(img)."""
        try:
            img = self._state.source_img
            assert img is not None
            result_img = convert_mv_a3(img)
            tile_size = 48

            self._state = dataclasses.replace(
                self._state,
                result_img=result_img,
                tiles=None,     # A3 uses result_img directly
                tile_size=tile_size,
            )
            self.after(0, lambda: self._on_convert_success_single(result_img, "A3", tile_size))
        except Exception as err:
            msg = str(err)
            self.after(0, lambda m=msg: self._on_convert_error(m))

    def _convert_a4(self) -> None:
        """A4 Wall — convert_mv_a4(img) → 2 strips, stitched for preview."""
        try:
            img = self._state.source_img
            assert img is not None
            tops_img, sides_img = convert_mv_a4(img)

            # Stitch vertically for single-image preview (SORTIE TILED panel)
            total_h = tops_img.height + sides_img.height
            max_w = max(tops_img.width, sides_img.width)
            stitched = Image.new("RGBA", (max_w, total_h))
            stitched.paste(tops_img, (0, 0))
            stitched.paste(sides_img, (0, tops_img.height))

            # Extract tile_size dynamically (32px or 48px) from sides strip.
            tile_size = sides_img.width // 16

            # 16 wall-side tiles (WALL_AUTOTILE_TABLE, 4-neighbor canvas)
            wall_side_tiles: list[Image.Image] = [
                sides_img.crop((i * tile_size, 0, (i + 1) * tile_size, tile_size))
                for i in range(16)
            ]

            # 47 wall-top tiles from the first row of tops_img (FLOOR_AUTOTILE_TABLE, blob canvas)
            # tops_img is 8 cols × 6 rows; tile slot i is at col=i%8, row=i//8
            wall_top_tiles: list[Image.Image] = [
                tops_img.crop((
                    (i % 8) * tile_size,
                    (i // 8) * tile_size,
                    (i % 8 + 1) * tile_size,
                    (i // 8 + 1) * tile_size,
                ))
                for i in range(47)
            ]

            self._state = dataclasses.replace(
                self._state,
                result_img=stitched,
                tiles=wall_side_tiles,
                tile_size=tile_size,
            )
            # Store strips for export and both tile lists for canvas switching
            self._a4_tops: Image.Image = tops_img
            self._a4_sides: Image.Image = sides_img
            self._a4_wall_side_tiles: list[Image.Image] = wall_side_tiles
            self._a4_wall_top_tiles: list[Image.Image] = wall_top_tiles

            self.after(0, lambda: self._on_convert_success_a4(stitched, wall_side_tiles, tile_size))
        except Exception as err:
            msg = str(err)
            self.after(0, lambda m=msg: self._on_convert_error(m))

    def _convert_a1(self) -> None:
        """A1 Animated — reuse convert_mv (animated path)."""
        self._convert_a2()  # A1 uses the same convert_mv with is_animated=True

    def _apply_recolor(self) -> None:
        """Recolor — apply current remap table to source image."""
        try:
            from asset_convertor.core.recolor import apply_remap
            img = self._state.source_img
            rs = self._state.recolor
            assert img is not None
            assert rs is not None
            result = apply_remap(img, rs.remap_table)
            rs_updated = dataclasses.replace(rs, result_img=result)
            self._state = dataclasses.replace(
                self._state, result_img=result, recolor=rs_updated,
            )
            self.after(0, lambda: self._on_convert_success_single(result, "Recolor", 48))
        except Exception as err:
            msg = str(err)
            self.after(0, lambda m=msg: self._on_convert_error(m))

    # ── Convert success callbacks (main thread) ───────────────────────────────

    def _on_convert_success_a2(
        self, tiles: list[list[Image.Image]] | list[Image.Image], tile_size: int
    ) -> None:
        self.btn_convert.configure(state="normal")
        self.btn_export.configure(state="normal")
        self._display_output_sheet(tiles, tile_size)
        self._draw_canvas_pattern(tiles, tile_size)
        self._set_status("Conversion réussie.")

        is_anim = getattr(self, "_animated_var", tk.BooleanVar()).get()
        if is_anim and isinstance(tiles, list) and tiles and isinstance(tiles[0], list):
            tiles_list = cast(list[list[Image.Image]], tiles)
            num_frames = len(tiles_list)
            self._setup_animation(num_frames)

    def _on_convert_success_a4(
        self,
        result_img: Image.Image,
        wall_side_tiles: list[Image.Image],
        tile_size: int,
    ) -> None:
        """A4 success: show stitched preview in SORTIE panel, draw default Mur canvas."""
        self.btn_convert.configure(state="normal")
        self.btn_export.configure(state="normal")
        self._display_result_image(result_img)
        w, h = result_img.size
        self.lbl_output_info.configure(text=f"A4 : {w}x{h} px")
        self._set_status(f"A4 : conversion réussie — {w}x{h} px.")
        # Default to Mur (sides) canvas
        self._a4_canvas_mode_var.set("Mur")
        self._draw_canvas_pattern(wall_side_tiles, tile_size)

    def _on_a4_canvas_mode_change(self, mode: str) -> None:
        """Switch canvas between Mur (4-neighbor sides) and Sol (blob tops)."""
        if not hasattr(self, "_a4_wall_side_tiles"):
            return
        tile_size = self._state.tile_size
        if mode == "Sol":
            tiles: list[Image.Image] = self._a4_wall_top_tiles
            # Temporarily override state tiles to blob for _redraw_canvas_grid
            self._state = dataclasses.replace(self._state, tiles=tiles)
            self._canvas_grid = [row[:] for row in _GRID_DEFAULT]
            self._redraw_canvas_grid()
            self.lbl_canvas_info.configure(
                text="Cliquez pour dessiner — bitmask 8-voisins (Sol/Toit)"
            )
        else:
            tiles = self._a4_wall_side_tiles
            self._state = dataclasses.replace(self._state, tiles=tiles)
            self._canvas_grid = [row[:] for row in _GRID_DEFAULT]
            self._redraw_canvas_grid()
            self.lbl_canvas_info.configure(
                text="Cliquez pour dessiner — bitmask 4-voisins (Mur)"
            )

    def _on_convert_success_single(
        self, result_img: Image.Image, label: str, tile_size: int
    ) -> None:
        self.btn_convert.configure(state="normal")
        self.btn_export.configure(state="normal")
        self._display_result_image(result_img)
        w, h = result_img.size
        self.lbl_output_info.configure(text=f"{label} : {w}x{h} px")
        self._set_status(f"{label} : conversion réussie — {w}x{h} px.")

    def _on_convert_error(self, message: str) -> None:
        self.btn_convert.configure(state="normal")
        self._set_status(f"❌ Erreur de conversion : {message}", error=True)

    # ── Recolor panel callbacks ───────────────────────────────────────────────

    def _on_recolor_state_change(self, new_state: AppState) -> None:
        """Called by RecolorPanel when remap table or preset changes."""
        self._state = new_state

    def _on_recolor_preview_ready(self, result: Image.Image) -> None:
        """Called by RecolorPanel when live preview image is ready."""
        self._display_result_image(result)

    # ── Export ────────────────────────────────────────────────────────────────

    def _export(self) -> None:
        if self._state.source_path is None:
            return

        out_dir = self._output_dir_var.get().strip() or OUTPUT_DIR_DEFAULT
        name = Path(self._state.source_path).stem

        resource_type = self._state.resource_type

        if resource_type == "A4":
            self._export_a4(out_dir, name)
        elif resource_type == "Recolor":
            self._export_recolor(out_dir, name)
        else:
            self._export_standard(out_dir, name)

    def _export_standard(self, out_dir: str, name: str) -> None:
        """Export A1/A2/A3 as PNG (+ TSX if checked)."""
        if not self._state.result_img:
            return
        try:
            export_tsx = self._export_tsx_var.get()
            is_animated = self._state.animated
            anim_str = getattr(self, "_anim_type_var", ctk.StringVar(value="Horizontale")).get()
            anim_mode = "Horizontale" if "Horizontale" in anim_str else "Verticale"

            if self._state.tiles and self._state.resource_type in ("A1", "A2"):
                # Use full export pipeline for A1/A2
                tiles_2d: list[list[Image.Image]] = (
                    [self._state.tiles]  # type: ignore[list-item]
                    if self._state.tiles and not isinstance(self._state.tiles[0], list)
                    else cast(list[list[Image.Image]], self._state.tiles)
                )
                png_path, tsx_path = export(
                    tiles_2d,
                    name, out_dir,
                    self._state.tile_size,
                    is_animated=is_animated,
                    animation_mode=anim_mode,
                    duration=self._state.anim_speed_ms,
                )
                status = f"Exporté : {Path(png_path).name}"
                if tsx_path and export_tsx:
                    status += f" + {Path(tsx_path).name}"
            else:
                # A3: simple grid tileset export (no wangset)
                os.makedirs(out_dir, exist_ok=True)
                img = self._state.result_img
                tile_size = self._state.tile_size
                cols = img.width // tile_size
                if export_tsx:
                    png_path, tsx_path = export_simple_sheet(
                        img, name, out_dir, tile_size, columns=cols,
                    )
                    status = f"Exporté : {Path(png_path).name} + {Path(tsx_path).name} → {out_dir}"
                else:
                    png_path = os.path.join(out_dir, f"{name}.png")
                    img.save(png_path)
                    status = f"Exporté : {Path(png_path).name} → {out_dir}"

            self._set_status(status)
        except (OSError, PermissionError) as exc:
            self._set_status(f"Impossible d'écrire dans {out_dir}. ({exc})", error=True)
        except ValueError as exc:
            self._set_status(f"Erreur interne : {exc}", error=True)

    def _export_a4(self, out_dir: str, name: str) -> None:
        """Export A4 as two PNG files (+ TSX if checked).

        - tops strip:  plain grid TSX (no wangset) via export_simple_sheet
        - sides strip: edge-wangset TSX (16 tiles, 4-neighbor) via export_wall_sides_sheet
        """
        if not hasattr(self, "_a4_tops"):
            return
        try:
            from asset_convertor.exporters.tsx_generator import (
                export_wall_sides_sheet, export_blob_tops_sheet,
            )

            export_tsx = self._export_tsx_var.get()
            tile_size = self._state.tile_size
            os.makedirs(out_dir, exist_ok=True)
            status_parts: list[str] = []

            # Tops strip — blob wangset (mixed, 47 shapes, FLOOR_AUTOTILE_TABLE)
            # Same format as A2 — appears in Tiled's Terrain collection.
            tops_name = f"{name}_tops"
            if export_tsx:
                png_path, tsx_path = export_blob_tops_sheet(
                    self._a4_tops, tops_name, out_dir, tile_size,
                )
                status_parts.append(f"{Path(png_path).name} + {Path(tsx_path).name}")
            else:
                png_path = os.path.join(out_dir, f"{tops_name}.png")
                self._a4_tops.save(png_path)
                status_parts.append(Path(png_path).name)


            # Sides strip — edge wangset TSX (16 tiles, 4-neighbor wall system)
            sides_name = f"{name}_sides"
            if export_tsx:
                png_path, tsx_path = export_wall_sides_sheet(
                    self._a4_sides, sides_name, out_dir, tile_size,
                )
                status_parts.append(f"{Path(png_path).name} + {Path(tsx_path).name}")
            else:
                png_path = os.path.join(out_dir, f"{sides_name}.png")
                self._a4_sides.save(png_path)
                status_parts.append(Path(png_path).name)

            self._set_status(f"A4 exporté : {' | '.join(status_parts)} → {out_dir}")
        except (OSError, PermissionError) as exc:
            self._set_status(f"Impossible d'écrire dans {out_dir}. ({exc})", error=True)
        except ValueError as exc:
            self._set_status(f"Erreur A4 : {exc}", error=True)

    def _export_recolor(self, out_dir: str, name: str) -> None:
        """Export recolored image as PNG."""
        rs = self._state.recolor
        if rs is None or rs.result_img is None:
            self._set_status("Appliquez d'abord le recolor avant d'exporter.", error=True)
            return
        try:
            os.makedirs(out_dir, exist_ok=True)
            png_path = os.path.join(out_dir, f"{name}_recolor.png")
            rs.result_img.save(png_path)
            self._set_status(f"Recolor exporté : {Path(png_path).name} → {out_dir}")
        except (OSError, PermissionError) as exc:
            self._set_status(f"Impossible d'écrire dans {out_dir}. ({exc})", error=True)

    def _pick_output_dir(self) -> None:
        d = filedialog.askdirectory(title="Dossier de sortie")
        if d:
            self._output_dir_var.set(d)
            self._state = dataclasses.replace(self._state, output_dir=d)

    # ── Validation ────────────────────────────────────────────────────────────

    def _validate_dimensions(
        self, img: Image.Image, resource_type: str, fmt: str,
    ) -> str | None:
        """Return error message or None if valid."""
        w, h = img.size
        is_anim = getattr(self, "_animated_var", tk.BooleanVar(value=False)).get()
        anim_str = getattr(self, "_anim_type_var", ctk.StringVar(value="Horizontale")).get()
        anim_mode = "Horizontale" if "Horizontale" in anim_str else "Verticale"

        if resource_type in ("A2", "A1"):
            if fmt == "XP":
                return self._validate_xp_dimensions(w, h, is_anim, anim_mode)
            return self._validate_mv_dimensions(w, h, is_anim, anim_mode, fmt)
        # A3 / A4 validation is done inside the converter itself
        return None

    def _validate_xp_dimensions(self, w: int, h: int, is_anim: bool, anim_mode: str) -> str | None:
        if is_anim:
            if anim_mode == "Verticale":
                return "L'animation verticale n'est pas supportée pour le format XP."
            if w % 96 != 0 or h != 128:
                return f"Format XP (Horizontale) invalide. Attendu : largeur multiple de 96px et hauteur 128px, obtenu : {w}x{h}"
        else:
            if w != 96 or h != 128:
                return f"Format XP statique invalide. Attendu : 96x128 px, obtenu : {w}x{h}"
        return None

    def _validate_mv_dimensions(self, w: int, h: int, is_anim: bool, anim_mode: str, mode: str) -> str | None:
        if is_anim:
            if anim_mode == "Horizontale":
                if h not in (96, 144):
                    return f"Format {mode} (Horizontale) invalide. Attendu : hauteur 96 ou 144 px, obtenu : {w}x{h}"
                tile_size = h // 3
                if w % (2 * tile_size) != 0:
                    return f"Format {mode} (Horizontale) invalide. Attendu : largeur multiple de {2 * tile_size}px, obtenu : {w}x{h}"
            else:
                if w not in (64, 96):
                    return f"Format {mode} (Verticale) invalide. Attendu : largeur 64 ou 96 px, obtenu : {w}x{h}"
                tile_size = w // 2
                if h % tile_size != 0:
                    return f"Format {mode} (Verticale) invalide. Attendu : hauteur multiple de {tile_size}px, obtenu : {w}x{h}"
        else:
            if (w, h) not in ((64, 96), (96, 144)):
                return f"Format {mode} statique invalide. Attendu : 64x96 ou 96x144 px, obtenu : {w}x{h}"
        return None

    # ── Display helpers ───────────────────────────────────────────────────────

    def _display_source(self, img: Image.Image, filename: str, resource_type: str) -> None:
        scaled = self._scale_to_fit(img, 200, 200)
        photo_source = ctk.CTkImage(
            light_image=scaled, dark_image=scaled, size=(scaled.width, scaled.height),
        )
        self.lbl_source.configure(image=photo_source, text="")
        self._photo_source = photo_source
        w, h = img.size
        self.lbl_source_info.configure(text=f"{filename}  |  {resource_type} / {w}x{h}")

    def _display_result_image(self, img: Image.Image) -> None:
        """Display a single PIL Image in the output panel."""
        scaled = self._scale_to_fit(img, 320, 280)
        photo_output = ctk.CTkImage(
            light_image=scaled, dark_image=scaled, size=(scaled.width, scaled.height),
        )
        self.lbl_output.configure(image=photo_output, text="")
        self._photo_output = photo_output

    def _display_output_sheet(
        self,
        tiles: list[list[Image.Image]] | list[Image.Image],
        tile_size: int,
    ) -> None:
        if tiles and isinstance(tiles[0], list):
            tiles_by_frame = cast(list[list[Image.Image]], tiles)
        else:
            tiles_by_frame = [cast(list[Image.Image], tiles)]

        sheet = assemble_sheet(tiles_by_frame, tile_size)
        self._display_result_image(sheet)
        num_frames = len(tiles_by_frame)
        self.lbl_output_info.configure(
            text=f"Tuile : {tile_size}px  |  Sortie : {8*tile_size}x{6*num_frames*tile_size}"
        )

    def _reset_output_panel(self) -> None:
        self.lbl_output.configure(image=None, text="Aucune conversion")
        self.lbl_output_info.configure(text="")

    def _reset_panels(self) -> None:
        self.lbl_source.configure(image=None, text="Aucun autotile chargé")
        self.lbl_source_info.configure(text="")
        self._reset_output_panel()
        self.canvas.delete("all")
        self._canvas_photos = []
        self._canvas_grid = [[False] * len(_GRID_DEFAULT[0]) for _ in _GRID_DEFAULT]
        self.lbl_canvas_info.configure(text="")

    @staticmethod
    def _scale_to_fit(img: Image.Image, max_w: int, max_h: int) -> Image.Image:
        scale = min(max_w / img.width, max_h / img.height)
        if abs(scale - 1.0) < 1e-6:
            return img
        new_w = max(1, int(img.width * scale))
        new_h = max(1, int(img.height * scale))
        return img.resize((new_w, new_h), Image.NEAREST)

    @staticmethod
    def _build_sheet_image(
        tiles: list[list[Image.Image]] | list[Image.Image], tile_size: int,
    ) -> Image.Image:
        """Assemble tiles into a sheet for display."""
        if tiles and isinstance(tiles[0], list):
            tiles_by_frame = cast(list[list[Image.Image]], tiles)
        else:
            tiles_by_frame = [cast(list[Image.Image], tiles)]
        return assemble_sheet(tiles_by_frame, tile_size)

    # ── Animation ────────────────────────────────────────────────────────────

    def _setup_animation(self, num_frames: int) -> None:
        is_anim = getattr(self, "_animated_var", tk.BooleanVar()).get()
        anim_str = getattr(self, "_anim_type_var", ctk.StringVar(value="Horizontale")).get()
        if is_anim and num_frames > 1:
            if "Horizontale" in anim_str and num_frames == 3:
                self._frame_sequence = [0, 1, 2, 1]
            elif "Verticale" in anim_str and num_frames == 3:
                self._frame_sequence = [0, 1, 2]
            elif num_frames == 4:
                self._frame_sequence = [0, 1, 2, 3]
            else:
                self._frame_sequence = list(range(num_frames))
            self._current_frame_idx = 0
            ms = self._state.anim_speed_ms
            self._timer_id = self.after(ms, self._tick_animation)

    def _stop_animation(self) -> None:
        if self._timer_id is not None:
            self.after_cancel(self._timer_id)
            self._timer_id = None
        self._current_frame_idx = 0
        self._frame_sequence = [0]

    def _tick_animation(self) -> None:
        tiles = self._state.tiles
        if not tiles:
            self._timer_id = None
            return
        self._current_frame_idx = (self._current_frame_idx + 1) % len(self._frame_sequence)
        self._redraw_canvas_grid()
        ms = self._state.anim_speed_ms
        self._timer_id = self.after(ms, self._tick_animation)

    # ── Status / Log ─────────────────────────────────────────────────────────

    def _set_status(self, message: str, *, error: bool = False) -> None:
        color = "#ff6b6b" if error else "gray"
        self.lbl_status.configure(text=f"État : {message}", text_color=color)
        self._log(message, level="WARN" if error else "INFO")

    def _log(self, message: str, level: str = "INFO") -> None:
        if not hasattr(self, "txt_log"):
            return
        now = datetime.datetime.now().strftime("%H:%M:%S")
        entry = f"[{now}] [{level:4}] {message}\n"
        self.txt_log.configure(state="normal")
        self.txt_log.insert("end", entry)
        self.txt_log.see("end")
        self.txt_log.configure(state="disabled")

    # ── Canvas ────────────────────────────────────────────────────────────────

    def _draw_canvas_pattern(
        self, tiles: list[list[Image.Image]] | list[Image.Image], tile_size: int
    ) -> None:
        self._canvas_grid = [row[:] for row in _GRID_DEFAULT]
        self._redraw_canvas_grid()
        if self._state.resource_type == "A4":
            mode = self._a4_canvas_mode_var.get()
            if mode == "Sol":
                self.lbl_canvas_info.configure(
                    text="Cliquez pour dessiner — bitmask 8-voisins (Sol/Toit)"
                )
            else:
                self.lbl_canvas_info.configure(
                    text="Cliquez pour dessiner — bitmask 4-voisins (Mur)"
                )
        else:
            self.lbl_canvas_info.configure(
                text="Cliquez pour dessiner — bitmask 8-voisins"
            )

    def _on_canvas_click(self, event: tk.Event) -> None:  # type: ignore[type-arg]
        col = event.x // _CELL_SIZE
        row = event.y // _CELL_SIZE
        grid = self._canvas_grid
        if 0 <= row < len(grid) and 0 <= col < len(grid[0]):
            grid[row][col] = not grid[row][col]
            self._redraw_canvas_grid()

    def _load_test_pattern(self) -> None:
        self._canvas_grid = [row[:] for row in _GRID_DEFAULT]
        self._redraw_canvas_grid()

    def _clear_canvas_grid(self) -> None:
        rows = len(self._canvas_grid)
        cols = len(self._canvas_grid[0]) if rows else len(_GRID_DEFAULT[0])
        self._canvas_grid = [[False] * cols for _ in range(rows)]
        self._redraw_canvas_grid()

    def _redraw_canvas_grid(self) -> None:
        grid = self._canvas_grid
        rows = len(grid)
        cols = len(grid[0]) if rows else 0
        self.canvas.configure(width=cols * _CELL_SIZE, height=rows * _CELL_SIZE)
        self.canvas.delete("all")
        self._canvas_photos = []

        tiles = self._state.tiles
        active_tiles: list[Image.Image] | None = None
        if tiles and isinstance(tiles, list):
            if isinstance(tiles[0], list):
                tiles_list = cast(list[list[Image.Image]], tiles)
                fi = self._frame_sequence[self._current_frame_idx % len(self._frame_sequence)]
                fi = min(fi, len(tiles_list) - 1)
                active_tiles = tiles_list[fi]
            else:
                active_tiles = cast(list[Image.Image], tiles)

        is_wall = (
            self._state.resource_type == "A4"
            and getattr(self, "_a4_canvas_mode_var", None) is not None
            and self._a4_canvas_mode_var.get() == "Mur"
        )

        for r, row_data in enumerate(grid):
            for c, filled in enumerate(row_data):
                x, y = c * _CELL_SIZE, r * _CELL_SIZE
                if filled and active_tiles:
                    if is_wall:
                        bm = _compute_wall_bitmask_4n(grid, r, c)
                        idx = _WALL_4N_BITMASK_TO_IDX.get(bm, 0)
                        if bm not in _WALL_4N_BITMASK_TO_IDX:
                            _logger.warning(
                                "A4 bitmask %d not in _WALL_4N_BITMASK_TO_IDX — fallback to idx 0",
                                bm,
                            )
                    else:
                        bm = _compute_cell_bitmask(grid, r, c)
                        idx = _BITMASK_TO_IDX.get(bm, 0)
                    tile = active_tiles[idx]
                    scaled = tile.resize((_CELL_SIZE, _CELL_SIZE), Image.NEAREST)
                    photo = ImageTk.PhotoImage(scaled)
                    self._canvas_photos.append(photo)
                    self.canvas.create_image(x, y, anchor="nw", image=photo)
                elif filled:
                    self.canvas.create_rectangle(
                        x, y, x + _CELL_SIZE, y + _CELL_SIZE,
                        fill="#3a3a3a", outline="#555555",
                    )
                else:
                    self.canvas.create_rectangle(
                        x, y, x + _CELL_SIZE, y + _CELL_SIZE,
                        fill="#1a1a1a", outline="#2a2a2a",
                    )

    def mainloop(self, n: int = 0) -> None:  # type: ignore[override]
        super().mainloop(n)
