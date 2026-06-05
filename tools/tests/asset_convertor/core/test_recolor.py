"""
Unit & integration tests for the Recolor Engine and Lospec Palette Bundle.

Spec: tools/docs/specs/asset_convertor_mv_recolor.md

TDD: Tests written RED — modules do not exist yet.
IDs: TC-001 … TC-025 (unit), IT-001 … IT-003 (integration)
"""

from __future__ import annotations

import pytest
from PIL import Image

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _solid_rgba(color: tuple, size: int = 10) -> Image.Image:
    """Create a solid RGBA image of given color."""
    return Image.new("RGBA", (size, size), color)


def _two_color(c1: tuple, c2: tuple, size: int = 10) -> Image.Image:
    """Create an image with c1 in the left half and c2 in the right half."""
    img = Image.new("RGBA", (size * 2, size))
    for y in range(size):
        for x in range(size):
            img.putpixel((x, y), c1)
        for x in range(size, size * 2):
            img.putpixel((x, y), c2)
    return img


# ===========================================================================
# extract_palette — UNIT TESTS
# ===========================================================================

class TestExtractPalette:

    def setup_method(self) -> None:
        from asset_convertor.core.recolor import extract_palette
        self.extract = extract_palette

    # TC-001: Single-color image returns list with one color
    def test_single_color(self) -> None:
        img = _solid_rgba((255, 0, 0, 255))
        palette = self.extract(img)
        assert palette == [(255, 0, 0, 255)]

    # TC-002: Two-color image returns both colors
    def test_two_colors(self) -> None:
        img = _two_color((255, 0, 0, 255), (0, 0, 255, 255))
        palette = self.extract(img)
        assert len(palette) == 2
        assert (255, 0, 0, 255) in palette
        assert (0, 0, 255, 255) in palette

    # TC-003: Fully transparent pixels excluded
    def test_transparent_excluded(self) -> None:
        img = Image.new("RGBA", (10, 10), (255, 0, 0, 0))  # all alpha=0
        with pytest.raises(ValueError, match="aucun pixel non-transparent"):
            self.extract(img)

    # TC-004: Near-transparent pixels excluded by threshold
    def test_near_transparent_excluded_by_threshold(self) -> None:
        img = Image.new("RGBA", (10, 10))
        # 3 red pixels (opaque) + rest with alpha=5 (below default threshold=10)
        for x in range(3):
            img.putpixel((x, 0), (255, 0, 0, 255))
        for x in range(3, 10):
            img.putpixel((x, 0), (0, 255, 0, 5))
        palette = self.extract(img, alpha_threshold=10)
        assert (255, 0, 0, 255) in palette
        # The semi-transparent green should not appear
        assert all(c[3] >= 10 for c in palette)

    # TC-005: max_colors respected
    def test_max_colors_respected(self) -> None:
        # Create image with 20 unique colors (each row is a different color)
        img = Image.new("RGBA", (20, 1))
        for i in range(20):
            img.putpixel((i, 0), (i * 10, 0, 0, 255))
        palette = self.extract(img, max_colors=5)
        assert len(palette) <= 5

    # TC-006: Most frequent color is first in result
    def test_most_frequent_first(self) -> None:
        # 100 red pixels, 10 blue pixels
        img = Image.new("RGBA", (110, 1))
        for x in range(100):
            img.putpixel((x, 0), (255, 0, 0, 255))
        for x in range(100, 110):
            img.putpixel((x, 0), (0, 0, 255, 255))
        palette = self.extract(img)
        assert palette[0] == (255, 0, 0, 255)

    # TC-007: All-transparent image raises ValueError
    def test_all_transparent_raises(self) -> None:
        img = Image.new("RGBA", (10, 10), (0, 0, 0, 0))
        with pytest.raises(ValueError, match="aucun pixel non-transparent"):
            self.extract(img)

    # TC-008: RGB input is converted to RGBA internally (returns 4-tuples)
    def test_rgb_input_returns_rgba_tuples(self) -> None:
        img = Image.new("RGB", (10, 10), (100, 150, 200))
        palette = self.extract(img)
        assert all(len(c) == 4 for c in palette)


# ===========================================================================
# propose_remap — UNIT TESTS
# ===========================================================================

