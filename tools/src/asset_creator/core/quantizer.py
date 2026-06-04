import numpy as np
from PIL import Image


def luminance(color: tuple[int, int, int]) -> float:
    return 0.299 * color[0] + 0.587 * color[1] + 0.114 * color[2]

def quantize_image(noise_map: np.ndarray, palette: list[tuple[int, int, int]]) -> Image.Image:
    """
    Map logical tones (0, 1, 2, 3, 4) to the provided palette.
    The palette is sorted by luminance (darkest to lightest).
    """
    sorted_palette = sorted(palette, key=luminance)

    # Handle if palette has fewer or more than 5 colors
    L = len(sorted_palette)
    if L == 0:
        # Fallback if empty palette: 5-step grayscale
        mapped_palette = [(0,0,0), (64,64,64), (128,128,128), (192,192,192), (255,255,255)]
    elif L < 5:
        # Repeat the lightest color to fill missing highlight slots
        mapped_palette = sorted_palette + [sorted_palette[-1]] * (5 - L)
    elif L == 5:
        # Use all 5 colors directly
        mapped_palette = sorted_palette
    else:
        # More than 5: pick 5 evenly distributed colors
        indices = np.linspace(0, L - 1, 5, dtype=int)
        mapped_palette = [sorted_palette[i] for i in indices]

    h, w = noise_map.shape
    out = np.zeros((h, w, 3), dtype=np.uint8)

    for y in range(h):
        for x in range(w):
            val = noise_map[y, x]
            # Ensure val is strictly between 0 and 4
            if val < 0:
                val = 0
            if val > 4:
                val = 4
            out[y, x] = mapped_palette[val]

    return Image.fromarray(out, "RGB")
