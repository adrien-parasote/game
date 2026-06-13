# Discovery: Dynamic Stair Clipping

> **Note:** This document replaces the previous French version.

## Objective
Dynamically clip the bottom half of the player sprite (so only the upper half is visible) when descending on specific stair tiles (e.g., ID 16 and 35 in `01-stairs.tsx`). The rest of the tile (rendered at `depth=0`) must remain visible behind the player. The clipping effect should be dynamic and proportional to the player's movement on the stairs, hiding up to half of the sprite.

## 1. Tiled Modifications (`01-stairs.tsx`)
We need a way to identify the tiles that require clipping.
*   **Approach:** Add a custom property to the target tiles (e.g., `stair_clip` (boolean) or `stair_clip_max` (integer)).
*   **Why:** This allows the game engine to differentiate these specific tiles from regular stairs without hardcoding tile IDs.

## 2. Code Modifications: Map Manager (`map/manager.py`)
The engine extracts stair properties via `get_vertical_move_props()`.
*   **Approach:** Extract the new `stair_clip` property from the Tiled properties and include it in the returned dictionary.

## 3. Code Modifications: Entity Logic (`entities/base.py`)
The player entity already features smooth interpolation for `visual_y_offset` (via `update_stair_offset()`). We need to mirror this for the clipping effect so that it feels dynamic during movement.
*   **Approach:** Introduce new attributes like `self.current_stair_clip` (float), `self.stair_start_clip`, and `self.stair_target_clip`.
*   **Movement:** During `start_move()`, set `stair_target_clip` (e.g., `16.0` if the target tile triggers clipping, else `0.0`).
*   **Interpolation:** In `update_stair_offset()`, interpolate `current_stair_clip` between the start and target values based on movement progress.

## 4. Code Modifications: Rendering (`engine/render_manager.py`)
Currently, Pygame-CE draws the entire `sprite.image`. To dynamically hide the bottom part, we can draw inspiration from the existing `WadingRenderer` (which composites grass over the sprite).
*   **Approach A: Image Composition**
    Create a transparent composite surface. Blit the sprite onto it, then clear the bottom area (height defined by `current_stair_clip`) using a transparent fill (e.g., `pygame.BLEND_RGBA_MIN` or `fill((0,0,0,0))` on a subsurface). Temporarily replace `sprite.image` with this composite before calling `custom_draw`.
*   **Approach B: Subsurface (Subsurface)**
    Instead of altering pixels, redefine `sprite.image` as a subsurface of the original image: `sprite.image.subsurface((0, 0, width, height - current_stair_clip))`. 
    *Warning:* This modifies the height of the visual `rect`. We must ensure that positioning (often managed by the sprite's center or bottom) remains correct relative to the camera.
*   **Recommendation:** Composition (Approach A) is safer and integrates perfectly with the current rendering pipeline (which uses `saved_images` for occlusion and wading), as it preserves the original dimensions of `sprite.image`.

## Conclusion of the DISCOVER Phase
The current architecture makes it straightforward to integrate this effect. We can reuse the interpolation pattern already in place for `visual_y_offset` and the image composition pattern used for occlusion and grass wading.
