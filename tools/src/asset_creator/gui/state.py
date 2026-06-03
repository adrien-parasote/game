"""GUI application state management.

Immutable state pattern — each parameter change creates a new AppState.
Widget values are synced to/from the state via read/write functions.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from asset_creator.core.constants import (
    DEFAULT_COLOR_ACCENT,
    DEFAULT_COLOR_BASE,
    DEFAULT_COLOR_HIGHLIGHT,
    DEFAULT_COLOR_SHADOW,
    DEFAULT_OUTPUT_DIR,
    DEFAULT_TSX_DIR,
)
from asset_creator.core.palette import PaletteRole, load_palette
from asset_creator.core.terrain import (
    DetailConfig,
    EdgeConfig,
    TerrainConfig,
    TextureConfig,
)


@dataclass(frozen=True)
class AppState:
    """Complete UI state. Immutable — create new instance on change."""

    # Preset
    terrain_name: str = "grass"

    # Texture params
    texture_type: str = "noise"
    scale: float = 0.12
    octaves: int = 3
    persistence: float = 0.5
    lacunarity: float = 2.0
    use_smooth_ramp: bool = True
    detail_scale: float = 0.5
    detail_strength: float = 0.06
    use_dithering: bool = True
    dither_matrix_size: int = 4
    texture_warp_scale: float = 0.05
    texture_warp_strength: float = 0.0

    # Detail overlay
    detail_type: str = "grass_blades"
    detail_density: float = 0.12
    detail_max_height: int = 4
    detail_max_length: int = 4

    # Edge
    edge_style: str = "organic"
    edge_width: int = 3
    edge_noise_scale: float = 0.3

    # Generation
    seed: int = 0

    # Export
    output_dir: str = DEFAULT_OUTPUT_DIR
    tsx_dir: str = DEFAULT_TSX_DIR
    name: str = "grass"

    # Palette colors (RGBA tuples, overridable via color pickers)
    color_shadow: tuple[int, int, int] = DEFAULT_COLOR_SHADOW
    color_base: tuple[int, int, int] = DEFAULT_COLOR_BASE
    color_highlight: tuple[int, int, int] = DEFAULT_COLOR_HIGHLIGHT
    color_accent: tuple[int, int, int] = DEFAULT_COLOR_ACCENT

    def to_texture_config(self) -> TextureConfig:
        """Convert to TextureConfig for generation pipeline."""
        return TextureConfig(
            texture_type=self.texture_type,
            scale=self.scale,
            octaves=self.octaves,
            persistence=self.persistence,
            lacunarity=self.lacunarity,
            use_smooth_ramp=self.use_smooth_ramp,
            detail_scale=self.detail_scale,
            detail_strength=self.detail_strength,
            use_dithering=self.use_dithering,
            dither_matrix_size=self.dither_matrix_size,
            warp_scale=self.texture_warp_scale,
            warp_strength=self.texture_warp_strength,
        )

    def to_detail_config(self) -> DetailConfig:
        """Convert to DetailConfig for generation pipeline."""
        return DetailConfig(
            detail_type=self.detail_type,
            density=self.detail_density,
            max_height=self.detail_max_height,
            max_length=self.detail_max_length,
        )

    def to_edge_config(self) -> EdgeConfig:
        """Convert to EdgeConfig for generation pipeline."""
        return EdgeConfig(
            style=self.edge_style,
            width=self.edge_width,
            noise_scale=self.edge_noise_scale,
        )


def state_from_preset(
    terrain_name: str,
    presets: dict[str, Any],
) -> AppState:
    """Create AppState from a terrain preset name.

    Args:
        terrain_name: Name of the terrain preset (e.g. "grass").
        presets: Dict mapping terrain names to TerrainConfig objects.

    Returns:
        New AppState populated from the preset's config values.
    """
    config: TerrainConfig = presets[terrain_name]
    palette_path = (
        Path(__file__).parent.parent / "config" / "palettes" / f"{config.palette_name}.yaml"
    )
    pal = load_palette(palette_path)
    return AppState(
        terrain_name=terrain_name,
        texture_type=config.texture.texture_type,
        scale=config.texture.scale,
        octaves=config.texture.octaves,
        persistence=config.texture.persistence,
        lacunarity=config.texture.lacunarity,
        use_smooth_ramp=config.texture.use_smooth_ramp,
        detail_scale=config.texture.detail_scale,
        detail_strength=config.texture.detail_strength,
        use_dithering=config.texture.use_dithering,
        dither_matrix_size=config.texture.dither_matrix_size,
        texture_warp_scale=config.texture.warp_scale,
        texture_warp_strength=config.texture.warp_strength,
        detail_type=config.detail.detail_type,
        detail_density=config.detail.density,
        detail_max_height=config.detail.max_height,
        detail_max_length=config.detail.max_length,
        edge_style=config.edge.style,
        edge_width=config.edge.width,
        edge_noise_scale=config.edge.noise_scale,
        name=terrain_name,
        color_shadow=pal.get_color(PaletteRole.SHADOW),
        color_base=pal.get_color(PaletteRole.BASE),
        color_highlight=pal.get_color(PaletteRole.HIGHLIGHT),
        color_accent=pal.get_color(PaletteRole.ACCENT),
    )
