# ADR-007 — Partial Occlusion: Composite Surface vs Scissor Clip vs API Modifier

**Date:** 2026-05-22  
**Status:** Accepted  
**Context:** Feature for partial occlusion of NPC sprites (sprites > TILE_SIZE)

## Context

NPC sprites (32×48px) are larger than a single tile (32×32px). When an NPC passes behind a foreground tile (depth > player.depth), the current implementation applies a global `set_alpha()` to the entire image, which is visually incorrect. Only the portion of the sprite overlapping the occluding tile should be rendered with alpha.

Three approaches were evaluated.

## Options

### Option A — SRCALPHA Composite Surface (Chosen)

For each occluded NPC, create a temporary `SRCALPHA` surface with the same dimensions as the sprite. Perform a full opaque blit, then blit the occluded zone with alpha using `pygame.Rect.clip()`.

**Advantages:**
- Logic is localized in `RenderManager.draw_scene()`
- `CameraGroup.custom_draw()` remains generic and unchanged
- O(1) computation per intersection
- Surface is allocated only if the NPC is actually occluded (rare case)
- Readable and testable

**Disadvantages:**
- 1 `Surface()` allocation per occluded NPC per frame (≈ 32×48px SRCALPHA)
- If 2 NPCs are occluded simultaneously, this results in 2 small allocations per frame

### Option B — Modifying the `custom_draw()` API

Pass a list of occluding zones `(rect, alpha)` to `CameraGroup.custom_draw()`, and handle the clipping during each sprite's blit.

**Rejected because:**
- Couples the generic `CameraGroup` API to the specific occlusion system
- `custom_draw()` becomes untestable without mocking the occluding zones
- Violates the SRP: CameraGroup is responsible for camera + Y-sorting, not occlusion logic

### Option C — `pygame.Surface.set_clip()` (Scissor)

Use the screen surface's native clipping to separate opaque and alpha zones. Set the screen clip to the opaque zone, blit opaque, then set the screen clip to the occluded zone, and blit alpha.

**Rejected because:**
- Calculating the complement of rects is difficult for non-rectangular shapes
- Risk of forgetting to reset the clip, causing global graphical artifacts
- Less readable than explicit composition

## Decision

**Option A** — SRCALPHA composite surface in `draw_scene()`.

## Consequences

- `draw_foreground()` changes its return type: `bool` -> `list[pygame.Rect]` (the screen-space rects of the active occluding tiles)
- `draw_scene()` iterates over sprites in pass 3b to apply partial occlusion
- Tests TC-OCC-001/002 need to be adapted (bool -> truthiness of the list)
- The Player retains their current global alpha behavior (unchanged)

## Performance Invariant

`len(occluded_rects)` is bounded by the number of visible tiles with depth > 1.
On a 1280×720 viewport with 32×32 tiles: max ~1400 visible tiles, but occluding tiles represent a tiny fraction.
Simultaneously occluded NPCs: typically 0-2.
Performance impact: negligible.
