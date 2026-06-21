# Strategic Blueprint: Vertical-Move Implementation Refactor

> Target Component: Stair & Ladder Movement
> Stage: 🎯 STRATEGY

## Success Metrics
- **Zero Coordinate Drift:** Traversing a staircase up and down returns the entity to the exact same logical starting coordinates.
- **Visual Angle Alignment:** Visual rendering coordinates must track the shallow 26.5-degree slope of the staircase (16px vertical rise per 32px horizontal step) without vertical jumps, pops, or sinking/floating artifacts.
- **Correct Input Locking:** On stair tiles, UP/DOWN directional inputs must be ignored. On ladder tiles, LEFT/RIGHT inputs must be ignored.
- **Zero Regressions:** The existing 1671 test suite must compile and pass after the implementation.

## Constraint Mapping
- **Input Constraints:** Players on stairs are restricted to Left/Right inputs. Players on ladders are restricted to Up/Down inputs.
- **Asset Constraints:** Must use the existing `01-stairs.png` and `01-stairs.tsx` files.
- **Parser Limitations:** The XML parser does not resolve default class properties for tilesets. The map manager lookup must handle fallbacks natively in Python.

## Architecture Direction
- **Diagonal Logical Navigation:** The logical coordinate positions change diagonally `(1, -1)` or `(-1, 1)` on the grid to match the diagonal zigzag placement of walkable tiles in Tiled.
- **Dynamic Step Alternation:** We will alternate flat and diagonal logical steps based on the `visual_y_offset` property. 
  - `stair_half = (visual_y_offset != 0)`
  - Climbing up: diagonal step happens when `stair_half` is true.
  - Descending down: diagonal step happens when `stair_half` is false.
- **Smooth Visual Y-Offset Interpolation:** Sprite visual Y offsets are calculated per frame in `BaseEntity.update(dt)` using a linear interpolation of the step progress:
  $$\text{progress} = 1.0 - \frac{\text{distance to target}}{\text{total step distance}}$$
  This visual offset keeps the sprite feet aligned with the shallow 26.5° staircase slope, preventing the character from floating/sinking.

## Exclusions & Boundaries
- **Depth Clipping:** The `stair_clip` / `clip` logic is excluded from this refactor. The code for RGBA-min surface composition and alpha clearing will be deleted.
- **Parser Revamps:** We will not modify `tmj_parser.py` to support tileset class property inheritance.

## Risk Assessment
- **Risk:** NPC pathfinding getting stuck or choosing incorrect routes due to diagonal stair tiles.
- **Mitigation:** Ensure `walkable_func` and boundary checks are called prior to launching any step, and align grid-unit movements cleanly.
