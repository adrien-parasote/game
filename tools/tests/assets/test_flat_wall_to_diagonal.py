"""
Tests for 2D Diagonal Wall Tile Transformation Utility.
Implements UT-001 through UT-005 and IT-001 through IT-003.
"""

import os
from pathlib import Path

import pytest
from PIL import Image

# Import the modules under test
from tools.src.assets.flat_wall_to_diagonal import (
    apply_vertical_shear,
    convert_image_file,
    parse_arguments,
)

# ── UT-001: Path Resolution & CLI Arguments ───────────────────────────────────


def test_ut_001_parse_arguments_defaults():
    """Verify default CLI arguments are resolved correctly."""
    args = parse_arguments([])
    assert args.direction == "both"
    assert Path(args.input_dir).name == "input"
    assert Path(args.output_dir).name == "tilesets"


def test_ut_001_parse_arguments_custom():
    """Verify custom CLI arguments override defaults."""
    args = parse_arguments(
        ["--input-dir", "custom/in", "--output-dir", "custom/out", "--direction", "nw-se"]
    )
    assert args.direction == "nw-se"
    assert args.input_dir == "custom/in"
    assert args.output_dir == "custom/out"


# ── UT-002: Missing Input Files ───────────────────────────────────────────────


def test_ut_002_missing_input_raises_error():
    """Verify that attempting to convert a non-existent file fails gracefully."""
    non_existent = Path("tools/src/input/does_not_exist_xyz.png")
    out_dir = Path("assets/images/tilesets")

    with pytest.raises((FileNotFoundError, SystemExit)):
        convert_image_file(non_existent, out_dir, "both")


# ── UT-003: Sheared Dimensions Scaling ────────────────────────────────────────


def test_ut_003_sheared_dimensions():
    """Verify sheared canvas dimensions are exactly W x (H + W)."""
    # Create a test image of 32x96 (like asset1.png)
    test_img = Image.new("RGBA", (32, 96), (255, 0, 0, 255))

    sheared_nw_se = apply_vertical_shear(test_img, "nw-se")
    assert sheared_nw_se.width == 32
    assert sheared_nw_se.height == 96 + 32  # 128 px

    sheared_ne_sw = apply_vertical_shear(test_img, "ne-sw")
    assert sheared_ne_sw.width == 32
    assert sheared_ne_sw.height == 128  # 128 px


# ── UT-004: NW-SE Column Translation Coordinates ─────────────────────────────


def test_ut_004_nw_se_column_translation():
    """Verify that NW-SE column x of the source is shifted downwards by x pixels."""
    # Create a 32x32 image with a single blue pixel at (0, 0) and green pixel at (31, 0)
    src = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
    src.putpixel((0, 0), (0, 0, 255, 255))  # Blue
    src.putpixel((31, 0), (0, 255, 0, 255))  # Green

    sheared = apply_vertical_shear(src, "nw-se")

    # In NW-SE, column x shifts down by x pixels:
    # Column 0: shift 0 -> Blue pixel should be at (0, 0)
    assert sheared.getpixel((0, 0)) == (0, 0, 255, 255)
    # Column 31: shift 31 -> Green pixel should be at (31, 31)
    assert sheared.getpixel((31, 31)) == (0, 255, 0, 255)

    # Bounding pixels above/below should be transparent
    assert sheared.getpixel((0, 1)) == (0, 0, 0, 0)
    assert sheared.getpixel((31, 30)) == (0, 0, 0, 0)


# ── UT-005: NE-SW Column Translation Coordinates ─────────────────────────────


def test_ut_005_ne_sw_column_translation():
    """Verify that NE-SW column x of the source is shifted downwards by W - 1 - x pixels."""
    # Create a 32x32 image with a single blue pixel at (0, 0) and green pixel at (31, 0)
    src = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
    src.putpixel((0, 0), (0, 0, 255, 255))  # Blue
    src.putpixel((31, 0), (0, 255, 0, 255))  # Green

    sheared = apply_vertical_shear(src, "ne-sw")

    # In NE-SW, column x shifts down by W - 1 - x pixels (here W = 32):
    # Column 0: shift 31 -> Blue pixel should be at (0, 31)
    assert sheared.getpixel((0, 31)) == (0, 0, 255, 255)
    # Column 31: shift 0 -> Green pixel should be at (31, 0)
    assert sheared.getpixel((31, 0)) == (0, 255, 0, 255)

    # Bounding pixels
    assert sheared.getpixel((0, 30)) == (0, 0, 0, 0)
    assert sheared.getpixel((31, 1)) == (0, 0, 0, 0)
