# Technical Specification: World & Interaction System

> Document Type: Implementation


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
  
### 2.3 Visual Proximity Indicators (Emotes)
The engine provides visual feedback to guide the player toward interactions.
- **Trigger**: Automatic `interact` (!) emote when `distance < 48px` to an interactive object or NPC.
- **Gating**: Only triggers if no emote is currently active to prevent visual clutter.
- **Feedback**: Provides immediate spatial awareness of interactable elements before the player presses any key.

## 3. Teleportation System

### 3.1 Detection
Teleporters are detected in Tiled maps strictly by the property:
- `name`: "type"
- `value`: "teleport"

### 3.2 Trigger Logic (`required_direction`)
Teleporters support dual-triggering mechanisms to balance convenience and control:

#### A. Arrival Trigger (Default)
- **Condition**: Triggers exactly when a movement step ends (`was_moving=True`, `is_moving=False`) while the player's physical hitbox overlaps the teleport volume.
- **Direction Guard**: If `required_direction` is NOT `"any"`, the player's final facing direction (`current_state`) must match the property.
- **Use Case**: Entering a building or crossing a map boundary while walking.

#### B. Intent Trigger (Responsive)
- **Condition**: Triggers while the player is already idle inside the teleport rect and pushes a movement key (`magnitude > 0`) in the `required_direction`.
- **Logic**: This allows a teleport to fire even if the move is physically blocked (e.g., trying to walk "into" a wall that is actually a portal).
- **'Any' Exception**: Portals with `required_direction="any"` **ignore Intent triggers**. This is a critical safety feature to prevent players from getting stuck in an infinite loop (teleporting, then immediately teleporting back when trying to walk away).

### 3.3 Map Loading Pipeline (`_load_map`)
1. **Clean Slate**: Disposes of all current entities except the persistent `Player`.
2. **Data Fetch**: `TmjParser` resolves the JSON/TMJ file and applies Project Resolver logic.
3. **WorldState Query**: Before spawning, the engine checks for saved states using `{map}_{id}` keys.
4. **Placement**: Player is moved to the target `00-spawn_point`.
5. **Finalization**: SFX is played, and the screen fade is cleared.


## 5. WorldState Persistence

### 5.1 Concept
The world must have an infallible memory. When an interactive object changes state (e.g. a door opens, a lever is pulled), this change must be remembered persistently throughout the game session, even if the player transitions between maps.

### 5.2 Persistence Key
Every interactive object is assigned a unique persistence key based on its map and native Tiled ID:
`{map_basename}_{tiled_id}`
Example: The lever with ID 58 in `01-castel.tmj` will have the key `01-castel_58`.

### 5.3 Behavior — Interactive Objects
- **Spawn Registration**: When a map loads, the engine constructs the `InteractiveEntity`. Before generating its visual layout, the engine queries the `WorldState` dictionary using the persistence key. If a state exists (e.g., `{'is_on': True}`), the object's `is_on` status is overridden, and its visual frame is snapped immediately.
- **State Mutation**: When an interaction resolves (by the player hitting the interact key, or via an interaction chain), the updated `is_on` state is written to the `WorldState` dictionary via its key.

### 5.4 Behavior — Pickup Items
Pickups use the same `{map_basename}_{tiled_id}` key format.

| Event | WorldState write | Spawn behavior |
|-------|-----------------|----------------|
| Full pickup (`remaining == 0`) | `{"collected": True}` | **Skip spawn** — item never appears again this session |
| Partial pickup (`remaining > 0`) | `{"quantity": remaining}` | Spawn with restored quantity |
| No event (never touched) | No entry | Spawn with original Tiled quantity |

**Key source:** Native Tiled `obj["id"]` integer (guaranteed unique per map, requires zero manual config).
**Key attachment:** `_world_state_key` is set on the `PickupItem` instance at spawn time, mirroring the interactive object pattern.

## 6. Anti-Patterns

