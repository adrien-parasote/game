# Technical Specification - NPC System

This document specifies the technical implementation of the Non-Playable Character (NPC) system, extending the existing `BaseEntity` and `SpriteSheet` architecture.

## 1. Goal Description
To populate the world with static and dynamic NPCs using a decoupled architecture, leveraging existing entity bounds and sprite-sheet rendering systems, enabling basic interactions and localized behaviors.

## 2. Component Changes

### [NEW] `src/entities/npc.py`
Creates the `NPC` class inheriting from `BaseEntity`.
- Uses `SpriteSheet` identical to the Player.
- Includes a simple state machine: `idle`, `wander`, `interact`.
- Uses a pathing algorithm restricted to a specified radius from spawn.

### [MODIFY] `src/entities/base.py`
- Add an `interact()` method stub or event hook that can be overridden by subclasses (Player triggering NPC, NPC responding).

### [MODIFY] `src/engine/game.py`
- Add an `npcs` group.
- Handle interaction input (e.g. `SPACE` key) projecting from Player's `target_pos` or `direction` to find a collidable NPC.

---

## 3. Mandatory Spec Sections

### 3.1. Anti-Patterns (DO NOT)

| ❌ Don't | ✅ Do Instead | Why |
|----------|---------------|-----|
| NPCs check collisions with each other | NPCs check `CollisionMap` or rely on Player checking | Optimizes CPU; $O(N^2)$ collision checks drop frame rate |
| Hardcode NPC dialogue in `npc.py` | Use external JSON/YAML | Allows localization and scale |
| Continuous pathfinding | Intermittent grid step randomizer | Reduces CPU overhead per NPC |
| Move NPCs when off-camera | Freeze distant NPCs based on Culling bounds | Prevents simulation of 500 NPCs draining CPU |
| `Player` handles dialogue UI | `Game` or `UI_Manager` handles dialogue | Decouples rendering overlay from input entity |

### 3.2. Test Case Specifications

#### Unit Tests (`tests/test_npc.py`)

| Test ID | Component | Input | Expected Output |
|---------|-----------|-------|-----------------|
| TC-N-01 | NPC Init | Spawn at (16,16) | `NPC.rect.size` == (32,32), anchored correctly |
| TC-N-02 | NPC Wander | Wander radius=1 on a 10x10 map | `NPC.pos` never exceeds radius from spawn |
| TC-N-03 | CPU Freeze | `is_visible`=False passed from `Game` | NPC bypasses `move()` logic |

#### Integration Tests (`tests/test_interaction.py`)

| Test ID | Flow | Setup | Verification | Teardown |
|---------|------|-------|--------------|----------|
| IT-N-01 | Player interacts | Player faces NPC, presses SPACE | `NPC.on_interact()` executes | Clear groups |

### 3.3. Error Handling Matrix

| Error Type | Detection | Response | Fallback |
|------------|-----------|----------|----------|
| Missing Spritesheet | `FileNotFoundError` | Use generic blue rectangle (via existing logic) | `is_moving` set false to prevent visual artifacts |
| Invalid Path/Wander | Wall collision returned | Cancel current wander vector | Re-eval after 2s cooldown |
| Missing Dialogue Key | `KeyError` on interaction | Show `...` bubble | Log warning |

## 4. Deep Links
- Camera and Rendering: [ENGINE_CORE.md - Render Constraints](file:///Users/adrien.parasote/Documents/perso/game/docs/specs/ENGINE_CORE.md#L15)
- Grid Movement Core: [ENGINE_CORE.md - Movement](file:///Users/adrien.parasote/Documents/perso/game/docs/specs/ENGINE_CORE.md#L27)
