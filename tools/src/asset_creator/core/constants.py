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
