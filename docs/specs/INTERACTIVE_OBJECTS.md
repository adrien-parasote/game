# Technical Specification - Interactive Objects [Implementation]

This document defines the requirements for fixed interactive objects (chests, switches, etc.) in the RPG engine.

## 1. InteractiveEntity Class

### Data Structure (Tiled)
| Property | Type | Description |
|----------|------|-------------|
| `sub_type` | string | "chest", "sign", etc. |
| `sprite_sheet` | string | Filename in `assets/images/sprites/` |
| `direction` | string | "up", "right", "left", "right" |
| `depth` | int | Typically 1 (Y-sorted) |
| `start_frame` | int | Starting row of animation (default 0) |
| `end_frame` | int | Ending row of animation (default 3) |
| `width` | int | **Visual** frame width in pixels (for slicing) |
| `height` | int | **Visual** frame height in pixels (for slicing) |
| `tiled_width` | int | **Logical** hitbox width (from Tiled rect) |
| `tiled_height` | int | **Logical** hitbox height (from Tiled rect) |
| `passable` | bool | If `true`, the object does not block movement. (Default: `false`) |

### Animation Logic
- **Column Mapping** (User Specified): 
  - `up`: Column 0
  - `right`: Column 1
  - `left`: Column 2
  - `down`: Column 3
- **Behavior**: On interaction, iterate through frames (rows) from `start_frame` to `end_frame` of the selected column once. 
- **Doors (sub_type: door)**:
  - Doors support toggle behavior (Open/Close).
  - Open: Animate from `start_frame` to `end_frame`.
  - Close: Animate from `end_frame` back to `start_frame`.

## 2. Spatial Interaction & Physics

### Interaction Validation
Valid ONLY if both conditions are met:
1. **Proximity**: `Vector2(player.pos).distance_to(obj.pos) < 80.0`.
   - `obj.pos` is the "footprint center" (center of the bottom 32x32 area).
   - Increased to 80px to support natural interaction from adjacent tiles.
2. **Relative Orientation (Opposite Rule)**: 
   - Object `up` (opens from south) -> Player must be south (`y > obj_y`) and facing `up`.
   - Object `down` -> Player must be north (`y < obj_y`) and facing `down`.
   - Object `left` -> Player must be east (`x > obj_x`) and facing `left`.
   - Object `right` -> Player must be west (`x < obj_x`) and facing `right`.

**Relaxation (Doors)**:
If `sub_type == 'door'` and `is_open == True`, the door can be closed from the "opposite side" (e.g., closing a door from the north while facing `down`). This ensures players can easily close doors behind them.

### Collision & Barriers
Interactive objects can be solids or triggers based on their properties.
- **Passable Property**: If an object has `passable: true`, it is never added to the `obstacles_group`.
- **Solid Logic**: By default (`passable: false`), all interactive objects are added to the `obstacles_group` upon spawning and block player movement.
- **Doors (sub_type: door)**:
  - Doors ignore their initial `passable` setting for dynamic behavior.
  - Dynamically added to `obstacles_group` when in the `closed` state (frame `start_frame`).
  - Removed from `obstacles_group` when in the `open` state (frame `end_frame`).

### Rendering & Alignment
- **Y-Sort**: Sprites are sorted by their `rect.bottom`.
- **Alignment**: Sprites are centered horizontally on the Tiled rectangle and aligned by `rect.bottom`. This allows sprites taller than 32px to correctly occlude characters behind them while maintaining grid-aligned collision footprints.

## 3. Anti-Patterns (DO NOT)

| ❌ Don't | ✅ Do Instead | Why |
|----------|---------------|-----|
| Divide sheet by hardcoded values | Use pixel-based slicing (`load_grid_by_size`) | Supports variable object sizes |
| Add doors to map collision layer | Use `obstacles_group` | Allows dynamic passage |
| Pass center pos only | Pass Tiled top-left and dimensions | Ensures correct visual alignment |
| Hardcode door state | Use `is_open` and `is_closing` flags | Animation state machine consistency |
| Use `SPACE` for objects | Use `E` key (Unified) | UX differentiation for objects |
| Calculate distance every frame | Calculate only on key press | CPU optimization |

## 4. Test Case Specifications

| TC-I-01 | Proximity | Player at 70px away | Interaction Succeeds |
| TC-I-02 | Proximity | Player at 90px away | Interaction Fails |
| TC-I-07 | Alignment | Sprite 64x64 on Tiled 64x32 | `rect.bottom` aligns with Tiled bottom |
| TC-I-10 | Door Close | Player at North of open door | Close Succeeds (Relaxed Orientation) |

## 5. Error Handling Matrix

| Error Type | Detection | Response | Fallback |
|------------|-----------|----------|----------|
| Frame Mismatch| `sheet_h % height != 0` | Auto-recalculate `height` | `sheet_h / (end_row + 1)` |
| Sheet Layout | `cols != 4` | Detect `last_cols` | Use dynamic indexing |
| Interaction Spam| Timer check | Ignore input | cooldown of 0.5s |

## 6. Deep Links
- **Interactive Spawning**: [game.py - _spawn_entities](file:///Users/adrien.parasote/Documents/perso/game/src/engine/game.py)
- **Base Interaction**: [base.py - interact](file:///Users/adrien.parasote/Documents/perso/game/src/entities/base.py#L73)
- **Sprite Slicing**: [spritesheet.py - load_grid_by_size](file:///Users/adrien.parasote/Documents/perso/game/src/graphics/spritesheet.py)
- **Collision Check**: [game.py - _is_collidable](file:///Users/adrien.parasote/Documents/perso/game/src/engine/game.py)
