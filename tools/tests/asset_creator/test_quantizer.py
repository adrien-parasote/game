import pytest
import numpy as np
from PIL import Image
from asset_creator.core.quantizer import quantize, load_palettes

def test_tc_002_downscaling_nearest_neighbor():
    """TC-002: Downscaling uses nearest neighbor."""
    noise_map = np.zeros((256, 256), dtype=np.float32)
    noise_map[0:128, 0:128] = 0.5
    palette = [(0,0,0), (128,128,128), (255,255,255)]
    
    img = quantize(noise_map, palette)
    assert img.size == (32, 32)
    
    colors_used = img.getcolors()
    for count, color in colors_used:
        assert color in palette

def test_tc_003_color_quantization_strictness():
    """TC-003: Color quantization strictness."""
    noise_map = np.linspace(0, 1, 256*256).reshape(256,256)
    palette = [(0,0,0), (255,0,0), (0,255,0), (0,0,255)]
    img = quantize(noise_map, palette)
    colors_used = img.getcolors()
    for count, color in colors_used:
        assert color in palette

def test_tc_006_palette_loader(tmp_path):
    """TC-006: Palette loader."""
    palette_file = tmp_path / "palettes.json"
    palette_file.write_text('{"PICO-8": ["#000000", "#1D2B53"]}')
    
    palettes = load_palettes(str(palette_file))
    assert palettes["PICO-8"] == [(0,0,0), (29,43,83)]
