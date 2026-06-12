# Specification: Stair Movement Mechanics

> Document type: Implementation

**Covers:** Stair Movement Feature — horizontal stairs (lateral stairs).
**Future extension:** This architecture also supports ladders (`ladder`) via the same Tiled class.
**Revision:** v4 — post adversarial review corrections 2026-06-10.

---

## Constraints

| Tier | Examples |
|------|----------|
| **Always do** | Run tests before committing. Validate `MapManager` property lookups gracefully (bounds check). |
| **Ask first** | Changing existing `get_direction_flags` signature. Changing `TileMapData` fields. |
| **Never do** | Modify `self.rect` for visual offsets. Reuse the `direction` property name for stair direction (collision with `direction_flags` system). Remove existing collision logic in `BaseEntity`. |

## Cross-Spec Contracts

### Produces

| Artifact | Type | Consumers |
|----------|------|---------------|
| `MapManager.get_vertical_move_props(tx, ty) → dict \| None` | New method | map-world-system, npc-system |
| `BaseEntity._vertical_move: dict \| None` | New field | camera-rendering |
| `BaseEntity.current_stair_offset: float` | New field | camera-rendering |
| `BaseEntity.stair_start_offset: float` | New field | entities-system |
| `BaseEntity.stair_target_offset: float` | New field | entities-system |
| `BaseEntity.stair_move_distance: float` | New field | entities-system |
| `BaseEntity.update_stair_offset()` | New method | entities-system |
| `VERTICAL_MOVE_MAP` | New constant | engine-core |

### Consumes

| Artifact | Source | Usage |
|----------|--------|-------|
| `MapManager.tiles[id].properties` | map-world-system | Reads `stair_direction` in `get_vertical_move_props` |
| `BaseEntity.start_move()` | entities-system | Insertion point for stair interception and offset setup |
| `BaseEntity.update()` | entities-system | Insertion point for offset interpolation |
| `CameraGroup.custom_draw()` | camera-rendering | Insertion point for `current_stair_offset` |
| `MapManager.get_direction_flags()` | map-world-system | Called AFTER interception (critical order) |

### Public Interface

| Interface | Signature | Contract |
|-----------|-----------|--------|
| `get_vertical_move_props` | `(tx: int, ty: int) → dict \| None` | Returns `{stair_direction, movement_type, visual_y_offset}` or `None` |
| `_vertical_move` | `dict \| None` | Updated in `start_move()` only. |
| `current_stair_offset` | `float` | Read in `custom_draw()`. Interpolated during entity movement. |
| `VERTICAL_MOVE_MAP` | `dict[tuple[tuple[int,int], str], tuple[int,int]]` | 4 mappings (input_dir, stair_dir) → intercepted_dir |



---

## 0. Tiled Configuration — Class `01-vertical-move`

### 0.1 Why a Dedicated Class

**Name collision issue (VERIFIED in code):** The parser `tmj_parser.py` (L307-308) uses `props["direction"]` to build `direction_flags` — the system that controls which exit directions are allowed on a tile. Placing `direction="right"` on a stair tile would be interpreted as "block all movement except to the right", completely breaking movement logic.

**Solution:** The Tiled class `01-vertical-move` with a `stair_direction` field (distinct name) replaces `01-tileset_ground` for vertical movement tilesets.

### 0.2 Definition of the Tiled Class `01-vertical-move` (IMPLEMENTED)

Present in `game.tiled-project` (id=24):

```json
{
    "id": 24,
    "members": [
        {"name": "depth",          "type": "int",    "value": 0},
        {"name": "material",       "type": "string", "value": ""},
        {"name": "movement_type",  "propertyType": "25-movement_type", "type": "string", "value": "stair"},
        {"name": "stair_direction","propertyType": "23-direction",     "type": "string", "value": ""},
        {"name": "stair_half",     "type": "string", "value": ""},
        {"name": "visual_y_offset","type": "int",    "value": 0},
        {"name": "walkable",       "type": "bool",   "value": true}
    ],
    "name": "01-vertical-move",
    "type": "class"
}
```

