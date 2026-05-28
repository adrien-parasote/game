# Strategic Blueprint — Partial Occlusion of Entity Sprites

> Document Type: Strategic
> Created: 2026-05-22

## Problem

NPC sprites (32×48px visually, 32×32px hitbox) receive a global alpha (`set_alpha(OCCLUSION_ALPHA)`) as soon as any part of their sprite overlaps a foreground tile (depth > player.depth). This behavior is visually incorrect: if only the NPC's feet are behind a wall, the head is as well.

**Expected Behavior:** Only the portion of the sprite physically on the occluding tile becomes semi-transparent. The rest remains opaque.

## Success Metrics

- Bottom part of the sprite on depth 2 tile → visible alpha
- Top part of the sprite off depth 2 tile → opaque
- Transition (partial overlap) → clean and stable split
- 60 FPS maintained (`clock.get_fps() > 55` with 2 occluded NPCs)
- Player: unchanged global alpha — TC-OCC-001/002 remain green

## Architectural Decision (→ ADR-007)

**Selected Option: SRCALPHA Composite Surface per Occluded NPC**

For each NPC whose visual sprite intersects an occluding tile:
1. Create a temporary `SRCALPHA` surface with the dimensions of the sprite
2. Perform a normal blit of the complete (opaque) image
3. For each sprite×tile intersection: draw the zone in alpha
4. Blit the composite surface onto the screen

O(1) calculation per intersection via `pygame.Rect.clip()`.
Surface allocated only when occlusion occurs (rare case).

**Rejected Alternatives:**
- `set_clip()` on screen: inversion logic is difficult to read
- Modifying `custom_draw()` API: couples `groups.py` too tightly to the occlusion system

## Impacted Pipeline

```
draw_foreground() → list[pygame.Rect]   ← CHANGE: bool → list (screen-space rects)
draw_scene() → uses the list for pass 3b NPC
custom_draw() → unchanged (CameraGroup remains generic)
```

## Scope of Affected Sprites

Partial occlusion applies to **all sprites** in pass 3b (`custom_draw(min_depth=player.depth)`):
- NPCs (sprite > TILE_SIZE)
- **Player** (same logic, same alpha)
- Interactive items if they have a sprite larger than a tile

The logic is generic — no entity-type-specific processing.

## Explicit Exclusions

| Exclusion | Precise Reason |
|---|---|
| Animated foreground tiles | ⚠️ Decision pending — see Gap #2 |
| Occluding zone cache | YAGNI — max 2-3 occluded sprites simultaneously |
| Lighting interaction | Sprite alpha does not impact the lighting system |

## Gaps Resolved Before SPEC

| # | Gap | Decision |
|---|---|---|
| 1 | `draw_foreground()` returns a bool → tests to adapt | Change the return type: `list[pygame.Rect]` (empty list = no occlusion, evaluates to False → partial backward compatibility) |
| 2 | Animated foreground tiles included? | ✅ **Yes — included.** Animated tiles do not yet have depth > 1 but will. The occluding rect collection scans `get_visible_animated_chunks()` in addition to static ones. When depth > 1 animated tiles exist, this will work automatically. |
| 3 | Variable sprite size in the future? | ✅ **Plan ahead** — use `sprite.image.get_size()` dynamically at each frame, never use cached sizes. Composite surface allocated at the current size of the active frame. |
| 4 | Generic Player? | ✅ **Yes — player included.** The logic is applied to all sprites in pass 3b. The player loses their global `set_alpha()` in favor of partial occlusion. |

**All gaps are resolved. STRATEGY complete. Ready for SPEC.**
