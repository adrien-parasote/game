# Research — P-001 Optimization: Rendering Bottlenecks
> Stage: 🔬 DISCOVER
> Date: 2026-06-11
> Topic: Optimizing _build_screen_occluding_rects and _blit_occluded_tiles_near_player in render_manager.py

---

## 1. Domain Context

In Pygame/pygame-ce games, when rendering tilemaps with layers and occlusion, the main loop must run at 60 FPS (approx. 16.6ms per frame budget).
When doing foreground rendering:
- Static foreground elements do not change position, so their world positions are fixed.
- Viewport culling (clipping to the screen/camera bounds) is required to avoid rendering or processing off-screen elements.
- Iterating a list of 400+ tiles every frame in Python incurs significant CPU overhead compared to C-level loops or smaller pre-filtered lists.

## 2. Competitive Landscape & Existing Solutions

- **pyscroll / pytmx**:
  Uses viewport-aligned chunking or pre-computed structures. By tracking the viewport bounding box and filtering tiles in world-space first, the loop size is reduced from the entire map size (hundreds of tiles) to only the active tiles visible on screen (typically <50 tiles).
- **Single-pass list filter**:
  Instead of multiple independent functions iterating the entire tile cache and performing viewport/depth culling, the active set of visible tiles is compiled once per frame. All subsequent rendering passes (building collision rects, applying partial transparency near the player) operate on this tiny subset.

## 3. Technical Feasibility

### Viewport Cull List Comprehension
In Python, list comprehensions run at C-speed and are significantly faster than explicit `for` loops with multiple conditions.
We can compile the visible tiles in `_draw_static_foreground_tiles` via:
```python
self._frame_visible_fg_tiles = [
    t for t in self.game.map_manager._fg_occlusion_world
    if t[2] > player_depth  # depth check
    and t[0] + tile_size > vp_left and t[0] < vp_right  # AABB x
    and t[1] + tile_size > vp_top and t[1] < vp_bottom  # AABB y
]
```
For a typical map, this filters ~480 tiles down to ~0-20 visible foreground tiles in a single pass.
Then `_build_screen_occluding_rects` and `_blit_occluded_tiles_near_player` only iterate over `self._frame_visible_fg_tiles`, reducing their iteration counts by 95%+.

### Backward Compatibility / Unit Tests
Since unit tests call the private methods directly to assert specific isolation behaviors, we must provide a fallback:
```python
visible_tiles = getattr(self, "_frame_visible_fg_tiles", None)
if visible_tiles is None:
    # Fallback to full list iteration for direct method calls from tests
    visible_tiles = self.game.map_manager._fg_occlusion_world
```

## 4. Decision: Adopt / Adapt / Build-New

**→ ADAPT**
We will adapt the existing `_draw_static_foreground_tiles` and its helper methods to use a single-pass frame-level visible tiles cache. This maintains exact function signatures and backward compatibility for all existing tests while delivering maximum performance.

## 5. Next Steps
Move to STRATEGY to plan the structural blueprint and verify constraints.
