# Technical Specification - Engine Core [Implementation]

This document consolidates all rendering, logic, and optimization specifications for the RPG Tile Engine.

## 1. Core Modules

| Module | Responsibility | Primary Classes |
|--------|----------------|-----------------|
| **Engine** | Lifecycle, Config, Events | `Game`, `Settings`, `Logger` |
| **Map** | Data, Culling, Layout | `MapManager`, `LayoutStrategy` |
| **Entity** | Sprites, Sorting, Movement | `BaseEntity`, `Player`, `CameraGroup`, `Teleport` |

## 2. Implementation Details

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

### F. Overlay Configuration
The engine supports configurable overlay elements for atmospheric or UI occlusion rendering.
- **Logic**: Defined via the `overlay` -> `occlusion_alpha` parameter in `settings.json` (accessible via `Settings.OCCLUSION_ALPHA`, default: `102`).
- **Purpose**: Provides a dynamic alpha value layer to allow tuning foreground tile transparency during occlusion checks.

### G. Time & Seasonal System
The engine maintains an internal world clock to drive environmental changes and simulation.
- **Timing**: Configurable via `Settings.MINUTE_DURATION` (default 1.5 real seconds per game minute).
- **Conversion**: `1 real second = (1 / MINUTE_DURATION)` game minutes.
- **Cycles**: 24-hour days, `Settings.DAYS_PER_SEASON` game days per season, and 4-season years.
- **Lighting**: A sinusoidal brightness factor calculated as `0.5 + 0.5 * sin(2π * hour/24 - π/2)`.
- **Night Overlay**: A full-screen black overlay (`#000000`) with alpha calculated from the inverse of brightness (max 180 alpha at midnight).

### H. CPU Freeze Optimization (Entity Visibility)
To optimize performance in large worlds, entity updates are intelligently skipped.
- **Mechanism**: The engine calculates an enlarged viewport based on current screen dimensions.
- **Margin**: A **+128px margin** is added to all sides of the viewport using `inflate_ip(128, 128)`.
- **Behavior**: If an entity's rect is outside this enlarged viewport, its `is_visible` flag is set to `False`, and its `update()` logic (AI, movement, animation) is bypassed.

### I. Spatial Interaction Logic
Entities can interact with their immediate surroundings based on orientation and proximity.
- **NPCs**: Project a 32x32 `target_rect` one tile ahead of the player. See [NPC_SYSTEM.md](NPC_SYSTEM.md) for details.
- **Objects**: Proximity and orientation checks defined by object type. See [INTERACTIVE_OBJECTS.md](INTERACTIVE_OBJECTS.md) for detailed validation logic (Omni vs Directional).
- **Cooldown**: A 0.5s interaction cooldown (`_interaction_cooldown`) prevents input spamming.
- **Unified Key**: The `E` key (`Settings.INTERACT_KEY`) is the universal trigger for both NPCs and fixed objects.

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
In addition to map tile collisions, the engine supports blocking player movement through fixed entities.
- **Mechanism**: The `_is_collidable` check in `Game` iterates through the `interactives` sprite group.
- **Detection**: Uses `collidepoint` check on the entity's 32x32 physical hitbox (`obj.rect`).
- **Scope**: Currently applied only to the `interactives` group to maintain O(N) performance for movement validation.

### L. GameHUD (Visual UI)
The HUD provides information about the current time, day, and season.
- **Rendering**: Drawn at the very end of the `Game.draw()` loop to ensure top-level visibility.
- **Scaling**: Uses `HUD_SCALE = 0.4` (internal resolution scaling) for the main clock graphic.
- **Anchors**: Pixel-precise coordinates for elements (scaled):
  - **Time**: Center `(104.0, 39.2)` relative to clock surface (derived from `(260, 98) * 0.4`).
  - **Season Icon**: Center `(125.2, 111.6)` (derived from `(313, 279) * 0.4`).
  - **Day Label**: Center `(53.2, 113.6)` (derived from `(133, 284) * 0.4`).
