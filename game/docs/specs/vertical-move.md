# Specification: Stair & Ladder Movement Mechanics

> Document Type: Implementation
> Stage: 📋 SPEC
> Revision: v15 (Adversarial Review Round 3 — D1–D4 resolved. Consolidated 2026-06-17 after 3 adversarial rounds.)

This specification defines the diagonal movement behavior for lateral stairs and vertical movement for ladders using Tiled properties.

---

## Constraints

| Tier | Constraint |
|------|------------|
| **Always do** | Run tests before committing. Verify `MapManager` lookups gracefully with bounds checking. |
| **Ask first** | Add any new Tiled classes or properties. |
| **Never do** | Modify `self.rect` for visual offsets. Use a plain single-word `direction` property in Tiled for stair direction (avoid name collision with `direction_flags`). Compound `direction` values containing a comma (e.g. `"up,left"`) are stair directions and do NOT collide. |

---

## Assumptions

| # | Assumption | Risk | Source Type | Validation |
|---|------------|------|-------------|------------|
| 1 | The stairs on the map are placed in a diagonal zigzag pattern (e.g. `(x, y) -> (x+1, y-1)`). | Medium | SHOW | Verified via Tiled grid structure audit and `grep_search` of TMJ file. |
| 2 | The check `(visual_y_offset != 0)` correctly identifies the upper part of the step. | Medium | SHOW | Verified via TSX file inspection and `view_file` of `01-stairs.tsx`. |
| 3 | Horizontal inputs are locked on stairs; vertical inputs are locked on ladders. | Low | TELL | Agreed upon in the contract and codified in this specification. |
| 4 | Pygame's event loop is single-threaded. `start_move()` and `update_stair_offset()` are never called concurrently. | Low | TELL | Structural guarantee of pygame's GIL + single-threaded event loop. |

---

## Cross-Spec Contracts

### Produces

