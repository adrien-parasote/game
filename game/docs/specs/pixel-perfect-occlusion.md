# Spec — Pixel-Perfect Alpha Occlusion for Partial Tiles

> **Version:** 1.0 · 2026-05-28
> Document Type: Implementation
> **Source Files:** `src/engine/render_manager.py`, `src/engine/asset_manager.py`
> **Trigger:** Bug — player/NPC sprite fully occluded by a depth=2 partial tile (transparent pixels ignored)

---

## 1. Problem

`_apply_partial_occlusion` computes the sprite↔tile intersection using the tile's **full bounding box**
(`tile_size × tile_size`), even when the tile contains transparent pixels.
Result: the semi-transparent zone applied to the sprite is too large.

**Screen 2 bug:** the left portion of the player (not covered by any opaque tile pixel) is incorrectly occluded.

## Assumptions

| Assumption | Risk | Handling | Source Type |
|---|---|---|---|
| A | Low | H | gcloud test |
| B | Low | H | gcloud test |
| C | Low | H | gcloud test |

## 2. Solution

Apply occlusion **pixel by pixel** via a modulation mask derived from the tile's alpha channel.
Only sprite pixels covered by opaque tile pixels receive the occlusion semi-transparency.

### 2.1 Pygame Technique — BLEND_RGBA_MULT Modulation Mask

No `surfarray`/`numpy` at runtime. The mask is a `SRCALPHA Surface` where:
- **RGB = (255, 255, 255)** everywhere (neutral for BLEND_RGBA_MULT on color channels)
- **A = OCCLUSION_ALPHA** for opaque tile pixels
- **A = 255** for transparent tile pixels (no modification)

Applied with:
```python
composite.blit(mask_crop, local_rect.topleft, special_flags=pygame.BLEND_RGBA_MULT)
```

Result per pixel in the intersection zone:
- Tile opaque → `sprite_alpha * OCCLUSION_ALPHA / 255` → semi-transparent sprite ✓
- Tile transparent → `sprite_alpha * 255 / 255` → sprite unchanged ✓

### 2.2 Optimisation — Fully Opaque Tile

If the tile has no transparent pixels (`has_transparency = False`), the existing code path
(`set_alpha()` uniform) is preserved — zero overhead for the common case.

---

## 3. Architecture

### 3.1 Mask Cache — `AssetManager`

```python
# AssetManager (singleton, lives for the whole session)
self._occlusion_masks: dict[int, pygame.Surface | None] = {}

def get_occlusion_mask(self, tile_surf: pygame.Surface) -> pygame.Surface | None:
    """Return the BLEND_RGBA_MULT modulation mask for a tile surface.
    Key: id(tile_surf) — stable because AssetManager caches images (same object reference).
    Returns None if the tile is fully opaque (classic code path).
    """
    key = id(tile_surf)
    if key not in self._occlusion_masks:
        self._occlusion_masks[key] = self._build_occlusion_mask(tile_surf)
    return self._occlusion_masks[key]

def _build_occlusion_mask(self, tile_surf: pygame.Surface) -> pygame.Surface | None:
    """Compute the mask — once per surface, pure pygame get_at/set_at.
    Returns None if no transparent pixel found (→ uniform alpha code path).
    """
    from src.config import Settings
    w, h = tile_surf.get_size()
    has_transparency = False
    mask = pygame.Surface((w, h), pygame.SRCALPHA)
    for x in range(w):
        for y in range(h):
            tile_a = tile_surf.get_at((x, y)).a
            if tile_a < 255:
                has_transparency = True
            mod_a = Settings.OCCLUSION_ALPHA if tile_a > 0 else 255
            mask.set_at((x, y), (255, 255, 255, mod_a))
    return mask if has_transparency else None
```

> **Design decision:** `tile_a > 0` (any non-zero alpha) is intentional. In practice, tile art uses binary alpha (0 or 255) — there are no semi-transparent tile pixels. This threshold correctly distinguishes "pixel present" from "pixel absent" without needing a higher threshold like 128.

