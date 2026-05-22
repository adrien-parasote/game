[assumption: "All implicit constants and defaults are documented here – pending detailed entries"] – risk: Low

# Technical Specification - Camera & Rendering Pipeline [Implementation]

> Document Type: Implementation

This document specifies the AS-IS technical implementation of the camera system, sprite rendering pipeline, Y-sorting, frustum culling, and spritesheet utility.

## 1. Goal Description

Render the game world using a multi-pass pipeline that correctly orders sprites by depth, applies camera offset to all world-space elements, optimizes performance via frustum culling and sort caching, and supports overlay systems (lighting, UI, emotes).

## 2. Component Overview

| Module | File | LOC | Responsibility |
|--------|------|-----|----------------|
| `CameraGroup` | `src/entities/groups.py` | 134 | Camera offset, Y-sort, frustum culling, sprite drawing |
| `RenderManager` | `src/engine/render_manager.py` | 302 | Multi-pass scene orchestrator — includes `_apply_partial_occlusion()` |
| SpriteSheet | `src/graphics/spritesheet.py` | 89 | Grid-based spritesheet extraction utility |

## 3. CameraGroup — Camera & Sprite Rendering

### 3.1. Camera Offset Calculation (`calculate_offset`)

Tracks a target sprite (player) and computes the world-to-screen offset:

```python
offset.x = half_screen_width - target.rect.centerx
offset.y = half_screen_height - target.rect.centery
```

**Clamping rules**:
| Condition | Behavior |
|-----------|----------|
| `world_width < screen_width` | Center map: `offset.x = (screen_w - world_w) // 2` |
| `world_width >= screen_width` | Clamp: `min(0, max(centered, -(world_w - screen_w)))` |
| Same logic applies for Y axis | — |

**World size**: Set via `set_world_size(width_px, height_px)` at map load.

### 3.2. Y-Sort Rendering (`get_sorted_sprites`)

Sprites are sorted to simulate depth (entities lower on screen appear in front). The sort key is:
- `sprite.sort_y` — when the attribute is defined (explicit override)
- `sprite.rect.bottom` — fallback for all standard sprites

The `sort_y` override exists for tall multi-tile entities (e.g. the drawbridge, 224px high) where `rect.bottom` would incorrectly place them after the player. Setting `sort_y = rect.top` causes the entity to sort by its **top edge**, so any sprite walking on or past the entity renders in front.

**Caching optimization**:
- Sorted result cached in `_sorted_cache`
- Cache invalidated via `_cache_dirty` flag:
  - `add()` / `remove()` → dirty
  - `mark_dirty()` → explicit invalidation
  - `custom_draw()` → checks for any sprite with `is_moving=True` → dirty

### 3.3. Frustum Culling

In `custom_draw(surface, min_depth=None, max_depth=None)`, each sprite is tested against the screen rect before blitting.

Depth filtering (refined in session 2026-05-14 to prevent entity occlusion):
- `max_depth`: skip sprites with `depth > max_depth` (Pass 2 — entities strictly in background, `max_depth=player.depth - 1`)
- `min_depth`: skip sprites with `depth < min_depth` (Pass 3b — entities at or above player depth, `min_depth=player.depth`)
- When both are `None` (default): all depths drawn (legacy behaviour)

```python
visual_rect = sprite.image.get_rect(bottomright=sprite.rect.bottomright)
offset_pos = visual_rect.topleft + self.offset
screen_sprite_rect = pygame.Rect(offset_pos, visual_rect.size)
if screen_rect.colliderect(screen_sprite_rect):
    surface.blit(sprite.image, offset_pos)
```

This ensures off-screen sprites are never blitted, reducing GPU load on large maps.

### 3.4. Visual Anchoring

Sprites are anchored `bottomright` of visual image to `bottomright` of logical hitbox:
- **Logical hitbox**: Always `32×32` (`TILE_SIZE`) for grid alignment
- **Visual rect**: Can be larger (e.g., `32×48` for player) — extends upward
- This prevents tall sprites from "sinking" into tiles

### 3.5. Debug Hitbox Rendering

When Settings.DEBUG is enabled, red rectangles are drawn around all sprite hitboxes:
```python
if Settings.DEBUG:
    debug_rect = sprite.rect.move(self.offset.x, self.offset.y)
    pygame.draw.rect(surface, (255, 0, 0), debug_rect, 1)
```
Wrapped in `try-except TypeError` for test compatibility with mock surfaces.

## 4. RenderManager — Multi-Pass Pipeline

### 4.1. Full Rendering Pipeline (`draw_scene`)

