#!/usr/bin/env python3
"""
Convert flat 2D wall assets into 45-degree diagonal wall assets (NW-SE and NE-SW slopes).
Uses a vertical shear transformation (column-by-column translation) to preserve
crisp pixel-art boundaries without horizonal resizing or sub-pixel blur.

Usage:
    python3 scripts/assets/flat_wall_to_diagonal.py \
            [--input-dir PATH] [--output-dir PATH] [--direction {nw-se,ne-sw,both}]
"""

import argparse
import sys
from pathlib import Path

try:
    from PIL import Image, UnidentifiedImageError
except ImportError:
    sys.exit("ERROR: Pillow is required. Run: pip install pillow")


# ── CLI & Argument Parsing ───────────────────────────────────────────────────


def parse_arguments(args_list: list[str]) -> argparse.Namespace:
    """Parse command line arguments for the transformation utility."""
    # Resolve default paths relative to workspace root (script directory parent)
    script_dir = Path(__file__).resolve().parent
    workspace_root = script_dir.parents[1]

    default_input = workspace_root / "scripts" / "input"
    default_output = workspace_root / "assets" / "images" / "tilesets"

    parser = argparse.ArgumentParser(
        description="2D Diagonal Wall Tile Transformation Utility (45-Degree Vertical Shear)"
    )
    parser.add_argument(
        "--input-dir",
        type=str,
        default=str(default_input),
        help=f"Directory containing flat wall assets (default: {default_input})",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=str(default_output),
        help=f"Directory where transformed tilesets will be saved (default: {default_output})",
    )
    parser.add_argument(
        "--direction",
        choices=["nw-se", "ne-sw", "both"],
        default="both",
        help="Direction of the diagonal wall slope (default: both)",
    )

    return parser.parse_args(args_list)


# ── Core Transformation Engine ────────────────────────────────────────────────


def apply_vertical_shear(src_img: Image.Image, direction: str) -> Image.Image:
    """Apply vertical shear column-by-column to create a lossless 45-degree angle.

    W: Width, H: Height.
    Output dimensions: W x (H + W) because the vertical translation slope is 1.0 (1px/1px).
    """
    w, h = src_img.size

    # 32px grid alignment safety check: warn but proceed if width is not standard multiple
    if w % 32 != 0 or h % 32 != 0:
        sys.stdout.write(
            f"WARNING: Image size ({w}x{h}) is not a multiple of 32px. Grid alignment may fail.\n"
        )

    # Output canvas size is W x (H + W)
    dest_img = Image.new("RGBA", (w, h + w))

    for x in range(w):
        # Crop single column of 1px width
        col = src_img.crop((x, 0, x + 1, h))

        if direction == "nw-se":
            # Shift column x downwards by x pixels
            dest_img.paste(col, (x, x))
        elif direction == "ne-sw":
            # Shift column x downwards by (w - 1 - x) pixels
            dest_img.paste(col, (x, w - 1 - x))
        else:
            raise ValueError(f"Unknown direction parameter: {direction!r}")

    return dest_img


# ── Processing & File Operations ──────────────────────────────────────────────


def convert_image_file(input_file: Path, output_dir: Path, direction: str) -> None:
    """Load flat wall asset, apply vertical shear, and save outputs."""
    if not input_file.exists():
        sys.stdout.write(f"ERROR: File not found: {input_file}\n")
        raise FileNotFoundError(f"File not found: {input_file}")

    try:
        src = Image.open(input_file).convert("RGBA")
    except UnidentifiedImageError:
        sys.stdout.write(
            f"ERROR: Cannot identify image '{input_file.name}' (corrupted or invalid format).\n"
        )
        raise
    except OSError as e:
        sys.stdout.write(f"ERROR: Cannot read image '{input_file.name}': {e}\n")
        raise

    output_dir.mkdir(parents=True, exist_ok=True)
    stem = input_file.stem

    # Determine which slopes to generate
    slopes = []
    if direction in ("nw-se", "both"):
        slopes.append("nw-se")
    if direction in ("ne-sw", "both"):
        slopes.append("ne-sw")

    for slope in slopes:
        out_name = f"{stem}_{slope.replace('-', '_')}.png"
        out_path = output_dir / out_name

        sheared = apply_vertical_shear(src, slope)

        try:
            sheared.save(out_path, format="PNG")
            sys.stdout.write(
                f"✅ Generated {slope.upper()}: {out_name} ({sheared.width}x{sheared.height} px)\n"
            )
        except OSError as e:
            sys.stdout.write(f"ERROR: Cannot save output '{out_path}': {e}\n")
            raise


def process_batch(input_path: Path, output_path: Path, direction: str) -> int:
    """Scan input directory for PNG assets and perform batch transformation."""
    if not input_path.exists() or not input_path.is_dir():
        sys.stdout.write(f"ERROR: Input directory '{input_path}' not found.\n")
        return 1

    png_files = list(input_path.glob("*.png"))

    # Filter out hidden files
    png_files = [f for f in png_files if not f.name.startswith(".")]

    if not png_files:
        sys.stdout.write(f"WARNING: No PNG files found in '{input_path}'. Exiting.\n")
        return 0

    sys.stdout.write(f"Found {len(png_files)} flat assets to convert in '{input_path.name}'.\n\n")

    success_count = 0
    for f in png_files:
        try:
            convert_image_file(f, output_path, direction)
            success_count += 1
        except Exception as e:
            sys.stdout.write(f"❌ Failed to process '{f.name}': {e}\n")

    sys.stdout.write(
        f"\nBatch processing complete. Successfully converted {success_count}/{len(png_files)} files.\n"
    )
    return 0


# ── Main Entrypoint ───────────────────────────────────────────────────────────


def main() -> None:
    args = parse_arguments(sys.argv[1:])
    input_p = Path(args.input_dir).resolve()
    output_p = Path(args.output_dir).resolve()

    exit_code = process_batch(input_p, output_p, args.direction)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
