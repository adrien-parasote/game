# Technical Specification — P-001: Foreground Rendering Optimization [Implementation]

> Document type: Implementation
> **Source Files:** `[render_manager.py](../../src/engine/render_manager.py#L1)`, `[manager.py](../../src/map/manager.py#L1)`
> **Covers:** P-001 (foreground tile pre-rendering + world-space occluding rect cache), P-008 (grass material pre-computation)
> **Research:** `[performance_optimization.md](../research/performance_optimization.md#1-domain-context--research-findings)`
> **Related specs:** `[camera-rendering.md](./camera-rendering.md#1-context--objective)`, `[performance-system.md](./performance-system.md#1-hot-path-rendering-optimizations)`

---

## 1. Context & Objective

### 1.1 Baseline Problem

`_draw_static_foreground_tiles` in `render_manager.py` costs **~11.8 ms/frame** (11.838 s / 1800 frames) and `_build_screen_occluding_rects` costs **~12.4 ms/frame** (12.394 s / 1800 frames). Together, static foreground rendering and rect building consume **~30% of the entire CPU budget**.

The primary causes are:
1. **O(N_world) Iterations**: The list comprehension filters all static foreground tiles in the world map (`_fg_occlusion_world`) to determine viewport intersection.
2. **Object Creation Overhead**: Every visible tile requires instantiating a new `pygame.Rect` object in screen-space every frame.
3. **Redundant Layer Scanning**: `get_grass_tile_image_at` scans all layers top-to-bottom for wading checks (called ~19 times/frame).

**Objective:** Use spatial grid culling to reduce the culling complexity to `O(Viewport)`, implement in-place `pygame.Rect` pooling to drop allocation rate to zero, and pre-compute a 2D grass material grid for `O(1)` wading lookups.

### 1.2 Architecture Direction

```
draw_foreground()
└── _draw_static_foreground_tiles()
    ├── _blit_foreground_surface()
    ├── Spatial Grid Lookup (O(Viewport) from _fg_occlusion_grid)
    ├── _build_screen_occluding_rects()   ← Uses self._rect_pool in-place
    └── _blit_occluded_tiles_near_player()← Scans 3x3 grid around player (O(1))
```

---

## 2. Constraints

| Tier | Examples |
|------|----------|
| **Always do** | Run tests before committing, reuse `pygame.Rect` objects from `self._rect_pool` rather than allocating new ones in rendering hot-paths, use `_fg_occlusion_grid` for viewport queries. |
| **Ask first** | Add new public methods to `RenderManager` or `MapManager`, change existing unit test structures. |
| **Never do** | Remove the fallback/compatibility paths required by unit tests, allocate temporary `Rect`s inside loops, make external library imports. |

---

## 3. Cross-Spec Contracts

### Produces

| Path / Identifier | Format | Schema location | Consumers |
|---|---|---|---|
| `MapManager._fg_occlusion_grid` | `dict[tuple[int, int], tuple[int, Surface, Surface\|None]]` | This spec § 4.1 | `[RenderManager._draw_static_foreground_tiles](../../src/engine/render_manager.py#L140)` |
| `MapManager._grass_grid` | `list[list[Surface\|None]]` | This spec § 4.2 | `[MapManager.get_grass_tile_image_at](../../src/map/manager.py#L428)` |

### Consumes

| Path / Identifier | Format | Schema location | Producer |
|---|---|---|---|
| `MapManager._fg_occlusion_world` | `list[tuple[int, int, int, Surface, Surface\|None]]` | `[p001-foreground-rendering.md](./p001-foreground-rendering.md#2-mapmanager-changes)` | `[MapManager](../../src/map/manager.py#L12)` |

### Public Interface

| Type | Identifier | Documented at |
|---|---|---|
| Method | `get_grass_tile_image_at(pixel_x, pixel_y)` | This spec § 4.3 |

### External Invocations

| Type | Invoked | Defined in |
|---|---|---|
| Method | `colliderect` | `[RenderManager._draw_static_foreground_tiles](../../src/engine/render_manager.py#L140)` |

### Tracked Concepts

