"""Sub-tile generation for blob terrain tiles.

Generates 20 distinct 16×16 sub-tiles grouped by quadrant (TL, TR, BL, BR)
and type (FILL, EDGE_V, EDGE_H, OUTER_CORNER, INNER_CORNER).

Edge masks are computed using distance fields with optional noise modulation.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

import numpy as np
from PIL import Image

from tools.asset_creator.core.constants import (
    BORDER_HIGHLIGHT_FACTOR,
    BORDER_SHADOW_FACTOR,
    DEFAULT_EDGE_NOISE_SCALE,
    DEFAULT_EDGE_WIDTH,
    DEFAULT_NOISE_SCALE,
    MASK_THRESHOLD,
    SUBTILE_SIZE,
    TILE_SIZE,
)

if TYPE_CHECKING:
    from numpy.typing import NDArray


class Quadrant(Enum):
    """Quadrant position within a 32×32 tile."""

    TL = "tl"
    TR = "tr"
    BL = "bl"
    BR = "br"


class SubTileType(Enum):
    """Type of sub-tile within a quadrant."""

    FILL = "fill"
    EDGE_V = "edge_v"
    EDGE_H = "edge_h"
    OUTER_CORNER = "outer_corner"
    INNER_CORNER = "inner_corner"


@dataclass(frozen=True)
class SubTileSet:
    """Immutable collection of 20 sub-tiles (4 quadrants × 5 types)."""

    tiles: dict[tuple[Quadrant, SubTileType], Image.Image]

    def get(self, quadrant: Quadrant, tile_type: SubTileType) -> Image.Image:
        """Retrieve a sub-tile by quadrant and type."""
        return self.tiles[(quadrant, tile_type)]


# ---------------------------------------------------------------------------
# Quadrant crop regions (from 32×32 base texture)
# ---------------------------------------------------------------------------

_QUADRANT_CROPS: dict[Quadrant, tuple[int, int, int, int]] = {
    Quadrant.TL: (0, 0, SUBTILE_SIZE, SUBTILE_SIZE),
    Quadrant.TR: (SUBTILE_SIZE, 0, TILE_SIZE, SUBTILE_SIZE),
    Quadrant.BL: (0, SUBTILE_SIZE, SUBTILE_SIZE, TILE_SIZE),
    Quadrant.BR: (SUBTILE_SIZE, SUBTILE_SIZE, TILE_SIZE, TILE_SIZE),
}


def _crop_quadrant(texture: Image.Image, quadrant: Quadrant) -> Image.Image:
    """Crop a subtile region from the texture for the given quadrant."""
    return texture.crop(_QUADRANT_CROPS[quadrant])


# ---------------------------------------------------------------------------
# Distance field computation
# ---------------------------------------------------------------------------

def _distance_v(width: int, height: int, quadrant: Quadrant, edge_width: int) -> NDArray[np.float64]:
    """Vertical distance field for EDGE_V mask.

    TL/BL: distance from left edge (x=0).
    TR/BR: distance from right edge (x=width-1).
    """
    xs = np.arange(width, dtype=np.float64)
    if quadrant in (Quadrant.TL, Quadrant.BL):
        row = xs / edge_width
    else:
        row = (width - 1 - xs) / edge_width
    return np.tile(row, (height, 1))


def _distance_h(width: int, height: int, quadrant: Quadrant, edge_width: int) -> NDArray[np.float64]:
    """Horizontal distance field for EDGE_H mask.

    TL/TR: distance from top edge (y=0).
    BL/BR: distance from bottom edge (y=height-1).
    """
    ys = np.arange(height, dtype=np.float64)
    if quadrant in (Quadrant.TL, Quadrant.TR):
        col = ys / edge_width
    else:
        col = (height - 1 - ys) / edge_width
    return np.tile(col.reshape(-1, 1), (1, width))


# ---------------------------------------------------------------------------
# Noise generation
# ---------------------------------------------------------------------------

def _generate_noise_simplex(
    width: int,
    height: int,
    seed: int,
    quadrant: Quadrant,
) -> NDArray[np.float64]:
    """Generate simplex noise normalized to [-1, 1]."""
    from opensimplex import OpenSimplex

    gen = OpenSimplex(seed=seed + hash(quadrant.value))
    noise = np.zeros((height, width), dtype=np.float64)
    scale = DEFAULT_NOISE_SCALE  # Controls noise frequency
    for y in range(height):
        for x in range(width):
            noise[y, x] = gen.noise2(x * scale, y * scale)
    return noise


def _generate_noise_dithered(width: int, height: int) -> NDArray[np.float64]:
    """Generate checkerboard dither pattern as noise substitute."""
    xs = np.arange(width)
    ys = np.arange(height)
    xx, yy = np.meshgrid(xs, ys)
    # Checkerboard: alternating +0.5 / -0.5
    return np.where((xx + yy) % 2 == 0, 0.5, -0.5).astype(np.float64)


def _get_noise(
    width: int,
    height: int,
    style: str,
    seed: int,
    quadrant: Quadrant,
) -> NDArray[np.float64]:
    """Get noise array based on edge style."""
    if style == "straight":
        return np.zeros((height, width), dtype=np.float64)
    if style == "dithered":
        return _generate_noise_dithered(width, height)
    # Default: organic (simplex)
    return _generate_noise_simplex(width, height, seed, quadrant)


# ---------------------------------------------------------------------------
# Mask generation
# ---------------------------------------------------------------------------


def _make_mask_fill(width: int, height: int) -> NDArray[np.uint8]:
    """FILL mask: all pixels opaque."""
    return np.full((height, width), 255, dtype=np.uint8)


def _make_mask_edge_v(
    width: int,
    height: int,
    quadrant: Quadrant,
    edge_width: int,
    noise: NDArray[np.float64],
    noise_scale: float,
) -> NDArray[np.uint8]:
    """EDGE_V mask using vertical distance field + noise."""
    dist = _distance_v(width, height, quadrant, edge_width)
    field = dist + noise * noise_scale
    return np.where(field > MASK_THRESHOLD, 255, 0).astype(np.uint8)


def _make_mask_edge_h(
    width: int,
    height: int,
    quadrant: Quadrant,
    edge_width: int,
    noise: NDArray[np.float64],
    noise_scale: float,
) -> NDArray[np.uint8]:
    """EDGE_H mask using horizontal distance field + noise."""
    dist = _distance_h(width, height, quadrant, edge_width)
    field = dist + noise * noise_scale
    return np.where(field > MASK_THRESHOLD, 255, 0).astype(np.uint8)


def _make_mask_outer_corner(
    width: int,
    height: int,
    quadrant: Quadrant,
    edge_width: int,
    noise: NDArray[np.float64],
    noise_scale: float,
) -> NDArray[np.uint8]:
    """OUTER_CORNER mask: min(D_h, D_v) + noise > threshold."""
    dist_v = _distance_v(width, height, quadrant, edge_width)
    dist_h = _distance_h(width, height, quadrant, edge_width)
    field = np.minimum(dist_v, dist_h) + noise * noise_scale
    return np.where(field > MASK_THRESHOLD, 255, 0).astype(np.uint8)


def _make_mask_inner_corner(
    width: int,
    height: int,
    quadrant: Quadrant,
    edge_width: int,
    noise: NDArray[np.float64],
    noise_scale: float,
) -> NDArray[np.uint8]:
    """INNER_CORNER mask: max(D_h, D_v) + noise > threshold."""
    dist_v = _distance_v(width, height, quadrant, edge_width)
    dist_h = _distance_h(width, height, quadrant, edge_width)
    field = np.maximum(dist_v, dist_h) + noise * noise_scale
    return np.where(field > MASK_THRESHOLD, 255, 0).astype(np.uint8)


# ---------------------------------------------------------------------------
# Border effects
# ---------------------------------------------------------------------------

def _apply_border_effects(
    pixels: NDArray[np.uint8],
    mask: NDArray[np.uint8],
) -> NDArray[np.uint8]:
    """Apply shadow/highlight to pixels near mask edges.

    Shadow: darken pixels at the outer edge (adjacent to transparent).
    Highlight: brighten pixels one pixel inward from the edge.
    """
    height, width = mask.shape
    result = pixels.copy()
    opaque = mask > 0

    shadow_factor = BORDER_SHADOW_FACTOR
    highlight_factor = BORDER_HIGHLIGHT_FACTOR

    for y in range(height):
        for x in range(width):
            if not opaque[y, x]:
                continue
            # Check if adjacent to transparent pixel
            is_border = False
            for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                ny, nx = y + dy, x + dx
                if 0 <= ny < height and 0 <= nx < width:
                    if not opaque[ny, nx]:
                        is_border = True
                        break
                else:
                    # Edge of sub-tile treated as transparent for border check
                    is_border = True
                    break

            if is_border:
                # Shadow: darken toward black
                for c in range(3):
                    result[y, x, c] = int(result[y, x, c] * shadow_factor)
            else:
                # Check if one pixel inward from border
                is_inner_border = False
                for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                    ny, nx = y + dy, x + dx
                    if 0 <= ny < height and 0 <= nx < width:
                        # Check if (ny, nx) is a border pixel
                        for ddy, ddx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                            nny, nnx = ny + ddy, nx + ddx
                            if 0 <= nny < height and 0 <= nnx < width:
                                if not opaque[nny, nnx]:
                                    is_inner_border = True
                                    break
                            else:
                                is_inner_border = True
                                break
                        if is_inner_border:
                            break

                if is_inner_border:
                    # Highlight: brighten
                    for c in range(3):
                        result[y, x, c] = min(255, int(result[y, x, c] * highlight_factor))

    return result


# ---------------------------------------------------------------------------
# Sub-tile generation
# ---------------------------------------------------------------------------

def _generate_single_subtile(
    base_crop: Image.Image,
    quadrant: Quadrant,
    tile_type: SubTileType,
    edge_width: int,
    noise: NDArray[np.float64],
    noise_scale: float,
) -> Image.Image:
    """Generate a single sub-tile by applying a mask to the cropped texture."""
    width, height = base_crop.size
    pixels = np.array(base_crop)

    mask_generators = {
        SubTileType.FILL: lambda: _make_mask_fill(width, height),
        SubTileType.EDGE_V: lambda: _make_mask_edge_v(
            width, height, quadrant, edge_width, noise, noise_scale,
        ),
        SubTileType.EDGE_H: lambda: _make_mask_edge_h(
            width, height, quadrant, edge_width, noise, noise_scale,
        ),
        SubTileType.OUTER_CORNER: lambda: _make_mask_outer_corner(
            width, height, quadrant, edge_width, noise, noise_scale,
        ),
        SubTileType.INNER_CORNER: lambda: _make_mask_inner_corner(
            width, height, quadrant, edge_width, noise, noise_scale,
        ),
    }

    mask = mask_generators[tile_type]()

    # Apply border effects for non-FILL types
    if tile_type != SubTileType.FILL:
        pixels = _apply_border_effects(pixels, mask)

    # Apply mask to alpha channel
    result = pixels.copy()
    result[:, :, 3] = mask

    return Image.fromarray(result, "RGBA")


def generate_subtiles(
    base_texture: Image.Image,
    edge_config: dict[str, object],
    seed: int = 0,
) -> SubTileSet:
    """Generate all 20 sub-tiles from a base texture.

    Args:
        base_texture: Seamless RGBA texture, at least 32×32.
        edge_config: Dict with keys 'style' ('organic'|'straight'|'dithered'),
                     'width' (int edge width), 'noise_scale' (float).
        seed: Random seed for deterministic noise generation.

    Returns:
        SubTileSet with 20 sub-tiles (4 quadrants × 5 types).

    Raises:
        ValueError: If base_texture is too small or not RGBA.
    """
    if base_texture.size[0] < TILE_SIZE or base_texture.size[1] < TILE_SIZE:
        msg = f"Base texture must be at least {TILE_SIZE}x{TILE_SIZE}, got {base_texture.size}"
        raise ValueError(msg)

    # Ensure RGBA mode
    texture = base_texture.convert("RGBA") if base_texture.mode != "RGBA" else base_texture

    style = str(edge_config.get("style", "organic"))
    edge_width = int(edge_config.get("width", DEFAULT_EDGE_WIDTH))  # type: ignore[arg-type]
    noise_scale = float(edge_config.get("noise_scale", DEFAULT_EDGE_NOISE_SCALE))  # type: ignore[arg-type]

    tiles: dict[tuple[Quadrant, SubTileType], Image.Image] = {}

    for quadrant in Quadrant:
        crop = _crop_quadrant(texture, quadrant)
        width, height = crop.size
        noise = _get_noise(width, height, style, seed, quadrant)

        for tile_type in SubTileType:
            tiles[(quadrant, tile_type)] = _generate_single_subtile(
                crop, quadrant, tile_type, edge_width, noise, noise_scale,
            )

    return SubTileSet(tiles=tiles)
