# Technical Specification - Interactive Objects [Implementation]

> Document Type: Implementation


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
| `element_id` | string | Unique identifier for communication and dialogue. Falls back to the raw Tiled object `id` (e.g. "61") if absent. |
| `target_id` | string | Holds the `element_id` of the object that this entity should activate or interact with. |
| `facing_direction` | string | Optional. Overrides the `position`-based `direction_str`. Useful for signs. |
| `is_on` | bool | The initial state of the object. Persisted in `WorldState` using `{map}-{element_id}` as key. |
| `sfx` | string | Optional. Name of the `.ogg` file in `assets/audio/sfx/` to play on interaction. |
| `sfx_ambient` | string | Optional. Name of the looping `.ogg` file in `assets/audio/sfx/` to play while `is_on` is True. |
| `off_position` | int | Column index for OFF state (`-1` = no switch, backward-compat default). When ≥ 0, `interact()` switches `col_index` between `on_position` (col 0) and `off_position`. Used by `animated_decor` (e.g. torch ON col 0 / OFF col 1). |
| `contents` | list[Item] | Dynamically populated list of `Item` objects (for chests), loaded from `LootTable`. |

### Animation Logic
- **Column Mapping**: 
  - The object property `position` (int, 0-3) determines the sprite-sheet column index directly (0-indexed).
  - Mapping: `0=Down, 1=Left, 2=Right, 3=Up` (matches `InteractiveEntity.POSITION_TO_DIR` in code).
  - The engine uses this index to slice the correct vertical strip from the spritesheet.
- **`off_position` Column Switch** (for `animated_decor`):
  - If `off_position == -1` (default): single-column spritesheet, no switch on toggle (backward compat).
  - If `off_position >= 0`: spritesheet has ≥2 columns. `interact()` calls `_update_col_index()` — `col_index = on_position` (0) when `is_on=True`, `col_index = off_position` when `is_on=False`.
  - `restore_state({'is_on': bool})` also calls `_update_col_index()` to restore visual state across map reloads.
  - **Tiled setup**: Set `off_position=1` on the tileset custom property of the `animated_decor` object; ensure spritesheet has col 0 = ON animation, col 1 = OFF animation.
- **Behavior**: On interaction, state toggles between ON and OFF. Default state is OFF, unless `is_animated` is true, or `sub_type` is a light source (`lamp`, `lantern`, `torch`, `fire`), in which case the default state is ON.
  - **Initialization**: If `is_on` is explicitly set to `true` at spawn, the object immediately enters its ON state. For non-animated objects (e.g., doors), `frame_index` is set to `end_row` and dynamic collision is updated accordingly during physics setup.

- **Animation (Linear)**: If `is_animated == false`, animation plays once from `start_frame` to `end_frame` (Toggle ON).
- **Animation (Looping)**: If `is_animated == true`, animation loops between `start_frame` and `end_frame` continuously while the state is ON.
- **Doors (sub_type: door)**:
  - Doors support toggle behavior.
  - Open (ON): Animate from `start_frame` to `end_frame`.
  - Close (OFF): Animate from `end_frame` back to `start_frame`.

## 2. Spatial Interaction & Physics

### Interaction Validation

Interaction is valid if the following conditions are met:

#### 0. Visual Feedback (Indicators)
The system automatically triggers an **interact** emote (!) above the player when they are within 48px of a valid target. This serves as a "ready to interact" visual cue.

#### I. Omni-directional Objects (Spatial Adjacency)
If `activate_from_anywhere` is `True`:
1. **Proximity**: `Vector2(player.pos).distance_to(obj.pos) < 48.0`.
2. **Orientation**: Player must be **facing towards** the object center (Directional Adjacency).
   - This ensures players cannot interact with objects while walking past them with their back turned.

#### II. Standard Directional Objects
If `activate_from_anywhere` is `False` (Default):
1. **Proximity**: `Vector2(player.pos).distance_to(obj.pos) < 45.0`.
   - `obj.pos` is the **footprint center** (center of the bottom 32x32 area).
   - Interaction is calculated as **Footprint-to-Footprint** distance.
2. **Relative Orientation (Physical Front Side Rule)**: 
   - Uses `InteractiveEntity.POSITION_TO_DIR` standard mapping: `0:Down, 1:Left, 2:Right, 3:Up`.
   - The direction specifies the object's **front side** (e.g. `down` means it faces the bottom of the screen).
   - The player must stand on the **corresponding physical side**, facing the **opposite way** (towards the object).
   - Object `down` -> Player must be south (`y > obj_y`), facing `up`.
   - Object `up` -> Player must be north (`y < obj_y`), facing `down`.
   - Object `left` -> Player must be west (`x < obj_x`), facing `right`.
   - Object `right` -> Player must be east (`x > obj_x`), facing `left`.
3. **Orthogonal Alignment**: 
   - The player must be orthogonally aligned to the front side (`abs(dx) < 20` or `abs(dy) < 20`), preventing diagonal triggers.
