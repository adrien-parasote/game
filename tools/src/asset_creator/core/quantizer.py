import json

import numpy as np
from PIL import Image


def quantize(noise_map: np.ndarray, palette: list[tuple[int, int, int]]) -> Image.Image:
    """Downscale to 32x32 using nearest neighbor and apply strict palette based on luminance."""
    # Downscale to 32x32 (TC-002)
    img_256 = Image.fromarray((noise_map * 255).astype(np.uint8))
    img_32 = img_256.resize((32, 32), Image.Resampling.NEAREST)

    # Sort palette by luminance
    def luminance(c):
        return 0.299*c[0] + 0.587*c[1] + 0.114*c[2]

    sorted_palette = sorted(palette, key=luminance)
    num_colors = len(sorted_palette)

    arr = np.array(img_32)
    h, w = arr.shape
    out = np.zeros((h, w, 3), dtype=np.uint8)

    # Map pixels to the sorted palette (TC-003)
    for y in range(h):
        for x in range(w):
            val = arr[y, x] / 255.0  # 0 to 1
            idx = int(val * num_colors)
            if idx >= num_colors:
                idx = num_colors - 1
            out[y, x] = sorted_palette[idx]

    return Image.fromarray(out, "RGB")

def load_palettes(filepath: str) -> dict:
    """Load palettes from a JSON file (TC-006)."""
    with open(filepath, encoding="utf-8") as f:
        data = json.load(f)

    palettes = {}
    for name, hex_colors in data.items():
        colors = []
        for h in hex_colors:
            h = h.lstrip('#')
            colors.append(tuple(int(h[i:i+2], 16) for i in (0, 2, 4)))
        palettes[name] = colors
    return palettes
