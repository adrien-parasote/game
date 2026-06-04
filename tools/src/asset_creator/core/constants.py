"""Centralized constants for the Asset Creator Tool."""

# Grid and size constraints
TILE_SIZE: int = 32
SUBTILE_SIZE: int = 16

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
