import json


def load_palettes(filepath: str) -> dict[str, list[tuple[int, int, int]]]:
    """
    Load palettes from a JSON file.
    Format: {"Name": ["#RRGGBB", ...]}
    Returns: {"Name": [(R, G, B), ...]}
    """
    with open(filepath, encoding="utf-8") as f:
        data = json.load(f)

    palettes = {}
    for name, hex_colors in data.items():
        colors = []
        for hex_code in hex_colors:
            # Remove '#' if present
            hex_code = hex_code.lstrip('#')
            # Convert hex string to RGB tuple
            if len(hex_code) == 6:
                r = int(hex_code[0:2], 16)
                g = int(hex_code[2:4], 16)
                b = int(hex_code[4:6], 16)
                colors.append((r, g, b))
        palettes[name] = colors

    return palettes
