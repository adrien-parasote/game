"""
asset_convertor.gui.state

Application state dataclasses for the Asset Convertor GUI v2.

Defines AppState and RecolorState as frozen dataclasses.
All state updates use dataclasses.replace() — never mutate.

Spec: tools/docs/specs/asset_convertor_mv_gui.md § "AppState"
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from asset_convertor.core.recolor import Color, RemapTable
from PIL import Image

# ---------------------------------------------------------------------------
# Type aliases
# ---------------------------------------------------------------------------

ResourceType = Literal["A1", "A2", "A3", "A4", "Recolor"]
FormatType = Literal["MV", "XP", "MZ"]


def _default_output_dir() -> str:
    """Return default output directory path."""
    return str(Path(__file__).parents[3] / "src" / "output")


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class RecolorState:
    """State for the Recolor mode. Populated when resource_type == 'Recolor'."""

    source_palette: list[Color] = field(default_factory=list)
    """Colors extracted from source_img by extract_palette()."""

    remap_table: RemapTable = field(default_factory=dict)
    """Current color remapping: source_color -> target_color. User-editable."""

    active_preset: str | None = None
    """Name of the currently selected Lospec preset, or None if none selected."""

    result_img: Image.Image | None = None
    """Recolored preview image produced by apply_remap(). None until computed."""


@dataclass(frozen=True)
class AppState:
    """
    Immutable application state for the Asset Convertor GUI.

    All updates MUST use dataclasses.replace(state, field=new_value).
    Never mutate this object directly.
    """

    # --- Source ---
    source_path: str | None = None
    """Absolute path to the loaded source file."""

    source_img: Image.Image | None = None
    """Raw loaded PIL Image. Never modified — all processing produces result_img."""

    # --- Mode ---
    resource_type: ResourceType = "A2"
    """Primary axis: what kind of resource is being converted."""

    format: FormatType = "MV"
    """Secondary axis: source/target RPG Maker format. Irrelevant for Recolor."""

    # --- A1 context (animation) ---
    animated: bool = False
    """True if A1 animated autotile mode is active."""

    anim_type: str = "Horizontale (Eau/Sol)"
    """Animation type string for A1 animated conversion."""

    anim_speed_ms: int = 150
    """Animation frame duration in milliseconds."""

    # --- Output ---
    output_dir: str = field(default_factory=_default_output_dir)
    """Directory where exported files will be saved."""

    export_png: bool = True
    """Whether to export the PNG file. Always True (cannot be unchecked)."""

    export_tsx: bool = True
    """Whether to export the TSX tileset file. Auto-set to False for Recolor."""

    # --- Conversion result ---
    result_img: Image.Image | None = None
    """Image produced by the converter. Displayed in the SORTIE panel."""

    tiles: list[Image.Image] | None = None
    """Flat list of tiles for canvas/export. Used by TSX exporter."""

    # --- Recolor (populated only when resource_type == "Recolor") ---
    recolor: RecolorState | None = None
    """Recolor sub-state. None when not in Recolor mode."""

    # --- Display ---
    tile_size: int = 48
    """Display size of each tile in the interactive canvas."""