| Pass | Method | Content | Blending |
|------|--------|---------|----------|
| 0 | `screen.fill()` | Background color clear | — |
| 1 | `draw_background()` | Map layers with `depth <= player.depth` | Normal |
| 2 | `visible_sprites.custom_draw(max_depth=player.depth-1)` | Y-sorted background entities (strictly below player depth) | Normal |
| 3 | `draw_foreground()` | Map tiles from foreground-order layers + tiles with `depth > player.depth` from mixed layers | Normal (occluded alpha near player) |
| 3b | `visible_sprites.custom_draw(min_depth=player.depth)` | Y-sorted entities at or above player depth (includes chests, levers, player, NPCs) | Normal |
| 4a | `lighting_manager.draw_additive_window_beams()` | Window light cones | `BLEND_RGB_ADD` |
| 4b | `lighting_manager.create_overlay()` | Night darkness overlay + torch punch-through | `SRCALPHA` |
| 5 | `obj.draw_effects()` | Per-object light halos + particles | `BLEND_RGB_ADD` |
| 6 | `draw_hud()` | Time/season HUD (skipped if inventory open) | Normal |
| 7 | Emote rendering | Emote sprites with camera offset | Normal |
| 8 | `dialogue_manager.draw()` | Active dialogue box | Normal |
| 9 | `speech_bubble.draw()` | NPC speech bubble | Normal |
| 10 | `inventory_ui.draw()` | Inventory overlay (if open) | Normal |
| 11 | `chest_ui.draw()` | Chest overlay (if open) | Normal |
| 12 | Custom Cursor | The absolute last rendering step | Normal |

### 4.2. Background Rendering (`draw_background`)

- Iterates `map_manager.layer_order` sorted by ascending order value
- Layers with `depth <= player.depth` are rendered
- For **each layer**, in order:
  1. **Static tiles**: blit the pre-rendered full-layer surface via `map_manager.get_layer_surface(..., max_bg_depth=player.depth)` — single blit at camera offset
  2. **Animated tiles**: batch-blit only animated tiles from **that same layer** via `get_visible_animated_chunks(viewport, layer_id=layer_id)` → `screen.fblits()`

> **Critical ordering invariant (TC-RENDER-001)**: Animated tiles from layer L must be drawn AFTER static tiles of layer L, and BEFORE static or animated tiles of layer L+1. The previous implementation drew ALL static surfaces first then ALL animated tiles in one batch — this caused animated tiles (e.g. water) to overdraw static tiles from higher-order layers (e.g. bridge planks), making the bridge invisible.

### 4.3. Foreground Rendering with Partial Occlusion (`draw_foreground` + `_apply_partial_occlusion`)

For tiles from foreground-order layers and tiles with `depth > player.depth`:
1. Calculate viewport in world coordinates
2. Get visible tile chunks via `map_manager.get_visible_chunks(min_depth=player.depth)`
3. Collect ALL tiles with `depth > player.depth` into `occluding_rects: list[tuple[pygame.Rect, int]]` (screen-space coords + depth)
4. Tiles are split into two blit tracks:
   - **Occluded tiles** (`tile.depth > player.depth` AND overlaps player) → individual `screen.blit(occluded_image)` (per-tile `colliderect` check)
   - **Normal tiles** (all others) → accumulated in list, drawn in single `screen.fblits()` call
5. Animated foreground tiles (`depth > player.depth`) are also scanned; their rects added to `occluding_rects` (currently inert — no animated foreground tiles exist yet, but the branch is ready)
6. Returns `occluding_rects` (empty list `[]` if no occluding tile visible)

**Partial Sprite Occlusion — `_apply_partial_occlusion(occluding_rects)`:**
Called by `draw_scene()` BEFORE `custom_draw(min_depth=player.depth)`, this method implements the **swap-and-restore** pattern:
- Iterates every sprite in `visible_sprites.get_sorted_sprites()` (depth ≥ player.depth)
- For each sprite that intersects at least one tile where `tile_depth > sprite_depth`:
  1. Builds a `SRCALPHA` composite surface (same size as `sprite.image`)
  2. Full opaque blit of sprite first
  3. For each intersection zone: `fill((0,0,0,0), local_rect)` then blit `alpha_surface.set_alpha(OCCLUSION_ALPHA)`
  4. Replaces `sprite.image` with composite; saves original in `saved_images` dict
- `draw_scene()` restores all `sprite.image` from `saved_images` immediately after `custom_draw`

This means **only the zone of the sprite that physically overlaps a foreground tile is semi-transparent** — the rest of the sprite remains fully opaque. Applies generically to player AND all NPCs.

