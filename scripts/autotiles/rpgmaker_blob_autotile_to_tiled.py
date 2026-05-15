"""
Convert a RPG Maker XP autotile (96×128, static or animated) to a Tiled-compatible
47-tile blob Wang tileset.

Differences vs 16-tile edge-only:
  - Encodes all 8 neighbors → no diagonal corner artefacts
  - wangset type="mixed" (corner+edge) in Tiled

Usage:
    python3 scripts/rpgmaker_blob_autotile_to_tiled.py <input.png>
            [--tsx PATH] [--png PATH] [--frame-duration MS]
"""

import argparse
import os
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    sys.exit("ERROR: Pillow is required. Run: pip install pillow")

# ── Constants ─────────────────────────────────────────────────────────────────

TILED_VERSION = "1.10.0"
WANG_COLOR = "#4488ff"

SUBTILE = 16
TILE_SIZE = 32
FRAME_W = 96
FRAME_H = 128
DEFAULT_MS = 200

# ── 47 valid blob bitmasks ────────────────────────────────────────────────────
# Bit layout: NW=1, N=2, NE=4, W=8, E=16, SW=32, S=64, SE=128
# Rule: diagonal bit can only be 1 if BOTH adjacent cardinals are 1.
# These 47 values cover all visually distinct blob tile configurations.

BLOB_BITMASKS = (
    0, 2, 8, 10, 11, 16, 18, 22, 24, 26, 27, 30, 31,
    64, 66, 72, 74, 75, 80, 82, 86, 88, 90, 91, 94, 95,
    104, 106, 107, 120, 122, 123, 126, 127,
    208, 210, 214, 216, 218, 219, 222, 223,
    248, 250, 251, 254, 255,
)  # exactly 47 entries

BLOB_COUNT = len(BLOB_BITMASKS)  # 47

# Quick reverse lookup: bitmask → strip index (frame 0)
BITMASK_TO_IDX = {bm: idx for idx, bm in enumerate(BLOB_BITMASKS)}

# ── RPG Maker XP sub-tile grid ────────────────────────────────────────────────
# Source autotile: 96×128 px = 6 cols × 8 rows of 16×16 sub-tiles.
#
#  Col  0   1   2   3   4   5
# Row 0 A-TL A-TR B-TL B-TR C-TL C-TR    A=isolated, B=inner-corner, C=variant
# Row 1 A-BL A-BR B-BL B-BR C-BL C-BR
# Row 2 D-TL D-TR E-TL E-TR F-TL F-TR    D=top-left, E=top-edge, F=top-right
# Row 3 D-BL D-BR E-BL E-BR F-BL F-BR
# Row 4 G-TL G-TR H-TL H-TR I-TL I-TR    G=left, H=center, I=right
# Row 5 G-BL G-BR H-BL H-BR I-BL I-BR
# Row 6 J-TL J-TR K-TL K-TR L-TL L-TR    J=bot-left, K=bot-edge, L=bot-right
# Row 7 J-BL J-BR K-BL K-BR L-BL L-BR
#
# The B tile (col 2-3, row 0-1) holds the inner-corner shadow pieces:
#   B-TL (2,0): shown when N=1, W=1 but NW=0  (top-left diagonal missing)
#   B-TR (3,0): shown when N=1, E=1 but NE=0
#   B-BL (2,1): shown when S=1, W=1 but SW=0
#   B-BR (3,1): shown when S=1, E=1 but SE=0

def _sub(frame: Image.Image, col: int, row: int) -> Image.Image:
    """Crop one 16×16 sub-tile from a 96×128 frame."""
    x, y = col * SUBTILE, row * SUBTILE
    return frame.crop((x, y, x + SUBTILE, y + SUBTILE))


def _quarter_tl(c1: bool, c2: bool, diag: bool, iso: bool) -> tuple[int, int]:
    if c1 and c2: return (2, 4) if diag else (4, 0)
    if c1: return (0, 4)
    if c2: return (2, 2)
    return (0, 0) if iso else (0, 2)

def _quarter_tr(c1: bool, c2: bool, diag: bool, iso: bool) -> tuple[int, int]:
    if c1 and c2: return (3, 4) if diag else (5, 0)
    if c1: return (5, 4)
    if c2: return (3, 2)
    return (1, 0) if iso else (5, 2)

def _quarter_bl(c1: bool, c2: bool, diag: bool, iso: bool) -> tuple[int, int]:
    if c1 and c2: return (2, 5) if diag else (4, 1)
    if c1: return (0, 5)
    if c2: return (2, 7)
    return (0, 1) if iso else (0, 7)

