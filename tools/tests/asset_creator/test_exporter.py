import os
import pytest
from PIL import Image
import xml.etree.ElementTree as ET
from asset_creator.exporters.exporter import export, derive_tile_name

def test_tc_004_tsx_xml_generation(tmp_path):
    """TC-004: .tsx XML generation structure."""
    img = Image.new("RGB", (32, 32))
    orig_output = os.getcwd()
    os.chdir(tmp_path)
    try:
        export(img, "stone_42")
        tsx_path = "output/stone_42.tsx"
        assert os.path.exists(tsx_path)
        
        tree = ET.parse(tsx_path)
        root = tree.getroot()
        assert root.tag == "tileset"
        assert root.attrib["name"] == "stone_42"
        assert root.attrib["tilewidth"] == "32"
        
        image_tag = root.find("image")
        assert image_tag is not None
        assert image_tag.attrib["source"] == "stone_42.png"
    finally:
        os.chdir(orig_output)

def test_tc_005_tile_name_derivation():
    """TC-005: tile_name derivation."""
    assert derive_tile_name("stone", 42) == "stone_42"
    assert derive_tile_name("Dark Wood", 7) == "dark_wood_7"
