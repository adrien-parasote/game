"""Centralized constants for the Asset Creator Tool."""

# Grid and size constraints
TILE_SIZE: int = 32
SUBTILE_SIZE: int = 16
NUM_BLOB_TILES: int = 47

# Blob bitmasks for autotile pipeline
BLOB_BITMASKS: tuple[int, ...] = (
    0,
    2,
    8,
    10,
    11,
    16,
    18,
    22,
    24,
    26,
    27,
    30,
    31,
    64,
    66,
    72,
    74,
    75,
    80,
    82,
    86,
    88,
    90,
    91,
    94,
    95,
    104,
    106,
    107,
    120,
    122,
    123,
    126,
    127,
    208,
    210,
    214,
    216,
    218,
    219,
    222,
    223,
    248,
    250,
    251,
    254,
    255,
)

# Edge mask generation thresholds
MASK_THRESHOLD: float = 0.5

# Noise defaults
DEFAULT_NOISE_SCALE: float = 0.15
DEFAULT_OCTAVES: int = 3
DEFAULT_PERSISTENCE: float = 0.5
DEFAULT_LACUNARITY: float = 2.0
DEFAULT_DENSITY: float = 0.3
DEFAULT_DETAIL_SCALE: float = 0.5
DEFAULT_DETAIL_STRENGTH: float = 0.06
DEFAULT_DITHER_MATRIX_SIZE: int = 4
DEFAULT_EDGE_WIDTH: int = 4
DEFAULT_EDGE_NOISE_SCALE: float = 0.3

# Border effect coefficients
BORDER_SHADOW_FACTOR: float = 0.7
BORDER_HIGHLIGHT_FACTOR: float = 1.2

# Dithering threshold matrix
BAYER_4X4: tuple[tuple[int, int, int, int], ...] = (
    (0, 8, 2, 10),
    (12, 4, 14, 6),
    (3, 11, 1, 9),
    (15, 7, 13, 5),
)

# AppState defaults
DEFAULT_OUTPUT_DIR: str = "assets/images/autotiles"
DEFAULT_TSX_DIR: str = "assets/tiled/autotiles"

# Default palette color tuples (shadow, base, highlight, accent)
DEFAULT_COLOR_SHADOW: tuple[int, int, int] = (45, 90, 30)
DEFAULT_COLOR_BASE: tuple[int, int, int] = (62, 124, 39)
DEFAULT_COLOR_HIGHLIGHT: tuple[int, int, int] = (90, 158, 58)
DEFAULT_COLOR_ACCENT: tuple[int, int, int] = (123, 192, 79)

# Pygame preview settings
PREVIEW_GRID_COLS: int = 12
PREVIEW_GRID_ROWS: int = 8
PREVIEW_MINIMAP_MARGIN: int = 16
PREVIEW_BG_COLOR: tuple[int, int, int] = (30, 30, 30)
PREVIEW_GRID_COLOR: tuple[int, int, int] = (50, 50, 50)
PREVIEW_TEXT_COLOR: tuple[int, int, int] = (200, 200, 200)

# --- Procedural Grass Constants ---

DEFAULT_TEXTURES = ["Grass"]

DEFAULT_PALETTES = {
    "Grass (Spring)": [(78, 122, 40), (115, 168, 55), (161, 214, 73), (212, 245, 110), (235, 255, 160)],
    "Grass (Summer)": [(20, 77, 36), (38, 115, 48), (62, 158, 55), (99, 199, 77), (145, 230, 100)],
    "Grass (Autumn)": [(92, 48, 21), (138, 83, 31), (186, 126, 39), (227, 177, 68), (250, 215, 110)],
    "Grass (Winter)": [(45, 66, 74), (74, 105, 112), (116, 153, 158), (174, 209, 214), (220, 240, 242)],
    "Grass (Crimson)": [(70, 10, 10), (120, 30, 30), (175, 55, 55), (220, 90, 90), (245, 140, 130)],
    "Grass (Teal)":    [(10, 60, 65), (20, 100, 105), (40, 150, 155), (80, 200, 200), (140, 235, 230)],
    "Grass (Snow)":    [(100, 120, 130), (160, 185, 195), (200, 220, 228), (230, 245, 250), (250, 255, 255)],
    "Grass (Purple)":  [(45, 20, 70), (85, 45, 130), (130, 80, 185), (175, 125, 225), (215, 175, 250)],
    "Grass (Savanna)": [(95, 80, 20), (145, 125, 35), (190, 170, 55), (225, 210, 90), (248, 238, 150)],
}

# Tone -1: Transparent
# --- CLASSIC (Slynyrd) ---
TUFT_CLASSIC_RIGHT = [
    [-1, -1,  3,  3],
    [-1,  3,  2,  2],
    [ 2,  2,  2, -1],
    [ 0,  2,  0, -1],
    [ 0,  0, -1, -1]
]
TUFT_CLASSIC_LEFT = [
    [ 3,  3, -1, -1],
    [ 2,  2,  3, -1],
    [-1,  2,  2,  2],
    [-1,  0,  2,  0],
    [-1, -1,  0,  0]
]
TUFT_CLASSIC_V = [
    [ 3, -1, -1,  3],
    [ 2,  3,  3,  2],
    [ 2,  2,  2,  2],
    [ 0,  2,  2,  0],
    [-1,  0,  0, -1]
]

# --- SHORT (Mossy) ---
TUFT_SHORT_1 = [[3], [2]]
TUFT_SHORT_2 = [[3], [0]]
TUFT_SHORT_3 = [[3, 3], [2, 2]]

# --- CURLY (Wavy) ---
TUFT_CURLY_1 = [[3, 3], [2, -1]]
TUFT_CURLY_2 = [[-1, 3], [ 2, 2]]
TUFT_CURLY_3 = [[ 3, -1], [ 3,  2], [-1,  2]]

# --- WILD (Long Diagonals) ---
TUFT_WILD_1 = [[-1, 3], [ 3, 2], [ 2, 0], [ 0, -1]]
TUFT_WILD_2 = [[ 3, -1], [ 2, 3], [ 0, 2], [-1, 0]]

# --- CRESCENT (5-tone curved blade shapes) ---
TUFT_CRESCENT_1 = [
    [-1, -1,  4,  4, -1],
    [-1,  3,  4,  4,  3],
    [ 2,  3,  3,  3,  2],
    [ 1,  2,  2,  2,  1],
    [-1,  0,  0,  0, -1]
]
TUFT_CRESCENT_2 = [
    [-1,  4, -1, -1, -1],
    [ 4,  4,  3, -1, -1],
    [ 3,  3,  2,  3, -1],
    [ 2,  2,  1,  2,  2],
    [-1,  0, -1,  0,  0]
]

# --- SWEEP (5-tone diagonal blade forms) ---
TUFT_SWEEP_LEFT = [
    [-1, -1, -1,  4,  4],
    [-1, -1,  3,  4, -1],
    [-1,  3,  3, -1, -1],
    [ 2,  2,  2, -1, -1],
    [ 0,  0,  1,  2, -1]
]
TUFT_SWEEP_RIGHT = [
    [ 4,  4, -1, -1, -1],
    [-1,  4,  3, -1, -1],
    [-1, -1,  3,  3, -1],
    [-1, -1,  2,  2,  2],
    [-1,  2,  1,  0,  0]
]

# --- ARCH (5-tone wide dome shape) ---
TUFT_ARCH = [
    [-1,  4,  4,  4, -1],
    [ 3,  4,  4,  4,  3],
    [ 2,  3,  3,  3,  2],
    [ 1,  2,  2,  2,  1],
    [ 0,  0,  0,  0,  0]
]