def _quarter_br(c1: bool, c2: bool, diag: bool, iso: bool) -> tuple[int, int]:
    if c1 and c2: return (3, 5) if diag else (5, 1)
    if c1: return (5, 5)
    if c2: return (3, 7)
    return (1, 1) if iso else (5, 7)

def _quarter(corner: str, c1: bool, c2: bool, diag: bool, iso: bool) -> tuple[int, int]:
    """Return (col, row) sub-tile for one quadrant of a blob tile.

    corner: 'tl' | 'tr' | 'bl' | 'br'
    c1: vertical cardinal  (N for tl/tr, S for bl/br)
    c2: horizontal cardinal (W for tl/bl, E for tr/br)
    diag: diagonal neighbor (NW, NE, SW, SE respectively)
    iso: True when ALL four cardinals are absent (full isolation)
    """
    if corner == "tl": return _quarter_tl(c1, c2, diag, iso)
    if corner == "tr": return _quarter_tr(c1, c2, diag, iso)
    if corner == "bl": return _quarter_bl(c1, c2, diag, iso)
    if corner == "br": return _quarter_br(c1, c2, diag, iso)
    raise ValueError(f"Unknown corner: {corner!r}")


def _build_blob_tile(frame: Image.Image, bitmask: int) -> Image.Image:
    """Assemble one 32×32 blob tile from the 8-neighbor bitmask."""
    nw = bool(bitmask & 1)
    n  = bool(bitmask & 2)
    ne = bool(bitmask & 4)
    w  = bool(bitmask & 8)
    e  = bool(bitmask & 16)
    sw = bool(bitmask & 32)
    s  = bool(bitmask & 64)
    se = bool(bitmask & 128)
    iso = not (n or s or w or e)

    tile = Image.new("RGBA", (TILE_SIZE, TILE_SIZE))
    for corner, c1, c2, diag, dx, dy in (
        ("tl", n, w, nw, 0,      0),
        ("tr", n, e, ne, SUBTILE, 0),
        ("bl", s, w, sw, 0,      SUBTILE),
        ("br", s, e, se, SUBTILE, SUBTILE),
    ):
        col, row = _quarter(corner, c1, c2, diag, iso)
        tile.paste(_sub(frame, col, row), (dx, dy))
    return tile


# ── Strip builder ─────────────────────────────────────────────────────────────


def _build_blob_strip(src: Image.Image, n_frames: int) -> Image.Image:
    """Build horizontal strip: N frames × 47 tiles × 32 px, 32 px tall."""
    total = n_frames * BLOB_COUNT
    strip = Image.new("RGBA", (TILE_SIZE * total, TILE_SIZE))

    for fi in range(n_frames):
        frame = src.crop((fi * FRAME_W, 0, (fi + 1) * FRAME_W, FRAME_H))
        for slot, bm in enumerate(BLOB_BITMASKS):
            x = (fi * BLOB_COUNT + slot) * TILE_SIZE
            strip.paste(_build_blob_tile(frame, bm), (x, 0))

    return strip


# ── Bitmask helpers ───────────────────────────────────────────────────────────


def _blob_mask(
    nw: bool, n: bool, ne: bool,
    w: bool,            e: bool,
    sw: bool, s: bool, se: bool,
) -> int:
    """Compute blob bitmask: clear diagonals whose adjacent cardinals are absent."""
    if not n: nw = ne = False
    if not s: sw = se = False
    if not w: nw = sw = False
    if not e: ne = se = False
    return (int(nw) | int(n)<<1 | int(ne)<<2 | int(w)<<3
            | int(e)<<4 | int(sw)<<5 | int(s)<<6 | int(se)<<7)


def _blob_wang_id(bitmask: int) -> str:
    """Tiled mixed-Wang wangid: Top, TopRight, Right, BottomRight, Bottom, BottomLeft, Left, TopLeft."""
    nw = (bitmask >> 0) & 1
    n  = (bitmask >> 1) & 1
    ne = (bitmask >> 2) & 1
    e  = (bitmask >> 4) & 1
    se = (bitmask >> 7) & 1
    s  = (bitmask >> 6) & 1
    sw = (bitmask >> 5) & 1
    w  = (bitmask >> 3) & 1
    # Tiled order: Top, TopRight, Right, BottomRight, Bottom, BottomLeft, Left, TopLeft
    return f"{n},{ne},{e},{se},{s},{sw},{w},{nw}"


# ── TSX generation ────────────────────────────────────────────────────────────


