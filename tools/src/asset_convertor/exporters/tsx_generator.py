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
        if bm == 0:
            # Omit tileid=0 (isolated tile, wangid all-zeros).
            # Tiled treats wangid="0,0,0,0,0,0,0,0" as "no terrain" which
            # confuses the terrain solver for all neighbouring tiles.
            # Production TSX files (e.g. 00-grass.tsx, 01-basement-top.tsx)
            # exclude this entry entirely.
            continue
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


# ---------------------------------------------------------------------------
# A3 / A4 — Simple grid tileset (no wangset, no blob format)
# ---------------------------------------------------------------------------

def generate_tsx_simple(
    name: str,
    tile_size: int,
    png_filename: str,
    tile_count: int,
    columns: int,
) -> str:
    """
    Generate a plain Tiled TSX for a simple grid tileset (no wangset).

    Used for A3 (Building) and A4 (Wall) sprite sheets where tiles are
    laid out in a regular N-column grid without autotile blob semantics.

    Args:
        name:         Tileset name.
        tile_size:    Tile width/height in pixels (square tiles assumed).
        png_filename: Relative path to the PNG image from the TSX file.
        tile_count:   Total number of tiles in the sheet.
        columns:      Number of tile columns in the sheet.

    Returns:
        XML string (UTF-8, with declaration).
    """
    rows = (tile_count + columns - 1) // columns  # ceiling division
    sheet_width = columns * tile_size
    sheet_height = rows * tile_size

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
            "tilecount": str(tile_count),
            "columns": str(columns),
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

    tree = ET.ElementTree(root)
    ET.indent(tree, space="  ")
    buf = io.BytesIO()
    tree.write(buf, encoding="utf-8", xml_declaration=True)
    return buf.getvalue().decode("utf-8")


def export_simple_sheet(
    sheet: Image.Image,
    name: str,
    output_dir: str | Path,
    tile_size: int,
    columns: int,
) -> tuple[str, str]:
    """
    Write a pre-assembled sprite sheet PNG and its simple TSX to disk.

    Used for A3 and A4 exports where the converter already returns the
    assembled sheet image (no per-tile list needed).

    Args:
        sheet:      Pre-assembled RGBA PIL Image (the converter output).
        name:       Base name for output files (e.g. "building" → building.png + building.tsx).
        output_dir: Directory to write files into (created if needed).
        tile_size:  Tile width/height in pixels.
        columns:    Number of columns in the sheet grid.

    Returns:
        Tuple of (png_path, tsx_path) as str.

    Raises:
        ValueError: if sheet dimensions are not divisible by tile_size.
        OSError:    if output_dir is not writable.
    """
    w, h = sheet.size
    if w % tile_size != 0 or h % tile_size != 0:
        raise ValueError(
            f"Sheet size {w}x{h} is not divisible by tile_size={tile_size}."
        )

    cols = w // tile_size
    rows = h // tile_size
    tile_count = cols * rows

    if columns != cols:
        raise ValueError(
            f"columns={columns} does not match sheet width ({w} / {tile_size} = {cols})."
        )

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    png_path = out / f"{name}.png"
    tsx_path = out / f"{name}.tsx"

    sheet.save(png_path)

    rel_png = os.path.relpath(png_path, tsx_path.parent)
    xml_str = generate_tsx_simple(
        name=name,
        tile_size=tile_size,
        png_filename=rel_png,
        tile_count=tile_count,
        columns=cols,
    )
    tsx_path.write_text(xml_str, encoding="utf-8")

    return str(png_path), str(tsx_path)


# ---------------------------------------------------------------------------
# A4 wall sides — 4-neighbor edge wangset (16 tiles)
# ---------------------------------------------------------------------------