| Path | Format | Schema Location | Consumers |
|------|--------|-----------------|-----------|
| `BaseEntity.current_stair_offset` | `float` | [vertical-move.md §5.1](./vertical-move.md#L256) | [camera-rendering.md](./camera-rendering.md#L76) |
| `BaseEntity.current_stair_clip` | `float` | [vertical-move.md §5.3](./vertical-move.md#L356) | [camera-rendering.md](./camera-rendering.md), [entities-system.md](./entities-system.md) |
| `BaseEntity._vertical_move` | `dict \| None` | [vertical-move.md §4.2](./vertical-move.md#L162) | [entities-system.md](./entities-system.md#L258) |
| `BaseEntity.update_stair_offset()` | `method` | [vertical-move.md §5.1](./vertical-move.md#L256) | [entities-system.md](./entities-system.md#L267) |
| `MapManager.get_vertical_move_props` | `method` | [vertical-move.md §4.2](./vertical-move.md#L162) | [entities-system.md](./entities-system.md#L258) |

### Consumes

| Path | Format | Schema Location | Producer |
|------|--------|-----------------|----------|
| N/A | N/A | N/A | N/A - reason: reads local Tiled map properties directly, no other specs produce them |

### Public Interface

| Type | Identifier | Documented at |
|------|------------|---------------|
| N/A | N/A | N/A - reason: class-level internal logic only |

### External Invocations

| Type | Identifier | Documented at |
|------|------------|---------------|
| N/A | N/A | N/A - reason: class-level internal logic only |

### Tracked Concepts

| Concept | Description | Documented at |
|---------|-------------|---------------|
| N/A | N/A | N/A - reason: class-level internal logic only |

---

## Anti-patterns

| # | Anti-pattern | Why Incorrect | What to Do Instead |
|---|--------------|---------------|---------------------|
| 1 | Setting a plain single-word `direction` (e.g. `"right"`) to indicate a stair | `direction` is reserved for `direction_flags` (tmj_parser.py L307). A plain `direction="right"` would be consumed by `direction_flags`, blocking all movement except to the right. Only compound `direction` values with a comma (e.g. `"up,left"`) are treated as stair directions. | Use compound `direction="up,left"` for new stair tiles. Use `stair_direction` only for legacy single-word keys. See §4.2 property resolution. |
| 2 | Modifying `self.rect` for visual offset | Breaks collision physics. `rect` is used for grid positioning and collision detection. | Apply the offset only in `offset_pos` during `blit()` in `custom_draw()`. |
| 3 | Restricting interception to the Player | All `BaseEntity`s go through `start_move()`. Restricting to the Player would prevent NPCs from climbing stairs. | The interception in `start_move()` automatically applies to all entities. |
| 4 | Calling `get_vertical_move_props` in `update()` or `move()` | Creates a per-frame call instead of a per-movement call. Unnecessary performance impact. | A single read in `start_move()`, result stored in `self._vertical_move`. |
| 5 | Inferring a staircase from visual layers | Visual layers can contain decorations without stair properties. | Rely solely on the `stair_direction` field returned by `get_vertical_move_props()` (see §4.2 for how it resolves from `direction` or `stair_direction` Tiled properties). |

---

## Error Handling

| Error | Response | Fallback | Logging |
|-------|----------|----------|---------|
| Tile has no stair direction property | Normal floor tile | `get_vertical_move_props` returns `None` (no compound `direction` and no `stair_direction`). `self._vertical_move = None`. Movement normal. | None (nominal case) |
| `stair_direction` value not in behavior's `move_map` | Missing config or unhandled direction | `move_map.get()` returns `None`. `start_move` aborts the move. | `logger.warning(f"Unknown stair_direction '{key}' at ({tx},{ty})")` |
| `movement_type` value not in `MOVEMENT_BEHAVIORS` | Unknown tile type | `MOVEMENT_BEHAVIORS.get()` returns `None`. `self._vertical_move = None`. Movement normal. | `logger.warning(f"Unknown movement_type '{mtype}' at ({tx},{ty})")` |
| `get_vertical_move_props` called out of bounds | tx/ty out of map boundaries | Bounds check at start of function -> returns `None`. | None |
| Diagonal target not walkable | Target tile `walkable=False` | `walkable_func` resets `target_pos = self.pos`. | None |
| `visual_y_offset` is missing or 0 on a clipped tile | Default to 8 | `visual_y_offset` is resolved as 8. | None |
| `visual_y_offset` is negative on a clipped tile | No clipping | Target clip resolves to 0.0. | None |
| `visual_y_offset` exceeds sprite height | Clamp to sprite height | Clip amount is clamped to `sprite.image.get_height()`. | None |

---

## Test Cases

### Unit Tests
| ID | Input | Expected Output |
|----|-------|-----------------|
| `UT-001` | `get_vertical_move_props(tx, ty)` on stair tile | Returns properties dictionary with `stair_direction` |
| `UT-002` | `get_vertical_move_props(tx, ty)` on normal tile | Returns `None` |
| `UT-003` | `get_vertical_move_props(-1, 0)` (out of bounds) | Returns `None` |
| `UT-004` | Pressing UP/DOWN on a stair tile | `is_moving` remains `False`, direction resets |
| `UT-005` | Pressing RIGHT/LEFT on a ladder tile | `is_moving` remains `False`, direction resets |
| `UT-006` | `get_vertical_move_props(tx, ty)` on tile with `clip = true` | Returns properties dict with `clip=True` |
| `UT-007` | Standing still on a tile with `clip = true` and `visual_y_offset = 24` | `current_stair_clip == 24.0` |
| `UT-008` | Moving from normal tile to clipped tile with `visual_y_offset = 8` (at 50% progress) | `current_stair_clip == 4.0` |
| `UT-009` | Standing still on a clipped tile with `visual_y_offset = 100` (sprite height is 32) | `current_stair_clip == 32.0` (clamped to height) |

### Integration Tests
| ID | Input | Expected Output |
|----|-------|-----------------|
| `IT-001` | Player climbs stairs to the top and descends to the bottom | Exact starting logical coordinates and 0.0 offset (symmetry) |
| `IT-002` | Player is at 50% movement progress on a stair step (`curr_dist == total_dist / 2`) | `current_stair_offset == stair_start_offset + (stair_target_offset - stair_start_offset) * 0.5`, within ±0.5px tolerance |
| `IT-003` | NPC pathfinder navigates path crossing stairs (calls `start_move()` on `BaseEntity`) | NPC reaches the tile on the other side of the staircase with correct final logical coordinates |
| `IT-004` | Player moves horizontally on row 35 across descending stair tiles with `clip = true` | Sprite is rendered partially clipped from the bottom using `area` in `custom_draw`, feet do not extend below the tile boundary |


---

## 4. Core Movement Interception & Slope Alternation
2026-06-17:
* **Logger requirement:** Implementation must instantiate a module-level logger: `logger = logging.getLogger(__name__)` in `base.py` to support warnings.

### 4.0 Execution Sequence in `start_move(input_dir)`

The ordered call sequence inside `start_move()` — an AI coder must implement these steps in this exact order:

1. Compute `(tx, ty)` from entity's current grid position.
2. Call `get_vertical_move_props(tx, ty)` → `current_vm`.
3. **Always assign:** `self._vertical_move = current_vm` (even when `None` — clears stale state).
4. If `current_vm` is `None` → normal floor movement, exit.
5. Look up `behavior = MOVEMENT_BEHAVIORS.get(current_vm["movement_type"])` → if `None`, log warning, exit.
6. Filter `input_dir` by `behavior.allowed_axes` (e.g. if 'horizontal', set `input_dir = (input_dir[0], 0)`). If the resulting `input_dir` is `(0, 0)`, **silently discard input** and exit.
7. Look up `intercepted_dir = behavior.move_map.get((input_dir, current_vm["stair_direction"]))` → if `None`, log warning, abort.
8. **§4.3 slope alternation FIRST:** apply `behavior.is_diagonal(current_vm["half"], intercepted_dir[1])` to decide `predicted_dir`. (If True, use full `(dx, dy)`. If False, use behavior's fallback axis).
9. **§4.4 boundary check AFTER:** call `get_vertical_move_props(tx + predicted_dir[0], ty + predicted_dir[1])` → `target_vm`. Store for use in §5.1 init.
10. If `target_vm` is `None` (not a stair tile) → we are stepping off. If descending (`intercepted_dir[1] > 0`), force `final_dir = (intercepted_dir[0], 0)` and re-fetch `target_vm` at this new location. If climbing, keep `final_dir = predicted_dir`.
11. Walkable check on final target tile coordinates.
12. If walkable → update `target_pos`; initialize offset tracking fields (see §5.1, explicitly overwriting `self._vertical_move = target_vm` to store target properties or clear to `None` when stepping off).

> **`_vertical_move` at arrival (user decision 2026-06-17: no re-fetch):** After step 12, `self._vertical_move` holds the **target** tile's properties (set in step 3 as `current_vm`, then overwritten to `target_vm` during offset init). When movement completes (`is_moving` → `False`), this becomes the current tile's properties. **No re-fetch is needed on arrival** — the `update_stair_offset()` standing-still branch reads `_vertical_move` directly. The existing re-fetch in `move()` (lines 69-72 of current `base.py`) is **deleted** as part of this refactor. `[user decision: no re-fetch, 2026-06-17]`

---

### 4.1 `StairBehavior` (in `config.py`)

> **Migration note:** This section defines the **target** architecture. The existing `Settings.VERTICAL_MOVE_MAP` flat dict and inline stair logic in `_apply_stair_interception()` are **replaced** by `StairBehavior` instances registered in `MOVEMENT_BEHAVIORS`. The existing `VERTICAL_MOVE_MAP` is deleted.

All movement types are defined via a single `StairBehavior` dataclass. Adding a new stair type requires only adding a new instance to `MOVEMENT_BEHAVIORS` — no changes to `start_move()` or `update_stair_offset()`.

```python
# Compound direction format from Tiled: "<visual_type>,<entry_side>"
#   visual_type = "up" (ascending asset) | "down" (descending asset)
#   entry_side  = "left" (entry on left) | "right" (entry on right)
# Legacy single-word keys ("right", "left") kept for backward compat.

@dataclass(frozen=True)
class StairBehavior:
    """Encapsulates movement map, slope alternation, and input restriction for one tile type."""
    move_map: dict[tuple[tuple[int, int], str], tuple[int, int]]
    # Returns True if this step should be diagonal given (half: bool, dy: int)
    is_diagonal: Callable[[bool, int], bool]
    # Axes allowed for input: "horizontal" | "vertical"
    allowed_axes: str
    # The axis to keep when is_diagonal returns False
    fallback_axis: str

STAIR_BEHAVIOR = StairBehavior(
    move_map={
        # --- Group A (up,right / down,right): ascend by going LEFT ---
        ((1, 0),  "up,right"):    (1,  1),   # Right → descend
        ((-1, 0), "up,right"):   (-1, -1),   # Left  → climb
        ((1, 0),  "down,right"): (1,  1),   # Right → descend
        ((-1, 0), "down,right"): (-1, -1),  # Left  → climb
        # --- Group B (up,left / down,left): ascend by going RIGHT ---
        ((1, 0),  "up,left"):    (1, -1),   # Right → climb
        ((-1, 0), "up,left"):   (-1,  1),   # Left  → descend
        ((1, 0),  "down,left"):  (1, -1),   # Right → climb
        ((-1, 0), "down,left"): (-1,  1),   # Left  → descend
        # --- Legacy single-word keys (backward compat) ---
        ((1, 0),  "right"):  (1, -1),   # Right → climb  [verified via POC 2026-06-17]
        ((-1, 0), "right"): (-1,  1),   # Left  → descend [verified via POC 2026-06-17]
        ((1, 0),  "left"):   (1,  1),   # Right → descend
        ((-1, 0), "left"):  (-1, -1),   # Left  → climb
    },
    is_diagonal=lambda half, dy: (dy < 0 and half) or (dy > 0 and not half),
    allowed_axes="horizontal",
    fallback_axis="horizontal",
)

LADDER_BEHAVIOR = StairBehavior(
    move_map={
        ((0, -1), "ladder"): (0, -1),  # Up on ladder → move up
        ((0,  1), "ladder"): (0,  1),  # Down on ladder → move down
    },
    is_diagonal=lambda half, dy: False,  # Ladders are always straight vertical
    allowed_axes="vertical",
    fallback_axis="vertical",
)

# Registry: movement_type (from Tiled) → behavior
MOVEMENT_BEHAVIORS: ClassVar[dict[str, StairBehavior]] = {
    "stair":  STAIR_BEHAVIOR,
    "ladder": LADDER_BEHAVIOR,
}
```

### 4.2 `MapManager` Lookup

> **Property resolution:** Tiled tiles use two naming conventions for stair direction:
> - **Compound format** (primary): `direction="up,left"`, `direction="down,right"`, etc. — detected by the presence of a comma.
> - **Legacy format**: `stair_direction="right"` or `stair_direction="left"` — explicit property name, no comma.
>
> The lookup reads `direction` first. If the value contains a comma, it is a compound stair direction. Otherwise, it falls back to the `stair_direction` property for legacy single-word keys. A plain single-word `direction` (e.g. `"right"`) is NOT treated as a stair direction — it belongs to `direction_flags`.

```python
def get_vertical_move_props(self, tx: int, ty: int) -> dict | None:
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
        raw_dir = props.get("direction", "")
        # Compound "up,left" / "down,right" style → stair direction.
        # Plain single-word "direction" (e.g. "right") is a direction_flags prop, not a stair.
        stair_dir = raw_dir if "," in raw_dir else props.get("stair_direction", "")
        if stair_dir:
            return {
                "stair_direction": stair_dir,
                "movement_type": props.get("movement_type", "stair"),
                "visual_y_offset": int(props.get("visual_y_offset", 0)),
                "half": props.get("half", False) in (True, "true"),
                "clip": props.get("clip", False) in (True, "true"),
            }
    return None
```

### 4.3 Slope Alternation Logic

> **Execution order:** Slope alternation runs FIRST (step 8 in §4.0), then §4.4 boundary check runs AFTER (step 9). If §4.4 detects a step-off (target is not a stair tile), it overrides `predicted_dir` to `(dx, 0)` — the slope alternation result is discarded in that case.

To keep the character feet aligned with the shallow 26.5° staircase slope (16px rise per 32px step) instead of a steep 45°, the logical grid movement alternates between flat `(dx, 0)` and diagonal `(dx, dy)` steps.

Variable definitions:
- `intercepted_dir` = `behavior.move_map.get((input_dir, current_vm["stair_direction"]))` — the raw diagonal from the move map (e.g. `(1, -1)`).
- `half` = `current_vm["half"]` — boolean from Tiled (`True` on upper step, `False` on lower step). Mapped from Tiled property `half`.

Alternation rule (encoded in `STAIR_BEHAVIOR.is_diagonal`):
* Climbing up (`intercepted_dir[1] < 0`): diagonal move occurs when `half is True` (entity is on the upper half of the step).
* Descending down (`intercepted_dir[1] > 0`): diagonal move occurs when `half is False` (entity is on the lower half of the step).
* If `is_diagonal` is False, keep only the behavior's `fallback_axis` component (for stairs: `final_dir = (dx, 0)`; for ladders: `final_dir = (0, dy)`).

### 4.4 Boundary Step-Off Rule

> **Execution order:** This check runs **after** §4.3 slope alternation (step 9 in §4.0 sequence) using the `predicted_dir`.

Call `get_vertical_move_props(tx + predicted_dir[0], ty + predicted_dir[1])` → `target_vm`.
Store `target_vm` — it is reused in §5.1 to initialize `stair_target_offset`.
* If `target_vm` is `None` (target is not a stair tile) → we are stepping off.
  * If descending (`intercepted_dir[1] > 0`), force `final_dir = (intercepted_dir[0], 0)` and re-fetch `target_vm` at this new flat location to ensure correct offsets.
  * If climbing, keep `final_dir = predicted_dir`.

### 4.5 Input Restrictions

**Design decision:** Locked-axis inputs are **filtered out** from the movement vector. If the remaining vector is `(0, 0)`, the input is **silently discarded** (no animation, no sound). If the player holds both a valid and invalid direction (e.g. UP+RIGHT on stairs), the invalid UP axis is stripped and the RIGHT axis is processed normally, preventing diagonal input freezes.

* **Stairs** (`allowed_axes = "horizontal"`): UP/DOWN components are stripped. Only LEFT/RIGHT components trigger movement.
* **Ladders** (`allowed_axes = "vertical"`): LEFT/RIGHT components are stripped. Only UP/DOWN components trigger movement.

### 4.6 Ladder Movement

Ladder movement is handled automatically via `LADDER_BEHAVIOR` registered in `MOVEMENT_BEHAVIORS`. No special-casing in `start_move()` is needed.

- The `move_map` maps `(UP, "ladder") → (0, -1)` and `(DOWN, "ladder") → (0, 1)` (pure vertical moves).
- `is_diagonal` always returns `False` — ladder movement never alternates, always straight.
- `visual_y_offset` on ladder tiles represents the entity's height on the ladder rung; interpolation in §5.1 applies identically to stairs.
- `stair_direction` for ladder tiles must be set to `"ladder"` in Tiled properties (same `stair_direction` field, different value).

---

## 5. Rendering & Offset Interpolation

### 5.1 `BaseEntity.update_stair_offset()`

**Field initialization (in `__init__`):**
To prevent `AttributeError` before the first movement, the entity must initialize these tracking fields to `0.0` in `BaseEntity.__init__()`:
`current_stair_offset`, `stair_start_offset`, `stair_target_offset`, `current_stair_clip`, `stair_start_clip`, `stair_target_clip`.

**Field initialization (in `start_move()`, step 12 of §4.0 sequence):**
These fields must be set **before** `is_moving` is set to `True`, using `target_vm` already fetched in §4.4:
```python
# target_vm is the result of get_vertical_move_props on the target tile (from §4.4 — no second call needed)
self._vertical_move      = target_vm                              # overwrite to target properties (clears to None when stepping off)
self.stair_start_pos     = pygame.math.Vector2(self.pos)          # cache start position for interpolation
self.stair_move_distance = (target_pos - self.pos).magnitude()    # total distance for this move
self.stair_start_offset  = self.current_stair_offset              # offset at move start
self.stair_target_offset = float(target_vm["visual_y_offset"]) if target_vm else 0.0

# Clip interpolation initialization
self.stair_start_clip    = self.current_stair_clip
if target_vm and target_vm.get("clip"):
    raw_offset = target_vm.get("visual_y_offset", 8)
    if raw_offset >= 0:
        clip_amount = 8 if raw_offset == 0 else raw_offset
        sprite_height = self.image.get_height() if self.image else 32
        self.stair_target_clip = float(min(clip_amount, sprite_height))
    else:
        # Negative offset means upward shift, no bottom clipping applies.
        self.stair_target_clip = 0.0
else:
    self.stair_target_clip = 0.0
```

**Per-frame update in `BaseEntity.update(dt)` AFTER the physical move completes:**
```python
def update_stair_offset(self):
    if not self.is_moving:
        vm = self._vertical_move
        self.current_stair_offset = float(vm.get("visual_y_offset", 0.0)) if vm else 0.0
        if vm and vm.get("clip"):
            raw_offset = vm.get("visual_y_offset", 8)
            if raw_offset >= 0:
                clip_amount = 8 if raw_offset == 0 else raw_offset
                sprite_height = self.image.get_height() if self.image else 32
                self.current_stair_clip = float(min(clip_amount, sprite_height))
            else:
                self.current_stair_clip = 0.0
        else:
            self.current_stair_clip = 0.0
    else:
        if self.stair_move_distance > 0:
            curr_dist = (self.target_pos - self.pos).magnitude()
            progress = max(0.0, min(1.0, 1.0 - curr_dist / self.stair_move_distance))
            self.current_stair_offset = self.stair_start_offset + (self.stair_target_offset - self.stair_start_offset) * progress
            self.current_stair_clip = self.stair_start_clip + (self.stair_target_clip - self.stair_start_clip) * progress
        else:
            self.current_stair_offset = self.stair_target_offset
            self.current_stair_clip = self.stair_target_clip
```

### 5.2 `CameraGroup.custom_draw()` Rendering

**Sign convention:** In pygame, Y increases **downward** on screen. `visual_y_offset` is stored in Tiled as a **signed integer** — it can be positive (shift sprite down) or negative (shift sprite up). The level designer uses it to fine-tune the entity's visual position on each stair step. Therefore `stair_y_offset` is **added** directly to the Y coordinate:

```python
visual_rect = sprite.image.get_rect(bottomright=sprite.rect.bottomright)
stair_y_offset = getattr(sprite, 'current_stair_offset', 0.0)
offset_pos = (visual_rect.left + self.offset.x, visual_rect.top + self.offset.y + stair_y_offset)

clip_amount = int(getattr(sprite, 'current_stair_clip', 0.0))
if clip_amount > 0:
    w, h = sprite.image.get_size()
    clip_amount = max(0, min(clip_amount, h))
    area = pygame.Rect(0, 0, w, h - clip_amount)
    surface.blit(sprite.image, offset_pos, area=area)
else:
    surface.blit(sprite.image, offset_pos)
```

### 5.3 Stair Clipping Specifications

*   **Tiled trigger:** The clipping effect is triggered on any tile with Tiled property `clip = true`.
*   **Clip calculation:** The clip amount uses the `visual_y_offset` (only if positive, resolving upward shifts to 0.0), defaulting to 8 if it is missing or 0, and clamped to the sprite's height.
*   **Interpolation:** The clip amount is interpolated smoothly between start and target values during movement.
*   **Grass wading interaction:** If `getattr(sprite, "current_stair_clip", 0.0) > 0`, the grass wading rendering effect is bypassed on the entity to prevent drawing grass over clipped transparent areas. The `WadingRenderer.apply_grass_wading_to_images` method in `src/engine/render_wading.py` must explicitly skip any sprite with a positive `current_stair_clip`.

---

## 6. Deep Links

* `MapManager`: [manager.py](../../src/map/manager.py#L1)
* `BaseEntity`: [base.py](../../src/entities/base.py#L1)
* `CameraGroup.custom_draw`: [groups.py](../../src/entities/groups.py#L1)
* `Settings`: [config.py](../../src/config.py#L1)
* `test_ladder_movement.py`: [test_ladder_movement.py](../../tests/entities/test_ladder_movement.py#L1)
