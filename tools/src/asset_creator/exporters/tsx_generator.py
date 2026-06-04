"""
asset_creator.exporters.tsx_generator

Assemble the 47-tile blob sprite sheet PNG and generate the Tiled TSX file.

Spec: tools/docs/specs/autotile_converter_spec.md § tsx_generator.py
"""

from __future__ import annotations

import os
import xml.etree.ElementTree as ET
from pathlib import Path

from asset_creator.core.converter_xp import BLOB_BITMASKS
from PIL import Image

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

BLOB_COUNT = 47
SHEET_COLS = 8
SHEET_ROWS = 6   # 8x6 = 48 slots; slot 47 (last) is transparent padding

TILED_VERSION = "1.10.0"
WANG_COLOR = "#4488ff"

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def assemble_sheet(tiles: list[Image.Image], tile_size: int) -> Image.Image:
    """
    Place 47 tiles into an 8-column x 6-row sprite sheet.  # noqa: RUF002

    Slot layout (left-to-right, top-to-bottom):
      Slots 0..46 → tiles[0..46]
      Slot 47     → transparent padding (empty)

    Args:
        tiles: List of exactly 47 RGBA PIL Images (each tile_size x tile_size).  # noqa: RUF002
        tile_size: Width/height of each tile in pixels (32 or 48).

    Returns:
        RGBA PIL Image of size (SHEET_COLS*tile_size, SHEET_ROWS*tile_size).
    """
    width = SHEET_COLS * tile_size
    height = SHEET_ROWS * tile_size
    sheet = Image.new("RGBA", (width, height), (0, 0, 0, 0))

    for slot, tile in enumerate(tiles):
        col = slot % SHEET_COLS
        row = slot // SHEET_COLS
        sheet.paste(tile, (col * tile_size, row * tile_size))

    # Slot 47 is left transparent (already done by Image.new alpha=0)
    return sheet


def bitmask_to_wangid(bitmask: int) -> str:
    """
    Convert a blob bitmask to a Tiled mixed-Wang wangid string.

    Tiled order: [top, topRight, right, bottomRight, bottom, bottomLeft, left, topLeft]
    Bitmask convention: NW=1, N=2, NE=4, W=8, E=16, SW=32, S=64, SE=128

    Args:
        bitmask: Integer blob bitmask (0..255).

    Returns:
        Comma-separated string of 8 values (0 or 1).
    """
    nw = (bitmask >> 0) & 1
    n  = (bitmask >> 1) & 1
    ne = (bitmask >> 2) & 1
    w  = (bitmask >> 3) & 1
    e  = (bitmask >> 4) & 1
    sw = (bitmask >> 5) & 1
    s  = (bitmask >> 6) & 1
    se = (bitmask >> 7) & 1
    # Tiled wangid order: top, topRight, right, bottomRight, bottom, bottomLeft, left, topLeft
    return f"{n},{ne},{e},{se},{s},{sw},{w},{nw}"


def generate_tsx(name: str, tile_size: int, png_filename: str) -> str:
    """
    Generate the TSX XML string for a 47-tile blob wangset.

    Args:
        name: Tileset name (used for wangset name and <tileset name>).
        tile_size: Tile width/height in pixels.
        png_filename: Relative path to the PNG file (used in <image source>).

    Returns:
        XML string (UTF-8, with declaration).
    """
    sheet_width = SHEET_COLS * tile_size
    sheet_height = SHEET_ROWS * tile_size
    total_tiles = SHEET_COLS * SHEET_ROWS  # 48 (slot 47 = transparent padding)

    root = ET.Element(
        "tileset",
        {
            "version": "1.10",
            "tiledversion": TILED_VERSION,
            "name": name,
            "tilewidth": str(tile_size),
            "tileheight": str(tile_size),
            "spacing": "0",
            "margin": "0",
            "tilecount": str(total_tiles),
            "columns": str(SHEET_COLS),
        },
    )
    ET.SubElement(
        root,
        "image",
        {
            "source": png_filename,
            "width": str(sheet_width),
            "height": str(sheet_height),
        },
    )

    wangsets = ET.SubElement(root, "wangsets")
    wangset = ET.SubElement(
        wangsets,
        "wangset",
        {
            "name": name,
            "type": "mixed",
            "tile": "-1",
        },
    )
    ET.SubElement(
        wangset,
        "wangcolor",
        {
            "name": name,
            "color": WANG_COLOR,
            "tile": "-1",
            "probability": "1",
        },
    )
    for slot, bm in enumerate(BLOB_BITMASKS):
        ET.SubElement(
            wangset,
            "wangtile",
            {
                "tileid": str(slot),
                "wangid": bitmask_to_wangid(bm),
            },
        )

    # Serialize to XML string
    tree = ET.ElementTree(root)
    ET.indent(tree, space="  ")

    # Build the XML manually to get xml_declaration
    import io
    buf = io.BytesIO()
    tree.write(buf, encoding="utf-8", xml_declaration=True)
    return buf.getvalue().decode("utf-8")


def export(
    tiles: list[Image.Image],
    name: str,
    output_dir: str | Path,
    tile_size: int,
) -> tuple[str, str]:
    """
    Write the 47-tile blob sprite sheet PNG and TSX to disk.

    Args:
        tiles: List of exactly 47 RGBA PIL Images.
        name: Base name for output files (e.g. "grass" → grass.png + grass.tsx).
        output_dir: Directory to write files into (created if needed).
        tile_size: Tile size in pixels (32 or 48).

    Returns:
        Tuple of (png_path, tsx_path) as str.

    Raises:
        ValueError: if len(tiles) != 47.
        OSError: if output_dir is not writable.
    """
    if len(tiles) != BLOB_COUNT:
        raise ValueError(
            f"Expected exactly {BLOB_COUNT} tiles, got {len(tiles)}."
        )

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    png_path = out / f"{name}.png"
    tsx_path = out / f"{name}.tsx"

    # Write PNG
    sheet = assemble_sheet(tiles, tile_size)
    sheet.save(png_path)

    # Compute relative path from TSX to PNG (same dir → just filename)
    rel_png = os.path.relpath(png_path, tsx_path.parent)

    # Write TSX
    xml_str = generate_tsx(name, tile_size, rel_png)
    tsx_path.write_text(xml_str, encoding="utf-8")

    return str(png_path), str(tsx_path)
