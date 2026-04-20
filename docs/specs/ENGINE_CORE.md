# Technical Specification - Engine Core [Implementation]

This document consolidates all rendering, logic, and optimization specifications for the RPG Tile Engine.

## 1. Core Modules

| Module | Responsibility | Primary Classes |
|--------|----------------|-----------------|
| **Engine** | Lifecycle, Config, Events | `Game`, `Settings`, `Logger` |
| **Map** | Data, Culling, Layout | `MapManager`, `LayoutStrategy` |
| **Entity** | Sprites, Sorting, Movement | `BaseEntity`, `Player`, `CameraGroup` |

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
- **Logic**: Defined via the `overlay` -> `occlusion_alpha` parameter in `settings.json` (accessible via `Settings.OCCLUSION_ALPHA`).
- **Purpose**: Provides a dynamic alpha value layer to allow tuning future day/night cycles or UI semi-transparency without hardcoding.

### G. Time & Seasonal System
The engine maintains an internal world clock to drive environmental changes and simulation.
- **Timing**: Configurable via `Settings.MINUTE_DURATION` (default 1.5 real seconds per game minute).
- **Conversion**: `1 real second = (1 / MINUTE_DURATION)` game minutes.
- **Cycles**: 24-hour days, `Settings.DAYS_PER_SEASON` game days per season, and 4-season years.
- **Lighting**: A sinusoidal brightness factor calculated as `0.5 + 0.5 * sin(2π * hour/24 - π/2)`.
- **Night Overlay**: A full-screen black overlay (`#000000`) with alpha calculated from the inverse of brightness (max 180 alpha at midnight).

### H. CPU Freeze Optimization (Entity Visibility)
To optimize performance in large worlds, entity updates are intelligently skipped.
- **Mechanism**: The engine calculates an enlarged viewport (screen + 128px margin). 
- **Behavior**: If an entity's rect is outside this enlarged viewport, its `is_visible` flag is set to `False`, and its `update()` logic (AI, movement, animation) is bypassed.

### I. Spatial Interaction Logic
Entities can interact with their immediate surroundings based on orientation and proximity.
- **NPCs**: When `SPACE` or `E` is pressed, the system projects a 32x32 `target_rect` one tile ahead of the player. The first NPC colliding with this rect is interacted with.
- **Objects**: When `E` is pressed, the system performs a proximity check (`< 80px`) and validates the "Opposite Rule". For **open doors**, this orientation check is relaxed to allow closing from the opposite side.
- **Cooldown**: A 0.5s interaction cooldown prevents input spamming.
- **Unified Key**: The `E` key (Settings.INTERACT_KEY) acts as a universal interaction trigger for both NPCs and fixed objects.

### J. Map Data Architecture (TMJ/TSX)
To maintain modularity, the engine decouples map parsing from rendering logic.
- **Data Schema**: The `load_map` method returns a dictionary containing indices:
  - `width`, `height`: Map dimensions in tiles.
  - `spawn_player`: Dict with `x` and `y` center coordinates.
  - `entities`: List of object dictionaries ready for engine spawning.
  - `tile_dict`: Mapping of GIDs to `TileProperty` objects (including collision and depth).
- **Coordinates**: Tiled object coordinates (Top-Left) are automatically offset by `TILE_SIZE / 2` to align with the center-based system.
- **Property Extraction & Nested Classes**: Since Tiled 1.10+, object custom classes store properties in nested dictionaries under the hood (e.g. `interactive_object -> sprite -> sprite_sheet`).
  - Spawning logic avoids checking direct Tiled "type" or "class" assignments. Instead, it uses a generic nested search to find logical markers like `entity_type`.
  - Resolution order for any property `key` during entity spawn is: `root` -> `interactive_object -> sprite` -> `sprite` -> `interactive_object`.
  - This effectively flattens structured configurations back into easy access values during object construction, allowing entities to remain ignorant to map architecture.

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
  - **Time**: Center `(107.2, 44.8)` relative to clock surface (derived from `(268, 112) * 0.4`).
  - **Season Icon**: Center `(125.2, 111.6)` (derived from `(313, 279) * 0.4`).
  - **Day Label**: Center `(57.2, 115.6)` (derived from `(143, 289) * 0.4`).
- **Margins**: `30px` from top and right screen edges.
- **Label System**: Uses `LabelRegistry` for multilingual support (Day/Jour titles).

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

## 5. Error Handling Matrix (Aggregated)

| Failure | Detection | Response | Fallback |
|---------|-----------|----------|----------|
| Config Corrupt | `JSONDecodeError` | Log Warning | Use internal defaults |
| Map Missing | `FileNotFoundError` | Log Critical | Safe loop abort |
| Surface None | `display is None` | Log Error | Use dummy surface |
| Bound Overflow| `pos > 1M` | Log Warn | Clamp to boundary |

## 6. Deep Links
- **Map Recursive Parsing**: [tmj_parser.py - _process_layers](src/map/tmj_parser.py#L55)
- **Property Detection**: [tmj_parser.py - _parse_objects](src/map/tmj_parser.py#L69)
- **Player Spawn Logic**: [game.py - __init__](src/engine/game.py#L18)
- **Frustum Culling**: [map_manager.py - get_visible_chunks](src/map/manager.py)
