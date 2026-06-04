import random

import numpy as np
from asset_creator.core.constants import (
    TUFT_CLASSIC_LEFT,
    TUFT_CLASSIC_RIGHT,
    TUFT_CLASSIC_V,
    TUFT_CURLY_1,
    TUFT_CURLY_2,
    TUFT_CURLY_3,
    TUFT_SHORT_1,
    TUFT_SHORT_2,
    TUFT_SHORT_3,
    TUFT_WILD_1,
    TUFT_WILD_2,
)


def apply_stamp(grid: np.ndarray, cluster: list[list[int]], x: int, y: int, tone: int):
    """Stamp a 2D binary cluster onto the grid with toroidal wrapping."""
    for dy, row in enumerate(cluster):
        for dx, val in enumerate(row):
            if val == 1:
                grid[(y + dy) % 32, (x + dx) % 32] = tone

def apply_composite_stamp(grid: np.ndarray, stamp: list[list[int]], x: int, y: int):
    """Stamp a 2D composite cluster (tones directly in the matrix, -1 for transparent)."""
    for dy, row in enumerate(stamp):
        for dx, val in enumerate(row):
            if val != -1:
                grid[(y + dy) % 32, (x + dx) % 32] = val

def generate_texture(texture_type: str, seed: int, density: int, sub_type: str = "classic") -> np.ndarray:
    """Generate procedural 32x32 texture using Slynyrd's Key Clusters Kitbashing."""
    rng = random.Random(seed)
    grid = np.ones((32, 32), dtype=int)

    texture_type = texture_type.lower()
    sub_type = sub_type.lower()

    if texture_type == "grass":
        if sub_type == "short":
            tufts = [TUFT_SHORT_1, TUFT_SHORT_2, TUFT_SHORT_3]
        elif sub_type == "curly":
            tufts = [TUFT_CURLY_1, TUFT_CURLY_2, TUFT_CURLY_3]
        elif sub_type == "wild":
            tufts = [TUFT_WILD_1, TUFT_WILD_2]
        else: # Classic
            tufts = [TUFT_CLASSIC_RIGHT, TUFT_CLASSIC_LEFT, TUFT_CLASSIC_V]

        # 1. Very light background noise to break up the flat Tone 1
        for _ in range(density * 3):
            grid[rng.randint(0, 31), rng.randint(0, 31)] = rng.choice([1, 2])

        # 2. Scatter Kitbash Tufts with Jittered Grid to prevent obvious repetition
        base_tufts = []
        num_tufts = density * 3
        grid_size = int(np.sqrt(num_tufts))
        if grid_size > 0:
            step = 32.0 / grid_size
            for gy in range(grid_size):
                for gx in range(grid_size):
                    x = int(gx * step + rng.uniform(0, step)) % 32
                    y = int(gy * step + rng.uniform(0, step)) % 32
                    base_tufts.append((x, y, rng.choice(tufts)))

        # Add some purely random tufts for an organic feel
        for _ in range(density):
            base_tufts.append((rng.randint(0, 31), rng.randint(0, 31), rng.choice(tufts)))

        # 3. Create virtual neighbors to guarantee seamless Z-order wrapping
        all_tufts = []
        for offset_y in [-32, 0, 32]:
            for offset_x in [-32, 0, 32]:
                for x, y, tuft in base_tufts:
                    all_tufts.append((x + offset_x, y + offset_y, tuft))

        # 4. Sort strictly by Y to enforce pixel-art depth rules (lower Y is behind)
        all_tufts.sort(key=lambda t: t[1])

        # 5. Draw all tufts (clipped to the 32x32 grid)
        for x, y, tuft in all_tufts:
            for dy, row in enumerate(tuft):
                for dx, val in enumerate(row):
                    if val != -1:
                        px = x + dx
                        py = y + dy
                        if 0 <= px < 32 and 0 <= py < 32:
                            grid[py, px] = val
    return grid