# shape_index (0-15) → 4N bitmask (N=2, W=8, E=4, S=1).
# Derived from WALL_AUTOTILE_TABLE: center coords (qsx/qsy=1,2) = neighbor PRESENT;
# outer coords (qsx/qsy=0,3) = edge visible = neighbor ABSENT.
_WALL_SHAPE_TO_4N_BITMASK: list[int] = [
    15,  # shape  0: N+W+E+S (fully surrounded — all interior quadrants)
     7,  # shape  1: N+E+S
    13,  # shape  2: W+E+S
     5,  # shape  3: E+S
    11,  # shape  4: N+W+S
     3,  # shape  5: N+S
     9,  # shape  6: W+S
     1,  # shape  7: S only
    14,  # shape  8: N+W+E
     6,  # shape  9: N+E
    12,  # shape 10: W+E
     4,  # shape 11: E only
    10,  # shape 12: N+W
     2,  # shape 13: N only
     8,  # shape 14: W only
     0,  # shape 15: isolated (all edges open)
]


def wall4n_bitmask_to_wangid(bitmask: int) -> str:
    """Convert a 4-neighbor wall bitmask to a Tiled edge wangid string.

    Convention: N=2 (bit 1), E=4 (bit 2), S=1 (bit 0), W=8 (bit 3).
    Tiled wangid order: [top, topRight, right, bottomRight, bottom, bottomLeft, left, topLeft].
    For edge wangsets, corner positions (topRight, bottomRight, bottomLeft, topLeft) = 0.

    Args:
        bitmask: 4N wall bitmask in [0, 15].

    Returns:
        Comma-separated 8-value string e.g. "1,0,1,0,0,0,0,0".
    """
    n = (bitmask >> 1) & 1  # bit 1
    e = (bitmask >> 2) & 1  # bit 2
    s = (bitmask >> 0) & 1  # bit 0
    w = (bitmask >> 3) & 1  # bit 3
    return f"{n},0,{e},0,{s},0,{w},0"


def generate_tsx_wall_sides(
    name: str,
    tile_size: int,
    png_filename: str,
    num_kinds: int = 1,
) -> str:
    """Generate a Tiled TSX with an edge wangset for A4 wall-side/top tiles (16 shapes).

    The strip is 16 tiles wide. When num_kinds > 1 the rows are stacked vertically
    (e.g. 2 material kinds = 32 tiles in 16 cols × 2 rows). The wangset only maps
    shape 0-15 of the first kind; additional rows are usable as palette overrides.

    Args:
        name:         Tileset name.
        tile_size:    Tile width/height in pixels (square tiles assumed).
        png_filename: Relative path to the PNG image from the TSX file.
        num_kinds:    Number of material kinds stacked vertically (default 1).

    Returns:
        XML string (UTF-8, with declaration).
    """
    sheet_width = 16 * tile_size
    sheet_height = num_kinds * tile_size
    total_tiles = 16 * num_kinds

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
            "columns": "16",
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
            "type": "corner-or-edge",
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
    for shape_idx, bitmask in enumerate(_WALL_SHAPE_TO_4N_BITMASK):
        if bitmask == 0:
            # Omit isolated shape (bitmask=0, wangid all-zeros).
            # Tiled treats wangid="0,0,0,0,0,0,0,0" as "no terrain";
            # registering it explicitly breaks terrain-brush resolution.
            continue
        ET.SubElement(
            wangset,
            "wangtile",
            {
                "tileid": str(shape_idx),
                "wangid": wall4n_bitmask_to_wangid(bitmask),
            },
        )

    tree = ET.ElementTree(root)
    ET.indent(tree, space="  ")
    buf = io.BytesIO()
    tree.write(buf, encoding="utf-8", xml_declaration=True)
    return buf.getvalue().decode("utf-8")