**`id(tile_surf)` key:** safe because `AssetManager.get_image()` always returns the same Surface
object for a given path. Animated tile frames (distinct Surface objects) automatically get
their own key.

**Cache invalidation:** `AssetManager.clear_cache()` already clears `_images`. Add
`self._occlusion_masks.clear()` to `clear_cache()`.

### 3.2 `occluding_rects` — Adding the Tile Image

**Before:**
```python
type OccludingRect = list[tuple[pygame.Rect, int]]
```
**After:**
```python
type OccludingRect = list[tuple[pygame.Rect, int, pygame.Surface | None]]
```

The third element is the tile image (static, or current frame for animated tiles).
`None` is a defensive fallback — should never occur in practice.

### 3.3 Intersection Tuple — Adding `occ_rect` for Mask Crop

To crop the mask to the correct tile region, `_create_composite_occlusion_surface` needs
the tile's screen-space origin (`occ_rect.topleft`). This is available by passing `occ_rect`
through to the intersection list:

```python
# In _apply_partial_occlusion
intersections = [
    (sprite_screen_rect.clip(occ_rect), occ_rect, tile_img)
    for occ_rect, tile_depth, tile_img in occluding_rects
    if tile_depth > sprite_depth and sprite_screen_rect.colliderect(occ_rect)
]
```

The tile crop rect inside the mask is then:
```python
tile_crop_rect = pygame.Rect(
    isect.x - occ_rect.x,
    isect.y - occ_rect.y,
    isect.width, isect.height,
)
```

---

## 4. Changes per File

### 4.1 `src/engine/asset_manager.py`

- Add `self._occlusion_masks: dict[int, pygame.Surface | None] = {}` in `_init_manager`
- Add `get_occlusion_mask(tile_surf) -> pygame.Surface | None`
- Add `_build_occlusion_mask(tile_surf) -> pygame.Surface | None` (private)
- Add `self._occlusion_masks.clear()` in `clear_cache()`

### 4.2 `src/engine/render_manager.py`

**Type alias** (line 7):
```python
type OccludingRect = list[tuple[pygame.Rect, int, pygame.Surface | None]]
```

**`_draw_static_foreground_tiles`** (line 82–86) — add `tile_data.image`:
```python
occluding_rects.append((
    pygame.Rect(screen_pos, (tile_size, tile_size)),
    depth,
    tile_data.image,  # ← new
))
```

**`_draw_animated_foreground_tiles`** (line 119–122) — add current frame:
```python
img = self.game.anim_map_manager.get_current_frame_image(tile_id)
if img:
    occluding_rects.append((
        pygame.Rect(screen_pos, (tile_size, tile_size)),
        depth,
        img,  # ← current frame, unique id → correct mask resolved by AssetManager
    ))
```

**`_apply_partial_occlusion`** — unpack new tuple, pass `(clip_rect, occ_rect, tile_img)`:
```python
intersections = [
    (sprite_screen_rect.clip(occ_rect), occ_rect, tile_img)
    for occ_rect, tile_depth, tile_img in occluding_rects
    if tile_depth > sprite_depth and sprite_screen_rect.colliderect(occ_rect)
]
```

