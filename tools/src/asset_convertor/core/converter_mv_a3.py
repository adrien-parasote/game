"""
asset_convertor.core.converter_mv_a3

Convert an RPG Maker MV A3 (Building/Roof) source tileset to a
Tiled-compatible tileset strip.

Source format:
  - 48px tiles: 768×384 px (full sheet), block=96×96 px, mini=24 px
  - 32px tiles: 512×256 px (full sheet), block=64×64 px, mini=16 px
  - 8 columns × 4 rows of autotile blocks.
  - Each block encodes one autotile kind using WALL_AUTOTILE_TABLE (16 shapes).

Output format:
  - 48px: 768 px wide (16 × 48), height = N_kinds × 48 px
  - 32px: 512 px wide (16 × 32), height = N_kinds × 32 px
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
# Valid A3 source block sizes → detected tile size
# An A3 block = 4 mini-tiles wide = 2 × tile_size
# ---------------------------------------------------------------------------

_VALID_BLOCK_SIZES_A3: dict[int, int] = {
    64: 32,   # 4 mini-tiles × 16px = 64px  (32px tileset)
    96: 48,   # 4 mini-tiles × 24px = 96px  (48px tileset)
}

_NUM_SHAPES = 16   # WALL_AUTOTILE_TABLE entries
_BLOCK_COLS = 8    # A3 sheet: 8 columns of blocks
_BLOCK_ROWS = 4    # A3 sheet: 4 rows of blocks


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def convert_mv_a3(img: Image.Image) -> Image.Image:
    """
    Convert an RPG Maker MV A3 (Building/Roof) source tileset
    to a Tiled-compatible tileset strip.

    Supports both 32px and 48px tile sizes:
      - 32px: source block = 64×64 px
      - 48px: source block = 96×96 px

    Args:
        img: PIL Image, source A3 PNG (RGBA or RGB).
             Width must be a multiple of 64 (32px) or 96 (48px).
             Minimum: one full block square.

    Returns:
        PIL Image: Output tileset strip, RGBA.
            width  = 16 × tile_size
            height = N_kinds × tile_size

    Raises:
        ValueError: If img width is not a multiple of 64 or 96.
        ValueError: If img dimensions are too small for the detected tile size.
        ValueError: If no valid autotile blocks are found.
    """
    src = img.convert("RGBA")
    tile_size, mini, block_size = _detect_a3_geometry(src)

    output_width = _NUM_SHAPES * tile_size

    n_cols = min(src.width // block_size, _BLOCK_COLS)
    n_rows = src.height // block_size

    kind_rows: list[Image.Image] = []

    for ty in range(n_rows):
        for tx in range(n_cols):
            bx = tx * 2   # block column in mini-tile units
            by = ty * 2   # block row in mini-tile units

            if _is_block_empty(src, bx, by, mini, block_size):
                continue

            row_img = _build_wall_strip(src, bx, by, tile_size, mini, output_width)
            kind_rows.append(row_img)

    if not kind_rows:
        raise ValueError(
            "Aucun bloc valide détecté. Le fichier est-il bien un A3 MV ?"
        )

    output = Image.new("RGBA", (output_width, tile_size * len(kind_rows)))
    for idx, row_img in enumerate(kind_rows):
        output.paste(row_img, (0, idx * tile_size))

    return output


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _detect_a3_geometry(src: Image.Image) -> tuple[int, int, int]:
    """
    Detect tile_size from source width and return geometry tuple.

    Returns:
        (tile_size, mini, block_size)

    Raises:
        ValueError: If source width is not a recognized A3 block size multiple,
                    or if dimensions are too small.
    """
    detected_tile_size: int | None = None
    detected_block_size: int | None = None

    for block_size, tile_size in _VALID_BLOCK_SIZES_A3.items():
        if src.width >= block_size and src.width % block_size == 0:
            detected_tile_size = tile_size
            detected_block_size = block_size
            break

    if detected_tile_size is None or detected_block_size is None:
        valid = ", ".join(
            f"{bs}px (tile={ts}px)" for bs, ts in sorted(_VALID_BLOCK_SIZES_A3.items())
        )
        raise ValueError(
            f"Largeur source A3 invalide: {src.width}px. "
            f"Doit être multiple d'un block_size valide: {valid}."
        )

    if src.height < detected_block_size:
        raise ValueError(
            f"Image trop petite: {src.size}. "
            f"Minimum {detected_block_size}×{detected_block_size} px pour A3 {detected_tile_size}px."
        )

    mini = detected_tile_size // 2
    return detected_tile_size, mini, detected_block_size


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


def _assemble_wall_tile(
    src: Image.Image, bx: int, by: int, shape: int, tile_size: int, mini: int
) -> Image.Image:
    """
    Assemble one tile_size×tile_size tile from WALL_AUTOTILE_TABLE[shape].

    Args:
        src: Source RGBA image.
        bx: Block column in mini-tile units (bx = tx * 2).
        by: Block row in mini-tile units (by = ty * 2).
        shape: Shape index 0-15 from WALL_AUTOTILE_TABLE.
        tile_size: Output tile size in pixels (32 or 48).
        mini: Half of tile_size (mini-tile edge length).

    Returns:
        New tile_size×tile_size RGBA Image.
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


def _build_wall_strip(
    src: Image.Image, bx: int, by: int,
    tile_size: int, mini: int, output_width: int,
) -> Image.Image:
    """
    Build a strip of 16 tiles (one per WALL_AUTOTILE_TABLE shape)
    for the block at (bx, by).

    Returns:
        New RGBA Image of size (output_width, tile_size).
    """
    strip = Image.new("RGBA", (output_width, tile_size))
    for shape in range(_NUM_SHAPES):
        tile = _assemble_wall_tile(src, bx, by, shape, tile_size, mini)
        strip.paste(tile, (shape * tile_size, 0))
    return strip
