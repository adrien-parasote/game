"""
asset_convertor.core.converter_mv_a4

Convert an RPG Maker MV A4 (Wall) source tileset to two Tiled-compatible
tileset strips — one for wall tops (FLOOR table), one for wall sides (WALL table).

Source format (tile_size=48): 768x720 px, mini-tile=24x24 px.
Source format (tile_size=32): 512x480 px, mini-tile=16x16 px.
  - 6 block-rows, alternating between FLOOR and WALL by row parity:
    ty=0 (even) → wall tops  (FLOOR_AUTOTILE_TABLE, 47 shapes, 8x6 output per kind)
    ty=1 (odd)  → wall sides (WALL_AUTOTILE_TABLE,  16 shapes, 16x1 output per kind)

Output (tile_size=48):
  - wall_tops_img:  RGBA, 8*48=384 wide, 6*48*N_top_kinds tall
  - wall_sides_img: RGBA, 16*48=768 wide, N_side_kinds*48 tall

Output (tile_size=32):
  - wall_tops_img:  RGBA, 8*32=256 wide, 6*32*N_top_kinds tall
  - wall_sides_img: RGBA, 16*32=512 wide, N_side_kinds*32 tall

Spec: tools/docs/specs/asset_convertor_mv_core_converters.md § "A4 Converter"
"""

from __future__ import annotations

from asset_convertor.core.converter_mv import FLOOR_AUTOTILE_TABLE
from asset_convertor.core.converter_mv_a3 import (
    WALL_AUTOTILE_TABLE,
)
from PIL import Image

# ---------------------------------------------------------------------------
# Valid A4 source block sizes → detected tile size
# An A4 block = 4 mini-tiles wide = 2 * tile_size
# ---------------------------------------------------------------------------

_VALID_BLOCK_SIZES_A4: dict[int, int] = {
    64: 32,   # 4 mini-tiles × 16px = 64px  (32px tileset)
    96: 48,   # 4 mini-tiles × 24px = 96px  (48px tileset)
}

# A4 source block-row Y offset in mini-tiles (from corescript)
# ty=0..5 → by = [0, 3, 5, 8, 10, 13]
_BY_LOOKUP_A4: dict[int, int] = {0: 0, 1: 3, 2: 5, 3: 8, 4: 10, 5: 13}