| Concept | Status in this spec | Mentioned in |
|---|---|---|
| `occluding_rects` | Reused from Rect pool | `[camera-rendering.md](./camera-rendering.md#3-rendering-loop-deconstruction)` |

---

## 4. MapManager Changes

### 4.1 `_fg_occlusion_grid` Creation

A dictionary `self._fg_occlusion_grid` mapping `(col, row)` grid coordinates to `(depth, image, occluded_image)` is populated during `__init__`:
```python
self._fg_occlusion_grid: dict[tuple[int, int], tuple[int, pygame.Surface, pygame.Surface | None]] = {}
```

Inside `_build_fg_occlusion_world()`, append to `self._fg_occlusion_grid`:
```python
# During the loop over layers, rows (y) and columns (x):
self._fg_occlusion_grid[(x, y)] = (tile.depth, tile.image, tile.occluded_image)
```

### 4.2 `_grass_grid` Pre-Computation

Pre-compute a 2D list `self._grass_grid` at initialization. `self._grass_grid[ty][tx]` stores the `pygame.Surface` of the grass tile if the topmost tile at `(tx, ty)` with depth $\le 1$ has material == "grass", and `None` otherwise.

We implement `_build_grass_grid(self) -> None`:
```python
def _build_grass_grid(self) -> None:
    """Pre-compute a 2D grid of grass tile images for O(1) wading checks."""
    self._grass_grid = [[None for _ in range(self.width)] for _ in range(self.height)]
    for y in range(self.height):
        for x in range(self.width):
            # Scan layers top-to-bottom (reversed order)
            for layer_id in reversed(self.layer_order):
                layer_data = self.layers.get(layer_id)
                if not layer_data:
                    continue
                tile_id = layer_data[y][x]
                if tile_id == 0 or tile_id not in self.tiles:
                    continue
                tile = self.tiles[tile_id]
                if getattr(tile, "depth", 0) > 1:
                    continue
                props = getattr(tile, "properties", {}) or {}
                if props.get("material") == "grass":
                    self._grass_grid[y][x] = tile.image
                break
```

Call `self._build_grass_grid()` in `MapManager.__init__`.

### 4.3 `get_grass_tile_image_at` Refactoring

Refactor to perform `O(1)` direct array access:
```python
def get_grass_tile_image_at(self, pixel_x: int, pixel_y: int) -> "pygame.Surface | None":
    grid_pos = self.layout.to_world(pixel_x, pixel_y)
    tx, ty = int(grid_pos[0]), int(grid_pos[1])
    if 0 <= ty < self.height and 0 <= tx < self.width:
        return self._grass_grid[ty][tx]
    return None
```

---

## 5. RenderManager Changes

### 5.1 `__init__` Pool Allocation

Initialize a pool of reusable screen-space `pygame.Rect` objects:
```python
# Pool size 2000 is sufficient to cover standard viewport bounds (40x22 tiles)
self._rect_pool = [pygame.Rect(0, 0, game.tile_size, game.tile_size) for _ in range(2000)]
```

### 5.2 `_draw_static_foreground_tiles` Viewport Query

Query only coordinates overlapping the viewport:
```python
def _draw_static_foreground_tiles(
    self,
    cam_offset: pygame.Vector2,
    walk_active: bool,
    player_screen_rect: pygame.Rect,
    player_depth: int,
    occluding_rects: OccludingRect,
) -> BlitSequence:
    self._blit_foreground_surface(cam_offset, player_depth)

    tile_size = self.game.tile_size
    vp = self._viewport_world

    start_col = max(0, int(vp.left // tile_size))
    end_col = min(self.game.map_manager.width, int(math.ceil(vp.right / tile_size)))
    start_row = max(0, int(vp.top // tile_size))
    end_row = min(self.game.map_manager.height, int(math.ceil(vp.bottom / tile_size)))

    self._frame_visible_fg_tiles = []
    for y in range(start_row, end_row):
        wy = y * tile_size
        for x in range(start_col, end_col):
            tile_info = self.game.map_manager._fg_occlusion_grid.get((x, y))
            if tile_info:
                depth, img, occ_img = tile_info
                if depth > player_depth:
                    self._frame_visible_fg_tiles.append((x * tile_size, wy, depth, img, occ_img))

    self._build_screen_occluding_rects(cam_offset, player_depth, occluding_rects)
    if not walk_active:
        self._blit_occluded_tiles_near_player(cam_offset, player_screen_rect, player_depth)

    self._frame_visible_fg_tiles = None
    return []
```

