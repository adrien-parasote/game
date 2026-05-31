"""PNG exporter for tileset images.

Validates and exports tileset strip PNG files for use in Tiled Map Editor.
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image

TILE_SIZE = 32


def validate_tileset(image: Image.Image, tile_size: int = TILE_SIZE) -> list[str]:
    """Validate tileset image. Returns list of error messages (empty = valid).

    Checks:
    - Height matches tile_size
    - Width is a multiple of tile_size
    - No individual tile is fully transparent (L-MAP-003)
    """
    errors: list[str] = []

    if image.height != tile_size:
        errors.append(
            f"Image height {image.height}px does not match tile size {tile_size}px"
        )

    if image.width % tile_size != 0:
        errors.append(
            f"Image width {image.width}px is not a multiple of tile size {tile_size}px"
        )

    if image.height == tile_size and image.width % tile_size == 0:
        tile_count = image.width // tile_size
        for i in range(tile_count):
            x = i * tile_size
            tile = image.crop((x, 0, x + tile_size, tile_size))
            if tile.mode != "RGBA":
                tile = tile.convert("RGBA")
            alpha_data = tile.getchannel("A")
            if alpha_data.getextrema()[1] == 0:
                errors.append(f"Tile {i} is fully transparent")

    return errors


def export_png(
    tileset_image: Image.Image,
    output_path: Path,
    tile_size: int = TILE_SIZE,
) -> Path:
    """Export tileset as PNG strip. Validates before saving.

    Args:
        tileset_image: The assembled tileset strip image.
        output_path: Destination path for the PNG file.
        tile_size: Size of each tile in pixels.

    Returns:
        The output path where the file was saved.

    Raises:
        ValueError: If tileset validation fails.
        OSError: If the file cannot be written.
    """
    errors = validate_tileset(tileset_image, tile_size)
    if errors:
        raise ValueError(
            "Tileset validation failed:\n" + "\n".join(f"  - {e}" for e in errors)
        )

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    tileset_image.save(output_path, "PNG")
    return output_path
