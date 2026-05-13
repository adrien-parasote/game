# Implementation Plan - Phase 1.6: Directional Autotiles

> Based on: `docs/specs/phase-1.6-directional-autotiles.md`

## 1. Inventory of Spec Requirements
1. `TileMapData` struct update (`walkable`, `direction_flags`, `frames`).
2. `TmjParser._parse_tsx` extraction logic for `walkable`, `direction`, and XML `<animation>`.
3. Rename `MapManager.is_collidable` to `is_walkable` (inverted logic) + handle empty coordinates as non-walkable.
4. Update `CollisionChecker` to call `is_walkable`.
5. Add `MapManager.get_direction_flags(x, y)`.
6. Add interception logic in `BaseEntity.start_move` utilizing cardinal priority (`abs(x) > abs(y)`).
7. Modify `MapManager.get_layer_surface` to skip blitting animated tiles into the cache.
8. Add `MapManager.get_visible_animated_chunks()`.
9. Modify `Game._draw_scene` to compute and render the correct animation frame based on `pygame.time.get_ticks()`.

## 2. Architecture Impact
- **Data Models**: `src/map/tmj_parser.py` (`TileMapData` dataclass).
- **Parsers**: `src/map/tmj_parser.py` (`_parse_tsx`).
- **Map State**: `src/map/manager.py` (caching, chunking, walkability queries).
- **Physics/Logic**: `src/engine/collision_checker.py`, `src/entities/base.py`.
- **Rendering**: `src/engine/game.py` (`_draw_scene`).

## 3. Implementation Steps (Vertical Slices)

### Step 1: Base Data Structure & Walkability Translation
*Replaces the binary `collidable` flag with the explicit `walkable` semantic across the engine.*

**Files:**
| File | Action | Description |
|------|--------|-------------|
| `src/map/tmj_parser.py` | Modify | Update `TileMapData` and `_parse_tsx` to extract `walkable`. Default to `True`. |
| `src/map/manager.py` | Modify | Rename `is_collidable` -> `is_walkable`. Invert logic. Empty coords = `False`. |
| `src/engine/collision_checker.py` | Modify | Update call sites from `is_collidable` to `is_walkable` (inverted). |

- **Dependencies:** None.
- **Risks:** L (Low) - Search/replace `is_collidable` might miss dynamic invocations. Mitigation: Run `pytest` / global grep.
- **Tests:** `TC-001` (partial), `TC-004`.
- **Acceptance Criteria:** Player can still walk on grass but is blocked by non-walkable walls. `TileMapData` possesses `walkable`. No crashes.

---

### Step 2: Directional Exit Constraints
*Implements the exit restriction from the tile the player is currently standing on.*

**Files:**
| File | Action | Description |
|------|--------|-------------|
| `src/map/tmj_parser.py` | Modify | Parse `direction` property in `_parse_tsx`. Convert to `set[str]` in `TileMapData`. Default `{"any"}`. |
| `src/map/manager.py` | Modify | Add `get_direction_flags(tx, ty)` returning the top layer's set. |
| `src/entities/base.py` | Modify | Inject logic at the top of `start_move()` to check `get_direction_flags` against the requested movement direction using cardinal priority. |

- **Dependencies:** Step 1.
- **Risks:** M (Medium) - Vector-to-string mapping might break for diagonals. Mitigation: Apply `abs(x) > abs(y)` cardinal priority strictly as specified.
- **Tests:** `TC-002`, `TC-003`, `TC-005`, `IT-001`.
- **Acceptance Criteria:** A tile flagged with `direction="up"` allows exiting upwards but cancels any attempt to exit left, right, or down.

---

### Step 3: Animated Tiles Data Pipeline & Cache Evasion
*Extracts the `<animation>` tags and prevents them from baking into the static map cache.*

**Files:**
| File | Action | Description |
|------|--------|-------------|
| `src/map/tmj_parser.py` | Modify | Read `<animation><frame...>` in `_parse_tsx()`. Populate `frames`. |
| `src/map/manager.py` | Modify | In `get_layer_surface()`, `if tile_data.frames: continue` to leave animated tiles out of the cache. |
| `src/map/manager.py` | Modify | Add `get_visible_animated_chunks()` generator, yielding only animated tiles within viewport. |

- **Dependencies:** Step 1.
- **Risks:** M (Medium) - XML ElementTree `findall` syntax. Mitigation: Precise XML pathing inside TSX loading. Map caching must correctly leave transparent holes.
- **Tests:** `TC-001`.
- **Acceptance Criteria:** Loading a map with water results in the water disappearing completely (transparent holes) since it's no longer baked into the static surface. No errors thrown.

---

### Step 4: Dynamic Batch Rendering
*Renders the animated tiles on the fly without tanking performance.*

**Files:**
| File | Action | Description |
|------|--------|-------------|
| `src/engine/game.py` | Modify | In `_draw_scene()` Pass 0, after `layer_surface` blit, iterate `get_visible_animated_chunks`. |
| `src/engine/game.py` | Modify | Apply modulo time logic (`pygame.time.get_ticks()`) to determine the active frame GID. Guard against negative/zero total duration. |

- **Dependencies:** Step 3.
- **Risks:** H (High) - Rendering a loop every frame can destroy FPS. Mitigation: Generator uses the exact same O(1) frustum culling boundaries as `get_visible_chunks`.
- **Tests:** `IT-002`, `IT-003`.
- **Acceptance Criteria:** Water tiles appear and animate synchronously every 150ms. FPS remains at 60.

## 4. Test Strategy Summary
- Unit tests (`tests/map/test_parser.py`, `tests/map/test_manager.py`) to verify `TileMapData` fields and logic.
- Integration tests (`tests/engine/test_game.py`) to verify `start_move` interception and rendering.
- `verify.py` will be run after all steps to guarantee zero regressions.
