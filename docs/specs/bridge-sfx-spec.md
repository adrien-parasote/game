[assumption: "All implicit constants and defaults are documented here – pending detailed entries"] – risk: Low

> Document Type: Implementation
# Drawbridge SFX Interaction Spec

This document specifies the interaction between the player's footsteps, Tiled tile properties (`walkable`, `footstep_material`, `sound_override`), and interactive bridge/drawbridge entity states.

---

## 1. Core Architecture

The footstep material system must dynamically resolve the surface under the player's feet at 60 FPS:

```
[BaseEntity.update] → [resolve_footstep_material()]
                               ↓
                   Query active map coordinate
                               ↓
             ┌─────────────────┴─────────────────┐
             ↓                                   ↓
      Is interactive entity?              Check background tile
             ↓                                   ↓
      Is it a Drawbridge?               Get 'footstep_material'
      (BridgeState: EXTENDED              (e.g., 'stone', 'grass', 'wood')
       -> Override: 'wood')
```

### 1.1 Resolution Priority
1. **Interactive Entities**: If the player is overlapping an active collision box of an interactive entity (e.g., a chest, lever, or bridge) that defines a material, this material takes absolute priority.
   - For a `Drawbridge` entity, the footprint material is dynamically overridden to `wood` if the drawbridge's state is `EXTENDED`. If the state is `RETRACTED` (and walkability constraints permit traversal), it falls back to the map tile's material.
2. **Background Tile**: Query the top layer of the map at the player's central tile coordinate. Read the custom property `footstep_material` (string).
   - If a custom property is defined, it is loaded.
   - If absent, it falls back to the default material: `stone` for indoors, `grass` for outdoors.

### 1.2 Interactive Entity State and SFX
An interactive bridge has 4 states (as defined in `src/entities/interactive.py`):
1. `RETRACTED` (default: closed/blocked)
2. `EXTENDING` (transitional: plays drawbridge extending mechanical gear SFX)
3. `EXTENDED` (opened/traversable: allows passage and overrides footsteps to `wood`)
4. `RETRACTING` (transitional: plays drawbridge retracting mechanical gear SFX)

---

## Assumptions

| Assumption | Risk Level | Implication | Validation |
|------------|------------|-------------|------------|
| Footstep audio channel limits | Low | Maximum 2 footstep audio channels play concurrently | High-speed co-op can trigger overlap. Addressed by standard mixer settings. |
| Material names match file names | Low | `footstep_{material}_{index}.ogg` files must exist on disk | Checked by tests |
| Entity overlapping boundaries | Low | Entity boundary checks are strictly 2D | Verified by overlap logic |

---

## 2. Anti-Patterns (DO NOT)

| ❌ Don't | ✅ Do Instead | Why |
|----------|---------------|-----|
| Play a loop of footstep sounds continuously | Trigger footstep sounds at specific frame markers within the entity's walk cycle | Matches player's visual movements and avoids audio spam |
| Hardcode the mapping between materials and filenames in the engine | Dynamically construct the file path using the material property: `assets/audio/sfx/footstep_{material}.ogg` | Simplifies adding new terrain types (e.g. `sand`, `water`) |
| Allow player traversal when bridge state is `EXTENDING` or `RETRACTING` | Set `walkable = False` on the entity during transitional states | Prevents the player from walking on empty space or getting stuck in walls |
| Let the drawbridge gear mechanical sound play infinitely | Stop the transitional gear SFX loop as soon as the bridge reaches the final target state (`EXTENDED` or `RETRACTED`) | Prevents ear fatigue and auditory clutter |

---

## 3. Test Case Specifications

### Unit Tests Required

| Test ID | Component | Input | Expected Output | Edge Cases |
|---------|-----------|-------|-----------------|------------|
| BRIDGE-U-001 | Bridge SFX | `sfx_open="bridge_open"` | `entity.sfx_open == "bridge_open"` | — |
| BRIDGE-U-002 | Bridge SFX | `sfx_close="bridge_close"` | `entity.sfx_close == "bridge_close"` | — |
| BRIDGE-U-003 | Bridge SFX | `material="wood"` | `entity.material == "wood"` | — |
| BRIDGE-U-004 | Bridge SFX | No `sfx_open` provided | `entity.sfx_open == ""` | — |
| BRIDGE-U-005 | Bridge SFX | No `sfx_close` provided | `entity.sfx_close == ""` | — |
| BRIDGE-U-006 | Bridge SFX | No `material` provided | `entity.material == ""` | — |
| BRIDGE-U-007 | Interaction | `is_on=True`, `sfx_open` set | `_resolve_sfx` returns `sfx_open` | — |
| BRIDGE-U-008 | Interaction | `is_on=False`, `sfx_close` set | `_resolve_sfx` returns `sfx_close` | — |
| BRIDGE-U-009 | Interaction | `is_on=True`, `sfx_open=""` | `_resolve_sfx` falls back to `sfx` | — |
| BRIDGE-U-010 | Interaction | `is_on=False`, `sfx_close=""` | `_resolve_sfx` falls back to `sfx` | — |
| BRIDGE-U-011 | Interaction | `sfx`, `sfx_open`, `sfx_close` empty | `_resolve_sfx` returns `""` | — |
| BRIDGE-U-012 | Interaction | Legacy entity (no `sfx_open`/`sfx_close` attrs) | `_resolve_sfx` returns `sfx` | Backward-compatibility guard |
| BRIDGE-U-013 | Player SFX | Override entity with `material="wood"` at player pos | `_resolve_footstep_material` returns `wood` | — |
| BRIDGE-U-014 | Player SFX | Override entity with `material=""` at player pos | `_resolve_footstep_material` falls back to map terrain | — |
| BRIDGE-U-015 | Player SFX | No override entities on map | `_resolve_footstep_material` uses map terrain | — |
| BRIDGE-U-016 | Player SFX | Player not on override entity | `_resolve_footstep_material` uses map terrain | Regression check |

