"""
asset_convertor.core.converter_mv_a3

Convert an RPG Maker MV A3 (Building/Roof) source tileset to a
Tiled-compatible tileset strip.

Source format: 768x384 px (full A3 sheet), tile_size=48, mini-tile=24x24 px.
  - 8 columns x 4 rows of autotile blocks (96x96 px each).
  - Each block encodes one autotile kind using WALL_AUTOTILE_TABLE (16 shapes).

Output format: Single PNG strip, 768 px wide (16 x 48), height = N_kinds x 48 px.
  - One row of 16 tiles per detected non-empty autotile kind.

Spec: tools/docs/specs/asset_convertor_mv_core_converters.md § "A3 Converter"
"""

from __future__ import annotations

from PIL import Image

# ---------------------------------------------------------------------------
# WALL_AUTOTILE_TABLE
# Source: rpgtkoolmv/corescript js/rpg_core/Tilemap.js (blob 9ff2991)
# 16 shapes, each = [TL, TR, BL, BR] as [qsx, qsy] mini-tile coordinates.
# ---------------------------------------------------------------------------

WALL_AUTOTILE_TABLE: list[list[list[int]]] = [
    [[2, 2], [1, 2], [2, 1], [1, 1]],  # shape  0
    [[0, 2], [1, 2], [0, 1], [1, 1]],  # shape  1
    [[2, 0], [1, 0], [2, 1], [1, 1]],  # shape  2
    [[0, 0], [1, 0], [0, 1], [1, 1]],  # shape  3
    [[2, 2], [3, 2], [2, 1], [3, 1]],  # shape  4
    [[0, 2], [3, 2], [0, 1], [3, 1]],  # shape  5
    [[2, 0], [3, 0], [2, 1], [3, 1]],  # shape  6
    [[0, 0], [3, 0], [0, 1], [3, 1]],  # shape  7
    [[2, 2], [1, 2], [2, 3], [1, 3]],  # shape  8
    [[0, 2], [1, 2], [0, 3], [1, 3]],  # shape  9
    [[2, 0], [1, 0], [2, 3], [1, 3]],  # shape 10
    [[0, 0], [1, 0], [0, 3], [1, 3]],  # shape 11
    [[2, 2], [3, 2], [2, 3], [3, 3]],  # shape 12
    [[0, 2], [3, 2], [0, 3], [3, 3]],  # shape 13
    [[2, 0], [3, 0], [2, 3], [3, 3]],  # shape 14
    [[0, 0], [3, 0], [0, 3], [3, 3]],  # shape 15
]

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_TILE_SIZE = 48
_MINI = _TILE_SIZE // 2           # 24 px mini-tile
_BLOCK_SIZE = _MINI * 4           # 96 px per autotile block (4 mini-tiles wide)
_NUM_SHAPES = 16                  # WALL_AUTOTILE_TABLE entries
_BLOCK_COLS = 8                   # A3 sheet: 8 columns of blocks
_BLOCK_ROWS = 4                   # A3 sheet: 4 rows of blocks (768x384 px)
_OUTPUT_WIDTH = _NUM_SHAPES * _TILE_SIZE  # 768 px


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def convert_mv_a3(img: Image.Image) -> Image.Image:
    """
    Convert an RPG Maker MV A3 (Building/Roof) source tileset
    to a Tiled-compatible tileset strip.

    Args:
        img: PIL Image, source A3 PNG (768x384 or smaller, RGBA or RGB).
             Must be at least 96x96 px and width must be a multiple of 96.

    Returns:
        PIL Image: Output tileset, RGBA, width=768, height=N*48
        where N = number of detected non-empty autotile blocks.

    Raises:
        ValueError: If img dimensions are too small (< 96x96 px).
        ValueError: If img width is not a multiple of 96.
        ValueError: If no valid autotile blocks are found.
    """
    src = img.convert("RGBA")
    _validate_a3_dimensions(src)

    # Determine block grid from source dimensions (may be partial sheet)
    n_cols = min(src.width // _BLOCK_SIZE, _BLOCK_COLS)
    n_rows = src.height // _BLOCK_SIZE

    # Collect non-empty kinds in reading order
    kind_rows: list[Image.Image] = []

    for ty in range(n_rows):
        for tx in range(n_cols):
            bx = tx * 2   # block column in mini-tiles (2 mini-tiles per block col)
            by = ty * 2   # block row in mini-tiles

            if _is_block_empty(src, bx, by):
                continue

            row_img = _build_wall_strip(src, bx, by)
            kind_rows.append(row_img)

    if not kind_rows:
        raise ValueError(
            "Aucun bloc valide détecté. Le fichier est-il bien un A3 MV ?"
        )

    # Stack all rows vertically
    output = Image.new("RGBA", (_OUTPUT_WIDTH, _TILE_SIZE * len(kind_rows)))
    for idx, row_img in enumerate(kind_rows):
        output.paste(row_img, (0, idx * _TILE_SIZE))

    return output


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _validate_a3_dimensions(src: Image.Image) -> None:
    """Raise ValueError if source dimensions are invalid for A3."""
    if src.width < _BLOCK_SIZE or src.height < _BLOCK_SIZE:
        raise ValueError(
            f"Image trop petite: {src.size}. Minimum {_BLOCK_SIZE}x{_BLOCK_SIZE} px pour A3."
        )
    if src.width % _BLOCK_SIZE != 0:
        raise ValueError(
            f"Largeur {src.width} invalide. Doit être multiple de {_BLOCK_SIZE} px pour A3 MV."
        )
    if src.height % _BLOCK_SIZE != 0:
        raise ValueError(
            f"Hauteur {src.height} invalide. Doit être multiple de {_BLOCK_SIZE} px pour A3 MV."
        )


def _is_block_empty(src: Image.Image, bx: int, by: int) -> bool:
    """Return True if the 96x96 block at (bx, by) mini-tile offset is all-transparent."""
    x0 = bx * _MINI
    y0 = by * _MINI
    crop = src.crop((x0, y0, x0 + _BLOCK_SIZE, y0 + _BLOCK_SIZE))
    # Check alpha channel — if all pixels are transparent, skip
    r, g, b, a = crop.split()
    return a.getextrema()[1] == 0


def _assemble_wall_tile(src: Image.Image, bx: int, by: int, shape: int) -> Image.Image:
    """
    Assemble one 48x48 tile from WALL_AUTOTILE_TABLE[shape].

    Args:
        src: Source RGBA image.
        bx: Block column in mini-tile units (each block = 2 mini-tiles wide).
        by: Block row in mini-tile units (each block = 2 mini-tiles tall).
        shape: Shape index 0-15 from WALL_AUTOTILE_TABLE.

    Returns:
        New 48x48 RGBA Image.
    """
    tile = Image.new("RGBA", (_TILE_SIZE, _TILE_SIZE))
    quads = WALL_AUTOTILE_TABLE[shape]

    # Quadrant positions in output: TL, TR, BL, BR
    dst_positions = [(0, 0), (_MINI, 0), (0, _MINI), (_MINI, _MINI)]

    for q, (dst_x, dst_y) in enumerate(dst_positions):
        qsx, qsy = quads[q]
        # Source coordinates: bx*2 because bx is already in mini-tile units
        # and each block is 2 mini-tiles wide, but bx already accounts for that.
        # The WALL table qsx/qsy reference within a 4x4 mini-tile grid per block.
        # Corescript formula: src_x = (bx + qsx) * MINI, but bx is block-relative
        # Actually bx = tx*2 and ty*2, so we apply qsx/qsy offset directly to bx/by:
        src_x = (bx + qsx) * _MINI
        src_y = (by + qsy) * _MINI
        crop = src.crop((src_x, src_y, src_x + _MINI, src_y + _MINI))
        tile.paste(crop, (dst_x, dst_y))

    return tile


def _build_wall_strip(src: Image.Image, bx: int, by: int) -> Image.Image:
    """
    Build a strip of 16 tiles (one per WALL_AUTOTILE_TABLE shape)
    for the block at (bx, by).

    Returns:
        New RGBA Image of size (768, 48).
    """
    strip = Image.new("RGBA", (_OUTPUT_WIDTH, _TILE_SIZE))
    for shape in range(_NUM_SHAPES):
        tile = _assemble_wall_tile(src, bx, by, shape)
        strip.paste(tile, (shape * _TILE_SIZE, 0))
    return strip
