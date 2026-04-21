# Technical Specification: World & Interaction System

This document defines the behavior of map transitions (teleports) and the refined interaction model for world objects.

## 1. System Overview
The system manages how the player interacts with the environment and transitions between map files. It prioritizes "Intentionality" — ensuring actions only occur when the player is correctly oriented and positioned.

## 2. Interaction Model

### 2.1 Standard Proximity Interaction
Triggered by `Settings.INTERACT_KEY`. Valid if:
- Distance between player center and object footprint center < 45px.
- Player is facing the object (e.g., if object faces 'down', player must face 'up' and be below it).

### 2.2 Refined `activate_from_anywhere`
Even if an object has `activate_from_anywhere = true`, it now requires **Directional Adjacency**.
- **Distance**: < 48px.
- **Facing**: Player must be looking towards the object.
- **Logic**: 
  - If horizontal distance > vertical distance: Player must face `right` if `dx > 0`, or `left` if `dx < 0`.
  - Otherwise: Player must face `down` if `dy > 0`, or `up` if `dy < 0`.

## 3. Teleportation System

### 3.1 Detection
Teleporters are detected in Tiled maps strictly by the property:
- `name`: "type"
- `value`: "teleport"

### 3.2 Trigger Logic (`required_direction`)
Teleporters are passive (trigger on arrival) but gated by intent:
- **`required_direction = "any"`** (Default): Triggers as soon as player enters the rect regardless of facing.
- **`required_direction = [up/down/left/right]`**: Triggers ONLY if the player's `current_state` matches the value.

## 4. Anti-Patterns

| ❌ Don't | ✅ Do Instead | Why |
|----------|---------------|-----|
| Use Tiled "Class" or numerical IDs for detection | Check for `type=teleport` property | Decouples logic from Tiled versioning/internal IDs |
| Trigger teleport on every frame in rect | Trigger only when `is_moving` becomes `False` | Prevents infinite loading loops |
| Allow interaction while facing away | Use `_facing_toward` helper | Increases realism and control precision |
| Hardcode map paths in loaders | Join paths via `os.path.join` and config | Ensures cross-platform compatibility |
| Clear player group on map load | Move player to new spawn then re-add | Preserves player state across maps |

## 5. Test Case Specifications

### 5.1 Unit Tests (`tests/test_world_teleport.py`)
| Test ID | Scenario | Input | Expected Result |
|---------|----------|-------|-----------------|
| TC-006 | Strict Detection | Property `type=teleport` | Object spawned as `Teleport` |
| TC-007 | Directional Adjacency | `activate_from_anywhere=True`, Facing away | Interaction fails |
| TC-008 | Teleport Guard (Invalid) | `req_dir="down"`, Player facing "up" | No transition |
| TC-009 | Teleport Guard (Valid) | `req_dir="down"`, Player facing "down"| `transition_map` called |
| TC-010 | Teleport 'Any' | `req_dir="any"`, Player facing any | `transition_map` called |

## 6. Error Handling Matrix

| Error Type | Detection | Mitigation | Result |
|------------|-----------|------------|--------|
| Missing Map | `os.path.exists(path)` is False | Log error, cancel transition | Player stays on current map |
| Missing Spawn ID| Spawn ID not found in entities | Log warning, spawn in map center | Player safe-spawns at center |
| Invalid Config | `required_direction` value typo | Default to "any" behavior | Teleport remains functional |

## 7. Deep Links
- **Spawning Logic**: [game.py:L168](file:///Users/adrien.parasote/Documents/perso/game/src/engine/game.py#L168)
- **Interaction Logic**: [game.py:L281](file:///Users/adrien.parasote/Documents/perso/game/src/engine/game.py#L281)
- **Teleport Check**: [game.py:L415](file:///Users/adrien.parasote/Documents/perso/game/src/engine/game.py#L415)
- **Teleport Entity**: [teleport.py](file:///Users/adrien.parasote/Documents/perso/game/src/entities/teleport.py)