**Fields:**
- `stair_direction` (enum `23-direction`, **default `""`**): `"right"` = staircase ascending to the right, `"left"` = ascending to the left. **Default empty = neutral tile, not a staircase.** Never `"any"` on a stair tile.
- `stair_half` (string, **default `""`**): `"bottom"` = bottom half of the step, `"top"` = top half of the step. Critical for determining when the diagonal physical movement is applied.
- `movement_type` (enum `25-movement_type`, default `"stair"`): `"stair"` | `"ladder"` — for future extension.
- `visual_y_offset` (int, default `0`): visual Y offset in pixels when rendering on this tile. Usually `-16` for bottom tiles and `0` for top tiles.
- `walkable` (bool, default `true`): `false` on wall tiles. Managed by the existing `is_walkable()` system.
- `depth` (int, default `0`): rendering depth, identical to `00-tileset`.
- `material` (string, default `""`): material for footstep sounds.

### 0.3 Application in `01-stairs.tsx` (VERIFIED — audit 2026-06-10)

**Actual Parser Behavior (VERIFIED — tmj_parser.py L295-298):**
The tileset has `class="01-vertical-move"` in its XML attribute, but the parser (`_parse_tileset_properties`) does NOT resolve Tiled classes via `TiledProject.resolve()` for tilesets (only for objects, L108). It only reads the XML `<properties>` nodes of the TSX — and `01-stairs.tsx` does NOT have them at the tileset level.

**Consequence:** `tileset_props = {}`. Only explicitly overridden properties per tile (`<property>` nodes inside `<tile>`) appear in `tile.properties`. Class defaults (`movement_type`, `visual_y_offset`) are **absent**.

Actual result in `tile.properties`:

```python
# Right step tile (e.g. id 0)
{
    "walkable": True,            # hardcoded fallback (_parse_tile_properties_and_anims L241)
    "depth": 0,                  # hardcoded fallback (L242)
    "direction": "any",          # hardcoded fallback (L243)
    "material": "stone",         # explicit override in TSX
    "stair_direction": "right",  # explicit override in TSX
    # ⚠️ "movement_type" and "visual_y_offset" are ABSENT
}

# Neutral / empty tile (e.g. id 4) — no <tile> node in TSX
{
    "walkable": True,            # hardcoded fallback (_process_single_tile L297)
    "depth": 0,                  # hardcoded fallback (L298)
    # ⚠️ "stair_direction" is ABSENT → get_vertical_move_props returns None ✅
}
```

**Impact on `get_vertical_move_props`:** The method handles absence via default values:
- `props.get("movement_type", "stair")` → returns `"stair"` ✅
- `int(props.get("visual_y_offset", -12))` → returns `-12` ✅

These hardcoded fallbacks **must match** the defaults of the Tiled class `01-vertical-move`. If the Tiled defaults change, the fallbacks must be updated.

**Complete tile inventory (VERIFIED):**

| Tile(s) | Role | `walkable` | Explicit Overrides |
|---------|------|-----------|--------------------|
| Right steps | 🪜 Right steps | `True` | `stair_direction="right"`, `stair_half` (`"bottom"` or `"top"`), `visual_y_offset` (`-16` or `0`) |
| Left steps | 🪜 Left steps | `True` | `stair_direction="left"`, `stair_half` (`"bottom"` or `"top"`), `visual_y_offset` (`-16` or `0`) |
| 2, 7, 13 | 🧱 Staircase walls | `False` | None (inherited — ignored because non-walkable) |
| Neutral | ⬜ Neutral / empty | `True` | None (inherited — not a staircase) |

**Staircase detection rule in the code:**
`stair_direction` is non-empty AND not None → stair tile.
`stair_direction == ""` → neutral tile, `get_vertical_move_props` returns `None`.

### 0.4 Stair Wall Detection

Wall detection uses the existing `is_walkable()` system in `MapManager`. Tiles with `walkable=false` (ids 2, 7, 13) block movement via `walkable_func` in `start_move`. No additional properties are needed for walls: the existing system is sufficient.

### 0.5 Parser Limitation — TSX Class Resolution

The parser `tmj_parser.py` does NOT resolve the `class=` attribute on tilesets via `TiledProject.resolve()`. Un-overridden class properties (`movement_type`, `visual_y_offset`) are not available in `tile.properties`.

**Adopted Strategy:** Rather than modifying the parser (which would impact all tilesets), the `get_vertical_move_props` method uses **hardcoded default values** that match the Tiled class defaults:

| Property | Tiled Class Default | Fallback in `get_vertical_move_props` | Matches? |
|-----------|--------------------|-----------------------------------------|--------------|
| `movement_type` | `"stair"` | `props.get("movement_type", "stair")` | ✅ |
| `visual_y_offset` | `-12` | `int(props.get("visual_y_offset", -12))` | ✅ |
| `stair_direction` | `""` | `props.get("stair_direction", "")` | ✅ |

