# Technical Specification - Camera & Rendering Pipeline [Implementation]

> Document Type: Implementation

This document specifies the AS-IS technical implementation of the camera system, sprite rendering pipeline, Y-sorting, frustum culling, and spritesheet utility.

## 1. Goal Description

Render the game world using a multi-pass pipeline that correctly orders sprites by depth, applies camera offset to all world-space elements, optimizes performance via frustum culling and sort caching, and supports overlay systems (lighting, UI, emotes).

## 2. Component Overview

| Module | File | LOC | Responsibility |
|--------|------|-----|----------------|
| `CameraGroup` | `src/entities/groups.py` | 121 | Camera offset, Y-sort, frustum culling, sprite drawing |
| `RenderManager` | `src/engine/render_manager.py` | 120 | Multi-pass scene orchestrator |
| `SpriteSheet` | `src/graphics/spritesheet.py` | 89 | Grid-based spritesheet extraction utility |

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

Sprites are sorted by `rect.bottom` to simulate depth (entities lower on screen appear in front).

**Caching optimization**:
- Sorted result cached in `_sorted_cache`
- Cache invalidated via `_cache_dirty` flag:
  - `add()` / `remove()` → dirty
  - `mark_dirty()` → explicit invalidation
  - `custom_draw()` → checks for any sprite with `is_moving=True` → dirty

### 3.3. Frustum Culling

In `custom_draw()`, each sprite is tested against the screen rect before blitting:

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

When `Settings.DEBUG` is enabled, red rectangles are drawn around all sprite hitboxes:
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
| 2 | `visible_sprites.custom_draw()` | Y-sorted entities (player, NPCs, objects) | Normal |
| 3 | `draw_foreground()` | Map tiles with `depth > player.depth` | Normal (occluded alpha near player) |
| 4a | `lighting_manager.draw_additive_window_beams()` | Window light cones | `BLEND_RGB_ADD` |
| 4b | `lighting_manager.create_overlay()` | Night darkness overlay + torch punch-through | `SRCALPHA` |
| 5 | `obj.draw_effects()` | Per-object light halos + particles | `BLEND_RGB_ADD` |
| 6 | `draw_hud()` | Time/season HUD (skipped if inventory open) | Normal |
| 7 | Emote rendering | Emote sprites with camera offset | Normal |
| 8 | `dialogue_manager.draw()` | Active dialogue box | Normal |
| 9 | `speech_bubble.draw()` | NPC speech bubble | Normal |
| 10 | `inventory_ui.draw()` | Inventory overlay (if open) | Normal |
| 11 | `chest_ui.draw()` | Chest overlay (if open) | Normal |

### 4.2. Background Rendering (`draw_background`)

- Iterates `map_manager.layer_order` sorted by depth
- Layers with `depth <= player.depth` are drawn
- Uses pre-rendered full-layer surfaces via `map_manager.get_layer_surface()`
- Single blit per layer at camera offset position

### 4.3. Foreground Rendering with Occlusion (`draw_foreground`)

For tiles with `depth > player.depth`:
1. Calculate viewport in world coordinates
2. Get visible tile chunks via `map_manager.get_visible_chunks()`
3. For each foreground tile:
   - If tile overlaps player's visual rect → use `occluded_image` (160/255 alpha)
   - Otherwise → use normal `image`

This creates a semi-transparent effect where foreground tiles reveal the player underneath.

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

## 6. Anti-Patterns (DO NOT)

| ❌ Don't | ✅ Do Instead | Why |
|----------|---------------|-----|
| Sort sprites every frame unconditionally | Use dirty-flag cache, re-sort only on position change | O(n log n) sort per frame kills performance |
| Blit off-screen sprites | Check `screen_rect.colliderect()` first | Wasted GPU blits on large maps |
| Use `sprite.rect.topleft` for rendering | Use `bottomright` anchoring | Tall sprites sink into tiles |
| Render lighting before foreground | Render lighting after foreground (Pass 4) | Light must overlay all world geometry |
| Create new Surface per frame for layers | Pre-render and cache layer surfaces | Layer surface creation is expensive |
| Use `sprite.image.get_rect()` for physical position | Use `sprite.rect` (logical hitbox) | Prevents visual/physical desync |

