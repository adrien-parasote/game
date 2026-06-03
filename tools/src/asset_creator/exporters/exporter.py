import os
import xml.etree.ElementTree as ET

from PIL import Image


def derive_tile_name(texture_type: str, seed: int) -> str:
    """Derive tile name (TC-005)."""
    return f"{texture_type.lower().replace(' ', '_')}_{seed}"

def export(image: Image.Image, tile_name: str):
    """Export the PNG and TSX file to output/ (TC-004, IT-003)."""
    out_dir = "output"
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)

    png_path = os.path.join(out_dir, f"{tile_name}.png")
    tsx_path = os.path.join(out_dir, f"{tile_name}.tsx")

    image.save(png_path)

    # TSX XML
    root = ET.Element("tileset", version="1.10", tiledversion="1.10.2",
                      name=tile_name, tilewidth="32", tileheight="32",
                      tilecount="1", columns="1")
    ET.SubElement(root, "image", source=f"{tile_name}.png", width="32", height="32")

    tree = ET.ElementTree(root)
    tree.write(tsx_path, encoding="UTF-8", xml_declaration=True)