**Risk:** If the Tiled defaults change, the fallbacks in the code must be updated manually. Accepted because the Tiled class is stable and the fallbacks are centralized in a single method.

---

## 1. Core Logic & Movement Interception

### 1.1 `VERTICAL_MOVE_MAP` Mapping Table (in `config.py`)

Replaces the hardcoded mapping in `start_move`. Add in `Settings` as a **class-level constant** — NOT loaded from `gameplay.json`. Add it directly at class body level, outside the `load()` method, alongside other constants like `TILE_SIZE`:

```python
# Maps (input_direction, stair_direction) → intercepted_direction
# Class-level constant — NOT a gameplay.json setting. Do NOT put in Settings.load().
VERTICAL_MOVE_MAP: dict[tuple[tuple[int, int], str], tuple[int, int]] = {
    ((1, 0), "right"):  (1, -1),   # Right on right staircase → diagonal climb
    ((-1, 0), "right"): (-1, 1),   # Left on right staircase → diagonal descent
    ((1, 0), "left"):  (1, 1),    # Right on left staircase → diagonal descent
    ((-1, 0), "left"):  (-1, -1),  # Left on left staircase → diagonal climb
    # Future extension:
    # ((0, 1), "up"): (0, 1),   # Up on ladder → vertical climb (same tile_size, inverted pygame Y)
}
```

### 1.2 `MapManager` — New Method `get_vertical_move_props`

```python
def get_vertical_move_props(self, tx: int, ty: int) -> dict | None:
    """
    Return vertical movement properties for the tile at (tx, ty), or None.

    Scans all layers at (tx, ty). Returns the first tile that has a
    'stair_direction' property (indicating a 25-vertical-move class tile).

    Returns:
        dict with keys 'stair_direction' (str), 'movement_type' (str),
        'visual_y_offset' (int) — or None if not a vertical-move tile.
    """
    if not (0 <= ty < self.height and 0 <= tx < self.width):
        return None

    for layer_id in reversed(self.layer_order):
        if layer_id not in self.layers:
            continue
        tile_id = self.layers[layer_id][ty][tx]
        if tile_id == 0 or tile_id not in self.tiles:
            continue
        tile = self.tiles[tile_id]
        props = tile.properties or {}
        stair_dir = props.get("stair_direction", "")
        if stair_dir:  # Non-empty string → explicit stair tile
            return {
                "stair_direction": stair_dir,
                "movement_type": props.get("movement_type", "stair"),
                "stair_half": props.get("stair_half", ""),
                "visual_y_offset": int(props.get("visual_y_offset", 0)),
            }
    return None  # "" or absent → neutral tile, not a stair
```

**Scan order:** reversed(layer_order) = top-to-bottom → the highest stair tile in the layer stack is returned.

### 1.3 `BaseEntity` — Interception logic & Step-Off Boundary Rule

**New attributes in `__init__`:**
```python
self._vertical_move: dict | None = None      # 25-vertical-move properties of current tile
self.current_stair_offset: float = 0.0      # Current visual Y offset applied during rendering
self.stair_start_offset: float = 0.0        # Visual Y offset at the beginning of the step
self.stair_target_offset: float = 0.0       # Visual Y offset at the target of the step
self.stair_move_distance: float = 0.0       # Total distance (in pixels) of the current step
```

**Symmetric Step-Off Interception in `start_move()`:**
The interception logic must verify the next tile in the input direction *before* intercepting.
1. Calculate the raw step direction from input (`dx`, `dy`) as discrete values (`-1`, `0`, or `1`).
2. Calculate the coordinates of the target tile if movement remained flat: `next_tx = current_tx + dx`, `next_ty = current_ty + dy`.
3. Query `get_vertical_move_props(next_tx, next_ty)`.
   - **Out-of-bounds edge case:** If `next_tx`/`next_ty` is outside the map bounds, `get_vertical_move_props` returns `None`. Treat this identically to a normal floor tile (step-off rule does NOT apply) — the walkability check at step 8 will block the out-of-bounds move.
