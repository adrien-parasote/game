"""
asset_convertor.core.converter_mv

Convert a RPG Maker MV/MZ A2 autotile block to 47 Tiled blob tiles.

Input: single autotile block (2 cols x 3 rows of tiles).  # noqa: RUF002
  - 64x96 px  -> tile_size=32 (community pack format)
  - 96x144 px -> tile_size=48 (standard MV/MZ)

Spec: tools/docs/specs/autotile_converter_spec.md section converter_mv.py
Bitmask convention (same as converter_xp.py):
  NW=1, N=2, NE=4, W=8, E=16, SW=32, S=64, SE=128

Implementation note:
  Uses the official FLOOR_AUTOTILE_TABLE from the RPGMaker MV corescript
  (rpgtkoolmv/corescript, js/rpg_core/Tilemap.js).
  The table encodes, for each of the 48 autotile shapes (0-47), the 4 source
  mini-tile coordinates [qsx, qsy] that must be assembled as [TL, TR, BL, BR].
  Mini-tile coordinates reference a 4-column x 6-row grid where each cell is
  tile_size/2 pixels wide/tall:
    row 0: A_TL A_TR B_TL B_TR
    row 1: A_BL A_BR B_BL B_BR
    row 2: C_TL C_TR D_TL D_TR
    row 3: C_BL C_BR D_BL D_BR
    row 4: E_TL E_TR F_TL F_TR
    row 5: E_BL E_BR F_BL F_BR
"""

from __future__ import annotations

from asset_convertor.core.converter_xp import BLOB_BITMASKS
from PIL import Image

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Valid MV block dimensions -> detected tile size
_VALID_BLOCK_SIZES: dict[tuple[int, int], int] = {
    (64, 96): 32,    # 2 cols x 3 rows of 32px tiles
    (96, 144): 48,   # 2 cols x 3 rows of 48px tiles
}

# ---------------------------------------------------------------------------
# Official FLOOR_AUTOTILE_TABLE from RPGMaker MV corescript
# (rpgtkoolmv/corescript js/rpg_core/Tilemap.js, identical in all releases)
#
# Each entry: [[qsx_TL, qsy_TL], [qsx_TR, qsy_TR],
#              [qsx_BL, qsy_BL], [qsx_BR, qsy_BR]]
#
# qsx, qsy index the 4x6 mini-tile grid described in the module docstring.
# Convert to pixel coordinates: x = qsx * half, y = qsy * half
# where half = tile_size // 2.
# ---------------------------------------------------------------------------