4. **Exception for Doors**:
   - Open doors (`is_on=True`) allow interaction from the opposite side to allow closing them while walking through.
5. **Emote Suppression**:
   - Proximity emotes (`!`) are suppressed if the object is in the `ON` (open) state and its `sub_type` is a container or barrier (e.g., `chest`, `door`).
   - Mechanical toggles (e.g., `lever`, `button`) always trigger proximity emotes regardless of state.

**Signs (`sub_type == 'sign'`)**:
Signs prioritize the `facing_direction` property (e.g., `up`, `down`) to determine the valid interaction side. If absent, they fallback to the `position` index mapping.

**Relaxation (Doors)**:
If `sub_type == 'door'` and `is_on == True`, the door can be closed from the "opposite side" (e.g., closing a door from the north while facing `down`). This ensures players can easily close doors behind them.

### Interaction Chaining
When an object is successfully interacted with, it checks its `target_id`.
- **Logic**: The `Game` engine searches for any entity with a matching `element_id`.
- **Recursion Guard**: Chaining is limited to a depth of 1 (A -> B) to prevent infinite loops.
- **Trigger**: The target's `interact()` method is called automatically.

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

### 2.4. Ambient Audio Logic
If `sfx_ambient` is defined, the object acts as a spatial audio emitter.
- **Trigger**: Plays looping audio when `is_on=True` and stops when `False`.
- **Spatial Attenuation**: Uses linear falloff based on distance from the player, up to `max_distance` (400px).
- **Minimum Volume**: Maintains a floor volume (e.g. 20% of base `SFX_VOLUME`) so the ambient sound remains slightly audible across the map.

### 2.5. Particle System
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
| Check strict Tiled `class` or `type` | Check for nested `entity_type` marker | Decouples engine instantiation from Tiled UI custom class hierarchy changes |
| Divide sheet by hardcoded values | Use pixel-based slicing (`load_grid_by_size`) | Supports variable object sizes |
| Add doors to map collision layer | Use `obstacles_group` | Allows dynamic passage |
| Pass center pos only | Pass Tiled top-left and dimensions | Ensures correct visual alignment |
| Hardcode door state | Use `is_on` and `is_closing` flags | Animation state machine consistency |
| Use `SPACE` for objects | Use `E` key (Unified) | UX differentiation for objects |
| Calculate distance every frame | Calculate only on key press | CPU optimization |
| Scale surfaces in `update` | Pre-calculate a scaling cache in `__init__` | `pygame.transform.scale` causes severe frame drops when called per-frame on multiple objects |
| Mega `__init__` methods | Refactor into private helper methods (`_parse_properties`, `_setup_physics`) | Ensure compliance with the 50-line maximum per method rule |
| Use Pygame Sprites for particles | Use simple lists of dicts | Sprite allocation overhead causes GC lag when managing hundreds of short-lived particles |
| Unlimited interaction chaining | Limit chaining depth to 1 | Prevents accidental infinite loops and stack overflows in map data |
| Ignore direction for omni-objects | Maintain 48px proximity AND facing requirement | Keeps interaction grounded in spatial awareness and intentionality |
| Rolling text for signs/books | Use Paginated Dialogue System | Allows for multi-page reading with user control |
| Mock `SpriteSheet.__init__` without `valid` attribute | Ensure mock instances have `valid = True` | Entities require `self.spritesheet.valid` to avoid AttributeErrors during initialization |
| Call `Teleport` with `pos` keyword | Use `rect: pygame.Rect` | `Teleport` requires a rect as its first positional argument |
| Use raw element IDs for dialogue | Prefix keys with `{map_name}-` | Dialogue lookups are composite to prevent cross-map collisions |
| Access `current_message` on Dialogue | Access `message` | `DialogueManager` uses `message` for raw content and `displayed_text` for visual state |
| Toggle objects twice in one frame | Call `update(dt)` between interactions | `is_on` toggle is gated by `is_animating`. Animation must finish before toggling back |


## ✅ Patterns to Reproduce

| Pattern | Description | Why |
|---------|-------------|-----|
| **Footprint Centering** | Define interaction `obj.pos` as footprint center, not sprite center. | Supports tall/offset visual assets while keeping grid-consistent logic. |
| **Boundary Value Specification** | Define procedural textures by boundary values (e.g. Center Alpha -> Edge Alpha). | Eliminates ambiguity in generation loops. |
| **ADD Blend Post-Overlay** | Apply additive light halos AFTER the night darkness overlay. | Ensures light sources actively cut through the dark rather than being dimmed by it. |
| **Pre-calculated Scaling Cache** | Pre-generate discrete scaled variants of complex surfaces during startup. | Replaces continuous runtime mathematical operations (which freeze pygame) with discrete memory lookups (which are instant). |
| **Door Relaxation Logic** | Allow `is_on=True` state to bypass standard orientation checks for `door` objects. | Enables players to close doors from the "behind" side after passing through them, improving spatial UX. |

## 4. Test Case Specifications