4. If the entity is currently on a stair tile:
   - Calculate `should_move_diagonally` based on the current tile's `stair_half` ("bottom" or "top") and movement direction.
   - **2. Check Target Grid Tile**
   - After determining `target_dir` (which may be diagonal), check if the target tile `(current_tx + target_dir.x, current_ty + target_dir.y)` has stair properties via `get_vertical_move_props`.
   - **If the target tile is a stair tile**: Use `target_dir`.
   - **If the target tile is NOT a stair tile**: Bypass diagonal interception and force `target_dir = (dx, 0)`. This handles stepping off the bottom extremity orthogonally.

#### State Caching
When `start_move()` computes the final `target_pos` and verifies walkability:
1. Fetch `target_vm = get_vertical_move_props(target_tx, target_ty)`.
2. Cache `self._vertical_move = target_vm` for the duration of the move.
   - *Fix: This ensures that when the move completes and `is_moving` becomes `False`, the visual interpolation uses the correct target properties, preventing visual snapping at the extremities.*

5. If the entity is on a normal floor tile, no interception occurs (normal orthogonal entry).
6. Calculate `target_pos` and perform standard walkability checks.
7. Setup interpolation caching:
   - Calculate grid targets: `target_tx = int(self.target_pos.x // TILE_SIZE)` and `target_ty = int(self.target_pos.y // TILE_SIZE)`.
   - `self.stair_start_offset = self.current_stair_offset`
   - Query `target_vm = get_vertical_move_props(target_tx, target_ty)`.
   - `self._vertical_move = target_vm`
   - `self.stair_target_offset = target_vm["visual_y_offset"] if target_vm else 0.0`
   - `self.stair_move_distance = (self.target_pos - self.pos).magnitude()`

**Silent blocking — direction reset:** When an input direction has no entry in `VERTICAL_MOVE_MAP` (e.g., `(0, -1)` Up, or a diagonal), the interception logic returns early without setting `is_moving = True`. The caller (`Player.update()`) resets `direction` to `Vector2(0, 0)` after each frame when `is_moving` remains `False`. This reset is the responsibility of the caller, not of `start_move()` itself.

**Execution order in `start_move()` (CRITICAL):**
```
1. Calculate current_tx, current_ty
2. Calculate input dx, dy, and next flat coordinates: next_tx, next_ty
3. Query vertical move properties for current and next flat tiles
4. Determine intercepted direction (apply diagonal interception based solely on should_move_diagonally)
5. Check get_direction_flags (existing) — applies to the ALREADY intercepted direction
6. Calculate target_pos = self.pos + self.direction * TILE_SIZE
7. World boundary clamping (existing)
8. Check walkable_func (existing) — verifies walkability of target_pos
9. If target_pos != pos:
   - Set is_moving = True
   - Cache stair_start_offset, stair_target_offset, stair_move_distance
10. Call update_stair_offset() — MUST run AFTER move(dt) completes (including is_moving flag update)
```

---

### 1.4 Rendering & Offset Interpolation

To ensure smooth visual alignment and eliminate visual snaps, the visual Y offset is interpolated per-frame.

**Call Order in `BaseEntity.update(dt)` (CRITICAL):**
`update_stair_offset()` MUST be called AFTER `move(dt)` completes — including the `is_moving` flag update. Calling it before `move(dt)` causes the idle path to fire one frame early, producing a visual snap on step-off.

```python
def update(self, dt: float):
    self.move(dt)                 # ← runs first, updates is_moving flag
    self.update_stair_offset()    # ← runs second, reads the updated is_moving flag
```

**Offset Interpolation in `update_stair_offset(self)`:**
Add a method `update_stair_offset(self)` called in `update(self, dt)` **after** `move(dt)`:
```python
def update_stair_offset(self):
    if not self.is_moving:
        # Standing still: read cached _vertical_move (set by start_move).
        # NEVER call get_vertical_move_props here — per-frame property reads
        # violate Anti-Pattern #4. _vertical_move is already correct for the
        # current tile and is only updated at move boundaries.
        vm = self._vertical_move
        self.current_stair_offset = vm["visual_y_offset"] if vm else 0.0
    else:
        # Moving: interpolate offset based on movement progress
        total_dist = self.stair_move_distance
        if total_dist > 0:
            curr_dist = (self.target_pos - self.pos).magnitude()
            progress = max(0.0, min(1.0, 1.0 - curr_dist / total_dist))
            self.current_stair_offset = self.stair_start_offset + (self.stair_target_offset - self.stair_start_offset) * progress
        else:
            self.current_stair_offset = self.stair_target_offset
```

**Integration Point: `CameraGroup.custom_draw()`**

