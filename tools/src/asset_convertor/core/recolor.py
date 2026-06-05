"""
asset_convertor.core.recolor

Pure-function recolor engine for pixel-art game assets.

Provides:
  - extract_palette: Extract unique non-transparent colors from a PIL Image
  - propose_remap: Propose nearest-color mapping (ΔE CIE76) from source to target palette
  - apply_remap: Apply a color remapping table to produce a new recolored image

No file I/O. No GUI imports. All functions are stateless and return new Images.

Spec: tools/docs/specs/asset_convertor_mv_recolor.md
"""

from __future__ import annotations

import math
from collections import Counter
from typing import cast

from PIL import Image

# ---------------------------------------------------------------------------
# Type definitions
# ---------------------------------------------------------------------------

type Color = tuple[int, int, int, int]          # (R, G, B, A), each 0-255
type Palette = list[Color]                      # ordered list of unique colors
type RemapTable = dict[Color, Color]            # source_color -> target_color


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def extract_palette(
    img: Image.Image,
    alpha_threshold: int = 10,
    max_colors: int = 256,
) -> Palette:
    """
    Extract unique non-transparent colors from a PIL Image.

    Args:
        img: Source image (any mode, converted to RGBA internally).
        alpha_threshold: Pixels with alpha < this value are skipped.
                         Default 10 — ignores nearly-invisible pixels.
        max_colors: Maximum number of unique colors to return.
                    If more, the most frequent colors are kept.

    Returns:
        Palette: List of (R, G, B, A) tuples, ordered by frequency (most common first).

    Raises:
        ValueError: If the image has 0 non-transparent pixels.
    """
    src = img.convert("RGBA")
    pixels = src.load()
    w, h = src.size

    counts: Counter[Color] = Counter()
    for y in range(h):
        for x in range(w):
            if pixels is None:
                continue
            px = cast("Color", pixels[x, y])
            if px[3] >= alpha_threshold:
                counts[px] += 1

    if not counts:
        raise ValueError(
            "Image vide : aucun pixel non-transparent trouvé."
        )

    # Return most frequent colors, capped at max_colors
    most_common = counts.most_common(max_colors)
    return [color for color, _ in most_common]


def propose_remap(
    source_palette: Palette,
    target_palette: Palette,
) -> RemapTable:
    """
    Propose a color remapping from source palette to target palette
    using perceptual nearest-color matching (ΔE CIE76).

    For each color in source_palette, finds the perceptually nearest
    color in target_palette.

    Args:
        source_palette: Colors extracted from the asset.
        target_palette: Colors from a Lospec preset.

    Returns:
        RemapTable: {source_color: nearest_target_color} for each source color.

    Notes:
        - Multiple source colors may map to the same target (many-to-one is valid).
        - ΔE uses CIE76 approximation via colorsys (stdlib).
    """
    remap: RemapTable = {}
    for src_color in source_palette:
        best = _nearest_color_delta_e(src_color, target_palette)
        remap[src_color] = best
    return remap


def apply_remap(
    img: Image.Image,
    remap_table: RemapTable,
    alpha_threshold: int = 10,
) -> Image.Image:
    """
    Apply a color remapping table to produce a recolored image.

    For each pixel in img:
    - If alpha < alpha_threshold: keep pixel unchanged.
    - If pixel color is in remap_table: replace with mapped color, preserving alpha.
    - If pixel color not in remap_table: keep unchanged.

    Args:
        img: Source image (any mode, converted to RGBA internally).
        remap_table: {(R,G,B,A) -> (R,G,B,A)} mapping.
        alpha_threshold: Pixels with alpha < this are preserved unchanged.

    Returns:
        Image.Image: New RGBA image with remapped colors. Input not mutated.
    """
    src = img.convert("RGBA")
    result = Image.new("RGBA", src.size)

    src_pixels = src.load()
    dst_pixels = result.load()

    w, h = src.size
    for y in range(h):
        for x in range(w):
            if src_pixels is None or dst_pixels is None:
                continue
            px = cast("Color", src_pixels[x, y])
            if px[3] < alpha_threshold:
                # Preserve transparent pixels unchanged
                dst_pixels[x, y] = px
            elif px in remap_table:
                # Apply remap but preserve original alpha
                target = remap_table[px]
                dst_pixels[x, y] = (target[0], target[1], target[2], px[3])
            else:
                dst_pixels[x, y] = px

    return result


# ---------------------------------------------------------------------------
# Internal: ΔE CIE76 color distance
# ---------------------------------------------------------------------------

def _rgb_to_lab(r: int, g: int, b: int) -> tuple[float, float, float]:
    """
    Approximate RGB (0-255) → CIE L*a*b* conversion.

    Uses sRGB → linear RGB → XYZ (D65) → Lab via the standard formula.
    This approximation is sufficient for perceptual palette matching.
    """
    # Normalize to 0.0-1.0
    r_n = r / 255.0
    g_n = g / 255.0
    b_n = b / 255.0

    # Linearize sRGB (gamma correction)
    def linearize(c: float) -> float:
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    r_lin = linearize(r_n)
    g_lin = linearize(g_n)
    b_lin = linearize(b_n)

    # sRGB → XYZ (D65 illuminant)
    x = r_lin * 0.4124564 + g_lin * 0.3575761 + b_lin * 0.1804375
    y = r_lin * 0.2126729 + g_lin * 0.7151522 + b_lin * 0.0721750
    z = r_lin * 0.0193339 + g_lin * 0.1191920 + b_lin * 0.9503041

    # Normalize by D65 white point
    x /= 0.95047
    z /= 1.08883
    # y is normalized to 1.0 by the formula above already

    # XYZ → Lab
    def f(t: float) -> float:
        return t ** (1.0 / 3.0) if t > 0.008856 else 7.787 * t + 16.0 / 116.0

    fx, fy, fz = f(x), f(y), f(z)
    L = 116.0 * fy - 16.0
    a = 500.0 * (fx - fy)
    b_lab = 200.0 * (fy - fz)

    return L, a, b_lab


def _delta_e_cie76(c1: Color, c2: Color) -> float:
    """
    Compute ΔE CIE76 between two RGBA colors (alpha ignored).

    ΔE = sqrt((L1-L2)² + (a1-a2)² + (b1-b2)²)
    """
    L1, a1, b1 = _rgb_to_lab(c1[0], c1[1], c1[2])
    L2, a2, b2 = _rgb_to_lab(c2[0], c2[1], c2[2])
    return math.sqrt((L1 - L2) ** 2 + (a1 - a2) ** 2 + (b1 - b2) ** 2)


def _nearest_color_delta_e(src_color: Color, target_palette: Palette) -> Color:
    """Return the target color perceptually nearest to src_color using ΔE CIE76."""
    return min(target_palette, key=lambda c: _delta_e_cie76(src_color, c))
