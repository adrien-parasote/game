"""
asset_convertor.gui.recolor_panel

RecolorPanel — CTkFrame widget for Recolor mode.

Three stacked sections:
  A) Palette de l'asset  — color swatches extracted from source image
  B) Palettes prédéfinies — 6 Lospec preset chips (2x3 grid)
  C) Remappage           — scrollable list of source → target color rows

This module only imports from core/ — no circular imports.
All state changes propagate upward via the `on_state_change` callback.

Spec: tools/docs/specs/asset_convertor_mv_gui.md § "Recolor Panel"
"""

from __future__ import annotations

import dataclasses
import threading
import tkinter as tk
from collections.abc import Callable
from tkinter import colorchooser
from tkinter.filedialog import askopenfilename

import customtkinter as ctk
from asset_convertor.core.palettes import get_palette, get_palette_names
from asset_convertor.core.recolor import (
    Color,
    RemapTable,
    apply_remap,
    extract_palette,
    propose_remap,
)
from asset_convertor.gui.state import AppState, RecolorState
from PIL import Image

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_SWATCH_SIZE = 28       # palette swatch button size
_REMAP_SWATCH = 20      # remap row swatch size
_MAX_SWATCHES = 32      # max palette colors shown


def _rgb_hex(color: Color) -> str:
    """Return #rrggbb string from an RGBA tuple."""
    return f"#{color[0]:02x}{color[1]:02x}{color[2]:02x}"


