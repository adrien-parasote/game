"""
asset_convertor.exporters.tsx_generator

Assemble the 47-tile blob sprite sheet PNG and generate the Tiled TSX file.

Spec: tools/docs/specs/autotile_converter_spec.md § tsx_generator.py
"""

from __future__ import annotations

import io
import os
import xml.etree.ElementTree as ET
from pathlib import Path

from asset_convertor.core.converter_xp import BLOB_BITMASKS
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


def assemble_sheet(tiles_by_frame: list[list[Image.Image]], tile_size: int) -> Image.Image:
    """
    Stack N animation frames vertically. Each frame contains 47 tiles.
    The sheet will have 8 columns and 6 * N rows.

    Slot layout per frame f:
      Slots 0..46 of frame f → tiles_by_frame[f][0..46]
      Slot 47 (last)          → transparent padding

    Args:
        tiles_by_frame: list of N frames, each containing 47 RGBA PIL Images.
        tile_size: Width/height of each tile in pixels (32 or 48).

    Returns:
        RGBA PIL Image of size (8 * tile_size, 6 * N * tile_size).
    """
    num_frames = len(tiles_by_frame)
    width = SHEET_COLS * tile_size
    height = SHEET_ROWS * num_frames * tile_size
    sheet = Image.new("RGBA", (width, height), (0, 0, 0, 0))

    for f_idx, frame_tiles in enumerate(tiles_by_frame):
        y_offset = f_idx * SHEET_ROWS * tile_size
        for slot, tile in enumerate(frame_tiles):
            col = slot % SHEET_COLS
            row = slot // SHEET_COLS
            sheet.paste(tile, (col * tile_size, y_offset + row * tile_size))

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



def generate_tsx(
    name: str,
    tile_size: int,
    png_filename: str,
    is_animated: bool = False,
    animation_mode: str = "Horizontale",
    duration: int = 150,
    num_frames: int = 1,
) -> str:
    """
    Generate the TSX XML string for a 47-tile blob wangset, with animation support.

    Args:
        name: Tileset name (used for wangset name and <tileset name>).
        tile_size: Tile width/height in pixels.
        png_filename: Relative path to the PNG file (used in <image source>).
        is_animated: True if the tileset is animated.
        animation_mode: "Horizontale" or "Verticale".
        duration: Animation frame duration in ms.
        num_frames: Number of animation frames.

    Returns:
        XML string (UTF-8, with declaration).
    """
    sheet_width = SHEET_COLS * tile_size
    sheet_height = SHEET_ROWS * num_frames * tile_size
    total_tiles = SHEET_COLS * SHEET_ROWS * num_frames

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

    # If animated, add <tile> elements with <animation> loops for first frame's tiles
    if is_animated and num_frames > 1:
        for i in range(BLOB_COUNT):
            tile_el = ET.SubElement(root, "tile", {"id": str(i)})
            anim_el = ET.SubElement(tile_el, "animation")

            # Sequence rules
            if num_frames == 3 and animation_mode == "Horizontale":
                frame_seq = [0, 1, 2, 1]
            elif num_frames == 3 and animation_mode == "Verticale":
                frame_seq = [0, 1, 2]
            elif num_frames == 4:
                frame_seq = [0, 1, 2, 3]
            else:
                frame_seq = list(range(num_frames))

            for f_idx in frame_seq:
                target_tileid = i + f_idx * (SHEET_COLS * SHEET_ROWS)
                ET.SubElement(
                    anim_el,
                     "frame",
                     {
                         "tileid": str(target_tileid),
                         "duration": str(duration),
                     }
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
    buf = io.BytesIO()
    tree.write(buf, encoding="utf-8", xml_declaration=True)
    return buf.getvalue().decode("utf-8")


def export(
    tiles: list[list[Image.Image]] | list[Image.Image],
    name: str,
    output_dir: str | Path,
    tile_size: int,
    is_animated: bool = False,
    animation_mode: str = "Horizontale",
    duration: int = 150,
) -> tuple[str, str]:
    """
    Write the 47-tile blob sprite sheet PNG and TSX to disk, supporting animation frames.

    Args:
        tiles: List of frames (each a list of 47 RGBA PIL Images), or flat list of 47 images for static.
        name: Base name for output files (e.g. "grass" → grass.png + grass.tsx).
        output_dir: Directory to write files into (created if needed).
        tile_size: Tile size in pixels (32 or 48).
        is_animated: True if animated autotile conversion is requested.
        animation_mode: "Horizontale" or "Verticale".
        duration: Animation frame duration in ms.

    Returns:
        Tuple of (png_path, tsx_path) as str.

    Raises:
        ValueError: if frame contains a number of tiles different from 47.
        OSError: if output_dir is not writable.
    """
    if not tiles:
        raise ValueError("No tiles provided.")

    from typing import cast
    if isinstance(tiles[0], list):
        tiles_by_frame = cast(list[list[Image.Image]], tiles)
    else:
        tiles_by_frame = cast(list[list[Image.Image]], [tiles])

    for f_idx, frame in enumerate(tiles_by_frame):
        if len(frame) != BLOB_COUNT:
            raise ValueError(
                f"Expected exactly {BLOB_COUNT} tiles in frame {f_idx}, got {len(frame)}."
            )

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    png_path = out / f"{name}.png"
    tsx_path = out / f"{name}.tsx"

    # Write PNG
    sheet = assemble_sheet(tiles_by_frame, tile_size)
    sheet.save(png_path)

    # Compute relative path from TSX to PNG (same dir → just filename)
    rel_png = os.path.relpath(png_path, tsx_path.parent)

    # Write TSX
    num_frames = len(tiles_by_frame)
    xml_str = generate_tsx(
        name=name,
        tile_size=tile_size,
        png_filename=rel_png,
        is_animated=is_animated,
        animation_mode=animation_mode,
        duration=duration,
        num_frames=num_frames,
    )
    tsx_path.write_text(xml_str, encoding="utf-8")

    return str(png_path), str(tsx_path)
