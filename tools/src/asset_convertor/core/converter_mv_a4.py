"""
asset_convertor.core.converter_mv_a4

Convert an RPG Maker MV A4 (Wall) source tileset to two Tiled-compatible
tileset images:
  - wall_tops:  blob autotile sheet (FLOOR_AUTOTILE_TABLE, 47 shapes, 8×6 grid)
  - wall_sides: wall autotile strip (WALL_AUTOTILE_TABLE,  16 shapes, 16×1 strip)

Source format (tile_size=48): one block = 96×240 px (2 tile-cols × 5 tile-rows).
Source format (tile_size=32): one block = 64×160 px (2 tile-cols × 5 tile-rows).
  - Rows 0-2 (top 6 mini-rows)    → wall TOPS  (floor autotile layout → FLOOR_AUTOTILE_TABLE)
  - Rows 3-4 (bottom 4 mini-rows) → wall SIDES (wall autotile layout  → WALL_AUTOTILE_TABLE)

The tops zone has a FLOOR source layout (same as A2): 4 mini-cols × 6 mini-rows.
FLOOR_AUTOTILE_TABLE reads (qsx, qsy) from this zone with qsy ∈ {0..5}, which maps
perfectly to the 6 mini-rows of the tops zone.

The sides zone has a WALL source layout: 4 mini-cols × 4 mini-rows.
WALL_AUTOTILE_TABLE reads (qsx, qsy) with qsy ∈ {0..3}, matching the 4 mini-rows.

Output (tile_size=32):
  - wall_tops_img:  RGBA, 8*32=256 wide,  N_top_kinds * 6*32 tall (47-blob sheet per kind)
  - wall_sides_img: RGBA, 16*32=512 wide, N_side_kinds * 32 tall  (16-wall strip per kind)

Output (tile_size=48):
  - wall_tops_img:  RGBA, 8*48=384 wide,  N_top_kinds * 6*48 tall
  - wall_sides_img: RGBA, 16*48=768 wide, N_side_kinds * 48 tall

Spec: tools/docs/specs/asset_convertor_mv_core_converters.md § "A4 Converter"
"""

from __future__ import annotations

from asset_convertor.core.constants import BLOB_BITMASKS
from asset_convertor.core.converter_mv import FLOOR_AUTOTILE_TABLE, _bitmask_to_shape
from asset_convertor.core.converter_mv_a3 import WALL_AUTOTILE_TABLE
from PIL import Image

# ---------------------------------------------------------------------------
# Valid A4 source block sizes → detected tile size
# An A4 block = 4 mini-tiles wide = 2 * tile_size
# ---------------------------------------------------------------------------

_VALID_BLOCK_SIZES_A4: dict[int, int] = {
    96: 48,   # 4 mini-tiles × 24px = 96px  (48px tileset)
    64: 32,   # 4 mini-tiles × 16px = 64px  (32px tileset)
}

# Wall source occupies the last _WALL_MINI_ROWS mini-rows of the A4 source image.
# 2 tile-rows = 4 mini-rows.
_WALL_MINI_ROWS = 4

# Tops zone: always the top 6 mini-rows of the source (3 tile-rows = floor autotile layout)
_TOP_MINI_ROWS = 6

