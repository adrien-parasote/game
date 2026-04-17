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
- **Timing**: 1 real second = 1 game minute; 1 real minute = 1 game hour.
- **Cycles**: 24-hour days, 30-day seasons, and 4-season years (120 days total).
- **Lighting**: A sinusoidal brightness factor calculated as `0.5 + 0.5 * sin(2π * time - π/2)`.
- **Night Overlay**: A full-screen black overlay with alpha calculated from the inverse of brightness (max 180 alpha at midnight).

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
- **Recursive Processing**: `TmjParser` traverses the layer tree recursively, supporting nested groups.
- **Spawn Detection**: The player spawn is identified by:
  - Any object with custom property `spawn_player: true`.
  - Any object with native `class` or `type` set to `player`.
- **Entity Extraction**: All objects found in `objectgroup` layers are collected into a unified `entities` list.
- **Coordinates**: Tiled object coordinates (Top-Left) are automatically offset by `TILE_SIZE / 2` to align with the center-based system.

### K. Entity Collision Logic
In addition to map tile collisions, the engine supports blocking player movement through fixed entities.
- **Mechanism**: The `_is_collidable` check in `Game` iterates through the `interactives` sprite group.
- **Detection**: Uses `collidepoint` check on the entity's 32x32 physical hitbox (`obj.rect`).
- **Scope**: Currently applied only to the `interactives` group to maintain O(N) performance for movement validation.

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
| TC-C-02 | Cam Center | Small map | Map centered on screen |
| TC-B-01 | Bounds | Player at X=-100 | Player at X=16 (edge) |
| TC-B-02 | Bounds | Player at X=5000 | Player at X=2032 (edge) |
| TC-R-03 | Visual Anchor | Image 32x48 | Topleft extends 16px up |
| TC-B-03 | Player Hitbox | Player spawn | Rect size is 32x32 |

## 5. Error Handling Matrix (Aggregated)

| Failure | Detection | Response | Fallback |
|---------|-----------|----------|----------|
| Config Corrupt | `JSONDecodeError` | Log Warning | Use internal defaults |
| Map Missing | `FileNotFoundError` | Log Critical | Safe loop abort |
| Surface None | `display is None` | Log Error | Use dummy surface |
| Bound Overflow| `pos > 1M` | Log Warn | Clamp to boundary |

## 6. Deep Links
- **Map Recursive Parsing**: [tmj_parser.py - _process_layers](src/map/tmj_parser.py#L44)
- **Property Detection**: [tmj_parser.py - _parse_objects](src/map/tmj_parser.py#L55)
- **Player Spawn Logic**: [game.py - __init__](src/engine/game.py#L67)
- **Frustum Culling**: [map_manager.py - get_visible_chunks](src/map/manager.py)
