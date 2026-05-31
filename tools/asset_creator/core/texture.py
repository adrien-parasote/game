"""Texture generation for the Asset Creator Tool.

Generates pixel art textures using noise, patterns, and palette colors.
Supports toroidal mapping for seamless tiling.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field

from opensimplex import OpenSimplex
from PIL import Image

from tools.asset_creator.core.palette import Palette, PaletteRole


@dataclass(frozen=True)
class TextureParams:
    """Parameters controlling texture generation.

    Attributes:
        texture_type: Type of texture ('noise', 'solid', 'dithered', etc.).
        scale: Noise sampling scale — larger values = more zoomed out.
        octaves: Number of noise octaves for multi-frequency detail.
        persistence: Amplitude decay per octave (0-1).
        lacunarity: Frequency multiplier per octave.
        thresholds: Noise value breakpoints mapping to palette roles.
        density: Probability of accent dots for stippled patterns (0-1).
    """

    texture_type: str = "noise"
    scale: float = 0.15
    octaves: int = 3
    persistence: float = 0.5
    lacunarity: float = 2.0
    thresholds: list[float] = field(default_factory=lambda: [-0.2, 0.4, 0.8])
    density: float = 0.3


def sample_toroidal_noise(
    x: float,
    y: float,
    width: int,
    height: int,
    scale: float,
    noise_gen: OpenSimplex,
) -> float:
    """Sample noise on a 2D torus mapped into 4D noise space.

    Maps (x, y) coordinates onto a torus via trigonometric projection,
    ensuring perfect seamless tiling in both axes.

    Args:
        x: Horizontal coordinate.
        y: Vertical coordinate.
        width: Texture width in pixels.
        height: Texture height in pixels.
        scale: Noise sampling scale factor.
        noise_gen: OpenSimplex noise generator instance.

    Returns:
        Noise value in approximately [-1, 1].
    """
    angle_x = (x / width) * 2 * math.pi
    angle_y = (y / height) * 2 * math.pi
    nx = math.cos(angle_x) * scale
    ny = math.sin(angle_x) * scale
    nz = math.cos(angle_y) * scale
    nw = math.sin(angle_y) * scale
    return noise_gen.noise4(nx, ny, nz, nw)


def _compute_multi_octave_noise(
    x: int,
    y: int,
    width: int,
    height: int,
    params: TextureParams,
    noise_gen: OpenSimplex,
) -> float:
    """Compute multi-octave toroidal noise for a single pixel.

    Args:
        x: Pixel x coordinate.
        y: Pixel y coordinate.
        width: Texture width.
        height: Texture height.
        params: Texture generation parameters.
        noise_gen: OpenSimplex noise generator.

    Returns:
        Combined noise value (not normalized to [-1,1]).
    """
    value = 0.0
    amplitude = 1.0
    frequency = 1.0

    for _ in range(params.octaves):
        value += amplitude * sample_toroidal_noise(
            x, y, width, height, params.scale * frequency, noise_gen,
        )
        amplitude *= params.persistence
        frequency *= params.lacunarity

    return value


def _noise_to_color(
    value: float,
    palette: Palette,
    thresholds: list[float],
) -> tuple[int, int, int]:
    """Map a noise value to a palette color using threshold breakpoints.

    Args:
        value: Noise value (approximately [-1, 1]).
        palette: Color palette with role mappings.
        thresholds: List of 3 threshold values [shadow, base, highlight].

    Returns:
        RGB color tuple from the palette.
    """
    if value < thresholds[0]:
        return palette.get_color(PaletteRole.SHADOW)
    if value < thresholds[1]:
        return palette.get_color(PaletteRole.BASE)
    if value < thresholds[2]:
        return palette.get_color(PaletteRole.HIGHLIGHT)
    return palette.get_color(PaletteRole.ACCENT)


def generate_noise_texture(
    width: int,
    height: int,
    palette: Palette,
    params: TextureParams,
    seed: int = 0,
) -> Image.Image:
    """Generate a seamless noise texture using toroidal noise mapping.

    Args:
        width: Image width in pixels.
        height: Image height in pixels.
        palette: Color palette to use.
        params: Noise generation parameters.
        seed: Random seed for reproducibility.

    Returns:
        RGBA PIL Image with pixels colored from the palette.
    """
    noise_gen = OpenSimplex(seed=seed)
    img = Image.new("RGBA", (width, height))
    pixels = img.load()

    for y in range(height):
        for x in range(width):
            value = _compute_multi_octave_noise(
                x, y, width, height, params, noise_gen,
            )
            rgb = _noise_to_color(value, palette, params.thresholds)
            pixels[x, y] = (*rgb, 255)

    return img


def _generate_solid(
    width: int, height: int, palette: Palette,
) -> Image.Image:
    """Fill with base color."""
    base = palette.get_color(PaletteRole.BASE)
    img = Image.new("RGBA", (width, height), (*base, 255))
    return img


def _generate_dithered(
    width: int, height: int, palette: Palette,
) -> Image.Image:
    """Alternate pixels between base and shadow using checkerboard."""
    base = palette.get_color(PaletteRole.BASE)
    shadow = palette.get_color(PaletteRole.SHADOW)
    img = Image.new("RGBA", (width, height))
    pixels = img.load()

    for y in range(height):
        for x in range(width):
            color = base if (x + y) % 2 == 0 else shadow
            pixels[x, y] = (*color, 255)

    return img


def _generate_stippled(
    width: int, height: int, palette: Palette, density: float, seed: int,
) -> Image.Image:
    """Scatter accent dots at density probability using seeded random."""
    base = palette.get_color(PaletteRole.BASE)
    accent = palette.get_color(PaletteRole.ACCENT)
    img = Image.new("RGBA", (width, height))
    pixels = img.load()
    rng = random.Random(seed)

    for y in range(height):
        for x in range(width):
            color = accent if rng.random() < density else base
            pixels[x, y] = (*color, 255)

    return img


def _generate_striped(
    width: int, height: int, palette: Palette,
) -> Image.Image:
    """Horizontal stripes alternating base/shadow."""
    base = palette.get_color(PaletteRole.BASE)
    shadow = palette.get_color(PaletteRole.SHADOW)
    img = Image.new("RGBA", (width, height))
    pixels = img.load()

    for y in range(height):
        color = base if y % 2 == 0 else shadow
        for x in range(width):
            pixels[x, y] = (*color, 255)

    return img


def generate_pattern_texture(
    width: int,
    height: int,
    palette: Palette,
    pattern_type: str,
    params: TextureParams,
    seed: int = 0,
) -> Image.Image:
    """Generate a pattern-based texture.

    Supported pattern types:
        - 'solid': Fill with base color.
        - 'dithered': Checkerboard alternation of base/shadow.
        - 'stippled': Random accent dots at given density.
        - 'noise': Delegate to generate_noise_texture.
        - 'striped': Horizontal stripes of base/shadow.

    Args:
        width: Image width in pixels.
        height: Image height in pixels.
        palette: Color palette to use.
        pattern_type: One of 'solid', 'dithered', 'stippled', 'noise', 'striped'.
        params: Texture generation parameters.
        seed: Random seed for reproducibility.

    Returns:
        RGBA PIL Image.

    Raises:
        ValueError: If pattern_type is not recognized.
    """
    if pattern_type == "solid":
        return _generate_solid(width, height, palette)
    if pattern_type == "dithered":
        return _generate_dithered(width, height, palette)
    if pattern_type == "stippled":
        return _generate_stippled(width, height, palette, params.density, seed)
    if pattern_type == "noise":
        return generate_noise_texture(width, height, palette, params, seed)
    if pattern_type == "striped":
        return _generate_striped(width, height, palette)
    raise ValueError(
        f"Unknown pattern type '{pattern_type}'. "
        f"Valid types: solid, dithered, stippled, noise, striped."
    )
