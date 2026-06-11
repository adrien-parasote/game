# ADR-013 — Stair Climbing Positioning and Alignment
> Status: Proposed
> Date: 2026-06-11

---

## 1. Context

In the 2D grid-based tile engine, diagonal and lateral staircases are traversed by intercepting orthogonal input (e.g. RIGHT/LEFT) and translating it into diagonal logical coordinates (e.g. RIGHT-UP / LEFT-DOWN). Currently, this traversal introduces two bugs:

1. **Step-Off Asymmetry (Y-Drift)**:
   When stepping onto a stair tile from the floor, the entry is orthogonal (flat Y). However, when stepping *off* the stair tile back onto the floor, the exit is intercepted as diagonal, shifting the entity down by 1 tile vertically. This asymmetry results in permanent coordinate drift.

2. **Abrupt Render Offset snaps**:
   Stair tiles visually rise by 12 pixels per step, whereas logical grid tiles are 32 pixels high. Currently, the visual offset (`visual_y_offset` = `-12`) is applied statically from the start of the step. This causes a lack of vertical elevation on the first step (rendering the entity inside the wall) and abrupt 44-pixel visual jumps on subsequent steps, causing the entity to appear to float.

---

## 2. Decision

We will implement two coordinated changes in the movement and rendering pipelines:

1. **Symmetric Step-Off Rule**:
   Modify `BaseEntity.start_move` to look ahead. If the player presses a direction, we compute the next flat tile in that direction.
   - To identify if a tile is a stair, explicitly check if `self.game.map_manager.get_vertical_move_props(tx, ty)` returns a valid dictionary.
   - If the next flat tile is a stair tile, apply the diagonal interception mapping from `VERTICAL_MOVE_MAP`.
   - If the next flat tile is a floor tile (returns `None`), bypass diagonal interception and move orthogonally (flat).
   This ensures that entry and exit boundary crossings are perfectly symmetric, resolving Y-coordinate drift.

2. **Visual Offset Interpolation**:
   - Add a dynamic attribute `self.current_stair_offset` (initialized to `0`) to `BaseEntity`.
   - When a step starts, cache the `start_pos`, the start visual offset, and determine the target offset by querying the target tile's properties.
   - During `BaseEntity.update(dt)`, if the entity is moving, calculate step progress carefully guarding against zero division:
     `total_dist = (self.target_pos - start_pos).magnitude()`
     `progress = 1.0 - (distance_to_target / total_dist)` if `total_dist > 0` else `1.0`.
   - Interpolate `self.current_stair_offset` linearly between start and target offsets using this progress value. If standing still, the offset matches the current tile's offset.
   - Update `CameraGroup.custom_draw` to apply the offset during rendering. Crucially, use safe property access `getattr(sprite, 'current_stair_offset', 0)` to prevent `AttributeError` for non-BaseEntity sprites (e.g. particles, items).

---

## 3. Consequences

- **Correctness**: Symmetrical entry/exit paths eliminate coordinate drift on stair descent.
- **Visual Smoothness**: Linear interpolation distributes the 12-pixel step offset smoothly across the 32-pixel step duration, aligning the sprite's feet with the stair graphic assets during movement.
- **NPC Compatibility**: All entities inheriting from `BaseEntity` (including NPCs) automatically benefit from the alignment fixes.
- **Isolation**: Collision logic and logical coordinates (`self.rect`) remain standard AABBs on the 32-pixel grid, ensuring safety and compatibility.