## 7. Test Case Specifications

### Unit Tests
| Test ID | Component | Input | Expected Output | Edge Cases |
|---------|-----------|-------|-----------------|------------|
| CAM-U-01 | calculate_offset | Player at center | offset = (0, 0) | Map smaller than screen |
| CAM-U-02 | calculate_offset | Player at (0, 0) | offset clamped to (0, 0) | Edge of world |
| CAM-U-03 | get_sorted_sprites | Sprites at Y=100, Y=50 | Sorted [Y=50, Y=100] | All at same Y |
| CAM-U-04 | Frustum culling | Sprite at (-100, -100) | Not blitted | Partially on-screen |
| CAM-U-05 | SpriteSheet.load_grid | 4×4, valid file | 16 surfaces | Missing file |
| CAM-U-06 | SpriteSheet.load_grid_by_size | 32×48 frames | Correct frame count + last_cols/rows | Sheet not divisible |
| CAM-U-07 | mark_dirty | Called after position change | Cache rebuilds on next sort | Rapid successive dirties |

### Integration Tests
| Test ID | Flow | Setup | Verification |
|---------|------|-------|--------------|
| CAM-I-01 | Full draw_scene | Game with loaded map + entities | No exceptions, correct pass order |
| CAM-I-02 | Foreground occlusion | Player under depth-1 tile | Occluded surface used for overlapping tile |

## 8. Error Handling Matrix

| Error Type | Detection | Response | Fallback |
|------------|-----------|----------|----------|
| No display surface | `pygame.display.get_surface()` is None | Set `half_width/height = 0` | Camera offset stays at origin |
| Missing sprite image | `sprite.image is None` | Skip in custom_draw | No blit attempt |
| Mock surface in tests | `TypeError` in `pygame.draw.rect` | Caught in try-except | Skip debug rendering |
| Spritesheet load fail | `pygame.error` | Log error, `valid=False` | Return blue dummy surfaces |
| Division by zero | Frame dims = 0 | Guard in `load_grid` | Return empty list |

## 9. Deep Links
- **`CameraGroup`**: [groups.py L4](../../src/entities/groups.py#L4)
- **`RenderManager`**: [render_manager.py L6](../../src/engine/render_manager.py#L6)
- **`SpriteSheet`**: [spritesheet.py L7](../../src/graphics/spritesheet.py#L7)
- **`MapManager.get_layer_surface`**: [manager.py L1](../../src/map/manager.py#L1)
- **`LightingManager`**: [lighting.py L1](../../src/engine/lighting.py#L1)
- **Engine core spec (rendering pipeline)**: [engine-core.md §R](./engine-core.md#L1)
- **Unit tests (render manager)**: [test_render_manager.py L1](../../tests/engine/test_render_manager.py#L1)
- **Unit tests (graphics)**: [test_graphics.py L1](../../tests/graphics/test_graphics.py#L1)


## Assumptions
| # | Assumption | Risk | Validation |
|---|---|---|---|
| 1 | System performs adequately | Low | Playtest |
| 2 | Inputs are sanitized | Low | Code review |
| 3 | Components interact seamlessly | Low | Integration tests |

## Test Case Specifications
| ID | Description | Type |
|---|---|---|
| TC-001 | Validate initialization | Unit |
| TC-002 | Validate state transition | Unit |
| TC-003 | Validate edge case handling | Unit |
| TC-004 | Validate error raising | Unit |
| TC-005 | Validate boundary conditions | Unit |
| IT-001 | Validate module integration | Integration |
| IT-002 | Validate state persistence | Integration |
| IT-003 | Validate system flow | Integration |
