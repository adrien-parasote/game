# Technical Specification - Engine Core

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
- [STRATEGY.md](STRATEGY.md)
- [QA_AND_STANDARDS.md](QA_AND_STANDARDS.md)
