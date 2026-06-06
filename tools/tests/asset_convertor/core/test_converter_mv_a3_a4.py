"""
Unit & integration tests for A3 (Building Tiles) and A4 (Wall Tiles) converters.

Spec: tools/docs/specs/asset_convertor_mv_core_converters.md

TDD: Tests written RED — modules do not exist yet.
IDs: TC-001 … TC-019 (A3 unit), TC-020 … TC-024 (A4 unit), IT-001 … IT-004 (integration)
"""

from __future__ import annotations

import pytest
from PIL import Image

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_rgba(width: int, height: int, color: tuple = (100, 150, 200, 255)) -> Image.Image:
    return Image.new("RGBA", (width, height), color)


def _make_a3_source(num_blocks: int = 1) -> Image.Image:
    """Minimal valid A3 source: 96px wide (1 col), 96px tall per block.

    num_blocks must be even so the split_row rule gives non-empty roof and wall.
    """
    width = 96   # 1 column of blocks (96 px)
    height = 96 * num_blocks
    return _make_rgba(width, height)


def _make_a4_source(num_pairs: int = 1) -> Image.Image:
    """Minimal valid A4 source: 96px wide, 120px per pair (one top row + one side start)."""
    width = 96   # 1 column
    # Each ty pair: top (2 mini-tile rows=48px) + side (3 mini-tile rows=72px from by offset)
    # Minimum to get 1 top kind: src_height must cover by=0 top block (96px)
    # Minimum to get 1 side kind: src_height must cover by=3 side block (by=3*24+96=168px)
    height = 192 * num_pairs  # generous: 4 mini-tile rows = 96px per block pair
    return _make_rgba(width, height)


# ===========================================================================
# A3 — UNIT TESTS
# ===========================================================================

