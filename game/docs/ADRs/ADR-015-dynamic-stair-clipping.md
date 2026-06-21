# ADR-015: Dynamic Stair Clipping Strategy

## Status
Accepted (2026-06-21)

## Context
When the player or NPCs descend stairs (specifically tiles where the player is visually lower but technically still on the grid, like descending stair tiles with the `clip = true` property), their sprite continues to render entirely. This breaks the illusion of descent, as the player's legs should be hidden behind the staircase geometry.

We need a mechanism to dynamically clip the bottom portion of the sprite, proportional to their movement down the stairs, while maintaining horizontal physical movement.

## Decision
We will implement **Direct Sprite Cropping (Skeleton A)** using Pygame-CE's `area` parameter in the `blit()` method, avoiding any transparent composite surface allocations.

### 1. Tiled Properties
* We will use the Tiled property `clip = true` (boolean) to identify tiles that require clipping.
* The clipping amount is determined by the absolute value of the `visual_y_offset` property.
* If `visual_y_offset` is empty or missing, it defaults to `8` pixels.
* The clipping amount is clamped to the sprite's height to prevent full invisibility or negative dimensions.

### 2. Code Interpolation (`BaseEntity`)
* Similar to `current_stair_offset` (which handles the vertical visual shift), we will introduce `current_stair_clip` (float) on `BaseEntity`.
* At the start of a movement in `start_move()`, the target clip value is computed based on the target tile's properties:
  - If `target_vm` has `clip = true`, target clip is `abs(target_vm["visual_y_offset"])` (defaulting to 8, clamped to sprite height).
  - Otherwise, target clip is `0.0`.
* In `update_stair_offset()`, `current_stair_clip` is smoothly interpolated between the start and target values using the movement progress percentage:
  ```python
  self.current_stair_clip = self.stair_start_clip + (self.stair_target_clip - self.stair_start_clip) * progress
  ```
* When standing still, `current_stair_clip` resolves directly to the current tile's clip amount.

### 3. Rendering Approach (Direct Sprite Cropping)
* In `CameraGroup.custom_draw()`, if `sprite` has a non-zero `current_stair_clip`, we pass an `area` parameter to `blit()` to only draw the top part of the sprite:
  ```python
  clip_amount = int(getattr(sprite, "current_stair_clip", 0.0))
  if clip_amount > 0:
      w, h = sprite.image.get_size()
      clip_amount = max(0, min(clip_amount, h))
      area = pygame.Rect(0, 0, w, h - clip_amount)
      surface.blit(sprite.image, offset_pos, area=area)
  else:
      surface.blit(sprite.image, offset_pos)
  ```
* This approach achieves zero dynamic memory allocation and requires no temporary surface composition.

## Consequences
* **Positive:** High performance (C-level Pygame-CE blit cropping), smooth visual effect, zero runtime memory allocations, no camera or physical collision changes.
* **Negative:** Simple rectangular clipping only (cannot mask along arbitrary slopes), but sufficient for the current tileset geometry.