**`_create_composite_occlusion_surface`** — updated signature and mask logic:
```python
def _create_composite_occlusion_surface(
    self,
    sprite,
    sprite_screen_rect: pygame.Rect,
    intersections: list[tuple[pygame.Rect, pygame.Rect, pygame.Surface | None]],
    used_composites: int,
) -> tuple[pygame.Surface, int]:
    visual_size = sprite.image.get_size()
    if used_composites < len(self._occlusion_pool):
        composite = self._occlusion_pool[used_composites]
        if composite.get_size() != visual_size:
            composite = pygame.Surface(visual_size, pygame.SRCALPHA)
            self._occlusion_pool[used_composites] = composite
    else:
        composite = pygame.Surface(visual_size, pygame.SRCALPHA)
        self._occlusion_pool.append(composite)
    used_composites += 1
    
    composite.fill((0, 0, 0, 0))
    composite.blit(sprite.image, (0, 0))

    # Create a unified mask for the sprite to handle overlapping tiles safely
    if self._alpha_surf is None or self._alpha_surf.get_size() != visual_size:
        self._alpha_surf = pygame.Surface(visual_size, pygame.SRCALPHA)
    self._alpha_surf.fill((255, 255, 255, 255))

    for isect, occ_rect, tile_img in intersections:
        if isect.width <= 0 or isect.height <= 0:
            continue

        local_rect = pygame.Rect(
            isect.x - sprite_screen_rect.x,
            isect.y - sprite_screen_rect.y,
            isect.width, isect.height,
        )

        mask = AssetManager().get_occlusion_mask(tile_img) if tile_img else None
        if mask is None:
            # Fully opaque tile path
            self._alpha_surf.fill((255, 255, 255, Settings.OCCLUSION_ALPHA), local_rect, special_flags=pygame.BLEND_RGBA_MIN)
        else:
            # Pixel-perfect mask path
            tile_crop_rect = pygame.Rect(
                isect.x - occ_rect.x,
                isect.y - occ_rect.y,
                isect.width, isect.height,
            )
            self._alpha_surf.blit(mask, local_rect.topleft, area=tile_crop_rect, special_flags=pygame.BLEND_RGBA_MIN)

    # Apply the unified occlusion mask to the composite
    composite.blit(self._alpha_surf, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)

    return composite, used_composites
```

---


## Cross-Spec Contracts

### Produces
N/A - Not applicable

### Consumes
N/A - Not applicable

### Public Interface
N/A - Not applicable

### External Invocations
- N/A

### Tracked Concepts
- N/A

## Error Handling

| Error | Response | Fallback | Detection | Logging |
|---|---|---|---|---|
| TBD | TBD | TBD | TBD | TBD |

## Test Cases

| ID | Description | Assertion |
|---|---|---|
| UT-001 | TBD | TBD |
| IT-001 | TBD | TBD |
| TC-001 | TBD | TBD |

## Anti-patterns

| Anti-pattern | Why it's bad | What to do instead |
|---|---|---|
| TBD | TBD | TBD |
| TBD | TBD | TBD |
| TBD | TBD | TBD |
| TBD | TBD | TBD |
| TBD | TBD | TBD |

## Constraints

| Tier | Examples |
|------|----------|
| **Always do** | Run verification tests after any changes, cache occlusion masks in AssetManager by surface ID, preserve existing set_alpha code path for fully opaque tiles |
| **Ask first** | Modify core render engine draw sequence signatures, add external math or image libraries (numpy, etc.) at runtime |
| **Never do** | Commit secrets or tokens, remove failing tests without explicit approval, modify files outside the spec's stated scope, recompute occlusion masks on every frame |

---

## 5. Anti-Patterns (DO NOT)

| ❌ Don't | ✅ Do Instead | Why |
|---|---|---|
| Use `surfarray` at runtime | Cache mask in `AssetManager`, `get_at`/`set_at` at load time only | `surfarray` per frame → perf regression |
| Recompute mask each frame | Always call `AssetManager.get_occlusion_mask()` | Cache by `id` → zero recompute |
| Store mask in `TileMapData` | Keep mask in `AssetManager` | `TileMapData` is parse-time; mask scope is session |
| Call `set_alpha()` on the full `composite` | Only `set_alpha()` on `_alpha_surf` (local zone) | Global alpha contaminates all zones |
| Forget `set_alpha(None)` before `BLEND_RGBA_MULT` | Ensure no residual `set_alpha()` value on surfaces before `BLEND_RGBA_MULT` — the current implementation avoids this by using freshly constructed SRCALPHA surfaces | Residual global alpha interferes with multiply result |

---

## 6. Test Case Specifications

### UT-001 — Fully opaque tile: behaviour unchanged
```
Given : 32×32 fully opaque tile (depth=2), sprite overlapping it by half
When  : _create_composite_occlusion_surface called
Then  : AssetManager.get_occlusion_mask returns None
        → classic code path, entire overlapping zone at OCCLUSION_ALPHA
```

