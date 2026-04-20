# Technical Specification - Interactive Objects [Implementation]

This document defines the requirements for fixed interactive objects (chests, switches, etc.) in the RPG engine.

## 1. InteractiveEntity Class

### Data Structure (Tiled)
| `is_passable` | bool | If `true`, the object is traversable when ON or permanently if floor decor. |
| `is_animated` | bool | If `true`, the object loops its animation between `start_frame` and `end_frame` when ON. |
| `halo_size` | int | Radius of the light halo in pixels (default 0). |
| `halo_color` | string | Color of the halo in `[R, G, B]` format (text in TMJ). |
| `halo_alpha` | int | Maximum alpha (center) of the radial gradient (0-255). |
| `particles` | bool | If `true`, the object emits particles when ON. |
| `particle_count` | int | Maximum number of active particles simultaneously. |

### Animation Logic
- **Column Mapping**: 
  - The object property `position` (int, 0-3) determines the sprite-sheet column index directly (0-indexed).
  - Mapping: 0=Up, 1=Right, 2=Left, 3=Down.
  - The engine uses this index to slice the correct vertical strip from the spritesheet.
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
   - This ensures interaction works correctly regardless of the sprite's visual height or offsets.
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
  - A high-quality radial gradient surface is generated using a pixel-by-pixel radius loop (`range(radius, 0, -1)`).
  - **Additive Technique**: The surface is NOT `SRCALPHA` (transparent). Instead, it uses a **Black background** (`[0, 0, 0]`) and the gradient is created by modulating the RGB intensity (`color = base_color * intensity`). This ensures `pygame.BLEND_RGB_ADD` works correctly and smoothly on all platforms.
  - **Falloff**: Uses a quadratic falloff (`(1.0 - ratio) ** 2`) for a natural-looking glow.
  - **Visual Centering**: The halo is centered on the visual middle of the entity (`rect.center`). This is distinct from the logical `pos` (footprint center), ensuring light appears correctly on tall objects.
  - To optimize rendering, a **Scaling Cache** of 10 variations (0.97 to 1.03 scale) is pre-generated at startup to avoid per-frame `pygame.transform.scale` operations.
- **Organic Flicker (Animation-Driven)**:
  - **Applicability**: This specialized logic applies to light-source entities. An entity is considered a light source if its `sub_type` is in `['lamp', 'lantern', 'torch', 'fire', 'candle']` OR if it has a `halo_size > 0`. Traditional animated objects like `chest` or `door` retain their standard animation speed (10.0 FPS).
  - **Synchronization**: For light sources, flicker modulation (`f_alpha`, `f_scale`) is derived directly from `frame_index`. This ensures the halo is brightest when the fire sprite is at its peak frame.
  - **Real-Life Timeline**: Light source animation speed is reduced to follow a "real-life flame" rhythm. Target speed is **1.5 FPS**, providing a very slow, atmospheric breathing effect.
  - **Desynchronization**: To prevent multiple light sources from pulsing in unison, each light source starts at a random `frame_index` offset within its animation loop.
- **Adaptive Intensity**:
  - Halo intensity scales with `global_darkness` (provided by the engine), normalized against `180` (MAX_NIGHT_ALPHA) to ensure peak brightness at midnight aligns with `halo_alpha`.
  - **Luminosity Floor**: Minimum 15% intensity is maintained even in full daylight if `is_on` is True.
- **Bio-Inspired Flicker**:
  - **Frequency**: ~2Hz (sinusoidal).
  - **Modulation**: ±12% on intensity (alpha), ±3% on size (scale).
  - **Phase**: Each object uses a unique random phase offset to prevent synchronized "breathing" between multiple instances.
- **Rendering**:
  - Drawn onto the main surface in the `draw_effects` method.
  - Method: `BLEND_RGB_ADD` on top of the final rendered frame.

### 2.4. Particle System
If `particles` is true, the object acts as a lightweight particle emitter when `is_on` is True.

- **Initialization & Cycle**:
  - Max particles bounded by `particle_count` (int). 
  - **Spawning**:
    - `x`: `centerx ± 4px` (Concentrated in the middle).
    - `y`: `top + (height * 0.33) ± 2px` (Upper third of the object).
  - **Physics**:
    - Velocity Y: Negative (drifting slowly upwards).
    - Velocity X: Slight sinusoidal oscillation (`math.sin(phase + life * 3.0) * 5.0`).
