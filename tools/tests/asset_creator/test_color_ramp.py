"""Tests for the OKLCh color ramp engine (TC-025 through TC-030)."""

from __future__ import annotations

import pytest

try:
    from asset_creator.core.color_ramp import (
        generate_hue_shifted_ramp,
        interpolate_oklch,
        oklch_to_rgb,
        rgb_to_oklch,
    )

    HAS_COLOR_RAMP = True
except ImportError:
    HAS_COLOR_RAMP = False

pytestmark = pytest.mark.skipif(not HAS_COLOR_RAMP, reason="color_ramp module not implemented yet")


class TestRgbOklchRoundTrip:
    """TC-025: rgb_to_oklch + oklch_to_rgb round-trip matches original ±1."""

    _COLORS: tuple[tuple[int, int, int], ...] = (
        (255, 0, 0),  # pure red
        (0, 255, 0),  # pure green
        (0, 0, 255),  # pure blue
        (255, 255, 255),  # white
        (0, 0, 0),  # black
        (97, 132, 71),  # mid-tone green (existing grass palette)
    )

    @pytest.mark.tc("TC-025")
    @pytest.mark.parametrize(
        "rgb",
        _COLORS,
        ids=[
            "pure_red",
            "pure_green",
            "pure_blue",
            "white",
            "black",
            "mid_green",
        ],
    )
    def test_round_trip(self, rgb: tuple[int, int, int]) -> None:
        """RGB -> OKLCh -> RGB must match original within ±1 per channel."""
        L, C, h = rgb_to_oklch(*rgb)
        r2, g2, b2 = oklch_to_rgb(L, C, h)

        assert abs(r2 - rgb[0]) <= 1, f"R: {r2} vs {rgb[0]}"
        assert abs(g2 - rgb[1]) <= 1, f"G: {g2} vs {rgb[1]}"
        assert abs(b2 - rgb[2]) <= 1, f"B: {b2} vs {rgb[2]}"

    @pytest.mark.tc("TC-025")
    def test_oklch_values_in_expected_ranges(self) -> None:
        """OKLCh output must have L in ~[0,1], C >= 0, h in [0,360).

        A small epsilon (1e-4) is used for L because the Oklab matrix
        constants produce L≈1.000027 for pure white — a known floating-
        point precision limitation of the standard matrices.
        """
        eps = 1e-4
        for rgb in self._COLORS:
            L, C, h = rgb_to_oklch(*rgb)
            assert -eps <= L <= 1.0 + eps, f"L out of range for {rgb}: {L}"
            assert -eps <= C, f"C negative for {rgb}: {C}"
            assert 0.0 <= h < 360.0, f"h out of range for {rgb}: {h}"


class TestGenerateHueShiftedRampCount:
    """TC-026: Ramp output has exactly num_steps colors."""

    @pytest.mark.tc("TC-026")
    @pytest.mark.parametrize("num_steps", [9, 11])
    def test_ramp_length(self, num_steps: int) -> None:
        """Ramp must contain exactly num_steps colors."""
        base = (97, 132, 71)
        ramp = generate_hue_shifted_ramp(base, num_steps=num_steps)

        assert len(ramp) == num_steps


class TestRampLightnessMonotonicity:
    """TC-027: Lightness monotonically increases from shadow to highlight."""

    @pytest.mark.tc("TC-027")
    def test_lightness_non_decreasing(self) -> None:
        """OKLCh L values must be non-decreasing across the ramp."""
        base = (97, 132, 71)
        ramp = generate_hue_shifted_ramp(base, num_steps=9)

        lightness_values = [rgb_to_oklch(*color)[0] for color in ramp]
        for i in range(1, len(lightness_values)):
            assert lightness_values[i] >= lightness_values[i - 1] - 1e-9, (
                f"Lightness decreased at index {i}: "
                f"{lightness_values[i - 1]:.4f} -> {lightness_values[i]:.4f}"
            )

    @pytest.mark.tc("TC-027")
    def test_lightness_non_decreasing_bright_base(self) -> None:
        """Lightness non-decreasing even with a bright base color."""
        base = (220, 230, 210)
        ramp = generate_hue_shifted_ramp(base, num_steps=9)

        lightness_values = [rgb_to_oklch(*color)[0] for color in ramp]
        for i in range(1, len(lightness_values)):
            assert lightness_values[i] >= lightness_values[i - 1] - 1e-9, (
                f"Lightness decreased at index {i}: "
                f"{lightness_values[i - 1]:.4f} -> {lightness_values[i]:.4f}"
            )


