"""Tile assembler for blob terrain tiles.

Assembles 47 blob tiles (32×32) from a SubTileSet by decoding bitmasks
and selecting the appropriate sub-tile for each quadrant.

Bitmask layout: NW=1, N=2, NE=4, W=8, E=16, SW=32, S=64, SE=128.
Wang ID order (Tiled): Top, TopRight, Right, BottomRight, Bottom,
                       BottomLeft, Left, TopLeft (L-MAP-002).
"""
from __future__ import annotations

from PIL import Image

from tools.asset_creator.core.subtile import Quadrant, SubTileSet, SubTileType

# ---------------------------------------------------------------------------
# Blob bitmask table (47 unique blob configurations)
# ---------------------------------------------------------------------------

BLOB_BITMASKS: tuple[int, ...] = (
    0, 2, 8, 10, 11, 16, 18, 22, 24, 26, 27, 30, 31,
    64, 66, 72, 74, 75, 80, 82, 86, 88, 90, 91, 94, 95,
    104, 106, 107, 120, 122, 123, 126, 127,
    208, 210, 214, 216, 218, 219, 222, 223,
    248, 250, 251, 254, 255,
)


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

    tile = Image.new("RGBA", (32, 32))

    # TL quadrant at (0,0): vertical=N, horizontal=W, diagonal=NW
    tl = select_subtile(
        subtile_set, Quadrant.TL,
        neighbors["n"], neighbors["w"], neighbors["nw"],
    )
    tile.paste(tl, (0, 0))

    # TR quadrant at (16,0): vertical=N, horizontal=E, diagonal=NE
    tr = select_subtile(
        subtile_set, Quadrant.TR,
        neighbors["n"], neighbors["e"], neighbors["ne"],
    )
    tile.paste(tr, (16, 0))

    # BL quadrant at (0,16): vertical=S, horizontal=W, diagonal=SW
    bl = select_subtile(
        subtile_set, Quadrant.BL,
        neighbors["s"], neighbors["w"], neighbors["sw"],
    )
    tile.paste(bl, (0, 16))

    # BR quadrant at (16,16): vertical=S, horizontal=E, diagonal=SE
    br = select_subtile(
        subtile_set, Quadrant.BR,
        neighbors["s"], neighbors["e"], neighbors["se"],
    )
    tile.paste(br, (16, 16))

    return tile


def assemble_tileset(subtile_set: SubTileSet) -> Image.Image:
    """Assemble the complete 47-tile horizontal strip.

    Args:
        subtile_set: The set of 20 sub-tiles to compose from.

    Returns:
        A (47×32, 32) RGBA strip image containing all blob tiles.
    """
    strip = Image.new("RGBA", (47 * 32, 32))
    for idx, bitmask in enumerate(BLOB_BITMASKS):
        tile = assemble_tile(subtile_set, bitmask)
        strip.paste(tile, (idx * 32, 0))
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
