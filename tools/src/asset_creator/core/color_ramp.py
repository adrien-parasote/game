"""OKLCh color space utilities and hue-shifted ramp generation.

Provides perceptually uniform color interpolation and ramp generation
for pixel art palettes. Uses Oklab/OKLCh color space instead of HSL
to avoid muddy mid-tones.
"""

from __future__ import annotations

import math


def _srgb_to_linear(c: float) -> float:
    """Convert sRGB component [0,1] to linear RGB."""
    if c <= 0.04045:
        return c / 12.92
    return ((c + 0.055) / 1.055) ** 2.4


def _linear_to_srgb(c: float) -> float:
    """Convert linear RGB component to sRGB [0,1]."""
    if c <= 0.0031308:
        return c * 12.92
    return 1.055 * (c ** (1.0 / 2.4)) - 0.055


def _linear_rgb_to_oklab(
    r: float,
    g: float,
    b: float,
) -> tuple[float, float, float]:
    """Convert linear RGB to Oklab (L, a, b).

    Uses the M1 (RGB→LMS) and M2 (LMS_cbrt→Lab) matrices from the
    official Oklab specification by Björn Ottosson.
    """
    # M1: linear sRGB -> LMS
    l_ = 0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b
    m_ = 0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b
    s_ = 0.0883024619 * r + 0.2024326933 * g + 0.6892650048 * b

    # Cube root (signed to handle edge cases near zero)
    l_cbrt = math.copysign(abs(l_) ** (1 / 3), l_) if l_ != 0 else 0.0
    m_cbrt = math.copysign(abs(m_) ** (1 / 3), m_) if m_ != 0 else 0.0
    s_cbrt = math.copysign(abs(s_) ** (1 / 3), s_) if s_ != 0 else 0.0

    # M2: LMS_cbrt -> Lab
    big_l = 0.2104542553 * l_cbrt + 0.7936177850 * m_cbrt - 0.0040720468 * s_cbrt
    a_val = 1.9779984951 * l_cbrt - 2.4285922050 * m_cbrt + 0.4505937099 * s_cbrt
    b_val = 0.0259040371 * l_cbrt + 0.7827717662 * m_cbrt - 0.8086757660 * s_cbrt

    return (big_l, a_val, b_val)


def _oklab_to_linear_rgb(
    big_l: float,
    a: float,
    b: float,
) -> tuple[float, float, float]:
    """Convert Oklab (L, a, b) to linear RGB.

    Uses M2^-1 (Lab→LMS_cbrt) then cubing, then M1^-1 (LMS→RGB).
    Matrix values computed as true inverse of M1/M2 for round-trip
    accuracy.
    """
    # M2^-1: Lab -> LMS_cbrt
    l_ = big_l + 0.3963377774 * a + 0.2158037573 * b
    m_ = big_l - 0.1055613458 * a - 0.0638541728 * b
    s_ = big_l - 0.0894841775 * a - 1.2914855480 * b

    # Cube to get LMS
    l_cubed = l_ * l_ * l_
    m_cubed = m_ * m_ * m_
    s_cubed = s_ * s_ * s_

    # M1^-1: LMS -> linear sRGB (true inverse of M1, computed via numpy)
    r = +4.0562053820035 * l_cubed - 3.2568174131119 * m_cubed + 0.2047061204385 * s_cubed
    g = -1.2380901986143 * l_cubed + 2.5345477404013 * m_cubed - 0.3025076460534 * s_cubed
    b_val = -0.1560256026350 * l_cubed - 0.3271460588888 * m_cubed + 1.5134402238170 * s_cubed

    return (r, g, b_val)


def rgb_to_oklch(r: int, g: int, b: int) -> tuple[float, float, float]:
    """Convert sRGB (0-255) to OKLCh (lightness, chroma, hue°).

    Args:
        r: Red channel 0-255.
        g: Green channel 0-255.
        b: Blue channel 0-255.

    Returns:
        Tuple of (L in [0,1], C >= 0, h in [0, 360)).
    """
    # sRGB [0,255] -> [0,1] -> linear
    lr = _srgb_to_linear(r / 255.0)
    lg = _srgb_to_linear(g / 255.0)
    lb = _srgb_to_linear(b / 255.0)

    big_l, a, b_val = _linear_rgb_to_oklab(lr, lg, lb)

    c = math.sqrt(a * a + b_val * b_val)
    h = math.degrees(math.atan2(b_val, a)) % 360

    return (big_l, c, h)


