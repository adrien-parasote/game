# Technical Specification - Interactive Objects [Implementation]

This document defines the requirements for fixed interactive objects (chests, switches, etc.) in the RPG engine.

## 1. InteractiveEntity Class

### Data Structure (Tiled)
| `is_passable` | bool | If `true`, the object is traversable when ON or permanently if floor decor. |
| `is_animated` | bool | If `true`, the object loops its animation between `start_frame` and `end_frame` when ON. |
| `halo_size` | int | Radius of the light halo in pixels (default 0). |
| `halo_color` | string | Color of the halo in `[R, G, B]` format (text in TMJ). |
| `halo_alpha` | int | Maximum alpha (center) of the radial gradient (0-255). |

### Animation Logic
- **Column Mapping** (User Specified): 
  - `up`: Column 0
  - `right`: Column 1
  - `left`: Column 2
  - `down`: Column 3
- **Behavior**: On interaction, state toggles between ON and OFF. Default state is OFF, unless `is_animated` is true, or `sub_type` is a light source (`lamp`, `lantern`, `torch`, `fire`), in which case the default state is ON.
- **Animation (Linear)**: If `is_animated == false`, animation plays once from `start_frame` to `end_frame` (Toggle ON).
- **Animation (Looping)**: If `is_animated == true`, animation loops between `start_frame` and `end_frame` continuously while the state is ON.
- **Doors (sub_type: door)**:
  - Doors support toggle behavior.
  - Open (ON): Animate from `start_frame` to `end_frame`.
  - Close (OFF): Animate from `end_frame` back to `start_frame`.

## 2. Spatial Interaction & Physics

### Interaction Validation
Valid ONLY if both conditions are met:
1. **Proximity**: `Vector2(player.pos).distance_to(obj.pos) < 45.0`.
   - `obj.pos` is the "footprint center" (center of the bottom 32x32 area).
   - Constrained to 45px for tight interaction requirements.
2. **Relative Orientation (Opposite Rule)**: 
   - Object `up` (opens from south) -> Player must be south (`y > obj_y`) and facing `up`.
   - Object `down` -> Player must be north (`y < obj_y`) and facing `down`.
   - Object `left` -> Player must be east (`x > obj_x`) and facing `left`.
   - Object `right` -> Player must be west (`x < obj_x`) and facing `right`.

**Relaxation (Doors)**:
If `sub_type == 'door'` and `is_on == True`, the door can be closed from the "opposite side" (e.g., closing a door from the north while facing `down`). This ensures players can easily close doors behind them.

### 2.1. Rendering & Alignment
- **Y-Sort**: Sprites are sorted by their `rect.bottom`. All `interactive_objects` use depth 1.
- **Alignment**: Sprites are centered horizontally on the Tiled rectangle and aligned by `rect.bottom`.

### 2.2. Collision & Barriers

The `is_passable` property controls **open-state traversability**, not initial collision state.

| Scenario | `is_passable` | Spawn (closed/OFF) | When ON |
|----------|-----------|----------------|-----------|
| Standard chest | `false` | Solid (in obstacles) | Solid |
| Traversable door | `true` | Solid (in obstacles) | Traversable (removed from obstacles) |
| Floor decor | `true` | Traversable (not in obstacles) | Traversable |

**Rules:**
- **Doors (`sub_type: door`)**: Always added to `obstacles_group` at spawn, regardless of `is_passable`. This ensures all doors start closed and blocking.
  - On `open` (animation reaches `end_frame`): removed from `obstacles_group` **only if** `is_passable: true`.
  - On `close` (animation returns to `start_frame`): **always** re-added to `obstacles_group`.
- **Non-door objects**: Added to `obstacles_group` at spawn **only if** `is_passable: false`.

### 2.3. Dynamic Lighting (Halos)
If `halo_size > 0`, a dynamic radial gradient halo is generated and rendered.

