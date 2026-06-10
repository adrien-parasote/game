# Strategic Blueprint — Performance Optimizations
> Date: 2026-06-11
> Target: Pygame-CE Game Engine optimizations

---

## 1. Success Metrics

Our objective is to restore the game engine to 60 FPS on standard development machines:

| Metric | Baseline | Target | Timeline |
|---|---|---|---|
| **Average Frame Time** | 45.73 ms | **< 16.7 ms** (60 FPS) | Immediately after implementation |
| **p95 Frame Time** | 46.00 ms | **< 20.0 ms** | Immediately after implementation |
| **p99 Frame Time** | 52.00 ms | **< 33.0 ms** | Immediately after implementation |
| **Spikes > 33 ms** | 100.0% | **< 1.0%** of frames | Immediately after implementation |
| **Memory Delta** | +0.80 KB/frame | **< 1.0 KB/frame** | Immediately after implementation |
| **GC Pressure** | 3 gen0 coll / 30s | **< 30 gen0 coll / 30s** | Immediately after implementation |

---

## 2. Constraint Mapping

- **Pygame-CE Compatibility**: Must remain compatible with pygame-ce v2.5.7+.
- **Visual Conformance**: Output rendering must be visually identical (pixel-perfect) to the unoptimized engine. No visual bugs, flickering, or occlusion errors.
- **API Contracts**: `RenderManager.draw_foreground()` must return a list of `(pygame.Rect, int, pygame.Surface)` tuples. This is a public contract tested by unit tests (e.g. `test_draw_foreground_occluding_tile_returns_tuple_list`).
- **Memory Boundaries**: Memory footprint growth must be negligible (no persistent reference leaks of pygame Surfaces).

---

## 3. Architecture Direction

We will implement local optimizations within `MapManager` and `RenderManager`:
- **Spatial Indexing**: `MapManager` will index static foreground tiles by their `(grid_x, grid_y)` coordinates during map load, changing culling complexity from O(N_world) to O(Viewport).
- **In-Place Rect Pool**: `RenderManager` will manage a pool of `pygame.Rect` objects, modifying their attributes in-place to avoid the garbage collection and allocation overhead of constructing new `Rect` instances.
- **O(1) Grass Material Grid**: `MapManager` will pre-compute a 2D grid of grass tiles to avoid scanning all layers in reversed order for wading checks.

---

## 4. Exclusions & Boundaries

- **No Third-Party Spatial Partitioning Libraries**: We will not pull in dependencies like `R-Tree` or `quadtree` libraries. Simple 2D grid/array indexing is sufficient for a grid-based tilemap and keeps the codebase light.
- **No Asset Modifiers**: No modification of sprite sheets, tilesets, or TMJ map files on disk.
- **No Multi-Threading**: All optimizations must remain single-threaded to avoid introducing complexity or race conditions in Pygame.

---

## 5. Risk Assessment

| Risk | Sévérité | Probabilité | Atténuation |
|---|---|---|---|
| **Stale Cache / Out of Sync** | 🟠 Élevée | 🟡 Moyenne | Ensure `RenderManager.reset_occ_cache()` or map changes fully rebuild/clear all pre-computed grids and pools. |
| **Memory leaks in Pool** | 🟡 Moyenne | 🟢 Faible | The `pygame.Rect` objects are lightweight and bounded by maximum viewport tiles (~2000). Pool will grow dynamically but never shrink, setting a hard cap on memory. |
| **Test regressions** | 🟠 Élevée | 🟡 Moyenne | Run full pytest suite before and after every optimization. Refuse any change that breaks existing tests. |