_FLOOR_AUTOTILE_TABLE: list[list[list[int]]] = [
    [[2, 4], [1, 4], [2, 3], [1, 3]],  # shape  0
    [[2, 0], [1, 4], [2, 3], [1, 3]],  # shape  1
    [[2, 4], [3, 0], [2, 3], [1, 3]],  # shape  2
    [[2, 0], [3, 0], [2, 3], [1, 3]],  # shape  3
    [[2, 4], [1, 4], [2, 3], [3, 1]],  # shape  4
    [[2, 0], [1, 4], [2, 3], [3, 1]],  # shape  5
    [[2, 4], [3, 0], [2, 3], [3, 1]],  # shape  6
    [[2, 0], [3, 0], [2, 3], [3, 1]],  # shape  7
    [[2, 4], [1, 4], [2, 1], [1, 3]],  # shape  8
    [[2, 0], [1, 4], [2, 1], [1, 3]],  # shape  9
    [[2, 4], [3, 0], [2, 1], [1, 3]],  # shape 10
    [[2, 0], [3, 0], [2, 1], [1, 3]],  # shape 11
    [[2, 4], [1, 4], [2, 1], [3, 1]],  # shape 12
    [[2, 0], [1, 4], [2, 1], [3, 1]],  # shape 13
    [[2, 4], [3, 0], [2, 1], [3, 1]],  # shape 14
    [[2, 0], [3, 0], [2, 1], [3, 1]],  # shape 15
    [[0, 4], [1, 4], [0, 3], [1, 3]],  # shape 16
    [[0, 4], [3, 0], [0, 3], [1, 3]],  # shape 17
    [[0, 4], [1, 4], [0, 3], [3, 1]],  # shape 18
    [[0, 4], [3, 0], [0, 3], [3, 1]],  # shape 19
    [[2, 2], [1, 2], [2, 3], [1, 3]],  # shape 20
    [[2, 2], [1, 2], [2, 3], [3, 1]],  # shape 21
    [[2, 2], [1, 2], [2, 1], [1, 3]],  # shape 22
    [[2, 2], [1, 2], [2, 1], [3, 1]],  # shape 23
    [[2, 4], [3, 4], [2, 3], [3, 3]],  # shape 24
    [[2, 4], [3, 4], [2, 1], [3, 3]],  # shape 25
    [[2, 0], [3, 4], [2, 3], [3, 3]],  # shape 26
    [[2, 0], [3, 4], [2, 1], [3, 3]],  # shape 27
    [[2, 4], [1, 4], [2, 5], [1, 5]],  # shape 28
    [[2, 0], [1, 4], [2, 5], [1, 5]],  # shape 29
    [[2, 4], [3, 0], [2, 5], [1, 5]],  # shape 30
    [[2, 0], [3, 0], [2, 5], [1, 5]],  # shape 31
    [[0, 4], [3, 4], [0, 3], [3, 3]],  # shape 32
    [[2, 2], [1, 2], [2, 5], [1, 5]],  # shape 33
    [[0, 2], [1, 2], [0, 3], [1, 3]],  # shape 34
    [[0, 2], [1, 2], [0, 3], [3, 1]],  # shape 35  (unused)
    [[2, 2], [3, 2], [2, 3], [3, 3]],  # shape 36
    [[2, 2], [3, 2], [2, 1], [3, 3]],  # shape 37
    [[2, 4], [3, 4], [2, 5], [3, 5]],  # shape 38
    [[2, 0], [3, 4], [2, 5], [3, 5]],  # shape 39
    [[0, 4], [1, 4], [0, 5], [1, 5]],  # shape 40
    [[0, 4], [3, 0], [0, 5], [1, 5]],  # shape 41
    [[0, 2], [3, 2], [0, 3], [3, 3]],  # shape 42
    [[0, 2], [1, 2], [0, 5], [1, 5]],  # shape 43
    [[0, 4], [3, 4], [0, 5], [3, 5]],  # shape 44
    [[2, 2], [3, 2], [2, 5], [3, 5]],  # shape 45
    [[0, 2], [3, 2], [0, 5], [3, 5]],  # shape 46
    [[0, 0], [1, 0], [0, 1], [1, 1]],  # shape 47
]


# ---------------------------------------------------------------------------
# Bitmask → shape index
# ---------------------------------------------------------------------------

_SHAPE_RESOLVERS = [
    # 0: no cardinals
    lambda dn, de, ds, dw: 46,
    # 1: N only
    lambda dn, de, ds, dw: 44,
    # 2: S only
    lambda dn, de, ds, dw: 42,
    # 3: N+S
    lambda dn, de, ds, dw: 32,
    # 4: W only
    lambda dn, de, ds, dw: 45,
    # 5: N+W
    lambda dn, de, ds, dw: 38 if dn else 39,
    # 6: S+W
    lambda dn, de, ds, dw: 36 if dw else 37,
    # 7: N+S+W
    lambda dn, de, ds, dw: 27 - 2 * dn - 1 * dw,
    # 8: E only
    lambda dn, de, ds, dw: 43,
    # 9: N+E
    lambda dn, de, ds, dw: 40 if de else 41,
    # 10: S+E
    lambda dn, de, ds, dw: 34 if ds else 35,
    # 11: N+S+E
    lambda dn, de, ds, dw: 19 - 1 * de - 2 * ds,
    # 12: W+E
    lambda dn, de, ds, dw: 33,
    # 13: N+W+E
    lambda dn, de, ds, dw: 31 - 1 * dn - 2 * de,
    # 14: W+E+S
    lambda dn, de, ds, dw: 23 - 2 * dw - 1 * ds,
    # 15: N+S+W+E
    lambda dn, de, ds, dw: (0 if dn else 1) | (0 if de else 2) | (0 if ds else 4) | (0 if dw else 8)
]