### 5.3 `_build_screen_occluding_rects` Rect Reuse

Modify pre-allocated `Rect` properties in-place to avoid heap allocations:
```python
def _build_screen_occluding_rects(
    self,
    cam_offset: pygame.Vector2,
    player_depth: int,
    occluding_rects: OccludingRect,
) -> None:
    cam_x = int(cam_offset.x)
    cam_y = int(cam_offset.y)
    tile_size = self.game.tile_size

    visible_tiles = getattr(self, "_frame_visible_fg_tiles", None)
    if visible_tiles is not None:
        pool_len = len(self._rect_pool)
        for i, (wx, wy, depth, img, _occ) in enumerate(visible_tiles):
            if i < pool_len:
                rect = self._rect_pool[i]
                rect.x = wx + cam_x
                rect.y = wy + cam_y
                rect.width = tile_size
                rect.height = tile_size
            else:
                rect = pygame.Rect(wx + cam_x, wy + cam_y, tile_size, tile_size)
                self._rect_pool.append(rect)
            occluding_rects.append((rect, depth, img))
    else:
        # Fallback path for unit tests calling this method directly
        vp = self._viewport_world
        for wx, wy, depth, img, _occ in self.game.map_manager._fg_occlusion_world:
            if depth <= player_depth:
                continue
            if wx + tile_size <= vp.left or wx >= vp.right:
                continue
            if wy + tile_size <= vp.top or wy >= vp.bottom:
                continue
            occluding_rects.append((
                pygame.Rect(wx + cam_x, wy + cam_y, tile_size, tile_size),
                depth,
                img,
            ))
```

### 5.4 `_blit_occluded_tiles_near_player` Sparse Checking

Only check the 9 tiles (3x3 grid) directly surrounding the player:
```python
def _blit_occluded_tiles_near_player(
    self,
    cam_offset: pygame.Vector2,
    player_screen_rect: pygame.Rect,
    player_depth: int,
) -> None:
    cam_x = int(cam_offset.x)
    cam_y = int(cam_offset.y)
    tile_size = self.game.tile_size
    screen = self.game.screen

    visible_tiles = getattr(self, "_frame_visible_fg_tiles", None)
    if visible_tiles is not None:
        # Optimized path: scan only the 3x3 area around player
        player_col = int(self.game.player.rect.centerx // tile_size)
        player_row = int(self.game.player.rect.centery // tile_size)

        for r in range(player_row - 1, player_row + 2):
            for c in range(player_col - 1, player_col + 2):
                tile_info = self.game.map_manager._fg_occlusion_grid.get((c, r))
                if tile_info:
                    depth, img, occ_img = tile_info
                    if depth > player_depth:
                        self._tile_rect.x = c * tile_size + cam_x
                        self._tile_rect.y = r * tile_size + cam_y
                        if player_screen_rect.colliderect(self._tile_rect):
                            screen.blit(occ_img if occ_img is not None else img, (self._tile_rect.x, self._tile_rect.y))
    else:
        # Fallback compatibility path for unit tests
        vp = self._viewport_world
        for wx, wy, depth, img, occ_img in self.game.map_manager._fg_occlusion_world:
            if depth <= player_depth:
                continue
            if wx + tile_size <= vp.left or wx >= vp.right:
                continue
            if wy + tile_size <= vp.top or wy >= vp.bottom:
                continue
            self._tile_rect.x = wx + cam_x
            self._tile_rect.y = wy + cam_y
            if player_screen_rect.colliderect(self._tile_rect):
                screen.blit(occ_img if occ_img is not None else img, (self._tile_rect.x, self._tile_rect.y))
```

---

## 6. Anti-Patterns