> ⛔ **DELETION REQUIRED:** Remove the existing `_vertical_move`-based stair Y-offset code from `custom_draw()` before adding the `current_stair_offset`-based offset. The old code reads `sprite._vertical_move` and applies a static offset — it must be fully deleted, not supplemented. Two parallel offset mechanisms would double-apply the visual offset.

Update rendering position calculation in `groups.py` to use `sprite.current_stair_offset` instead:
```python
# Modified code in CameraGroup.custom_draw
visual_rect = sprite.image.get_rect(bottomright=sprite.rect.bottomright)

# Dynamic stair visual offset (interpolated — replaces old _vertical_move-based offset)
stair_y_offset = getattr(sprite, 'current_stair_offset', 0.0)

offset_pos = (visual_rect.left + self.offset.x, visual_rect.top + self.offset.y + stair_y_offset)
# ... culling and drawing ...
```
This distributes the 12px visual offset change continuously over the duration of the 32px step, preventing sinking and floating bugs.


---

## 2. NPC Pathfinding

### 2.1 Compatibility with the Current System

The interception in `start_move()` applies to all `BaseEntity`s. If the NPC pathfinder generates tile-by-tile steps in the form of directional vectors like `(1,0)`, `(-1,0)`, etc. (which is the standard case), the interception automatically corrects them to diagonal when the entity is on a staircase.

**Requirement:** The pathfinder must operate in grid-steps (direction to the next tile), not direct pixel trajectories. If the pathfinder calculates a direct vector `(target_px - pos_px)`, it will bypass `start_move()` and the interception will not apply.

### 2.2 Diagonal Cost in the A\* Algorithm

If the pathfinder uses A\*, the cost of a stair tile must reflect the actual displacement:
- A diagonal step covers `√2 × TILE_SIZE` pixels but costs `1 tile` in grid time.
- If A\* calculates distances in tiles, staircases are transparent (identical cost).
- If A\* calculates distances in pixels, add a cost of `√2` for tiles with `stair_direction`.

**[Tiled Author Task]**: No additional configuration required at this stage if the pathfinder is grid-based. To be re-evaluated if NPCs bypass staircases.

### 2.3 Edge Case: NPC Arrives at Destination at Top of Staircase

If the NPC target is a tile beyond the top of the stairs, the NPC traverses normally via interception. If the target IS on the staircase, the NPC stops at the correct (grid-aligned) position.

---

## 3. Anti-Patterns

| # | Anti-Pattern | Why Incorrect | What to Do Instead |
|---|-------------|-----------|---------------------|
| 1 | Reusing `direction` for stair direction | `direction` is reserved for `direction_flags` (tmj_parser.py L307). Placing `direction="right"` would block all movement except to the right. | Use `stair_direction` exclusively. |
| 2 | Modifying `self.rect` for visual offset | Breaks collision physics. `rect` is used for grid positioning and collision detection. | Apply the offset only in `offset_pos` during `blit()` in `custom_draw()`. |
| 3 | Restricting interception to the Player | All `BaseEntity`s go through `start_move()`. Restricting to the Player would prevent NPCs from climbing stairs. | The interception in `start_move()` automatically applies to all entities. |
| 4 | Calling `get_vertical_move_props` in `update()` or `move()` | Creates a per-frame call instead of a per-movement call. Unnecessary performance impact. | A single read in `start_move()`, result stored in `self._vertical_move`. |
| 5 | Inferring a staircase from visual layers | Visual layers can contain decorations without stair properties. | Rely solely on `stair_direction` in `tile.properties`. |
| 6 | Checking `get_direction_flags` BEFORE stair interception | The intercepted (diagonal) direction would be checked against the source tile flags — risk of incorrect blocking. | Stair interception is always BEFORE `get_direction_flags` in `start_move()`. |
| 7 | Placing non-empty `stair_direction` on wall tiles | Tiles with `walkable=false` should not have a stair direction. | `walkable=false` blocks movement via `is_walkable()`. `stair_direction` remains empty on walls. |
| 8 | Assuming `movement_type`/`visual_y_offset` are in `tile.properties` | The parser does not resolve TSX classes (§0.5). These properties are absent unless explicitly overridden. | Use `props.get("movement_type", "stair")` and `props.get("visual_y_offset", -12)` with fallbacks. |

---

## 4. Error Handling Matrix