# Output geometry constants (tile-size-independent)
_TOP_SHEET_COLS = 8
_TOP_SHEET_ROWS = 6    # 47 tiles + 1 padding = 48 slots = 6×8
_SIDE_NUM_SHAPES = 16
_BLOCK_COLS = 8


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def convert_mv_a4(img: Image.Image) -> tuple[Image.Image, Image.Image]:
    """
    Convert an RPG Maker MV A4 (Wall) source tileset to two
    Tiled-compatible tileset strips.

    Supports both 32px and 48px tile sizes:
      - 32px: source block width = 64px
      - 48px: source block width = 96px

    Args:
        img: PIL Image, source A4 PNG (RGBA or RGB).
             Width must be a multiple of 64 (32px) or 96 (48px).
             Minimum height: 5 mini-tile rows = 5 × (tile_size/2).

    Returns:
        tuple: (wall_tops_img, wall_sides_img)
            wall_tops_img:  RGBA, width=8*tile_size, height=N_top_kinds * 6*tile_size
                            (47 shapes per kind, 8-col × 6-row per kind)
            wall_sides_img: RGBA, width=16*tile_size, height=N_side_kinds * tile_size
                            (16 shapes per kind, from WALL_AUTOTILE_TABLE)

    Raises:
        ValueError: If img width is not recognized as a valid A4 block size.
        ValueError: If img dimensions are too small for the detected tile size.
    """
    src = img.convert("RGBA")
    tile_size, mini, block_size, mini_a4_row = _detect_a4_geometry(src)

    top_output_w = _TOP_SHEET_COLS * tile_size
    side_output_w = _SIDE_NUM_SHAPES * tile_size

    max_ty = 5
    top_strips: list[Image.Image] = []
    side_strips: list[Image.Image] = []

    for ty in range(max_ty + 1):
        by = _BY_LOOKUP_A4[ty]

        # Check if this row fits within source image
        if (by + 4) * mini > src.height:
            break

        # Determine horizontal range
        n_cols = min(src.width // block_size, _BLOCK_COLS)

        if ty % 2 == 0:
            # FLOOR row (wall tops) — 47 shapes, 8×6 tile sheet per kind
            for tx in range(n_cols):
                bx = tx * 2  # block column in mini-tile units
                if _is_block_empty(src, bx, by, mini, block_size):
                    continue
                sheet = _build_floor_sheet(src, bx, by, tile_size, mini, top_output_w)
                top_strips.append(sheet)
        else:
            # WALL row (wall sides) — 16 shapes, 16×1 strip per kind
            for tx in range(n_cols):
                bx = tx * 2
                if _is_block_empty(src, bx, by, mini, block_size):
                    continue
                strip = _assemble_wall_tile_strip(src, bx, by, tile_size, mini, side_output_w)
                side_strips.append(strip)

    # Build output images
    tops_img = _stack_vertically(top_strips, top_output_w) if top_strips else (
        Image.new("RGBA", (top_output_w, 0))
    )
    sides_img = _stack_vertically(side_strips, side_output_w) if side_strips else (
        Image.new("RGBA", (side_output_w, 0))
    )

    # Ensure non-zero height for empty results
    if tops_img.height == 0:
        tops_img = Image.new("RGBA", (top_output_w, _TOP_SHEET_ROWS * tile_size))
    if sides_img.height == 0:
        sides_img = Image.new("RGBA", (side_output_w, tile_size))

    return tops_img, sides_img


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _detect_a4_geometry(src: Image.Image) -> tuple[int, int, int, int]:
    """
    Detect tile_size from source width and return geometry tuple.

    Returns:
        (tile_size, mini, block_size, mini_a4_row)

    Raises:
        ValueError: If source width is not a recognized A4 block size multiple,
                    or if dimensions are too small.
    """
    # Try to find matching block_size
    detected_tile_size: int | None = None
    detected_block_size: int | None = None

    for block_size, tile_size in _VALID_BLOCK_SIZES_A4.items():
        if src.width >= block_size and src.width % block_size == 0:
            detected_tile_size = tile_size
            detected_block_size = block_size
            break

    if detected_tile_size is None or detected_block_size is None:
        valid = ", ".join(
            f"{bs}px (tile={ts}px)" for bs, ts in sorted(_VALID_BLOCK_SIZES_A4.items())
        )
        raise ValueError(
            f"Largeur source A4 invalide: {src.width}px. "
            f"Doit être multiple d'un block_size valide: {valid}."
        )

    mini = detected_tile_size // 2
    block_size = detected_block_size
    mini_a4_row = mini * 5  # minimum height: 1 top pair + 1 side row = 5 mini-tile rows

    if src.width < block_size or src.height < mini_a4_row:
        raise ValueError(
            f"Image trop petite: {src.size}. "
            f"Minimum {block_size}x{mini_a4_row} px pour A4 {detected_tile_size}px."
        )

    return detected_tile_size, mini, block_size, mini_a4_row


def _is_block_empty(
    src: Image.Image, bx: int, by: int, mini: int, block_size: int
) -> bool:
    """Return True if the block at (bx, by) mini-tile offset is all-transparent."""
    x0 = bx * mini
    y0 = by * mini
    x1 = min(x0 + block_size, src.width)
    y1 = min(y0 + block_size, src.height)
    if x1 <= x0 or y1 <= y0:
        return True
    crop = src.crop((x0, y0, x1, y1))
    _, _, _, a = crop.split()
    return a.getextrema()[1] == 0


def _assemble_floor_tile(
    src: Image.Image, bx: int, by: int, shape: int, tile_size: int, mini: int
) -> Image.Image:
    """
    Assemble one tile_size×tile_size tile from FLOOR_AUTOTILE_TABLE[shape].

    Args:
        src: Source RGBA image.
        bx: Block column offset in mini-tile units.
        by: Block row offset in mini-tile units.
        shape: Shape index 0-46 from FLOOR_AUTOTILE_TABLE.
        tile_size: Output tile size in pixels (32 or 48).
        mini: Half of tile_size (mini-tile edge length).
    """
    tile = Image.new("RGBA", (tile_size, tile_size))
    quads = FLOOR_AUTOTILE_TABLE[shape]

    dst_positions = [(0, 0), (mini, 0), (0, mini), (mini, mini)]

    for q, (dst_x, dst_y) in enumerate(dst_positions):
        qsx, qsy = quads[q]
        src_x = (bx + qsx) * mini
        src_y = (by + qsy) * mini
        crop = src.crop((src_x, src_y, src_x + mini, src_y + mini))
        tile.paste(crop, (dst_x, dst_y))

    return tile


def _assemble_wall_tile(
    src: Image.Image, bx: int, by: int, shape: int, tile_size: int, mini: int
) -> Image.Image:
    """
    Assemble one tile_size×tile_size tile from WALL_AUTOTILE_TABLE[shape].

    Args:
        src: Source RGBA image.
        bx: Block column in mini-tile units.
        by: Block row in mini-tile units.
        shape: Shape index 0-15 from WALL_AUTOTILE_TABLE.
        tile_size: Output tile size in pixels (32 or 48).
        mini: Half of tile_size (mini-tile edge length).
    """
    tile = Image.new("RGBA", (tile_size, tile_size))
    quads = WALL_AUTOTILE_TABLE[shape]

    dst_positions = [(0, 0), (mini, 0), (0, mini), (mini, mini)]

    for q, (dst_x, dst_y) in enumerate(dst_positions):
        qsx, qsy = quads[q]
        src_x = (bx + qsx) * mini
        src_y = (by + qsy) * mini
        crop = src.crop((src_x, src_y, src_x + mini, src_y + mini))
        tile.paste(crop, (dst_x, dst_y))

    return tile


def _build_floor_sheet(
    src: Image.Image, bx: int, by: int,
    tile_size: int, mini: int, output_w: int,
) -> Image.Image:
    """
    Build a 8-col × 6-row sheet of 47 FLOOR tiles + 1 transparent padding.

    Returns:
        RGBA Image, width=output_w, height=_TOP_SHEET_ROWS * tile_size.
    """
    sheet = Image.new("RGBA", (output_w, _TOP_SHEET_ROWS * tile_size))
    for shape in range(47):
        tile = _assemble_floor_tile(src, bx, by, shape, tile_size, mini)
        col = shape % _TOP_SHEET_COLS
        row = shape // _TOP_SHEET_COLS
        sheet.paste(tile, (col * tile_size, row * tile_size))
    # Slot 47 left transparent (padding)
    return sheet


def _assemble_wall_tile_strip(
    src: Image.Image, bx: int, by: int,
    tile_size: int, mini: int, output_w: int,
) -> Image.Image:
    """
    Build a strip of 16 WALL tiles for the block at (bx, by).

    Returns:
        RGBA Image, width=output_w, height=tile_size.
    """
    strip = Image.new("RGBA", (output_w, tile_size))
    for shape in range(_SIDE_NUM_SHAPES):
        tile = _assemble_wall_tile(src, bx, by, shape, tile_size, mini)
        strip.paste(tile, (shape * tile_size, 0))
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