def _generate_tsx(
    png_path: Path, tsx_path: Path,
    name: str, n_frames: int, frame_duration: int,
) -> None:
    total = n_frames * BLOB_COUNT
    rel_png = os.path.relpath(png_path, tsx_path.parent)

    root = ET.Element("tileset", {
        "version": "1.10", "tiledversion": TILED_VERSION,
        "name": name,
        "tilewidth": str(TILE_SIZE), "tileheight": str(TILE_SIZE),
        "spacing": "0", "margin": "0",
        "tilecount": str(total), "columns": str(total),
    })
    ET.SubElement(root, "image", {
        "source": rel_png,
        "width": str(TILE_SIZE * total),
        "height": str(TILE_SIZE),
    })

    if n_frames > 1:
        for slot in range(BLOB_COUNT):
            tile_el = ET.SubElement(root, "tile", {"id": str(slot)})
            anim_el = ET.SubElement(tile_el, "animation")
            for fi in range(n_frames):
                ET.SubElement(anim_el, "frame", {
                    "tileid": str(fi * BLOB_COUNT + slot),
                    "duration": str(frame_duration),
                })

    wangsets = ET.SubElement(root, "wangsets")
    wangset = ET.SubElement(wangsets, "wangset", {
        "name": name, "type": "mixed", "tile": "-1",
    })
    ET.SubElement(wangset, "wangcolor", {
        "name": name, "color": WANG_COLOR, "tile": "-1", "probability": "1",
    })
    for slot, bm in enumerate(BLOB_BITMASKS):
        ET.SubElement(wangset, "wangtile", {
            "tileid": str(slot),
            "wangid": _blob_wang_id(bm),
        })

    try:
        ET.ElementTree(root).write(tsx_path, encoding="utf-8", xml_declaration=True)
    except OSError as e:
        sys.exit(f"ERROR: Cannot write TSX '{tsx_path}': {e}")


# ── Validation & convert ──────────────────────────────────────────────────────


def convert(
    input_path: Path, tsx_path: Path, png_path: Path, frame_duration: int,
) -> None:
    if not input_path.exists():
        sys.exit(f"ERROR: File not found: {input_path}")
    if frame_duration <= 0:
        sys.exit("ERROR: --frame-duration must be > 0.")

    try:
        src = Image.open(input_path).convert("RGBA")
    except OSError as e:
        sys.exit(f"ERROR: Cannot open image '{input_path}': {e}")

    if src.height != FRAME_H:
        sys.exit(f"ERROR: Expected height {FRAME_H}px, got {src.height}px.")
    if src.width % FRAME_W != 0:
        sys.exit(f"ERROR: Width {src.width}px is not a multiple of {FRAME_W}px.")

    n_frames = src.width // FRAME_W
    if n_frames == 1:
        sys.stdout.write(
            "WARNING: Single frame detected — output will be static (no animation)."
            " No <animation> elements will be generated.\n"
        )

    try:
        tsx_path.parent.mkdir(parents=True, exist_ok=True)
        png_path.parent.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        sys.exit(f"ERROR: Could not create output directory: {e}")

    strip = _build_blob_strip(src, n_frames)
    try:
        strip.save(png_path)
    except OSError as e:
        sys.exit(f"ERROR: Cannot write PNG '{png_path}': {e}")

    _generate_tsx(png_path, tsx_path, tsx_path.stem, n_frames, frame_duration)

    rel = os.path.relpath(png_path, tsx_path.parent)
    sys.stdout.write(
        f"✅ PNG : {png_path} ({strip.size[0]}×{strip.size[1]} px)\n"
        f"✅ TSX : {tsx_path} (ref: {rel})\n\n"
        f"   {n_frames} frame(s) · 47 tiles blob (8 voisins, sans artefacts de coins)\n\n"
        "Import dans Tiled :\n"
        "  1. Carte > Jeux de tuiles > Importer\n"
        f"  2. Sélectionne {tsx_path.name}\n"
        "  3. Repeins avec l'outil Terrain — les coins sont maintenant corrects !\n"
    )


# ── CLI ───────────────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(
        description="RPG Maker XP autotile → Tiled 47-tile blob Wang tileset."
    )
    parser.add_argument("input", type=Path, help="Autotile source PNG (96×128 ou N×96×128)")
    parser.add_argument("--tsx", type=Path, default=None, metavar="PATH")
    parser.add_argument("--png", type=Path, default=None, metavar="PATH")
    parser.add_argument("--frame-duration", type=int, default=DEFAULT_MS, metavar="MS")

    args = parser.parse_args()
    tsx = (args.tsx or args.input.with_name(args.input.stem + "_blob.tsx")).with_suffix(".tsx")
    png = (args.png or tsx.with_suffix(".png")).with_suffix(".png")
    convert(args.input, tsx, png, args.frame_duration)


if __name__ == "__main__":
    main()
