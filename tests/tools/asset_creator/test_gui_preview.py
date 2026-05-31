"""Tests for GUI preview engine (TC-015 → TC-019).

Verifies PIL image conversion, nearest-neighbor scaling,
and tile strip extraction — all without Dear PyGui dependency.
"""
from __future__ import annotations

import pytest
from PIL import Image

from tools.asset_creator.gui.preview import (
    extract_tiles_from_strip,
    pil_to_dpg_rgba,
    scale_nearest,
)


class TestPilToDpgRgba:
    """TC-015 & TC-016: pil_to_dpg_rgba output length and value range."""

    def test_output_length_32x32(self) -> None:
        """TC-015: 32×32 RGBA image → len(result) == 32 * 32 * 4."""
        img = Image.new("RGBA", (32, 32), (128, 64, 32, 255))
        result = pil_to_dpg_rgba(img)
        assert len(result) == 32 * 32 * 4

    def test_output_length_16x16(self) -> None:
        """Output length correct for different image sizes."""
        img = Image.new("RGBA", (16, 16), (0, 0, 0, 255))
        result = pil_to_dpg_rgba(img)
        assert len(result) == 16 * 16 * 4

    def test_all_values_in_range(self) -> None:
        """TC-016: All values between 0.0 and 1.0."""
        img = Image.new("RGBA", (32, 32), (255, 255, 255, 255))
        result = pil_to_dpg_rgba(img)
        assert all(0.0 <= v <= 1.0 for v in result)

    def test_zero_values(self) -> None:
        """Black transparent image → all zeros."""
        img = Image.new("RGBA", (4, 4), (0, 0, 0, 0))
        result = pil_to_dpg_rgba(img)
        assert all(v == pytest.approx(0.0) for v in result)

    def test_max_values(self) -> None:
        """White opaque image → all ones."""
        img = Image.new("RGBA", (4, 4), (255, 255, 255, 255))
        result = pil_to_dpg_rgba(img)
        assert all(v == pytest.approx(1.0) for v in result)

    def test_rgb_image_converted_to_rgba(self) -> None:
        """RGB image is auto-converted to RGBA."""
        img = Image.new("RGB", (4, 4), (128, 64, 32))
        result = pil_to_dpg_rgba(img)
        # Should have alpha channel added (len = w*h*4)
        assert len(result) == 4 * 4 * 4

    def test_specific_color_value(self) -> None:
        """Known color value maps correctly."""
        img = Image.new("RGBA", (1, 1), (128, 0, 255, 128))
        result = pil_to_dpg_rgba(img)
        assert result[0] == pytest.approx(128 / 255.0, abs=1e-3)  # R
        assert result[1] == pytest.approx(0.0)  # G
        assert result[2] == pytest.approx(1.0)  # B
        assert result[3] == pytest.approx(128 / 255.0, abs=1e-3)  # A


class TestScaleNearest:
    """TC-017: scale_nearest preserves pixel art sharpness."""

    def test_scaled_dimensions(self) -> None:
        """4×4 image scaled by 8 → 32×32."""
        img = Image.new("RGBA", (4, 4), (0, 0, 0, 255))
        result = scale_nearest(img, factor=8)
        assert result.size == (32, 32)

    def test_checkerboard_pixel_blocks(self) -> None:
        """Each original pixel becomes an 8×8 block of same color."""
        img = Image.new("RGBA", (4, 4), (0, 0, 0, 255))
        # Create checkerboard: alternate black and white
        pixels = img.load()
        for y in range(4):
            for x in range(4):
                if (x + y) % 2 == 0:
                    pixels[x, y] = (255, 255, 255, 255)  # white
                else:
                    pixels[x, y] = (0, 0, 0, 255)  # black

        result = scale_nearest(img, factor=8)
        result_pixels = result.load()

        # Check that each 8×8 block is uniform
        for orig_y in range(4):
            for orig_x in range(4):
                expected_color = pixels[orig_x, orig_y]
                for dy in range(8):
                    for dx in range(8):
                        rx = orig_x * 8 + dx
                        ry = orig_y * 8 + dy
                        assert result_pixels[rx, ry] == expected_color, (
                            f"Pixel ({rx},{ry}) expected {expected_color}, "
                            f"got {result_pixels[rx, ry]}"
                        )

    def test_factor_1_returns_same_size(self) -> None:
        """Scale factor 1 → same dimensions."""
        img = Image.new("RGBA", (10, 10), (128, 128, 128, 255))
        result = scale_nearest(img, factor=1)
        assert result.size == (10, 10)

    def test_does_not_mutate_original(self) -> None:
        """Original image is not modified."""
        img = Image.new("RGBA", (4, 4), (100, 100, 100, 255))
        original_size = img.size
        _ = scale_nearest(img, factor=4)
        assert img.size == original_size


class TestExtractTilesFromStrip:
    """TC-018 & TC-019: extract_tiles_from_strip count and dimensions."""

    def test_47_tiles_from_strip(self) -> None:
        """TC-018: 47-tile-wide strip → returns exactly 47 tiles."""
        strip_width = 47 * 32
        strip = Image.new("RGBA", (strip_width, 32), (0, 0, 0, 255))
        tiles = extract_tiles_from_strip(strip)
        assert len(tiles) == 47

    def test_each_tile_is_32x32(self) -> None:
        """TC-019: Each extracted tile is 32×32."""
        strip_width = 47 * 32
        strip = Image.new("RGBA", (strip_width, 32), (0, 0, 0, 255))
        tiles = extract_tiles_from_strip(strip)
        for i, tile in enumerate(tiles):
            assert tile.size == (32, 32), f"Tile {i} has size {tile.size}"

    def test_single_tile_strip(self) -> None:
        """A 32-wide strip → exactly 1 tile."""
        strip = Image.new("RGBA", (32, 32), (128, 128, 128, 255))
        tiles = extract_tiles_from_strip(strip)
        assert len(tiles) == 1
        assert tiles[0].size == (32, 32)

    def test_custom_tile_size(self) -> None:
        """Custom tile_size=16 works correctly."""
        strip = Image.new("RGBA", (64, 16), (0, 0, 0, 255))
        tiles = extract_tiles_from_strip(strip, tile_size=16)
        assert len(tiles) == 4
        for tile in tiles:
            assert tile.size == (16, 16)

    def test_tile_content_preserved(self) -> None:
        """Each tile has the correct content from the strip."""
        # Create strip with 3 tiles of different colors
        strip = Image.new("RGBA", (96, 32), (0, 0, 0, 0))
        for i, color in enumerate(
            [(255, 0, 0, 255), (0, 255, 0, 255), (0, 0, 255, 255)]
        ):
            for x in range(32):
                for y in range(32):
                    strip.putpixel((i * 32 + x, y), color)

        tiles = extract_tiles_from_strip(strip)
        assert len(tiles) == 3
        # First tile should be red
        assert tiles[0].getpixel((0, 0)) == (255, 0, 0, 255)
        # Second tile should be green
        assert tiles[1].getpixel((0, 0)) == (0, 255, 0, 255)
        # Third tile should be blue
        assert tiles[2].getpixel((0, 0)) == (0, 0, 255, 255)