class TestRampHueShift:
    """TC-028: Shadow and highlight colors have correct hue shifts."""

    @pytest.mark.tc("TC-028")
    def test_shadow_hue_shift_direction(self) -> None:
        """Shadow colors (first 3) should be shifted toward shadow_hue_shift."""
        base = (97, 132, 71)
        shadow_shift = -30.0
        ramp = generate_hue_shifted_ramp(
            base,
            num_steps=9,
            shadow_hue_shift=shadow_shift,
            highlight_hue_shift=20.0,
        )

        _, _, h_base = rgb_to_oklch(*base)
        # First color (darkest shadow) should have most hue shift
        _, _, h_shadow = rgb_to_oklch(*ramp[0])

        # The shadow hue should differ from base in the shadow_shift direction
        diff = (h_shadow - h_base + 180) % 360 - 180
        # shadow_shift is -30, so the diff should be negative
        assert diff < 0, (
            f"Shadow hue should shift negative. "
            f"Base hue: {h_base:.1f}, Shadow hue: {h_shadow:.1f}, diff: {diff:.1f}"
        )

    @pytest.mark.tc("TC-028")
    def test_highlight_hue_shift_direction(self) -> None:
        """Highlight colors (last 3) should be shifted toward highlight_hue_shift."""
        base = (97, 132, 71)
        highlight_shift = 20.0
        ramp = generate_hue_shifted_ramp(
            base,
            num_steps=9,
            shadow_hue_shift=-30.0,
            highlight_hue_shift=highlight_shift,
        )

        _, _, h_base = rgb_to_oklch(*base)
        # Last color (brightest highlight) should have most hue shift
        _, _, h_highlight = rgb_to_oklch(*ramp[-1])

        # The highlight hue should differ from base in the positive direction
        diff = (h_highlight - h_base + 180) % 360 - 180
        assert diff > 0, (
            f"Highlight hue should shift positive. "
            f"Base hue: {h_base:.1f}, Highlight hue: {h_highlight:.1f}, diff: {diff:.1f}"
        )


class TestRampSrgbValidity:
    """TC-029: All generated colors are valid sRGB [0, 255]."""

    @pytest.mark.tc("TC-029")
    @pytest.mark.parametrize(
        "base_rgb",
        [
            (97, 132, 71),  # mid-tone green
            (10, 10, 10),  # very dark
            (245, 245, 245),  # very bright
            (255, 0, 0),  # saturated red
            (0, 0, 255),  # saturated blue
        ],
        ids=["mid_green", "very_dark", "very_bright", "saturated_red", "saturated_blue"],
    )
    def test_all_channels_in_range(self, base_rgb: tuple[int, int, int]) -> None:
        """Every channel of every ramp color must be in [0, 255]."""
        ramp = generate_hue_shifted_ramp(base_rgb, num_steps=9)

        for i, color in enumerate(ramp):
            assert len(color) == 3, f"Color at index {i} has {len(color)} channels"
            for ch_idx, val in enumerate(color):
                assert isinstance(val, int), (
                    f"Channel {ch_idx} at index {i} is {type(val)}, expected int"
                )
                assert 0 <= val <= 255, f"Channel {ch_idx} at index {i} out of range: {val}"


class TestInterpolateOklch:
    """TC-030: OKLCh interpolation boundary and midpoint behavior."""

    @pytest.mark.tc("TC-030")
    def test_interpolate_t0_returns_color_a(self) -> None:
        """interpolate_oklch(a, b, 0.0) must return a (±1)."""
        a = (255, 0, 0)
        b = (0, 0, 255)
        result = interpolate_oklch(a, b, 0.0)

        assert abs(result[0] - a[0]) <= 1
        assert abs(result[1] - a[1]) <= 1
        assert abs(result[2] - a[2]) <= 1

    @pytest.mark.tc("TC-030")
    def test_interpolate_t1_returns_color_b(self) -> None:
        """interpolate_oklch(a, b, 1.0) must return b (±1)."""
        a = (255, 0, 0)
        b = (0, 0, 255)
        result = interpolate_oklch(a, b, 1.0)

        assert abs(result[0] - b[0]) <= 1
        assert abs(result[1] - b[1]) <= 1
        assert abs(result[2] - b[2]) <= 1

    @pytest.mark.tc("TC-030")
    def test_interpolate_midpoint_between_a_and_b(self) -> None:
        """interpolate_oklch(a, b, 0.5) produces a color between a and b.

        Verified by checking the L value is between L_a and L_b.
        """
        a = (50, 50, 50)
        b = (200, 200, 200)
        result = interpolate_oklch(a, b, 0.5)

        L_a, _, _ = rgb_to_oklch(*a)
        L_b, _, _ = rgb_to_oklch(*b)
        L_mid, _, _ = rgb_to_oklch(*result)

        assert min(L_a, L_b) <= L_mid <= max(L_a, L_b), (
            f"Midpoint L={L_mid:.4f} not between L_a={L_a:.4f} and L_b={L_b:.4f}"
        )

    @pytest.mark.tc("TC-030")
    def test_interpolate_same_color_returns_same(self) -> None:
        """Interpolating between the same color returns that color (±1)."""
        c = (100, 150, 200)
        result = interpolate_oklch(c, c, 0.5)

        assert abs(result[0] - c[0]) <= 1
        assert abs(result[1] - c[1]) <= 1
        assert abs(result[2] - c[2]) <= 1
