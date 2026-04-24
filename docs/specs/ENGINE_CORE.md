# Technical Specification - Engine Core [Implementation]

This document consolidates all rendering, logic, and optimization specifications for the RPG Tile Engine.

## 1. Core Modules

| Module | Responsibility | Primary Classes |
|--------|----------------|-----------------|
| **Engine** | Lifecycle, Config, Events | `Game`, `Settings`, `Logger` |
| **Map** | Data, Culling, Layout | `MapManager`, `LayoutStrategy` |
| **Entity** | Sprites, Sorting, Movement | `BaseEntity`, `Player`, `CameraGroup`, `Teleport` |
| **Logic** | Interaction gating, Proximity | `InteractionManager` |
| **System** | Persistence, State | `WorldState` |

## 2. Context Stack (AI Prompting Guide)

Before performing any code changes, an AI agent MUST load the following "Context Stack" to understand the interconnected logic:

1.  **Strategic**: `ENGINE_CORE.md` (This document) - High-level architectural rules.
2.  **Implementation**: `INTERACTIVE_OBJECTS.md` - If touching any map objects.
3.  **Core Logic**: `src/engine/game.py` - The main coordination loop.
4.  **Spatial Logic**: `src/engine/interaction.py` - How entities see each other.
5.  **Global State**: `src/config.py` - All thresholds and constants.

## 3. Implementation Details

### A. Rendering Optimization (Frustum Culling)
To support large maps, only visible tiles are processed.
- **Math**: 
  - `start_col = floor(viewport.left / tile_size)`
  - `end_col = ceil(viewport.right / tile_size)`
- **Behavior**: Iterate only through this O(1) range in `MapManager`.

### B. Camera Clamping
The viewport is constrained to the map boundaries.
- **Logic**: `offset.x = clamp(centered_x, -(world_w - screen_w), 0)`.
- **Centering**: If `world_w < screen_w`, `offset.x = (screen_w - world_w) // 2`.

### C. Grid-Based Movement
All entities move in discrete steps of `TILE_SIZE`.
- **Logic**:
  - `is_moving` flag prevents starting new moves mid-travel.
  - `target_pos` is calculated as `current_pos + direction * TILE_SIZE`.
  - Cardinal directions only (Up, Down, Left, Right).
- **Centering**:
  - Entities must always be aligned to tile centers: `(x * TILE_SIZE + TILE_SIZE/2, y * TILE_SIZE + TILE_SIZE/2)`.
  - Spawning and movement targets must maintain this half-tile offset.
- **Interpolation**: Smooth movement between tiles using `Settings.PLAYER_SPEED`.

### D. World Boundaries (Player/Entity)
All entities are physically restricted to map dimensions.
- **Logic**: Clamping is applied to `target_pos` to prevent choosing a target outside the world.
- **Placement**: Integrated into the Grid Movement controller in `BaseEntity`.

### E. Visual Anchoring vs Physical Hitbox
Sprites are often taller than a single tile (e.g. 32x48 images on 32x32 tiles).
- **Physical Hitbox**: Must strictly remain 32x32 (`Settings.TILE_SIZE`) to maintain grid alignment.
- **Visual Anchoring**: Rendered images are offset such that the `bottomright` of the image aligns exactly with the `bottomright` of the physical hitbox. 
- **Occlusion Check**: To trigger foreground tile overlap (alpha blending), the system uses the full expanded visual rect, not just the physical hitbox.

### F. Configuration Split
The engine uses a dual-configuration architecture to separate technical and gameplay concerns.
- **`settings.json`**: Technical parameters (resolution, fullscreen, log level, culling margins, map paths).
- **`gameplay.json`**: Logic parameters (player speed, NPC speed multipliers, interaction keys, time scales, UI text speed).
- **Logic**: The `src/config.py` manager merges these into a single `Settings` object for engine-wide access.

### G. Time & Seasonal System
The engine maintains an internal world clock to drive environmental changes and simulation.
- **Timing**: Configurable via `Settings.MINUTE_DURATION` (default 1.5 real seconds per game minute).
- **Conversion**: 1 real second = (1 / MINUTE_DURATION) game minutes.
- **Cycles**: 24-hour days, `Settings.DAYS_PER_SEASON` game days per season, and 4-season years.
- **Lighting**: A sinusoidal brightness factor calculated as `0.5 + 0.5 * sin(2π * hour/24 - π/2)`.
- **Night Overlay**: A full-screen black overlay (`#000000`) with alpha calculated from the inverse of brightness (max 180 alpha at midnight).

