> **Design tokens** – see [design-tokens.md](./design-tokens.md)
[assumption: "All implicit constants and defaults are documented here – pending detailed entries"] – risk: Low

# Technical Specification - Directional Movement & Animated Autotiles

> Document Type: Implementation
> Status: IMPLEMENTED

## 1. Goal Description

This specification details the transition from a binary collision model (`collidable`) to a richer constraint model using `walkable` and `direction` flags. It also defines the implementation of Tiled's native animated tiles (autotiles like `01-water`) using a "Dynamic Batching" render strategy to preserve cache performance.

## 2. Component Overview

| Module | File | Modification |
|--------|------|--------------|
| `TmjParser` | `src/map/tmj_parser.py` | Extract `walkable`, `direction`, and `<animation>` tags. |
| `MapManager` | `src/map/manager.py` | Rename `is_collidable` -> `is_walkable`. Support dynamic batching. |
| `CollisionChecker` | `src/engine/collision_checker.py` | Adapt to `is_walkable`. |
| `BaseEntity` | `src/entities/base.py` | Add intercept logic in `start_move` for directional constraints. |
| `Game` | `src/engine/game.py` | Add animated tile pass in `_draw_scene`. |

## 3. Data Structures

### 3.1. TileMapData Update
`src/map/tmj_parser.py`
```python
@dataclass
class TileMapData:
    image: pygame.Surface
    depth: int
    walkable: bool
    direction_flags: set[str]  # e.g. {"up", "right"} or {"any"}
    frames: list[tuple[int, int]] | None = None # [(tile_id, duration_ms), ...]
    occluded_image: pygame.Surface | None = None
    properties: dict[str, Any] | None = None
```

## 4. Implementation Details

### A. Walkable & Direction Properties Parsing
In `TmjParser._parse_tsx()`:
1.  **Defaults**:
    -   `walkable`: Default to `True` (inverted from `collidable: False`).
    -   `direction`: Default to `"any"`.
2.  **Extraction**:
    -   Read `walkable` (bool) and `direction` (string) from TSX properties.
    -   Parse the `direction` string into a `set[str]`: `set(d.strip() for d in val.split(",") if d.strip())`.
    -   If the set is empty, default to `{"any"}`.
    -   Store in `TileMapData`.

### B. MapManager Collision Updates
In `MapManager`:
1.  Rename `is_collidable(x, y)` to `is_walkable(x, y)`.
2.  **Logic**: Return `False` if **any** tile at `(x, y)` has `walkable == False`. Otherwise, return `True`.
3.  Add `get_direction_flags(x, y) -> set[str]`:
    -   Returns the `direction_flags` of the highest layer tile at `(x, y)`.
    -   Returns `{"any"}` if empty or out of bounds.

### C. Movement Constraint Logic
In `BaseEntity.start_move()`:
1.  Before checking destination `collision_func`, check the **current** tile's direction flags.
2.  **Algorithm**:
    ```python
    current_tx = int(self.pos.x // Settings.TILE_SIZE)
    current_ty = int(self.pos.y // Settings.TILE_SIZE)
    allowed_directions = self.game.map_manager.get_direction_flags(current_tx, current_ty)
    
    # Map vector to string (Cardinal priority)
    requested_dir = None
    if abs(self.direction.x) > abs(self.direction.y):
        if self.direction.x > 0: requested_dir = "right"
        else: requested_dir = "left"
    else:
        if self.direction.y > 0: requested_dir = "down"
        else: requested_dir = "up"
    
    # Check constraint
    if "any" not in allowed_directions and requested_dir not in allowed_directions:
        return # Movement blocked by current tile's exit constraints
    ```
3.  **Then** check if the destination is walkable via `collision_func` (which delegates to `MapManager.is_walkable`).

### D. Native Animated Autotiles (Dynamic Batching)
To support Tiled's `<animation>` tags natively without destroying the `get_layer_surface()` cache performance:

1.  **Parsing (`TmjParser._parse_tsx`)**:
    -   Find `<animation>` inside `<tile>`.
    -   Extract `<frame tileid="X" duration="Y"/>`.
    -   Store as `frames = [(firstgid + int(tileid), int(duration)), ...]`.
2.  **Caching Strategy (`MapManager.get_layer_surface`)**:
    -   When blitting tiles to the static cached layer Surface, **skip** any tile that has `frames is not None`.
3.  **Dynamic Rendering (`MapManager.get_visible_animated_chunks`)**:
    -   Create a new generator similar to `get_visible_chunks`.
    -   It yields `(px, py, tile_id, depth)` only for tiles where `frames` is not None.
