# Research: Diagonal Stair Movement in 2D Tile-Based Games

## 1. Domain Context
**Question:** How is elevation and stair movement traditionally conceptualized in 2D grid-based engines?
- **Concept:** 2D top-down or 3/4 perspective games lack a true Z-axis. Elevation is simulated visually via Y-axis displacement.
- **Side Stairs:** When stairs are drawn horizontally (from left to right going up), a purely horizontal movement (X-axis) breaks the illusion, as the player character floats off the steps. The movement must follow the diagonal visual slope of the staircase (X and Y simultaneously).
- **UX Standard:** The player expects to only press "Right" or "Left" to navigate horizontal stairs, while the engine automatically handles the vertical displacement to keep them on the steps.

## 2. Competitive Landscape
**Question:** How do other engines and games solve this problem?
- **RPG Maker (Vanilla):** Relies on "Eventing". Developers place an invisible event on the first stair tile. When the player touches it, it forces a predefined movement route (e.g., "Move Right, Move Up, Move Right, Move Up") and disables normal input. [Source: RPG Maker Web Forums]
- **RPG Maker (Plugins):** Plugins like `TSR_SideStairs` or `Galv's Diagonal Movement` use Region IDs or Terrain Tags in the map editor. If a tile is marked as a "Stair" with a specific direction, the plugin intercepts horizontal input and converts it into diagonal movement automatically.
- **Pokémon (Gen 3 & 4):** Side stairs use specific tile metadata. When traversing them, pressing Left or Right causes the character to move diagonally. The engine automatically locks vertical input (Up/Down) while on the staircase to prevent breaking the path.

## 3. Technical Feasibility (Our Engine)
**Question:** Can we build this in our custom Pygame engine, and how?
- **Tiled Data Injection:** We can add custom properties to the stair tiles in `01-stairs.tsx`. For example, `stair_type: "up_right"`. I can see from `01-stairs.tsx` that the user has already added a class `00-tileset` with `direction="right"` or `"left"` to the stair tiles.
- **Engine Capabilities:** 
  - `BaseEntity.start_move()` computes `self.target_pos = self.pos + self.direction * Settings.TILE_SIZE`. 
  - `MapManager` can be queried to read the `direction` or `stair` property of the current tile.
- **Implementation Strategy:**
  1. In `BaseEntity.start_move()`, check if the current tile has a stair property.
  2. If the tile is `stair_type="up_right"` and the entity's `self.direction` is `(1, 0)` (Right), mutate the direction to `(1, -1)` (Right + Up). If `self.direction` is `(-1, 0)` (Left), mutate to `(-1, 1)` (Left + Down).
  3. The existing `self.move(dt)` uses vector normalization and moves towards `target_pos`. This inherently supports moving to a diagonal tile `(x+32, y-32)`.
  4. Block vertical input (Up/Down) while on these specific stairs to avoid sequence breaking.

## 4. Cross-Axis Synthesis
1. **Data-Driven > Event-Driven:** Just like modern RPG Maker plugins, intercepting movement via Tiled metadata (`direction="right"`) is vastly superior and more scalable than placing "Forced Move Route" events on every stair. Our `MapManager` already supports property extraction, making this adaptation straightforward.
2. **UX to Math Conversion:** The player's mental model (Market standard: "I press right to go up the stairs") conflicts with grid math ("I need to move up and right"). By intercepting the direction vector in `BaseEntity.start_move()`, we seamlessly bridge this gap. The player presses Right, the engine executes Diagonal, preserving the UX while utilizing the engine's existing vector movement logic.

## 5. Decision
**Build/Adapt:** We will **Adapt** the Tiled properties and **Build** the interceptor logic in `BaseEntity.start_move()`. 
- **Tiled:** Standardize the property (e.g., `stair="right"` meaning it ascends to the right).
- **Code:** Read this property in `start_move()` and modify `self.direction` before calculating `target_pos`.

---

## Addendum: Descent Asymmetry Fix (2026-06-11)

> Source: stair_mechanics_analysis.md (originally French, translated 2026-06-12)

### Root Cause

After initial implementation, a second bug was identified affecting descent movement. The logic for determining whether the player should move diagonally was set to `should_move_diagonally = stair_half` unconditionally, which only works correctly for **ascent**.

**On ascent:** The upper-half tile (`stair_half=True`) is where diagonal movement must occur to reach the next Y level — correct.

**On descent:** The lower-half tile (`stair_half=False`) is where diagonal movement must occur to descend to the next Y level — incorrect with the original formula. This caused a zigzag misalignment during descent.

### Fix

The algorithm now checks the movement direction:
- **Ascending** (`intercepted_dir[1] < 0`): `should_move_diagonally = stair_half`
- **Descending** (`intercepted_dir[1] > 0`): `should_move_diagonally = not stair_half`

In code (`base.py` line 115):
```python
should_move_diagonally = stair_half if is_going_up else (not stair_half)
```

Unit tests in `test_stair_movement.py` were updated to reflect this physical symmetry. The fix is documented in ADR-013.

