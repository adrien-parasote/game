# Grass Wading Effect — Implementation Plan

## Objective

When the player or an NPC walks on autotiles with `material = "grass"`, the bottom third of their sprite appears to be **inside the grass** rather than superimposed on top of it.

## Visual Effect (user-validated)

- **Re-blit** the grass tile image over the lower portion of the sprite (feet disappear into the grass)
- **Semi-transparency** on that same lower zone (makes the transition softer)
- Combined = most immersive result

## Zone affected

- **Bottom 10px** of the 32×32 sprite (tiers inférieur)
- Configurable via `Settings.GRASS_WADING_DEPTH = 10`

## Assumptions

| Assumption | Risk |
|---|---|
| Grass tiles stay at depth=0 (background) | Low — confirmed, footstep audio depends on it |
| TILE_SIZE = 32px | Low — confirmed in Settings |
| Effect applies to player AND NPCs | Low — user intent |
| `material = "grass"` is the trigger property | Low — confirmed in all 00-grass-*.tsx |
| Bottom 10px = wading zone | Low — user validated |

---

## Proposed Changes

### Step 1: Configuration (`src/config.py` + `settings.json`)

#### [MODIFY] [config.py](file:///Users/adrien.parasote/Documents/perso/game/src/config.py)

Add two new settings in `_DEFAULTS["overlay"]` and `_apply_systems()`:

```python
# In _DEFAULTS["overlay"]:
"grass_wading_depth": 10,     # pixels from bottom of sprite
"grass_wading_alpha": 140,    # alpha of the re-blit zone (0-255)
```

Expose as:
- `Settings.GRASS_WADING_DEPTH: int` — height in pixels of the wading zone
- `Settings.GRASS_WADING_ALPHA: int` — alpha applied to the wading zone

#### [MODIFY] [settings.json](file:///Users/adrien.parasote/Documents/perso/game/settings.json)

```json
"overlay": {
  "occlusion_alpha": 102,
  "grass_wading_depth": 10,
  "grass_wading_alpha": 140
}
```

---

### Step 2: Map Manager (`src/map/manager.py`)

#### [MODIFY] [manager.py](file:///Users/adrien.parasote/Documents/perso/game/src/map/manager.py)

Add new method `get_grass_tile_image_at(pixel_x, pixel_y) -> pygame.Surface | None`:

- Same logic as `get_terrain_material_at()` (find highest depth≤1 tile at position)
- Returns `TileMapData.image` if `material == "grass"`, else `None`
- Used by `RenderManager` to get the exact grass pixel art to re-blit

> **Why a new method?** `get_terrain_material_at()` only returns a string. We need the Surface. Keeping them separate avoids changing the existing footstep API.

```python
def get_grass_tile_image_at(self, pixel_x: int, pixel_y: int) -> pygame.Surface | None:
    """Return the image of the grass tile at the given pixel position, or None."""
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

---

### Step 3: Render Manager (`src/engine/render_manager.py`)

#### [MODIFY] [render_manager.py](file:///Users/adrien.parasote/Documents/perso/game/src/engine/render_manager.py)

Add private method `_apply_grass_wading(surface: pygame.Surface)` and call it in `draw_scene()`.

**Algorithm:**

```
For each sprite in visible_sprites.get_sorted_sprites():
  1. Skip if no rect or no image
  2. Compute visual screen rect (same formula as custom_draw)
  3. Probe grass at sprite foot position: (rect.centerx, rect.bottom - 2)
     → get_grass_tile_image_at(world_x, world_y)
  4. If no grass image → skip
  5. Compute wading_rect = bottom GRASS_WADING_DEPTH pixels of sprite screen rect
  6. Clip wading_rect to screen bounds
  7. Re-blit grass tile image, aligned to tile grid, clipped to wading_rect
  8. Blit a semi-transparent black surface over wading_rect at GRASS_WADING_ALPHA
     to blend the sprite zone into the grass
```

**Grass image alignment:**
```
world_foot_x = sprite.rect.centerx
world_foot_y = sprite.rect.bottom
tile_origin_x = (world_foot_x // tile_size) * tile_size
tile_origin_y = (world_foot_y // tile_size) * tile_size
screen_tile_x = tile_origin_x + cam_offset.x
screen_tile_y = tile_origin_y + cam_offset.y
```
Then clip the grass image blit to `wading_rect` only.

**Call in `draw_scene()`:**
```python
# After: self.game.visible_sprites.custom_draw(min_depth=player.depth)
# Before: lighting_manager.draw_additive_window_beams(...)
if not walk_active:
    self._apply_grass_wading(self.game.screen)
```

---

## Rendering Pipeline After Change

```
draw_background()              → tiles depth=0 (grass rendered here)
custom_draw(max_depth=0)       → sprites depth < player.depth
draw_foreground()              → tiles depth > player.depth  
custom_draw(min_depth=1)       → sprites depth ≥ 1 (player + NPCs drawn fully)
_apply_grass_wading()          → [NEW] re-blit grass pixels + alpha over feet zone
lighting beams + night overlay → unchanged
effects, HUD, dialogue...      → unchanged
```

> [!IMPORTANT]
> `_apply_grass_wading()` runs AFTER sprites are fully drawn — it paints grass texture OVER the already-rendered sprite bottom zone.

---

## Verification Plan

### Automated Tests (TDD Gate)

New tests in `tests/engine/test_render_manager.py`:
- `test_grass_wading_applies_when_on_grass()` — sprite on grass tile → wading blit occurs
- `test_grass_wading_skipped_when_not_on_grass()` — sprite on dirt → no blit
- `test_grass_wading_skipped_during_walk()` — `_intra_walk_target` set → no effect
- `test_grass_wading_skipped_no_sprite_rect()` — sprite.rect=None → no crash

New tests in `tests/map/test_manager.py`:
- `test_get_grass_tile_image_at_returns_surface()`
- `test_get_grass_tile_image_at_returns_none_for_non_grass()`
- `test_get_grass_tile_image_at_returns_none_out_of_bounds()`

### Manual Verification

1. `python3 src/main.py` — walk on grass areas → bottom of sprite shows grass texture over feet
2. Walk on dirt/stone → NO effect
3. NPC walking on grass → same effect applies
4. No flickering, no performance regression (profile with `scripts/profile_game.py` if needed)