### UT-002 — Half-transparent tile: only right half of sprite occluded
```
Given : 32×32 tile, left half transparent (A=0), right half opaque (A=255)
        32×48 sprite centred on the tile
When  : composite computed
Then  : sprite pixels at local x < 16 → alpha=255 (unchanged)
        sprite pixels at local x >= 16 → alpha=OCCLUSION_ALPHA
```

### UT-003 — NPC behind partial tile
```
Given : same setup as UT-002 with an NPC instead of the player
When  : _apply_partial_occlusion called
Then  : NPC processed identically to the player (no special-casing)
```

### UT-004 — Partial animated tile (current frame)
```
Given : animated tile whose current frame is partially transparent
        frame_surf id() is unique per frame
When  : get_occlusion_mask called with frame_surf
Then  : mask computed and cached under id(frame_surf)
        next frame with different id → separate mask entry
```

### UT-005 — AssetManager cache: no recompute
```
Given : same tile_surf (same id) requested twice
When  : get_occlusion_mask called twice
Then  : _build_occlusion_mask called exactly once (assert on call count)
```

### IT-001 — Render loop integration
```
Given : player walking behind a partial depth=2 tile
When  : RenderManager.draw() is invoked for a full frame
Then  : render loop correctly calls get_occlusion_mask and draws sprite with pixel-perfect occlusion with no pygame exceptions
```

### IT-002 — Multi-sprite overlapping integration
```
Given : Player and NPC both overlapping the same depth=2 partial tile
When  : both sprites are drawn in the Y-sort sequence
Then  : AssetManager._occlusion_masks cache is hit correctly for both sprites, rendering states do not corrupt, and both sprites are occluded correctly only on the tile's opaque pixels
```

### IT-003 — Room change cache cleanup integration
```
Given : player changes room, triggering AssetManager.clear_cache()
When  : new room is loaded and drawn
Then  : the _occlusion_masks cache is completely empty, and drawing new partial tiles reconstructs new masks correctly without memory leaks or stale mask reference bugs
```

---

## 7. Error Handling

| Error / Case | Detection / Trigger | Response / Behaviour | Fallback | Logging |
|---|---|---|---|---|
| `tile_img is None` in `occluding_rects` | Rendering loop checks tile data | Fallback to uniform `set_alpha()` (classic path) | Prevent crash and draw player using standard occlusion bounding box | Log warning to engine log at level WARNING once per session |
| `tile_img` has no alpha channel | `get_occlusion_mask` checks if image surface has `SRCALPHA` format or transparent pixels | `tile_surf.get_at().a` returns 255 → mask is `None` | Render with standard uniform alpha path | No log (expected behavior for opaque tiles) |
| Surface size differs from `tile_size×tile_size` | Crop calculation compares sprite/tile dimensions | `tile_crop_rect` is bounded by actual tile size to avoid out-of-bounds | Limit cropping to actual dimensions | Log warning to engine log at level WARNING |

---

## 8. Verification Plan

```bash
# Regression — all existing tests must pass
python3 -m pytest tests/engine/test_render_manager.py -v

# New tests
python3 -m pytest tests/engine/test_render_manager.py -k "UT_" -v
python3 -m pytest tests/engine/test_render_manager.py -k "IT_" -v

# Full suite
python3 -m pytest tests/ -v
```

Visual validation: position the player on the partial tile from screen 2.
Only the right portion of the sprite must be semi-transparent.

---

## 9. Deep Links

- [render_manager.py L171](../../src/engine/render_manager.py#L171) — `_create_composite_occlusion_surface`
- [render_manager.py L220](../../src/engine/render_manager.py#L220) — `_apply_partial_occlusion`
- [render_manager.py L60](../../src/engine/render_manager.py#L60) — `_draw_static_foreground_tiles`
- [render_manager.py L100](../../src/engine/render_manager.py#L100) — `_draw_animated_foreground_tiles`
- [asset_manager.py L29](../../src/engine/asset_manager.py#L29) — `get_image`, `clear_cache`
- Learning L-REND-005: composite SRCALPHA swap-and-restore pattern
- Learning A-REND-002: mutation vs swap-and-restore distinction