### H. CPU Freeze Optimization (Entity Visibility)
To optimize performance in large worlds, entity updates are intelligently skipped.
- **Mechanism**: The engine calculates an enlarged viewport based on current screen dimensions.
- **Margin**: A **+128px margin** is added to all sides of the viewport using `inflate_ip(128, 128)`.
- **Behavior**: If an entity's rect is outside this enlarged viewport, its `is_visible` flag is set to `False`, and its `update()` logic (AI, movement, animation) is bypassed.

### I. Spatial Interaction Logic
Decoupled logic in `InteractionManager` handles all entity/player spatial triggers.
- **NPCs**: Project a 32x32 `target_rect` one tile ahead of the player.
- **Objects**: Proximity (<45px) and orientation checks defined by object type.
- **Door Relaxation**: Open doors (`is_on=True`) allow interaction from the "wrong" side to enable closing after passing through.
- **Cooldown**: A 0.5s interaction cooldown prevents input spamming.
- **Unified Key**: The `E` key (`Settings.INTERACT_KEY`) is the universal trigger.

### J. Map Data Architecture (TMJ/TSX)
To maintain modularity, the engine decouples map parsing from rendering logic.
- **Data Schema**: The `load_map` method returns a dictionary containing indices:
  - `width`, `height`: Map dimensions in tiles.
  - `spawn_player`: Dict with `x` and `y` center coordinates.
  - `entities`: List of object dictionaries ready for engine spawning.
  - `tile_dict`: Mapping of GIDs to `TileProperty` objects (including collision and depth).
- **Coordinates**: Tiled object coordinates (Top-Left) are automatically offset by `TILE_SIZE / 2` to align with the center-based system.
- **Property Extraction & Schema Resolution**: Since Tiled 1.10+, object custom classes store properties in nested dictionaries under the hood. 
  - **TiledProject Resolver**: The engine now loads `assets/tiled/game.tiled-project` to handle recursive inheritance for Tiled Classes (`propertyTypes`).
  - **Logic**: It deep-merges project defaults with map-level overrides. 
  - **Example**: If a `torch` is defined as a `12-light_source` class in Tiled, the engine automatically populates it with `particles: true` even if not present in the `.tmj` file.
  - **Resolution**: Spawning logic uses a generic nested search helper (`_get_property`) to find logical markers across resolved structures.

### K. Entity Collision Logic
In addition to map tile collisions, the engine supports blocking player movement through dynamic entities.
- **Mechanism**: The `_is_collidable` check in `Game` iterates through the `interactives` and `npcs` sprite groups.
- **Detection**: Uses `collidepoint` check on the entity's physical hitbox (`obj.rect`).
- **Scope**: Applied to `interactives` (Doors, etc.) and `npcs` to ensure physical consistency.

### L. GameHUD (Visual UI)
The HUD provides information about the current time, day, and season.
- **Rendering**: Drawn at the very end of the `Game.draw()` loop to ensure top-level visibility.
- **Scaling**: Uses `HUD_SCALE = 0.4` for the clock and `HUD_SCALE = 0.64` for the dialogue box (fit 2000px assets to 1280px screen).
- **Dialogue UI**:
  - **Message Zone**: Centered horizontally, occupies the middle-third of the text box.
  - **Typewriter Effect**: Speed controlled by `Settings.TEXT_SPEED` (characters per second).
  - **Paging Logic**: Automatic pagination. If text exceeds the box's capacity, the typing stops. The user must press the interaction key (`Settings.INTERACT_KEY`) to skip typing or advance to the next page.
- **Label System**: Uses `fr.json` (or other lang) for localized strings.

### M. Interconnected World (Teleportation)
The engine supports a multiverse structure defined by Tiled World files.
- **World Config**: The initial map is resolved at startup by parsing `assets/tiled/maps/world.world` (JSON). 
- **Teleport Entity**: A logical trigger volume strictly defined by the Tiled property `type: teleport`. It is invisible and non-collidable.
- **Properties**:
  - `target_map`: The `.tmj` file to load.
  - `target_spawn_id`: The `spawn_id` of the destination `00-spawn_point`.
  - `transition_type`: `"fade"` (slow black overlay) or `"instant"`.
  - `required_direction`: `"any"` (default), `"up"`, `"down"`, `"left"`, or `"right"`.
- **Transition Logic**:
  - Triggered when a player **finishes** a movement step (`was_moving=True` and `is_moving=False`) while overlapping a teleport rect (Arrival trigger).
  - **Intent Trigger**: Triggered while the player is already idle on a teleport rect and **pushes** a movement key (`direction.magnitude() > 0`) in the `required_direction`. This ensures transitions fire even if the move is physically blocked by a wall.
  - **'Any' Portal Exception**: To prevent infinite "spawn-and-re-teleport" loops, portals with `required_direction="any"` ignore Intent triggers and only fire on Arrival.
  - **Direction Guard**: If `required_direction` is not `"any"`, the player's `current_state` (facing direction) must match the property Value to trigger the transition.
  - **Fading**: Uses a full-screen black surface with incrementing alpha. The `time_system` continues to update during the fade to maintain simulation continuity.

  - **Infinite Loop Protection**: Atomic detection after movement prevents a player from being immediately teleported back if spawned on a portal.
