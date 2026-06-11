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

## Produces

| Artifact | Type | Consumers |
|----------|------|---------------|
| `MapManager.get_vertical_move_props(tx, ty) → dict \| None` | New method | map-world-system, npc-system |
| `BaseEntity._vertical_move: dict \| None` | New field | camera-rendering |
| `VERTICAL_MOVE_MAP` | New constant | engine-core |

## Consumes

| Artifact | Source | Usage |
|----------|--------|-------|
| `MapManager.tiles[id].properties` | map-world-system | Reads `stair_direction` in `get_vertical_move_props` |
| `BaseEntity.start_move()` | entities-system | Insertion point for stair interception |
| `CameraGroup.custom_draw()` | camera-rendering | Insertion point for `visual_y_offset` |
| `MapManager.get_direction_flags()` | map-world-system | Called AFTER interception (critical order) |

## Public Interface

| Interface | Signature | Contract |
|-----------|-----------|--------|
| `get_vertical_move_props` | `(tx: int, ty: int) → dict \| None` | Returns `{stair_direction, movement_type, visual_y_offset}` or `None` |
| `_vertical_move` | `dict \| None` | Updated in `start_move()` only. Read in `custom_draw()` |
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
        {"name": "visual_y_offset","type": "int",    "value": -12},
        {"name": "walkable",       "type": "bool",   "value": true}
    ],
    "name": "01-vertical-move",
    "type": "class"
}
```

**Fields:**
- `stair_direction` (enum `23-direction`, **default `""`**): `"right"` = staircase ascending to the right, `"left"` = ascending to the left. **Default empty = neutral tile, not a staircase.** Never `"any"` on a stair tile.
- `movement_type` (enum `25-movement_type`, default `"stair"`): `"stair"` | `"ladder"` — for future extension.
- `visual_y_offset` (int, default `-12`): visual Y offset in pixels when rendering on this tile. Adjustable per tileset.
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

| Tile(s) | Role | `walkable` | `stair_direction` |
|---------|------|-----------|------------------|
| 0, 6, 12, 18, 19, 24, 25, 30, 31 | 🪜 Right steps | `True` | `"right"` (explicit override) |
| 1, 8, 14, 20, 21, 26, 27, 32, 33 | 🪜 Left steps | `True` | `"left"` (explicit override) |
| 2, 7, 13 | 🧱 Staircase walls | `False` | `""` (inherited — ignored because non-walkable) |
| 3, 4, 5, 9, 10, 11, 15, 16, 17, 22, 23, 28, 29, 34, 35 | ⬜ Neutral / empty | `True` | `""` (inherited — not a staircase) |

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

Replaces the hardcoded mapping in `start_move`. To add in `Settings`:

```python
# Maps (input_direction, stair_direction) → intercepted_direction
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
                "visual_y_offset": int(props.get("visual_y_offset", -12)),
            }
    return None  # "" or absent → neutral tile, not a stair
```

**Scan order:** reversed(layer_order) = top-to-bottom → the highest stair tile in the layer stack is returned.

### 1.3 `BaseEntity` — `_vertical_move` Flag and Modification of `start_move()`

**New field in `__init__`:**
```python
self._vertical_move: dict | None = None  # 25-vertical-move properties of current tile
```

**Execution order in `start_move()` (CRITICAL — stair interception must be BEFORE `get_direction_flags`):**

```
1. Calculate current_tx, current_ty
2. ── [NEW] ── Query get_vertical_move_props(current_tx, current_ty)
   a. If the tile is a staircase:
      - If input_dir == (0, 0): let it pass
      - Else: lookup VERTICAL_MOVE_MAP[(input_dir, stair_direction)]
        → If mapping found: replace self.direction with the intercepted direction
        → If no mapping: reset direction + return (complete silent blocking of all unmanaged input, including diagonals)
      - Update self._vertical_move with the properties
   b. Else (normal floor): self._vertical_move = None
