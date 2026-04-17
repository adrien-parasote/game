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
| `width` | int | Frame width in pixels (default 32) |
| `height` | int | Frame height in pixels (default 32) |

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
1. **Proximity**: `Vector2(player.pos).distance_to(footprint_center) < 45.0`.
   - `footprint_center` is the center of the bottom 32x32 area of the object.
2. **Relative Orientation (Opposite Rule)**: 
   - Object `up` (opens from south) -> Player must be at `y > object.rect.bottom - 16` and facing `up`.
   - Object `down` -> Player must be at `y < object.rect.bottom - 16` and facing `down`.
   - Object `left` -> Player must be at `x > object.rect.centerx` and facing `left`.
   - Object `right` -> Player must be at `x < object.rect.centerx` and facing `right`.

### Collision & Barriers
Interactive objects can be solids or triggers.
- **Chests/Fixed Objects**: Included in `interactives` group; checked via `_is_collidable`.
- **Doors**:
  - Dynamically added to `obstacles_group` when in the `closed` state (frame `start_frame`).
  - Removed from `obstacles_group` when in the `open` state (frame `end_frame`).
  - Allows passage ONLY when fully open.

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

| ID | Component | Input | Expected Output |
|----|-----------|-------|-----------------|
| TC-I-06 | Sizing | Door 32x64 | Sprite sliced 32x64 |
| TC-I-07 | Alignment | Door at (100,100) H:64 | `rect.bottom` == 164 |
| TC-I-08 | Door Collision| Open door | `obstacles_group`.remove(door) |
| TC-I-09 | Door Collision| Close door | `obstacles_group`.add(door) |

## 5. Error Handling Matrix

| Error Type | Detection | Response | Fallback |
|------------|-----------|----------|----------|
| Invalid Size | `width % sheet_w != 0` | Log Warning | Default to 32x32 |
| Group Missing | `obstacles_group is None`| Log Error | Object remains non-solid |
| Interaction Spam| Timer check | Ignore input | cooldown of 0.5s |

## 6. Deep Links
- **Interactive Spawning**: [game.py - _spawn_entities](file:///Users/adrien.parasote/Documents/perso/game/src/engine/game.py)
- **Base Interaction**: [base.py - interact](file:///Users/adrien.parasote/Documents/perso/game/src/entities/base.py#L73)
- **Sprite Slicing**: [spritesheet.py - load_grid_by_size](file:///Users/adrien.parasote/Documents/perso/game/src/graphics/spritesheet.py)
- **Collision Check**: [game.py - _is_collidable](file:///Users/adrien.parasote/Documents/perso/game/src/engine/game.py)
