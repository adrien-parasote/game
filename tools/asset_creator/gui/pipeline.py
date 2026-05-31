"""Tileset generation and export pipeline — no DPG dependency.

Contains the regenerate_tileset, generate_standalone_tile, and export
functions extracted so that integration tests can exercise the full
pipeline without a display.
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image

from tools.asset_creator.core.constants import TILE_SIZE
from tools.asset_creator.core.detail_overlay import apply_detail_overlay
from tools.asset_creator.core.palette import load_palette
from tools.asset_creator.core.subtile import generate_subtiles
from tools.asset_creator.core.terrain import TerrainConfig
from tools.asset_creator.core.texture import (
    TextureParams,
    generate_noise_texture_v2,
    generate_pattern_texture,
)
from tools.asset_creator.core.tile_assembler import assemble_tileset
from tools.asset_creator.exporters.png_exporter import export_png
from tools.asset_creator.exporters.tsx_exporter import export_tsx
from tools.asset_creator.gui.preview import extract_tiles_from_strip
from tools.asset_creator.gui.state import AppState

PALETTE_DIR = Path(__file__).parent.parent / "config" / "palettes"


def _build_texture(
    state: AppState,
    presets: dict[str, TerrainConfig],
) -> Image.Image:
    """Generate the base 32x32 texture from state and presets.

    Shared by both standalone and autotile pipelines.

    Returns:
        32x32 RGBA PIL Image.
    """
    config = presets[state.terrain_name]
    palette_path = PALETTE_DIR / f"{config.palette_name}.yaml"
    base_palette = load_palette(palette_path)

    # Override palette colors with user-customised values from state
    from tools.asset_creator.core.palette import Palette, RampConfig
    custom_colors = (
        state.color_shadow,
        state.color_base,
        state.color_highlight,
        state.color_accent,
    )

    # Re-create the ramp configuration using the user's custom base color
    ramp_config = None
    if base_palette.ramp_config is not None:
        ramp_config = RampConfig(
            base_color=state.color_base,
            steps=base_palette.ramp_config.steps,
            shadow_hue_shift=base_palette.ramp_config.shadow_hue_shift,
            highlight_hue_shift=base_palette.ramp_config.highlight_hue_shift,
            lightness_range=base_palette.ramp_config.lightness_range,
        )

    # Use the 4 user colors directly for interpolation and construct a valid ramp_config
    # This ensures all 4 color pickers affect the rendered output
    palette = Palette(
        name=base_palette.name,
        colors=custom_colors,
        roles=base_palette.roles,
        ramp_config=ramp_config,
    )

    params = TextureParams(
        texture_type=config.texture.texture_type,
        scale=state.scale,
        octaves=state.octaves,
        persistence=state.persistence,
        lacunarity=state.lacunarity,
        density=config.texture.density,
        detail_scale=state.detail_scale,
        detail_strength=state.detail_strength,
        use_dithering=state.use_dithering,
        dither_matrix_size=state.dither_matrix_size,
    )

    if config.texture.texture_type == "noise":
        texture = generate_noise_texture_v2(32, 32, palette, params, seed=state.seed)
    else:
        texture = generate_pattern_texture(
            32, 32, palette, config.texture.texture_type, params, seed=state.seed,
        )

    if config.detail.detail_type != "none":
        texture = apply_detail_overlay(
            texture,
            palette,
            detail_type=config.detail.detail_type,
            density=state.detail_density,
            seed=state.seed,
            max_height=state.detail_max_height,
            max_length=state.detail_max_length,
        )

    return texture


def generate_standalone_tile(
    state: AppState,
    presets: dict[str, TerrainConfig],
) -> Image.Image:
    """Generate a single 32x32 standalone tile (texture + detail only).

    No edge processing, no subtile assembly. The result is a single tile
    that can be directly pasted into an existing tileset.

    Args:
        state: Current application state with generation parameters.
        presets: Dict mapping terrain names to TerrainConfig objects.

    Returns:
        Single 32x32 RGBA PIL Image.
    """
    return _build_texture(state, presets)


def regenerate_tileset(
    state: AppState,
    presets: dict[str, TerrainConfig],
) -> list[Image.Image]:
    """Run the full autotile pipeline and return individual tiles.

    Generates texture -> applies detail -> processes edges -> assembles
    47-tile Wang blob tileset.

    Args:
        state: Current application state with all generation parameters.
        presets: Dict mapping terrain names to TerrainConfig objects.

    Returns:
        List of 47 PIL Images, each 32x32, one per blob tile.
    """
    texture = _build_texture(state, presets)

    edge_config = {
        "style": state.edge_style,
        "width": state.edge_width,
        "noise_scale": state.edge_noise_scale,
    }
    subtiles = generate_subtiles(texture, edge_config, seed=state.seed)
    tileset_strip = assemble_tileset(subtiles)
    return extract_tiles_from_strip(tileset_strip, tile_size=TILE_SIZE)


def tiles_to_strip(tiles: list[Image.Image], tile_size: int = TILE_SIZE) -> Image.Image:
    """Reassemble individual tiles into a horizontal strip.

    Args:
        tiles: List of square tile images.
        tile_size: Size of each tile in pixels.

    Returns:
        Horizontal strip image (width = len(tiles) x tile_size).
    """
    strip = Image.new("RGBA", (len(tiles) * tile_size, tile_size))
    for i, tile in enumerate(tiles):
        strip.paste(tile, (i * tile_size, 0))
    return strip


def do_export_autotile(
    state: AppState,
    tiles: list[Image.Image],
    png_dir: Path | None = None,
    tsx_dir: Path | None = None,
) -> tuple[Path, Path]:
    """Export autotile as PNG strip + TSX file.

    Args:
        state: Application state (provides name, output_dir, tsx_dir).
        tiles: List of 47 tile images to export.
        png_dir: Override for PNG output directory.
        tsx_dir: Override for TSX output directory.

    Returns:
        Tuple of (png_path, tsx_path).
    """
    out_png = Path(png_dir) if png_dir else Path(state.output_dir)
    out_tsx = Path(tsx_dir) if tsx_dir else Path(state.tsx_dir)

    strip = tiles_to_strip(tiles, TILE_SIZE)
    png_path = out_png / f"{state.name}.png"
    tsx_path = out_tsx / f"{state.name}.tsx"

    export_png(strip, png_path)
    export_tsx(tsx_path, png_path, state.name)
    return png_path, tsx_path


def do_export_standalone(
    state: AppState,
    tile: Image.Image,
    png_dir: Path | None = None,
) -> Path:
    """Export standalone tile as a single 32x32 PNG.

    Args:
        state: Application state (provides name, output_dir).
        tile: Single 32x32 tile image.
        png_dir: Override for PNG output directory.

    Returns:
        Path to the exported PNG.
    """
    out_png = Path(png_dir) if png_dir else Path(state.output_dir)
    png_path = out_png / f"{state.name}_tile.png"
    export_png(tile, png_path)
    return png_path


# Backward compat alias used by integration tests
do_export = do_export_autotile