### Unit Tests Required
| Test ID | Component | Input | Expected Output | Edge Cases |
|---------|-----------|-------|-----------------|------------|
| INT-U-01 | State Toggle | Call `interact()` on OFF object | Sets `is_on` to True, `is_animating` to True | Object is `is_animated=True` |
| INT-U-02 | Animation Step | `update(dt)` when `is_animating=True` | `frame_index` increments based on speed and `dt` | Time step > animation duration |
| INT-U-03 | Animation Loop | `update(dt)` past `end_frame` for looping obj | `frame_index` resets to `start_frame` | High frame rate |
| INT-U-04 | Animation Reverse | `update(dt)` when closing door | `frame_index` decrements towards `start_row` | None |
| INT-U-05 | Pre-calculated Cache | `halo_size=50` | `light_mask_cache` has exactly 10 surfaces (0.97 to 1.03) | `halo_size=0` |
| INT-U-06 | Particle Spawn | `update(dt)` with `particles=True` & `is_on=True` | Active particles list is populated up to `particle_count` | dt=0 |
| INT-U-07 | Particle Cleanup| particle life expires | Removed from active particles list | Empty list |

### Integration Tests Required
| Test ID | Flow | Setup | Verification | Teardown |
|---------|------|-------|--------------|----------|
| INT-I-01 | Proximity Validation | Spawn player at `dir=(0,1)`, object at distance 40px | Press E triggers state change | None |
| INT-I-02 | Proximity Rejection | Spawn player at `dir=(0,1)`, object at distance 50px | Press E does NOT trigger state change | None |
| INT-I-03 | Orientation Validation | Open door from 'wrong' side (Relaxed rule) | Valid orientation identified, state toggles to close | None |
| INT-I-04 | Omni-directional Interaction | `activate_from_anywhere=True`, player facing away | Interaction REJECTED (requires facing) | Boundary at 48px |
| INT-I-05 | Interaction Chaining | Lever `target_id` points to Door `element_id` | Pulling lever opens door | Recursion depth limit |

## 5. Error Handling Matrix

| Error Type | Detection | Response | Fallback |
|------------|-----------|----------|----------|
| Frame Mismatch| `sheet_h % height != 0` | Auto-recalculate `height` | `sheet_h / (end_row + 1)` |
| Sheet Layout | `cols != 4` | Detect `last_cols` | Use dynamic indexing |
| Missing Asset (Sign)| `sub_type == 'sign'` and sheet missing | Use transparent surface | Allows invisible triggers without visual artifacts |
| Headless Display| `pygame.display.get_surface()` is None | Skip `.convert_alpha()` | Prevents crashes during headless unit testing |
| Interaction Spam| Timer check | Ignore input | cooldown of 0.5s |
| Failed Interact | No target found | Show 'question' emote | Optional via `Settings.ENABLE_FAILED_INTERACTION_EMOTE` |

## 6. Deep Links
- **`InteractiveEntity` class**: [interactive.py L11](../../src/entities/interactive.py#L11)
- **`InteractiveEntity.interact`**: [interactive.py L265](../../src/entities/interactive.py#L265)
- **`InteractiveEntity.restore_state`**: [interactive.py L288](../../src/entities/interactive.py#L288)
- **`InteractiveEntity.update`**: [interactive.py L308](../../src/entities/interactive.py#L308)
- **Interactive Spawning**: [game.py L215](../../src/engine/game.py#L215)
- **Collision Check**: [game.py L340](../../src/engine/game.py#L340)
- **Unified Interaction Handling**: [interaction.py L26](../../src/engine/interaction.py#L26)
- **Sprite Slicing**: [spritesheet.py L1](../../src/graphics/spritesheet.py#L1)
- **Unit tests (interactive entity)**: [test_interactive.py L1](../../tests/entities/test_interactive.py#L1)
- **Integration tests (interaction)**: [test_interaction.py L33](../../tests/engine/test_interaction.py#L33)

### Linked Test Functions

| Spec ID | Test Function | File |
|---------|---------------|------|
| INT-U-01 | `test_interact_sign_returns_element_id` | `../../tests/entities/test_interactive.py:L97` |
| INT-U-02 | `test_update_animated_looping_wraps_frame` | `../../tests/entities/test_interactive.py:L116` |
| INT-U-03 | `test_update_animated_off_resets_frame` | `../../tests/entities/test_interactive.py:L123` |
| INT-U-04 | `test_update_closing_door_decrements_frame` | `../../tests/entities/test_interactive.py:L130` |
| INT-I-01 | `test_interaction_orientation` | `../../tests/engine/test_interaction.py:L68` |
| INT-I-02 | `test_pickup_diagonal_rejection` | `../../tests/engine/test_interaction.py:L354` |
| INT-I-03 | `test_verify_orientation_door_relaxed` | `../../tests/engine/test_interaction.py:L102` |
| INT-I-04 | `test_anywhere_object_diagonal_rejection` | `../../tests/engine/test_interaction.py:L384` |
| INT-I-05 | `test_interaction_toggle_entity_by_id` | `../../tests/engine/test_interaction.py:L513` |