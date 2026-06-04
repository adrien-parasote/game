"""
asset_creator.core.converter_xp

Convert a RPG Maker XP autotile (96x128 RGBA) to 47 Tiled blob tiles.

Spec: tools/docs/specs/autotile_converter_spec.md § converter_xp.py
Bitmask convention (same as rpgmaker_blob_autotile_to_tiled.py):
  NW=1, N=2, NE=4, W=8, E=16, SW=32, S=64, SE=128
"""

from __future__ import annotations

from PIL import Image

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SUBTILE = 16
TILE_SIZE = 32
FRAME_W = 96
FRAME_H = 128

# 47 valid blob bitmasks in output sheet order.
# Convention: NW=1, N=2, NE=4, W=8, E=16, SW=32, S=64, SE=128
# Rule: diagonal bit is only 1 when BOTH adjacent cardinals are 1.
BLOB_BITMASKS: tuple[int, ...] = (
    0, 2, 8, 10, 11, 16, 18, 22, 24, 26, 27, 30, 31,
    64, 66, 72, 74, 75, 80, 82, 86, 88, 90, 91, 94, 95,
    104, 106, 107, 120, 122, 123, 126, 127,
    208, 210, 214, 216, 218, 219, 222, 223,
    248, 250, 251, 254, 255,
)  # exactly 47

assert len(BLOB_BITMASKS) == 47, "BLOB_BITMASKS must have exactly 47 entries"

# ---------------------------------------------------------------------------
# RPG Maker XP sub-tile grid layout
# ---------------------------------------------------------------------------
#
# Source autotile: 96x128 px = 6 cols x 8 rows of 16x16 sub-tiles.
#
#  Col  0   1   2   3   4   5
# Row 0 A-TL A-TR X-TL X-TR B-TL B-TR    A=isolated, X=absence-de-surface, B=inner-corner
# Row 1 A-BL A-BR X-BL X-BR B-BL B-BR
# Row 2 D-TL D-TR E-TL E-TR F-TL F-TR    D=top-left, E=top-edge, F=top-right
# Row 3 D-BL D-BR E-BL E-BR F-BL F-BR
# Row 4 G-TL G-TR H-TL H-TR I-TL I-TR    G=left, H=center, I=right
# Row 5 G-BL G-BR H-BL H-BR I-BL I-BR
# Row 6 J-TL J-TR K-TL K-TR L-TL L-TR    J=bot-left, K=bot-edge, L=bot-right
# Row 7 J-BL J-BR K-BL K-BR L-BL L-BR
#
# B tile (col 4-5, row 0-1) = virages internes (inner-corner pieces, 16x16 each):
#   B-TL (4,0): used when NW missing  (N+W present but NW=0)
#   B-TR (5,0): used when NE missing
#   B-BL (4,1): used when SW missing
#   B-BR (5,1): used when SE missing
# X tile (col 2-3, row 0-1) = "absence de surface" (background when no autotile placed)


def _extract_subtile(img: Image.Image, col: int, row: int) -> Image.Image:
    """Crop one 16x16 sub-tile at (col*16, row*16) from the source image."""
    x, y = col * SUBTILE, row * SUBTILE
    return img.crop((x, y, x + SUBTILE, y + SUBTILE))


def _assemble_tile(
    subtiles: dict[str, Image.Image],
    quadrants: tuple[str, str, str, str],
) -> Image.Image:
    """
    Build a 32x32 tile from 4 named 16x16 sub-tiles.

    Args:
        subtiles: dict mapping name → 16x16 PIL Image
        quadrants: (top_left, top_right, bottom_left, bottom_right) sub-tile names
    """
    tile = Image.new("RGBA", (TILE_SIZE, TILE_SIZE))
    tl_name, tr_name, bl_name, br_name = quadrants
    tile.paste(subtiles[tl_name], (0, 0))
    tile.paste(subtiles[tr_name], (SUBTILE, 0))
    tile.paste(subtiles[bl_name], (0, SUBTILE))
    tile.paste(subtiles[br_name], (SUBTILE, SUBTILE))
    return tile


def _quarter_tl(c1: bool, c2: bool, diag: bool, iso: bool) -> tuple[int, int]:
    """Return (col, row) of 16x16 sub-tile for top-left quadrant."""
    if c1 and c2:
        return (2, 4) if diag else (4, 0)  # B-TL: inner corner NW missing
    if c1:
        return (0, 4)
    if c2:
        return (2, 2)
    return (0, 0) if iso else (0, 2)


def _quarter_tr(c1: bool, c2: bool, diag: bool, iso: bool) -> tuple[int, int]:
    """Return (col, row) of 16x16 sub-tile for top-right quadrant."""
    if c1 and c2:
        return (3, 4) if diag else (5, 0)  # B-TR: inner corner NE missing
    if c1:
        return (5, 4)
    if c2:
        return (3, 2)
    return (1, 0) if iso else (5, 2)


def _quarter_bl(c1: bool, c2: bool, diag: bool, iso: bool) -> tuple[int, int]:
    """Return (col, row) of 16x16 sub-tile for bottom-left quadrant."""
    if c1 and c2:
        return (2, 5) if diag else (4, 1)  # B-BL: inner corner SW missing
    if c1:
        return (0, 5)
    if c2:
        return (2, 7)
    return (0, 1) if iso else (0, 7)


def _quarter_br(c1: bool, c2: bool, diag: bool, iso: bool) -> tuple[int, int]:
    """Return (col, row) of 16x16 sub-tile for bottom-right quadrant."""
    if c1 and c2:
        return (3, 5) if diag else (5, 1)  # B-BR: inner corner SE missing
    if c1:
        return (5, 5)
    if c2:
        return (3, 7)
    return (1, 1) if iso else (5, 7)


def _build_tile_from_bitmask(src: Image.Image, bitmask: int) -> Image.Image:
    """
    Assemble one 32x32 tile from the 8-neighbor bitmask by sampling
    the correct 16x16 quadrants from the source image.
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

    tile = Image.new("RGBA", (TILE_SIZE, TILE_SIZE))

    # Each quadrant: (corner, vertical_cardinal, horizontal_cardinal, diagonal, dx, dy)
    for corner_fn, c1, c2, diag, dx, dy in (
        (_quarter_tl, n, w, nw, 0, 0),
        (_quarter_tr, n, e, ne, SUBTILE, 0),
        (_quarter_bl, s, w, sw, 0, SUBTILE),
        (_quarter_br, s, e, se, SUBTILE, SUBTILE),
    ):
        col, row = corner_fn(c1, c2, diag, iso)
        tile.paste(_extract_subtile(src, col, row), (dx, dy))

    return tile


def convert_xp(img: Image.Image) -> list[Image.Image]:
    """
    Convert a 96x128 RPG Maker XP autotile to 47 Tiled blob tiles.

    Args:
        img: RGBA PIL Image, must be 96x128 px.

    Returns:
        list of 47 RGBA PIL Images, each 32x32 px.
        Index i corresponds to BLOB_BITMASKS[i].

    Raises:
        ValueError: if img dimensions are not 96x128.
    """
    if img.width != FRAME_W or img.height != FRAME_H:
        raise ValueError(
            f"Expected XP autotile 96x128 px, got {img.width}x{img.height}."
        )

    # Work on a copy to avoid mutating the source
    src = img.copy().convert("RGBA")

    return [_build_tile_from_bitmask(src, bitmask) for bitmask in BLOB_BITMASKS]