| Error State | Cause | Handling | Verification |
|-------------|-------|----------|--------------|
| Tile has no `stair_direction` property | Normal floor tile | `get_vertical_move_props` returns `None`. `self._vertical_move = None`. Movement normal. | VERIFIED (tmj_parser.py defaults) |
| `stair_direction` value not in `VERTICAL_MOVE_MAP` | Missing config or unhandled direction | `VERTICAL_MOVE_MAP.get()` returns `None`. `start_move` aborts the move, keeping `is_moving = False` and resetting direction. Silent blocking. | ASSUMED |
| `get_vertical_move_props` called out of bounds | tx/ty hors carte | Bounds check en tête of function → returns `None`. | SPECIFIED |
| Diagonal target not walkable | Target tile `walkable=False` | `walkable_func` resets `target_pos = self.pos`. Movement silently cancelled. | VERIFIED (base.py L101-104) |
| `self.game` or `map_manager` absent | Unit tests without context | Existing guard `hasattr(self.game, "map_manager")` → skip. | VERIFIED (base.py L69) |
| `movement_type` inconnu (ex: `"ladder"`) | Extension non implémentée | Traité identiquement à `"stair"` par `VERTICAL_MOVE_MAP` (même clé). Extension future. | ASSUMED |

---

## Assumptions

| # | Assumption | Risk | Source Type | Handling |
|---|-----------|--------|-------------|---------|
| A1 | `stair_direction` is in `tile.properties` for tiles with explicit override in the TSX | Low | SHOW | VERIFIED — all 18 stair tiles have an explicit `<property>` in the TSX |
| A2 | `movement_type` and `visual_y_offset` are absent from `tile.properties` (parser does not resolve TSX class) | Medium | SHOW | Managed via hardcoded fallbacks in `get_vertical_move_props` matching class defaults (§0.5) |
| A3 | The NPC pathfinder operates in grid-steps (direction to next tile), not direct pixel trajectory | Medium | SHOW | VERIFIED — npc.py L125-131 (process_ai) uses orthogonal unit vector choices. |
| A4 | `TileMapData.properties` (existing field, type `dict[str, Any] or None`) is the entry point. No schema modification of `TileMapData` is needed | Low | SHOW | VERIFIED — the field already exists (tmj_parser.py L20) |
| A5 | The visual offset is smoothly interpolated during movement to avoid sudden vertical snaps. | Low | SHOW | VERIFIED — simulation shows smooth transition without aesthetic discontinuity. |


---

## 5. Test Case Specifications

### Unit Tests (`game/tests/entities/test_stair_movement.py`)

**MapManager:**
- `UT-001`: `get_vertical_move_props(tx, ty)` returns `{"stair_direction": "right", "movement_type": "stair", "visual_y_offset": -12}` on mock tile with `stair_direction="right"`.
- `UT-002`: `get_vertical_move_props(tx, ty)` returns `None` on tile without `stair_direction`.
- `UT-003`: `get_vertical_move_props(-1, 0)` returns `None` (out of bounds — bounds check).
- `UT-004`: `get_vertical_move_props(tx, ty)` returns `None` on tile with `direction="right"` but without `stair_direction` (verifies no name collision).

**BaseEntity — start_move on right staircase (`stair_direction="right"`):**
- `UT-005`: Input `(1, 0)` → `direction` intercepted at `(1, -1)`, `target_pos` = `(pos.x+32, pos.y-32)`, `is_moving = True`.
- `UT-006`: Input `(-1, 0)` → `direction` intercepted at `(-1, 1)`, `target_pos` = `(pos.x-32, pos.y+32)`.
- `UT-007`: Input `(0, -1)` (Up) → `is_moving` remains `False`, `direction` reset to `(0, 0)`. Silent blocking.
- `UT-008`: Input `(1, 1)` (Unmapped diagonal) → `is_moving` remains `False`, `direction` reset to `(0, 0)`. Silent blocking (prevents diagonal exit).

**BaseEntity — start_move on left staircase (`stair_direction="left"`):**
- `UT-009`: Input `(-1, 0)` → direction intercepted at `(-1, -1)`, `target_pos` = `(pos.x-32, pos.y-32)`.
- `UT-010`: Input `(1, 0)` → direction intercepted at `(1, 1)`, `target_pos` = `(pos.x+32, pos.y+32)`.