class TestProposeRemap:

    def setup_method(self) -> None:
        from asset_convertor.core.recolor import propose_remap
        self.propose = propose_remap

    # TC-009: Exact match maps to itself
    def test_exact_match(self) -> None:
        source = [(255, 0, 0, 255)]
        target = [(255, 0, 0, 255), (0, 255, 0, 255)]
        remap = self.propose(source, target)
        assert remap[(255, 0, 0, 255)] == (255, 0, 0, 255)

    # TC-010: Nearest by ΔE — pure red maps to orange not pink when both present
    def test_nearest_perceptual(self) -> None:
        source = [(255, 0, 0, 255)]
        # Orange (perceptually close to red) vs cold purple (far from red)
        target = [(255, 165, 0, 255), (75, 0, 130, 255)]
        remap = self.propose(source, target)
        # Red should map to orange (not purple) — orange is closer in Lab space
        assert remap[(255, 0, 0, 255)] == (255, 165, 0, 255)

    # TC-011: All source colors present in output
    def test_all_source_colors_in_output(self) -> None:
        source = [(255, 0, 0, 255), (0, 255, 0, 255), (0, 0, 255, 255),
                  (255, 255, 0, 255), (0, 255, 255, 255)]
        target = [(128, 0, 0, 255), (0, 128, 0, 255), (0, 0, 128, 255)]
        remap = self.propose(source, target)
        assert len(remap) == len(source)

    # TC-012: Many-to-one mapping is valid (no error)
    def test_many_to_one_valid(self) -> None:
        # Two very similar source colors should both map to the same target
        source = [(255, 0, 0, 255), (254, 0, 0, 255)]
        target = [(255, 0, 0, 255)]
        remap = self.propose(source, target)
        # Both map to the same target — no error
        assert remap[(255, 0, 0, 255)] == (255, 0, 0, 255)
        assert remap[(254, 0, 0, 255)] == (255, 0, 0, 255)


# ===========================================================================
# apply_remap — UNIT TESTS
# ===========================================================================

class TestApplyRemap:

    def setup_method(self) -> None:
        from asset_convertor.core.recolor import apply_remap
        self.apply = apply_remap

    # TC-013: Single color remapped correctly
    def test_single_color_remapped(self) -> None:
        img = _solid_rgba((255, 0, 0, 255))
        remap = {(255, 0, 0, 255): (0, 0, 255, 255)}
        result = self.apply(img, remap)
        px = result.getpixel((0, 0))
        assert px[:3] == (0, 0, 255)

    # TC-014: Alpha preserved after remap (original alpha kept, not remap target alpha)
    def test_alpha_preserved(self) -> None:
        img = Image.new("RGBA", (1, 1), (255, 0, 0, 128))
        remap = {(255, 0, 0, 128): (0, 0, 255, 255)}
        result = self.apply(img, remap)
        px = result.getpixel((0, 0))
        # Color changed to blue, but original alpha (128) is preserved
        assert px[3] == 128

    # TC-015: Color not in remap table left unchanged
    def test_unmapped_color_unchanged(self) -> None:
        img = _two_color((255, 0, 0, 255), (0, 255, 0, 255))
        remap = {(255, 0, 0, 255): (0, 0, 255, 255)}  # only red is remapped
        result = self.apply(img, remap)
        # Green pixels should be unchanged
        green_px = result.getpixel((10, 0))
        assert green_px == (0, 255, 0, 255)

    # TC-016: Transparent pixels not remapped (alpha < threshold)
    def test_transparent_pixels_not_remapped(self) -> None:
        img = Image.new("RGBA", (2, 1))
        img.putpixel((0, 0), (255, 0, 0, 5))   # near-transparent red
        img.putpixel((1, 0), (255, 0, 0, 255))  # opaque red
        remap = {(255, 0, 0, 5): (0, 255, 0, 255), (255, 0, 0, 255): (0, 255, 0, 255)}
        result = self.apply(img, remap, alpha_threshold=10)
        # Near-transparent pixel (alpha=5 < 10) should be preserved unchanged
        assert result.getpixel((0, 0)) == (255, 0, 0, 5)
        # Opaque pixel should be remapped
        assert result.getpixel((1, 0))[:3] == (0, 255, 0)

    # TC-017: Input not mutated
    def test_input_not_mutated(self) -> None:
        img = _solid_rgba((255, 0, 0, 255))
        original = img.tobytes()
        remap = {(255, 0, 0, 255): (0, 0, 255, 255)}
        self.apply(img, remap)
        assert img.tobytes() == original

    # TC-018: Output mode is RGBA
    def test_output_mode_rgba(self) -> None:
        img = Image.new("RGB", (10, 10), (255, 0, 0))
        result = self.apply(img, {})
        assert result.mode == "RGBA"

    # TC-019: Output dimensions match input
    def test_output_dimensions_match(self) -> None:
        img = _make_rgba_dim(192, 96)
        result = self.apply(img, {})
        assert result.size == (192, 96)

    def test_large_image_performance(self) -> None:
        """IT test: 768x720 image processes in <5 seconds with PIL PixelAccess."""
        import time
        img = Image.new("RGBA", (768, 720), (200, 100, 50, 255))
        remap = {(200, 100, 50, 255): (50, 100, 200, 255)}
        start = time.time()
        from asset_convertor.core.recolor import apply_remap
        result = apply_remap(img, remap)
        elapsed = time.time() - start
        assert elapsed < 5.0  # Must complete in <5 seconds
        assert result.getpixel((0, 0))[:3] == (50, 100, 200)


