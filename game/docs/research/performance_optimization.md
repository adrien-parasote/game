# Research Report — Game Engine Performance Optimizations
> Date: 2026-06-11
> Focus: Pygame-CE CPU hot-path rendering bottlenecks, coordinate translations, and tile material scanning optimizations.
> Status: Completed

---

## 1. Domain Context & Research Findings

Our `cProfile` analysis of the current game engine reveals severe CPU bottlenecks in the rendering loop:
- **`_build_screen_occluding_rects`** (12.394s tottime)
- **`_draw_static_foreground_tiles`** (11.838s tottime)
- **`_blit_occluded_tiles_near_player`** (5.564s tottime)
- **`_apply_partial_occlusion`** (4.550s tottime)
- **`get_grass_tile_image_at`** (0.928s tottime)

These hotspots are driven by two main issues:
1. **O(N) List Comprehensions & Linear Searches**: Iterating through all foreground tiles in the world map (`self.game.map_manager._fg_occlusion_world`) every frame to check viewport intersection and player collision.
2. **Object Creation Overhead**: Allocating hundreds of `pygame.Rect` objects every frame in the rendering loop.

### Web Search Results & Technical Feasibility
1. **Pygame-CE Rect Instantiation**: Creating new `pygame.Rect` instances incurs significant Python-to-C overhead. Pygame CE best practices recommend reusing existing `Rect` objects and modifying their attributes in-place (e.g. `.x = ...`, `.y = ...`) or using in-place methods (`move_ip`, `inflate_ip`).
2. **Spatial Culling**: Standard tilemaps index tiles in a 2D array or grid. Instead of a flat list, querying columns and rows corresponding to the camera viewport (`O(Viewport)` complexity) completely eliminates the dependency on total map size.
3. **Caching & O(1) Lookups**: Repeatedly scanning tile layers at a specific grid coordinate is slow. Pre-computing a 2D grid containing only relevant metadata (e.g. tile images with material == "grass" for wading) at map load time resolves lookup overhead.

---

## 2. Adopt, Adapt, or Build Decision

We choose to **Adapt** the current custom rendering pipeline:

| Problem ID | Root Cause | Proposed Decision | Implementation Strategy |
|---|---|---|---|
| **P-001** | O(N) world tile loop + new `Rect` allocations | **Adapt & Caching** | Index foreground tiles in a 2D grid (`_fg_occlusion_grid`). Look up only tiles inside the viewport. Pre-allocate a pool of screen-space `Rect`s and modify their attributes in-place. |
| **P-008** | Repeated layer scans for grass materials | **Adapt & Pre-computation** | Pre-compute a 2D grid of grass tiles (`self._grass_grid`) on map load. Query `self._grass_grid[ty][tx]` in O(1). |
| **P-003** | Particle system overhead | **Adapt** | Batch particle draws and pool active particle objects. |
| **P-004** | Screen-space collision clipping | **Adapt** | Perform bounding box intersection checks in world-space using pre-allocated Rects. |
| **P-006** | darkness overlay recreation | **Adapt** | Dirty flag caching for the overlay. |

---

## 3. Reference & API Citations
- **Pygame Rect attribute modification**: Setting `rect.x` and `rect.y` directly is faster than `rect.move(dx, dy)` because it avoids allocating new objects.
- **Pygame Surface blitting**: Layered pre-rendered surfaces (as implemented via `get_layer_surface` in P-001) are efficient, but the viewport culling and occlusion overlays must be mapped to grid coordinates to scale with map dimensions.