| ❌ Don't | ✅ Do Instead | Why |
|---|---|---|
| Construct new `pygame.Rect` objects inside rendering loops | Reuse from `self._rect_pool` in-place | Avoids heavy CPU allocation & GC overhead. |
| Query the full `_fg_occlusion_world` list every frame | Scan only viewport indices in `_fg_occlusion_grid` | Moves search from `O(N_world)` to `O(Viewport)`. |
| Loop over all visible tiles to blit occlusions near the player | Loop over a fixed 3x3 grid around player | Limits collision checks to exactly 9 tiles (`O(1)`). |
| Perform linear layer scans for grass wading material checks | Look up pre-computed material grid `_grass_grid` | Replaces `O(Layers)` search with `O(1)` list lookup. |
| Re-size or clear the `self._rect_pool` list dynamically every frame | Keep the pool size stable, expanding only if needed | Prevents list allocation overhead. |

---

## 7. Error Handling Matrix

| Error | Response | Fallback | Classification |
|---|---|---|---|
| Viewport column/row indices out of bounds | Clamp to grid boundaries | Return early / `continue` | SHOW: verified via layout clamping bounds checks |
| Player center coordinate floats | Use `int(centerx // tile_size)` | Standard integer division | SHOW: verified via standard division |
| Grid coordinate lookup returns `None` | Skip coordinate | `dict.get((x, y))` returns `None` safely | SHOW: verified via dictionary fallback test |
| Grass grid initialization on empty map | Yield empty grid | 2D list of `None` | SHOW: verified via initialization test |

---

## 8. Test Case Specifications

### 8.1 Unit Tests

| Test ID | Test Function | Description | Assertion |
|---|---|---|---|
| UT-001 | `test_fg_occlusion_grid_matches_world_list` | Grid contains exactly the same tiles as the flat list | `len(mm._fg_occlusion_grid) == len(mm._fg_occlusion_world)` |
| UT-002 | `test_grass_grid_contains_correct_material_surfaces` | Grass grid contains only surfaces of tiles configured as grass | `all(isinstance(s, pygame.Surface) for row in mm._grass_grid for s in row if s is not None)` |
| UT-003 | `test_rect_pool_reused_in_build_screen_occluding_rects` | Rect pool is reused and no new Rects are allocated when within pool bounds | `id(rm.draw_foreground()[0][0]) == id(rm._rect_pool[0])` |
| UT-004 | `test_grass_grid_lookup_O1_performance` | Grass tile lookup using `get_grass_tile_image_at` is fast | Execution time for 1000 calls < 5ms |
| UT-005 | `test_rect_pool_grows_when_limit_exceeded` | Pool appends new Rects if more visible tiles are requested | Pool size increases beyond 2000 |

### 8.2 Integration Tests

| Test ID | Test Function | Description | Assertion |
|---|---|---|---|
| IT-001 | `test_viewport_culling_limits_iterations` | RenderManager only loops over viewport bounds | Viewport culling matches visual expectations |
| IT-002 | `test_draw_static_foreground_tiles_returns_empty_list` | Method contract returns empty list | `result == []` |
| IT-003 | `test_draw_foreground_walk_active_skips_occluded_blit` | Occlusion blitting skipped during active walk | No player-adjacent blits |

---

## 9. Bundling & Native-Module Audit
- BM1: N/A — Pure Python/Pygame project, no bundler is used.
- BM2: N/A — No client/server splitting.
- BM3: N/A — No native Node modules introduced.
- BM4: N/A — No production constants or fields renamed.

---

## 10. Assumptions

| # | Assumption | Risk | Source Type | Validation |
|---|---|---|---|---|
| 1 | Single-threaded main loop | Low | SHOW: verified via codebase run loop | All in-place modifications to Rects in the pool are safe from concurrent access. |
| 2 | Grass material is immutable at runtime | Low | SHOW: verified via map load logic | The grid is computed at map load time and doesn't need to be updated. |
| 3 | The viewport fits within map boundaries | Low | SHOW: verified via layout clamping | Viewport grid column/row limits are clamped using `max(0, ...)` and `min(mm.width, ...)`. |