- **Margins**: `20px` from top and right screen edges.
- **Label System**: Uses `LabelRegistry` for multilingual support (Day/Jour titles).

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

## 3. Anti-Patterns (DO NOT)

| ❌ Don't | ✅ Do Instead | Why |
|----------|---------------|-----|
| Load assets in `draw()` | Use pre-cached assets | Frame drops |
| Clamp `rect` directly | Clamp `pos` (float) | Better precision/no jitter |
| Hardcode screen sizes | Use `surface.get_size()` | Support Fullscreen/Resizing |
| Direct coordinate access | Use `CoordinateSystem` | Blocks future Isometric support |
| Scroll camera off map | Apply Map Clamping | Professional polish |
| Call `.fill()` on a shared `Surface` | Remove debug rendering | Modifies frames persistently |
| Use `image.get_rect()` for hitbox | Use `Rect(0,0,TILE,TILE)` | Prevents physical vs visual conflict |
| Blit starting from `topleft` | Align `bottomright` | Prevents tall sprites from sinking |

## 4. Test Case Specifications (Aggregated)

| ID | Topic | Input | Expected Output |
|----|-------|-------|-----------------|
| TC-R-01 | Y-Sorting | [Y=100, Y=50] | Rendered [50, 100] |
| TC-R-02 | Culling | Viewport at (0,0) | Only first tiles rendered |
| TC-C-01 | Cam Clamp | Player at (0,0) | Offset = 0 |
| TC-R-03 | Visual Anchor | Image 32x48 | Topleft extends 16px up |
| TC-M-01 | TSX Parsing | External .tsx file | `tile_dict` populated with collidable data |
| TC-X-01 | Interaction | Door closed | `_is_collidable` returns `True` |
| TC-X-02 | Interaction | Door open + Passable | `_is_collidable` returns `False` |
| TC-H-01 | HUD | Interaction log added | HUD renders message with scrolling logic |
| TC-G-01 | Run Loop | QUIT event | `sys.exit()` called, loop terminates |
| TC-T-01 | Teleport | Overlap + Finish Move | `_load_map` called with correct target |
| TC-T-02 | Fading | `transition_type="fade"` | Screen alpha increments, player frozen |

## 5. Error Handling Matrix (Aggregated)

| Failure | Detection | Response | Fallback |
|---------|-----------|----------|----------|
| Config Corrupt | `JSONDecodeError` | Log Warning | Use internal defaults |
| Map Missing | `FileNotFoundError` | Log Critical | Safe loop abort |
| Surface None | `display is None` | Log Error | Use dummy surface |
| Bound Overflow| `pos > 1M` | Log Warn | Clamp to boundary |
| Map Target Fail | `transition_map` target missing | Log Error | Abort transition, keep current map |
| Spawn ID Fail | `spawn_id` mismatch | Log Warning | Default to map center |

## ✅ Patterns to Reproduce

| Pattern | Description | Why |
|---------|-------------|-----|
| **Defensive Asset Normalization** | Always include an extension normalization step (e.g. `.tjm` -> `.tmj`) when resolving external map/tileset paths. | Handles common export-to-filesystem naming typos from the Tiled editor. |
| **Explicit Teleport Triggers** | Trigger teleport only on Arrival (move end) or Intent (explicit movement input while idle). | Prevents infinite teleport loops while ensuring physics-blocked moves still trigger transitions. |

## 6. Deep Links
- **Map Recursive Parsing**: [tmj_parser.py - _process_layers](src/map/tmj_parser.py#L55)
- **Property Detection**: [tmj_parser.py - _parse_objects](src/map/tmj_parser.py#L69)
- **Player Spawn Logic**: [game.py - _load_map](src/engine/game.py#L95)
- **Entity Spawning**: [game.py - _spawn_entities](src/engine/game.py#L179)
- **Interaction Logic**: [game.py - _handle_interactions](src/engine/game.py#L293)
- **Frustum Culling**: [map_manager.py - get_visible_chunks](src/map/manager.py)
- **Teleport Logic**: [game.py - _check_teleporters](src/engine/game.py#L428)