def _bitmask_to_shape(bitmask: int) -> int:
    """
    Compute the RPGMaker MV autotile shape index (0-47) for a blob bitmask.

    Blob bitmask bit positions: NW=1, N=2, NE=4, W=8, E=16, SW=32, S=64, SE=128.
    Diagonal bits are only "effective" when both adjacent cardinal bits are set.

    Shape groups (corrected per FLOOR_AUTOTILE_TABLE specifications):
      0-15 : all 4 cardinals (N+S+W+E), 16 diagonal combinations
     16-19 : N+S+E, no W  — varying NE, SE
     20-23 : W+E+S, no N  — varying SW, SE
     24-27 : N+S+W, no E  — varying NW, SW
     28-31 : N+W+E, no S  — varying NW, NE
     32    : N+S only (vertical bar)
     33    : W+E only (horizontal bar)
     34-35 : S+E only (varying SE diagonal)
     36-37 : S+W only (varying SW diagonal)
     38-39 : N+W only (varying NW diagonal)
     40-41 : N+E only (varying NE diagonal)
     42    : S only
     43    : E only
     44    : N only
     45    : W only
     46    : isolated (no cardinal neighbours)
    """
    n  = bool(bitmask & 2)
    w  = bool(bitmask & 8)
    e  = bool(bitmask & 16)
    s  = bool(bitmask & 64)

    eff_nw = int(n and w and bool(bitmask & 1))
    eff_ne = int(n and e and bool(bitmask & 4))
    eff_sw = int(s and w and bool(bitmask & 32))
    eff_se = int(s and e and bool(bitmask & 128))

    ck = int(n) | (int(s) << 1) | (int(w) << 2) | (int(e) << 3)
    return _SHAPE_RESOLVERS[ck](eff_nw, eff_ne, eff_se, eff_sw)




# ---------------------------------------------------------------------------
# Quadrant extraction
# ---------------------------------------------------------------------------

def _get_quadrant(
    img: Image.Image,
    qsx: int,
    qsy: int,
    half: int,
) -> Image.Image:
    """
    Extract one (half x half) mini-tile from the source image.

    Args:
        img:  The full MV autotile block.
        qsx:  Column index in the 4-column mini-tile grid (0-3).
        qsy:  Row index in the 6-row mini-tile grid (0-5).
        half: Half of tile_size in pixels (mini-tile edge length).
    """
    x = qsx * half
    y = qsy * half
    return img.crop((x, y, x + half, y + half))


# ---------------------------------------------------------------------------
# Tile assembly
# ---------------------------------------------------------------------------

def _build_mv_tile(img: Image.Image, bitmask: int, tile_size: int) -> Image.Image:
    """
    Assemble one output tile from the MV autotile block using the bitmask.

    Args:
        img:       The MV autotile block (RGBA, already a copy).
        bitmask:   Blob bitmask (0..255, only the 47 valid values are used).
        tile_size: Source tile size: 32 or 48.

    Returns:
        RGBA PIL Image, tile_size x tile_size pixels.
        (Caller is responsible for downscaling 48→32 if required.)
    """
    shape = _bitmask_to_shape(bitmask)
    quads_qs = _FLOOR_AUTOTILE_TABLE[shape]  # [[qsx_TL,qsy_TL], …]

    half = tile_size // 2
    tile = Image.new("RGBA", (tile_size, tile_size))

    positions = [(0, 0), (half, 0), (0, half), (half, half)]  # TL, TR, BL, BR
    for (dx, dy), (qsx, qsy) in zip(positions, quads_qs, strict=True):
        quad = _get_quadrant(img, qsx, qsy, half)
        tile.paste(quad, (dx, dy))

    return tile


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def detect_tile_size(img: Image.Image) -> int:
    """
    Detect the tile size from the MV autotile block dimensions.

    Args:
        img: MV autotile block image.

    Returns:
        32 or 48 (tile size in pixels).

    Raises:
        ValueError: if block dimensions are not a recognized MV format.
    """
    size = (img.width, img.height)
    if size not in _VALID_BLOCK_SIZES:
        valid = ", ".join(f"{w}x{h}" for (w, h) in sorted(_VALID_BLOCK_SIZES.keys()))
        raise ValueError(
            f"Unrecognized MV autotile block dimensions {img.width}x{img.height}. "
            f"Expected one of: {valid}."
        )
    return _VALID_BLOCK_SIZES[size]


def convert_mv(img: Image.Image) -> list[Image.Image]:
    """
    Convert a MV/MZ A2 autotile block to 47 Tiled blob tiles.

    Auto-detects tile size from block dimensions:
      - 64x96  -> 32px tiles (output at native 32px)
      - 96x144 -> 48px tiles (output scaled down to 32px)

    Args:
        img: RGBA PIL Image (MV A2 autotile block).

    Returns:
        list of 47 RGBA PIL Images, each 32x32 px.
        Index i corresponds to BLOB_BITMASKS[i].

    Raises:
        ValueError: if img dimensions are not a recognized MV format.
    """
    tile_size = detect_tile_size(img)      # raises ValueError for unknown sizes

    src = img.copy().convert("RGBA")

    tiles = []
    for bitmask in BLOB_BITMASKS:
        tile = _build_mv_tile(src, bitmask, tile_size)
        if tile_size != 32:
            tile = tile.resize((32, 32), Image.NEAREST)
        tiles.append(tile)

    return tiles