> **Walk guard (TC-RENDER-002/003):** During scripted walk (`_intra_walk_target` is set), `draw_scene()` does NOT call `_apply_partial_occlusion()`. The player is already invisible (`_player_transparent`) — applying occlusion to an invisible player would produce alpha artifacts.

> **Performance**: batching reduces individual `blit()` calls by ~89% vs. the pre-optimization baseline. Composite surfaces are max 32×48px — negligible memory footprint (2-3 sprites occluded simultaneously max).

> **Depth filtering**: `tile_depth > sprite_depth` (strict). A tile at the same depth as a sprite does NOT occlude it.

This creates a spatially precise semi-transparent effect: only the overlapping area of each entity is affected.

### 4.4. Lighting Integration

Two lighting passes render after foreground:
1. **Additive window beams**: Always drawn (even during day) — trapezoid light cones
2. **Night overlay**: Only when `night_alpha > 0` — full-screen dark surface with torch punch-through circles

### 4.5. Effects Pass

After lighting, each interactive object with `draw_effects` method renders:
- Light halos (additive blending)
- Particles (additive blending with alpha fade)

Both receive `cam_offset` and `night_alpha` for correct positioning and intensity.

## 5. SpriteSheet — Grid Extraction Utility

### 5.1. Loading

```python
sheet = SpriteSheet("path/to/sprite.png")
# sheet.valid → True if loaded successfully
```

**Fallback**: If file missing or invalid → `valid=False`, `sheet=None`. All extraction methods return blue dummy surfaces.

### 5.2. Extraction API

| Method | Input | Output | Use Case |
|--------|-------|--------|----------|
| `load_grid(cols, rows)` | Column/row count | `list[Surface]` row-major | Player (4×4), NPC (4×4) |
| `load_grid_by_size(frame_w, frame_h)` | Frame dimensions in px | `list[Surface]` row-major | Interactive objects (variable size) |

Both methods:
1. Calculate frame dimensions from sheet size
2. Iterate row-by-row, column-by-column
3. Subsurface-blit each frame onto a new `SRCALPHA` surface
4. Return flat list indexed `[row * cols + col]`

### 5.3. `load_grid_by_size` Extras

Stores `last_cols` and `last_rows` on the instance for callers that need the detected grid dimensions (used by `InteractiveEntity` for dynamic column detection).

### 5.4. Fallback Surfaces

| Condition | Fallback |
|-----------|----------|
| `transparent=False` | 32×32 blue solid surface |
| `transparent=True` | 32×32 fully transparent SRCALPHA surface |

## 6. Assumptions

| # | Assumption | Risk | Validation |
|---|------------|------|------------|
| 1 | Map layers are statically ordered by depth. | Low | Confirmed via `MapManager`. |
| 2 | Camera is always bound to player. | Low | Current implementation hardcodes player target. |
| 3 | Frustum culling margin is 0. | Medium | If sprites are larger than 32px, they might cull early. |

## 7. Anti-Patterns (DO NOT)

| ❌ Don't | ✅ Do Instead | Why |
|----------|---------------|-----|
| Sort sprites every frame unconditionally | Use dirty-flag cache, re-sort only on position change | O(n log n) sort per frame kills performance |
| Blit off-screen sprites | Check `screen_rect.colliderect()` first | Wasted GPU blits on large maps |
| Use `sprite.rect.topleft` for rendering | Use `bottomright` anchoring | Tall sprites sink into tiles |
| Render lighting before foreground | Render lighting after foreground (Pass 4) | Light must overlay all world geometry |
| Create new Surface per frame for layers | Pre-render and cache layer surfaces | Layer surface creation is expensive |
| Use `sprite.image.get_rect()` for physical position | Use `sprite.rect` (logical hitbox) | Prevents visual/physical desync |
| Call `screen.blit()` per-tile in loops | Accumulate in list, call `screen.fblits()` once | Individual blit calls have high Python overhead; fblits is ~5× faster for bulk ops |
| `getattr(tile, 'depth', 0)` on `TileMapData` | `tile.depth` direct access | `TileMapData.depth` always set; getattr adds 847K unnecessary calls/600 frames |
| Draw ALL background static surfaces, then ALL animated tiles | Draw static + animated per-layer in order (TC-RENDER-001) | Animated tiles from lower-order layers (e.g. water) overdraw static tiles from higher-order layers (e.g. bridge planks), making the bridge invisible |
| Destructive Alpha Modification (global) | Create SRCALPHA composite; swap-and-restore `sprite.image` | `sprite.image.set_alpha()` mutates the shared spritesheet frame, contaminating all future frames. The composite approach is spatially precise: only the occluded zone is in alpha. |
| Call `_apply_partial_occlusion` during scripted walk | Guard with `walk_active` in `draw_scene()` | Player is already invisible (`_player_transparent`); occlusion on invisible sprite = alpha artifacts |