### Integration Tests Required

| Test ID | Flow | Setup | Verification | Teardown |
|---------|------|-------|--------------|----------|
| BRIDGE-I-001 | Lever triggers bridge ON | Lever target is bridge; pull lever | Bridge toggled ON, plays `sfx_open` | Reset |
| BRIDGE-I-002 | Lever triggers bridge OFF | Lever target is bridge; pull lever again | Bridge toggled OFF, plays `sfx_close` | Reset |
| BRIDGE-I-003 | Footsteps on lowered bridge | Bridge lowered (`is_on=True`, `material="wood"`); player walks on it | Plays `04-footstep_wood` instead of water sound | — |

---

## 4. Error Handling Matrix

| Error Type | Detection | Response | Fallback | Logging | Alert |
|------------|-----------|----------|----------|---------|-------|
| Missing footstep SFX file | `FileNotFoundError` during sound load | Play fallback footstep sound | Stone or grass fallback sound | ERROR | None |
| Audio Mixer busy | `pygame.error` raised during `play()` | Gracefully ignore play request | Skip sound trigger this frame | WARN | None |
| Invalid material property | String parsed does not match known materials | Interpret as default material | Default `stone` footstep sound | WARN | None |

---

## 5. Deep Links
- **`Drawbridge` entity class**: [interactive.py L121](../../src/entities/interactive.py#L121)
- **Footstep material resolver**: [player.py L156](../../src/entities/player.py#L156)
- **Audio play triggers**: [audio.py L43](../../src/engine/audio.py#L43)

### Linked Test Functions

| Test ID | Test Function | File |
|---------|---------------|------|
| BRIDGE-U-001 | `test_sfx_open_stored_on_entity` | `../../tests/entities/test_bridge_sfx.py` |
| BRIDGE-U-002 | `test_sfx_close_stored_on_entity` | `../../tests/entities/test_bridge_sfx.py` |
| BRIDGE-U-003 | `test_material_stored_on_entity` | `../../tests/entities/test_bridge_sfx.py` |
| BRIDGE-U-004 | `test_sfx_open_defaults_to_empty_string` | `../../tests/entities/test_bridge_sfx.py` |
| BRIDGE-U-005 | `test_sfx_close_defaults_to_empty_string` | `../../tests/entities/test_bridge_sfx.py` |
| BRIDGE-U-006 | `test_material_defaults_to_empty_string` | `../../tests/entities/test_bridge_sfx.py` |
| BRIDGE-U-007 | `test_sfx_open_used_when_on` | `../../tests/engine/test_bridge_sfx_interaction.py` |
| BRIDGE-U-008 | `test_sfx_close_used_when_off` | `../../tests/engine/test_bridge_sfx_interaction.py` |
| BRIDGE-U-009 | `test_fallback_to_sfx_when_sfx_open_empty_and_on` | `../../tests/engine/test_bridge_sfx_interaction.py` |
| BRIDGE-U-010 | `test_fallback_to_sfx_when_sfx_close_empty_and_off` | `../../tests/engine/test_bridge_sfx_interaction.py` |
| BRIDGE-U-011 | `test_returns_empty_when_all_sfx_empty` | `../../tests/engine/test_bridge_sfx_interaction.py` |
| BRIDGE-U-012 | `test_legacy_entity_without_sfx_open_close_uses_sfx` | `../../tests/engine/test_bridge_sfx_interaction.py` |
| BRIDGE-U-013 | `test_override_entity_with_material_returns_material` | `../../tests/entities/test_bridge_sfx_player.py` |
| BRIDGE-U-014 | `test_override_entity_with_empty_material_falls_back_to_map` | `../../tests/entities/test_bridge_sfx_player.py` |
| BRIDGE-U-015 | `test_no_override_entity_uses_map_manager` | `../../tests/entities/test_bridge_sfx_player.py` |
| BRIDGE-U-016 | `test_regression_tile_material_returned_when_no_override` | `../../tests/entities/test_bridge_sfx_player.py` |
| BRIDGE-I-001 | `test_trigger_object_plays_sfx_open_when_toggled_on` | `../../tests/engine/test_bridge_sfx_interaction.py` |
| BRIDGE-I-002 | `test_trigger_object_plays_sfx_close_when_toggled_off` | `../../tests/engine/test_bridge_sfx_interaction.py` |
| BRIDGE-I-003 | `test_footstep_uses_bridge_material_wood` | `../../tests/entities/test_bridge_sfx_player.py` |
