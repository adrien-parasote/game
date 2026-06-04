import pytest
import os
import numpy as np
from PIL import Image

# We will import the modules once they are created
# from src.asset_creator.core.generator import generate_texture
# from src.asset_creator.core.quantizer import quantize_image
# from src.asset_creator.exporters.exporter import export_tile
# from src.asset_creator.config.palette_loader import load_palettes

import xml.etree.ElementTree as ET

def test_tc001_output_dimensions():
    """TC-001: Image output from the quantizer must be exactly 32x32."""
    from src.asset_creator.core.quantizer import quantize_image
    
    # Fake a valid generation output
    fake_gen = np.zeros((32, 32), dtype=int)
    palette = [(0,0,0), (100,100,100), (200,200,200), (255,255,255)]
    
    img = quantize_image(fake_gen, palette)
    assert img.size == (32, 32)
    assert img.mode == "RGB"

def test_tc002_generator_output_format():
    """TC-002: Generator returns a (32, 32) numpy array with values in [0, 1, 2, 3]."""
    from src.asset_creator.core.generator import generate_texture
    
    output = generate_texture("grass", seed=42, density=10)
    assert isinstance(output, np.ndarray)
    assert output.shape == (32, 32)
    assert np.all(np.isin(output, [0, 1, 2, 3]))

def test_tc003_color_quantization_strictness():
    """TC-003: Output image only contains colors present in the sorted palette."""
    from src.asset_creator.core.quantizer import quantize_image
    
    # Generate some random logical indices
    fake_gen = np.random.randint(0, 4, (32, 32))
    # Unsorted palette (to ensure the quantizer sorts it by luminance correctly)
    # Bright red, dark blue, white, black
    palette = [(255,0,0), (0,0,100), (255,255,255), (0,0,0)]
    
    img = quantize_image(fake_gen, palette)
    colors_used = [color for count, color in img.getcolors()]
    
    # All used colors must be in the original palette
    for c in colors_used:
        assert c in palette

def test_tc004_tsx_generation_structure(tmp_path):
    """TC-004: Given tile_name, the generated XML parses successfully as valid XML with tilewidth=32."""
    from src.asset_creator.exporters.exporter import export_tile
    from src.asset_creator.core.quantizer import quantize_image
    
    # We will export to a tmp_path
    os.environ["EXPORT_DIR"] = str(tmp_path)
    
    img = Image.new("RGB", (32, 32))
    png_path, tsx_path = export_tile(img, "stone", 42)
    
    assert os.path.exists(tsx_path)
    
    # Parse XML
    tree = ET.parse(tsx_path)
    root = tree.getroot()
    
    assert root.tag == "tileset"
    assert root.attrib.get("name") == "stone_42"
    assert root.attrib.get("tilewidth") == "32"
    assert root.attrib.get("tileheight") == "32"
    
    image_element = root.find("image")
    assert image_element is not None
    assert image_element.attrib.get("source") == "stone_42.png"

def test_tc005_generator_fallback():
    """TC-005: Unknown texture_type is handled gracefully."""
    from src.asset_creator.core.generator import generate_texture
    
    output = generate_texture("some_unknown_type", seed=42, density=10)
    assert output.shape == (32, 32)
    assert np.all(np.isin(output, [0, 1, 2, 3]))

def test_tc006_palette_loader(tmp_path):
    """TC-006: palettes.json is parsed from hex strings to RGB tuples."""
    from src.asset_creator.config.palette_loader import load_palettes
    import json
    
    fake_json = tmp_path / "palettes.json"
    fake_json.write_text(json.dumps({
        "TestPalette": ["#000000", "#1D2B53", "#008751", "#ABFC4C"]
    }))
    
    palettes = load_palettes(str(fake_json))
    assert "TestPalette" in palettes
    # Ensure it converted hex to tuples
    assert palettes["TestPalette"] == [(0,0,0), (29,43,83), (0,135,81), (171,252,76)]

def test_tc007_determinism():
    """TC-007: Same seed = same ndarray output."""
    from src.asset_creator.core.generator import generate_texture
    
    out1 = generate_texture("grass", seed=42, density=10)
    out2 = generate_texture("grass", seed=42, density=10)
    
    assert np.array_equal(out1, out2)

def test_it001_gui_to_preview_flow():
    """IT-001: GUI triggers background generation thread and updates preview."""
    # We will test the debouncer / generation queue in the GUI layer
    pass

def test_it002_end_to_end_pipeline(tmp_path):
    """IT-002: GUI triggers Generator -> Quantizer -> Exporter (writes valid PNG and TSX)."""
    from src.asset_creator.core.generator import generate_texture
    from src.asset_creator.core.quantizer import quantize_image
    from src.asset_creator.exporters.exporter import export_tile
    
    os.environ["EXPORT_DIR"] = str(tmp_path)
    
    # 1. Generate
    gen_array = generate_texture("grass", seed=100, density=15)
    # 2. Quantize
    palette = [(0,0,0), (50,50,50), (150,150,150), (250,250,250)]
    img = quantize_image(gen_array, palette)
    # 3. Export
    png, tsx = export_tile(img, "grass", 100)
    
    assert os.path.exists(png)
    assert os.path.exists(tsx)

def test_it003_xml_injection_safety(tmp_path):
    """IT-003: Seed/Name cannot break XML structure."""
    from src.asset_creator.exporters.exporter import export_tile
    
    os.environ["EXPORT_DIR"] = str(tmp_path)
    img = Image.new("RGB", (32, 32))
    
    # Malicious texture name
    malicious_name = 'stone" tilewidth="999'
    png, tsx = export_tile(img, malicious_name, 42)
    
    # Should still parse without the attribute being overridden
    tree = ET.parse(tsx)
    root = tree.getroot()
    assert root.attrib.get("tilewidth") == "32"
