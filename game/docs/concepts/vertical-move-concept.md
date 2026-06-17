# Concept: Vertical-Move (Stairs & Ladders) Refactor

> One-sentence problem statement: Players and NPCs need a robust, bug-free vertical movement system (stairs and ladders) because the current implementation causes coordinate offsets, drift (asymmetry between climbing up and down), and unexpected movement behaviors.

## Problem
* The current stair-climbing logic suffers from a coordinate drift bug where moving up and down the stairs shifts the entity's Y-coordinate on the grid, misaligning them with the floor.
* The visual offset is applied instantly or awkwardly, causing sprites to clip into the walls or float above the staircase during traversal.
* Ladders need to be restricted to vertical inputs, but the current logic handles them poorly or identically to stairs.

## Direction
* **Vrai déplacement diagonal logique (Interpretation B):** The player will move diagonally on the logical grid for diagonal stairs, matching the physical layout of the staircases on the Tiled map.
* **Symmetric Step-Off Boundaries:** Verify if the target tile is a stair tile *before* applying the diagonal movement vector to ensure perfect coordinates upon entering and exiting stairs.
* **Smooth Offset Interpolation:** Smoothly interpolate the sprite's `visual_y_offset` based on movement progress between the source tile and target tile.
* **Slope Angle Matching (26.5° slope):** Moving strictly diagonally on a 32x32 grid creates a 45° angle, which makes the character float above the shallower 26.5° steps. We will alternate flat and diagonal steps dynamically by deriving `stair_half` from the tile's `visual_y_offset` property:
  * `stair_half = (visual_y_offset != 0)`
  * This preserves the shallow movement slope without requiring a dedicated `half` property in Tiled.

## Target User
* The Player and any NPCs navigating the game world.

## Success Looks Like
* Walking up and down stairs diagonally feels fluid and natural, with the sprite's feet staying aligned with the visual steps.
* Repeatedly climbing and descending the staircase leaves the character on the exact same starting tile (no Y coordinate drift).
* Ladders restrict movement to Up/Down inputs only.

## Scope Boundaries
What's IN:
* Characters inheriting from `BaseEntity` (Player, NPCs).
* Stair movement: horizontal/lateral diagonal stairs.
* Ladder movement: vertical climbing.
* Visual offset interpolation.

What's NOT (and why):
* Changing the map tileset assets — we must use the existing `01-stairs.png` and `01-stairs.tsx` files.
* Changing map parser to resolve Tiled classes (we will use hardcoded defaults instead).
* Sprite depth clipping (`stair_clip` / `clip` logic is excluded from this refactor per user feedback).

## Key Assumptions
* The stairs on the map are placed in a diagonal zigzag pattern (e.g. `(x, y) -> (x+1, y-1)`) matching Interpretation B. (Confirmed)
* Tiled class `01-vertical-move` properties will be retrieved via `MapManager.get_vertical_move_props()`. (Confirmed)
* `visual_y_offset` in the code acts as a screen space rendering displacement and doesn't affect collision hitboxes. (Confirmed)

## Open Questions for Strategy
* How should A* pathfinding for NPCs account for diagonal movement costs on stairs?
* How do we handle edge cases where NPCs or the Player are pushed or teleported while on stairs?