def _make_rgba_dim(w: int, h: int) -> Image.Image:
    return Image.new("RGBA", (w, h), (0, 128, 0, 255))


# ===========================================================================
# palettes.py — UNIT TESTS
# ===========================================================================

class TestPalettes:

    def setup_method(self) -> None:
        from asset_convertor.core.palettes import get_palette, get_palette_names
        self.names = get_palette_names
        self.get = get_palette

    # TC-020: All 6 palettes accessible
    def test_six_palettes_available(self) -> None:
        names = self.names()
        assert len(names) == 6

    # TC-021: Endesga 32 has 32 colors
    def test_endesga_32_count(self) -> None:
        palette = self.get("Endesga 32")
        assert len(palette) == 32

    # TC-022: GameBoy has 4 colors
    def test_gameboy_count(self) -> None:
        palette = self.get("GameBoy")
        assert len(palette) == 4

    # TC-023: Unknown palette raises KeyError
    def test_unknown_raises(self) -> None:
        with pytest.raises(KeyError):
            self.get("Nonexistent Palette XYZ")

    # TC-024: Returned palette is a copy (mutation doesn't affect source)
    def test_returned_palette_is_copy(self) -> None:
        from asset_convertor.core import palettes as _palettes_mod
        names = self.names()
        palette = self.get(names[0])
        original_len = len(palette)
        palette.append((0, 0, 0, 255))  # mutate the copy
        # The original should be unchanged
        palette_fresh = self.get(names[0])
        assert len(palette_fresh) == original_len

    # TC-025: All colors are 4-tuples (RGBA)
    def test_all_colors_are_rgba_tuples(self) -> None:
        for name in self.names():
            palette = self.get(name)
            for color in palette:
                assert len(color) == 4, f"Color {color} in '{name}' is not a 4-tuple"
                assert all(0 <= v <= 255 for v in color), f"Out of range: {color}"


# ===========================================================================
# INTEGRATION TESTS — Recolor pipeline
# ===========================================================================

class TestRecolorIntegration:

    # IT-001: Full pipeline — extract → propose → apply
    def test_full_pipeline(self) -> None:
        from asset_convertor.core.palettes import get_palette
        from asset_convertor.core.recolor import apply_remap, extract_palette, propose_remap

        # Create a simple pixel-art style image
        img = Image.new("RGBA", (10, 10))
        colors = [(200, 100, 50, 255), (150, 80, 30, 255), (100, 60, 20, 255)]
        for i, c in enumerate(colors):
            for x in range(i * 3, (i + 1) * 3):
                for y in range(10):
                    if x < 10:
                        img.putpixel((x, y), c)

        palette = extract_palette(img)
        target = get_palette("Endesga 32")
        remap = propose_remap(palette, target)
        result = apply_remap(img, remap)

        assert isinstance(result, Image.Image)
        assert result.size == img.size

    # IT-002: Recolor preserves transparency mask
    def test_recolor_preserves_transparency(self) -> None:
        from asset_convertor.core.recolor import apply_remap

        img = Image.new("RGBA", (10, 10), (255, 0, 0, 255))
        # Set a transparent region
        for x in range(5):
            for y in range(5):
                img.putpixel((x, y), (0, 0, 0, 0))

        remap = {(255, 0, 0, 255): (0, 0, 255, 255)}
        result = apply_remap(img, remap)

        # Transparent region stays transparent
        for x in range(5):
            for y in range(5):
                assert result.getpixel((x, y))[3] == 0

    # IT-003: Proposed remap + manual override applied correctly
    def test_manual_override_applied(self) -> None:
        from asset_convertor.core.palettes import get_palette
        from asset_convertor.core.recolor import apply_remap, extract_palette, propose_remap

        img = _solid_rgba((200, 100, 50, 255))
        palette = extract_palette(img)
        target = get_palette("Endesga 32")
        remap = propose_remap(palette, target)

        # Manually override the mapping
        source_color = palette[0]
        manual_target = (99, 88, 77, 255)
        remap[source_color] = manual_target

        result = apply_remap(img, remap)
        assert result.getpixel((0, 0))[:3] == (99, 88, 77)
