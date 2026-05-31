"""Terrain-specific detail overlays for V2 texture generation.

Applies procedural stamps (grass blades, dirt specks, stone cracks, sand grains)
on top of the base texture for visual richness.
"""
from __future__ import annotations

import inspect
import random

from PIL import Image

from tools.asset_creator.core.palette import Palette


def _add_grass_blades(
    img: Image.Image,
    palette: Palette,
    seed: int,
    density: float = 0.12,
    max_height: int = 4,
) -> None:
    """Overlay procedural grass blade detail.

    Draws vertical 1-pixel-wide blades at random positions.
    Uses the top 3 colors from the extended palette ramp:
    highlight at base, accent in middle, tip (brightest) at top.

    Args:
        img: Image to modify in-place.
        palette: Palette with extended_colors.
        seed: Random seed for reproducibility.
        density: Fraction of pixels to seed blades (0-0.5).
        max_height: Maximum blade height in pixels.
    """
    rng = random.Random(seed)
    w, h = img.size
    pixels = img.load()
    if pixels is None:
        raise RuntimeError("Failed to load image pixels")
    colors = list(palette.extended_colors)

    # Use top 3 colors from ramp as highlight/accent/tip
    highlight = colors[-3] if len(colors) >= 3 else colors[-1]
    accent = colors[-2] if len(colors) >= 2 else colors[-1]
    tip = colors[-1]

    num_blades = int(w * h * density)

    for _ in range(num_blades):
        bx = rng.randint(0, w - 1)
        by = rng.randint(max_height, h - 1)
        blade_h = rng.randint(2, max(2, max_height))

        for j in range(blade_h):
            py = by - j
            if 0 <= py < h:
                # Tip = brightest, base = highlight
                if j == blade_h - 1:
                    color = tip
                elif j >= blade_h // 2:
                    color = accent
                else:
                    color = highlight
                pixels[bx, py] = (*color, 255)

            # Random bend
            if rng.random() < 0.3:
                bx = max(0, min(w - 1, bx + rng.choice([-1, 1])))


def _add_dirt_specks(
    img: Image.Image,
    palette: Palette,
    seed: int,
    density: float = 0.08,
) -> None:
    """Scatter dark/light single-pixel specks.

    Args:
        img: Image to modify in-place.
        palette: Palette with extended_colors.
        seed: Random seed for reproducibility.
        density: Probability per pixel of placing a speck (0-0.5).
    """
    rng = random.Random(seed)
    w, h = img.size
    pixels = img.load()
    if pixels is None:
        raise RuntimeError("Failed to load image pixels")
    colors = list(palette.extended_colors)

    dark = colors[0]   # darkest
    light = colors[-1]  # brightest

    for y in range(h):
        for x in range(w):
            if rng.random() < density:
                color = dark if rng.random() < 0.6 else light
                pixels[x, y] = (*color, 255)


def _add_stone_cracks(
    img: Image.Image,
    palette: Palette,
    seed: int,
    density: float = 0.05,
    max_length: int = 4,
) -> None:
    """Draw thin crack lines in shadow color.

    Uses a random-walk to create natural-looking cracks.

    Args:
        img: Image to modify in-place.
        palette: Palette with extended_colors.
        seed: Random seed for reproducibility.
        density: Fraction of total pixels used to seed cracks (0-0.5).
        max_length: Maximum crack length in pixels.
    """
    rng = random.Random(seed)
    w, h = img.size
    pixels = img.load()
    if pixels is None:
        raise RuntimeError("Failed to load image pixels")
    colors = list(palette.extended_colors)
    shadow = colors[0]

    num_cracks = int(w * h * density)

    for _ in range(num_cracks):
        cx = rng.randint(0, w - 1)
        cy = rng.randint(0, h - 1)
        length = rng.randint(2, max(2, max_length))

        for _ in range(length):
            if 0 <= cx < w and 0 <= cy < h:
                pixels[cx, cy] = (*shadow, 255)
            # Random walk
            cx += rng.choice([-1, 0, 1])
            cy += rng.choice([-1, 0, 1])


def _add_sand_grains(
    img: Image.Image,
    palette: Palette,
    seed: int,
    density: float = 0.10,
) -> None:
    """Single-pixel bright/dark grains for sandy textures.

    Args:
        img: Image to modify in-place.
        palette: Palette with extended_colors.
        seed: Random seed for reproducibility.
        density: Probability per pixel of placing a grain (0-0.5).
    """
    rng = random.Random(seed)
    w, h = img.size
    pixels = img.load()
    if pixels is None:
        raise RuntimeError("Failed to load image pixels")
    colors = list(palette.extended_colors)

    dark = colors[1] if len(colors) > 1 else colors[0]
    bright = colors[-2] if len(colors) > 2 else colors[-1]

    for y in range(h):
        for x in range(w):
            if rng.random() < density:
                color = bright if rng.random() < 0.5 else dark
                pixels[x, y] = (*color, 255)


_OVERLAY_TYPES = {
    "grass_blades": _add_grass_blades,
    "dirt_specks": _add_dirt_specks,
    "stone_cracks": _add_stone_cracks,
    "sand_grains": _add_sand_grains,
}


def apply_detail_overlay(
    img: Image.Image,
    palette: Palette,
    detail_type: str,
    density: float,
    seed: int,
    **kwargs: object,
) -> Image.Image:
    """Apply terrain-specific detail overlay to base texture.

    Always returns a copy — never mutates the input image.

    Args:
        img: Base texture image (will be copied, not mutated).
        palette: Color palette with extended_colors.
        detail_type: Type of overlay: 'grass_blades', 'dirt_specks',
                     'stone_cracks', 'sand_grains', or 'none'.
        density: Overlay density (clamped to 0.0-0.5).
        seed: Random seed for reproducibility.
        **kwargs: Additional arguments passed to the overlay function.

    Returns:
        New image with overlay applied.

    Raises:
        ValueError: If detail_type is not recognized.
    """
    if detail_type == "none":
        return img.copy()

    if detail_type not in _OVERLAY_TYPES:
        valid = sorted(_OVERLAY_TYPES.keys()) + ["none"]
        raise ValueError(
            f"Unknown detail type '{detail_type}'. Valid types: {valid}"
        )

    density = max(0.0, min(0.5, density))  # Clamp

    result = img.copy()
    overlay_fn = _OVERLAY_TYPES[detail_type]

    # Filter kwargs to only include params the overlay function accepts
    sig = inspect.signature(overlay_fn)
    valid_params = set(sig.parameters.keys()) - {"img", "palette", "seed", "density"}
    filtered_kwargs = {k: v for k, v in kwargs.items() if k in valid_params}

    overlay_fn(result, palette, seed, density=density, **filtered_kwargs)
    return result
