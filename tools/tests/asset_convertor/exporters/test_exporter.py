import os
import xml.etree.ElementTree as ET

from asset_convertor.exporters.exporter import export_tile
from PIL import Image


def test_tc004_tsx_generation_structure(tmp_path):
    """TC-004: Generated XML parses successfully as valid XML with tilewidth=32."""
    os.environ["EXPORT_DIR"] = str(tmp_path)
    img = Image.new("RGB", (32, 32))
    png_path, tsx_path = export_tile(img, "stone", 42)
    assert os.path.exists(tsx_path)
    tree = ET.parse(tsx_path)
    root = tree.getroot()
    assert root.tag == "tileset"
    assert root.attrib.get("name") == "stone_42"
    assert root.attrib.get("tilewidth") == "32"
    assert root.attrib.get("tileheight") == "32"
    image_element = root.find("image")
    assert image_element is not None
    assert image_element.attrib.get("source") == "stone_42.png"

def test_it003_xml_injection_safety(tmp_path):
    """IT-003: Seed/Name cannot break XML structure."""
    os.environ["EXPORT_DIR"] = str(tmp_path)
    img = Image.new("RGB", (32, 32))
    malicious_name = 'stone" tilewidth="999'
    png, tsx = export_tile(img, malicious_name, 42)
    tree = ET.parse(tsx)
    root = tree.getroot()
    assert root.attrib.get("tilewidth") == "32"
