"""Tests for the detail overlay system (TC-041 to TC-045)."""

from __future__ import annotations

import pytest
from asset_creator.core.palette import Palette, PaletteRole
from PIL import Image

try:
    from asset_creator.core.palette import RampConfig

    HAS_V2_PALETTE = True
except ImportError:
    HAS_V2_PALETTE = False

pytestmark = pytest.mark.skipif(not HAS_V2_PALETTE, reason="V2 detail overlay not implemented yet")


@pytest.fixture
def extended_palette() -> Palette:
    """Palette with V2 ramp config for testing."""
    from asset_creator.core.palette import RampConfig

    return Palette(
        name="test_v2",
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
            base_color=(90, 158, 58),
            steps=9,
            shadow_hue_shift=-15.0,
            highlight_hue_shift=10.0,
            lightness_range=0.25,
        ),
    )


@pytest.fixture
def base_image() -> Image.Image:
    """A 32x32 solid green RGBA image for overlay testing."""
    return Image.new("RGBA", (32, 32), (62, 124, 39, 255))


class TestGrassBladeOverlay:
    """TC-041: Grass blade overlay modifies pixels."""

    @pytest.mark.tc("TC-041")
    def test_grass_blades_modify_pixels(
        self,
        base_image: Image.Image,
        extended_palette: Palette,
    ) -> None:
        """Grass blade overlay must modify at least some pixels."""
        from asset_creator.core.detail_overlay import apply_detail_overlay

        result = apply_detail_overlay(
            img=base_image,
            palette=extended_palette,
            detail_type="grass_blades",
            density=0.12,
            seed=42,
        )

        assert result.tobytes() != base_image.tobytes(), (
            "Grass blade overlay did not modify any pixels"
        )


class TestOverlayDimensions:
    """TC-042: Overlay preserves image dimensions."""

    @pytest.mark.tc("TC-042")
    def test_overlay_preserves_dimensions(
        self,
        base_image: Image.Image,
        extended_palette: Palette,
    ) -> None:
        """Output image must have the same size as input."""
        from asset_creator.core.detail_overlay import apply_detail_overlay

        for detail_type in ("grass_blades", "dirt_specks", "stone_cracks", "sand_grains", "none"):
            result = apply_detail_overlay(
                img=base_image,
                palette=extended_palette,
                detail_type=detail_type,
                density=0.10,
                seed=42,
            )
            assert result.size == base_image.size, (
                f"Overlay '{detail_type}' changed dimensions from "
                f"{base_image.size} to {result.size}"
            )
            assert result.mode == base_image.mode, (
                f"Overlay '{detail_type}' changed mode from {base_image.mode} to {result.mode}"
            )


class TestOverlaySeedReproducibility:
    """TC-043: Overlay is seed-reproducible."""

    @pytest.mark.tc("TC-043")
    def test_same_seed_produces_identical_overlay(
        self,
        base_image: Image.Image,
        extended_palette: Palette,
    ) -> None:
        """Same seed must produce pixel-identical overlay result."""
        from asset_creator.core.detail_overlay import apply_detail_overlay

        for detail_type in ("grass_blades", "dirt_specks", "stone_cracks", "sand_grains"):
            result1 = apply_detail_overlay(
                img=base_image,
                palette=extended_palette,
                detail_type=detail_type,
                density=0.10,
                seed=42,
            )
            result2 = apply_detail_overlay(
                img=base_image,
                palette=extended_palette,
                detail_type=detail_type,
                density=0.10,
                seed=42,
            )
            assert result1.tobytes() == result2.tobytes(), (
                f"Overlay '{detail_type}' produced different results with same seed"
            )


class TestNoneOverlay:
    """TC-044: detail_type='none' returns image unchanged."""

    @pytest.mark.tc("TC-044")
    def test_none_returns_unchanged_copy(
        self,
        base_image: Image.Image,
        extended_palette: Palette,
    ) -> None:
        """'none' overlay must return a pixel-identical copy."""
        from asset_creator.core.detail_overlay import apply_detail_overlay

        result = apply_detail_overlay(
            img=base_image,
            palette=extended_palette,
            detail_type="none",
            density=0.10,
            seed=42,
        )

        assert result.tobytes() == base_image.tobytes(), "'none' overlay modified pixels"
        # Must be a copy, not the same object
        assert result is not base_image, "'none' overlay must return a copy, not the original"


class TestBladeColorsFromRamp:
    """TC-045: Blade pixels use colors from palette's extended_colors ramp."""

    @pytest.mark.tc("TC-045")
    def test_blade_pixels_use_extended_ramp_colors(
        self,
        extended_palette: Palette,
    ) -> None:
        """Grass blade colors must come from the top 3 extended ramp colors."""
        from asset_creator.core.detail_overlay import apply_detail_overlay

        # Use a distinctive background to identify blade pixels
        bg_color = (0, 0, 0, 255)
        img = Image.new("RGBA", (32, 32), bg_color)

        result = apply_detail_overlay(
            img=img,
            palette=extended_palette,
            detail_type="grass_blades",
            density=0.20,
            seed=42,
        )

        extended_colors = extended_palette.extended_colors
        # Top 3 colors are used for blades
        blade_palette = set(extended_colors[-3:])

        modified_pixels: list[tuple[int, int, int]] = []
        for y in range(32):
            for x in range(32):
                r, g, b, a = result.getpixel((x, y))
                if (r, g, b, a) != bg_color:
                    modified_pixels.append((r, g, b))

        assert len(modified_pixels) > 0, "No blade pixels were drawn"

        for pixel_color in modified_pixels:
            assert pixel_color in blade_palette, (
                f"Blade pixel color {pixel_color} not in top 3 ramp colors {blade_palette}"
            )


class TestOverlayInvalidType:
    """Edge case: unknown detail_type raises ValueError."""

    def test_unknown_detail_type_raises(
        self,
        base_image: Image.Image,
        extended_palette: Palette,
    ) -> None:
        """Unknown overlay type must raise ValueError."""
        from asset_creator.core.detail_overlay import apply_detail_overlay

        with pytest.raises(ValueError, match="Unknown detail type"):
            apply_detail_overlay(
                img=base_image,
                palette=extended_palette,
                detail_type="lava_bubbles",
                density=0.10,
                seed=42,
            )


class TestOverlayImmutability:
    """Overlay must not mutate the input image."""

    def test_input_image_not_mutated(
        self,
        base_image: Image.Image,
        extended_palette: Palette,
    ) -> None:
        """Original image must remain unchanged after overlay."""
        from asset_creator.core.detail_overlay import apply_detail_overlay

        original_bytes = base_image.tobytes()

        apply_detail_overlay(
            img=base_image,
            palette=extended_palette,
            detail_type="grass_blades",
            density=0.15,
            seed=42,
        )

        assert base_image.tobytes() == original_bytes, (
            "apply_detail_overlay mutated the input image"
        )