- **Initialization**:
  - `halo_color` is parsed from string (e.g., `"[255, 204, 0]"`) into an RGB tuple.
  - A high-quality radial gradient surface is generated once (Center: `halo_alpha`, Edge: 0).
- **Adaptive Intensity**:
  - Halo intensity scales with `global_darkness` (provided by the engine), normalized against `180` (MAX_NIGHT_ALPHA) to ensure peak brightness at midnight aligns with `halo_alpha`.
  - **Luminosity Floor**: Minimum 15% intensity is maintained even in full daylight if `is_on` is True.
- **Bio-Inspired Flicker**:
  - **Frequency**: ~2Hz (sinusoidal).
  - **Modulation**: ±12% on intensity (alpha), ±3% on size (scale).
  - **Phase**: Each object uses a unique random phase offset to prevent synchronized "breathing" between multiple instances.
- **Rendering**:
  - Drawn at the **footprint center** (horizontal center, 16px above the Tiled rectangle bottom).
  - Method: `BLEND_RGB_ADD` on top of the dark night overlay.

## 3. Anti-Patterns (DO NOT)

| ❌ Don't | ✅ Do Instead | Why |
|----------|---------------|-----|
| Divide sheet by hardcoded values | Use pixel-based slicing (`load_grid_by_size`) | Supports variable object sizes |
| Add doors to map collision layer | Use `obstacles_group` | Allows dynamic passage |
| Pass center pos only | Pass Tiled top-left and dimensions | Ensures correct visual alignment |
| Hardcode door state | Use `is_on` and `is_closing` flags | Animation state machine consistency |
| Use `SPACE` for objects | Use `E` key (Unified) | UX differentiation for objects |
| Calculate distance every frame | Calculate only on key press | CPU optimization |

## ✅ Patterns to Reproduce

| Pattern | Description | Why |
|---------|-------------|-----|
| **Footprint Centering** | Define interaction `obj.pos` as footprint center, not sprite center. | Supports tall/offset visual assets while keeping grid-consistent logic. |
| **Boundary Value Specification** | Define procedural textures by boundary values (e.g. Center Alpha -> Edge Alpha). | Eliminates ambiguity in generation loops. |
| **ADD Blend Post-Overlay** | Apply additive light halos AFTER the night darkness overlay. | Ensures light sources actively cut through the dark rather than being dimmed by it. |

## 4. Test Case Specifications

| TC-I-01 | Proximity | Player at 40px away | Interaction Succeeds |
| TC-I-02 | Proximity | Player at 50px away | Interaction Fails |
| TC-I-11 | Animation | `is_animated=True` | Loops back from `end_frame` to `start_frame` |
| TC-I-12 | Halo | `halo_size > 0` | Surface generated with radial alpha gradient |
| TC-I-07 | Alignment | Sprite 64x64 on Tiled 64x32 | `rect.bottom` aligns with Tiled bottom |
| TC-I-08 | Door Close | Player at North of open door | Close Succeeds (Relaxed Orientation) |
| TC-I-09 | Animation | Logic reverse on close | `frame_index` decreases back to start |
| TC-I-10 | Coverage | Full Module Scan | 100% unit test coverage achieved |

## 5. Error Handling Matrix

| Error Type | Detection | Response | Fallback |
|------------|-----------|----------|----------|
| Frame Mismatch| `sheet_h % height != 0` | Auto-recalculate `height` | `sheet_h / (end_row + 1)` |
| Sheet Layout | `cols != 4` | Detect `last_cols` | Use dynamic indexing |
| Interaction Spam| Timer check | Ignore input | cooldown of 0.5s |

## 6. Deep Links
- **Interactive Spawning**: [game.py - _spawn_entities](src/engine/game.py#L91)
- **Base Interaction**: [base.py - interact](src/entities/base.py#L73)
- **Sprite Slicing**: [spritesheet.py - load_grid_by_size](src/graphics/spritesheet.py)
- **Collision Check**: [game.py - _is_collidable](src/engine/game.py#L126)
