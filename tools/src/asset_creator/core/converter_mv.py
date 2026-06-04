"""
asset_creator.core.converter_mv

Convert a RPG Maker MV/MZ A2 autotile block to 47 Tiled blob tiles.

Input: single autotile block (2 cols x 3 rows of tiles).  # noqa: RUF002
  - 64x96 px  -> tile_size=32 (community pack format)
  - 96x144 px -> tile_size=48 (standard MV/MZ)

Spec: tools/docs/specs/autotile_converter_spec.md section converter_mv.py
Bitmask convention (same as converter_xp.py):
  NW=1, N=2, NE=4, W=8, E=16, SW=32, S=64, SE=128
"""

from __future__ import annotations

from asset_creator.core.converter_xp import BLOB_BITMASKS
from PIL import Image

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SUBTILE = 16  # quadrant size in pixels (half of a 32px tile)

# Valid MV block dimensions -> detected tile size
_VALID_BLOCK_SIZES: dict[tuple[int, int], int] = {
    (64, 96): 32,    # 2 cols x 3 rows of 32px tiles
    (96, 144): 48,   # 2 cols x 3 rows of 48px tiles
}

# ---------------------------------------------------------------------------
# MV A2 block layout (2 columns x 3 rows of tile_size x tile_size tiles)
# ---------------------------------------------------------------------------
#
# Tile positions (col, row) within the 2x3 block:
#
#   (0,0)=A  (1,0)=B
#   (0,1)=C  (1,1)=D
#   (0,2)=E  (1,2)=F
#
# Standard RPGMaker MV A2 sub-tile mapping (using 16x16 or 24x24 quadrants):
#
# Each 32/48px tile has 4 quadrants: TL, TR, BL, BR (each = tile_size/2 px)
#
# The 6 source tiles encode the following shapes:
#   A (0,0): outer corner pieces (used when isolated or edge-only)
#   B (1,0): center/inner-fill pieces -- the "fully surrounded" interior
#   C (0,1): bottom-left connection
#   D (1,1): bottom-right connection
#   E (0,2): top-left / left-wall connections
#   F (1,2): top-right / right-wall connections
#
# Verified against community implementations (Leafo, RPGMakerWeb forum posts,
# and visual inspection of sample_mv_32px.png sub-tile color distribution).


def _get_quadrant(
    img: Image.Image,
    tile_col: int,
    tile_row: int,
    quad_col: int,
    quad_row: int,
    tile_size: int,
) -> Image.Image:
    """
    Extract one (tile_size/2 x tile_size/2) quadrant from a tile in the MV block.

    Args:
        img: The full MV autotile block image.
        tile_col, tile_row: Position of the 32/48px tile within the 2x3 grid.
        quad_col, quad_row: Position of the quadrant within the tile (0 or 1).
        tile_size: 32 or 48 (size of each tile in the block).
    """
    half = tile_size // 2
    x = tile_col * tile_size + quad_col * half
    y = tile_row * tile_size + quad_row * half
    return img.crop((x, y, x + half, y + half))


# ---------------------------------------------------------------------------
# Quadrant-selection helpers
# Each returns (tile_col, tile_row, quad_col, quad_row) for _get_quadrant
# ---------------------------------------------------------------------------

def _pick_tl(n: bool, w: bool, nw: bool, iso: bool) -> tuple[int, int, int, int]:
    """Select source quadrant for the top-left corner of an output tile."""
    if n and w and nw:
        return (1, 0, 0, 0)   # inner fill — tile B TL
    if n:
        return (0, 2, 1, 0)   # N edge — tile E TR
    if w:
        return (0, 1, 0, 0)   # W edge — tile C TL
    return (0, 0, 0, 0)       # outer corner — tile A TL (isolated or N+W no diag)


def _pick_tr(n: bool, e: bool, ne: bool, iso: bool) -> tuple[int, int, int, int]:
    """Select source quadrant for the top-right corner of an output tile."""
    if n and e and ne:
        return (1, 0, 1, 0)   # inner fill — tile B TR
    if n:
        return (1, 2, 0, 0)   # N edge — tile F TL
    if e:
        return (1, 1, 1, 0)   # E edge — tile D TR
    return (0, 0, 1, 0)       # outer corner — tile A TR


def _pick_bl(s: bool, w: bool, sw: bool, iso: bool) -> tuple[int, int, int, int]:
    """Select source quadrant for the bottom-left corner of an output tile."""
    if s and w and sw:
        return (1, 0, 0, 1)   # inner fill — tile B BL
    if s:
        return (0, 2, 1, 1)   # S edge — tile E BR
    if w:
        return (0, 1, 0, 1)   # W edge — tile C BL
    return (0, 0, 0, 1)       # outer corner — tile A BL


def _pick_br(s: bool, e: bool, se: bool, iso: bool) -> tuple[int, int, int, int]:
    """Select source quadrant for the bottom-right corner of an output tile."""
    if s and e and se:
        return (1, 0, 1, 1)   # inner fill — tile B BR
    if s:
        return (1, 2, 0, 1)   # S edge — tile F BL
    if e:
        return (1, 1, 1, 1)   # E edge — tile D BR
    return (0, 0, 1, 1)       # outer corner — tile A BR


def _build_mv_tile(img: Image.Image, bitmask: int, tile_size: int) -> Image.Image:
    """
    Assemble one output tile from the MV autotile block using the bitmask.

    Args:
        img: The MV autotile block (RGBA, already a copy).
        bitmask: Blob bitmask (0..255, only 47 valid values used).
        tile_size: 32 or 48 (from detect_tile_size).

    Returns:
        RGBA PIL Image of size 32x32.
    """
    nw = bool(bitmask & 1)
    n = bool(bitmask & 2)
    ne = bool(bitmask & 4)
    w = bool(bitmask & 8)
    e = bool(bitmask & 16)
    sw = bool(bitmask & 32)
    s = bool(bitmask & 64)
    se = bool(bitmask & 128)
    iso = not (n or s or w or e)

    half = tile_size // 2
    tile = Image.new("RGBA", (tile_size, tile_size))

    def paste(dx: int, dy: int, src: tuple[int, int, int, int]) -> None:
        quad = _get_quadrant(img, src[0], src[1], src[2], src[3], tile_size)
        tile.paste(quad, (dx, dy))

    paste(0,    0,    _pick_tl(n, w, nw, iso))
    paste(half, 0,    _pick_tr(n, e, ne, iso))
    paste(0,    half, _pick_bl(s, w, sw, iso))
    paste(half, half, _pick_br(s, e, se, iso))

    if tile_size != 32:
        return tile.resize((32, 32), Image.NEAREST)
    return tile


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
      - 64x96  -> 32px tiles
      - 96x144 -> 48px tiles (output scaled to 32px)

    Args:
        img: RGBA PIL Image (MV A2 autotile block).

    Returns:
        list of 47 RGBA PIL Images, each 32x32 px.
        Index i corresponds to BLOB_BITMASKS[i].

    Raises:
        ValueError: if img dimensions are not a recognized MV format.
    """
    tile_size = detect_tile_size(img)  # raises ValueError for unknown sizes

    # Work on a copy to avoid mutating the source
    src = img.copy().convert("RGBA")

    return [_build_mv_tile(src, bitmask, tile_size) for bitmask in BLOB_BITMASKS]
