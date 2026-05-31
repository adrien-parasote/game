"""Tile assembler for blob terrain tiles.

Assembles 47 blob tiles (32×32) from a SubTileSet by decoding bitmasks
and selecting the appropriate sub-tile for each quadrant.

Bitmask layout: NW=1, N=2, NE=4, W=8, E=16, SW=32, S=64, SE=128.
Wang ID order (Tiled): Top, TopRight, Right, BottomRight, Bottom,
                       BottomLeft, Left, TopLeft (L-MAP-002).
"""
from __future__ import annotations

from PIL import Image

from tools.asset_creator.core.constants import (
    BLOB_BITMASKS,
    NUM_BLOB_TILES,
    SUBTILE_SIZE,
    TILE_SIZE,
)
from tools.asset_creator.core.subtile import Quadrant, SubTileSet, SubTileType

# ---------------------------------------------------------------------------
# Sub-tile selection
# ---------------------------------------------------------------------------

def select_subtile(
    subtile_set: SubTileSet,
    quadrant: Quadrant,
    cardinal_1: bool,
    cardinal_2: bool,
    diagonal: bool,
) -> Image.Image:
    """Select the right sub-tile for a quadrant based on neighbor state.

    Args:
        subtile_set: The set of 20 sub-tiles to choose from.
        quadrant: Which quadrant (TL, TR, BL, BR) this sub-tile occupies.
        cardinal_1: Whether the vertical neighbor exists (N for TL/TR, S for BL/BR).
        cardinal_2: Whether the horizontal neighbor exists (W for TL/BL, E for TR/BR).
        diagonal: Whether the diagonal neighbor exists (NW, NE, SW, SE).

    Returns:
        The selected 16×16 sub-tile image.
    """
    if cardinal_1 and cardinal_2:
        tile_type = SubTileType.FILL if diagonal else SubTileType.INNER_CORNER
        return subtile_set.get(quadrant, tile_type)
    if cardinal_1:
        return subtile_set.get(quadrant, SubTileType.EDGE_V)
    if cardinal_2:
        return subtile_set.get(quadrant, SubTileType.EDGE_H)
    return subtile_set.get(quadrant, SubTileType.OUTER_CORNER)


# ---------------------------------------------------------------------------
# Bitmask decoding
# ---------------------------------------------------------------------------

def _decode_bitmask(bitmask: int) -> dict[str, bool]:
    """Decode a bitmask into neighbor flags.

    Layout: NW=1, N=2, NE=4, W=8, E=16, SW=32, S=64, SE=128.
    """
    return {
        "nw": bool(bitmask & 1),
        "n": bool(bitmask & 2),
        "ne": bool(bitmask & 4),
        "w": bool(bitmask & 8),
        "e": bool(bitmask & 16),
        "sw": bool(bitmask & 32),
        "s": bool(bitmask & 64),
        "se": bool(bitmask & 128),
    }


# ---------------------------------------------------------------------------
# Tile assembly
# ---------------------------------------------------------------------------

def assemble_tile(subtile_set: SubTileSet, bitmask: int) -> Image.Image:
    """Assemble one 32×32 tile from the sub-tile set based on bitmask.

    Each tile is composed of 4 quadrants (16×16 each):
    - TL at (0,0): vertical=N, horizontal=W, diagonal=NW
    - TR at (16,0): vertical=N, horizontal=E, diagonal=NE
    - BL at (0,16): vertical=S, horizontal=W, diagonal=SW
    - BR at (16,16): vertical=S, horizontal=E, diagonal=SE

    Args:
        subtile_set: The set of 20 sub-tiles to compose from.
        bitmask: 8-bit neighbor bitmask.

    Returns:
        A 32×32 RGBA tile image.
    """
    neighbors = _decode_bitmask(bitmask)

    tile = Image.new("RGBA", (TILE_SIZE, TILE_SIZE))

    # TL quadrant at (0,0): vertical=N, horizontal=W, diagonal=NW
    tl = select_subtile(
        subtile_set, Quadrant.TL,
        neighbors["n"], neighbors["w"], neighbors["nw"],
    )
    tile.paste(tl, (0, 0))

    # TR quadrant at (SUBTILE_SIZE,0): vertical=N, horizontal=E, diagonal=NE
    tr = select_subtile(
        subtile_set, Quadrant.TR,
        neighbors["n"], neighbors["e"], neighbors["ne"],
    )
    tile.paste(tr, (SUBTILE_SIZE, 0))

    # BL quadrant at (0,SUBTILE_SIZE): vertical=S, horizontal=W, diagonal=SW
    bl = select_subtile(
        subtile_set, Quadrant.BL,
        neighbors["s"], neighbors["w"], neighbors["sw"],
    )
    tile.paste(bl, (0, SUBTILE_SIZE))

    # BR quadrant at (SUBTILE_SIZE,SUBTILE_SIZE): vertical=S, horizontal=E, diagonal=SE
    br = select_subtile(
        subtile_set, Quadrant.BR,
        neighbors["s"], neighbors["e"], neighbors["se"],
    )
    tile.paste(br, (SUBTILE_SIZE, SUBTILE_SIZE))

    return tile


def assemble_tileset(subtile_set: SubTileSet) -> Image.Image:
    """Assemble the complete 47-tile horizontal strip.

    Args:
        subtile_set: The set of 20 sub-tiles to compose from.

    Returns:
        A (47×32, 32) RGBA strip image containing all blob tiles.
    """
    strip = Image.new("RGBA", (NUM_BLOB_TILES * TILE_SIZE, TILE_SIZE))
    for idx, bitmask in enumerate(BLOB_BITMASKS):
        tile = assemble_tile(subtile_set, bitmask)
        strip.paste(tile, (idx * TILE_SIZE, 0))
    return strip


# ---------------------------------------------------------------------------
# Wang ID generation
# ---------------------------------------------------------------------------

def blob_wang_id(bitmask: int) -> str:
    """Convert a bitmask to Tiled mixed-Wang wangid string.

    Order: Top, TopRight, Right, BottomRight, Bottom, BottomLeft, Left, TopLeft
    (L-MAP-002).

    Bit layout: NW=1, N=2, NE=4, W=8, E=16, SW=32, S=64, SE=128.

    Args:
        bitmask: 8-bit neighbor bitmask.

    Returns:
        Comma-separated string of 8 values (0 or 1).
    """
    n = (bitmask >> 1) & 1
    ne = (bitmask >> 2) & 1
    e = (bitmask >> 4) & 1
    se = (bitmask >> 7) & 1
    s = (bitmask >> 6) & 1
    sw = (bitmask >> 5) & 1
    w = (bitmask >> 3) & 1
    nw = (bitmask >> 0) & 1
    return f"{n},{ne},{e},{se},{s},{sw},{w},{nw}"