- **Map Loading (`_load_map`)**:
  - Systematic cleanup of `interactives`, `npcs`, `obstacles_group`, and `teleports_group`.
  - The `Player` instance is preserved and repositioned to the exact coordinates of the target `00-spawn_point`.
  - Logically handles `.tjm` vs `.tmj` extension mismatches for compatibility.

### N. Audio Management (BGM & SFX)
The engine features a centralized audio system for atmospheric music and interactive sound effects.
- **Module**: `src/engine/audio.py` (`AudioManager`).
- **Technical Configuration**:
  - `bgm_volume`, `sfx_volume` (0.0 to 1.0) defined in `Settings`.
  - Preloading: All `.ogg` files in `assets/audio/sfx/` are loaded into memory during initialization.
- **Continuum Logic**: When transitioning between maps, the engine checks the `bgm` property of the target map. If it matches the current BGM name, the track continues uninterrupted.
- **Transitions**: BGM changes involve a 500ms fade-out/fade-in.
- **SFX Overlap Guard**: SFX playback tracks a `source_id`. If the same source (e.g., a lever) triggers its SFX again before completion, the previous instance is stopped to prevent volume doubling/flanging.

### O. Debug Mode & Visual Hitboxes
The engine includes a technical debugging layer for development verification.
- **Toggle**: Controlled by `Settings.DEBUG` (loaded from `settings.json`'s `debug.enabled` field).
- **Map Override**: If `DEBUG` is active, the engine bypasses the default map and loads `99-debug_room.tmj` at startup.
- **Hitbox Rendering**: When active, all entity physical hitboxes (`rect`) are outlined in red (`(255, 0, 0)`) in the `CameraGroup` draw loop.
- **Robustness**: Debug rendering is wrapped in safety checks (`try-except TypeError`) to handle mock surfaces during automated testing.

### P. Paginated Dialogue System
The dialogue system (HUD) uses a multi-page architecture with typewriter effects.
- **Pagination Strategy**: Pre-calculates wrapping based on `font_message` metrics and `dialogue_box` internal margins (140px).
- **Dynamic Layout**: Line count per page automatically adjusts based on the presence of a `title` (3 lines with title, 5 lines without).
- **State Machine**:
  1. **Typing**: Text is revealed character-by-character.
  2. **Page Complete**: Reveals the "Next" cursor (`06-cursor.png`).
  3. **Skip**: Pressing `Settings.INTERACT_KEY` while typing immediately fills the current page.
  4. **Next**: Pressing `Settings.INTERACT_KEY` when page is complete advances to the next page or closes the dialogue.
- **Shadowing**: All text is rendered twice (2px offset) to ensure visibility against complex backgrounds.

### Q. World State Persistence
To maintain consistency across map transitions, the engine uses a session-persistent state dictionary.
- **Unique Key**: Generated as `{map_basename}_{tiled_id}` to ensure zero collisions across different maps.
- **Persistence Scope**: Only the `is_on` state of `InteractiveEntity` objects is currently tracked.
- **Lifecycle**:
  - **Save**: Triggered immediately during `interact()` or interaction chaining (`toggle_entity_by_id`).
  - **Restore**: Performed during map loading (`Game._spawn_entities`) before any rendering occurs.
  - **Visual Sync**: Restored entities automatically snap to their final frame (start/end row) to prevent animation glitches on reload.
### R. The Rendering Pipeline (`_draw_scene`)

The engine uses a multi-pass rendering pipeline to combine layers, entities, and environmental effects.

1.  **Pass 1: Background**: Draw map layers with `depth=0`.
2.  **Pass 2: Sorted Entities**: Draw `visible_sprites` using Y-Sorting.
3.  **Pass 4: Environmental Overlay**:
    *   **Night Surface**: If `night_alpha > 0`, blit a full-screen black overlay with `SRCALPHA`.
    *   **Light Halos**: Blit pre-calculated light masks using `BLEND_RGB_ADD` **after** the night overlay to "cut through" the darkness.
4.  **Pass 3: Foreground**: Draw map layers with `depth=1` (Occlusion).
5.  **Pass 5: UI/HUD**: Draw clock, season, and active dialogue boxes.

### S. Dynamic Effect Specifications

#### Light Halos (Premium Glow)
- **Generation**: Radial gradient from `halo_color` to `(0,0,0)`.
- **Scaling**: Each halo uses a pre-calculated cache of 10 surfaces (size 97% to 103%) to simulate "breathing".
- **Flicker**: Derived from `sin(time * flicker_speed)`.

#### Particle Logic (Performance-Safe)
- **Data Model**: Simple list of dicts (x, y, vx, vy, life).
- **Update**: `life -= dt`. Remove if `life <= 0`.
- **Rendering**: `pygame.draw.circle` with alpha fading: `alpha = (life / max_life)`.

## 4. Anti-Patterns (DO NOT)

| ❌ Don't | ✅ Do Instead | Why |
|----------|---------------|-----|
| Load assets in `draw()` | Use pre-cached assets | Frame drops and I/O overhead |
| Clamp `rect` directly | Clamp `pos` (float) | Prevents sub-pixel jitter and rounding errors |
| Hardcode screen sizes | Use `surface.get_size()` | Support Fullscreen and dynamic resizing |
| Direct coordinate access | Use `CoordinateSystem` | Decouples rendering from game logic |
| Scroll camera off map | Apply Map Clamping | Professional polish and boundary consistency |
| Call `.fill()` on a shared `Surface` | Remove debug rendering | Modifies frames persistently and breaks culling |
| Use `image.get_rect()` for hitbox | Use `Rect(0,0,TILE,TILE)` | Prevents physical vs visual conflict (offset logic) |
| Blit starting from `topleft` | Align `bottomright` | Prevents tall sprites from "sinking" into tiles |
| Use `print()` for debugging | Use the `logging` module | Standardized output and production-ready tracking |
| Interact while facing away | Validate facing direction | Prevents "psychic" interactions through back-facing |
| Render to non-Surface objects | Type-check or wrap with `try-except` | Prevents crashes in unit tests using Mocks |

## 4. Test Case Specifications (Aggregated)

| ID | Topic | Input | Expected Output |
|----|-------|-------|-----------------|
| TC-R-01 | Y-Sorting | [Y=100, Y=50] | Rendered [50, 100] |
| TC-R-02 | Culling | Viewport at (0,0) | Only first tiles rendered |
| TC-C-01 | Cam Clamp | Player at (0,0) | Offset = 0 |
| TC-R-03 | Visual Anchor | Image 32x48 | Topleft extends 16px up |
| TC-H-01 | HUD | Dialogue started | Text paginated and typing initiated |
| TC-H-02 | HUD | Skip request | `displayed_text` immediately filled |
| TC-W-01 | WorldState | Toggle lever + Reload | Lever remains in toggled state |
| TC-T-01 | Teleport | Overlap + Intent (DIR) | `transition_map` triggered |
| TC-T-02 | Teleport | Overlap + 'Any' Portal | Intent ignored, triggers on Arrival |

## 5. Error Handling Matrix (Aggregated)

| Failure | Detection | Response | Fallback |
|---------|-----------|----------|----------|
| Config Corrupt | `JSONDecodeError` | Log Warning | Use internal defaults |
| Map Missing | `FileNotFoundError` | Log Critical | Safe loop abort |
| Surface None | `TypeError` in Draw | Log Error | Ignore rendering step (safe for tests) |
| Dialogue Key Fail| Missing `fr.json` key | Log Warning | Show raw key or empty string |
| Audio Init Fail | `pygame.mixer` error | Log Warning | Disable audio system, continue game |
| Interaction Loop | Chaining depth > 1 | Log Warning | Break chain to prevent recursion crash |

## ✅ Patterns to Reproduce

| Pattern | Description | Why |
|---------|-------------|-----|
| **Defensive Asset Normalization** | Always include an extension normalization step (e.g. `.tjm` -> `.tmj`) when resolving external map/tileset paths. | Handles common export-to-filesystem naming typos from the Tiled editor. |
| **Explicit Teleport Triggers** | Trigger teleport only on Arrival (move end) or Intent (explicit movement input while idle). | Prevents infinite teleport loops while ensuring physics-blocked moves still trigger transitions. |
| **State Snapshot Restoration** | Objects must restore their state *before* the first frame of map display. | Prevents "flicker" where an object starts in default state before snapping to saved state. |

## 6. Deep Links
- **Map Recursive Parsing**: [tmj_parser.py - _process_layers](src/map/tmj_parser.py#L55)
- **World State Logic**: [world_state.py](src/engine/world_state.py)
- **Interaction Logic**: [interaction.py](src/engine/interaction.py)
- **Dialogue Paging Logic**: [dialogue.py - _paginate](src/ui/dialogue.py#L74)
- **Teleport Logic**: [game.py - _check_teleporters](src/engine/game.py#L517)
- **SFX Overlap Guard**: [audio.py - play_sfx](src/engine/audio.py#L111)
- **Hitbox Debugging**: [groups.py - custom_draw](src/entities/groups.py#L65)