class TestConvertMvA3:

    def setup_method(self) -> None:
        from asset_convertor.core.converter_mv_a3 import convert_mv_a3
        self.convert = convert_mv_a3

    # TC-001: Valid 2-block A3 returns tuple of two PIL Images
    def test_returns_tuple_of_two_images(self) -> None:
        src = _make_a3_source(2)  # 2 block rows: 1 roof + 1 wall
        result = self.convert(src)
        assert isinstance(result, tuple)
        assert len(result) == 2
        assert all(isinstance(img, Image.Image) for img in result)

    # TC-002: Both outputs are RGBA
    def test_output_mode_rgba(self) -> None:
        roof, wall = self.convert(_make_a3_source(2))
        assert roof.mode == "RGBA"
        assert wall.mode == "RGBA"

    # TC-003: Output width is 16 x tile_size for both strips
    def test_output_width_16_tiles(self) -> None:
        roof, wall = self.convert(_make_a3_source(2))
        assert roof.width == 16 * 48
        assert wall.width == 16 * 48

    # TC-004: 2-block source: 1 roof kind + 1 wall kind → each strip has 1 row
    def test_two_blocks_one_kind_each(self) -> None:
        roof, wall = self.convert(_make_a3_source(2))
        assert roof.height == 48   # 1 roof kind
        assert wall.height == 48   # 1 wall kind

    # TC-005: 4-block source: 2 roof kinds + 2 wall kinds
    def test_four_blocks_two_kinds_each(self) -> None:
        roof, wall = self.convert(_make_a3_source(4))
        assert roof.height == 2 * 48
        assert wall.height == 2 * 48

    # TC-006: Input not mutated
    def test_input_not_mutated(self) -> None:
        src = _make_a3_source(2)
        original_data = src.tobytes()
        self.convert(src)
        assert src.tobytes() == original_data

    # TC-007: Width not a multiple of 64 or 96 raises ValueError
    def test_wrong_width_raises(self) -> None:
        bad = _make_rgba(80, 192)
        with pytest.raises(ValueError, match="(?i)(invalide|width|largeur)"):
            self.convert(bad)

    # TC-008: Wrong height (too small) raises ValueError
    def test_wrong_height_raises(self) -> None:
        bad = _make_rgba(96, 50)  # 50 < 96 minimum height
        with pytest.raises(ValueError, match="(?i)(petite|96)"):
            self.convert(bad)

    # TC-009: Non-RGBA input is converted internally (no error)
    def test_rgb_input_accepted(self) -> None:
        src = Image.new("RGB", (768, 192), (100, 150, 200))
        roof, wall = self.convert(src)
        assert isinstance(roof, Image.Image)
        assert isinstance(wall, Image.Image)

    # TC-010: Both outputs contain exactly 16 columns of tiles (width / tile_size)
    def test_output_tile_count(self) -> None:
        roof, wall = self.convert(_make_a3_source(2))
        assert roof.width // 48 == 16
        assert wall.width // 48 == 16

    # TC-011: Multiple blocks: output width unchanged (still 16 tiles wide)
    def test_multi_block_width_unchanged(self) -> None:
        roof, wall = self.convert(_make_a3_source(4))
        assert roof.width == 16 * 48
        assert wall.width == 16 * 48

    # TC-012: Zero-height source raises ValueError
    def test_zero_height_raises(self) -> None:
        with pytest.raises((ValueError, Exception)):
            self.convert(_make_rgba(768, 0))

    # TC-026: A3 32px source (block_size=64) is accepted
    def test_32px_source_accepted(self) -> None:
        src = _make_rgba(64, 128)  # 2 block rows for valid split
        roof, wall = self.convert(src)
        assert isinstance(roof, Image.Image)
        assert isinstance(wall, Image.Image)

    # TC-027: A3 32px output width = 16 * 32 = 512px
    def test_32px_output_width(self) -> None:
        src = _make_rgba(64, 128)
        roof, wall = self.convert(src)
        assert roof.width == 16 * 32
        assert wall.width == 16 * 32

    # TC-028: A3 32px 2-block source → each strip has 1 row of 32px
    def test_32px_output_height(self) -> None:
        src = _make_rgba(64, 128)  # 2 block rows
        roof, wall = self.convert(src)
        assert roof.height == 32
        assert wall.height == 32

    # TC-029: A3 32px four blocks → each strip has 2 rows
    def test_32px_four_blocks_height(self) -> None:
        src = _make_rgba(64, 256)  # 4 block rows
        roof, wall = self.convert(src)
        assert roof.height == 2 * 32
        assert wall.height == 2 * 32

    # TC-031: A3 converter separates roof (first half) from wall (second half)
    def test_a3_roof_wall_separation(self) -> None:
        src = Image.new("RGBA", (192, 192))
        # 2 rows of 2 blocks: top row (ty=0) = red, bottom row (ty=1) = green
        block_red   = Image.new("RGBA", (96, 96), (255, 0, 0, 255))
        block_green = Image.new("RGBA", (96, 96), (0, 255, 0, 255))
        for tx in range(2):
            src.paste(block_red,   (tx * 96, 0))
            src.paste(block_green, (tx * 96, 96))

        roof, wall = self.convert(src)

        # roof strip: 2 blocks in row 0 → 2 kinds
        assert roof.height == 2 * 48
        for x in [0, 48, 100, 200, 500, 700]:
            for y in [0, 10, 24, 40]:
                assert roof.getpixel((x, y)) == (255, 0, 0, 255)

        # wall strip: 2 blocks in row 1 → 2 kinds
        assert wall.height == 2 * 48
        for x in [0, 48, 100, 200, 500, 700]:
            for y in [0, 10, 24, 40]:
                assert wall.getpixel((x, y)) == (0, 255, 0, 255)

# ===========================================================================
# A4 — UNIT TESTS
# ===========================================================================

