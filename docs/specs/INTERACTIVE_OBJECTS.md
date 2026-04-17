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

### Animation Logic
- **Column Mapping** (User Specified): 
  - `up`: Column 0
  - `right`: Column 1
  - `left`: Column 2
  - `down`: Column 3
- **Behavior**: On interaction, iterate through frames (rows) from `start_frame` to `end_frame` of the selected column once. The final frame remains displayed (handled by `is_open` state).

## 2. Spatial Interaction Validation

Interaction is valid ONLY if both conditions are met:
1. **Proximity**: `Vector2(player.pos).distance_to(object.pos) < 45.0`.
2. **Relative Orientation (Opposite Rule)**: 
   - Object `up` (opens from south) -> Player must be at `y > object.y` and facing `up`.
   - Object `down` -> Player must be at `y < object.y` and facing `down`.
   - Object `left` -> Player must be at `x > object.x` and facing `left`.
   - Object `right` -> Player must be at `x < object.x` and facing `right`.

### Collision
Interactive objects are **solid**. They are included in the `interactives` group and checked during `_is_collidable` calls in `Game`. The player cannot move into a tile occupied by an interactive object.

## 3. Anti-Patterns (DO NOT)

| ❌ Don't | ✅ Do Instead | Why |
|----------|---------------|-----|
| Use `SPACE` for objects | Use `E` key | UX differentiation requested |
| Hardcode sprite indices | Use dict mapping | Maintainability |
| Project a tile ahead (NPC style) | Use proximity check | Better feel for non-grid-aligned interactions |
| Animate in `update()` loop | Use state-triggered animation | Performance and logic clarity |
| Calculate distance every frame | Calculate only on key press | CPU optimization |

## 4. Test Case Specifications

| ID | Component | Input | Expected Output |
|----|-----------|-------|-----------------|
| TC-I-01 | Proximity | Distance 40px | Success |
| TC-I-02 | Proximity | Distance 50px | Failure |
| TC-I-03 | Orientation | Chest "up", Player facing "up" at South | Success |
| TC-I-04 | Orientation | Chest "up", Player facing "up" at North | Failure |
| TC-I-05 | Animation | Trigger Chest "right" | Column 1 animates row 0-3 |

## 5. Error Handling Matrix

| Error Type | Detection | Response | Fallback |
|------------|-----------|----------|----------|
| Missing Sheet | `FileNotFoundError` | Log Error | Show dummy red box |
| Invalid Dir | `ValueError` | Log Warning | Default to `down` (Col 3) |
| Interaction Spam| Timer check | Ignore input | cooldown of 0.5s |

## 6. Deep Links
- **Interactive Spawning**: [game.py - _spawn_entities](file:///Users/adrien.parasote/Documents/perso/game/src/engine/game.py)
- **Base Interaction**: [base.py - interact](file:///Users/adrien.parasote/Documents/perso/game/src/entities/base.py#L73)
- **Sprite Grids**: [spritesheet.py - load_grid](file:///Users/adrien.parasote/Documents/perso/game/src/graphics/spritesheet.py#L18)
- **Collision Check**: [game.py - _is_collidable](file:///Users/adrien.parasote/Documents/perso/game/src/engine/game.py)