def oklch_to_rgb(
    big_l: float,
    c: float,
    h: float,
) -> tuple[int, int, int]:
    """Convert OKLCh back to clamped sRGB (0-255).

    Args:
        big_l: Lightness in [0, 1].
        c: Chroma >= 0.
        h: Hue in degrees [0, 360).

    Returns:
        Tuple of (r, g, b) integers clamped to [0, 255].
    """
    a = c * math.cos(math.radians(h))
    b_val = c * math.sin(math.radians(h))

    lr, lg, lb = _oklab_to_linear_rgb(big_l, a, b_val)

    # Linear -> sRGB -> [0,255], clamped
    sr = _linear_to_srgb(max(0.0, min(1.0, lr)))
    sg = _linear_to_srgb(max(0.0, min(1.0, lg)))
    sb = _linear_to_srgb(max(0.0, min(1.0, lb)))

    return (
        max(0, min(255, round(sr * 255))),
        max(0, min(255, round(sg * 255))),
        max(0, min(255, round(sb * 255))),
    )


def interpolate_oklch(
    color_a: tuple[int, int, int],
    color_b: tuple[int, int, int],
    t: float,
) -> tuple[int, int, int]:
    """Interpolate between two RGB colors in OKLCh space.

    Args:
        color_a: Start RGB color.
        color_b: End RGB color.
        t: Interpolation factor in [0, 1]. 0 = color_a, 1 = color_b.

    Returns:
        Interpolated RGB color.
    """
    la, ca, ha = rgb_to_oklch(*color_a)
    lb, cb, hb = rgb_to_oklch(*color_b)

    # Interpolate L and C linearly
    big_l = la + (lb - la) * t
    c = ca + (cb - ca) * t

    # Interpolate hue via shortest arc
    diff = hb - ha
    if diff > 180:
        diff -= 360
    elif diff < -180:
        diff += 360
    h = (ha + diff * t) % 360

    return oklch_to_rgb(big_l, c, h)


def generate_hue_shifted_ramp(
    base_rgb: tuple[int, int, int],
    num_steps: int = 9,
    shadow_hue_shift: float = -30.0,
    highlight_hue_shift: float = 20.0,
    lightness_range: float = 0.35,
    saturation_curve: float = 0.02,
) -> list[tuple[int, int, int]]:
    """Generate a hue-shifted color ramp from a base color.

    Shadows shift toward cooler hues (negative shift), highlights toward
    warmer hues (positive shift). Saturation increases slightly in shadows
    and decreases in highlights.

    Args:
        base_rgb: Anchor RGB color (appears at the midpoint of the ramp).
        num_steps: Number of colors in the ramp (typically 7-11).
        shadow_hue_shift: Hue shift in degrees for the darkest shadow.
            Negative = cooler.
        highlight_hue_shift: Hue shift in degrees for the brightest
            highlight. Positive = warmer.
        lightness_range: Total lightness spread (half above, half below).
        saturation_curve: Chroma adjustment magnitude.
            Positive = shadows more saturated.

    Returns:
        List of RGB tuples ordered darkest (shadow) to brightest (highlight).
    """
    l_base, c_base, h_base = rgb_to_oklch(*base_rgb)

    mid = num_steps // 2
    ramp: list[tuple[int, int, int]] = []

    for i in range(num_steps):
        # t ranges from -1 (darkest) to +1 (brightest)
        t = (i - mid) / max(mid, 1)

        # Lightness: linear spread around base
        new_l = l_base + t * (lightness_range / 2)
        new_l = max(0.0, min(1.0, new_l))

        # Chroma: slightly higher in shadows, lower in highlights
        chroma_adj = -t * saturation_curve  # negative t (shadow) -> + chroma
        new_c = max(0.0, c_base + chroma_adj)

        # Hue: shift based on direction
        hue_shift = shadow_hue_shift * abs(t) if t < 0 else highlight_hue_shift * t
        new_h = (h_base + hue_shift) % 360

        ramp.append(oklch_to_rgb(new_l, new_c, new_h))

    return ramp
