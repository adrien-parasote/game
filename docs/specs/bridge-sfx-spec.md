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
| BRIDGE-U-001 | Footstep System | Player stands on grass tile (`footstep_material="grass"`) | Footstep sound loaded is `footstep_grass_X.ogg` | Property is absent (falls back to default) |
| BRIDGE-U-002 | Interaction | Player stands on `EXTENDED` drawbridge | Traversal allowed (`walkable=True`), footstep overrides to `wood` | Bridge is `RETRACTED` (traversal blocked) |
| BRIDGE-U-003 | State Machine | Lever triggers Drawbridge state to `EXTENDING` | transitional sound `sfx_bridge_gears.ogg` plays | Lever is triggered multiple times in rapid succession |
| BRIDGE-U-004 | Audio Manager | Play transitional sound `sfx_bridge_gears.ogg` | Sound plays on dedicated channel | Channel allocation failure (handles gracefully) |
| BRIDGE-U-005 | Collision | Player overlaps bridge boundary in `EXTENDED` state | `has_overlap` returns `True`, footsteps override to `wood` | Partial boundary overlap |
| BRIDGE-U-006 | State Transitions | Bridge transitions from `EXTENDING` to `EXTENDED` | Transitional gear SFX stops, `walkable` set to `True` | Bridge gets blocked mid-transition |
| BRIDGE-U-007 | Sound Cache | Footstep material requested twice in succession | Sound loaded from cache, no duplicate disk read | Cache gets cleared under low memory |
| BRIDGE-U-008 | Asset Validation | All footstep materials defined in `gameplay.json` | Files exist under `assets/audio/sfx/` | A material has no matching audio file (throws warning) |

### Integration Tests Required

| Test ID | Flow | Setup | Verification | Teardown |
|---------|------|-------|--------------|----------|
| BRIDGE-I-001 | Complete Lever & Drawbridge Cycle | Player triggers lever → Drawbridge extends → Player crosses | Transitional gear SFX plays, stops, footstep switches to `wood`, crossing is successful | Reset entities states |
| BRIDGE-I-002 | Quick Crossing Rejection | Player attempts to cross during `EXTENDING` state | Traversal is blocked, player collision stops movement | Reset player position |

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
| BRIDGE-U-001 | `test_footstep_material_resolution` | `../../tests/entities/test_player.py` |
| BRIDGE-U-002 | `test_bridge_traversal_when_extended` | `../../tests/entities/test_bridge_sfx.py` |
| BRIDGE-U-003 | `test_bridge_extending_plays_gears` | `../../tests/entities/test_bridge_sfx.py` |
| BRIDGE-U-004 | `test_audio_manager_channel_allocation` | `../../tests/engine/test_audio.py` |
| BRIDGE-U-005 | `test_player_overlap_bridge_triggers_material` | `../../tests/engine/test_bridge_sfx_interaction.py` |
| BRIDGE-U-006 | `test_bridge_transitions_to_extended` | `../../tests/entities/test_bridge_sfx_player.py` |
| BRIDGE-U-007 | `test_footstep_sound_caching` | `../../tests/engine/test_audio.py` |
| BRIDGE-U-008 | `test_all_materials_exist_on_disk` | `../../tests/engine/test_audio.py` |
| BRIDGE-I-001 | `test_complete_lever_bridge_cycle` | `../../tests/engine/test_bridge_sfx_interaction.py` |
| BRIDGE-I-002 | `test_crossing_rejected_during_transition` | `../../tests/engine/test_bridge_sfx_interaction.py` |
