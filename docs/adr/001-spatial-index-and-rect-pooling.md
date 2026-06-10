# ADR 001 — Spatial Grid Indexing and Rect Pooling
> Status: Accepted
> Date: 2026-06-11

---

## 1. Context

In `RenderManager._draw_static_foreground_tiles`, the game engine retrieves and filters visible static foreground tiles by iterating through a flat list of all foreground tiles in the world map (`_fg_occlusion_world`). On larger maps, this list comprehension runs in `O(N_world)` every frame, causing a severe CPU bottleneck (14.9% of total playing CPU).

Additionally, in `_build_screen_occluding_rects`, a new `pygame.Rect` instance is created for each visible tile every frame:
```python
pygame.Rect(wx + cam_x, wy + cam_y, tile_size, tile_size)
```
This causes heavy object allocation and garbage collection overhead (15.6% of CPU).

---

## 2. Decision

We will implement two coordinated optimizations:

1. **Spatial Grid Indexing**:
   - `MapManager` will build a spatial dictionary or 2D list `_fg_occlusion_grid` during initialization:
     ```python
     self._fg_occlusion_grid: dict[tuple[int, int], tuple[int, pygame.Surface, pygame.Surface | None]] = {}
     ```
     mapping `(grid_x, grid_y)` to `(depth, image, occluded_image)`.
   - In `RenderManager._draw_static_foreground_tiles`, we will calculate the visible grid columns and rows based on the viewport bounds and query only the tiles within those bounds, changing the complexity to `O(Viewport)`.

2. **In-Place Rect Pooling**:
   - `RenderManager` will keep a pre-allocated list of `pygame.Rect` objects `self._rect_pool`.
   - Instead of instantiating new `pygame.Rect` instances, we will traverse the visible tiles, reuse Rects from `self._rect_pool`, and assign their `.x` and `.y` properties in-place.
   - If the number of visible tiles exceeds the size of `self._rect_pool`, we will dynamically append new `pygame.Rect` instances to the pool.

---

## 3. Consequences

- **Performance**: Static foreground tile processing and screen rect compilation will scale with viewport size rather than map size. Rect allocations in the loop will drop to zero.
- **Safety**: Safe because `occluding_rects` is discarded at the end of the frame rendering pass and is not stored or shared across threads.
- **Backward Compatibility**: `self._fg_occlusion_world` is kept intact to avoid breaking any unit tests that query it directly, but the main rendering paths will use the optimized spatial grid.