# Output geometry constants (tile-size-independent)
# Tops: 47 shapes in an 8-col × 6-row grid   (FLOOR_AUTOTILE_TABLE)
# Sides: 16 shapes in a 16-col × 1-row strip (WALL_AUTOTILE_TABLE)
_TOP_SHEET_COLS = 8    # blob autotile sheet width in tiles
_TOP_SHEET_ROWS = 6    # blob autotile sheet height in tiles (47 shapes + 1 padding)
_SIDE_NUM_SHAPES = 16  # 4-neighbor wall shapes
_BLOCK_COLS = 8        # max horizontal blocks in an A4 source


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def convert_mv_a4(img: Image.Image) -> tuple[Image.Image, Image.Image]:
    """
    Convert an RPG Maker MV A4 (Wall) source tileset to two Tiled-compatible images.

    - wall_tops:  blob autotile sheet (FLOOR_AUTOTILE_TABLE, 47 shapes, 8×6 tiles per kind)
    - wall_sides: wall strip (WALL_AUTOTILE_TABLE, 16 shapes, 16×1 tiles per kind)

    Supports both 32px and 48px tile sizes:
      - 32px: source block width = 64px
      - 48px: source block width = 96px

    The tops zone (first 3 tile-rows of each block pair) is a FLOOR autotile source.
    It is assembled using FLOOR_AUTOTILE_TABLE into the standard 8×6 blob sheet format
    (slots 0-46 = 47 shapes, slot 47 = transparent padding).

    The sides zone (last 2 tile-rows = bottom 4 mini-rows of the source) is a WALL
    autotile source assembled with WALL_AUTOTILE_TABLE into a 16-tile strip.

    Args:
        img: PIL Image, source A4 PNG (RGBA or RGB).
             Width must be a multiple of 64 (32px) or 96 (48px).
             Minimum height: 5 mini-tile rows × (tile_size/2).

    Returns:
        tuple: (wall_tops_img, wall_sides_img)
            wall_tops_img:  RGBA, width=8*tile_size, height=N_kinds * 6*tile_size
                            (47-shape blob sheet per kind)
            wall_sides_img: RGBA, width=16*tile_size, height=N_side_kinds * tile_size
                            (16-shape wall strip per kind)

    Raises:
        ValueError: If img width is not recognized as a valid A4 block size.
        ValueError: If img dimensions are too small for the detected tile size.
    """
    src = img.convert("RGBA")
    tile_size, mini, block_size, mini_a4_row = _detect_a4_geometry(src)

    top_output_w = _TOP_SHEET_COLS * tile_size        # 8 * tile_size
    top_output_h_per_kind = _TOP_SHEET_ROWS * tile_size  # 6 * tile_size
    side_output_w = _SIDE_NUM_SHAPES * tile_size      # 16 * tile_size

    top_sheets: list[Image.Image] = []
    side_strips: list[Image.Image] = []

    # Process only one pair of block rows: tops (rows 0-2) + sides (rows 3-4)
    # For a standard single-kind A4 source (2 cols × 5 rows), there is one pair.
    # Multi-kind sources are not common for A4 but supported by iterating columns.
    n_cols = min(src.width // block_size, _BLOCK_COLS)

    # Tops: read from the top 6 mini-rows (by=0)
    top_by = 0
    for tx in range(n_cols):
        bx = tx * 4  # block column in mini-tile units
        if _is_block_empty(src, bx, top_by, mini, block_size):
            continue
        sheet = _assemble_floor_tile_sheet(
            src, bx, top_by, tile_size, mini, top_output_w, top_output_h_per_kind
        )
        top_sheets.append(sheet)

    # Sides: read from the last 4 mini-rows
    wall_mini_y0 = _get_wall_source_mini_y0(src, mini)
    for tx in range(n_cols):
        bx = tx * 4
        if _is_block_empty(src, bx, wall_mini_y0, mini, block_size):
            continue
        strip = _assemble_wall_tile_strip(
            src, bx, wall_mini_y0, tile_size, mini, side_output_w
        )
        side_strips.append(strip)

    # Build output images
    tops_img = _stack_vertically(top_sheets, top_output_w) if top_sheets else (
        Image.new("RGBA", (top_output_w, top_output_h_per_kind))
    )
    sides_img = _stack_vertically(side_strips, side_output_w) if side_strips else (
        Image.new("RGBA", (side_output_w, tile_size))
    )

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
    mini_a4_row = mini * 5  # minimum height: 1 top zone (6 rows) + 1 side zone (4 rows) - 5 overlap

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


def _get_wall_source_mini_y0(src: Image.Image, mini: int) -> int:
    """Return the mini-tile row index of the wall (sides) source block origin.

    The A4 sides zone occupies the last _WALL_MINI_ROWS (4) mini-rows of the source.
    """
    return (src.height - _WALL_MINI_ROWS * mini) // mini


def _assemble_floor_tile(
    src: Image.Image, bx: int, by: int, shape: int, tile_size: int, mini: int
) -> Image.Image:
    """Assemble one tile_size×tile_size tile from FLOOR_AUTOTILE_TABLE[shape].

    The FLOOR_AUTOTILE_TABLE uses (qsx, qsy) coordinates where:
      - qsx ∈ {0,1,2,3} = mini-tile column within the block
      - qsy ∈ {0,1,2,3,4,5} = mini-tile row within the tops zone

    Args:
        src:       Source RGBA image.
        bx:        Block column offset in mini-tile units.
        by:        Block row offset in mini-tile units (0 for tops zone).
        shape:     Shape index 0-46 from FLOOR_AUTOTILE_TABLE.
        tile_size: Output tile size in pixels (32 or 48).
        mini:      Half of tile_size (mini-tile edge length).
    """
    out = Image.new("RGBA", (tile_size, tile_size))
    quads = FLOOR_AUTOTILE_TABLE[shape]
    dst_positions = [(0, 0), (mini, 0), (0, mini), (mini, mini)]

    for q, (dst_x, dst_y) in enumerate(dst_positions):
        qsx, qsy = quads[q]
        src_x = (bx + qsx) * mini
        src_y = (by + qsy) * mini
        crop = src.crop((src_x, src_y, src_x + mini, src_y + mini))
        out.paste(crop, (dst_x, dst_y))

    return out


def _assemble_floor_tile_sheet(
    src: Image.Image, bx: int, by: int,
    tile_size: int, mini: int,
    output_w: int, output_h: int,
) -> Image.Image:
    """Build the 8×6 blob autotile sheet for the block at (bx, by).

    Slots 0-46: the 47 FLOOR_AUTOTILE_TABLE shapes.
    Slot 47:    transparent padding (to fill the 8×6 = 48 slot grid).

    Returns:
        RGBA Image, width=output_w (8*tile_size), height=output_h (6*tile_size).
    """
    sheet = Image.new("RGBA", (output_w, output_h))
    for slot, bm in enumerate(BLOB_BITMASKS):
        # Convert blob bitmask to RPGMaker shape index, then assemble that shape.
        # BLOB_BITMASKS order matches the TSX wangid order (tileid=slot ↔ bitmask=bm).
        # Using _bitmask_to_shape ensures the right FLOOR_AUTOTILE_TABLE row is read
        # for this bitmask, so the pixel content matches the declared wangid.
        shape = _bitmask_to_shape(bm)
        tile = _assemble_floor_tile(src, bx, by, shape, tile_size, mini)
        col = slot % _TOP_SHEET_COLS
        row = slot // _TOP_SHEET_COLS
        sheet.paste(tile, (col * tile_size, row * tile_size))
    # slot 47 = transparent padding → already transparent by default
    return sheet


def _assemble_wall_tile(
    src: Image.Image, bx: int, by: int, shape: int, tile_size: int, mini: int
) -> Image.Image:
    """Assemble one tile_size×tile_size tile from WALL_AUTOTILE_TABLE[shape].

    Coordinate convention:
        WALL_AUTOTILE_TABLE [qsx, qsy] coordinates map directly to the source
        mini-tile grid without any axis inversion.  The wall source block
        starts at pixel y = by * mini, where `by` MUST be the value returned
        by _get_wall_source_mini_y0() (i.e. the last _WALL_MINI_ROWS mini-rows
        of the source image).

    Args:
        src:       Source RGBA image.
        bx:        Block column offset in mini-tile units (horizontal only).
        by:        Wall source block row in mini-tile units — use _get_wall_source_mini_y0().
        shape:     Shape index 0-15 from WALL_AUTOTILE_TABLE.
        tile_size: Output tile size in pixels (32 or 48).
        mini:      Half of tile_size (mini-tile edge length).
    """
    out = Image.new("RGBA", (tile_size, tile_size))
    quads = WALL_AUTOTILE_TABLE[shape]
    dst_positions = [(0, 0), (mini, 0), (0, mini), (mini, mini)]

    for q, (dst_x, dst_y) in enumerate(dst_positions):
        qsx, qsy = quads[q]
        src_x = (bx + qsx) * mini
        src_y = by * mini + qsy * mini
        crop = src.crop((src_x, src_y, src_x + mini, src_y + mini))
        out.paste(crop, (dst_x, dst_y))

    return out


def _assemble_wall_tile_strip(
    src: Image.Image, bx: int, by: int,
    tile_size: int, mini: int, output_w: int,
) -> Image.Image:
    """Build a strip of 16 WALL tiles for the block at (bx, by).

    Returns:
        RGBA Image, width=output_w (16*tile_size), height=tile_size.
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
