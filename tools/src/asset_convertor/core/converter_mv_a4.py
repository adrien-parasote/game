"""
asset_convertor.core.converter_mv_a4

Convert an RPG Maker MV A4 (Wall) source tileset to two Tiled-compatible
tileset strips — one for wall tops (FLOOR table), one for wall sides (WALL table).

Source format: 768x720 px (full A4 sheet), tile_size=48, mini-tile=24x24 px.
  - 6 block-rows, alternating between FLOOR and WALL by row parity:
    ty=0 (even) → wall tops  (FLOOR_AUTOTILE_TABLE, 47 shapes, 8x6 output per kind)
    ty=1 (odd)  → wall sides (WALL_AUTOTILE_TABLE,  16 shapes, 16x1 output per kind)

Output:
  - wall_tops_img:  RGBA, 8*48=384 wide, 6*48*N_top_kinds tall
  - wall_sides_img: RGBA, 16*48=768 wide, N_side_kinds*48 tall

Spec: tools/docs/specs/asset_convertor_mv_core_converters.md § "A4 Converter"
"""

from __future__ import annotations

from asset_convertor.core.converter_mv import FLOOR_AUTOTILE_TABLE
from asset_convertor.core.converter_mv_a3 import (
    _assemble_wall_tile,
)
from PIL import Image

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_TILE_SIZE = 48
_MINI = _TILE_SIZE // 2         # 24 px mini-tile
_BLOCK_SIZE = _MINI * 4         # 96 px per autotile block (4 mini-tiles wide)
_MINI_A4_ROW = _MINI * 5       # 120 px = minimum height (1 top pair + 1 side row)

# A4 source block-row Y offset in mini-tiles (from corescript)
# ty=0..5 → by = [0, 3, 5, 8, 10, 13]
_BY_LOOKUP_A4: dict[int, int] = {0: 0, 1: 3, 2: 5, 3: 8, 4: 10, 5: 13}

# For FLOOR tiles, A4 top rows occupy 5 mini-tile rows (2+3 = top block + half)
# This lookup maps ty (0,2,4) to the pixel-height boundary in the source image.
# Each pair (top-row + side-row) occupies: floor_rows * MINI = 5 * 24 = 120 px
# But the blocks within each ty are 2 mini-tiles tall (one autotile block = 96x96)
# We use the lookup above.

# Output geometry for wall-tops (FLOOR table, same as A2)
_TOP_SHEET_COLS = 8
_TOP_SHEET_ROWS = 6              # 47 tiles + 1 padding = 48 slots = 6x8
_TOP_OUTPUT_W = _TOP_SHEET_COLS * _TILE_SIZE   # 384 px

# Output geometry for wall-sides (WALL table, same as A3)
_SIDE_NUM_SHAPES = 16
_SIDE_OUTPUT_W = _SIDE_NUM_SHAPES * _TILE_SIZE  # 768 px

