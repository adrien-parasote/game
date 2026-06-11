# Research: Stair Climbing Positioning & Alignment Bugs

> Document Type: Research
> Stage: 🔬 DISCOVER
> Target Component: Stair Movement & Camera Rendering

---

## 1. Domain Context & Competitive Landscape

### 1.1 Grid-Based Stair Traversal
In 2D grid-based tile engines (e.g., classic Pokémon, RPG Maker, Chrono Trigger), handling staircases presents a classic coordination problem between the **logical collision grid** and the **visual presentation**:
1. **Vertical/Orthogonal Stairs**: Traversed by moving vertically (`UP`/`DOWN`). These typically require no diagonal logic but may require depth changes.
2. **Lateral/Diagonal Stairs**: Traversed by moving horizontally (`LEFT`/`RIGHT`), where the character moves diagonally (both horizontally and vertically) on the screen.

### 1.2 The Visual/Logical Gap
Because grid tiles are discrete squares (typically 32x32 pixels), a diagonal move changes the character's logical position by 1 tile vertically (32 pixels). However:
- A stair step is visually drawn as rising by a fraction of a tile (e.g., 12 pixels).
- To prevent the character from floating or sinking, the engine must apply a visual rendering offset (`visual_y_offset`) to align the sprite's feet with the drawn step.
- As the player climbs multiple steps, this offset must compensate for the difference between the accumulated logical grid height (32 pixels per step) and the visual staircase height (12 pixels per step).

---

## 2. Technical Feasibility & Root Cause Analysis

We investigated the stair movement bugs reported by the user on the bottom-right staircase of the basement map (`castel/interior/01-basement.tmj`):

### 2.1 The Map Stair Layout (Verified via scan)
The stairs on the right of the basement consist of 3 columns (`x = 35..37`) spanning `y = 31..34`:
- **Bottom Steps**: `(35, 34)`, `(36, 34)`, `(37, 33)` (all marked as `stair_direction: "right"`).
- **Ledge/Walls**: `(37, 34)` is a wall (`walkable: false`). Ledge is at `y = 31`.
- **Traversal**: The player starts on the floor (`y = 34`) and climbs UP-RIGHT by moving RIGHT, or descends DOWN-LEFT by moving LEFT.

---

### 2.2 Root Cause 1: Asymmetric Step-Off causing Y-Drift ("trop en décalage")
Currently, the movement direction is intercepted into a diagonal vector whenever the player starts on a stair tile:
- **On Step-On (UP)**: The player starts on a floor tile `(34, 34)`. Since this is a floor tile, they move **orthogonally** (flat) to `(35, 34)`. Y changes by `0`.
- **On Step-Off (DOWN)**: The player is on the bottom step `(35, 34)` (which is a stair tile). They press LEFT to step off. Because they start on a stair tile, the engine intercepts the move to diagonal `(-1, 1)` (left-down), landing them at `(34, 35)`. Y changes by `+1`.

**Consequence:** The path is asymmetric. Climbing up and then down shifts the player's Y coordinate down by 1 tile (32 pixels), leaving them misaligned on the floor.

---

### 2.3 Root Cause 2: Start-of-Step Offset Evaluation ("dans le mur" and "trop haut/milieu")
The visual rendering offset `visual_y_offset` is only updated once in `BaseEntity.start_move()` at the beginning of a step:
1. **First Step**: Player moves from floor `(34, 34)` (offset 0) to step 1 `(35, 34)`. The step starts on floor, so offset is `0` throughout the movement and when standing still. But step 1 is visually raised. Result: Player is rendered too low (inside the wall).
2. **Second Step**: Player moves from step 1 `(35, 34)` (stair) to step 2 `(36, 33)`. Offset becomes `-12` immediately. Logical Y changes from `34` to `33` (-32px). Rendered Y is `Y_logical - 12` which is `Y_start - 44`. But step 2 should be at `Y_start - 24`. Result: Player looks too high.
3. **Third Step**: Rendered Y is `Y_start - 76` instead of `Y_start - 36`. Result: Player looks much too high.

---

## 3. Proposed Solution (Adopt/Adapt/Build-New: Adapt)

We will **adapt** the existing `BaseEntity` movement interception and rendering offset logic to handle transition boundaries correctly.

### 3.1 The Stair Step-Off Rule (Exit Interception)
In `BaseEntity.start_move()`, check if the flat target tile in the input direction is a stair tile:
- If yes: apply diagonal interception (keep climbing/descending).
- If no: do **not** apply diagonal interception (exit stairs orthogonally).

This restores perfect symmetry: the player enters orthogonally and exits orthogonally, keeping Y aligned.

### 3.2 Visual Offset Interpolation
To prevent visual snaps and positioning bugs:
1. Initialize `self.current_stair_offset = 0` in `BaseEntity.__init__`.
2. At the start of a move, cache the starting offset `self.stair_start_offset`, query the target tile's visual offset `self.stair_target_offset`, and record `self.stair_move_distance`.
3. In `BaseEntity.update(dt)`, interpolate `self.current_stair_offset` smoothly based on the movement progress:
   $$\text{progress} = 1.0 - \frac{\text{distance to target}}{\text{total step distance}}$$
4. Update `CameraGroup.custom_draw` to use `sprite.current_stair_offset` instead of the static `_vertical_move["visual_y_offset"]`.

### 3.3 Proof of Concept (POC) Verification
We created a headless Python simulation (`simulate_climb_new.py`) matching the game engine and basement map. The simulation verified:
- **Upward Climb Y Rendered**: Smoothly transitions through `1088.0` (floor) $\rightarrow$ `1076.0` (Step 1) $\rightarrow$ `1044.0` (Step 2) $\rightarrow$ `1012.0` (Step 3).
- **Downward Descent Y Logicals**: The player returns to the exact starting coordinates `(34, 34)` at Y coordinate `1104.0` with offset `0.0`.

---

## 4. Discovery Exit Checklist

- [x] Decomposed topic and researched technical feasibility.
- [x] Identified root causes (fencepost transition asymmetry + start-only offset mapping).
- [x] Verified proposed solution using Python headless simulation.
- [x] Produced research artifact under `docs/research/stair_climbing.md`.
