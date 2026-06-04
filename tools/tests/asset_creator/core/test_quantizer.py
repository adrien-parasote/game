import numpy as np
from src.asset_creator.core.quantizer import quantize_image

def test_tc001_output_dimensions():
    """TC-001: Image output from the quantizer must be exactly 32x32."""
    fake_gen = np.zeros((32, 32), dtype=int)
    palette = [(0,0,0), (100,100,100), (200,200,200), (255,255,255)]
    img = quantize_image(fake_gen, palette)
    assert img.size == (32, 32)
    assert img.mode == "RGB"

def test_tc003_color_quantization_strictness():
    """TC-003: Output image only contains colors present in the sorted palette."""
    fake_gen = np.random.randint(0, 4, (32, 32))
    palette = [(255,0,0), (0,0,100), (255,255,255), (0,0,0)]
    img = quantize_image(fake_gen, palette)
    colors_used = [color for count, color in img.getcolors()]
    for c in colors_used:
        assert c in palette