class RecolorPanel(ctk.CTkFrame):
    """
    Right panel for Recolor mode.

    Args:
        parent: Parent widget.
        state: Current AppState (with recolor sub-state already set).
        on_state_change: Callback called with the new AppState whenever
                         the recolor state changes (remap update, preset select…).
        on_preview_update: Callback called when the recolored preview image is ready.
    """

    def __init__(
        self,
        parent: ctk.CTkFrame,
        state: AppState,
        on_state_change: Callable[[AppState], None],
        on_preview_update: Callable[[Image.Image], None],
        on_error: Callable[[str], None] | None = None,
    ) -> None:
        super().__init__(parent)
        self._state = state
        self._on_state_change = on_state_change
        self._on_preview_update = on_preview_update
        self._on_error = on_error
        self._debounce_id: str | None = None
        self._selected_source_color: Color | None = None

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure((0, 1, 2), weight=0)

        self._build_palette_section()
        self._build_presets_section()
        self._build_remap_section()

        # Populate if we already have a source image
        if state.source_img is not None:
            self._extract_and_show_palette(state.source_img)

    # -----------------------------------------------------------------------
    # Section A — Palette de l'asset
    # -----------------------------------------------------------------------

    def _build_palette_section(self) -> None:
        frame = ctk.CTkFrame(self)
        frame.grid(row=0, column=0, sticky="ew", padx=6, pady=(6, 2))
        frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            frame, text="PALETTE DE L'ASSET",
            font=ctk.CTkFont(size=12, weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=8, pady=(6, 2))

        # Scrollable canvas for swatches
        self._swatch_canvas = tk.Canvas(
            frame, height=_SWATCH_SIZE + 4, bg="#1a1a1a",
            highlightthickness=0,
        )
        self._swatch_canvas.grid(row=1, column=0, sticky="ew", padx=6, pady=2)

        self._swatch_scroll = ctk.CTkScrollbar(
            frame, orientation="horizontal",
            command=self._swatch_canvas.xview,
        )
        self._swatch_scroll.grid(row=2, column=0, sticky="ew", padx=6)
        self._swatch_canvas.configure(xscrollcommand=self._swatch_scroll.set)

        self._swatch_inner = tk.Frame(self._swatch_canvas, bg="#1a1a1a")
        self._swatch_canvas.create_window((0, 0), window=self._swatch_inner, anchor="nw")
        self._swatch_inner.bind("<Configure>", lambda e: self._swatch_canvas.configure(
            scrollregion=self._swatch_canvas.bbox("all")
        ))

        self._lbl_palette_info = ctk.CTkLabel(frame, text="", text_color="gray", font=ctk.CTkFont(size=11))
        self._lbl_palette_info.grid(row=3, column=0, pady=(0, 4))

        # Import palette button — Feature F-PALETTE-IMG
        ctk.CTkButton(
            frame,
            text="\U0001f5bc\ufe0f Importer depuis image\u2026",
            height=26,
            font=ctk.CTkFont(size=11),
            command=self._import_palette_from_image,
        ).grid(row=4, column=0, sticky="ew", padx=6, pady=(0, 6))

    def _extract_and_show_palette(self, img: Image.Image) -> None:
        """Extract palette from img and rebuild swatch row."""
        try:
            palette = extract_palette(img, max_colors=_MAX_SWATCHES)
        except ValueError:
            palette = []

        rs = self._state.recolor or RecolorState()
        rs_updated = dataclasses.replace(rs, source_palette=palette)
        self._state = dataclasses.replace(self._state, recolor=rs_updated)
        self._on_state_change(self._state)

        self._rebuild_swatches(palette)

    def _rebuild_swatches(self, palette: list[Color]) -> None:
        """Rebuild the swatch canvas from the given palette.

        Fix AP-RE-SWATCH-01: uses tk.Canvas instead of tk.Button so that
        macOS Aqua rendering does not override the background color.
        """
        for w in self._swatch_inner.winfo_children():
            w.destroy()

        for i, color in enumerate(palette):
            hex_color = _rgb_hex(color)
            canvas = tk.Canvas(
                self._swatch_inner,
                width=_SWATCH_SIZE, height=_SWATCH_SIZE,
                bg=hex_color,
                highlightthickness=1, highlightbackground="#555",
                cursor="hand2",
            )
            canvas.grid(row=0, column=i, padx=1, pady=2)
            canvas.bind("<Button-1>", lambda e, c=color: self._on_source_swatch_click(c))

        count = len(palette)
        self._lbl_palette_info.configure(
            text=f"{count} couleur{'s' if count != 1 else ''} détectée{'s' if count != 1 else ''}"
        )

    def _on_source_swatch_click(self, color: Color) -> None:
        """Mark color as selected source for manual remap."""
        self._selected_source_color = color

    def _import_palette_from_image(self) -> None:
        """Import a palette from an external image and apply it as remap targets.

        Feature F-PALETTE-IMG — spec: asset_convertor_recolor_swatch_fix.md § Feature 2

        Flow:
          1. Guard: source_palette must be loaded first.
          2. filedialog.askopenfilename → cancel → early return (silent).
          3. Image.open → OSError → on_error callback (❌ message).
          4. extract_palette → ValueError (all-transparent) → on_error (❌ message).
          5. propose_remap(source_palette, imported_palette) → update RecolorState.
          6. Rebuild remap rows + schedule preview refresh.
        """
        rs = self._state.recolor
        if rs is None or not rs.source_palette:
            if self._on_error is not None:
                self._on_error(
                    "\u26a0\ufe0f Import palette : chargez d\u2019abord un asset source."
                )
            return

        path: str = askopenfilename(
            title="Importer une palette depuis une image",
            filetypes=[
                ("Images", "*.png *.jpg *.jpeg *.bmp *.gif *.webp"),
                ("Tous les fichiers", "*.*"),
            ],
        )
        if not path:
            return  # User cancelled — silent, no error

        try:
            img = Image.open(path).convert("RGBA")
        except OSError as exc:
            if self._on_error is not None:
                self._on_error(f"\u274c Import palette : fichier illisible \u2014 {exc}")
            return

        try:
            imported_palette = extract_palette(img, max_colors=_MAX_SWATCHES)
        except ValueError as exc:
            if self._on_error is not None:
                self._on_error(
                    f"\u274c Import palette : image vide ou enti\u00e8rement transparente \u2014 {exc}"
                )
            return

        remap = propose_remap(rs.source_palette, imported_palette)
        rs_updated = dataclasses.replace(
            rs,
            remap_table=remap,
            active_preset=None,  # imported palette clears any active preset
        )
        self._state = dataclasses.replace(self._state, recolor=rs_updated)
        self._on_state_change(self._state)

        self._rebuild_remap_rows(rs_updated.source_palette, remap)
        self._schedule_preview_refresh()

    # -----------------------------------------------------------------------
    # Section B — Palettes prédéfinies
    # -----------------------------------------------------------------------

    def _build_presets_section(self) -> None:
        frame = ctk.CTkFrame(self)
        frame.grid(row=1, column=0, sticky="ew", padx=6, pady=2)
        frame.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkLabel(
            frame, text="PALETTES PRÉDÉFINIES",
            font=ctk.CTkFont(size=12, weight="bold"),
        ).grid(row=0, column=0, columnspan=2, sticky="w", padx=8, pady=(6, 2))

        names = get_palette_names()
        for idx, name in enumerate(names[:6]):
            col = idx % 2
            row = 1 + idx // 2
            self._build_preset_chip(frame, name, row, col)

    def _build_preset_chip(
        self, parent: ctk.CTkFrame, name: str, row: int, col: int
    ) -> None:
        """Build one palette chip button with 5 micro-swatches."""
        chip_frame = ctk.CTkFrame(parent, corner_radius=4)
        chip_frame.grid(row=row, column=col, padx=4, pady=2, sticky="ew")
        chip_frame.grid_columnconfigure(0, weight=1)

        # Name label
        btn = ctk.CTkButton(
            chip_frame, text=name, height=28, font=ctk.CTkFont(size=11),
            anchor="w",
            command=lambda n=name: self._on_preset_click(n),
        )
        btn.grid(row=0, column=0, sticky="ew", padx=2, pady=2)

        # 5 micro-swatches drawn on a tiny canvas
        palette = get_palette(name)
        swatch_w = 5 * 12
        micro = tk.Canvas(chip_frame, width=swatch_w, height=10, bg="#1a1a1a",
                          highlightthickness=0)
        micro.grid(row=1, column=0, sticky="ew", padx=4, pady=(0, 4))
        for j, color in enumerate(palette[:5]):
            x0, x1 = j * 12, (j + 1) * 12
            micro.create_rectangle(x0, 0, x1, 10, fill=_rgb_hex(color), outline="")

    def _on_preset_click(self, name: str) -> None:
        """Apply Lospec preset: propose_remap → update RecolorState → trigger preview."""
        rs = self._state.recolor
        if rs is None or not rs.source_palette:
            return

        target = get_palette(name)
        remap = propose_remap(rs.source_palette, target)

        rs_updated = dataclasses.replace(
            rs, remap_table=remap, active_preset=name,
        )
        self._state = dataclasses.replace(self._state, recolor=rs_updated)
        self._on_state_change(self._state)

        # Rebuild remap section
        self._rebuild_remap_rows(rs_updated.source_palette, remap)

        # Trigger live preview (debounced)
        self._schedule_preview_refresh()

    # -----------------------------------------------------------------------
    # Section C — Remappage
    # -----------------------------------------------------------------------

    def _build_remap_section(self) -> None:
        frame = ctk.CTkFrame(self)
        frame.grid(row=2, column=0, sticky="nsew", padx=6, pady=(2, 6))
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            frame, text="REMAPPAGE",
            font=ctk.CTkFont(size=12, weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=8, pady=(6, 2))

        # Scrollable frame for remap rows
        self._remap_scroll_frame = ctk.CTkScrollableFrame(frame, height=200)
        self._remap_scroll_frame.grid(row=1, column=0, sticky="nsew", padx=4, pady=(0, 6))
        self._remap_scroll_frame.grid_columnconfigure(0, weight=1)

    def _rebuild_remap_rows(
        self, palette: list[Color], remap: RemapTable,
    ) -> None:
        """Rebuild all remap rows from the current palette and remap table."""
        for w in self._remap_scroll_frame.winfo_children():
            w.destroy()

        for i, src_color in enumerate(palette):
            dst_color = remap.get(src_color, src_color)
            self._build_remap_row(i, src_color, dst_color)

    def _build_remap_row(self, idx: int, src: Color, dst: Color) -> None:
        """Build one remap row: [src swatch] → [dst swatch] [hex entry]."""
        row_frame = ctk.CTkFrame(self._remap_scroll_frame, fg_color="transparent")
        row_frame.grid(row=idx, column=0, sticky="ew", padx=2, pady=1)

        # Source swatch (read-only)
        src_canvas = tk.Canvas(
            row_frame, width=_REMAP_SWATCH, height=_REMAP_SWATCH,
            bg=_rgb_hex(src), highlightthickness=1, highlightbackground="#555",
        )
        src_canvas.pack(side="left", padx=(4, 2))

        # Arrow
        ctk.CTkLabel(row_frame, text="→", width=20).pack(side="left")

        # Dest swatch (clickable → colorchooser)
        dst_canvas = tk.Canvas(
            row_frame, width=_REMAP_SWATCH, height=_REMAP_SWATCH,
            bg=_rgb_hex(dst), highlightthickness=1, highlightbackground="#888",
            cursor="hand2",
        )
        dst_canvas.pack(side="left", padx=(2, 4))
        dst_canvas.bind(
            "<Button-1>",
            lambda e, s=src, d=dst_canvas: self._open_color_picker(s, d),
        )

        # Hex entry
        hex_var = tk.StringVar(value=_rgb_hex(dst)[1:])  # without '#'
        entry = ctk.CTkEntry(row_frame, textvariable=hex_var, width=72,
                             font=ctk.CTkFont(family="Courier", size=11))
        entry.pack(side="left", padx=2)

        entry.bind("<Return>", lambda e, s=src, v=hex_var, d=dst_canvas, ew=entry:
                   self._on_hex_commit(s, v, d, ew))
        entry.bind("<FocusOut>", lambda e, s=src, v=hex_var, d=dst_canvas, ew=entry:
                   self._on_hex_commit(s, v, d, ew))

    def _open_color_picker(self, src: Color, dst_canvas: tk.Canvas) -> None:
        """Open system color chooser and update remap for src color."""
        initial = dst_canvas.cget("bg")
        result = colorchooser.askcolor(color=initial, title=f"Choisir la couleur cible pour {_rgb_hex(src)}")
        if result and result[0]:
            r, g, b = (int(x) for x in result[0])
            new_color: Color = (r, g, b, 255)
            self._update_remap_entry(src, new_color)
            dst_canvas.configure(bg=_rgb_hex(new_color))

    def _on_hex_commit(
        self, src: Color, hex_var: tk.StringVar,
        dst_canvas: tk.Canvas, entry: ctk.CTkEntry,
    ) -> None:
        """Validate hex entry and update remap. Flash red on error."""
        raw = hex_var.get().strip().lstrip("#")
        if len(raw) != 6:
            self._flash_entry_error(entry, hex_var)
            return
        try:
            r = int(raw[0:2], 16)
            g = int(raw[2:4], 16)
            b = int(raw[4:6], 16)
        except ValueError:
            self._flash_entry_error(entry, hex_var)
            return

        new_color: Color = (r, g, b, 255)
        self._update_remap_entry(src, new_color)
        dst_canvas.configure(bg=_rgb_hex(new_color))

    def _flash_entry_error(self, entry: ctk.CTkEntry, hex_var: tk.StringVar) -> None:
        """Flash the entry border red for 1 second, then restore."""
        rs = self._state.recolor
        if rs:
            old = rs.remap_table.get(
                self._selected_source_color or (0, 0, 0, 255),
                (0, 0, 0, 255),
            )
            hex_var.set(_rgb_hex(old)[1:])
        entry.configure(border_color="red")
        self.after(1000, lambda: entry.configure(border_color=""))

    def _update_remap_entry(self, src: Color, new_dst: Color) -> None:
        """Update one remap entry and propagate state."""
        rs = self._state.recolor
        if rs is None:
            return
        new_remap = dict(rs.remap_table)
        new_remap[src] = new_dst
        rs_updated = dataclasses.replace(rs, remap_table=new_remap)
        self._state = dataclasses.replace(self._state, recolor=rs_updated)
        self._on_state_change(self._state)
        self._schedule_preview_refresh()

    # -----------------------------------------------------------------------
    # Public update API
    # -----------------------------------------------------------------------

    def update_state(self, new_state: AppState) -> None:
        """Called from app.py when the outer state changes."""
        self._state = new_state
        if new_state.source_img is not None and new_state.recolor:
            palette = new_state.recolor.source_palette
            if palette:
                self._rebuild_swatches(palette)
                self._rebuild_remap_rows(palette, new_state.recolor.remap_table)

    # -----------------------------------------------------------------------
    # Live preview — debounced 300ms
    # -----------------------------------------------------------------------

    def _schedule_preview_refresh(self) -> None:
        """Debounce preview refresh: cancel existing timer and reset to 300ms."""
        if self._debounce_id is not None:
            self.after_cancel(self._debounce_id)
        self._debounce_id = self.after(300, self._refresh_preview)

    def _refresh_preview(self) -> None:
        """Run apply_remap in background thread, callback with result image."""
        self._debounce_id = None
        rs = self._state.recolor
        if rs is None or not rs.remap_table or self._state.source_img is None:
            return
        src_img = self._state.source_img
        remap = dict(rs.remap_table)

        def _worker() -> None:
            try:
                result = apply_remap(src_img, remap)
                rs_inner = self._state.recolor
                if rs_inner is not None:
                    rs_updated = dataclasses.replace(rs_inner, result_img=result)
                    self._state = dataclasses.replace(self._state, recolor=rs_updated)
                    self._on_state_change(self._state)
                self.after(0, lambda: self._on_preview_update(result))
            except Exception as exc:
                self.after(0, lambda m=str(exc): self._on_preview_update_error(m))

        threading.Thread(target=_worker, daemon=True).start()

    def _on_preview_update_error(self, message: str) -> None:
        """Log error — the on_preview_update callback is not called on error."""
        # Silently pass error to parent via a label update if desired
        # For now the parent app handles log display
        pass