# A3/A4 block column count
_BLOCK_COLS = 8


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def convert_mv_a4(img: Image.Image) -> tuple[Image.Image, Image.Image]:
    """
    Convert an RPG Maker MV A4 (Wall) source tileset to two
    Tiled-compatible tileset strips.

    Args:
        img: PIL Image, source A4 PNG (768x720 or smaller, RGBA or RGB).
             Must be at least 96x120 px (one top row + one side row).

    Returns:
        tuple: (wall_tops_img, wall_sides_img)
            wall_tops_img:  RGBA, width=384, height=N_top_kinds * 288
                            (47 shapes per kind, 8-col x 6-row per kind)
            wall_sides_img: RGBA, width=768, height=N_side_kinds * 48
                            (16 shapes per kind, from WALL_AUTOTILE_TABLE)

    Raises:
        ValueError: If img dimensions are smaller than 96x120 px.
        ValueError: If img width is not a multiple of 96.
    """
    src = img.convert("RGBA")
    _validate_a4_dimensions(src)

    # Determine available block-rows from source height
    # Each "ty pair" (one floor row + one side row) uses 5 mini-tile rows = 120 px
    # We check available ty values 0..5
    max_ty = 5

    top_strips: list[Image.Image] = []     # 8x6-tile sheets per top kind
    side_strips: list[Image.Image] = []    # 16x1-tile strips per side kind

    for ty in range(max_ty + 1):
        by = _BY_LOOKUP_A4[ty]

        # Check if this row fits within source image
        if (by + 4) * _MINI > src.height:   # need at least 4 mini-tile rows per block
            break

        # Determine horizontal range
        n_cols = min(src.width // _BLOCK_SIZE, _BLOCK_COLS)

        if ty % 2 == 0:
            # FLOOR row (wall tops) — 47 shapes, 8x6 tile sheet per kind
            for tx in range(n_cols):
                bx = tx * 2  # block column in mini-tiles
                if _is_block_empty(src, bx, by):
                    continue
                sheet = _build_floor_sheet(src, bx, by)
                top_strips.append(sheet)
        else:
            # WALL row (wall sides) — 16 shapes, 16x1 strip per kind
            for tx in range(n_cols):
                bx = tx * 2
                if _is_block_empty(src, bx, by):
                    continue
                strip = _assemble_wall_tile_strip(src, bx, by)
                side_strips.append(strip)

    # Build output images
    tops_img = _stack_vertically(top_strips, _TOP_OUTPUT_W) if top_strips else (
        Image.new("RGBA", (_TOP_OUTPUT_W, 0))
    )
    sides_img = _stack_vertically(side_strips, _SIDE_OUTPUT_W) if side_strips else (
        Image.new("RGBA", (_SIDE_OUTPUT_W, 0))
    )

    # Ensure non-zero height for empty results (return 1xtile_size placeholder)
    if tops_img.height == 0:
        tops_img = Image.new("RGBA", (_TOP_OUTPUT_W, _TOP_SHEET_ROWS * _TILE_SIZE))
    if sides_img.height == 0:
        sides_img = Image.new("RGBA", (_SIDE_OUTPUT_W, _TILE_SIZE))

    return tops_img, sides_img


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _validate_a4_dimensions(src: Image.Image) -> None:
    """Raise ValueError if source dimensions are invalid for A4."""
    if src.width < _BLOCK_SIZE or src.height < _MINI_A4_ROW:
        raise ValueError(
            f"Image trop petite: {src.size}. Minimum {_BLOCK_SIZE}x{_MINI_A4_ROW} px pour A4."
        )
    if src.width % _BLOCK_SIZE != 0:
        raise ValueError(
            f"Largeur {src.width} invalide. Doit être multiple de {_BLOCK_SIZE} px pour A4 MV."
        )


def _is_block_empty(src: Image.Image, bx: int, by: int) -> bool:
    """Return True if the 96x96 block at (bx, by) mini-tile offset is all-transparent."""
    x0 = bx * _MINI
    y0 = by * _MINI
    # Guard: don't crop beyond image bounds
    x1 = min(x0 + _BLOCK_SIZE, src.width)
    y1 = min(y0 + _BLOCK_SIZE, src.height)
    if x1 <= x0 or y1 <= y0:
        return True
    crop = src.crop((x0, y0, x1, y1))
    _, _, _, a = crop.split()
    return a.getextrema()[1] == 0


def _assemble_floor_tile(src: Image.Image, bx: int, by: int, shape: int) -> Image.Image:
    """
    Assemble one 48x48 tile from FLOOR_AUTOTILE_TABLE[shape].
    Same algorithm as converter_mv.py _build_mv_tile, adapted for A4.

    Args:
        src: Source RGBA image.
        bx: Block column offset in mini-tile units.
        by: Block row offset in mini-tile units.
        shape: Shape index 0-46 from FLOOR_AUTOTILE_TABLE.
    """
    tile = Image.new("RGBA", (_TILE_SIZE, _TILE_SIZE))
    quads = FLOOR_AUTOTILE_TABLE[shape]

    # Quadrant positions: TL, TR, BL, BR
    dst_positions = [(0, 0), (_MINI, 0), (0, _MINI), (_MINI, _MINI)]

    for q, (dst_x, dst_y) in enumerate(dst_positions):
        qsx, qsy = quads[q]
        src_x = (bx + qsx) * _MINI
        src_y = (by + qsy) * _MINI
        crop = src.crop((src_x, src_y, src_x + _MINI, src_y + _MINI))
        tile.paste(crop, (dst_x, dst_y))

    return tile


def _build_floor_sheet(src: Image.Image, bx: int, by: int) -> Image.Image:
    """
    Build a 8-col x 6-row sheet of 47 FLOOR tiles + 1 transparent padding.

    Output: RGBA Image, width=384, height=288 (6 rows x 48px per kind).
    """
    sheet = Image.new("RGBA", (_TOP_OUTPUT_W, _TOP_SHEET_ROWS * _TILE_SIZE))
    for shape in range(47):
        tile = _assemble_floor_tile(src, bx, by, shape)
        col = shape % _TOP_SHEET_COLS
        row = shape // _TOP_SHEET_COLS
        sheet.paste(tile, (col * _TILE_SIZE, row * _TILE_SIZE))
    # Slot 47 is left transparent (padding)
    return sheet


def _assemble_wall_tile_strip(src: Image.Image, bx: int, by: int) -> Image.Image:
    """
    Build a strip of 16 WALL tiles for the block at (bx, by).

    Output: RGBA Image, width=768, height=48.
    """
    strip = Image.new("RGBA", (_SIDE_OUTPUT_W, _TILE_SIZE))
    for shape in range(_SIDE_NUM_SHAPES):
        tile = _assemble_wall_tile(src, bx, by, shape)
        strip.paste(tile, (shape * _TILE_SIZE, 0))
    return strip


def _stack_vertically(images: list[Image.Image], width: int) -> Image.Image:
    """Stack a list of images vertically into a single image."""
    total_height = sum(img.height for img in images)
    result = Image.new("RGBA", (width, total_height))
    y = 0
    for img in images:
        result.paste(img, (0, y))
        y += img.height
    return result
