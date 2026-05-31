# Strategic Blueprint — Intra-Map Teleport + Walk Camera Transition

> Version 1.0 · 2026-05-22 · Status: STRATEGY

---

## 1. Exact Problem to Solve

**Scenario:** The player enters a castle. The door is a Tiled `Teleport` zone.  
**Current Problem:** `target_map == _current_map_name` → `transition_map()` → `_load_map()` → the entire map is destroyed and reloaded: entities are cleared, spawn is repositioned, and an optional fade occurs. Result: white/black flash, loss of context, and the same map restarts from scratch.  
**Secondary Problem:** No `transition_type` makes the camera follow while the player WALKS from the source zone to the destination zone. The only smooth option is `"fade"` (fade to black), which hides the movement.

**Expected Outcome:**
- Intra-map teleport: zero reloads, zero flashes, entities preserved.
- `transition_type = "walk"`: the player moves automatically in a straight line from A→B, the camera follows in real-time, and everything remains visible on screen.

---

## 2. Success Metrics

| Criterion | Measure |
|---------|--------|
| Zero map reloads | `_load_map()` is not called when `target_map == _current_map_name` |
| Entities preserved | Sprites remain in their groups after teleportation |
| Smooth transition | 60 FPS maintained during the `"walk"` (profiler confirms < 8ms/frame) |
| Camera follows the player | `visible_sprites.offset` is updated at each frame of the walk |
| Tiled integration | No new Tiled properties required (reuses `target_map`, `target_spawn_id`, `transition_type`) |

---

## 3. Architectural Advantage

The existing system is already close to the solution:
- `Teleport` stores `target_map`, `target_spawn_id`, and `transition_type` → no new properties.
- `CameraGroup.calculate_offset()` tracks the player at each frame → if the player walks toward the destination, the camera follows naturally.
- `_position_player()` in `MapLoader` is already isolated → reusable without `_load_map()`.
- `WorldState` + `_save_interactive_states()` protect states (A-ML-001) → no risk of loss.

---

## 4. Main Architectural Decision

### Q4: Movement Mechanism for `"walk"` — Lerp vs Pathfinding vs Simulated Input

Three options:

| Option | Mechanism | Pro | Con |
|--------|-----------|-----|-----|
| **A — Direct Lerp** | Tweening pos A→B in N frames | Simple, predictable, 0 collision risk | Ignores the collision system (but this is intentional — the teleport has authority) |
| **B — Simulated Inputs** | Push `player.direction` toward target | Reuses `player.input()` | Hard to end precisely, drift possible |
| **C — Pathfinding** | Calculate path tile-by-tile | Respects obstacles | Disproportionate complexity for a straight corridor |

**DECISION: Option A — Direct Lerp in `game.py`.**

Rationale:
1. An entry-type teleport into a building is always a STRAIGHT trajectory (corridor, door).
2. The player does not need to bypass obstacles — the teleport overrides physics.
3. Lerp = 10 lines in `game.py`, no new dependencies.
4. Duration is configurable: `INTRA_WALK_SPEED = 4` tiles/second by default.
5. Consistent with `L-ARCH-005`: no Manager/Factory for what is resolvable in a single function.

**Consequences:**
- During the walk, `player.input()` is suspended (movement is scripted).
- Collisions do not apply (the teleport has authority over the path).
- The camera follows via normal `calculate_offset()` — no modification to `CameraGroup`.

---

## 5. Technical Stack & Rationale

| Component | Technology | Rationale |
|-----------|-------------|-----------|
| Intra-map detection | `interaction.py` | This is where `check_teleporters()` already lives |
| Walk controller | `game.py` method `intra_map_teleport()` | Pattern L-ARCH-008: context injection `game: Any` |
| Spawn resolution | `map_loader.py` method `resolve_spawn_by_id()` | MapLoader owns the knowledge of the spawn |
| Movement | Direct Lerp on `player.pos` + `player.rect` | No dependency on `player.input()` |
| Camera | Existing `CameraGroup.calculate_offset()` | No changes required |
| Tiled | Existing properties (`target_map`, `target_spawn_id`, `transition_type="walk"`) | Zero new properties |

---

## 6. Features — Ordered by Dependency

### Feature 1: Intra-map detection in `check_teleporters()`
`interaction.py` — branching: same map → `game.intra_map_teleport()`, different map → `game.transition_map()` (unchanged).

### Feature 2: `MapLoader.resolve_spawn_by_id()` 
`map_loader.py` — reads spawn entities from `self.game.map_manager` (in memory) to find the pixel coordinates of the `target_spawn_id`.

> ⚠️ **Gap G1**: Does `map_manager` in memory expose spawn entities? Verify if `TmjParser` stores entities or only tiles.

### Feature 3: `game.intra_map_teleport(target_spawn_id, transition_type)`
`game.py` — dispatcher:
- `"instant"` → calls `_map_loader._position_player(spawn_pos)` directly.
- `"walk"` → starts a frame-by-frame lerp loop.

### Feature 4: Walk loop in `_update_core_state()`
`game.py` — state `_intra_walk_active`: if active, moves `player.pos` one step closer to `_walk_target` each frame, calculates the player orientation based on the walk direction.

### Feature 5: Tests
- TC-01: Intra-map `"instant"` teleport → reposition without reload.
- TC-02: Intra-map `"walk"` teleport → starts the walk loop.
- TC-03: Walk ends → `_intra_walk_active = False`, position = target.
- TC-04: Cross-map teleport → `transition_map()` called (regression check).

---

## 7. What We Do NOT Build

| Exclusion | Rationale |
|-----------|-----------|
| ❌ A* Pathfinding for the walk | Disproportionate — teleport corridors are straight by design |
| ❌ New Tiled property type | Existing properties are sufficient |
| ❌ Modification to `CameraGroup` | `calculate_offset()` tracks the player naturally |
| ❌ Camera Lerp (separate camera tween) | Unnecessary if the player lerps — the camera follows |
| ❌ Door animation (open/close) | Out of scope — managed by existing interactive items |
| ❌ Multi-step waypoints | Out of scope — always straight line A→B |

---

## Gap Discovery — ✅ ALL RESOLVED

| # | Gap | Decision |
|---|-----|----------|
| **G1** ✅ | Does `map_manager` expose spawn entities in memory? | YES — `MapManager._entities` (line 16) stores the complete list of entities, including spawn points. `resolve_spawn_by_id()` can search directly inside `self.game.map_manager._entities`. |
| **G2** ✅ | Inputs during the walk? | **Completely blocked** — no movement, inventory, or interaction during the transition. |
| **G3** ✅ | Duration vs Speed? | **Fixed Speed** = same `px/s` as normal player movement (`Settings.PLAYER_SPEED`). Short distance = fast transition, long distance = slower transition. Natural and coherent. |
| **G4** ✅ | Orientation during the walk? | **Tracks the direction of the automatic movement** — if the player walks upward, `player.current_state = "up"`. The walk animation plays normally. |

---

*All gaps are resolved → ready for SPEC.*
