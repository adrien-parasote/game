# Technical Specification — Intra-Map Teleport & Walk Transition [Implementation]

> Document Type: Implementation
> **Covers:** F1 (intra-carte detection), F2 (resolve_spawn_by_id), F3 (intra_map_teleport), F4 (walk loop), F5 (tests)
> **Source:** `src/engine/interaction.py`, `src/engine/game.py`, `src/engine/map_loader.py`
> **Strategic Blueprint:** [`docs/strategic/intra-map-teleport-blueprint.md`](../strategic/intra-map-teleport-blueprint.md#top)

---

## 1. Problem Statement

When a `Teleport` entity has `target_map == _current_map_name`, calling `game.transition_map()` triggers a full `_load_map()` cycle: all entity groups are cleared, the TMJ file is re-parsed, and the player is repositioned — causing a visual flash and destroying runtime entity states.

Additionally, no `transition_type` exists that makes the camera follow the player walking from the teleport source to the destination. Only `"fade"` (blind cut) and `"instant"` are available.

---

## 2. Architecture Overview

```
check_teleporters()
  ├── tp.target_map == _current_map_name?
  │     YES → game.intra_map_teleport(target_spawn_id, transition_type)
  │             ├── "instant" → _map_loader._position_player(spawn_pos)
  │             └── "walk"   → set _intra_walk_state, animate in _update_core_state()
  └── NO  → game.transition_map()  [unchanged]
```

**No new Tiled properties required.** Reuse existing:
- `target_map` = current map filename (e.g. `castel_door.tmj`)
- `target_spawn_id` = destination spawn point id
- `transition_type` = `"walk"` (new token) or `"instant"` (existing)

---

## 3. Tiled Configuration

### 3.1 Teleport Object Properties (no change to schema)

| Property | Type | Value for intra-map |
|----------|------|---------------------|
| `target_map` | string | Same as current map filename |
| `target_spawn_id` | string | ID of the destination spawn point |
| `transition_type` | string | `"walk"` or `"instant"` |
| `required_direction` | string | e.g. `"up"` (optional constraint) |

### 3.2 Spawn Point Requirements

Destination spawn points **must** have a `spawn_id` property matching the `target_spawn_id` value. They are detected via `MapManager._entities` (already in memory — G1 resolved).

---

## 4. Implementation Specification

### 4.1 `interaction.py` — `check_teleporters()` branch

**Location:** [`src/engine/interaction.py#L290-L297`](../../src/engine/interaction.py#L290-L297)

Replace the single call to `game.transition_map()` with a branch:

```python
# BEFORE (line ~290):
self.game.transition_map(tp.target_map, tp.target_spawn_id, tp.transition_type)

# AFTER:
if tp.target_map in ("", self.game._current_map_name):
    self.game.intra_map_teleport(tp.target_spawn_id, tp.transition_type)
else:
    self.game.transition_map(tp.target_map, tp.target_spawn_id, tp.transition_type)
```

**Rules:**
- Empty `target_map` (`""`) also routes to intra-map (defensive guard).
- Cross-map path is **unchanged** — zero regression risk.
- The `break` after the call (line 297) is preserved.

---

### 4.2 `map_loader.py` — `resolve_spawn_by_id()`

**New method on `MapLoader`.**

```python
def resolve_spawn_by_id(self, target_spawn_id: str) -> tuple[int, int] | None:
    """Find pixel coordinates of a spawn_id on the currently loaded map.

    Reads from game.map_manager._entities (in-memory, no disk I/O).
    Returns (pixel_x, pixel_y) center of the spawn tile, or None if not found.
    """
    half_tile = self.game.tile_size // 2
    for ent in self.game.map_manager._entities:
        ent_type = ent.get("type", "")
        props = ent.get("properties", {})
        is_spawn = ent_type == "14-spawn_point" or props.get("spawn_player") is True
        if not is_spawn:
            continue
        if props.get("spawn_id") == target_spawn_id:
            return (ent["x"] + half_tile, ent["y"] + half_tile)
    logging.warning(f"resolve_spawn_by_id: '{target_spawn_id}' not found on current map")
    return None
```

**Rules:**
- Reads `self.game.map_manager._entities` — same logic as `_resolve_spawn()` but no fallbacks.
- No disk I/O (A-ARCH-001 compliance).
- Returns `None` on miss — caller must handle gracefully.

---

### 4.3 `game.py` — `intra_map_teleport()`

**New public method on `Game`.**

```python
def intra_map_teleport(self, target_spawn_id: str, transition_type: str) -> None:
    """Reposition the player within the current map without reloading it.

    Preserves all entity groups, world state, and audio.
    Supports transition_type: 'instant' or 'walk'.
    """
    spawn_pos = self._map_loader.resolve_spawn_by_id(target_spawn_id)
    if spawn_pos is None:
        logging.error(
            f"intra_map_teleport: spawn '{target_spawn_id}' not found — abort"
        )
        return

    if transition_type == "walk":
        self._start_intra_walk(pygame.math.Vector2(spawn_pos))
    else:
        self._map_loader._position_player(spawn_pos)
```

---

### 4.4 `game.py` — Walk State

**Two new private methods + one state field on `Game`.**

#### 4.4.1 State field (add to `_init_groups()`)

```python
# Intra-map walk state — None when inactive
self._intra_walk_target: pygame.math.Vector2 | None = None
```

#### 4.4.2 `_start_intra_walk()`

```python
def _start_intra_walk(self, target: pygame.math.Vector2) -> None:
    """Start a scripted walk from current player position to target (pixel coords).

    Initiates physics target, triggers is_moving state, and computes initial direction/facing.
    Input is blocked for the duration (handled in _update_core_state).
    """
    self._intra_walk_target = target
    self.player.target_pos = target
    self.player.is_moving = True
    # Set initial player facing direction
    delta = target - self.player.pos
    if delta.magnitude() > 0:
        if abs(delta.x) >= abs(delta.y):
            self.player.current_state = "right" if delta.x > 0 else "left"
        else:
            self.player.current_state = "up" if delta.y < 0 else "down"
```

#### 4.4.3 `_tick_intra_walk()` — called in `_update_core_state()` instead of normal input

```python
def _tick_intra_walk(self, dt: float) -> None:
    """Check arrival status and maintain player facing direction.

    Reuses player.move(dt) (triggered via visible_sprites.update) for actual translation.
    Terminates the walk when player.is_moving becomes False.
    """
    if self._intra_walk_target is None:
        return

    # Check for arrival
    if not self.player.is_moving:
        self._intra_walk_target = None
        self.player.direction = pygame.math.Vector2(0, 0)
        return

    # Keep facing updated based on remaining distance vector
    delta = self._intra_walk_target - self.player.pos
    if delta.magnitude() > 0:
        if abs(delta.x) >= abs(delta.y):
            self.player.current_state = "right" if delta.x > 0 else "left"
        else:
            self.player.current_state = "up" if delta.y < 0 else "down"
```

---

### 4.5 `game.py` — `_update_core_state()` integration

**Location:** [`src/engine/game.py#L449`](../../src/engine/game.py#L449)

The walk state intercepts the normal update path **before** `player.input()`:

```python
    def _update_core_state(self, dt: float):
        self.time_system.update(dt)
        self.interaction_manager.update(dt)
        
        if self._intra_walk_target is not None:
            # INTERCEPT: If walking via teleport, override standard loop
            self._tick_intra_walk(dt)
            self.visible_sprites.update(dt)
            # Skip player input, interact, and teleporter checks
        else:
            self.player.input()
            self.interaction_manager.handle_interactions()
            was_moving = self.player.is_moving
            self.visible_sprites.update(dt)
            self.interaction_manager.check_teleporters(was_moving)
            
        # ... (Keep rest of existing _update_core_state: NPCs, interactives, ambient audio)
```

**Rules:**
- `self.visible_sprites.update(dt)` is kept so sprite animations continue during walk.
- `check_teleporters()` is **not** called during walk (prevents re-trigger mid-walk).
- `interaction_manager.update(dt)` is kept for cooldown tick only.

---

## 5. Constraints

| Tier | Examples |
|------|----------|
| **Always do** | Run full test suite after changes, log warnings on spawn not found, preserve `break` in `check_teleporters()` |
| **Ask first** | Add new Tiled property types, change `Settings.PLAYER_SPEED` semantics, modify `_position_player()` signature |
| **Never do** | Call `_load_map()` for intra-map teleports, modify `CameraGroup`, modify `MapManager`, read disk inside `resolve_spawn_by_id()` |

---

## 6. Cross-Spec Contracts

### Produces
| Identifier | Format | Consumers |
|------------|--------|-----------|
| `game._intra_walk_target: Vector2 \| None` | Python attribute | `_update_core_state()` — same file |
| `MapLoader.resolve_spawn_by_id()` | Method `(str) → tuple \| None` | `game.intra_map_teleport()` |
| `game.intra_map_teleport()` | Method `(str, str) → None` | `interaction.py#check_teleporters()` |

### Consumes
| Identifier | Format | Producer |
|------------|--------|----------|
| `MapManager._entities` | `list[dict]` | `map_loader.py#load()` via `TmjParser` |
| `MapLoader._position_player()` | Method | [`map-world-system.md § "Player Spawn"](./map-world-system.md#top) |
| `Settings.PLAYER_SPEED` | `float` px/s | `src/config.py` |
| `player.current_state` | `str` ("up","down","left","right") | [`entities-system.md § "Player States"`](./entities-system.md#top) |

### Public Interface
| Type | Identifier | Notes |
|------|------------|-------|
| Method | `game.intra_map_teleport(target_spawn_id, transition_type)` | Called from `interaction.py` |
| Method | `map_loader.resolve_spawn_by_id(target_spawn_id)` | Called from `game.py` |

### Tracked Concepts
| Concept | Status here | Mentioned in |
|---------|-------------|-------------|
| `transition_type` | Extended with `"walk"` | [`engine-core.md § "7. Spatial Interaction"`](./engine-core.md#top) |
| Teleport trigger | Intra-map branch added | [`map-world-system.md`](./map-world-system.md#top) |

---

## 7. Anti-Patterns

| ❌ Don't | ✅ Do Instead | Why |
|----------|---------------|-----|
| Call `_load_map()` or `transition_map()` for intra-map moves | Use `intra_map_teleport()` | Destroys entities, causes visual flash (the whole problem) |
| Read the TMJ file inside `resolve_spawn_by_id()` | Read `map_manager._entities` (in memory) | A-ARCH-001: no disk I/O inside hot methods |
| Call `check_teleporters()` during walk | Guard with `if _intra_walk_target is not None: return` | Prevents re-triggering the same teleport mid-walk |
| Allow `player.input()` during walk | Skip via early `return` in `_update_core_state()` | G2: all inputs are blocked during scripted walk |
| Duplicate player translation logic inside walk tick | Re-use player.move(dt) by setting target_pos | Avoids resetting is_moving=False every frame, which disables sprite animations and footstep sounds |
| Hardcode walk speed | Use `Settings.PLAYER_SPEED` | G3: walk speed = player normal speed |
| Leave `player.is_moving = True` after walk ends | Set `is_moving = False` + `direction = (0,0)` | A-GAME-003: direction not cleared → retry loop |
| Update `current_state` only at walk start | Update every frame in `_tick_intra_walk()` | G4: facing follows movement direction continuously |

---

## 8. Error Handling Matrix

| Error | Detection | Mitigation | Fallback |
|-------|-----------|------------|----------|
| `target_spawn_id` not found on map | `resolve_spawn_by_id()` returns `None` | Log `error`, return early | Player stays at current position, no crash |
| `target_map` typo that matches current map accidentally | `tp.target_map == _current_map_name` true but spawn not found | Same as above — error log surfaced | No reload triggered (better than wrong reload) |
| `delta.magnitude() == 0` at walk start | `dist <= step` guard (step ≥ 0) | Immediate snap + walk termination | No divide-by-zero, player positioned correctly |
| Walk target unreachable (out of map bounds) | Spawn resolved to valid pixel from `_entities` data | Tiled authoring responsibility; spec doesn't add runtime bounds check | Out-of-bounds position will be clamped by `CameraGroup` |

---

## 9. Test Case Specifications

### 9.1 Unit Tests — `tests/engine/test_intra_map_teleport.py`

| Test ID | Function | Description |
|---------|----------|-------------|
| TC-001 | `test_intra_map_teleport_instant_repositions_player` | `intra_map_teleport("spawn_a", "instant")` → player pos == spawn_a coords, no `_load_map` called |
| TC-002 | `test_intra_map_teleport_walk_sets_walk_state` | `intra_map_teleport("spawn_b", "walk")` → `_intra_walk_target` is set, player.target_pos is updated, is_moving is True |
| TC-003 | `test_intra_map_teleport_unknown_spawn_logs_error_and_returns` | `resolve_spawn_by_id("nonexistent")` returns `None` → no exception, player pos unchanged |
| TC-004 | `test_resolve_spawn_by_id_finds_correct_entity` | `map_manager._entities` has spawn with `spawn_id="door_exit"` → returns correct pixel coords |
| TC-005 | `test_resolve_spawn_by_id_returns_none_on_miss` | No matching spawn → returns `None`, logs warning |
| TC-006 | `test_tick_intra_walk_updates_facing_direction` | `_tick_intra_walk(dt)` updates `player.current_state` based on target vector |
| TC-007 | `test_tick_intra_walk_terminates_on_arrival` | `_tick_intra_walk(dt)` once `player.is_moving` is `False` → clears `_intra_walk_target` and resets direction |
| TC-008 | `test_tick_intra_walk_updates_facing_horizontal` | Walk left → `player.current_state == "left"` |
| TC-009 | `test_tick_intra_walk_updates_facing_vertical` | Walk up → `player.current_state == "up"` |
| TC-010 | `test_update_core_state_blocks_input_during_walk` | `_intra_walk_target` is set → `player.input()` not called |

### 9.2 Integration Tests

| Test ID | Function | Description |
|---------|----------|-------------|
| IT-001 | `test_check_teleporters_routes_intra_map` | Teleport with `target_map == _current_map_name` → `intra_map_teleport()` called, NOT `transition_map()` |
| IT-002 | `test_check_teleporters_routes_cross_map` | Teleport with different `target_map` → `transition_map()` called (regression test) |
| IT-003 | `test_full_walk_cycle_terminates` | Walk from A to B over N frames → `_intra_walk_target == None` at end, `player.pos == target` |

---

## 10. Bundling & Native-Module Audit

- BM1: N/A — pure Python, no CLIENT/SERVER bundling
- BM2: N/A — no bundled framework
- BM3: N/A — no native modules introduced
- BM4: N/A — no field/constant rename

---

## 11. Assumptions

| # | Assumption | Risk | Validation | Source Type |
|---|------------|------|------------|-------------|
| A1 | [SHOW] `Settings.PLAYER_SPEED` is in px/s (int) and consistent with `BaseEntity.start_move()` speed | Low | Grep `PLAYER_SPEED` in `config.py` → verified | SHOW |
| A2 | [SHOW] All destination spawn points have a `spawn_id` property set in Tiled — if missing, `resolve_spawn_by_id()` returns `None` silently | Medium | Map authoring discipline; surfaced by error log → verified | SHOW |
| A3 | [SHOW] The `player.current_state` string values are exactly `"up"`, `"down"`, `"left"`, `"right"` — no other values used for walk animation | Low | Grep `current_state` in `player.py` → verified | SHOW |

---

## 12. Deep Links

- **`check_teleporters()` call site:** [`interaction.py#L290-L297`](../../src/engine/interaction.py#L290-L297)
- **`_position_player()` reused:** [`map_loader.py#L182-L189`](../../src/engine/map_loader.py#L182-L189)
- **`resolve_spawn_by_id()` new method:** [`map_loader.py#L201-L222`](../../src/engine/map_loader.py#L201-L222)
- **`_update_core_state()` insertion point:** [`game.py#L449`](../../src/engine/game.py#L449)
- **`intra_map_teleport()` new method:** [`game.py#L301-L319`](../../src/engine/game.py#L301-L319)
- **`_intra_walk_target` field:** [`game.py#L119`](../../src/engine/game.py#L119)
- **`MapManager._entities` source:** [`map/manager.py#L16`](../../src/map/manager.py#L16)
- **`transition_map()` unchanged:** [`game.py#L254`](../../src/engine/game.py#L254)
- **Strategic blueprint:** [`docs/strategic/intra-map-teleport-blueprint.md`](../strategic/intra-map-teleport-blueprint.md#top)
- **A-GAME-003 (direction clear):** [`.agents/learnings/game_engine.md#A-GAME-003`](../../.agents/learnings/game_engine.md#A-GAME-003)
- **A-ARCH-001 (no disk I/O in hot paths):** [`.agents/learnings/game_engine.md#A-ARCH-001`](../../.agents/learnings/game_engine.md#A-ARCH-001)
