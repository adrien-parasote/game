"""TSX exporter for Tiled Wang set tileset files.

Generates .tsx (XML) files with Wang set definitions for blob autotiling.
"""
from __future__ import annotations

import os
import xml.etree.ElementTree as ET
from pathlib import Path

from tools.asset_creator.core.tile_assembler import BLOB_BITMASKS, blob_wang_id

TILED_VERSION = "1.10.0"
WANG_COLOR = "#4488ff"
TILE_SIZE = 32


def compute_relative_path(png_path: Path, tsx_path: Path) -> str:
    """Compute relative path from TSX location to PNG location."""
    return os.path.relpath(png_path, tsx_path.parent)


def export_tsx(
    output_path: Path,
    png_path: Path,
    name: str,
    tile_size: int = TILE_SIZE,
    tile_count: int = 47,
) -> Path:
    """Generate TSX file with Wang set for blob tileset.

    Args:
        output_path: Destination path for the TSX file.
        png_path: Path to the associated PNG tileset image.
        name: Name for the tileset and Wang set.
        tile_size: Size of each tile in pixels.
        tile_count: Number of tiles in the tileset.

    Returns:
        The output path where the file was saved.

    Raises:
        OSError: If the file cannot be written.
    """
    output_path = Path(output_path)
    png_path = Path(png_path)
    rel_png = compute_relative_path(png_path, output_path)

    root = ET.Element("tileset", {
        "version": "1.10",
        "tiledversion": TILED_VERSION,
        "name": name,
        "tilewidth": str(tile_size),
        "tileheight": str(tile_size),
        "tilecount": str(tile_count),
        "columns": str(tile_count),
    })

    ET.SubElement(root, "image", {
        "source": rel_png,
        "width": str(tile_size * tile_count),
        "height": str(tile_size),
    })

    wangsets = ET.SubElement(root, "wangsets")
    wangset = ET.SubElement(wangsets, "wangset", {
        "name": name,
        "type": "mixed",
        "tile": "-1",
    })

    ET.SubElement(wangset, "wangcolor", {
        "name": name,
        "color": WANG_COLOR,
        "tile": "-1",
        "probability": "1",
    })

    for slot, bitmask in enumerate(BLOB_BITMASKS):
        ET.SubElement(wangset, "wangtile", {
            "tileid": str(slot),
            "wangid": blob_wang_id(bitmask),
        })

    output_path.parent.mkdir(parents=True, exist_ok=True)

    tree = ET.ElementTree(root)
    ET.indent(tree, space="  ")
    tree.write(output_path, encoding="utf-8", xml_declaration=True)
    return output_path
