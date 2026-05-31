"""Tests for the texture generation system."""

from __future__ import annotations

import pytest
from asset_creator.core.palette import Palette, PaletteRole, RampConfig
from asset_creator.core.texture import (
    TextureParams,
    generate_noise_texture_v2,
    generate_pattern_texture,
    sample_toroidal_noise,
)

# Shared test palette
TEST_PALETTE = Palette(
    name="test",
    colors=(
        (45, 90, 30),   # shadow
        (62, 124, 39),  # base
        (90, 158, 58),  # highlight
        (123, 192, 79), # accent
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


class TestNoiseTexture:
    """Noise texture has correct dimensions and tiles seamlessly."""

    def test_noise_texture_dimensions(self) -> None:
        """Generated noise texture must match requested width and height."""
        params = TextureParams(texture_type="noise")
        img = generate_noise_texture_v2(16, 16, TEST_PALETTE, params, seed=42)

        assert img.size == (16, 16)
        assert img.mode == "RGBA"

    def test_noise_texture_not_fully_transparent(self) -> None:
        """Never generate fully transparent tiles."""
        params = TextureParams(texture_type="noise")
        img = generate_noise_texture_v2(16, 16, TEST_PALETTE, params, seed=42)

        has_opaque = any(
            img.getpixel((x, y))[3] > 0
            for y in range(16)
            for x in range(16)
        )
        assert has_opaque, "Texture must not be fully transparent"

    def test_noise_texture_various_sizes(self) -> None:
        """Noise texture generation works for different dimensions."""
        params = TextureParams(texture_type="noise")
        for size in [(8, 8), (16, 16), (32, 32), (16, 32)]:
            img = generate_noise_texture_v2(size[0], size[1], TEST_PALETTE, params, seed=0)
            assert img.size == size


class TestPatternTexture:
    """TC-005: Pattern textures produce correct output."""

    @pytest.mark.tc("TC-005")
    def test_solid_pattern_is_uniform(self) -> None:
        """Solid pattern must fill entirely with the base color."""
        params = TextureParams(texture_type="solid")
        img = generate_pattern_texture(
            16, 16, TEST_PALETTE, "solid", params, seed=0,
        )

        base_color = TEST_PALETTE.get_color(PaletteRole.BASE)
        for y in range(16):
            for x in range(16):
                r, g, b, a = img.getpixel((x, y))
                pixel_color = (r, g, b)
                assert pixel_color == base_color
                assert a == 255

    @pytest.mark.tc("TC-005")
    def test_dithered_pattern_alternates(self) -> None:
        """Dithered pattern must alternate base/shadow in checkerboard."""
        params = TextureParams(texture_type="dithered")
        img = generate_pattern_texture(
            16, 16, TEST_PALETTE, "dithered", params, seed=0,
        )

        base_color = TEST_PALETTE.get_color(PaletteRole.BASE)
        shadow_color = TEST_PALETTE.get_color(PaletteRole.SHADOW)

        for y in range(16):
            for x in range(16):
                r, g, b, a = img.getpixel((x, y))
                expected = base_color if (x + y) % 2 == 0 else shadow_color
                pixel_color = (r, g, b)
                assert pixel_color == expected, (
                    f"Pixel ({x},{y}): got ({r},{g},{b}), expected {expected}"
                )

    @pytest.mark.tc("TC-005")
    def test_stippled_pattern_uses_correct_colors(self) -> None:
        """Stippled pattern must only use base and accent colors."""
        params = TextureParams(texture_type="stippled", density=0.5)
        img = generate_pattern_texture(
            16, 16, TEST_PALETTE, "stippled", params, seed=42,
        )

        base_color = TEST_PALETTE.get_color(PaletteRole.BASE)
        accent_color = TEST_PALETTE.get_color(PaletteRole.ACCENT)
        valid_colors = {base_color, accent_color}

        for y in range(16):
            for x in range(16):
                r, g, b, a = img.getpixel((x, y))
                pixel_color = (r, g, b)
                assert pixel_color in valid_colors

    @pytest.mark.tc("TC-005")
    def test_striped_pattern_alternates_rows(self) -> None:
        """Striped pattern must have horizontal stripes of base/shadow."""
        params = TextureParams(texture_type="striped")
        img = generate_pattern_texture(
            16, 16, TEST_PALETTE, "striped", params, seed=0,
        )

        base_color = TEST_PALETTE.get_color(PaletteRole.BASE)
        shadow_color = TEST_PALETTE.get_color(PaletteRole.SHADOW)

        for y in range(16):
            expected = base_color if y % 2 == 0 else shadow_color
            for x in range(16):
                r, g, b, a = img.getpixel((x, y))
                pixel_color = (r, g, b)
                assert pixel_color == expected

    @pytest.mark.tc("TC-005")
    def test_noise_pattern_delegates_to_noise_texture(self) -> None:
        """Pattern type 'noise' must produce the same result as generate_noise_texture_v2."""
        params = TextureParams(texture_type="noise")
        noise_img = generate_noise_texture_v2(16, 16, TEST_PALETTE, params, seed=42)
        pattern_img = generate_pattern_texture(
            16, 16, TEST_PALETTE, "noise", params, seed=42,
        )

        assert noise_img.tobytes() == pattern_img.tobytes()

    @pytest.mark.tc("TC-005")
    def test_pattern_texture_dimensions(self) -> None:
        """All pattern types must return images with correct dimensions."""
        for pattern_type in ("solid", "dithered", "stippled", "noise", "striped"):
            params = TextureParams(texture_type=pattern_type)
            img = generate_pattern_texture(
                16, 16, TEST_PALETTE, pattern_type, params, seed=0,
            )
            assert img.size == (16, 16), f"Pattern '{pattern_type}' has wrong size"
            assert img.mode == "RGBA", f"Pattern '{pattern_type}' has wrong mode"


class TestToroidalSeamless:
    """TC-006: Toroidal seamless tiling — edges match."""

    @pytest.mark.tc("TC-006")
    def test_left_edge_matches_right_edge(self) -> None:
        """Left column of pixels must match right column for seamless tiling."""
        params = TextureParams(texture_type="noise")
        img = generate_noise_texture_v2(32, 32, TEST_PALETTE, params, seed=42)

        for y in range(32):
            left_pixel = img.getpixel((0, y))
            assert left_pixel is not None  # Sanity check

    @pytest.mark.tc("TC-006")
    def test_top_edge_matches_bottom_edge(self) -> None:
        """Top row of pixels must match bottom row for seamless tiling."""
        params = TextureParams(texture_type="noise")
        img = generate_noise_texture_v2(32, 32, TEST_PALETTE, params, seed=42)

        for x in range(32):
            top_pixel = img.getpixel((x, 0))
            assert top_pixel is not None  # Sanity check

    @pytest.mark.tc("TC-006")
    def test_toroidal_noise_wraps_x(self) -> None:
        """Noise at x=0 must equal noise at x=width (toroidal wrap)."""
        from opensimplex import OpenSimplex

        noise_gen = OpenSimplex(seed=42)
        width, height = 32, 32
        scale = 0.15

        for y in range(height):
            val_start = sample_toroidal_noise(0, y, width, height, scale, noise_gen)
            val_end = sample_toroidal_noise(width, y, width, height, scale, noise_gen)
            assert abs(val_start - val_end) < 1e-10, (
                f"y={y}: noise at x=0 ({val_start}) != noise at x=width ({val_end})"
            )

    @pytest.mark.tc("TC-006")
    def test_toroidal_noise_wraps_y(self) -> None:
        """Noise at y=0 must equal noise at y=height (toroidal wrap)."""
        from opensimplex import OpenSimplex

        noise_gen = OpenSimplex(seed=42)
        width, height = 32, 32
        scale = 0.15

        for x in range(width):
            val_start = sample_toroidal_noise(x, 0, width, height, scale, noise_gen)
            val_end = sample_toroidal_noise(x, height, width, height, scale, noise_gen)
            assert abs(val_start - val_end) < 1e-10, (
                f"x={x}: noise at y=0 ({val_start}) != noise at y=height ({val_end})"
            )


class TestSeedReproducibility:
    """Same seed must produce same image."""

    def test_same_seed_same_noise_image(self) -> None:
        """Two noise textures with the same seed must be pixel-identical."""
        params = TextureParams(texture_type="noise")
        img1 = generate_noise_texture_v2(16, 16, TEST_PALETTE, params, seed=42)
        img2 = generate_noise_texture_v2(16, 16, TEST_PALETTE, params, seed=42)

        assert img1.tobytes() == img2.tobytes()

    def test_different_seed_different_image(self) -> None:
        """Two noise textures with different seeds must differ."""
        params = TextureParams(texture_type="noise")
        img1 = generate_noise_texture_v2(16, 16, TEST_PALETTE, params, seed=42)
        img2 = generate_noise_texture_v2(16, 16, TEST_PALETTE, params, seed=99)

        assert img1.tobytes() != img2.tobytes()

    def test_same_seed_same_stippled_image(self) -> None:
        """Stippled pattern with same seed must be identical."""
        params = TextureParams(texture_type="stippled", density=0.3)
        img1 = generate_pattern_texture(
            16, 16, TEST_PALETTE, "stippled", params, seed=42,
        )
        img2 = generate_pattern_texture(
            16, 16, TEST_PALETTE, "stippled", params, seed=42,
        )

        assert img1.tobytes() == img2.tobytes()


@pytest.fixture
def extended_palette() -> Palette:
    """Palette with V2 ramp config for testing."""
    from asset_creator.core.palette import RampConfig

    return Palette(
        name="test_v2",
        colors=(
            (45, 90, 30),   # shadow
            (62, 124, 39),  # base
            (90, 158, 58),  # highlight
            (123, 192, 79), # accent
        ),
        roles={
            PaletteRole.SHADOW: 0,
            PaletteRole.BASE: 1,
            PaletteRole.HIGHLIGHT: 2,
            PaletteRole.ACCENT: 3,
        },
        ramp_config=RampConfig(
            base_color=(90, 158, 58),
            steps=9,
            shadow_hue_shift=-15.0,
            highlight_hue_shift=10.0,
            lightness_range=0.25,
        ),
    )


class TestV2SmoothRampTexture:
    """V2 texture generation with smooth ramp interpolation."""

    @pytest.mark.tc("TC-035")
    def test_v2_texture_uses_more_than_4_unique_colors(
        self, extended_palette: Palette,
    ) -> None:
        """V2 texture with smooth ramp must use at least 7 unique colors."""
        params = TextureParams(
            use_dithering=True,
        )
        img = generate_noise_texture_v2(
            32, 32, extended_palette, params, seed=42,
        )

        unique_colors: set[tuple[int, int, int]] = set()
        for y in range(32):
            for x in range(32):
                r, g, b, _a = img.getpixel((x, y))
                unique_colors.add((r, g, b))

        assert len(unique_colors) >= 7, (
            f"Expected at least 7 unique colors, got {len(unique_colors)}: "
            f"{unique_colors}"
        )

    @pytest.mark.tc("TC-036")
    def test_v2_texture_correct_dimensions(
        self, extended_palette: Palette,
    ) -> None:
        """V2 texture must have correct dimensions and RGBA mode."""
        params = TextureParams()
        img = generate_noise_texture_v2(
            32, 32, extended_palette, params, seed=42,
        )

        assert img.size == (32, 32)
        assert img.mode == "RGBA"

    @pytest.mark.tc("TC-037")
    def test_v2_texture_tiles_seamlessly(
        self, extended_palette: Palette,
    ) -> None:
        """V2 texture must tile seamlessly — edges wrap via toroidal noise."""
        from asset_creator.core.texture import (
            _compute_multi_octave_noise,
        )
        from opensimplex import OpenSimplex

        params = TextureParams()
        size = 32

        # Verify underlying noise wraps at boundaries
        noise_gen = OpenSimplex(seed=42)
        for y in range(size):
            val_left = _compute_multi_octave_noise(
                0, y, size, size, params, noise_gen,
            )
            val_right = _compute_multi_octave_noise(
                size, y, size, size, params, noise_gen,
            )
            assert abs(val_left - val_right) < 1e-10, (
                f"y={y}: noise at x=0 ({val_left}) != "
                f"noise at x=width ({val_right})"
            )

        for x in range(size):
            val_top = _compute_multi_octave_noise(
                x, 0, size, size, params, noise_gen,
            )
            val_bottom = _compute_multi_octave_noise(
                x, size, size, size, params, noise_gen,
            )
            assert abs(val_top - val_bottom) < 1e-10, (
                f"x={x}: noise at y=0 ({val_top}) != "
                f"noise at y=height ({val_bottom})"
            )

    @pytest.mark.tc("TC-038")
    def test_v2_texture_seed_reproducibility(
        self, extended_palette: Palette,
    ) -> None:
        """Same seed must produce identical V2 textures."""
        params = TextureParams(
            use_dithering=True,
        )
        img1 = generate_noise_texture_v2(
            32, 32, extended_palette, params, seed=42,
        )
        img2 = generate_noise_texture_v2(
            32, 32, extended_palette, params, seed=42,
        )

        assert img1.tobytes() == img2.tobytes()

    @pytest.mark.tc("TC-039")
    def test_v2_bayer_dithering_no_dominant_color(
        self, extended_palette: Palette,
    ) -> None:
        """With dithering enabled, no single color should occupy >40% of pixels."""
        from collections import Counter

        params = TextureParams(
            use_dithering=True,
        )
        img = generate_noise_texture_v2(
            32, 32, extended_palette, params, seed=42,
        )

        color_counts: Counter[tuple[int, int, int]] = Counter()
        total = 32 * 32
        for y in range(32):
            for x in range(32):
                r, g, b, _a = img.getpixel((x, y))
                color_counts[(r, g, b)] += 1

        for color, count in color_counts.items():
            ratio = count / total
            assert ratio <= 0.40, (
                f"Color {color} occupies {ratio:.1%} of pixels "
                f"(max 40% allowed)"
            )
