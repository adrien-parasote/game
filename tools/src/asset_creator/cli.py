"""CLI interface for the Asset Creator Tool.

Provides commands:
- generate: Generate a terrain tileset (PNG + TSX)
- list: List available terrain presets
- preview: Preview an existing tileset PNG
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from asset_creator.core.constants import (
    DEFAULT_OUTPUT_DIR,
    DEFAULT_TSX_DIR,
    TILE_SIZE,
)
from asset_creator.core.detail_overlay import apply_detail_overlay
from asset_creator.core.palette import load_palette
from asset_creator.core.subtile import generate_subtiles
from asset_creator.core.terrain import get_builtin_presets, load_terrain_presets
from asset_creator.core.texture import (
    TextureParams,
    generate_noise_texture_v2,
    generate_pattern_texture,
)
from asset_creator.core.tile_assembler import assemble_tileset
from asset_creator.exporters.png_exporter import export_png
from asset_creator.exporters.tsx_exporter import export_tsx
from PIL import Image

PALETTE_DIR = Path(__file__).parent / "config" / "palettes"
DEFAULT_PNG_DIR = Path(DEFAULT_OUTPUT_DIR)
DEFAULT_TSX_DIR = Path(DEFAULT_TSX_DIR)


def _build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="asset_creator",
        description="Generate Tiled-native tilesets from terrain definitions.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # ── generate ──────────────────────────────────────────────────────────
    gen = subparsers.add_parser(
        "generate",
        help="Generate a terrain tileset (PNG + TSX).",
    )
    gen.add_argument(
        "--terrain",
        required=True,
        help="Terrain preset name (e.g. grass) or path to custom YAML.",
    )
    gen.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_PNG_DIR,
        help=f"Output directory for PNG (default: {DEFAULT_PNG_DIR}).",
    )
    gen.add_argument(
        "--tsx-dir",
        type=Path,
        default=DEFAULT_TSX_DIR,
        help=f"Output directory for TSX (default: {DEFAULT_TSX_DIR}).",
    )
    gen.add_argument(
        "--seed",
        type=int,
        default=0,
        help="Random seed for reproducible generation (default: 0).",
    )
    gen.add_argument(
        "--variants",
        type=int,
        default=1,
        help="Number of variants to generate (default: 1).",
    )
    gen.add_argument(
        "--preview",
        action="store_true",
        help="Open Pygame preview before exporting.",
    )
    gen.add_argument(
        "--name",
        help="Output filename stem (default: terrain name, e.g. 'grass').",
    )

    # ── list ──────────────────────────────────────────────────────────────
    subparsers.add_parser("list", help="List available terrain presets.")

    # ── preview ───────────────────────────────────────────────────────────
    prev = subparsers.add_parser(
        "preview",
        help="Preview an existing tileset PNG in Pygame.",
    )
    prev.add_argument("png_path", type=Path, help="Path to the tileset PNG.")

    # ── gui ───────────────────────────────────────────────────────────────
    subparsers.add_parser("gui", help="Launch interactive GUI.")

    return parser


def _resolve_terrain_config(terrain_arg: str) -> tuple[str, dict]:
    """Resolve terrain name or path to a terrain config.

    Returns (terrain_name, presets_dict) where presets_dict
    contains the terrain config under the terrain_name key.
    """
    terrain_path = Path(terrain_arg)
    if terrain_path.exists() and terrain_path.suffix in (".yaml", ".yml"):
        presets = load_terrain_presets(terrain_path)
        if not presets:
            sys.exit(f"ERROR: No terrains found in {terrain_path}")
        name = next(iter(presets))
        return name, presets

    presets = get_builtin_presets()
    if terrain_arg not in presets:
        available = ", ".join(sorted(presets.keys()))
        sys.exit(f"ERROR: Unknown terrain '{terrain_arg}'. Available presets: {available}")
    return terrain_arg, presets


def _generate_terrain(
    terrain_name: str,
    presets: dict,
    seed: int,
    output_dir: Path,
    tsx_dir: Path,
    name_stem: str | None,
    show_preview: bool,
) -> tuple[Path, Path]:
    """Generate a single terrain tileset.

    Returns (png_path, tsx_path).
    """
    config = presets[terrain_name]
    palette_path = PALETTE_DIR / f"{config.palette_name}.yaml"
    palette = load_palette(palette_path)

    params = TextureParams(
        texture_type=config.texture.texture_type,
        scale=config.texture.scale,
        octaves=config.texture.octaves,
        persistence=config.texture.persistence,
        lacunarity=config.texture.lacunarity,
        density=config.texture.density,
        detail_scale=config.texture.detail_scale,
        detail_strength=config.texture.detail_strength,
        use_dithering=config.texture.use_dithering,
        dither_matrix_size=config.texture.dither_matrix_size,
    )

    if config.texture.texture_type == "noise":
        texture = generate_noise_texture_v2(TILE_SIZE, TILE_SIZE, palette, params, seed=seed)
    else:
        texture = generate_pattern_texture(
            TILE_SIZE,
            TILE_SIZE,
            palette,
            config.texture.texture_type,
            params,
            seed=seed,
        )

    # Apply detail overlay
    if config.detail.detail_type != "none":
        texture = apply_detail_overlay(
            texture,
            palette,
            detail_type=config.detail.detail_type,
            density=config.detail.density,
            seed=seed,
            max_height=config.detail.max_height,
            max_length=config.detail.max_length,
        )

    edge_config = {
        "style": config.edge.style,
        "width": config.edge.width,
        "noise_scale": config.edge.noise_scale,
    }
    subtiles = generate_subtiles(texture, edge_config, seed=seed)
    tileset_image = assemble_tileset(subtiles)

    if show_preview:
        try:
            from asset_creator.preview.pygame_preview import run_preview

            run_preview(tileset_image, subtiles)
        except ImportError:
            sys.stdout.write("WARNING: Pygame preview not available. Exporting directly.\n")

    stem = name_stem or terrain_name
    png_path = output_dir / f"{stem}.png"
    tsx_path = tsx_dir / f"{stem}.tsx"

    export_png(tileset_image, png_path)
    export_tsx(tsx_path, png_path, stem)

    return png_path, tsx_path


def cmd_generate(args: argparse.Namespace) -> None:
    """Handle the 'generate' command."""
    terrain_name, presets = _resolve_terrain_config(args.terrain)

    for variant_idx in range(args.variants):
        seed = args.seed + variant_idx
        name_stem = args.name
        if args.variants > 1:
            base = name_stem or terrain_name
            name_stem = f"{base}-v{variant_idx + 1}"

        png_path, tsx_path = _generate_terrain(
            terrain_name,
            presets,
            seed,
            args.output_dir,
            args.tsx_dir,
            name_stem,
            args.preview,
        )
        sys.stdout.write(f"✅ PNG: {png_path}\n✅ TSX: {tsx_path}\n")

    if args.variants > 1:
        sys.stdout.write(f"\nGenerated {args.variants} variant(s).\n")


def cmd_list(_args: argparse.Namespace) -> None:
    """Handle the 'list' command."""
    presets = get_builtin_presets()
    sys.stdout.write("Available terrain presets:\n")
    for name, config in sorted(presets.items()):
        sys.stdout.write(
            f"  {name:20s} palette={config.palette_name:15s} "
            f"texture={config.texture.texture_type}\n"
        )


def cmd_preview(args: argparse.Namespace) -> None:
    """Handle the 'preview' command."""
    png_path = args.png_path
    if not png_path.exists():
        sys.exit(f"ERROR: File not found: {png_path}")
    try:
        image = Image.open(png_path).convert("RGBA")
    except OSError as e:
        sys.exit(f"ERROR: Cannot open image: {e}")

    try:
        from asset_creator.preview.pygame_preview import run_preview

        run_preview(image, subtile_set=None)
    except ImportError:
        sys.exit("ERROR: Pygame preview not available.")


def cmd_gui(_args: argparse.Namespace) -> None:
    """Handle the 'gui' command — launch interactive Dear PyGui window."""
    try:
        from asset_creator.gui.app import run_gui

        run_gui()
    except ImportError:
        sys.exit("ERROR: Dear PyGui not available. Install with: pip install dearpygui")


def main() -> None:
    """Main CLI entry point."""
    parser = _build_parser()
    args = parser.parse_args()

    commands = {
        "generate": cmd_generate,
        "list": cmd_list,
        "preview": cmd_preview,
        "gui": cmd_gui,
    }

    handler = commands.get(args.command)
    if handler is None:
        parser.print_help()
        sys.exit(1)

    handler(args)
