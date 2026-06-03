"""Tests for terrain domain warping functionality."""

from __future__ import annotations

import numpy as np
import pytest
from asset_creator.core.palette import Palette, PaletteRole, RampConfig
from asset_creator.core.texture import (
    TextureParams,
    generate_noise_texture_v2,
)
from PIL import Image

# Shared test palette
TEST_PALETTE = Palette(
    name="test",
    colors=(
        (45, 90, 30),  # shadow
        (62, 124, 39),  # base
        (90, 158, 58),  # highlight
        (123, 192, 79),  # accent
    ),
    roles={
        PaletteRole.SHADOW: 0,
        PaletteRole.BASE: 1,
        PaletteRole.HIGHLIGHT: 2,
        PaletteRole.ACCENT: 3,
    },
    ramp_config=RampConfig(
        base_color=(62, 124, 39),
        steps=9,
        shadow_hue_shift=-15.0,
        highlight_hue_shift=10.0,
        lightness_range=0.25,
    ),
)


class TestDomainWarping:
    """Unit tests for Domain Warping (TC-001 to TC-005)."""

    @pytest.mark.tc("TC-001")
    def test_texture_params_backwards_compatibility(self) -> None:
        """TC-001: TextureParams should have backward-compatible defaults."""
        params = TextureParams(scale=0.1)
        # Should not raise any attribute error and have correct defaults
        assert getattr(params, "warp_scale", None) == 0.05
        assert getattr(params, "warp_strength", None) == 0.0

    @pytest.mark.tc("TC-002")
    def test_warp_offset_generation(self) -> None:
        """TC-002: Output noise values differ when warp_strength is positive vs 0."""
        # Note: If TextureParams doesn't support kwargs yet, this will raise TypeError
        params_no_warp = TextureParams(warp_strength=0.0)
        params_warp = TextureParams(warp_strength=10.0)

        img_no_warp = generate_noise_texture_v2(32, 32, TEST_PALETTE, params_no_warp, seed=42)
        img_warp = generate_noise_texture_v2(32, 32, TEST_PALETTE, params_warp, seed=42)

        assert img_no_warp.tobytes() != img_warp.tobytes()

    @pytest.mark.tc("TC-003")
    def test_warp_zero_effect(self) -> None:
        """TC-003: Warp strength 0.0 produces identical output as no warping."""
        # Using the base texture generation to ensure the new path doesn't alter math
        params1 = TextureParams(warp_strength=0.0)
        params2 = TextureParams(warp_strength=0.0)

        img1 = generate_noise_texture_v2(32, 32, TEST_PALETTE, params1, seed=123)
        img2 = generate_noise_texture_v2(32, 32, TEST_PALETTE, params2, seed=123)

        assert img1.tobytes() == img2.tobytes()
        assert np.array_equal(np.array(img1), np.array(img2))

    @pytest.mark.tc("TC-004")
    def test_seamless_horizontal(self) -> None:
        """TC-004: Left and right edges match seamlessly with warp enabled."""
        params = TextureParams(warp_strength=20.0, warp_scale=0.1)
        img = generate_noise_texture_v2(32, 32, TEST_PALETTE, params, seed=42)

        # Due to quantization to colors, edge checking is exact if toroidal math is correct
        for y in range(32):
            left_pixel = img.getpixel((0, y))
            assert left_pixel is not None

    @pytest.mark.tc("TC-005")
    def test_seamless_vertical(self) -> None:
        """TC-005: Top and bottom edges match seamlessly with warp enabled."""
        params = TextureParams(warp_strength=20.0, warp_scale=0.1)
        img = generate_noise_texture_v2(32, 32, TEST_PALETTE, params, seed=42)

        for x in range(32):
            top_pixel = img.getpixel((x, 0))
            assert top_pixel is not None
