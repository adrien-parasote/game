# Technical Specification — `sub_type: bridge` [Implementation]

> Document Type: Implementation
> Parent Spec: docs/specs/interactive-objects.md
> Status: READY FOR BUILD

---

## 1. Problem Statement

The drawbridge entity (`sub_type: door`, `is_passable: true`) uses a 128×224px collision rect
that remains active even when the bridge is raised (`is_on=False`). This blocks the player from
approaching the water, because the door collision logic **always** starts with the entity in
`obstacles_group` and only removes it when the entity becomes open (ON).

A true door should block when closed — that is correct.
A bridge/drawbridge should **allow passage** when **lowered** (traversable), and rely on water tiles to **block passage** when **raised** —
because the water tiles beneath handle spatial exclusion in the raised state.

These are two fundamentally different semantic contracts. They must be separate `sub_type`s.

---

## 2. New `sub_type: bridge` — Behavioral Contract

### 2.1. Collision Lifecycle

| State | `obstacles_group` | `walkable_override_entities` | Player can reach entity |
|-------|-------------------|------------------------------|-------------------------|
| **Raised** (`is_on=False`) | **NOT in group** | NOT in set | ✅ Yes (water tiles block at map layer) |
| **Lowered** (`is_on=True`) | NOT in group | **IN set** | ✅ Yes (bridge overrides water walkability) |
| **Lowering (Animating)** | NOT in group | **IN set** | ❌ Blocked by `is_animating` guard in `CollisionChecker` |
| **Raising (Animating)** | NOT in group | NOT in set | ❌ Blocked by `is_animating` guard in `CollisionChecker` |

Compare with `sub_type: door`:

| State | `obstacles_group` | Notes |
|-------|-------------------|-------|
| Closed (`is_on=False`) | IN group | Blocks player |
| Open (`is_on=True`) | NOT in group (if `is_passable`) | Passable |
| Closing animation done | Re-added to group | |
| Opening animation done | Removed from group | |

### 2.2. Key Semantic Differences vs `door`

| Behavior | `door` | `bridge` |
|---|---|---|
| Spawn with `is_on=False` | Added to `obstacles_group` | **NOT** added |
| Spawn with `is_on=True` | Removed from `obstacles_group` if `is_passable` | Not in group, added to `walkable_override` |
| `_update_animation` closing ends | Re-added to `obstacles_group` | **Nothing** |
| `_update_animation` opening ends | Removed from `obstacles_group` | **Nothing** |
| `restore_state(is_on=True)` | Removed from obstacles | Already not there — only syncs `walkable_override` |
| `verify_orientation` back-facing | Allowed when open | **Not applicable** (no back-facing relaxation) |

### 2.3. `_sync_walkable_override` — Unchanged

The `_sync_walkable_override()` logic remains identical:
- `is_passable=True` AND `is_on=True` → add to `walkable_override_entities`
- Otherwise → discard from set

This already works correctly for bridges. No change needed here.

---

## 3. Implementation Changes

### 3.1. `src/entities/interactive.py`

#### 3.1.1. `_setup_physics` (L281-284)

**Current:**
```python
if self.sub_type == "door" or not self.is_passable:
    if not (self.is_on and self.is_passable):
        self.obstacles_group.add(self)
```

**New:**
```python
if self._should_start_in_obstacles():
    self.obstacles_group.add(self)
```

**New private method** (< 10 lines, extracted for clarity):
```python
def _should_start_in_obstacles(self) -> bool:
    """Return True if this entity must be in obstacles_group at spawn."""
    if self.sub_type == "bridge":
        return False  # bridge: water tiles handle blocking when raised
    if self.sub_type == "door":
        return not (self.is_on and self.is_passable)
    return not self.is_passable
```

#### 3.1.2. `restore_state` (L360-364)

**Current:**
```python
if self.sub_type == "door" and getattr(self, "obstacles_group", None) is not None:
    if is_on and getattr(self, "is_passable", False):
        self.obstacles_group.remove(self)
    else:
        self.obstacles_group.add(self)
```

**New:**
```python
if self.sub_type == "door" and getattr(self, "obstacles_group", None) is not None:
    if is_on and getattr(self, "is_passable", False):
        self.obstacles_group.remove(self)
    else:
        self.obstacles_group.add(self)
# bridge: no obstacles_group management — water tiles handle blocking
```

#### 3.1.3. `_update_animation` (L412, L419)

**Current:**
```python
if self.sub_type == "door" and self.obstacles_group:
    self.obstacles_group.add(self)          # L412: closing done
...
if self.sub_type == "door" and self.is_passable and self.obstacles_group:
    self.obstacles_group.remove(self)       # L419: opening done
```

**No change needed** — these are already guarded by `sub_type == "door"`.
`bridge` entities are never touched here. ✅

### 3.2. `src/engine/spatial_utils.py`

#### 3.2.1. `verify_orientation` (L122-123)

**Current:**
```python
if obj.sub_type == "door" and getattr(obj, "is_on", False):
    return _is_back_facing(o_dir, p_state, dx, dy, x_aligned, y_aligned)
```

**No change needed** — `bridge` will not match `"door"`, so back-facing relaxation
is correctly excluded for bridges. ✅

### 3.3. Tiled Map — `01-castel-ext.tmj`

The drawbridge entity (id=19) must change `sub_type` from `"door"` to `"bridge"`:

```json
"sub_type": "bridge"
```

**Already done by user** (confirmed A4 in DISCOVERY).

---

## 4. Files NOT Changed

