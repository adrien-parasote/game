"""
Convert a RPG Maker XP autotile PNG to a Tiled-compatible tileset.

RPG Maker XP autotile layout (96×128, tiles are 32×32):
  - Divided into 6 columns × 8 rows of 16×16 half-tiles
  - Each of the 16 Wang edge combinations is assembled from 4 half-tiles

Outputs:
  - <name>_tiled.png : strip of 16 tiles (32×32 each → 512×32)
  - <name>_tiled.tsx : Tiled tileset XML with Wang data pre-configured

Usage:
    python3 scripts/rpgmaker_autotile_to_tiled.py <input.png> [output_stem]

Output stem defaults to <input_dir>/<input_stem>_tiled
"""

import sys
import os
import xml.etree.ElementTree as ET
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    sys.exit("ERROR: Pillow is required. Run: pip install pillow")

TILED_VERSION = "1.10.0"
WANG_COLOR = "#55aa00"

TILE_SIZE = 32
HALF = TILE_SIZE // 2  # 16 px — each tile assembled from 2×2 half-tiles
TILE_COUNT = 16

# ── Half-tile source positions (col, row) in the 16×16 half-tile grid ────────
# Autotile 3×4 grid of 32×32 tiles (= 6×8 grid of 16×16 half-tiles):
#   A(0,0) isolated   B(1,0) inner-corners  C(2,0) variant
#   D(0,1) left edge  E(1,1) top edge       F(2,1) right edge
#   G(0,2) left edge  H(1,2) CENTER (full)  I(2,2) right edge
#   J(0,3) bot-left   K(1,3) bottom edge    L(2,3) bot-right
# fmt: off
_Q = {
    # CENTER of the big block -> cols 2-3, rows 4-5
    "inn_tl": (2, 4), "inn_tr": (3, 4), "inn_bl": (2, 5), "inn_br": (3, 5),
    
    # TOP EDGE (straight top, connects L/R) -> cols 2-3, row 2
    "top_tl": (2, 2), "top_tr": (3, 2),
    
    # BOTTOM EDGE (straight bottom, connects L/R) -> cols 2-3, row 7
    # Note: Row 7 contains the grass "feet", which is required for a bottom border
    "bot_bl": (2, 7), "bot_br": (3, 7),
    
    # LEFT EDGE (straight left, connects T/B) -> col 0, rows 4-5
    "lft_tl": (0, 4), "lft_bl": (0, 5),
    
    # RIGHT EDGE (straight right, connects T/B) -> col 5, rows 4-5
    "rgt_tr": (5, 4), "rgt_br": (5, 5),
    
    # ISOLATED tile A -> cols 0-1, rows 0-1
    "out_tl": (0, 0), "out_tr": (1, 0), "out_bl": (0, 1), "out_br": (1, 1),
    
    # CONVEX CORNERS (outer corners directly from the big block)
    "cvx_tl": (0, 2), "cvx_tr": (5, 2), "cvx_bl": (0, 7), "cvx_br": (5, 7),
}
# fmt: on


def _half_tile(src: Image.Image, col: int, row: int) -> Image.Image:
    """Crop a 16×16 half-tile from source at grid position (col, row)."""
    x, y = col * HALF, row * HALF
    return src.crop((x, y, x + HALF, y + HALF))


def _quarter_source(top: bool, right: bool, bottom: bool, left: bool, corner: str) -> tuple[int, int]:
    """Return the half-tile source (col, row) for one corner of a tile.

    Key names in _Q refer to the SOURCE tile, not the destination corner:
      - "inn_*" = center tile H (both edges present)
      - "top_*" = top-edge tile E (only top neighbour present)
      - "bot_*" = bottom-edge tile K (only bottom neighbour present)
      - "lft_*" = left-edge tile D/G (only left neighbour present)
      - "rgt_*" = right-edge tile F/I (only right neighbour present)
      - "out_*" = isolated tile A (no neighbours, mask=0)
      - "cvx_*" = convex corner tile B (no neighbours for this corner, but others connect)
    """
    mask_zero = not (top or right or bottom or left)

    if corner == "tl":
        if top and left: return _Q["inn_tl"]
        if top:          return _Q["lft_tl"]   # left=border, top connects
        if left:         return _Q["top_tl"]   # top=border, left connects
        return _Q["out_tl"] if mask_zero else _Q["cvx_tl"]

    if corner == "tr":
        if top and right: return _Q["inn_tr"]
        if top:           return _Q["rgt_tr"]   # right=border, top connects
        if right:         return _Q["top_tr"]   # top=border, right connects
        return _Q["out_tr"] if mask_zero else _Q["cvx_tr"]

    if corner == "bl":
        if bottom and left: return _Q["inn_bl"]
        if bottom:          return _Q["lft_bl"]  # left=border, bottom connects
        if left:            return _Q["bot_bl"]  # bottom=border, left connects
        return _Q["out_bl"] if mask_zero else _Q["cvx_bl"]

    if corner == "br":
        if bottom and right: return _Q["inn_br"]
        if bottom:           return _Q["rgt_br"]  # right=border, bottom connects
        if right:            return _Q["bot_br"]  # bottom=border, right connects
        return _Q["out_br"] if mask_zero else _Q["cvx_br"]

    raise ValueError(f"Unknown corner: {corner!r}. Expected one of: tl, tr, bl, br.")