3. Check get_direction_flags (existing) — applies to the ALREADY intercepted direction
4. Calculate target_pos = self.pos + self.direction * TILE_SIZE (direction can be diagonal)
5. World boundary clamping (existing)
6. Check walkable_func (existing) — verifies the target diagonal tile
7. Set is_moving = True
```

**Why interception is BEFORE `get_direction_flags`:** The `get_direction_flags` check uses the requested direction to decide if movement is allowed. If we verify `"right"` against the flags of a stair tile, and the tile has `direction="any"` (default), it passes. If the order were reversed, a stair tile with restrictive flags would block before interception.

### 1.4 Rendering — `visual_y_offset` via Flag (NOT per Frame)

**Resolved Anti-Pattern:** The previous section said "update per frame". This is incorrect and contradicts Anti-Pattern #4.

**Definitive Rule:** `self._vertical_move` is updated ONLY in `start_move()` (once per movement). The renderer reads `self._vertical_move["visual_y_offset"]` if non-None, otherwise 0.

**Integration Point: `CameraGroup.custom_draw()`** ([groups.py#L94](file:///Users/adrien.parasote/Documents/perso/game/game/src/entities/groups.py#L94))

The modification is done in the `custom_draw()` method of `CameraGroup`, which owns the entity rendering pipeline (see `camera-rendering.md`). The current code (L124-129):

```python
# Current code (groups.py L121-129)
visual_rect = sprite.image.get_rect(bottomright=sprite.rect.bottomright)
offset_pos = visual_rect.topleft + self.offset
# ... culling ...
surface.blit(sprite.image, offset_pos)
```

Modification to apply — adding the `y_offset` to `offset_pos`:

```python
# Modified code
visual_rect = sprite.image.get_rect(bottomright=sprite.rect.bottomright)

# ── [NEW] ── Stair visual offset
stair_y_offset = 0
vm = getattr(sprite, '_vertical_move', None)
if vm is not None:
    stair_y_offset = vm["visual_y_offset"]

offset_pos = (visual_rect.left + self.offset.x, visual_rect.top + self.offset.y + stair_y_offset)
# ... culling with offset_pos ...
surface.blit(sprite.image, offset_pos)
```

**Note:** `sprite.rect` is NOT modified. Collision physics remain intact. `getattr` with a fallback of `None` ensures compatibility with sprites that do not have `_vertical_move` (obstacles, decorations).

**Assumed Limitation (Visual Snap):** Since `_vertical_move` is updated at the start of the movement based on the source tile, the `y_offset` is applied in a binary fashion. When an entity starts walking from the floor to a staircase, it has no offset. When it stops on the staircase and begins its next step, the offset of `-12` s applies at once, creating a visual "snap" of 12 pixels upwards. The reverse occurs when exiting the staircase. This aesthetic discontinuity is accepted for this version to avoid complex per-frame interpolation calculations.

**stair→floor transition:** When the entity arrives on a normal tile and starts its next movement, `start_move()` sets `self._vertical_move = None` → `stair_y_offset = 0` instantaneously in the next render.

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
| `stair_direction` value not in `VERTICAL_MOVE_MAP` | Missing config or unhandled direction | `start_move` lets it pass without interception (normal orthogonal movement). Log WARNING. | ASSUMED |
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
| A5 | The visual "snap" of 12 pixels during floor ↔ staircase transition is aesthetically acceptable for now, avoiding rendering complexity with interpolation. | Medium | TELL | Assumed tolerance. Documented in §1.4. |

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
- `UT-012`: Entity leaves stair tile to normal floor → `_vertical_move` is `None` after `start_move()`. Visual offset = 0.
- `UT-013`: `walkable_func` returns `False` for diagonal target → `target_pos` = `pos`, `is_moving = False` (staircase blocked by wall).

**Rendering offset:**
- `UT-014`: `_vertical_move = {"visual_y_offset": -12, ...}` → `draw_pos.y = entity.rect.y - 12`. `entity.rect.y` unchanged.
- `UT-015`: `_vertical_move = None` → `draw_pos.y = entity.rect.y` (no offset).

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
