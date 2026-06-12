> **Note**: This document was originally written in French and translated to English on 2026-06-12.

> **Status: MERGED** — Key findings incorporated into stair-movement.md (Addendum section). This document is preserved for historical context.

# Analysis: Stair Mechanics Bug

## 1. Root Cause (Code)
The issue of abrupt jumps ("goes up in the middle", "too high") comes from a **bug in `game/src/map/manager.py`**.
At line 339, the function `get_vertical_move_props` contains:
```python
"visual_y_offset": int(props.get("visual_y_offset", 0)),
```
This line completely overwrites the fallback offset calculation (which alternates between 0 and -16) and forces the offset to 0 for all tiles that do not have the property explicitly set in Tiled.
As a consequence, the character does not "slide" upward on the first half of the staircase, and then suffers an abrupt 32-pixel jump at the moment of diagonal movement.

## 2. Root Cause (Tiled)
The `_apply_stair_interception` system and `VERTICAL_MOVE_MAP` in `base.py` **require** that stairs be drawn physically in a zigzag pattern (steps drawn diagonally on the Tiled grid) and not as a horizontal block.

When the player moves right on a staircase ascending to the right:
1. On a `stair_half = False` tile: the player moves horizontally `(1, 0)`.
2. On a `stair_half = True` tile: the player moves diagonally `(1, -1)` (changes physical Y row in the map).

If the staircase is drawn as a straight block or a large horizontal line (`(x,y)`, `(x+1, y)`, `(x+2, y)`), the second movement (which is diagonal `(1, -1)`) will **physically move** the character off the staircase row (hence "does not follow the bottom line" or the fact that it moves straight ahead if it falls back onto a tile with no stair property).

## 3. How to Fix

**In the code (`game/src/map/manager.py`):**
Replace the dictionary key in the return value:
```python
# Replace (line 339):
"visual_y_offset": int(props.get("visual_y_offset", 0)),
# With:
"visual_y_offset": visual_y_offset,
```

**In Tiled:**
For a straight staircase to work smoothly, its tiles must be placed on the map in a zigzag pattern:
* Position `(x, y)`: Step start tile (offset `0`, `stair_half = False`). Resulting movement: `(1, 0)`.
* Position `(x+1, y)`: Step end tile (offset `-16`, `stair_half = True`). Resulting movement: `(1, -1)`.
* Position `(x+2, y-1)`: Start of next step (offset `0`, `stair_half = False`). Resulting movement: `(1, 0)`.
* Position `(x+3, y-1)`: End of next step (offset `-16`, `stair_half = True`). Resulting movement: `(1, -1)`.

*Note: These properties were applied in `01-stairs.tsx` for each 2x3 and single block.*

## 4. Ascent/Descent Asymmetry (Fixed)

A second major bug affected the movement direction (descent). The logic dictating whether the player should move diagonally was strictly fixed to `should_move_diagonally = stair_half`.

* On **ascent**, this works (the second half of the step = diagonal).
* On **descent**, this caused an incorrect zigzag, because the step must be descended on its **first** half (which physically corresponds to the same `stair_half=False` tile).

**Fix applied in `base.py`:**
The algorithm now checks the direction:
- **Ascending:** `should_move_diagonally = stair_half`
- **Descending:** `should_move_diagonally = not stair_half`

*(Unit tests in `test_stair_movement.py` were also corrected to reflect this physical symmetry.)*
