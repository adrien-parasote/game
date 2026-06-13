# ADR-015: Dynamic Stair Clipping Strategy

## Status
Accepted (integrated into stair-movement.md v7, 2026-06-13)

## Context
When the player descends stairs (specifically tiles where the player is visually lower but technically still on the grid, like IDs 16 and 35 in `01-stairs.tsx`), their sprite continues to render entirely. This breaks the illusion of descent, as the player's legs should be hidden behind the staircase geometry.

We need a mechanism to dynamically clip the bottom half of the player sprite. The clipping must be proportional to their movement down the stairs.

## Decision

We will implement **Composition-based Clipping** driven by a new Tiled property `stair_clip`.

### 1. Tiled Property (`stair_clip`)
*   We will add a boolean property `stair_clip = true` to specific stair tiles (like ID 16 and 35).
*   **Why a boolean instead of an integer?** It keeps the Tiled workflow simple. The maximum clip amount is a fixed value derived from the stair step geometry: `float(Settings.TILE_SIZE // 2)` = 16.0 pixels. This avoids hardcoding pixel values in the map file and ensures the clip matches the physical step height, not the sprite height.

### 2. Code Interpolation (`BaseEntity`)
*   Similar to how `visual_y_offset` is interpolated into `current_stair_offset`, we will introduce `current_stair_clip`.
*   When moving towards a tile with `stair_clip = true`, the target clip is `float(Settings.TILE_SIZE // 2)` (16.0 pixels). Otherwise, it's `0.0`.
*   **Why `TILE_SIZE // 2` instead of `sprite.image.get_height() // 2`?** The clipping represents the stair step height (a fixed geometric property of the tileset), not a proportion of the sprite. Using sprite height would cause taller sprites (e.g. 48px or 64px) to be clipped above the step face, creating a "floating torso" artifact. See `_max_stair_clip()` in stair-movement.md §1.3.
*   This ensures the player smoothly "sinks" into the stairs as they move.

### 3. Rendering Approach (Composition)
*   Instead of using `subsurface` (which alters the physical height of the image and could disrupt camera anchoring or occlusion logic), we will use image composition.
*   The composition is integrated directly into the `custom_draw()` rendering pipeline in `CameraGroup`.
*   It creates a transparent surface of the exact same size as the sprite, blits the sprite onto it, and clears the bottom area (defined by `current_stair_clip`) with `(0,0,0,0)` using `BLEND_RGBA_MIN`.
*   This preserves the original `sprite.image` dimensions, matching the existing occlusion and wading rendering patterns.

## Consequences
*   **Positive:** Smooth, dynamic visual effect that sells the illusion of depth. No collision or camera logic changes required.
*   **Negative:** Requires an extra composition pass for entities on stairs, but performance impact is negligible since it only applies to moving entities on specific tiles.