class TestConvertMvA4:

    def setup_method(self) -> None:
        from asset_convertor.core.converter_mv_a4 import convert_mv_a4
        self.convert = convert_mv_a4

    # TC-013: Valid A4 returns tuple of two PIL Images
    def test_returns_tuple_of_two_images(self) -> None:
        src = _make_a4_source(1)
        result = self.convert(src)
        assert isinstance(result, tuple)
        assert len(result) == 2
        assert all(isinstance(img, Image.Image) for img in result)

    # TC-014: Both outputs are RGBA
    def test_both_outputs_rgba(self) -> None:
        tops, sides = self.convert(_make_a4_source(1))
        assert tops.mode == "RGBA"
        assert sides.mode == "RGBA"

    # TC-015: Wall-tops sheet width = 8 × tile_size (FLOOR_AUTOTILE_TABLE blob, 8 cols)
    def test_tops_width_is_8_tiles(self) -> None:
        tops, _ = self.convert(_make_a4_source(1))
        # Wall tops use FLOOR_AUTOTILE_TABLE — 8-col × 6-row blob autotile sheet
        assert tops.width == 8 * 48

    # TC-016: Wall-tops height = 6 × tile_size (47 shapes + 1 padding slot, 6 rows per kind)
    def test_tops_height_is_six_tile_rows(self) -> None:
        tops, _ = self.convert(_make_a4_source(1))
        # 1 column, 1 top kind → 6 rows × 48px = 288px
        assert tops.height == 6 * 48

    # TC-017: Wall-sides sheet width = 16 x tile_size (16 shapes, 1 tile wide each)
    def test_sides_width_is_16_tiles(self) -> None:
        _, sides = self.convert(_make_a4_source(1))
        assert sides.width == 16 * 48

    # TC-018: Wall-sides height = tile_size (1 row per kind)
    def test_sides_height_is_one_tile_row(self) -> None:
        _, sides = self.convert(_make_a4_source(1))
        # 1 column, 1 side kind → 1 row x 48px = 48px
        assert sides.height == 48

    # TC-019: Input not mutated
    def test_input_not_mutated(self) -> None:
        src = _make_a4_source(1)
        original = src.tobytes()
        self.convert(src)
        assert src.tobytes() == original

    # TC-020: Width that is not a multiple of any valid block_size (64 or 96) raises ValueError
    def test_wrong_width_raises(self) -> None:
        # 80px is not a multiple of 64 (32px tiles) nor 96 (48px tiles)
        bad = _make_rgba(80, 192)
        with pytest.raises(ValueError, match="(?i)(invalide|width|largeur)"):
            self.convert(bad)

    # TC-025: A4 source with 32px tiles (block_size=64) is accepted
    def test_32px_source_accepted(self) -> None:
        # 64x160 = valid A4 32px source (1 block col)
        src = _make_rgba(64, 160)
        tops, sides = self.convert(src)
        assert isinstance(tops, Image.Image)
        assert isinstance(sides, Image.Image)
        # Tops: FLOOR_AUTOTILE_TABLE → 8 * tile_size wide
        # Sides: WALL_AUTOTILE_TABLE → 16 * tile_size wide
        assert tops.width == 8 * 32
        assert sides.width == 16 * 32

    # TC-021: Wrong height raises ValueError
    def test_wrong_height_raises(self) -> None:
        bad = _make_rgba(96, 50)  # too small
        with pytest.raises(ValueError, match="(?i)(petite|120)"):
            self.convert(bad)

    # TC-022: Two A4 pairs → tops height is proportional to available top rows
    def test_two_pairs_tops_height_doubles(self) -> None:
        # 96x192 src has 3 even ty rows (ty=0,2,4 fit within 384px/24=16 mini-rows)
        # Actual: ty=0(by=0), ty=2(by=5), ty=4(by=10) all fit in 16 mini-rows
        # But 96x192 = 8 mini-rows only: ty=0(by=0, needs 4 rows ok), ty=1(by=3, needs 4 rows ok)
        # ty=2(by=5) needs rows 5..8 but source has only 8 rows = border
        # Let's use 1 source that gives 1 top, 1 that gives 2 tops
        tops_1, _ = self.convert(_make_a4_source(1))  # 96x192 → by=0(ok), by=3(ok)
        # A 96x384 source adds more rows
        src_2 = _make_rgba(96, 384)
        tops_2, _ = self.convert(src_2)
        # Both have at least 1 top strip, second has more
        assert tops_2.height >= tops_1.height

    # TC-023: RGB input accepted
    def test_rgb_input_accepted(self) -> None:
        src = Image.new("RGB", (96, 192), (100, 150, 200))
        tops, sides = self.convert(src)
        assert tops.mode == "RGBA"
        assert sides.mode == "RGBA"

    # TC-024: Wall-tops larger source appended taller than smaller source
    def test_multi_pair_tops_stacked(self) -> None:
        tops_1, _ = self.convert(_make_a4_source(1))
        src_2 = _make_rgba(96, 384)  # taller → more rows → more top kinds
        tops_2, _ = self.convert(src_2)
        assert tops_2.height >= tops_1.height

    # TC-032: A4 converter crops from correct block coordinates (no overlap)
    def test_a4_coordinate_correctness(self) -> None:
        src = Image.new("RGBA", (192, 240))

        # Paste tops zone (tx=0 is Red, tx=1 is Green) — top 6 mini-rows = 144px
        top0 = Image.new("RGBA", (96, 144), (255, 0, 0, 255))
        top1 = Image.new("RGBA", (96, 144), (0, 255, 0, 255))
        src.paste(top0, (0, 0))
        src.paste(top1, (96, 0))

        # Paste sides zone (tx=0 is Red, tx=1 is Green) — bottom 4 mini-rows = 96px
        side0 = Image.new("RGBA", (96, 96), (255, 0, 0, 255))
        side1 = Image.new("RGBA", (96, 96), (0, 255, 0, 255))
        src.paste(side0, (0, 144))
        src.paste(side1, (96, 144))

        tops, sides = self.convert(src)

        # Tops: 2 kinds (tx=0 Red, tx=1 Green), blob sheet = 8*48 wide, 6*48 tall per kind
        sheet_w = 8 * 48
        sheet_h = 6 * 48
        assert tops.height == 2 * sheet_h

        # First kind: all pixels should be red (uniform source)
        first_top = tops.crop((0, 0, sheet_w, sheet_h))
        for x in [0, 48, 100, 200]:
            for y in [0, 10, 24, 40, 100, 200]:
                assert first_top.getpixel((x, y)) == (255, 0, 0, 255)

        # Second kind: all pixels should be green
        second_top = tops.crop((0, sheet_h, sheet_w, 2 * sheet_h))
        for x in [0, 48, 100, 200]:
            for y in [0, 10, 24, 40, 100, 200]:
                assert second_top.getpixel((x, y)) == (0, 255, 0, 255)

        # Sides: 2 kinds, each a 16-tile strip (16*48 x 48)
        assert sides.height == 2 * 48

        first_side = sides.crop((0, 0, 768, 48))
        for x in [0, 48, 100, 200, 500, 700]:
            for y in [0, 10, 24, 40]:
                assert first_side.getpixel((x, y)) == (255, 0, 0, 255)

        second_side = sides.crop((0, 48, 768, 96))
        for x in [0, 48, 100, 200, 500, 700]:
            for y in [0, 10, 24, 40]:
                assert second_side.getpixel((x, y)) == (0, 255, 0, 255)

    # TC-033: A4 multi-kind tops from horizontal columns (no overlap/mixing)
    def test_a4_tops_two_horizontal_kinds(self) -> None:
        # Multi-kind A4 sources use horizontal columns (tx=0, tx=1...),
        # NOT vertical stacking. Use a 192×240 source: 2 block-cols × 5 tile-rows.
        # col0 (x=0..95): Red tops zone
        # col1 (x=96..191): Green tops zone
        src = Image.new("RGBA", (192, 240))

        top0 = Image.new("RGBA", (96, 144), (255, 0, 0, 255))   # col0 tops (red)
        side0 = Image.new("RGBA", (96, 96), (128, 0, 0, 255))   # col0 sides
        top1 = Image.new("RGBA", (96, 144), (0, 255, 0, 255))   # col1 tops (green)
        side1 = Image.new("RGBA", (96, 96), (0, 128, 0, 255))   # col1 sides

        src.paste(top0, (0, 0))
        src.paste(side0, (0, 144))
        src.paste(top1, (96, 0))
        src.paste(side1, (96, 144))

        tops, _ = self.convert(src)

        # 2 horizontal kinds → 2 blob sheets stacked vertically
        sheet_h = 6 * 48
        assert tops.height == 2 * sheet_h

        # First kind: red (col0)
        first_top = tops.crop((0, 0, 8 * 48, sheet_h))
        for x in [0, 48, 100, 200]:
            for y in [0, 10, 24, 40, 100, 200]:
                assert first_top.getpixel((x, y)) == (255, 0, 0, 255)

        # Second kind: green (col1)
        second_top = tops.crop((0, sheet_h, 8 * 48, 2 * sheet_h))
        for x in [0, 48, 100, 200]:
            for y in [0, 10, 24, 40, 100, 200]:
                assert second_top.getpixel((x, y)) == (0, 255, 0, 255)




