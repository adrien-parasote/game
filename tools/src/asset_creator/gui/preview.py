"""PIL Image to Dear PyGui raw texture conversion.

Handles RGBA PIL images → numpy float32 arrays → DPG raw textures.
Uses Image.NEAREST for pixel art scaling (no bilinear blur).

NOTE: This module does NOT import dearpygui. Functions here are pure
PIL/numpy utilities that can be tested without a GUI.
"""
from __future__ import annotations

import numpy as np
from PIL import Image


def pil_to_dpg_rgba(img: Image.Image) -> list[float]:
    """Convert PIL RGBA image to flat float32 list for DPG raw texture.

    Args:
        img: PIL Image in any mode (auto-converted to RGBA).

    Returns:
        Flat list of floats [r,g,b,a, r,g,b,a, ...] in [0.0, 1.0].
    """
    rgba = img.convert("RGBA")
    arr = np.array(rgba, dtype=np.float32) / 255.0
    return arr.ravel().tolist()


def scale_nearest(img: Image.Image, factor: int) -> Image.Image:
    """Scale PIL image by integer factor using nearest-neighbor.

    Args:
        img: Source image.
        factor: Integer scale factor (e.g., 4 for 32→128).

    Returns:
        New scaled image with crisp pixel art edges. Original is unchanged.
    """
    w, h = img.size
    return img.resize((w * factor, h * factor), Image.NEAREST)


def extract_tiles_from_strip(
    strip: Image.Image,
    tile_size: int = 32,
) -> list[Image.Image]:
    """Extract individual tiles from a horizontal tileset strip.

    Args:
        strip: Horizontal strip image (width = N × tile_size).
        tile_size: Size of each square tile.

    Returns:
        List of tile PIL Images (copies, not views).
    """
    count = strip.width // tile_size
    return [
        strip.crop((i * tile_size, 0, (i + 1) * tile_size, tile_size))
        for i in range(count)
    ]
