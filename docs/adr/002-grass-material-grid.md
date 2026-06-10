# ADR 002 — Grass Material Grid Pre-Computation
> Status: Accepted
> Date: 2026-06-11

---

## 1. Context

During rendering, the grass wading effect (`_apply_grass_wading_to_images`) is computed for every visible sprite. This calls `MapManager.get_grass_tile_image_at` for the foot position of each sprite (averaging 19 times per frame, totaling 34,200 calls in a 30s session).

Each call to `get_grass_tile_image_at` performs a coordinate conversion and loops over all map layers in reversed order to check the topmost depth <= 1 tile's material property. This layer scanning creates redundant overhead in a critical rendering hot-path.

---

## 2. Decision

We will optimize the lookup by pre-computing a 2D grid at map load time:

1. **Pre-computed 2D Grid**:
   - `MapManager` will initialize a 2D list `self._grass_grid` of size `(height, width)` during `__init__`.
   - We will populate the grid once using the original scanning logic. For each `(ty, tx)`, `self._grass_grid[ty][tx]` will store the grass tile's `pygame.Surface` if the topmost depth <= 1 tile is grass, or `None` otherwise.

2. **O(1) Direct Lookup**:
   - We will refactor `get_grass_tile_image_at(self, pixel_x, pixel_y)` to perform O(1) direct array access:
     ```python
     grid_pos = self.layout.to_world(pixel_x, pixel_y)
     tx, ty = int(grid_pos[0]), int(grid_pos[1])
     if 0 <= ty < self.height and 0 <= tx < self.width:
         return self._grass_grid[ty][tx]
     return None
     ```

---

## 3. Consequences

- **Performance**: Scanning overhead is completely removed from the per-frame wading pass. Lookup is a simple bounds check and list lookup.
- **Memory**: The 2D list stores references to existing Pygame Surfaces, consuming negligible memory (a few kilobytes).
- **Safety**: Safe because map structures (layers and tilesets) are immutable during gameplay. If a map is reloaded or changed, the `MapManager` is re-instantiated, automatically rebuilding the grid.
