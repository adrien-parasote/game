# Technical Specification — Grass Wading Effect [Implementation]

> **Document Type:** Implementation
> **Feature:** Grass Wading — visual immersion when player/NPCs walk on grass tiles
> **Covers:** grass-wading rendering pass, config extension, MapManager query extension
> **Related specs:** [camera-rendering.md §4](./camera-rendering.md#L94), [map-world-system.md §4.2](./map-world-system.md#L83)

---

## 1. Goal Description

When the player or any NPC stands on a tile with `properties.material == "grass"`, the bottom portion of their sprite appears to be physically **inside** the grass rather than floating on top. The effect uses two combined passes applied after the sprite draw:

1. **Grass re-blit**: the grass tile image is painted over the bottom `GRASS_WADING_DEPTH` pixels of the sprite — the feet literally disappear into the grass texture.
2. **Alpha blend**: a semi-transparent overlay is applied over the same zone at `GRASS_WADING_ALPHA` — the sprite-to-grass transition is softened.

Effect applies to **all visible sprites** (player + NPCs). It is triggered purely by tile data — no entity-side logic required.

---

## 2. Component Overview

| Module | File | LOC delta | Responsibility |
|--------|------|-----------|----------------|
| `RenderManager` | `src/engine/render_manager.py` | +~55 | New `_apply_grass_wading()` method + call in `draw_scene()` |
| `MapManager` | `src/map/manager.py` | +~20 | New `get_grass_tile_image_at()` query method |
| `Settings` | `src/config.py` | +4 | Two new overlay constants |
| `settings.json` | `settings.json` | +2 | Persist the two new constants |

---

## 3. Constraints

| Tier | Examples |
|------|----------|
| **Always do** | Guard the wading pass with `walk_active` (same as `_apply_partial_occlusion`). Clip wading rect to screen bounds before any blit. Use `visual_rect` formula identical to `custom_draw` and `_apply_partial_occlusion`. |
| **Ask first** | Changing `TILE_SIZE`, the `depth` property of grass tiles, or the definition of `material` in TSX files. |
| **Never do** | Mutate `sprite.image` permanently (swap-and-restore is required if sprite.image is touched). Allocate a `pygame.Surface` per frame per sprite for the alpha overlay — use fill instead. Probe terrain at `sprite.rect.centerx, sprite.rect.top` — always probe at foot position (`rect.bottom - 2`). Apply the effect to sprites with `depth < player.depth` (Pass 2 entities — they are already below the grass layer). |

---

## 4. Cross-Spec Contracts

### Produces

| Identifier | Format | Consumers |
|---|---|---|
| N/A — this pass produces only rendered pixels, no runtime artifacts | — | — |

### Consumes

| Identifier | Format | Defined in |
|---|---|---|
| `MapManager.get_grass_tile_image_at(px, py)` | `pygame.Surface \| None` | This spec §5.2 (new method) |
| `CameraGroup.get_sorted_sprites()` | `list[Sprite]` | [camera-rendering.md §3.2](./camera-rendering.md#L42) |
| `Settings.GRASS_WADING_DEPTH` | `int` pixels | This spec §6 |
| `Settings.GRASS_WADING_ALPHA` | `int` 0–255 | This spec §6 |
| `Settings.TILE_SIZE` | `int` (32) | [00_MASTER.md §3](./00_MASTER.md#L63) |
| `game._intra_walk_target` | `Any \| None` | [intra-map-teleport.md §4](../specs/intra-map-teleport.md#L1) |

### Public Interface

| Type | Identifier | Documented at |
|---|---|---|
| Method | `MapManager.get_grass_tile_image_at(pixel_x, pixel_y) -> Surface \| None` | This spec §5.2 |
| Method | `RenderManager._apply_grass_wading(surface)` | This spec §5.1 |
| Constant | `Settings.GRASS_WADING_DEPTH` | This spec §6 |
| Constant | `Settings.GRASS_WADING_ALPHA` | This spec §6 |

### External Invocations

| Type | Invoked | Defined in |
|---|---|---|
| Method | `MapManager.get_terrain_material_at()` (parallel, not replaced) | [map-world-system.md §4.2](./map-world-system.md#L83) |
| Guard | `getattr(game, "_intra_walk_target", None)` | [camera-rendering.md §4.3.3](./camera-rendering.md#L259) |

### Tracked Concepts

| Concept | Status in this spec | Mentioned in |
|---|---|---|
| `visual_rect = sprite.image.get_rect(bottomright=sprite.rect.bottomright)` | Reused invariant — must match `custom_draw` and `_apply_partial_occlusion` | [camera-rendering.md §4.3.2](./camera-rendering.md#L185) |
| `walk_active` guard | Applied identically to all render-time sprite modifications | [camera-rendering.md §4.3.3](./camera-rendering.md#L259) |

---

## 5. Implementation Specification

### 5.1. `RenderManager._apply_grass_wading(surface: pygame.Surface)`

**Location**: `src/engine/render_manager.py`  
**Deep link**: [render_manager.py L224](../../src/engine/render_manager.py#L224) (after `draw_scene`)  
**Called from**: `draw_scene()`, after `custom_draw(min_depth=player.depth)`, before lighting passes

**Preconditions** (all must be true to proceed):
- `self.game.map_manager` is not None
- `walk_active` is False (identical check to `_apply_partial_occlusion`)

**Algorithm (per sprite):**

```python
def _apply_grass_wading(self, surface: pygame.Surface) -> None:
    if not self.game.map_manager:
        return

    cam_offset = self.game.visible_sprites.offset
    tile_size = self.game.tile_size
    wading_depth = Settings.GRASS_WADING_DEPTH
    wading_alpha = Settings.GRASS_WADING_ALPHA

    for sprite in self.game.visible_sprites.get_sorted_sprites():
        if not sprite.image or not sprite.rect:
            continue

        # Build visual screen rect — identical to custom_draw and _apply_partial_occlusion
        visual_rect = sprite.image.get_rect(bottomright=sprite.rect.bottomright)
        sprite_screen_rect = pygame.Rect(
            (visual_rect.left + cam_offset.x, visual_rect.top + cam_offset.y),
            visual_rect.size,
        )

        # Probe grass at foot position (bottom center of hitbox, 2px up to avoid edge miss)
        foot_world_x = sprite.rect.centerx
        foot_world_y = sprite.rect.bottom - 2

        grass_img = self.game.map_manager.get_grass_tile_image_at(foot_world_x, foot_world_y)
        if grass_img is None:
            continue  # Not on grass — skip

        # Compute wading zone: bottom GRASS_WADING_DEPTH pixels of the screen sprite rect
        wading_rect = pygame.Rect(
            sprite_screen_rect.left,
            sprite_screen_rect.bottom - wading_depth,
            sprite_screen_rect.width,
            wading_depth,
        )
        # Clip to screen bounds — prevents out-of-bounds blits at map edges
        screen_rect = surface.get_rect()
        wading_rect = wading_rect.clip(screen_rect)
        if wading_rect.width <= 0 or wading_rect.height <= 0:
            continue

        # --- Pass 1: Re-blit grass tile image aligned to tile grid ---
        # Compute which tile is under the foot
        tile_world_x = (foot_world_x // tile_size) * tile_size
        tile_world_y = (foot_world_y // tile_size) * tile_size
        # Tile top-left in screen space
        tile_screen_x = tile_world_x + cam_offset.x
        tile_screen_y = tile_world_y + cam_offset.y

        # Area of the grass tile image that aligns with wading_rect
        grass_crop = pygame.Rect(
            wading_rect.x - tile_screen_x,
            wading_rect.y - tile_screen_y,
            wading_rect.width,
            wading_rect.height,
        )
        surface.blit(grass_img, wading_rect.topleft, area=grass_crop)

        # --- Pass 2: Semi-transparent fill to blend sprite into grass ---
        alpha_surf = pygame.Surface(wading_rect.size, pygame.SRCALPHA)
        alpha_surf.fill((0, 0, 0, 255 - wading_alpha))  # alpha = inverse of visibility
        surface.blit(alpha_surf, wading_rect.topleft)
```

**Call site in `draw_scene()`:**

```python
# After: self.game.visible_sprites.custom_draw(self.game.screen, min_depth=player.depth)
# Before: self.game.lighting_manager.draw_additive_window_beams(...)
walk_active = getattr(self.game, "_intra_walk_target", None) is not None
if not walk_active:
    self._apply_grass_wading(self.game.screen)
```

**Render pass table (updated):**

| Pass | Method | Content |
|------|--------|---------|
| 0 | `screen.fill()` | Background clear |
| 1 | `draw_background()` | Tiles depth ≤ player.depth (incl. grass depth=0) |
| 2 | `custom_draw(max_depth=player.depth-1)` | Background entities |
| 3 | `draw_foreground()` | Foreground tiles + occlusion rects |
| 3b | `_apply_partial_occlusion()` | Sprite composites for foreground tile occlusion |
| 3c | `custom_draw(min_depth=player.depth)` | Player + NPCs fully drawn |
| **3d** | **`_apply_grass_wading()`** | **[NEW] Grass re-blit + alpha over sprite foot zone** |
| 4a | `draw_additive_window_beams()` | Window light cones |
| 4b | `create_overlay()` | Night darkness + torch halos |
| 5+ | Effects, HUD, emotes, dialogue | Unchanged |

---

### 5.2. `MapManager.get_grass_tile_image_at(pixel_x, pixel_y)`

**Location**: `src/map/manager.py`  
**Deep link**: [manager.py L277](../../src/map/manager.py#L277) (after `get_terrain_material_at`)

**Signature:**
```python
def get_grass_tile_image_at(self, pixel_x: int, pixel_y: int) -> pygame.Surface | None:
```

**Algorithm:**
```python
def get_grass_tile_image_at(self, pixel_x: int, pixel_y: int) -> "pygame.Surface | None":
    """Return the image surface of the grass tile at pixel_x, pixel_y, or None.

    Identical scan logic to get_terrain_material_at():
    - Skips tiles with depth > 1 (roofs, ceilings)
    - Returns tile.image when material == "grass"
    - Returns None if position is out of bounds or no grass tile is found
    """
    grid_pos = self.layout.to_world(pixel_x, pixel_y)
    tx, ty = int(grid_pos[0]), int(grid_pos[1])

    if not (0 <= ty < self.height and 0 <= tx < self.width):
        return None

    for layer_id in reversed(self.layer_order):
        layer_data = self.layers.get(layer_id)
        if not layer_data:
            continue
        tile_id = layer_data[ty][tx]
        if tile_id == 0 or tile_id not in self.tiles:
            continue
        tile = self.tiles[tile_id]
        if getattr(tile, "depth", 0) > 1:
            continue
        props = getattr(tile, "properties", {}) or {}
        if props.get("material") == "grass":
            return tile.image

    return None
```

**Invariants:**
- Does NOT modify any mutable state — read-only
- Returns the exact `TileMapData.image` Surface (no copy, no allocation)
- Identical layer scan order to `get_terrain_material_at` — results are consistent

---

### 5.3. Grass Tile Alignment Detail

The grass re-blit must be **pixel-aligned to the tile grid**, not to the sprite position. This prevents the grass texture from "sliding" when the sprite moves within a tile.

```
World foot position:  (foot_world_x=688, foot_world_y=1630)
Tile size:            32px
Tile origin (world):  (tile_world_x=672, tile_world_y=1616)   # floor to tile grid
Tile origin (screen): (tile_screen_x=672+cam_x, tile_screen_y=1616+cam_y)
Wading rect (screen): bottom 10px of sprite screen rect
grass_crop:           area within tile image that overlaps wading_rect
```

The `grass_crop` rect is computed relative to the tile origin in screen space, so as the sprite moves across a tile boundary, the crop shifts smoothly through the tile image.

---

## 6. Settings Extension

### `src/config.py`

In `_DEFAULTS["overlay"]`:
```python
"grass_wading_depth": 10,   # pixels from bottom of sprite where grass is rendered over
"grass_wading_alpha": 140,  # 0–255: controls sprite visibility under grass (higher = more opaque grass)
```

In `_apply_systems()`:
```python
cls.GRASS_WADING_DEPTH: int = data.get("overlay", {}).get("grass_wading_depth", 10)
cls.GRASS_WADING_ALPHA: int = data.get("overlay", {}).get("grass_wading_alpha", 140)
```

### `settings.json`

```json
"overlay": {
  "occlusion_alpha": 102,
  "grass_wading_depth": 10,
  "grass_wading_alpha": 140
}
```

**Value semantics:**
| Setting | Range | Effect |
|---------|-------|--------|
| `GRASS_WADING_DEPTH` | 4–16 px | Height of the wading zone; 10 = ~1/3 of 32px sprite |
| `GRASS_WADING_ALPHA` | 0–255 | Fill alpha on wading zone: 255 = fully opaque grass (no sprite), 0 = no effect |

---

## 7. Bundling & Native-Module Audit

- **BM1**: N/A — this is a Python/Pygame project, no bundled framework.
- **BM2**: N/A — no client/server split.
- **BM3**: N/A — no native modules introduced.
- **BM4**: N/A — no field or constant renaming. New constants `GRASS_WADING_DEPTH` / `GRASS_WADING_ALPHA` have no prior test fixtures.

---

## 8. Anti-Patterns (DO NOT)

| ❌ Don't | ✅ Do Instead | Why |
|----------|---------------|-----|
| Probe terrain at `sprite.rect.centerx, sprite.rect.centery` | Probe at `sprite.rect.centerx, sprite.rect.bottom - 2` | Center of sprite is chest-height; grass detection must be at feet |
| Mutate `sprite.image` in `_apply_grass_wading` | Blit directly to `surface` — do NOT touch `sprite.image` | `sprite.image` is a shared spritesheet frame; mutating it contaminates all future frames |
| Allocate `pygame.Surface` per frame per sprite for re-blit | Use `surface.blit(grass_img, ..., area=grass_crop)` — no allocation | Per-frame Surface allocation kills performance at 60fps with multiple NPCs |
| Blit the whole grass tile image | Crop with `area=grass_crop` to extract only the relevant tile pixels | Blit without crop draws beyond wading zone |
| Use `sprite.rect.topleft` as screen position | Compute `visual_rect` with `bottomright=sprite.rect.bottomright` as in `custom_draw` | Must match the formula used in Pass 3c exactly |
| Apply wading to sprites with `depth < player.depth` | Skip sprites from Pass 2 (they are already below grass) | Background entities are behind the grass layer — no wading effect needed |
| Call `_apply_grass_wading` during scripted walk | Guard with `walk_active` check | Player is invisible during scripted walk; painting grass over invisible sprite creates artifacts |
| Skip screen-bounds clip on `wading_rect` | Always `wading_rect = wading_rect.clip(surface.get_rect())` | Sprites at map edges have their foot rect partially off-screen |
| Call `get_grass_tile_image_at` before confirming `map_manager` exists | Guard: `if not self.game.map_manager: return` | `map_manager` can be None during scene transitions |
| Use `getattr(tile, "depth", 0)` in `get_grass_tile_image_at` | Use `getattr(tile, "depth", 0)` (consistent with `get_terrain_material_at`) | Same tile depth convention — depth > 1 = roof/ceiling, skip |
| Implement wading for water tiles via this feature | Keep `material == "grass"` as the only trigger | Water wading is a distinct visual and gameplay feature; scope must not expand |
| Pre-cache grass images in `MapManager.__init__` | Look up `tile.image` at probe time | Grass images are already loaded in `TileMapData` — no redundant cache needed |

---

## 9. Test Case Specifications

### Unit Tests — `tests/engine/test_render_manager.py`

| Test ID | Component | Setup | Expected |
|---------|-----------|-------|----------|
| GW-UT-001 | `_apply_grass_wading` | `map_manager.get_grass_tile_image_at()` returns a Surface; sprite on grass | `surface.blit` called for the wading zone |
| GW-UT-002 | `_apply_grass_wading` | `get_grass_tile_image_at()` returns None (sprite on dirt) | No blit performed for that sprite |
| GW-UT-003 | `_apply_grass_wading` | `walk_active=True` (scripted walk active) | Method never called (guarded in `draw_scene`) |
| GW-UT-004 | `_apply_grass_wading` | `sprite.rect = None` | Skip silently — no crash |
| GW-UT-005 | `_apply_grass_wading` | `sprite.image = None` | Skip silently — no crash |
| GW-UT-006 | `_apply_grass_wading` | `self.game.map_manager = None` | Return immediately — no crash |
| GW-UT-007 | `_apply_grass_wading` | `wading_rect` computed from sprite at bottom screen edge | `wading_rect.clip()` reduces height; blit still called with clipped rect |
| GW-UT-008 | `_apply_grass_wading` | Two sprites, one on grass and one on dirt | Only the grass sprite triggers blit |

### Unit Tests — `tests/map/test_manager.py`

| Test ID | Component | Setup | Expected |
|---------|-----------|-------|----------|
| GW-MM-001 | `get_grass_tile_image_at` | Tile at coords has `material="grass"` and `depth=0` | Returns `tile.image` (Surface) |
| GW-MM-002 | `get_grass_tile_image_at` | Tile at coords has `material="dirt"` | Returns `None` |
| GW-MM-003 | `get_grass_tile_image_at` | Tile has `material="grass"` but `depth=2` (roof) | Returns `None` — roof tile is skipped |
| GW-MM-004 | `get_grass_tile_image_at` | Pixel coords out of bounds (negative or > map size) | Returns `None` — no crash |
| GW-MM-005 | `get_grass_tile_image_at` | No tile at position (tile_id == 0) | Returns `None` |
| GW-MM-006 | `get_grass_tile_image_at` | Two stacked layers: top=dirt(depth=0), bottom=grass(depth=0) | Returns `None` — top layer (dirt) wins |
| GW-MM-007 | `get_grass_tile_image_at` | Two stacked layers: top=roof(depth=2), bottom=grass(depth=0) | Returns grass image — roof is skipped |

### Integration Tests

| Test ID | Flow | Setup | Verification |
|---------|------|-------|--------------|
| GW-IT-001 | Full draw_scene — grass | Map with grass tile under player rect | `_apply_grass_wading` runs without exception; no regression in existing render passes |
| GW-IT-002 | NPC on grass | NPC sprite positioned on grass tile | Wading blit applied to NPC sprite zone |
| GW-IT-003 | Scripted walk guard | `_intra_walk_target` set on game | `_apply_grass_wading` not called |

### Linked Test Functions

| Test ID | Function | File |
|---------|----------|------|
| GW-UT-001–008 | `test_grass_wading_*` | `../../tests/engine/test_render_manager.py` |
| GW-MM-001–007 | `test_get_grass_tile_image_at_*` | `../../tests/map/test_manager.py` |

---

## 10. Error Handling Matrix

| Error Type | Detection | Response | Fallback |
|------------|-----------|----------|----------|
| `map_manager` is None | Guard at method entry | `return` immediately | No wading, no crash |
| `sprite.rect` is None | `if not sprite.rect: continue` | Skip sprite | No blit attempt |
| `sprite.image` is None | `if not sprite.image: continue` | Skip sprite | No blit attempt |
| `get_grass_tile_image_at` returns None | `if grass_img is None: continue` | Skip sprite | No blit |
| `wading_rect` empty after clip | `if wading_rect.width <= 0: continue` | Skip sprite | No blit |
| `grass_crop` partially out of tile image | `pygame.Surface.blit` clips automatically | Silent clipping | Partial correct blit |

---

## 11. Assumptions

| # | Assumption | Risk | Validation |
|---|------------|------|------------|
| 1 | All grass autotiles (`00-grass-1/2/3/4/5`) have `depth=0` — they are background tiles | Low | Confirmed from TSX files — no depth property set |
| 2 | Grass tiles have `material="grass"` set at tileset level (no per-tile override required) | Low | Confirmed in all 00-grass-*.tsx |
| 3 | `TILE_SIZE = 32px` — wading zone of 10px ≈ bottom third | Low | Confirmed in Settings |
| 4 | `visual_rect` formula must match `custom_draw` and `_apply_partial_occlusion` exactly | Low | Invariant enforced in camera-rendering.md §4.3.2 |
| 5 | At most 3–4 sprites visible on screen simultaneously — per-sprite blit overhead negligible | Medium | Verify with `scripts/profile_game.py` if NPC count grows |
| 6 | No grass tile has `depth=1` (bridge-level) — only `depth=0` (ground) | Low | Confirmed from all TSX files |
| 7 | The effect must NOT be applied during `walk_active` (scripted walk) | Low | Consistent with `_apply_partial_occlusion` guard |
| 8 | `tile.image` is the full 32×32 tile surface and does not require any crop for the default case | Low | TileMapData.image is always a 32×32 subsurface of the spritesheet |

---

## 12. Deep Links

- **`RenderManager`**: [render_manager.py L6](../../src/engine/render_manager.py#L6)
- **`RenderManager.draw_scene()`**: [render_manager.py L224](../../src/engine/render_manager.py#L224)
- **`RenderManager._apply_partial_occlusion()`**: [render_manager.py L143](../../src/engine/render_manager.py#L143)
- **`MapManager`**: [manager.py L9](../../src/map/manager.py#L9)
- **`MapManager.get_terrain_material_at()`**: [manager.py L277](../../src/map/manager.py#L277)
- **`TileMapData.properties`**: [tmj_parser.py L12](../../src/map/tmj_parser.py#L12)
- **`Settings.OCCLUSION_ALPHA`** (parallel constant): [config.py L136](../../src/config.py#L136)
- **`CameraGroup.get_sorted_sprites()`**: [groups.py L76](../../src/entities/groups.py#L76)
- **`CameraGroup.custom_draw()`**: [groups.py L91](../../src/entities/groups.py#L91)
- **Walk guard pattern**: [camera-rendering.md §4.3.3](./camera-rendering.md#L259)
- **Partial occlusion spec (reference pattern)**: [camera-rendering.md §4.3.2](./camera-rendering.md#L185)
- **Map-world material query**: [map-world-system.md §4.2](./map-world-system.md#L83)
- **Grass tileset (source)**: [00-grass-1.tsx L1](../../assets/tiled/autotiles/00-grass-1.tsx#L1)
- **Test file (render manager)**: [test_render_manager.py L1](../../tests/engine/test_render_manager.py#L1)
- **Test file (map manager)**: [test_manager.py L1](../../tests/map/test_manager.py#L1)
