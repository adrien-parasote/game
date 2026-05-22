# Implementation Plan — Partial Sprite Occlusion

This implementation plan details the addition of a **generic, partial sprite occlusion system** in the game's rendering pipeline. This replaces the full-sprite alpha transparency currently applied only to the player, extending high-quality partial-occlusion rendering to the player and all NPC entities.

## Spec Gate Score & Findings

The specification file [partial-sprite-occlusion.md](file:///Users/adrien.parasote/Documents/perso/game/docs/specs/partial-sprite-occlusion.md) has successfully passed all structural gates:
* **Structural Precheck Score**: **10/10** (0 FAILs, 8 PASSes)
* **Test Case Standard**: Checked and standardized to standard unit (`UT-xxx`) and integration (`IT-xxx`) formats.
* **Deep Links Validity**: 100% of the 13 file/heading links are anchored with section/line markers (`#L...`).
* **AI Coder Understandability Score**: **10/10**.

## Adversarial Review Summary

An adversarial review (self-model preflight) was performed on the updated spec. The following critical design considerations were identified and resolved in the spec's design:

### 1. Pygame Alpha Blending Destination Clear (CRITICAL)
* **Problem**: Standard Pygame alpha blending preserves the destination's alpha if you blit a semi-transparent surface on top of an opaque surface of the same color. Simply blitting a semi-transparent layer over `composite` makes the composite remain fully opaque.
* **Resolution**: Prior to blitting the semi-transparent `alpha_surface`, the intersection area inside `composite` must be cleared to fully transparent: `composite.fill((0, 0, 0, 0), local_rect)`.

### 2. Depth-Sorting Layer Order (HIGH)
* **Problem**: Drawing occlusion overlays *after* `custom_draw` completes breaks depth sorting. Background sprites' transparent areas would be blitted on top of foreground sprites.
* **Resolution**: The **Swap-and-Restore Pattern** was chosen. The composite surfaces are generated and swapped into `sprite.image` *before* `custom_draw()` is invoked. Pygame then naturally depth-sorts and renders the composite sprites perfectly. Immediately after `custom_draw()`, the original images are restored.

### 3. Scripted Walk Compatibility (HIGH)
* **Problem**: During a scripted walk (`_intra_walk_target` is active), the player sprite is made completely invisible (`_player_transparent`). Applying occlusion to an invisible sprite would produce a visible alpha artifact.
* **Resolution**: Retain the `walk_active` check to skip occlusion composite generation entirely during scripted walk transitions.

---

## User Review Required

> [!IMPORTANT]
> **Signature Change**: `RenderManager.draw_foreground` will change its public return signature from `-> bool` to `-> list[pygame.Rect]`. This changes how existing unit tests `TC-OCC-001` and `TC-OCC-002` assert behavior, and these tests are being retrofitted to `UT-011` and `UT-012` to assert list contents/length instead of boolean returns.

> [!TIP]
> **Performance Optimization**: By filtering sprites using `sprite_screen_rect.colliderect(occ_rect)` before computing fine clipping, we bypass expensive surface operations for 95%+ of invisible or non-occluded entities.

---

## Proposed Changes

---

### Component: Rendering Engine

#### [MODIFY] [render_manager.py](file:///Users/adrien.parasote/Documents/perso/game/src/engine/render_manager.py)
* Update `draw_foreground()` to return a `list[pygame.Rect]` of all screen-space rects representing active occluding tiles (layers with depth > player.depth and tiles with depth > player.depth).
* Remove the direct tile-by-tile player collision checks and player `set_alpha` mutations from `draw_foreground()`.
* Implement the new private helper `_apply_partial_occlusion(occluding_rects: list[pygame.Rect]) -> dict[pygame.sprite.Sprite, pygame.Surface]`:
  * Returns a dictionary mapping mutated sprites to their original opaque images for immediate post-render restoration.
  * For each sprite, constructs the screen-space `visual_rect` using `sprite.image.get_rect(bottomright=sprite.rect.bottomright) + cam_offset`.
  * Computes standard Pygame intersections: `sprite_screen_rect.clip(occ_rect)`.
  * For occluded areas: clears `composite` using `fill((0, 0, 0, 0))` and blits `alpha_surface` with `Settings.OCCLUSION_ALPHA`.
* In `draw_scene()`, replace the player-specific alpha override block with the generic swap-and-restore pipeline:
  1. Call `occluding_rects = draw_foreground()`.
  2. If `not walk_active`, swap sprite images: `saved_images = self._apply_partial_occlusion(occluding_rects)`.
  3. Invoke `self.game.visible_sprites.custom_draw(self.game.screen, min_depth=self.game.player.depth)`.
  4. Restore all swapped sprite images: `sprite.image = original_image`.

---

### Component: Test Suite

#### [MODIFY] [test_render_manager.py](file:///Users/adrien.parasote/Documents/perso/game/tests/engine/test_render_manager.py)
* Retrofit existing occlusion tests to match the new `draw_foreground()` signature (asserting list elements or emptiness).
* Add new unit and integration tests covering:
  * Static and animated tile rect collection.
  * Correct composite surface creation (transparent intersection, opaque non-intersection).
  * Multiple overlapping occluding rects.
  * Suppression of occlusion during active scripted walk.

---

## Verification Plan

### Automated Tests
* Run the specific render manager test suite:
  ```bash
  pytest tests/engine/test_render_manager.py -v
  ```
* Run the full regression test suite to guarantee 100% passing tests:
  ```bash
  pytest
  ```

### Manual Verification
* Visual verification in-game: Walk the player and NPCs behind static trees/chimneys and verify that only the feet/body sections intersecting the tiles become semi-transparent, while heads/upper sections remain 100% opaque.
* Verify there is zero rendering lag or frame rate dropping when multiple NPCs are occluded simultaneously.
