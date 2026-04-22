# Technical Specification - NPC System [Implementation]

This document specifies the technical implementation of the Non-Playable Character (NPC) system, extending the existing `BaseEntity` and `SpriteSheet` architecture.

## 1. Goal Description
To populate the world with static and dynamic NPCs using a decoupled architecture, leveraging existing entity bounds and sprite-sheet rendering systems, enabling basic interactions and localized behaviors.

## 2. Component Changes

### [IMPLEMENTED] `src/entities/npc.py`
The `NPC` class inherits from `BaseEntity` and implements specific AI behaviors.
- **Visuals**: Uses `SpriteSheet` for 4x4 grid animations.
- **States**: `idle`, `wander`, `interact`.
- **Wander Radius**: AI logic enforces a distance check (in tiles) from the original `spawn_pos`.

### [IMPLEMENTED] `src/entities/base.py`
- Provided `interact(initiator)` method stub for subclass overrides.
- Shared movement and boundary logic.

### [PARTIAL] `src/engine/game.py`
- **[IMPLEMENTED]** Manages `npcs` sprite group.
- **[IMPLEMENTED]** Implements spatial interaction logic via `_handle_interactions`.
- **[IMPLEMENTED]** Manage NPC spawning in `_spawn_entities`.
- **[IMPLEMENTED]** Integrated NPCs into `_is_collidable` logic (NPCs act as dynamic obstacles).

---

## 3. 📋 SPEC: NPC AI and Interaction Logic

This section defines the behavior and failure modes for autonomous entities.

### 3.1. Anti-Patterns (DO NOT)

| ❌ Don't | ✅ Do Instead | Why |
|----------|---------------|-----|
| NPCs check collisions with each other | NPCs use `_is_collidable` (shared logic) | Prevents overlapping and ensures physical presence |
| Hardcode NPC dialogue in `npc.py` | Use external JSON/YAML | Allows localization and scale |
| Continuous pathfinding | Intermittent grid step randomizer | Reduces CPU overhead per NPC |
| Move NPCs when off-camera | Freeze distant NPCs (CPU Freeze) | Enlarged viewport (128px) determines `is_visible` |
| `Player` handles dialogue UI | `Game` or `UI_Manager` handles dialogue | Decouples rendering overlay from input entity |
| Manual property parsing in AI logic | Use `TmjParser` properties dict | Centralizes data extraction and simplifies AI classes |

### 3.2. NPC Animation & Facing
- **Rows**: 0:Down, 1:Left, 2:Right, 3:Up (Physical sheet offsets: 0, 4, 8, 12).
- **Animation speed**: Base speed of `1.0 / 0.15` (~6.6 FPS) when moving.
- **Facing**: NPCs automatically rotate to face the player during interaction by calculating the position delta.

### 3.2. Test Case Specifications

#### Unit & Behavior Tests (`tests/test_npc.py`, `tests/test_npc_ai.py`)
| Test ID | Component | Input | Expected Output |
|---------|-----------|-------|-----------------|
| TC-N-01 | NPC Init | Spawn at (16,16) | `NPC.rect.size` == (32,32), anchored correctly |
| TC-N-02 | NPC Wander | Wander radius=1 on a 10x10 map | `NPC.pos` never exceeds radius from spawn |
| TC-N-03 | CPU Freeze | `is_visible`=False passed from `Game` | NPC bypasses `move()` logic |
| TC-N-04 | AI State | Trigger interaction | NPC enters `interact` state and faces player |

#### Integration Tests (`tests/test_interaction.py`, `tests/test_game_helpers.py`)
| Test ID | Flow | Setup | Verification | Teardown |
|---------|------|-------|--------------|----------|
| IT-N-01 | Player interacts | Player faces NPC, presses SPACE or E | `NPC.on_interact()` executes | Clear groups |
| IT-N-02 | NPC Spawn | Tiled Map with NPC data | `Game` spawns instances in `npcs` group | Clear groups |

### 3.3. Error Handling Matrix

| Error Type | Detection | Response | Fallback |
|------------|-----------|----------|----------|
| Missing Spritesheet | `FileNotFoundError` | Use generic blue rectangle (via existing logic) | `is_moving` set false to prevent visual artifacts |
| Invalid Path/Wander | Wall collision returned | Cancel current wander vector | Re-eval after 2s cooldown |
| Missing Dialogue Key | `KeyError` on interaction | Show `...` bubble | Log warning |
| Missing Map Properties | `props.get()` returns `None` | Use engine defaults (NPC speed, etc.) | Log Warning |

## 4. Deep Links
- Camera and Rendering: [ENGINE_CORE.md - Render Constraints](ENGINE_CORE.md#L15)
- Grid Movement Core: [ENGINE_CORE.md - Movement](ENGINE_CORE.md#L27)
