"""
Convertisseur Autotile - RPG Maker -> Tiled

Interface customtkinter 3 panneaux :
  - SOURCE : previsualisation de l'autotile d'entree
  - SORTIE TILED : grille 8x6 des 47 tuiles converties  # noqa: RUF002
  - APERCU CANVAS : motif de test 5x5  # noqa: RUF002

Spec : tools/docs/specs/autotile_converter_spec.md section gui/app.py
"""

from __future__ import annotations

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

# Motif test 5x5 (bitmasks 8-voisins)
# Convention : NW=1, N=2, NE=4, W=8, E=16, SW=32, S=64, SE=128
_TEST_PATTERN: list[list[int]] = [
    [0,    2,    2,    2,    0],
    [8,    90,   90,   90,   16],
    [8,    90,   255,  90,   16],
    [8,    90,   90,   90,   16],
    [0,    64,   64,   64,   0],
]

_BITMASK_TO_IDX: dict[int, int] = {bm: idx for idx, bm in enumerate(BLOB_BITMASKS)}


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
        self._photo_source: ImageTk.PhotoImage | None = None
        self._photo_output: ImageTk.PhotoImage | None = None
        self._canvas_photos: list[ImageTk.PhotoImage] = []

        self._build_ui()
        self._reset_panels()

    # ── Construction UI ───────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._build_toolbar()
        self._build_panels()
        self._build_footer()

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
            width=200,
            height=200,
            bg="#222222",
            highlightthickness=0,
        )
        self.canvas.grid(row=0, column=0, padx=4, pady=4)

        self.lbl_canvas_info = ctk.CTkLabel(frame, text="", text_color="gray")
        self.lbl_canvas_info.grid(row=2, column=0, pady=(2, 8))

    def _build_footer(self) -> None:
        footer = ctk.CTkFrame(self, height=56, corner_radius=0)
        footer.grid(row=2, column=0, sticky="ew", padx=0, pady=0)
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
        self._photo_source = ImageTk.PhotoImage(scaled)
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
        self._photo_output = ImageTk.PhotoImage(scaled)
        self.lbl_output.configure(image=self._photo_output, text="")
        self.lbl_output_info.configure(
            text=f"Tuile : {tile_size}px  |  Sortie : {8*tile_size}x{6*tile_size}"
        )

    def _draw_canvas_pattern(
        self, tiles: list[Image.Image], tile_size: int
    ) -> None:
        display_size = 32  # toujours 32px dans le canvas
        total = 5 * display_size
        self.canvas.configure(width=total, height=total)
        self.canvas.delete("all")
        self._canvas_photos = []

        for row_idx, row in enumerate(_TEST_PATTERN):
            for col_idx, bm in enumerate(row):
                idx = _BITMASK_TO_IDX.get(bm, 0)
                tile = tiles[idx]
                scaled = tile.resize((display_size, display_size), Image.NEAREST)
                photo = ImageTk.PhotoImage(scaled)
                self._canvas_photos.append(photo)
                self.canvas.create_image(
                    col_idx * display_size,
                    row_idx * display_size,
                    anchor="nw",
                    image=photo,
                )

        self.lbl_canvas_info.configure(text="Motif test 5x5 (bitmask 8-voisins)")

    def _reset_panels(self) -> None:
        self.lbl_source.configure(image=None, text="Aucun autotile chargé")
        self.lbl_source_info.configure(text="")
        self.lbl_output.configure(image=None, text="Aucune conversion")
        self.lbl_output_info.configure(text="")
        self.canvas.delete("all")
        self._canvas_photos = []
        self.lbl_canvas_info.configure(text="")

    @staticmethod
    def _scale_to_fit(img: Image.Image, max_w: int, max_h: int) -> Image.Image:
        """Scale image to fit within max_w x max_h using NEAREST, preserve aspect ratio."""
        scale = min(max_w / img.width, max_h / img.height, 1.0)
        if scale < 1.0:
            new_w = max(1, int(img.width * scale))
            new_h = max(1, int(img.height * scale))
            return img.resize((new_w, new_h), Image.NEAREST)
        return img

    def _set_status(self, message: str, *, error: bool = False) -> None:
        color = "#ff6b6b" if error else "gray"
        self.lbl_status.configure(text=f"État : {message}", text_color=color)

    def mainloop(self, n: int = 0) -> None:  # type: ignore[override]
        super().mainloop(n)