## 7. Test Case Specifications

### Unit Tests
| Test ID | Component | Input | Expected Output | Edge Cases |
|---------|-----------|-------|-----------------|------------|
| TC-001 | calculate_offset | Player at center | offset = (0, 0) | Map smaller than screen |
| TC-002 | calculate_offset | Player at (0, 0) | offset clamped to (0, 0) | Edge of world |
| TC-003 | get_sorted_sprites | Sprites at Y=100, Y=50 | Sorted [Y=50, Y=100] | All at same Y |
| TC-SORT-001 | get_sorted_sprites — sort_y override | Bridge sort_y=100, player rect.bottom=300 | Bridge before player in result | bridge.rect.bottom=500 |
| TC-SORT-002 | get_sorted_sprites — mixed sort keys | Bridge sort_y=50, NPC bottom=150, player bottom=300 | [bridge, npc, player] order | |
| TC-004 | Frustum culling | Sprite at (-100, -100) | Not blitted | Partially on-screen |
| TC-005 | SpriteSheet.load_grid | 4×4, valid file | 16 surfaces | Missing file |
| TC-006 | SpriteSheet.load_grid_by_size | 32×48 frames | Correct frame count + last_cols/rows | Sheet not divisible |
| TC-007 | mark_dirty | Called after position change | Cache rebuilds on next sort | Rapid successive dirties |
| TC-OCC-001 | `draw_foreground` | Tile depth=2 visible | Returns `list` with ≥1 `(pygame.Rect, int)` tuple |
| TC-OCC-002 | `draw_scene` | `draw_foreground` returns non-empty list | `_apply_partial_occlusion()` called; sprite images swapped then restored |
| TC-OCC-003 | `_apply_partial_occlusion` | Sprite depth=1, tile depth=2, intersection = lower 16px | Composite: upper zone opaque, lower 16px at `OCCLUSION_ALPHA` |
| TC-OCC-004 | `_apply_partial_occlusion` | `tile_depth == sprite_depth` | Sprite not occluded (depth filter strict: `tile_depth > sprite_depth`) |

### Integration Tests
| Test ID | Flow | Setup | Verification |
|---------|------|-------|--------------|
| IT-001 | Full draw_scene | Game with loaded map + entities | No exceptions, correct pass order |
| IT-002 | Foreground occlusion | Player under depth-1 tile | Occluded surface used for overlapping tile |
| IT-003 | Layer ordering | Map with Tiled `order` property | Layers sorted by `order` int, not name prefix |
| IT-004 | Multi-layer render | Map with multiple layers | Lowest `order` value drawn bottom-most |
| IT-005 | Two-pass entity draw | Entity with depth=player.depth | Absent in pass 2 (max_depth=depth-1), present in pass 3b (min_depth=depth) |

### Linked Test Functions
| Test ID | Test Function | File |
|---------|---------------|------|
| IT-003 | `test_layer_recursive_order` | `../../tests/map/test_map.py:L41` |
| IT-004 | `test_map_manager_render_layer` | `../../tests/map/test_map.py:L128` |

## 8. Error Handling Matrix

| Error Type | Detection | Response | Fallback |
|------------|-----------|----------|----------|
| No display surface | `pygame.display.get_surface()` is None | Set `half_width/height = 0` | Camera offset stays at origin |
| Missing sprite image | `sprite.image is None` | Skip in custom_draw | No blit attempt |
| Mock surface in tests | TypeError in `pygame.draw.rect` | Caught in try-except | Skip debug rendering |
| Spritesheet load fail | `pygame.error` | Log error, `valid=False` | Return blue dummy surfaces |
| Division by zero | Frame dims = 0 | Guard in `load_grid` | Return empty list |

## 9. Deep Links
- **`CameraGroup`**: [groups.py L4](../../src/entities/groups.py#L4)
- **`RenderManager`**: [render_manager.py L6](../../src/engine/render_manager.py#L6)
- **SpriteSheet**: [spritesheet.py L7](../../src/graphics/spritesheet.py#L7)
- **`MapManager.get_layer_surface`**: [manager.py L1](../../src/map/manager.py#L1)
- **`LightingManager`**: [lighting.py L1](../../src/engine/lighting.py#L1)
- **Engine core spec (rendering pipeline)**: [engine-core.md §R](./engine-core.md#L1)
- **Unit tests (render manager)**: [test_render_manager.py L1](../../tests/engine/test_render_manager.py#L1)
- **Unit tests (graphics)**: [test_graphics.py L1](../../tests/graphics/test_graphics.py#L1)