def export_wall_sides_sheet(
    sheet: Image.Image,
    name: str,
    output_dir: str | Path,
    tile_size: int,
) -> tuple[str, str]:
    """Write a 4-neighbor wall strip PNG and its edge-wangset TSX to disk.

    Accepts 1 or more kinds stacked vertically (height must be a multiple of tile_size).
    Used for both A4 wall-sides and A4 wall-tops (both use WALL_AUTOTILE_TABLE).

    Args:
        sheet:      Pre-assembled RGBA PIL Image. Width = 16 * tile_size.
                    Height = N_kinds * tile_size (N ≥ 1).
        name:       Base name (e.g. "dungeon_sides" → dungeon_sides.png + dungeon_sides.tsx).
        output_dir: Directory to write files into (created if needed).
        tile_size:  Tile width/height in pixels.

    Returns:
        Tuple of (png_path, tsx_path) as str.

    Raises:
        ValueError: if sheet width ≠ 16 * tile_size or height not divisible by tile_size.
        OSError:    if output_dir is not writable.
    """
    expected_w = 16 * tile_size
    w, h = sheet.size
    if w != expected_w:
        raise ValueError(
            f"Wall sheet must be {expected_w}px wide (16 tiles × {tile_size}px); got {w}x{h}."
        )
    if h % tile_size != 0 or h == 0:
        raise ValueError(
            f"Wall sheet height {h} must be a non-zero multiple of tile_size={tile_size}px."
        )

    num_kinds = h // tile_size
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    png_path = out / f"{name}.png"
    tsx_path = out / f"{name}.tsx"

    sheet.save(png_path)

    rel_png = os.path.relpath(png_path, tsx_path.parent)
    xml_str = generate_tsx_wall_sides(
        name=name,
        tile_size=tile_size,
        png_filename=rel_png,
        num_kinds=num_kinds,
    )
    tsx_path.write_text(xml_str, encoding="utf-8")

    return str(png_path), str(tsx_path)


# ---------------------------------------------------------------------------
# A4 wall tops — blob wangset (mixed, 47 shapes from FLOOR_AUTOTILE_TABLE)
# ---------------------------------------------------------------------------

def export_blob_tops_sheet(
    sheet: Image.Image,
    name: str,
    output_dir: str | Path,
    tile_size: int,
) -> tuple[str, str]:
    """Write A4 wall-top sheet PNG and its blob-wangset TSX to disk.

    The sheet is a pre-assembled 8-col × 6-row-per-kind grid produced by
    convert_mv_a4(). Each 6-row block encodes 47 FLOOR_AUTOTILE_TABLE shapes
    (slots 0-46) plus one transparent padding slot (slot 47).

    The generated TSX uses type="mixed" wangset (blob 8-neighbor), identical to
    the A2 tileset export, so Tiled shows it in the Terrain collection.

    Args:
        sheet:      Pre-assembled RGBA PIL Image from convert_mv_a4() tops output.
                    Width = 8 * tile_size. Height = N_kinds * 6 * tile_size.
        name:       Base name (e.g. "dungeon_tops" → dungeon_tops.png + dungeon_tops.tsx).
        output_dir: Directory to write files into (created if needed).
        tile_size:  Tile width/height in pixels (32 or 48).

    Returns:
        Tuple of (png_path, tsx_path) as str.

    Raises:
        ValueError: if sheet width ≠ 8 * tile_size or height not divisible by 6 * tile_size.
        OSError:    if output_dir is not writable.
    """
    expected_w = SHEET_COLS * tile_size
    w, h = sheet.size
    if w != expected_w:
        raise ValueError(
            f"Wall-tops sheet must be {expected_w}px wide (8 cols × {tile_size}px); got {w}x{h}."
        )
    if h % (SHEET_ROWS * tile_size) != 0:
        raise ValueError(
            f"Wall-tops sheet height {h} must be divisible by "
            f"6 * tile_size = {SHEET_ROWS * tile_size}px."
        )

    # Number of kinds stacked vertically (each = SHEET_ROWS tiles tall = one 47-blob set)
    num_kinds = h // (SHEET_ROWS * tile_size)

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    png_path = out / f"{name}.png"
    tsx_path = out / f"{name}.tsx"

    sheet.save(png_path)

    rel_png = os.path.relpath(png_path, tsx_path.parent)
    # generate_tsx treats num_kinds as num_frames (each = 6 rows of 47 blobs).
    # blob wangid mapping: BLOB_BITMASKS[slot] → tileid=slot per kind.
    xml_str = generate_tsx(
        name=name,
        tile_size=tile_size,
        png_filename=rel_png,
        is_animated=False,
        num_frames=num_kinds,
    )
    tsx_path.write_text(xml_str, encoding="utf-8")

    return str(png_path), str(tsx_path)