| ❌ Don't | ✅ Do Instead | Why |
|----------|---------------|-----|
| Use Tiled "Class" or numerical IDs for teleport detection | Check for `type=teleport` property | Decouples logic from Tiled versioning/internal IDs |
| Trigger teleport on every frame in rect | Trigger on Arrival (move end) or Intent (direction magnitude while idle) | Prevents infinite loading loops while supporting responsive transitions |
| Allow interaction while facing away | Use `_facing_toward` helper | Increases realism and control precision |
| Hardcode map paths in loaders | Join paths via `os.path.join` and config | Ensures cross-platform compatibility |
| Clear player group on map load | Move player to new spawn then re-add | Preserves player state across maps |
| Target `element_id` as persistence primary key | Target Native Tiled `obj['id']` | The Tiled ID is always present and guaranteed unique per TMJ file. `element_id` relies on manual configuration and could be missing. |
| Persist position of objects | Persist only `is_on` | Current engine objects are static. Persisting state changes covers all interactive logic needs without inflating the footprint. |
| Save WorldState per-frame | Save only in `interact()` or toggles | Avoiding excessive state writes preserves 60FPS target. |
| Call `pickup.kill()` without a WorldState write | Always `world_state.set(key, {"collected": True})` before `kill()` | Without persistence, item respawns at full quantity on next map load. |
| Omit `_world_state_key` from spawned `PickupItem` | Always attach `item._world_state_key = state_key` in `_spawn_pickup` | Key must be on the entity to be accessible at collection time in `InteractionManager`. |

## 7. Test Case Specifications

### 7.1 Unit Tests (`tests/test_world_teleport.py`)
| Test ID | Scenario | Input | Expected Result |
|---------|----------|-------|-----------------|
| TC-006 | Strict Detection | Property `type=teleport` | Object spawned as `Teleport` |
| TC-007 | Directional Adjacency | `activate_from_anywhere=True`, Facing away | Interaction fails |
| TC-008 | Teleport Guard (Invalid) | `req_dir="down"`, Player facing "up" | No transition |
| TC-009 | Teleport Guard (Valid) | `req_dir="down"`, Player facing "down"| `transition_map` called |
| TC-010 | Teleport 'Any' | `req_dir="any"`, Player facing any | `transition_map` called |

### 7.2 Unit Tests (`tests/test_world_state.py`)
| Test ID | Scenario | Expected Result |
|---------|----------|-----------------|
| WS-001 | `make_key("00-spawn.tmj", 58)` | `"00-spawn_58"` |
| WS-002 | `set` then `get` | Value properly stored and retrieved |
| WS-003 | `get` inexistent key | `None` returned |
| WS-004 | Entity spawn (Saved ON) | `is_on` is True, `frame_index` at `end_row` |
| WS-005 | Entity spawn (Saved OFF) | `is_on` is False, `frame_index` at `start_row` |
| WS-006 | Standard interact saves state | `world_state.get()` reflects ON state |
| WS-007 | Map reload maintains state | Full simulation of `A -> B -> A` loads the correct toggled state |
| WS-008 | Interaction chaining saves state | State correctly updated via `toggle_entity_by_id` |
| WS-009 | Full pickup persists `collected: True` | `world_state.set(key, {"collected": True})` called before `kill()` |
| WS-010 | Partial pickup persists remaining quantity | `world_state.set(key, {"quantity": N})` written when inventory full |
| WS-011 | Spawn skips collected item | No `PickupItem` spawned when `world_state` has `collected: True` |
| WS-012 | Spawn restores partial quantity | `PickupItem` spawned with `quantity=N` from `world_state` |

## 8. Error Handling Matrix

| Error Type | Detection | Mitigation | Result |
|------------|-----------|------------|--------|
| Missing Map | `os.path.exists(path)` is False | Log error, cancel transition | Player stays on current map |
| Missing Spawn ID| Spawn ID not found in entities | Log warning, spawn in map center | Player safe-spawns at center |
| Invalid Config | `required_direction` value typo | Default to "any" behavior | Teleport remains functional |

## 9. Deep Links
- **Spawning Logic**: [game.py:L168](../../src/engine/game.py#L168)
- **Interaction Logic**: [game.py:L281](../../src/engine/game.py#L281)
- **Teleport Check**: [game.py:L415](../../src/engine/game.py#L415)
- **Teleport Entity**: [teleport.py L1](../../src/entities/teleport.py#L1)
- **Loot Table Initialization**: [loot-table-spec.md](./loot-table-spec.md#loot-table)

### Linked Test Functions

| Test ID | Test Function | File |
|---------|---------------|------|
| TC-006 | `test_game_entity_spawning` | `../../tests/engine/test_game.py:L80` |
| TC-007 | `test_interaction_orientation` | `../../tests/engine/test_interaction.py:L68` |
| TC-008 | `test_interaction_check_teleporters` | `../../tests/engine/test_interaction.py:L496` |
| TC-009 | `test_interaction_check_teleporters` | `../../tests/engine/test_interaction.py:L496` |
| TC-010 | `test_interaction_check_teleporters` | `../../tests/engine/test_interaction.py:L496` |