4.  **Game Loop (`Game._draw_scene`)**:
    -   After rendering the static layer surface from `MapManager`, iterate `get_visible_animated_chunks()`.
    -   Compute the current frame index:
        ```python
        current_time = pygame.time.get_ticks()
        tile_data = map_manager.tiles[tile_id]
        total_duration = sum(dur for _, dur in tile_data.frames)
        if total_duration <= 0:
            frame_gid = tile_data.frames[0][0] # Fallback to first frame
        else:
            time_in_cycle = current_time % total_duration
            # ... Find frame logic ...
        
        # Find frame
        accumulated = 0
        frame_gid = tile_data.frames[0][0]
        for f_gid, dur in tile_data.frames:
            accumulated += dur
            if time_in_cycle < accumulated:
                frame_gid = f_gid
                break
        
        # Blit frame_gid's image
        ```

## 5. Anti-Patterns (DO NOT)
| ❌ Don't | ✅ Do Instead | Why |
|----------|---------------|-----|
| Invalidate the entire layer cache every 150ms | Use "Rendu séparé" (Dynamic Batching) for animated tiles | Redrawing a 3200x3200 surface every 150ms will drop FPS to 0. |
| Check destination tile for direction constraints | Check the *current* departure tile | The `direction` property defines *exit* permissions, not entry permissions. |
| Crash if `walkable` is missing | Default `walkable` to `True` | Ensures old maps without properties don't freeze the game. |
| Process animated frames directly in TMJ `load` | Defer to `_parse_tsx` where firstgid is known | Local `<animation>` IDs must be converted to global IDs via `firstgid`. |
| Create a separate pygame Surface for animated tiles | Yield directly to the screen display during `draw_scene` | Avoids allocating yet another intermediate large surface. |

## 6. Error Handling
| Error Type | Detection | Response | Fallback |
|------------|-----------|----------|----------|
| Missing `direction` | KeyError in `props` | Log debug | Set `direction` to `{"any"}` |
| Invalid `<animation>` reference | Missing `tileid` in `tile_dict` | Log error | Skip frame, use static tile image |
| Negative or Zero `duration` | Check `<frame duration="...">` or sum | Log warning | Force total duration or frame to `100` |
| Empty `direction` string | `direction: ""` in Tiled | Log debug | Set `direction` to `{"any"}` |

## 7. Deep Links
- **TmjParser**: [tmj_parser.py L123](../../src/map/tmj_parser.py#L123)
- **MapManager**: [manager.py L85](../../src/map/manager.py#L85)
- **BaseEntity**: [base.py L40](../../src/entities/base.py#L40)

## 8. Assumptions
| # | Assumption | Risk | Validation |
|---|------------|------|------------|
| 1 | Animated frames all belong to the same TSX as the parent tile. | Low | Tiled exports frame `tileid` relative to the current TSX. |
| 2 | A tile cannot have both `depth > 0` (occlusion) and an `<animation>`. | Medium | If true, dynamic batching would need to support alpha-blended animated tiles. We assume animated water is `depth=0`. |
| 3 | Static maps without animated tiles will not suffer any performance overhead from the generator. | Low | Empty generator exits instantly in `Game._draw_scene`. |
| 4 | Empty coordinates (no tiles) should be treated as non-walkable. | Low | `is_walkable` logic should check if at least one tile exists. |

## 9. Test Case Specifications

### Unit Tests
| ID | Component | Input | Expected Output |
|----|-----------|-------|-----------------|
| TC-001 | `TmjParser` | TSX with `<animation>` | `TileMapData.frames` populated correctly |
| TC-002 | `TmjParser` | `direction: "up, right"` | `direction_flags == {"up", "right"}` |
| TC-003 | `BaseEntity` | Try moving "left" on tile with `direction: "up"` | Move cancelled, `target_pos` unchanged |
| TC-004 | `MapManager` | `get_visible_animated_chunks` called on static map | Yields empty sequence |
| TC-005 | `BaseEntity` | Try moving "up" on tile with `direction: "any"` | Move allowed, `target_pos` updated |

### Integration Tests
| ID | Flow | Setup | Verification |
|----|------|-------|--------------|
| IT-001 | Movement Constraint | Player on `"up"` tile | Arrow down ignored, arrow up allowed |
| IT-002 | Animated Tile Render | Map with water tile | `get_layer_surface` contains transparent hole, dynamic batching yields correct frame. |
| IT-003 | Frame Cycle Accuracy | Wait `150ms` | Animated tile yields exactly the second frame ID in sequence. |