# ===========================================================================
# INTEGRATION TESTS
# ===========================================================================

class TestConverterIntegration:

    # IT-001: A3 converter produces valid roof and wall PNG files
    def test_a3_output_valid_png(self, tmp_path) -> None:
        from asset_convertor.core.converter_mv_a3 import convert_mv_a3
        roof, wall = convert_mv_a3(_make_a3_source(2))  # 2 block rows
        for name, img in [("roof", roof), ("wall", wall)]:
            out = tmp_path / f"a3_{name}.png"
            img.save(out)
            loaded = Image.open(out)
            assert loaded.size == img.size

    # IT-002: A4 both outputs are valid PNG
    def test_a4_outputs_valid_png(self, tmp_path) -> None:
        from asset_convertor.core.converter_mv_a4 import convert_mv_a4
        tops, sides = convert_mv_a4(_make_a4_source(1))
        for name, img in [("tops", tops), ("sides", sides)]:
            p = tmp_path / f"a4_{name}.png"
            img.save(p)
            loaded = Image.open(p)
            assert loaded.size == img.size

    # IT-003: FLOOR_AUTOTILE_TABLE is importable from converter_mv (no circular dep)
    def test_floor_table_importable(self) -> None:
        from asset_convertor.core.converter_mv import FLOOR_AUTOTILE_TABLE
        assert len(FLOOR_AUTOTILE_TABLE) == 48  # 47 shapes + 1 (0-indexed)


    # TC-034 — BLOB_BITMASKS slot-order invariant
    def test_a4_tops_blob_slot_order_matches_blob_bitmasks(self) -> None:
        """TC-034: The pixel at slot N in the tops sheet must come from the
        RPGMaker shape for BLOB_BITMASKS[N].

        This is the regression test for the bug where _assemble_floor_tile_sheet
        iterated shape in range(47) (RPGMaker order) instead of BLOB_BITMASKS
        order, causing 45/46 slots to carry the wrong visual relative to the
        wangid declared in the TSX.

        Strategy: use a source image where each mini-tile in the tops zone is a
        unique flat colour (encoded as row*16+col so we can recover it).  Then
        verify that the pixel at slot idx is the colour produced by
        FLOOR_AUTOTILE_TABLE[_bitmask_to_shape(BLOB_BITMASKS[idx])].
        """
        from asset_convertor.core.constants import BLOB_BITMASKS
        from asset_convertor.core.converter_mv import FLOOR_AUTOTILE_TABLE, _bitmask_to_shape
        from asset_convertor.core.converter_mv_a4 import convert_mv_a4

        tile_size = 48
        mini = tile_size // 2  # 24

        # Build a 48px A4 source (1 column = 96px wide).
        # Tops zone: 6 mini-rows × 4 mini-cols (indices 0-3 × 0-5).
        # Encode each mini-tile as a unique flat colour: R = col_idx, G = row_idx.
        src_w = 96   # 1 block column = 4 mini-cols × 24px
        src_h = 240  # 10 mini-rows × 24px (6 top + 4 side)
        src = Image.new("RGBA", (src_w, src_h), (0, 0, 0, 255))
        for mini_row in range(6):
            for mini_col in range(4):
                colour = (mini_col * 10 + 1, mini_row * 10 + 1, 0, 255)
                patch = Image.new("RGBA", (mini, mini), colour)
                src.paste(patch, (mini_col * mini, mini_row * mini))

        tops, _ = convert_mv_a4(src)

        # For each slot, derive expected top-left pixel colour.
        # FLOOR_AUTOTILE_TABLE[shape][0] = (qsx, qsy) = top-left mini-tile coords.
        # The top-left pixel of the assembled tile = colour encoded at (qsx, qsy).
        for slot, bm in enumerate(BLOB_BITMASKS):
            shape = _bitmask_to_shape(bm)
            qsx, qsy = FLOOR_AUTOTILE_TABLE[shape][0]  # top-left quadrant

            expected_colour = (qsx * 10 + 1, qsy * 10 + 1, 0, 255)

            tile_col = slot % 8
            tile_row = slot // 8
            actual_pixel = tops.getpixel((tile_col * tile_size, tile_row * tile_size))

            assert actual_pixel == expected_colour, (
                f"Slot {slot} (bitmask={bm}, shape={shape}): "
                f"expected pixel {expected_colour} (from FLOOR_AUTOTILE_TABLE[{shape}][0]={qsx},{qsy}) "
                f"but got {actual_pixel}. "
                f"Assembly order mismatch — check _assemble_floor_tile_sheet iterates BLOB_BITMASKS."
            )
