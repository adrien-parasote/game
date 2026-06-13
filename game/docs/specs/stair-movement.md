# Specification: Stair Movement Mechanics

> Document type: Implementation

**Covers:** Stair Movement Feature — horizontal stairs (lateral stairs).
**Future extension:** This architecture also supports ladders (`ladder`) via the same Tiled class.
**Revision:** v6 — Added dynamic stair clipping per ADR-015 (2026-06-13).

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
| `BaseEntity.current_stair_clip: float` | New field | camera-rendering |
| `BaseEntity.stair_start_clip: float` | New field | entities-system |
| `BaseEntity.stair_target_clip: float` | New field | entities-system |
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
| `get_vertical_move_props` | `(tx: int, ty: int) → dict \| None` | Returns `{stair_direction, movement_type, stair_half, visual_y_offset, stair_clip}` or `None` |
| `_vertical_move` | `dict \| None` | Updated in `start_move()` only. |
| `current_stair_offset` | `float` | Read in `custom_draw()`. Interpolated during entity movement. |
| `current_stair_clip` | `float` | Read in `custom_draw()`. Interpolated during entity movement to dynamically clip the sprite. |
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
        {"name": "stair_clip",     "type": "bool",   "value": false},
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
- `stair_clip` (bool, **default `false`**): `true` = this tile clips the bottom half of the sprite when walked on, simulating depth.
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
- `int(props.get("visual_y_offset", 0))` → returns `0` ✅

These hardcoded fallbacks **must match** the defaults of the Tiled class `01-vertical-move`. If the Tiled defaults change, the fallbacks must be updated.

**Complete tile inventory (VERIFIED):**

| Tile(s) | Role | `walkable` | `stair_clip` | Explicit Overrides |
|---------|------|-----------|------------|--------------------|
| Right steps (upper-half view, e.g. IDs 16, 35) | 🪜 Right steps — depth view | `True` | `true` — clips player's lower half to simulate depth | `stair_direction="right"`, `stair_half`, `visual_y_offset`, `stair_clip=true` |
| Right steps (lower-half / entry tiles) | 🪜 Right steps — flat approach | `True` | `false` (default) | `stair_direction="right"`, `stair_half`, `visual_y_offset` |
| Left steps (upper-half view) | 🪜 Left steps — depth view | `True` | `true` | `stair_direction="left"`, `stair_half`, `visual_y_offset`, `stair_clip=true` |
| Left steps (lower-half / entry tiles) | 🪜 Left steps — flat approach | `True` | `false` (default) | `stair_direction="left"`, `stair_half`, `visual_y_offset` |
| 2, 7, 13 | 🧱 Staircase walls | `False` | `false` (irrelevant — non-walkable) | None |
| Neutral | ⬜ Neutral / empty | `True` | `false` (default) | None |

