"""
Tests for 2D Diagonal Wall Tile Transformation Utility.
Implements UT-001 through UT-005 and IT-001 through IT-006.
"""

import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from PIL import Image

# Import the modules under test
from tools.src.assets.flat_wall_to_diagonal import (
    apply_vertical_shear,
    convert_image_file,
    parse_arguments,
    process_batch,
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


# ── IT-001: convert_image_file — valid both-direction flow ───────────────────


def test_it_001_convert_image_file_both(tmp_path):
    """IT-001: convert_image_file with direction='both' creates two output files."""
    src = Image.new("RGBA", (32, 32), (128, 0, 0, 255))
    input_file = tmp_path / "wall.png"
    src.save(str(input_file))
    out_dir = tmp_path / "out"

    convert_image_file(input_file, out_dir, "both")

    assert (out_dir / "wall_nw_se.png").exists()
    assert (out_dir / "wall_ne_sw.png").exists()


def test_it_001_convert_image_file_nw_se_only(tmp_path):
    """IT-001b: convert_image_file with direction='nw-se' creates only nw_se file."""
    src = Image.new("RGBA", (32, 32), (0, 128, 0, 255))
    input_file = tmp_path / "wall.png"
    src.save(str(input_file))
    out_dir = tmp_path / "out"

    convert_image_file(input_file, out_dir, "nw-se")

    assert (out_dir / "wall_nw_se.png").exists()
    assert not (out_dir / "wall_ne_sw.png").exists()


def test_it_001_convert_image_file_ne_sw_only(tmp_path):
    """IT-001c: convert_image_file with direction='ne-sw' creates only ne_sw file."""
    src = Image.new("RGBA", (32, 32), (0, 0, 128, 255))
    input_file = tmp_path / "wall.png"
    src.save(str(input_file))
    out_dir = tmp_path / "out"

    convert_image_file(input_file, out_dir, "ne-sw")

    assert not (out_dir / "wall_nw_se.png").exists()
    assert (out_dir / "wall_ne_sw.png").exists()


def test_it_001_non_multiple_of_32_prints_warning(tmp_path, capsys):
    """IT-001d: Image not multiple of 32px emits WARNING to stdout (covers line 72)."""
    src = Image.new("RGBA", (30, 30), (255, 255, 0, 255))
    input_file = tmp_path / "oddwall.png"
    src.save(str(input_file))
    out_dir = tmp_path / "out"

    convert_image_file(input_file, out_dir, "nw-se")
    captured = capsys.readouterr()
    assert "WARNING" in captured.out


def test_it_001_corrupted_image_raises(tmp_path):
    """IT-001e: Non-image file passed to convert_image_file raises (covers line 90)."""
    bad_file = tmp_path / "notanimage.png"
    bad_file.write_bytes(b"NOT A PNG FILE AT ALL")
    out_dir = tmp_path / "out"

    from PIL import UnidentifiedImageError
    with pytest.raises((UnidentifiedImageError, OSError)):
        convert_image_file(bad_file, out_dir, "nw-se")



# ── IT-002: process_batch ─────────────────────────────────────────────────────


def test_it_002_process_batch_happy_path(tmp_path):
    """IT-002: process_batch converts all PNGs in a directory."""
    input_dir = tmp_path / "input"
    input_dir.mkdir()
    output_dir = tmp_path / "output"

    # Create two valid PNG files
    for name in ("wall_a.png", "wall_b.png"):
        img = Image.new("RGBA", (32, 32), (100, 100, 100, 255))
        img.save(str(input_dir / name))

    result = process_batch(input_dir, output_dir, "nw-se")
    assert result == 0

    assert (output_dir / "wall_a_nw_se.png").exists()
    assert (output_dir / "wall_b_nw_se.png").exists()


def test_it_002_process_batch_no_pngs(tmp_path, capsys):
    """IT-002b: process_batch with empty directory returns 0 with WARNING."""
    input_dir = tmp_path / "empty"
    input_dir.mkdir()
    output_dir = tmp_path / "output"

    result = process_batch(input_dir, output_dir, "both")
    captured = capsys.readouterr()
    assert result == 0
    assert "WARNING" in captured.out or "No PNG" in captured.out


def test_it_002_process_batch_missing_input_dir(tmp_path, capsys):
    """IT-002c: process_batch with non-existent input dir returns 1."""
    missing = tmp_path / "nonexistent"
    output_dir = tmp_path / "output"

    result = process_batch(missing, output_dir, "both")
    captured = capsys.readouterr()
    assert result == 1
    assert "ERROR" in captured.out


def test_it_002_process_batch_ignores_hidden_files(tmp_path):
    """IT-002d: Hidden PNG files (starting with '.') are skipped."""
    input_dir = tmp_path / "input"
    input_dir.mkdir()
    output_dir = tmp_path / "output"

    # Hidden file — should be skipped
    hidden = input_dir / ".hidden.png"
    img = Image.new("RGBA", (32, 32), (50, 50, 50, 255))
    img.save(str(hidden))

    result = process_batch(input_dir, output_dir, "nw-se")
    # No non-hidden PNGs → WARNING, return 0
    assert result == 0
    # Output dir should be empty
    assert not output_dir.exists() or not list(output_dir.glob("*.png"))


# ── IT-003: main() entrypoint ─────────────────────────────────────────────────


def test_it_003_main_calls_process_batch(tmp_path):
    """IT-003: main() resolves args and calls process_batch (covers lines 176-185)."""
    input_dir = tmp_path / "main_in"
    input_dir.mkdir()
    output_dir = tmp_path / "main_out"

    img = Image.new("RGBA", (32, 32), (200, 200, 200, 255))
    img.save(str(input_dir / "test.png"))

    with patch(
        "sys.argv",
        [
            "flat_wall_to_diagonal.py",
            "--input-dir", str(input_dir),
            "--output-dir", str(output_dir),
            "--direction", "nw-se",
        ],
    ):
        from tools.src.assets.flat_wall_to_diagonal import main
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 0  # successful batch → exit 0


# ── Branch coverage: error paths ──────────────────────────────────────────────


def test_unknown_direction_raises_value_error():
    """Line 90: apply_vertical_shear raises ValueError for unknown direction."""
    from assets.flat_wall_to_diagonal import apply_vertical_shear

    img = Image.new("RGBA", (32, 32), (100, 100, 100, 255))
    with pytest.raises(ValueError, match="Unknown direction"):
        apply_vertical_shear(img, "invalid-direction")


def test_convert_oserror_on_open(tmp_path):
    """Lines 111-113: OSError during image open is caught, re-raised with stderr output."""
    from unittest.mock import MagicMock, patch

    from PIL import UnidentifiedImageError

    valid_file = tmp_path / "wall.png"
    valid_file.write_bytes(b"fake content")  # just needs to exist

    with patch("PIL.Image.open", side_effect=OSError("disk error")):
        with pytest.raises(OSError):
            convert_image_file(valid_file, tmp_path / "out", "nw-se")


def test_convert_oserror_on_save(tmp_path, capsys):
    """Lines 136-138: OSError during image save is caught, logged, and re-raised."""
    from unittest.mock import MagicMock, patch

    img = Image.new("RGBA", (32, 32), (100, 100, 100, 255))
    input_file = tmp_path / "wall.png"
    img.save(str(input_file))

    with patch("PIL.Image.Image.save", side_effect=OSError("no space")):
        with pytest.raises(OSError):
            convert_image_file(input_file, tmp_path / "out", "nw-se")

    captured = capsys.readouterr()
    assert "ERROR" in captured.out


def test_process_batch_error_handler(tmp_path, capsys):
    """Lines 163-164: process_batch catches exceptions from individual files and continues."""
    input_dir = tmp_path / "input"
    input_dir.mkdir()
    output_dir = tmp_path / "out"

    # One good PNG
    good_img = Image.new("RGBA", (32, 32), (100, 100, 100, 255))
    good_img.save(str(input_dir / "good.png"))

    # One corrupted file that will raise UnidentifiedImageError
    bad_file = input_dir / "bad.png"
    bad_file.write_bytes(b"THIS IS NOT A PNG")

    result = process_batch(input_dir, output_dir, "nw-se")
    captured = capsys.readouterr()

    # good.png succeeds, bad.png fails → error message emitted
    assert "❌" in captured.out or "Failed" in captured.out
    assert result == 0




