# ADR-016: Dynamic Stair Slope Alternation and Clipping Removal

## Status
Accepted (integrated into vertical-move specification, 2026-06-17)

## Context
When characters traverse diagonal stairs, moving strictly diagonally on a 32x32 grid creates a 45-degree angle of movement (red line in `wrong.png`). However, the staircase artwork is drawn at a shallower 26.5-degree slope (16px vertical rise for every 32px horizontal run). To align the character's feet with the artwork (green line in `right.png`), the movement must alternate between flat steps `(1,0)` and diagonal steps `(1,-1)`.

Previously, this was managed by explicitly tagging tiles with a boolean `half` / `stair_half` property in the Tiled editor to tell the engine when to move flat vs. diagonally. The user deleted the `half` property from the Tiled class to simplify tileset configuration and requested that we handle this dynamically.

Additionally, the user requested the complete removal of the `stair_clip` / `clip` depth clipping code and variables to keep the initial refactor simpler.

## Decision
We will dynamically determine the step alternation in Python without requiring a dedicated `half` property in Tiled. We will also completely remove the depth clipping logic.

### 1. Dynamic Slope Alternation
* We already configure a non-zero `visual_y_offset` (such as `-16`) in Tiled for the upper portion of steps, and `0` for the lower portion of steps.
* The engine will dynamically calculate `stair_half` based on the tile's `visual_y_offset` property:
  ```python
  stair_half = (visual_y_offset != 0)
  ```
* Climbing up: diagonal step happens when `stair_half` is true.
* Descending down: diagonal step happens when `stair_half` is false (or `not stair_half`).
* This enables perfect alignment with the 26.5-degree slope, preventing coordinate drift and floating sprites, while keeping the Tiled asset authoring process extremely simple.

### 2. Clipping Logic Removal
* The `stair_clip` property and the `current_stair_clip`, `stair_start_clip`, `stair_target_clip` attributes are completely deprecated and removed.
* The transparent composition surface and RGBA-min alpha clearing code inside `CameraGroup.custom_draw()` will be deleted.

## Consequences
* **Positive:** Simpler Tiled tileset class definition with fewer properties to maintain. Zero coordinate drift and perfect visual slope tracking (26.5°). Less complex rendering logic.
* **Negative:** None. Any future depth clipping will be implemented as a separate feature layer.
