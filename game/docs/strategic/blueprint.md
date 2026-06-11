# Strategic Blueprint — Stair Climbing Alignment & Positioning Fixes
> Date: 2026-06-11
> Target: Pygame-CE Game Engine - Entity movement and rendering

---

## 1. Success Metrics

Our objective is to ensure pixel-perfect and logically symmetric stair traversal for both the player and NPCs:

| Metric | Baseline | Target | Timeline |
|---|---|---|---|
| **Y-Coordinate Drift** | 32 pixels (1 tile) shift on descent | **0 pixels** (perfect coordinate alignment) | Immediately after implementation |
| **Step-On Alignment** | Sprite rendered in the wall (0 offset) | **Feet aligned with step** | Immediately after implementation |
| **Middle-Step Floating** | Sudden 44px jump (floats too high) | **Smooth visual ascent/descent** | Immediately after implementation |
| **Regression Rate** | N/A | **0% broken tests** (100% pass rate) | Immediately after implementation |

---

## 2. Constraint Mapping

- **Hitbox Integrity**: Do not modify `sprite.rect` or the collision checking engine. The physics and collision bounds must remain standard axis-aligned bounding boxes (AABB) on the 2D grid.
- **NPC Compatibility**: NPCs traversing the stairs must share the exact same movement interception, boundary, and offset interpolation rules.
- **Tiled Properties**: No modifications to map assets (`.tmj`) or tileset (`.tsx`) property schemas. The engine must dynamically consume the existing properties (`stair_direction` and `visual_y_offset`).
- **No External Dependencies**: Keep all calculations self-contained within standard Pygame-CE functions to prevent library dependencies or runtime overhead.

---

## 3. Architecture Direction

We will implement a dual-part solution in `BaseEntity` and `CameraGroup`:
1. **Symmetric Step-Off Boundary Rule**: Intercept diagonal stair movement only if the target tile in the player's current direction is also a stair tile. If it is a floor tile, bypass diagonal interception and move orthogonally (flat).
2. **Visual Offset Interpolation**:
   - Cache starting offset and target offset at the beginning of a step.
   - Interpolate `self.current_stair_offset` linearly based on step progress (distance to target / total step distance).
   - Draw sprites using `sprite.current_stair_offset` instead of static tile-based offsets.

---

## 4. Exclusions & Boundaries

- **No Custom Pathfinding Changes**: We will not rewrite or modify NPC pathfinding algorithms for stairs. They will continue using standard grid coordinates.
- **No Collision Layer Alterations**: No custom stair ramps or sloped collision polygons will be added to the physics engine.
- **No Manual Coordinate Snapping**: Avoid teleporting or snapping coordinates at the end of steps to resolve alignment; the movement system must naturally land on correct coordinates.

---

## 5. Risk Assessment

| Risk | Severity | Probability | Mitigation |
|---|---|---|---|
| **NPC Pathfinding Stalls** | 🟠 High | 🟢 Low | Ensure the step-off check correctly evaluates walkability and direction flags before applying orthogonal movement. |
| **Visual Flickering / Jumps** | 🟡 Medium | 🟡 Medium | Linear interpolation must be updated every frame in `BaseEntity.update(dt)` using accurate delta-time scale. |
| **Test Failures on Map Coordinate Checks** | 🟠 High | 🟢 Low | Ensure target positions match the exact 32-pixel grid system. Orthogonal step-off restores coordinate alignment naturally. |