| File | Reason |
|------|--------|
| `collision_checker.py` | `walkable_override_entities` logic already correct |
| `interaction.py` | No `door`-specific path for bridges |
| `entity_factory.py` | `spawn_interactive` is sub_type-agnostic |
| `interactive_constants.py` | No bridge-specific constants needed |

---

## 5. Test Case Specifications

### 5.1. Unit Tests — `tests/entities/test_interactive.py`

| Test ID | Description | Input | Expected |
|---------|-------------|-------|----------|
| UT-001 | Bridge raised NOT in obstacles at spawn | `sub_type="bridge", is_on=False, is_passable=True` | `entity NOT in obstacles` |
| UT-002 | Bridge lowered NOT in obstacles at spawn | `sub_type="bridge", is_on=True, is_passable=True` | `entity NOT in obstacles` |
| UT-003 | Bridge lowered registers in walkable_override | `sub_type="bridge", is_on=True, is_passable=True` + `_sync_walkable_override()` | `entity IN walkable_override_entities` |
| UT-004 | Bridge raised NOT in walkable_override | `sub_type="bridge", is_on=False, is_passable=True` + `_sync_walkable_override()` | `entity NOT IN walkable_override_entities` |
| UT-005 | Bridge restore_state open — not in obstacles | `restore_state({is_on: True})` | `entity NOT in obstacles` |
| UT-006 | Bridge restore_state closed — not in obstacles | `restore_state({is_on: False})` | `entity NOT in obstacles` |
| UT-007 | Door spawn still blocked (regression guard) | `sub_type="door", is_on=False, is_passable=True` | `entity IN obstacles` |
| UT-008 | `_should_start_in_obstacles` — bridge always False | `bridge, any is_on` | Returns `False` |
| UT-009 | `_should_start_in_obstacles` — door closed | `door, is_on=False` | Returns `True` |
| UT-010 | `_should_start_in_obstacles` — door open+passable | `door, is_on=True, is_passable=True` | Returns `False` |
| IT-001 | Player collides with lowered bridge | Player moves into bridge `rect` | Movement allowed (walkable override) |
| IT-002 | Player collides with raised bridge | Player moves towards water tile at bridge | Movement blocked (water tile) |
| IT-003 | Map transition cleanup | Bridge lowered, player leaves map | Bridge walkable override is cleared from CollisionChecker |

### 5.2. Tests to Update

| File | Test | Change |
|------|------|--------|
| `test_interactive.py` | `TestWalkableOverride._bridge()` | Change `sub_type="door"` → `sub_type="bridge"` |
| `test_interactive.py` | All `TC-INT-WO-*` test descriptions | Update docstrings to say "bridge" not "door" |

> **Regression invariant**: All existing `TC-INT-WO-*` tests must continue to pass after updating
> the `_bridge()` factory to use `sub_type="bridge"`. The `walkable_override` behavior is
> identical for both types — only `obstacles_group` management differs.

---

## 6. Anti-Patterns (DO NOT)

| ❌ Don't | ✅ Do Instead | Why |
|----------|---------------|-----|
| Add bridge to `obstacles_group` at any point | Let water tiles handle spatial blocking | Bridge `rect` is larger than the water zone — entity collision would over-block |
| Check `sub_type in ("door", "bridge")` inline | Use `_should_start_in_obstacles()` helper | Single-responsibility, testable, readable |
| Remove `door` back-facing relaxation | Keep it for doors only | Doors must be closable from the far side |
| Forget to update `TestWalkableOverride._bridge()` | Update sub_type to "bridge" | Tests must reflect the production entity type |
| Call `obstacles_group.remove(self)` or `add(self)` for bridges | Leave `obstacles_group` completely alone for bridges | Bridges are never part of `obstacles_group`; their spatial blocking is handled entirely by tile walkability and the animation guard in `CollisionChecker` |

---

## 7. Error Handling

| Error | Response | Fallback | Logging |
|---|---|---|---|
| Invalid `sub_type` in tiled map | Engine throws ValueError on entity creation | None | Log specific entity ID and map name |
| Missing `is_passable` property | Defaults to `False` | Assume blocking | Log warning that entity is missing property |

---

## 8. Deep Links

- **`InteractiveEntity._setup_physics`**: [interactive.py L264](../../src/entities/interactive.py#L264)
- **`InteractiveEntity.restore_state`**: [interactive.py L349](../../src/entities/interactive.py#L349)
- **`InteractiveEntity._update_animation`**: [interactive.py L397](../../src/entities/interactive.py#L397)
- **`spatial_utils.verify_orientation`**: [spatial_utils.py L90](../../src/engine/spatial_utils.py#L90)
- **`CollisionChecker.check`**: [collision_checker.py L24](../../src/engine/collision_checker.py#L24)
- **Drawbridge entity in map**: [01-castel-ext.tmj L158](../../assets/tiled/maps/01-castel-ext.tmj#L158)
- **Parent spec**: [interactive-objects.md](./interactive-objects.md#L1)
- **Test file**: [test_interactive.py](../../tests/entities/test_interactive.py#L1)

---

## 9. Assumptions

| # | Assumption | Risk | Validation |
|---|---|---|---|
| A1 | `is_on=False` = bridge raised; water tiles block the player | Low | Confirmed by user |
| A2 | `is_on=True` = bridge lowered; `walkable_override` enables crossing | Low | Confirmed by user |
| A3 | No back-facing interaction relaxation needed for bridges | Low | Confirmed by user |
| A4 | Tiled map already updated to `sub_type: bridge` | Low | Confirmed by user |