**`stair_clip=true` rule:** Apply to tiles where the player's lower body should disappear behind the stair face. These are the "side-view" tiles where the stair geometry is visually above the player's feet position.

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
| `visual_y_offset` | `0` | `int(props.get("visual_y_offset", 0))` | ✅ |
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
                "stair_half": bool(props.get("stair_half", False)),
                "visual_y_offset": int(props.get("visual_y_offset", 0)),
                "stair_clip": bool(props.get("stair_clip", False)),
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
self.stair_start_pos: pygame.math.Vector2   # World position at the start of the current step (interpolation anchor)
self.current_stair_clip: float = 0.0        # Current visual clip applied during rendering
self.stair_start_clip: float = 0.0          # Visual clip at the beginning of the step
self.stair_target_clip: float = 0.0         # Visual clip at the target of the step
self.stair_move_distance: float = 0.0       # Total distance (in pixels) of the current step (kept for API compat)
```

> **Implementation note:** `stair_start_pos` is set in `start_move()` to `pygame.math.Vector2(self.pos)` before movement begins. `update_stair_offset()` uses `(self.target_pos - self.stair_start_pos).magnitude()` as the total step distance denominator (equivalent to `stair_move_distance` but avoids floating-point drift). Initialize `stair_start_pos` in `__init__` to `pygame.math.Vector2(pos)`.

**New private helper `_max_stair_clip(self) → float`:**
```python
def _max_stair_clip(self) -> float:
    """Return maximum clip amount for this entity.

    Returns float(Settings.TILE_SIZE // 2) (16.0) for all sprites, since
    the visual step geometry is fixed at 16px. Never uses sprite height
    proportional clipping, as that would cause visual gaps (floating torso
    artifacts) for taller sprites (e.g. 48px or 64px tall).
    """
    return float(Settings.TILE_SIZE // 2)
```

**Usage:** Call `self._max_stair_clip()` in `start_move()` and `update_stair_offset()` instead of inline `else 16`.

**Symmetric Step-Off Interception in `start_move()`:**
The interception logic must verify the next tile in the input direction *before* intercepting.
1. Calculate the raw step direction from input (`dx`, `dy`) as discrete values (`-1`, `0`, or `1`).
2. If the input has no entry in `VERTICAL_MOVE_MAP` (e.g. `(0, -1)` Up), silently block: reset `direction` to `(0, 0)`, return `False`.
3. If the entity is currently on a stair tile, determine `should_move_diagonally`:

   **Decision rule — `should_move_diagonally` (EXACT, sourced from `01-stairs.tsx` and ADR-013):**

   The TSX exposes a boolean property `stair_half` on each walkable stair tile:
   - `stair_half = True` → the tile is the **upper half** of a step (requires diagonal movement to reach the next Y level).
   - `stair_half = False` / absent → the tile is the **lower half** of a step (movement stays flat to step off, or player is at the bottom entry).

   ```python
   stair_half = vm.get("stair_half", False)   # bool, from tile props
   # is_going_up uses domain semantics: right direction on right staircase = ascending;
   # left direction on left staircase = ascending. This is equivalent to
   # intercepted_dir[1] < 0 for the current VERTICAL_MOVE_MAP, but stated explicitly
   # to remain correct if the map is extended with non-obvious entries.
   # ⚠️ WARNING: if VERTICAL_MOVE_MAP gains a case where right+right_stair = descending,
   # this formula must be updated. Use intercepted_dir[1] < 0 as the canonical truth.
   is_going_up = (stair_dir == "right" and dx == 1) or (stair_dir == "left" and dx == -1)
   # For ascending: diagonal on upper-half tile
   # For descending: diagonal on lower-half tile (= full tile in descent direction)
   should_move_diagonally = stair_half if is_going_up else (not stair_half)
   ```

   No `tile_id % N` arithmetic. No parity checks. **Only `stair_half` and direction.**

4. Apply direction:
   - If `should_move_diagonally`: `target_dir = VERTICAL_MOVE_MAP[map_key]` (diagonal).
   - If not: `target_dir = (dx, 0)` (flat).

5. **Step-off boundary rule (target grid check):**
   - After computing `target_dir`, check if the target tile `(current_tx + target_dir[0], current_ty + target_dir[1])` has stair properties via `get_vertical_move_props`.
   - **If the target tile is NOT a stair tile**: force `target_dir = (dx, 0)`. This handles stepping off the top extremity onto a flat floor tile.

#### State Caching
When `start_move()` computes the final `target_pos` and verifies walkability:
1. Fetch `target_vm = get_vertical_move_props(target_tx, target_ty)`.
2. Cache `self._vertical_move = target_vm` for the duration of the move.
   - This ensures the visual interpolation uses the correct target properties, preventing visual snapping at the extremities.

5. If the entity is on a normal floor tile, no interception occurs (normal orthogonal entry).
6. Calculate `target_pos` and perform standard walkability checks.
7. Setup interpolation caching:
   - Calculate grid targets: `target_tx = int(self.target_pos.x // TILE_SIZE)` and `target_ty = int(self.target_pos.y // TILE_SIZE)`.
   - `self.stair_start_offset = self.current_stair_offset`
   - `self.stair_start_clip = self.current_stair_clip`
   - Query `target_vm = get_vertical_move_props(target_tx, target_ty)`.
   - `self._vertical_move = target_vm`
   - `self.stair_target_offset = target_vm["visual_y_offset"] if target_vm else 0.0`
   - `max_clip = self._max_stair_clip()`  ← uses helper; never hardcodes pixel value
   - `self.stair_target_clip = max_clip if target_vm and target_vm.get("stair_clip") else 0.0`
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
        
        max_clip = self._max_stair_clip()  # half sprite height, or TILE_SIZE//2 if no image yet
        self.current_stair_clip = max_clip if vm and vm.get("stair_clip") else 0.0
    else:
        # Moving: interpolate offset based on movement progress
        total_dist = self.stair_move_distance
        if total_dist > 0:
            curr_dist = (self.target_pos - self.pos).magnitude()
            progress = max(0.0, min(1.0, 1.0 - curr_dist / total_dist))
            self.current_stair_offset = self.stair_start_offset + (self.stair_target_offset - self.stair_start_offset) * progress
            self.current_stair_clip = self.stair_start_clip + (self.stair_target_clip - self.stair_start_clip) * progress
        else:
            self.current_stair_offset = self.stair_target_offset
            self.current_stair_clip = self.stair_target_clip
```

**Integration Point: `CameraGroup.custom_draw()`**

> ⛔ **DELETION REQUIRED:** Remove the existing `_vertical_move`-based stair Y-offset code from `custom_draw()` before adding the `current_stair_offset`-based offset. The old code reads `sprite._vertical_move` and applies a static offset — it must be fully deleted, not supplemented. Two parallel offset mechanisms would double-apply the visual offset.

**Combined clip + offset design intent:**
- `stair_y_offset` shifts the entire sprite image **up/down in screen space**, correcting grid alignment for diagonal steps. Example: `-16` moves the sprite 16px higher on screen.
- `stair_clip` removes pixels from the **image bottom** (image-space), hiding the player's lower body behind the stair face.
- These two effects are **independent by design** and tuned per tile: the offset aligns the sprite to the grid; the clip creates the depth illusion. Both non-zero simultaneously is the normal case on `stair_clip=true` tiles.
- Visual contract: after applying both, the player's visible bottom on screen is `offset_pos.y + (image_height - stair_clip)`. Tiles must be authored so this aligns with the visual stair face.

**Complete replacement for the drawing body in `CameraGroup.custom_draw()` (replaces L109-L143 of groups.py):**
```python
# Align bottom-right of sprite image to bottom-right of logical hitbox
visual_rect = sprite.image.get_rect(bottomright=sprite.rect.bottomright)

# Dynamic stair visual offset (interpolated — replaces old _vertical_move-based offset)
stair_y_offset = getattr(sprite, 'current_stair_offset', 0.0)
if not isinstance(stair_y_offset, int | float):
    stair_y_offset = 0.0

offset_pos = (visual_rect.left + self.offset.x, visual_rect.top + self.offset.y + stair_y_offset)

# Frustum culling — MUST occur BEFORE composition to avoid allocating a surface for off-screen sprites
screen_sprite_rect = pygame.Rect(offset_pos, visual_rect.size)
if not screen_rect.colliderect(screen_sprite_rect):
    continue

# Dynamic clipping via Composition (only when sprite is in the clip zone)
stair_clip = int(getattr(sprite, 'current_stair_clip', 0.0))
if stair_clip > 0:
    # 1. Create a transparent surface of the same dimensions (preserves size for occlusion logic)
    clipped_image = pygame.Surface(sprite.image.get_size(), pygame.SRCALPHA)
    # 2. Blit the original image at origin
    clipped_image.blit(sprite.image, (0, 0))
    # 3. Clear the bottom `stair_clip` pixels — BLEND_RGBA_MIN with (0,0,0,0) zeroes all channels
    clip_rect = pygame.Rect(0, clipped_image.get_height() - stair_clip, clipped_image.get_width(), stair_clip)
    clipped_image.fill((0, 0, 0, 0), clip_rect, special_flags=pygame.BLEND_RGBA_MIN)
    surface.blit(clipped_image, offset_pos)
else:
    surface.blit(sprite.image, offset_pos)

# Debug Hitbox Rendering
if Settings.DEBUG:
    debug_rect = sprite.rect.move(self.offset.x, self.offset.y)
    try:  # noqa: SIM105
        pygame.draw.rect(surface, (255, 0, 0), debug_rect, 1)
    except TypeError:
        # Fallback for mock surfaces in tests where pygame.draw.rect fails
        pass
```
This distributes both the Y-offset and the clip continuously over the duration of each step, preventing sinking, floating, and sudden-reveal bugs.


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

### 2.4 NPC Sprite Clipping on `stair_clip` Tiles

Because `update_stair_offset()` runs on all `BaseEntity`s, NPCs walking over a `stair_clip=true` tile will also have their lower half clipped. **This is intentional** — it preserves visual consistency between the player and NPCs traversing the same staircase geometry.

If a specific NPC type should NOT be clipped (e.g. a floating ghost), add an opt-out attribute to that entity subclass:
```python
# In the entity subclass __init__:
self.stair_clip_exempt: bool = True
```
Then guard in `update_stair_offset()`:
```python
if getattr(self, 'stair_clip_exempt', False):
    self.current_stair_clip = 0.0
    return
```
**Default:** all entities are clipped. `stair_clip_exempt` is opt-in, not opt-out.

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
| 8 | Assuming `movement_type`/`visual_y_offset` are in `tile.properties` | The parser does not resolve TSX classes (§0.5). These properties are absent unless explicitly overridden. | Use `props.get("movement_type", "stair")` and `props.get("visual_y_offset", 0)` with fallbacks. |
| 9 | Using `subsurface` for clipping rendering | Modifying the surface dimensions breaks alignment logic and occlusion culling checks. | Use Composition: render original to a transparent surface, fill bottom with transparent color, then blit. |

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
| A6 | `sprite.image` supports per-pixel alpha (`SRCALPHA`) when `stair_clip > 0` — required for `BLEND_RGBA_MIN` to zero the alpha channel | Medium | ASSUMED | All game entity images are loaded with `convert_alpha()`. Verify in UT-017 that `clipped_image` has `SRCALPHA`. |
| A7 | `stair_clip=true` on the specified tiles (depth-view upper-half tiles, e.g. IDs 16, 35) produces the correct depth illusion — i.e. the visual stair face aligns with where the clip removes pixels | Medium | ASSUMED | Visual verification required during first gameplay test. Debug overlay (`Settings.DEBUG`) shows hitbox alignment. |
| A8 | Per-frame surface composition (`pygame.Surface` + `blit` + `fill`) is negligible for ≤4 stair-stepping entities simultaneously | Medium | ASSUMED | Not measured. Accept for initial implementation; profile if frame drops occur on stair tiles. |
| A9 | `_max_stair_clip()` returning `float(Settings.TILE_SIZE // 2)` correctly represents the stair step height boundary for leg occlusion | Medium | ASSUMED | Step geometry is fixed at 16px. Validated for standard and taller sprites (prevents floating torso visual gaps). |
| A10 | Sprite animation frame dimension changes during a step do not affect clip correctness because `_max_stair_clip()` returns a fixed `TILE_SIZE`-derived value, independent of `sprite.image` dimensions | Low | ASSUMED | Safe by design — clip amount is geometry-based (step height), not sprite-based. |


---

## 5. Test Case Specifications

### Unit Tests (`game/tests/entities/test_stair_movement.py`)

**MapManager:**
- `UT-001`: `get_vertical_move_props(tx, ty)` returns `{"stair_direction": "right", "movement_type": "stair", "visual_y_offset": 0}` on mock tile with `stair_direction="right"`.
- `UT-002`: `get_vertical_move_props(tx, ty)` returns `None` on tile without `stair_direction`.
- `UT-003`: `get_vertical_move_props(-1, 0)` returns `None` (out of bounds — bounds check).
- `UT-004`: `get_vertical_move_props(tx, ty)` returns `None` on tile with `direction="right"` but without `stair_direction` (verifies no name collision).

**BaseEntity — start_move on right staircase (`stair_direction="right"`):**
- `UT-005a`: `stair_half=False` (lower half) + input `(1, 0)` → direction stays flat `(1, 0)`, target_pos = `(pos.x+32, pos.y)`, `is_moving = True`.
- `UT-005b`: `stair_half=True` (upper half) + input `(1, 0)` → direction intercepted at `(1, -1)`, target_pos = `(pos.x+32, pos.y-32)`, `is_moving = True`.
- `UT-006a`: `stair_half=True` (upper half) + input `(-1, 0)` → direction stays flat `(-1, 0)` (target tile is flat floor → step-off rule), `is_moving = True`.
- `UT-006b`: `stair_half=False` (lower half / bottom entry) + input `(-1, 0)` → direction stays flat `(-1, 0)` (bottom of staircase, no stair tile below), `is_moving = True`.
- `UT-007`: Input `(0, -1)` (Up) → `is_moving` remains `False`, `direction` reset to `(0, 0)`. Silent blocking.
- `UT-008`: Input `(1, 1)` (Unmapped diagonal) → `is_moving` remains `False`, `direction` reset to `(0, 0)`. Silent blocking.

**BaseEntity — start_move on left staircase (`stair_direction="left"`):**
- `UT-009a`: `stair_half=True` (upper half) + input `(-1, 0)` → direction stays flat `(-1, 0)` (step-off to flat floor), `is_moving = True`.
- `UT-009b`: `stair_half=False` (lower half / bottom entry) + input `(-1, 0)` → direction stays flat `(-1, 0)` (bottom of staircase, no stair tile below), `is_moving = True`.
- `UT-010a`: `stair_half=False` (lower half) + input `(1, 0)` → direction stays flat `(1, 0)` (step-off to flat floor), `is_moving = True`.
- `UT-010b`: `stair_half=True` (upper half) + input `(1, 0)` → direction intercepted at `(1, 1)`, target_pos = `(pos.x+32, pos.y+32)`.

**BaseEntity — transitions:**
- `UT-011`: Entity on normal floor → `_vertical_move` is `None`. Input `(1, 0)` → normal orthogonal movement `(pos.x+32, pos.y)`.
- `UT-012`: Entity on stair tile with `stair_half=True` + input `(-1,0)` + next tile is normal floor → step-off rule forces direction flat `(-1, 0)`, target_pos = `(pos.x-32, pos.y)`, `is_moving = True`.
- `UT-013`: `walkable_func` returns `False` for diagonal target → `target_pos` = `pos`, `is_moving = False` (staircase blocked by wall).

**Rendering offset & Interpolation:**
- `UT-014`: At progress = 50% of a step toward `target_offset=-16, target_clip=max_clip`: assert `current_stair_offset == -8.0` and `current_stair_clip == max_clip / 2`. At progress = 100%: assert `current_stair_offset == -16.0` and `current_stair_clip == max_clip`.
- `UT-015`: `CameraGroup.custom_draw()` applies `current_stair_offset` to render coordinates instead of static properties.
- `UT-017`: `CameraGroup.custom_draw()` with `current_stair_clip = 8` on a 32×48 sprite: assert pixel at `(0, 39)` has alpha > 0 (visible); assert pixel at `(0, 47)` has alpha == 0 (cleared). Assert `sprite.image` is unchanged after draw (original surface not mutated). Assert clipped surface has `pygame.SRCALPHA` flag.
- `UT-018` (combined clip + offset): Entity on tile with `visual_y_offset=-16` AND `stair_clip=true`. After `update_stair_offset()` (idle, fully arrived): `current_stair_offset == -16.0`, `current_stair_clip == _max_stair_clip()`. Call `custom_draw()`. Assert `offset_pos.y == visual_rect.top + camera_offset.y - 16`. Assert the blit uses `clipped_image` (not `sprite.image` directly). Assert pixel at image bottom is alpha 0 on the composed surface.

**_max_stair_clip helper:**
- `UT-019a`: Entity with `image.get_height() == 48` → `_max_stair_clip() == 16.0`.
- `UT-019b`: Entity with `image = None` → `_max_stair_clip() == float(Settings.TILE_SIZE // 2)`.

**stair_clip_exempt opt-out:**
- `UT-020`: Entity subclass with `stair_clip_exempt = True` placed on a `stair_clip=true` tile. After `update_stair_offset()` (idle): assert `current_stair_clip == 0.0`. Assert `current_stair_offset` IS still set to the tile's `visual_y_offset` (clip exemption does NOT imply offset exemption).

**VERTICAL_MOVE_MAP (config):**
- `UT-016`: `VERTICAL_MOVE_MAP[((1, 0), "right")] == (1, -1)` — verifies table correctness for all 4 combinations.

### Integration Tests (`game/tests/integration/test_stairs_integration.py`)

- `IT-001`: Load mini-map with a `stair_direction="right"`, `stair_half=True` tile. Spawn player on it. Input Right. Assert `pos == (initial.x + 32, initial.y - 32)` and `is_moving = False` (movement completed).
- `IT-002`: Same setup. Assert `_vertical_move["visual_y_offset"] == -16` during movement, then `_vertical_move = None` after reaching a floor tile.
- `IT-003`: Mini-map with 3 consecutive stair tiles (`stair_direction="right"`, alternating `stair_half`). Player traverses with repeated Right inputs. Assert each step applies interception only when `stair_half=True`.
- `IT-004`: Mini-map with staircase surrounded by walls (`walkable=False`). Input Up on stair tile → `is_moving = False`. Input Down → `is_moving = False`.
- `IT-005`: NPC with pathfinding to a tile beyond a staircase. Assert NPC traverses the staircase diagonally without getting stuck.
- `IT-006`: Tile with `direction="right"` (without `stair_direction`) → `get_vertical_move_props` returns `None`. No interception.

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

## Revision History

| Version | Date | Change |
|---------|------|--------|
| v1 | 2026-06-04 | Initial spec — basic stair interception |
| v2 | 2026-06-08 | Added NPC pathfinding section, cross-spec contracts |
| v3 | 2026-06-09 | Added §0 Tiled config, error handling, test cases |
| v4 | 2026-06-10 | Post adversarial review corrections |
| v5 | 2026-06-12 | Corrected descent diagonal logic per ADR-013: `should_move_diagonally = not stair_half` for descent (was `bool(stair_half)`) |
| v6 | 2026-06-13 | Added dynamic stair clipping per ADR-015 |
| v7 | 2026-06-13 | Post adversarial review (Round 0): completed `custom_draw()` code block, added `_max_stair_clip()` helper, fixed hardcoded fallback (TILE_SIZE//2), added clip+offset combined intent prose, added tile inventory `stair_clip` column, added A6–A9 assumptions, improved UT-017 with pixel assertions, added UT-018/UT-019. |
| v8 | 2026-06-13 | Post adversarial review (Round 1 — Gemini 3.5 Flash): fixed `_max_stair_clip()` to return `TILE_SIZE//2` instead of `get_height()//2` (F-HIGH-04), centralized `visual_y_offset` fallback to `0` (F-MED-04). Post adversarial review (Round 1 — Claude Opus 4.6): updated `camera-rendering.md` cross-spec contract for `current_stair_clip` (F-HIGH-05), updated ADR-015 clip formula (F-HIGH-06), added A10 assumption. |
| v9 | 2026-06-13 | Post adversarial review (Round 2 — Claude Sonnet 4.6): added `stair_start_pos` to `__init__` attribute list with implementation note (F-006); aligned `is_going_up` formula to code's domain-semantic derivation with VERTICAL_MOVE_MAP extension warning (F-004); added UT-020 for `stair_clip_exempt` opt-out including offset-not-exempt assertion (F-005); added SRCALPHA assertion to UT-017 (A6 coverage). |
