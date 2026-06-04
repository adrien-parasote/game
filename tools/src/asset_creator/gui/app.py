"""
Convertisseur Autotile - RPG Maker -> Tiled

Interface customtkinter 3 panneaux :
  - SOURCE : previsualisation de l'autotile d'entree
  - SORTIE TILED : grille 8x6 des 47 tuiles converties  # noqa: RUF002
  - APERCU CANVAS : motif de test 5x5  # noqa: RUF002

Spec : tools/docs/specs/autotile_converter_spec.md section gui/app.py
"""

from __future__ import annotations

import datetime
import os
import threading
import tkinter as tk
from dataclasses import dataclass, field
from pathlib import Path
from tkinter import filedialog
from typing import Literal

import customtkinter as ctk
from asset_creator.core.converter_mv import convert_mv
from asset_creator.core.converter_xp import BLOB_BITMASKS, convert_xp
from asset_creator.exporters.tsx_generator import export
from PIL import Image, ImageTk

# ── Configuration UI ─────────────────────────────────────────────────────────

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

OUTPUT_DIR_DEFAULT = str(Path(__file__).parents[3] / "src" / "output")

_CELL_SIZE = 32  # taille d'affichage de chaque cellule dans le canvas interactif

# Grille de test par defaut 5x5 - correspondance avec l'ancien _TEST_PATTERN
_GRID_DEFAULT: list[list[bool]] = [
    [False, True,  True,  True,  False],
    [True,  True,  True,  True,  True ],
    [True,  True,  True,  True,  True ],
    [True,  True,  True,  True,  True ],
    [False, True,  True,  True,  False],
]

_BITMASK_TO_IDX: dict[int, int] = {bm: idx for idx, bm in enumerate(BLOB_BITMASKS)}


def _compute_cell_bitmask(grid: list[list[bool]], row: int, col: int) -> int:
    """Compute 8-neighbor blob bitmask for a cell in the interactive grid.

    Diagonal bits follow blob rules: set only when both adjacent cardinals are set.
    Convention: NW=1, N=2, NE=4, W=8, E=16, SW=32, S=64, SE=128.
    """
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


# ── Dataclass état interne ────────────────────────────────────────────────────


@dataclass
class AppState:
    source_path: str | None = None
    source_img: Image.Image | None = None
    mode: Literal["XP", "MV", "MZ"] = "MV"
    tiles: list[Image.Image] | None = None
    tile_size: int = 32
    output_dir: str = field(default_factory=lambda: OUTPUT_DIR_DEFAULT)


# ── Application principale ────────────────────────────────────────────────────