def _build_tile(src: Image.Image, mask: int) -> Image.Image:
    """Compose one 32×32 tile from the autotile source using a 4-bit edge mask.

    Bit mask: bit0=Top, bit1=Right, bit2=Bottom, bit3=Left (1 = neighbour present).
    """
    top = bool(mask & 1)
    right = bool(mask & 2)
    bottom = bool(mask & 4)
    left = bool(mask & 8)

    tile = Image.new("RGBA", (TILE_SIZE, TILE_SIZE))

    for corner, dx, dy in [("tl", 0, 0), ("tr", HALF, 0), ("bl", 0, HALF), ("br", HALF, HALF)]:
        col, row = _quarter_source(top, right, bottom, left, corner)
        tile.paste(_half_tile(src, col, row), (dx, dy))

    return tile


def _wang_id(mask: int) -> str:
    """Compute Tiled wangid string for a 4-bit edge mask (Edge-only format).

    Tiled Edge Wang format (8 values):
        T, 0, R, 0, B, 0, L, 0
    (Corners are set to 0 as we only use edge-based matching for 16 tiles).
    """
    t = int(bool(mask & 1))
    r = int(bool(mask & 2))
    b = int(bool(mask & 4))
    l = int(bool(mask & 8))

    return f"{t},0,{r},0,{b},0,{l},0"


def _generate_tsx(png_path: Path, tsx_path: Path, name: str) -> None:
    """Write a Tiled TSX file with Wang terrain data (Edge-only)."""
    rel_png_path = os.path.relpath(png_path, tsx_path.parent)

    root = ET.Element("tileset", {
        "version": "1.10",
        "tiledversion": TILED_VERSION,
        "name": name,
        "tilewidth": str(TILE_SIZE),
        "tileheight": str(TILE_SIZE),
        "spacing": "0",
        "margin": "0",
        "tilecount": str(TILE_COUNT),
        "columns": str(TILE_COUNT),
    })

    ET.SubElement(root, "image", {
        "source": rel_png_path,
        "width": str(TILE_SIZE * TILE_COUNT),
        "height": str(TILE_SIZE),
    })

    wangsets = ET.SubElement(root, "wangsets")
    wangset = ET.SubElement(wangsets, "wangset", {
        "name": name,
        "type": "edge",
        "tile": "-1"
    })

    ET.SubElement(wangset, "wangcolor", {
        "name": name,
        "color": WANG_COLOR,
        "tile": "-1",
        "probability": "1"
    })

    for i in range(TILE_COUNT):
        ET.SubElement(wangset, "wangtile", {
            "tileid": str(i),
            "wangid": _wang_id(i)
        })

    try:
        tree = ET.ElementTree(root)
        tree.write(tsx_path, encoding="utf-8", xml_declaration=True)
    except OSError as e:
        sys.exit(f"ERROR: Cannot write TSX file '{tsx_path}': {e}")


def convert(input_path: Path, tsx_path: Path, png_path: Path) -> None:
    """Convert one RPG Maker XP autotile to a Tiled Wang tileset (PNG + TSX)."""
    src = Image.open(input_path).convert("RGBA")

    if src.size != (96, 128):
        sys.exit(
            f"ERROR: Expected 96×128 px autotile, got {src.size[0]}×{src.size[1]}."
            " Make sure this is a RPG Maker XP autotile."
        )

    # Ensure directories exist
    try:
        tsx_path.parent.mkdir(parents=True, exist_ok=True)
        png_path.parent.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        sys.exit(f"ERROR: Could not create output directory: {e}")

    # Generate the tile strip
    strip = Image.new("RGBA", (TILE_SIZE * TILE_COUNT, TILE_SIZE))
    for mask in range(TILE_COUNT):
        strip.paste(_build_tile(src, mask), (mask * TILE_SIZE, 0))
    try:
        strip.save(png_path)
    except OSError as e:
        sys.exit(f"ERROR: Cannot write PNG file '{png_path}': {e}")

    # Generate the TSX with Wang data
    _generate_tsx(png_path, tsx_path, tsx_path.stem)

    rel_path = os.path.relpath(png_path, tsx_path.parent)
    sys.stdout.write(f"✅ PNG: {png_path} ({strip.size[0]}×{strip.size[1]} px)\n")
    sys.stdout.write(f"✅ TSX: {tsx_path} (ref: {rel_path})\n\n")
    sys.stdout.write(
        "Import dans Tiled:\n"
        "  1. Ferme le tileset actuel (sans sauvegarder)\n"
        f"  2. Carte > Jeux de tuiles > Nouveau jeu de tuiles → importe {tsx_path.name}\n"
        "  3. Le terrain Wang est déjà configuré — utilise l'outil Terrain pour peindre !\n"
    )


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit(
            "Usage: python3 scripts/rpgmaker_autotile_to_tiled.py <input.png> [tsx_path] [png_path]\n"
            "  tsx_path : chemin du fichier .tsx à générer\n"
            "  png_path : chemin du fichier .png (strip) à générer\n"
        )

    input_path = Path(sys.argv[1])
    if not input_path.exists():
        sys.exit(f"ERROR: File not found: {input_path}")

    # TSX Path
    if len(sys.argv) >= 3:
        tsx_path = Path(sys.argv[2]).with_suffix(".tsx")
    else:
        tsx_path = input_path.with_name(input_path.stem + "_tiled.tsx")

    # PNG Path
    if len(sys.argv) >= 4:
        png_path = Path(sys.argv[3]).with_suffix(".png")
    else:
        png_path = tsx_path.with_suffix(".png")

    convert(input_path, tsx_path, png_path)


if __name__ == "__main__":
    main()
