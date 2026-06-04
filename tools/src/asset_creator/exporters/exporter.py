import os
import xml.etree.ElementTree as ET
from PIL import Image

def export_tile(image: Image.Image, texture_type: str, seed: int) -> tuple[str, str]:
    """
    Save the tile as PNG and generate the corresponding .tsx file.
    Output goes to EXPORT_DIR env var (for testing) or default 'output/'.
    """
    output_dir = os.environ.get("EXPORT_DIR", "output")
    os.makedirs(output_dir, exist_ok=True)
    
    tile_name = f"{texture_type}_{seed}"
    
    # We MUST escape or strip malicious names just in case, or let xml.etree handle it
    # ET.Element will handle attribute escaping correctly when writing XML
    
    png_filename = f"{tile_name}.png"
    tsx_filename = f"{tile_name}.tsx"
    
    png_path = os.path.join(output_dir, png_filename)
    tsx_path = os.path.join(output_dir, tsx_filename)
    
    # Save PNG
    image.save(png_path)
    
    # Generate TSX
    root = ET.Element("tileset", version="1.10", tiledversion="1.10.2", name=tile_name, tilewidth="32", tileheight="32", tilecount="1", columns="1")
    image_element = ET.SubElement(root, "image", source=png_filename, width="32", height="32")
    
    tree = ET.ElementTree(root)
    # xml declaration is standard
    tree.write(tsx_path, encoding="UTF-8", xml_declaration=True)
    
    return png_path, tsx_path