class App(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Convertisseur Autotile — RPG Maker → Tiled")
        self.geometry("1100x720")
        self.resizable(True, True)

        self._state = AppState()
        self._photo_source: ctk.CTkImage | None = None
        self._photo_output: ctk.CTkImage | None = None
        self._canvas_photos: list[ImageTk.PhotoImage] = []
        self._canvas_grid: list[list[bool]] = [row[:] for row in _GRID_DEFAULT]

        self._setup_icon()
        self._build_ui()
        self._reset_panels()

    def _setup_icon(self) -> None:
        """Icone macOS via AppKit (silencieux si non disponible)."""
        try:
            import AppKit  # type: ignore[import-untyped]  # pyobjc, macOS only
            ns_app = AppKit.NSApplication.sharedApplication()
            icon_path = os.path.join(os.path.dirname(__file__), "assets", "icon.png")
            if os.path.exists(icon_path):
                ns_icon = AppKit.NSImage.alloc().initWithContentsOfFile_(icon_path)
                ns_app.setApplicationIconImage_(ns_icon)
        except (ImportError, AttributeError):
            pass  # non-macOS ou pyobjc non installe

    # ── Construction UI ───────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._build_toolbar()
        self._build_panels()
        self._build_log()    # row 2 — terminal journal
        self._build_footer() # row 3

    def _build_toolbar(self) -> None:
        bar = ctk.CTkFrame(self, height=56, corner_radius=0)
        bar.grid(row=0, column=0, sticky="ew", padx=0, pady=0)
        bar.grid_columnconfigure(3, weight=1)

        # Bouton ouvrir
        self.btn_open = ctk.CTkButton(
            bar,
            text="📂 Ouvrir un autotile",
            width=180,
            command=self._open_file,
        )
        self.btn_open.grid(row=0, column=0, padx=(12, 8), pady=10)

        # Sélecteur de format
        ctk.CTkLabel(bar, text="Format :").grid(row=0, column=1, padx=(4, 4))
        self._mode_var = ctk.StringVar(value="MV")
        for i, mode in enumerate(("XP", "MV", "MZ")):
            rb = ctk.CTkRadioButton(
                bar,
                text=mode,
                variable=self._mode_var,
                value=mode,
                command=self._on_mode_change,
            )
            rb.grid(row=0, column=2 + i, padx=4)

        # Bouton convertir
        self.btn_convert = ctk.CTkButton(
            bar,
            text="⚙ Convertir",
            width=130,
            state="disabled",
            command=self._convert,
        )
        self.btn_convert.grid(row=0, column=5, padx=(16, 8), pady=10)

    def _build_panels(self) -> None:
        container = ctk.CTkFrame(self, fg_color="transparent")
        container.grid(row=1, column=0, sticky="nsew", padx=8, pady=4)
        container.grid_columnconfigure((0, 1, 2), weight=1)
        container.grid_rowconfigure(0, weight=1)

        self._build_source_panel(container)
        self._build_output_panel(container)
        self._build_canvas_panel(container)

    def _build_source_panel(self, parent: ctk.CTkFrame) -> None:
        frame = ctk.CTkFrame(parent)
        frame.grid(row=0, column=0, sticky="nsew", padx=4)
        frame.grid_rowconfigure(1, weight=1)
        frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(frame, text="SOURCE", font=ctk.CTkFont(size=13, weight="bold")).grid(
            row=0, column=0, pady=(8, 4)
        )

        self.lbl_source = ctk.CTkLabel(
            frame,
            text="Aucun autotile chargé",
            width=220,
            height=220,
            fg_color=("#d0d0d0", "#2a2a2a"),
            corner_radius=6,
        )
        self.lbl_source.grid(row=1, column=0, padx=8, pady=4, sticky="nsew")

        self.lbl_source_info = ctk.CTkLabel(frame, text="", text_color="gray")
        self.lbl_source_info.grid(row=2, column=0, pady=(2, 8))

    def _build_output_panel(self, parent: ctk.CTkFrame) -> None:
        frame = ctk.CTkFrame(parent)
        frame.grid(row=0, column=1, sticky="nsew", padx=4)
        frame.grid_rowconfigure(1, weight=1)
        frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(frame, text="SORTIE TILED", font=ctk.CTkFont(size=13, weight="bold")).grid(
            row=0, column=0, pady=(8, 4)
        )

        self.lbl_output = ctk.CTkLabel(
            frame,
            text="Aucune conversion",
            width=300,
            height=220,
            fg_color=("#d0d0d0", "#2a2a2a"),
            corner_radius=6,
        )
        self.lbl_output.grid(row=1, column=0, padx=8, pady=4, sticky="nsew")

        self.lbl_output_info = ctk.CTkLabel(frame, text="", text_color="gray")
        self.lbl_output_info.grid(row=2, column=0, pady=(2, 8))

    def _build_canvas_panel(self, parent: ctk.CTkFrame) -> None:
        frame = ctk.CTkFrame(parent)
        frame.grid(row=0, column=2, sticky="nsew", padx=4)
        frame.grid_rowconfigure(1, weight=1)
        frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(frame, text="APERÇU CANVAS", font=ctk.CTkFont(size=13, weight="bold")).grid(
            row=0, column=0, pady=(8, 4)
        )

        canvas_frame = ctk.CTkFrame(
            frame, fg_color=("#d0d0d0", "#2a2a2a"), corner_radius=6
        )
        canvas_frame.grid(row=1, column=0, padx=8, pady=4, sticky="nsew")
        canvas_frame.grid_rowconfigure(0, weight=1)
        canvas_frame.grid_columnconfigure(0, weight=1)

        self.canvas = tk.Canvas(
            canvas_frame,
            width=160,
            height=160,
            bg="#222222",
            highlightthickness=0,
        )
        self.canvas.grid(row=0, column=0, padx=4, pady=4)
        self.canvas.bind("<Button-1>", self._on_canvas_click)

        # Boutons canvas
        btn_frame = ctk.CTkFrame(frame, fg_color="transparent")
        btn_frame.grid(row=2, column=0, pady=(0, 2))
        ctk.CTkButton(
            btn_frame, text="↺ Pattern", width=90,
            command=self._load_test_pattern,
        ).pack(side="left", padx=2)
        ctk.CTkButton(
            btn_frame, text="✕ Effacer", width=90,
            command=self._clear_canvas_grid,
        ).pack(side="left", padx=2)

        self.lbl_canvas_info = ctk.CTkLabel(frame, text="", text_color="gray")
        self.lbl_canvas_info.grid(row=3, column=0, pady=(2, 8))

    def _build_footer(self) -> None:
        footer = ctk.CTkFrame(self, height=56, corner_radius=0)
        footer.grid(row=3, column=0, sticky="ew", padx=0, pady=0)
        footer.grid_columnconfigure(2, weight=1)

        self.btn_export = ctk.CTkButton(
            footer,
            text="💾 Exporter PNG + TSX",
            width=180,
            state="disabled",
            command=self._export,
        )
        self.btn_export.grid(row=0, column=0, padx=(12, 8), pady=10)

        ctk.CTkLabel(footer, text="Dossier :").grid(row=0, column=1, padx=(4, 2))

        self._output_dir_var = ctk.StringVar(value=self._state.output_dir)
        self.entry_output_dir = ctk.CTkEntry(
            footer, textvariable=self._output_dir_var, width=280
        )
        self.entry_output_dir.grid(row=0, column=2, padx=(0, 4), pady=10, sticky="ew")

        btn_dir = ctk.CTkButton(
            footer,
            text="📂",
            width=36,
            command=self._pick_output_dir,
        )
        btn_dir.grid(row=0, column=3, padx=(0, 12))

        self.lbl_status = ctk.CTkLabel(
            footer, text="État : Prêt.", text_color="gray", anchor="w"
        )
        self.lbl_status.grid(row=0, column=4, padx=(8, 12), sticky="ew")

    # ── Handlers ─────────────────────────────────────────────────────────────

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

        # Valider les dimensions selon le mode
        mode = self._mode_var.get()
        error = self._validate_dimensions(img, mode)
        if error:
            self._set_status(error, error=True)
            self.btn_convert.configure(state="disabled")
            return

        self._state = AppState(
            source_path=path,
            source_img=img,
            mode=mode,  # type: ignore[arg-type]  # validated above
            output_dir=self._output_dir_var.get(),
        )

        self._display_source(img, Path(path).name, mode)
        self.btn_convert.configure(state="normal")
        self._set_status(f"Fichier chargé : {Path(path).name}")

    def _validate_dimensions(self, img: Image.Image, mode: str) -> str | None:
        """Retourne un message d'erreur ou None si valide."""
        w, h = img.width, img.height
        if mode == "XP":
            if w != 96 or h != 128:
                return f"Format XP invalide. Attendu : 96x128 px, obtenu : {w}x{h}"
        elif mode in ("MV", "MZ") and (w, h) not in ((64, 96), (96, 144)):
            return (
                f"Format {mode} invalide. Attendu : 64x96 ou 96x144 px, obtenu : {w}x{h}"
            )
        return None

    def _on_mode_change(self) -> None:
        new_mode = self._mode_var.get()
        if self._state.source_img is not None:
            error = self._validate_dimensions(self._state.source_img, new_mode)
            if error:
                self._set_status(error, error=True)
                self.btn_convert.configure(state="disabled")
                return
        self._state = AppState(
            source_path=self._state.source_path,
            source_img=self._state.source_img,
            mode=new_mode,  # type: ignore[arg-type]  # validated above
            output_dir=self._output_dir_var.get(),
        )
        self._reset_panels()
        self.btn_export.configure(state="disabled")
        if self._state.source_img:
            self.btn_convert.configure(state="normal")

    def _convert(self) -> None:
        if self._state.source_img is None:
            return

        self._set_status("Conversion en cours…")
        self.btn_convert.configure(state="disabled")

        def _run() -> None:
            try:
                mode = self._state.mode
                img = self._state.source_img
                assert img is not None  # guarded by early-return above
                if mode == "XP":
                    tiles = convert_xp(img)
                    tile_size = 32
                else:  # MV or MZ
                    tiles = convert_mv(img)
                    tile_size = tiles[0].width if tiles else 32

                self._state = AppState(
                    source_path=self._state.source_path,
                    source_img=self._state.source_img,
                    mode=mode,
                    tiles=tiles,
                    tile_size=tile_size,
                    output_dir=self._output_dir_var.get(),
                )
                self.after(0, self._on_convert_success)
            except Exception as err:
                msg = str(err)
                self.after(
                    0,
                    lambda m=msg: self._on_convert_error(m),
                )

        threading.Thread(target=_run, daemon=True).start()

    def _on_convert_success(self) -> None:
        tiles = self._state.tiles
        if not tiles:
            return

        self._display_output_sheet(tiles, self._state.tile_size)
        self._draw_canvas_pattern(tiles, self._state.tile_size)
        self.btn_convert.configure(state="normal")
        self.btn_export.configure(state="normal")
        sheet_w = 8 * self._state.tile_size
        sheet_h = 6 * self._state.tile_size
        self._set_status(
            f"Conversion reussie : 47 tuiles . {sheet_w}x{sheet_h} px"
        )

    def _on_convert_error(self, message: str) -> None:
        self.btn_convert.configure(state="normal")
        self._set_status(f"Erreur de conversion : {message}", error=True)

    def _export(self) -> None:
        if not self._state.tiles or not self._state.source_path:
            return

        out_dir = self._output_dir_var.get().strip() or OUTPUT_DIR_DEFAULT
        name = Path(self._state.source_path).stem

        try:
            png_path, tsx_path = export(
                self._state.tiles, name, out_dir, self._state.tile_size
            )
            self._set_status(
                f"Exporté : {Path(png_path).name} + {Path(tsx_path).name} → {out_dir}"
            )
        except (OSError, PermissionError) as exc:
            self._set_status(
                f"Impossible d'écrire dans {out_dir}. Choisissez un autre dossier. ({exc})",
                error=True,
            )
        except ValueError as exc:
            self._set_status(f"Erreur interne : {exc}", error=True)

    def _pick_output_dir(self) -> None:
        d = filedialog.askdirectory(title="Dossier de sortie")
        if d:
            self._output_dir_var.set(d)
            self._state = AppState(
                source_path=self._state.source_path,
                source_img=self._state.source_img,
                mode=self._state.mode,
                tiles=self._state.tiles,
                tile_size=self._state.tile_size,
                output_dir=d,
            )

    # ── Display helpers ───────────────────────────────────────────────────────

    def _display_source(
        self, img: Image.Image, filename: str, mode: str
    ) -> None:
        scaled = self._scale_to_fit(img, 200, 200)
        self._photo_source = ctk.CTkImage(
            light_image=scaled, dark_image=scaled, size=(scaled.width, scaled.height)
        )
        self.lbl_source.configure(image=self._photo_source, text="")
        w, h = img.size
        self.lbl_source_info.configure(
            text=f"{filename}  |  Format: {mode}/{w}x{h}"
        )

    def _display_output_sheet(
        self, tiles: list[Image.Image], tile_size: int
    ) -> None:
        from asset_creator.exporters.tsx_generator import assemble_sheet

        sheet = assemble_sheet(tiles, tile_size)
        scaled = self._scale_to_fit(sheet, 320, 220)
        self._photo_output = ctk.CTkImage(
            light_image=scaled, dark_image=scaled, size=(scaled.width, scaled.height)
        )
        self.lbl_output.configure(image=self._photo_output, text="")
        self.lbl_output_info.configure(
            text=f"Tuile : {tile_size}px  |  Sortie : {8*tile_size}x{6*tile_size}"
        )

    def _draw_canvas_pattern(
        self, tiles: list[Image.Image], tile_size: int
    ) -> None:
        """Initialise la grille interactive avec le motif de test et redessine."""
        self._canvas_grid = [row[:] for row in _GRID_DEFAULT]
        self._redraw_canvas_grid()
        self.lbl_canvas_info.configure(
            text="Cliquez pour dessiner - 5x5 - bitmask 8-voisins"
        )

    def _reset_panels(self) -> None:
        self.lbl_source.configure(image=None, text="Aucun autotile chargé")
        self.lbl_source_info.configure(text="")
        self.lbl_output.configure(image=None, text="Aucune conversion")
        self.lbl_output_info.configure(text="")
        self.canvas.delete("all")
        self._canvas_photos = []
        self._canvas_grid = [[False] * len(_GRID_DEFAULT[0]) for _ in _GRID_DEFAULT]
        self.lbl_canvas_info.configure(text="")

    @staticmethod
    def _scale_to_fit(img: Image.Image, max_w: int, max_h: int) -> Image.Image:
        """Scale image to fit within max_w x max_h using NEAREST, preserve aspect ratio.

        Upscales small images (e.g. 64x96 source in a 220x220 panel) and
        downscales large images. Both directions preserve aspect ratio.
        """
        scale = min(max_w / img.width, max_h / img.height)  # no 1.0 cap — allow upscale
        if abs(scale - 1.0) < 1e-6:
            return img
        new_w = max(1, int(img.width * scale))
        new_h = max(1, int(img.height * scale))
        return img.resize((new_w, new_h), Image.NEAREST)

    def _set_status(self, message: str, *, error: bool = False) -> None:
        color = "#ff6b6b" if error else "gray"
        self.lbl_status.configure(text=f"État : {message}", text_color=color)
        self._log(message, level="WARN" if error else "INFO")

    def _log(self, message: str, level: str = "INFO") -> None:
        """Ajoute une entrée horodatée dans le terminal journal."""
        if not hasattr(self, "txt_log"):
            return
        now = datetime.datetime.now().strftime("%H:%M:%S")
        entry = f"[{now}] [{level:4}] {message}\n"
        self.txt_log.configure(state="normal")
        self.txt_log.insert("end", entry)
        self.txt_log.see("end")
        self.txt_log.configure(state="disabled")

    def _build_log(self) -> None:
        """Terminal journal entre les panneaux et le footer (row 2)."""
        log_frame = ctk.CTkFrame(self, corner_radius=0)
        log_frame.grid(row=2, column=0, sticky="ew", padx=0, pady=0)
        log_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            log_frame, text="Journal :", font=ctk.CTkFont(size=11)
        ).grid(row=0, column=0, padx=(12, 6), pady=4, sticky="w")

        self.txt_log = ctk.CTkTextbox(
            log_frame,
            height=64,
            font=ctk.CTkFont(family="Courier", size=11),
            fg_color=("#111111", "#0a0a0a"),
            text_color="#8fbcbb",
            activate_scrollbars=True,
        )
        self.txt_log.grid(row=0, column=1, padx=(0, 8), pady=4, sticky="ew")
        self.txt_log.configure(state="disabled")

    def _on_canvas_click(self, event: tk.Event) -> None:  # type: ignore[type-arg]
        """Toggle la cellule cliquée et redessine le canvas."""
        col = event.x // _CELL_SIZE
        row = event.y // _CELL_SIZE
        grid = self._canvas_grid
        if 0 <= row < len(grid) and 0 <= col < len(grid[0]):
            grid[row][col] = not grid[row][col]
            self._redraw_canvas_grid()

    def _load_test_pattern(self) -> None:
        """Reinitialise la grille avec le motif de test 5x5."""
        self._canvas_grid = [row[:] for row in _GRID_DEFAULT]
        self._redraw_canvas_grid()

    def _clear_canvas_grid(self) -> None:
        """Efface toutes les cellules du canvas."""
        rows = len(self._canvas_grid)
        cols = len(self._canvas_grid[0]) if rows else len(_GRID_DEFAULT[0])
        self._canvas_grid = [[False] * cols for _ in range(rows)]
        self._redraw_canvas_grid()

    def _redraw_canvas_grid(self) -> None:
        """Redessine le canvas interactif depuis self._canvas_grid."""
        grid = self._canvas_grid
        rows = len(grid)
        cols = len(grid[0]) if rows else 0
        total_w = cols * _CELL_SIZE
        total_h = rows * _CELL_SIZE

        self.canvas.configure(width=total_w, height=total_h)
        self.canvas.delete("all")
        self._canvas_photos = []

        tiles = self._state.tiles
        for r, row_data in enumerate(grid):
            for c, filled in enumerate(row_data):
                x, y = c * _CELL_SIZE, r * _CELL_SIZE
                if filled and tiles:
                    bm = _compute_cell_bitmask(grid, r, c)
                    idx = _BITMASK_TO_IDX.get(bm, 0)
                    tile = tiles[idx]
                    scaled = tile.resize((_CELL_SIZE, _CELL_SIZE), Image.NEAREST)
                    photo = ImageTk.PhotoImage(scaled)
                    self._canvas_photos.append(photo)
                    self.canvas.create_image(x, y, anchor="nw", image=photo)
                elif filled:
                    # Conversion pas encore faite : placeholder coloré
                    self.canvas.create_rectangle(
                        x, y, x + _CELL_SIZE, y + _CELL_SIZE,
                        fill="#3a3a3a", outline="#555555",
                    )
                else:
                    # Cellule vide
                    self.canvas.create_rectangle(
                        x, y, x + _CELL_SIZE, y + _CELL_SIZE,
                        fill="#1a1a1a", outline="#2a2a2a",
                    )

    def mainloop(self, n: int = 0) -> None:  # type: ignore[override]
        super().mainloop(n)