**BaseEntity — transitions:**
- `UT-011`: Entity on normal floor → `_vertical_move` is `None`. Input `(1, 0)` → normal orthogonal movement `(pos.x+32, pos.y)`.
- `UT-012`: Entity leaves stair tile to normal floor → step-off rule preserves orthogonal target pos, and visual offset is smoothly interpolated from `-12` to `0` at the end of the move.
- `UT-013`: `walkable_func` returns `False` for diagonal target → `target_pos` = `pos`, `is_moving = False` (staircase blocked by wall).

**Rendering offset & Interpolation:**
- `UT-014`: Interpolation updates `current_stair_offset` smoothly during movement (e.g. at progress = 50%, offset is halfway between start and target offsets).
- `UT-015`: `CameraGroup.custom_draw()` applies `current_stair_offset` to render coordinates instead of static properties.


**VERTICAL_MOVE_MAP (config):**
- `UT-016`: `VERTICAL_MOVE_MAP[((1, 0), "right")] == (1, -1)` — verifies table correctness for all 4 combinations.

### Integration Tests (`game/tests/integration/test_stairs_integration.py`)

- `IT-001`: Load mini-map with a `stair_direction="right"` tile. Spawn player on it. Input Right. Assert `pos == (initial.x + 32, initial.y - 32)` and `is_moving = False` (movement completed).
- `IT-002`: Same setup. Assert `_vertical_move["visual_y_offset"] == -12` during movement, then `_vertical_move = None` after reaching a floor tile.
- `IT-003`: Mini-map with 3 consecutive stair tiles (`stair_direction="right"`). Player traverses the 3 tiles with repeated Right inputs. Assert that final position is `(x + 96, y - 96)` (3 × diagonal).
- `IT-004`: Mini-map with staircase surrounded by walls (`walkable=False`). Input Up on stair tile → `is_moving = False`. Input Down → `is_moving = False`.
- `IT-005`: NPC with pathfinding to a tile beyond a staircase. Assert that the NPC traverses the staircase diagonally (via the `start_move()` interception) without getting stuck.
- `IT-006`: Tile with `direction="right"` (without `stair_direction`) → `get_vertical_move_props` returns `None`. No interception. Verifies isolation of the `direction_flags` system.

---

## 6. Deep Links

- `MapManager`: [game/src/map/manager.py#L1](file:///Users/adrien.parasote/Documents/perso/game/game/src/map/manager.py#L1) — `get_direction_flags` (L119), new `get_vertical_move_props`
- `BaseEntity`: [game/src/entities/base.py#L1](file:///Users/adrien.parasote/Documents/perso/game/game/src/entities/base.py#L1) — `start_move()` (L62), new `_vertical_move`
- `CameraGroup.custom_draw`: [game/src/entities/groups.py#L94](file:///Users/adrien.parasote/Documents/perso/game/game/src/entities/groups.py#L94) — rendering y_offset integration point (L121-129)
- `TmjParser._parse_tileset_properties`: [game/src/map/tmj_parser.py#L189](file:///Users/adrien.parasote/Documents/perso/game/game/src/map/tmj_parser.py#L189) — reads XML `<properties>` (does NOT resolve `class=`)
- `TmjParser._parse_tile_properties_and_anims`: [game/src/map/tmj_parser.py#L230](file:///Users/adrien.parasote/Documents/perso/game/game/src/map/tmj_parser.py#L230) — walkable/depth/direction fallbacks (L241-243)
- `TmjParser._process_single_tile`: [game/src/map/tmj_parser.py#L276](file:///Users/adrien.parasote/Documents/perso/game/game/src/map/tmj_parser.py#L276) — `direction_flags` construction from `props["direction"]` (L307-308)
- `Settings` (config): [game/src/config.py#L1](file:///Users/adrien.parasote/Documents/perso/game/game/src/config.py#L1) — `VERTICAL_MOVE_MAP`
- Stair tileset: [assets/tiled/tiles/01-stairs.tsx#L1](file:///Users/adrien.parasote/Documents/perso/game/assets/tiled/tiles/01-stairs.tsx#L1) — `class="01-vertical-move"`, 36 tiles
- Tiled Project (classes): [assets/tiled/game.tiled-project#L1](file:///Users/adrien.parasote/Documents/perso/game/assets/tiled/game.tiled-project#L1) — class `01-vertical-move` (id=24)

## Project Deliverables Tree
```text
├── camera-rendering.md
├── game/tests/entities/test_stair_movement.py
└── game/tests/integration/test_stairs_integration.py
```
