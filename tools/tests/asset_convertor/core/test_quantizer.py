import numpy as np
from asset_convertor.core.quantizer import quantize_image


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

def test_tc001_grass_five_colors():
    """TC-001: Handles a 5-color palette, mapping values 0-4."""
    # Create an array that has exactly values 0, 1, 2, 3, 4
    fake_gen = np.zeros((32, 32), dtype=int)
    for i in range(5):
        fake_gen[0, i] = i

    palette = [(0,0,0), (64,64,64), (128,128,128), (192,192,192), (255,255,255)]
    img = quantize_image(fake_gen, palette)
    colors_used = [color for count, color in img.getcolors()]
    assert len(colors_used) == 5
    for p in palette:
        assert p in colors_used

def test_tc002_grass_less_than_five_colors():
    """TC-002: Handles palettes with fewer than 5 colors by repeating the lightest color."""
    fake_gen = np.zeros((32, 32), dtype=int)
    for i in range(5):
        fake_gen[0, i] = i

    palette = [(0,0,0), (128,128,128), (255,255,255)]
    img = quantize_image(fake_gen, palette)
    colors_used = [color for count, color in img.getcolors()]
    # Since the highest tone is padded with the lightest color, we expect exactly 3 unique colors in the output.
    assert len(colors_used) == 3

def test_tc003_grass_more_than_five_colors():
    """TC-003: Handles palettes with more than 5 colors by selecting 5 evenly spaced colors."""
    fake_gen = np.zeros((32, 32), dtype=int)
    for i in range(5):
        fake_gen[0, i] = i

    palette = [(0,0,0), (1,1,1), (2,2,2), (3,3,3), (4,4,4), (5,5,5), (6,6,6)]
    img = quantize_image(fake_gen, palette)
    colors_used = [color for count, color in img.getcolors()]
    assert len(colors_used) == 5
    # The selected colors should be indices 0, 1, 3, 4, 6 in the 7-element array, via np.linspace(0, 6, 5) => [0, 1, 3, 4, 6]
    expected_colors = [palette[0], palette[1], palette[3], palette[4], palette[6]]
    for c in expected_colors:
        assert c in colors_used


def test_empty_palette_falls_back_to_grayscale():
    """L==0: empty palette triggers 5-step grayscale fallback (covers line 19)."""
    # All cells value 0 → should get the darkest grayscale color (0,0,0)
    fake_gen = np.zeros((32, 32), dtype=int)
    img = quantize_image(fake_gen, [])
    assert img.size == (32, 32)
    assert img.mode == "RGB"
    # With empty palette, fallback is 5-step grayscale [0,64,128,192,255]
    # val=0 → (0,0,0)
    assert img.getpixel((0, 0)) == (0, 0, 0)


def test_val_below_zero_clamped_to_zero():
    """Negative noise map values are clamped to 0 before palette lookup (covers line 39)."""
    fake_gen = np.full((32, 32), -3, dtype=int)
    palette = [(10, 10, 10), (50, 50, 50), (100, 100, 100), (150, 150, 150), (200, 200, 200)]
    img = quantize_image(fake_gen, palette)
    # val<0 → clamped to 0 → darkest sorted palette color
    assert img.size == (32, 32)
    colors_used = {c for _, c in img.getcolors()}
    # Only one unique color should appear (all cells clamped to tone 0)
    assert len(colors_used) == 1


def test_val_above_four_clamped_to_four():
    """Noise map values > 4 are clamped to 4 before palette lookup (covers line 41)."""
    fake_gen = np.full((32, 32), 99, dtype=int)
    palette = [(10, 10, 10), (50, 50, 50), (100, 100, 100), (150, 150, 150), (200, 200, 200)]
    img = quantize_image(fake_gen, palette)
    # val>4 → clamped to 4 → lightest sorted palette color
    assert img.size == (32, 32)
    colors_used = {c for _, c in img.getcolors()}
    assert len(colors_used) == 1