- **Rendering**:
  - **Data Structure**: Use simple lists of dicts (e.g. `[x, y, vx, vy, life, max_life, size, phase]`).
  - **Drawing**: `pygame.draw.circle` with a radius of `1px` (90%) or `2px` (10%).
  - **Fading**: `alpha = (life / max_life) ** 0.6`. Multiply RGB by alpha using `BLEND_RGB_ADD` for vibrant luminosity.


## 3. Anti-Patterns (DO NOT)

| ❌ Don't | ✅ Do Instead | Why |
|----------|---------------|-----|
| Divide sheet by hardcoded values | Use pixel-based slicing (`load_grid_by_size`) | Supports variable object sizes |
| Add doors to map collision layer | Use `obstacles_group` | Allows dynamic passage |
| Pass center pos only | Pass Tiled top-left and dimensions | Ensures correct visual alignment |
| Hardcode door state | Use `is_on` and `is_closing` flags | Animation state machine consistency |
| Use `SPACE` for objects | Use `E` key (Unified) | UX differentiation for objects |
| Calculate distance every frame | Calculate only on key press | CPU optimization |
| Scale surfaces in `update` | Pre-calculate a scaling cache in `__init__` | `pygame.transform.scale` causes severe frame drops when called per-frame on multiple objects |
| Mega `__init__` methods | Refactor into private helper methods (`_parse_properties`, `_setup_physics`) | Ensure compliance with the 50-line maximum per method rule |
| Use Pygame Sprites for particles | Use simple lists of dicts | Sprite allocation overhead causes GC lag when managing hundreds of short-lived particles |

## ✅ Patterns to Reproduce

| Pattern | Description | Why |
|---------|-------------|-----|
| **Footprint Centering** | Define interaction `obj.pos` as footprint center, not sprite center. | Supports tall/offset visual assets while keeping grid-consistent logic. |
| **Boundary Value Specification** | Define procedural textures by boundary values (e.g. Center Alpha -> Edge Alpha). | Eliminates ambiguity in generation loops. |
| **ADD Blend Post-Overlay** | Apply additive light halos AFTER the night darkness overlay. | Ensures light sources actively cut through the dark rather than being dimmed by it. |
| **Pre-calculated Scaling Cache** | Pre-generate discrete scaled variants of complex surfaces during startup. | Replaces continuous runtime mathematical operations (which freeze pygame) with discrete memory lookups (which are instant). |

## 4. Test Case Specifications

### Unit Tests Required
| Test ID | Component | Input | Expected Output | Edge Cases |
|---------|-----------|-------|-----------------|------------|
| TC-U-01 | State Toggle | Call `interact()` on OFF object | Sets `is_on` to True, `is_animating` to True | Object is `is_animated=True` |
| TC-U-02 | Animation Step | `update(dt)` when `is_animating=True` | `frame_index` increments based on speed and `dt` | Time step > animation duration |
| TC-U-03 | Animation Loop | `update(dt)` past `end_frame` for looping obj | `frame_index` resets to `start_frame` | High frame rate |
| TC-U-04 | Animation Reverse | `update(dt)` when closing door | `frame_index` decrements towards `start_row` | None |
| TC-U-05 | Pre-calculated Cache | `halo_size=50` | `light_mask_cache` has exactly 10 surfaces (0.97 to 1.03) | `halo_size=0` |
| TC-U-06 | Particle Spawn | `update(dt)` with `particles=True` & `is_on=True` | Active particles list is populated up to `particle_count` | dt=0 |
| TC-U-07 | Particle Cleanup| particle life expires | Removed from active particles list | Empty list |

### Integration Tests Required
| Test ID | Flow | Setup | Verification | Teardown |
|---------|------|-------|--------------|----------|
| TC-I-01 | Proximity Validation | Spawn player at `dir=(0,1)`, object at distance 40px | Press E triggers state change | None |
| TC-I-02 | Proximity Rejection | Spawn player at `dir=(0,1)`, object at distance 50px | Press E does NOT trigger state change | None |
| TC-I-03 | Orientation Validation | Open door from 'wrong' side (Relaxed rule) | Valid orientation identified, state toggles to close | None |

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
