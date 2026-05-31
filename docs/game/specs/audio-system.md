# Technical Specification — Audio System [Implementation]

> **Document Type:** Implementation
> **Source:** `src/engine/audio.py` (253 LOC), `src/entities/interactive.py`, `src/entities/player.py`

This document specifies the AS-IS implementation and integration of the `AudioManager` subsystem, including ambient propose/flush systems and dynamic footstep material resolution.

---

## 1. Goal Description

Manage all game audio:
- **Background Music (BGM)**: Continuous playback with a seamless cross-map transition system (continuum rule).
- **Sound Effects (SFX)**: Dynamic preloading, playing, and stopping to prevent flanging under rapid triggers.
- **Ambient Loops**: Propose/flush per-frame model with distance-based falloff.
- **Footstep SFX Resolution**: Frame-by-frame (60 FPS) surface material detection with dynamic interactive entity overrides (e.g., Drawbridges) and map-tile fallback.

---

## 2. Component Overview

| Module | File | LOC | Responsibility |
|--------|------|-----|----------------|
| `AudioManager` | `src/engine/audio.py` | 253 | BGM, SFX, ambient loop management |
| `resolve_footstep_material` | `src/entities/player.py` | — | Resolves material under player's feet (entity vs map tile) |
| `Drawbridge` | `src/entities/interactive.py` | — | Extends/retracts, overrides footstep material to `wood` |

### Instantiation
- `AudioManager` is instantiated once by `Game.__init__()` and stored as `game.audio`.
- It is NOT a strict singleton, but acts as a unique manager accessed via the `game` context.

### External Dependencies
- `pygame.mixer` — mixer initialization, channels, Sound/Music objects.
- `src.config.Settings` — `BGM_VOLUME`, `SFX_VOLUME` configured dynamically.

---

## 3. Constants & Settings

| Constant | Value | Source | Purpose |
|----------|-------|------------|---------|
| `AMBIENT_VOLUME_SCALE` | `0.8` | `audio.py:10` | Max fraction of `SFX_VOLUME` for ambient sounds |
| `AMBIENT_MAX_DISTANCE` | `300.0` | `audio.py:13` | Distance (px) at which ambient volume reaches minimum |
| `AMBIENT_MIN_FALLOFF` | `0.05` | `audio.py:14` | Floor multiplier — ambient never drops below 5% |
| Mixer channels | `32` | `audio.py:48` | Total pygame mixer channels allocated |

---

## 4. Interfaces & Core Behaviors

### 4.1. Initialization
```python
def __init__(self) -> None
```
1. Set `bgm_dir = "assets/audio/bgm"`, `sfx_dir = "assets/audio/sfx"`.
2. Initialize `pygame.mixer` if not already initialized.
3. Set 32 mixer channels via `pygame.mixer.set_num_channels(32)`.
4. If mixer init fails, set `is_enabled = False` and return early.
5. Call `preload_sfx()` to cache all `.ogg` files from `sfx_dir`.

**State initialized**:
| Attribute | Type | Initial Value |
|-----------|------|---------------|
| `current_bgm` | `str \| None` | `None` |
| `sounds` | `dict[str, Sound]` | Populated by `preload_sfx()` |
| `ambient_sounds` | `dict[str, Sound]` | `{}` |
| `ambient_channels` | `dict[str, Channel]` | `{}` |
| `_ambient_proposals` | `dict[str, float]` | `{}` |
| `is_muted` | `bool` | `False` |
| `is_enabled` | `bool` | `True` (if mixer init succeeds) |

### 4.2. Background Music (BGM)
```python
def play_bgm(self, name: str, loop: bool = True, fade_ms: int = 500) -> None
```
1. If `name == self.current_bgm` AND music is playing -> **no-op** (continuum rule).
2. Load `assets/audio/bgm/{name}.ogg`.
3. Set volume to `Settings.BGM_VOLUME`.
4. Play with `loops=-1` (infinite) if `loop=True`, else `loops=0`.
5. Apply fade-in of `fade_ms` milliseconds.
6. Update `self.current_bgm = name`.

> [!NOTE]
> **Continuum Rule**: When transitioning between maps that share the same BGM track name, the music is NOT restarted. This ensures seamless map transitions.

```python
def stop_bgm(self, fade_ms: int = 500) -> None
```
Fade out current BGM over `fade_ms` ms, and set `current_bgm = None`.

### 4.3. Sound Effects (SFX)
```python
def preload_sfx(self) -> None
```
Scan `sfx_dir` for all `.ogg` files, load each as `pygame.mixer.Sound`, and cache in `self.sounds` keyed by filename without extension.

```python
def play_sfx(self, name: str, source_id: str | None = None, volume_multiplier: float = 1.0) -> bool
```
1. Look up `name` in preloaded `self.sounds`.
2. If not found, attempt lazy load from `sfx_dir/{name}.ogg`.
3. **Stop** the sound if already playing (prevents flanging from rapid triggers).
4. Set volume to `Settings.SFX_VOLUME * volume_multiplier`.
5. Play on the first available channel.
6. Return `True` on success, `False` on failure.

---

## 5. Ambient Audio — Propose/Flush Model

### 5.1 Architecture

```
Frame N:
  entity_A.update() → audio.propose_ambient("fire_loop", dist=50)
  entity_B.update() → audio.propose_ambient("fire_loop", dist=120)
  entity_C.update() → audio.propose_ambient("water_loop", dist=80)

  game._update() → audio.flush_ambient()
    → fire_loop: volume = falloff(min(50, 120)) = falloff(50)
    → water_loop: volume = falloff(80)
    → any previously active sound with 0 proposals → channel.stop()
```

```python
def propose_ambient(self, name: str, distance: float) -> None
```
Record `min(existing_proposal, distance)` for `name` in `_ambient_proposals`. Multiple entities proposing the same sound name -> closest wins.

```python
def flush_ambient(self) -> None
```
Called once per frame in `Game._update()`:
1. For each proposal `(name, min_dist)`:
   - If `name` not in `ambient_sounds` -> load `.ogg`, start looping on a new channel.
   - Compute volume: `SFX_VOLUME * AMBIENT_VOLUME_SCALE * falloff(min_dist)`.
   - Apply volume to the sound object.
2. For each `name` in `ambient_sounds` NOT in current proposals -> stop its channel, remove from tracking.
3. Clear `_ambient_proposals`.

**Falloff Formula**:
```python
falloff = max(AMBIENT_MIN_FALLOFF, 1.0 - (min_dist / AMBIENT_MAX_DISTANCE))
volume = Settings.SFX_VOLUME * AMBIENT_VOLUME_SCALE * falloff
```

| Distance (px) | Falloff | Volume (SFX=1.0) |
|----------------|---------|-------------------|
| 0 | 1.00 | 0.80 |
| 75 | 0.75 | 0.60 |
| 150 | 0.50 | 0.40 |
| 225 | 0.25 | 0.20 |
| 300+ | 0.05 | 0.04 |

---

## 6. Footstep Surface & Drawbridge Resolution

The player's footstep material is resolved dynamically frame-by-frame:

```
[Player.update] → [resolve_footstep_material()]
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

### 6.1 Resolution Priority
1. **Interactive Entities Override**: If the player is overlapping an active collision/interaction boundary of an entity that defines a material, this material takes absolute priority.
   - For a `Drawbridge` entity, the footprint material is dynamically overridden to `wood` if the drawbridge's state is `EXTENDED`. If the state is `RETRACTED` (and walkability constraints permit traversal), it falls back to the map tile's material.
2. **Background Tile**: Query the top layer of the map at the player's central tile coordinate. Read the custom property `material` (string).
   - If a custom property is defined, it is loaded.
   - If absent, it returns `None` and the player falls back to the generic `04-footstep` sound effect.

> [!NOTE]
> The "stone for indoors, grass for outdoors" default described previously was aspirational.
> The current implementation returns `None` when no tile has a `material` property set,
> and the player falls back to the generic `04-footstep` sound effect. There is no indoor/outdoor
> map classification mechanism in the engine. If one is needed, add a `map_type` custom
> property (`"indoor"` | `"outdoor"`) to the Tiled map object.

### 6.3 Spatial Volume for Positional SFX
For non-ambient SFX triggered at a world position (e.g., NPC footsteps, environmental triggers), volume is computed with a linear distance falloff:
```python
volume = max(0.0, 1.0 - distance / MAX_AUDIO_DISTANCE)
```
Linear falloff to zero at `MAX_AUDIO_DISTANCE` (= `AMBIENT_MAX_DISTANCE`, 300px). Beyond this radius, the sound is not played.

### 6.2 Drawbridge Mechanical Sound States
An interactive bridge has 4 states (defined in `src/entities/interactive.py`):
1. `RETRACTED` (default: closed/blocked)
2. `EXTENDING` (transitional: plays drawbridge extending mechanical gear SFX)
3. `EXTENDED` (opened/traversable: allows passage and overrides footsteps to `wood`)
4. `RETRACTING` (transitional: plays drawbridge retracting mechanical gear SFX)

---

## 7. Anti-Patterns (DO NOT)

| ❌ Don't | ✅ Do Instead | Why |
|----------|---------------|-----|
| Play ambient directly in entity.update() | Use `propose_ambient()` | Only closest source should control volume |
| Create new Sound objects per frame | Preload in `preload_sfx()` or cache in `ambient_sounds` | Avoids I/O in game loop |
| Use `sound.play()` without `sound.stop()` first | Stop then play for SFX | Prevents flanging from rapid triggers |
| Call `flush_ambient()` per entity | Call once per frame in `Game._update()` | Ensures all proposals are collected first |
| Set ambient volume without falloff | Use the `falloff` formula | Abrupt volume changes are jarring |
| Play a loop of footstep sounds continuously | Trigger footstep sounds at specific frame markers within the entity's walk cycle | Matches player's visual movements and avoids audio spam |
| Hardcode the mapping between materials and filenames in the engine | Dynamically construct the file path using the material property: `assets/audio/sfx/footstep_{material}.ogg` | Simplifies adding new terrain types (e.g. `sand`, `water`) |
| Allow player traversal when bridge state is `EXTENDING` or `RETRACTING` | Set `walkable = False` on the entity during transitional states | Prevents the player from walking on empty space or getting stuck in walls |
| Let the drawbridge gear mechanical sound play infinitely | Stop the transitional gear SFX loop as soon as the bridge reaches the final target state (`EXTENDED` or `RETRACTED`) | Prevents ear fatigue and auditory clutter |

---

## 8. Error Handling Matrix

| Error Type | Detection | Response | Fallback | Logging |
|------------|-----------|----------|----------|---------|
| Mixer init failure | `pygame.error` in `__init__` | Log warning | `is_enabled = False`, all methods no-op | WARN |
| Missing BGM file | `os.path.exists()` check | Log error | No playback, no crash | ERROR |
| Missing SFX file | `os.path.exists()` in `play_sfx` | Log warning | Return `False` | WARN |
| Missing ambient file | `os.path.exists()` in `flush_ambient` | Log warning | Skip sound, continue | WARN |
| No free channel | `sound.play()` returns `None` | Log warning | Sound not started | WARN |
| Missing footstep SFX file | `FileNotFoundError` during sound load | Play fallback footstep sound | Falls back to the generic `04-footstep` sound effect. | ERROR |
| Invalid material property | String parsed does not match known materials | Interpret as default material | Falls back to the generic `04-footstep` sound effect. | WARN |

---

## 9. Test Case Specifications

### 9.1 Unit Tests
| Test ID | Component | Input | Expected Output |
|---------|-----------|-------|-----------------|
| UT-AUD-01 | `play_bgm` | Same name twice | Second call is no-op |
| UT-AUD-02 | `play_bgm` | Different name | Previous BGM replaced |
| UT-AUD-03 | `play_sfx` | Unknown name, file exists | Lazy load succeeds, returns True |
| UT-AUD-04 | `play_sfx` | Unknown name, no file | Returns False |
| UT-AUD-05 | `propose_ambient` | Same name, dist 50 then 120 | `_ambient_proposals[name] = 50` |
| UT-AUD-06 | `flush_ambient` | 1 proposal at dist=150 | Volume = `SFX_VOL * 0.8 * 0.5` |
| UT-AUD-07 | `flush_ambient` | 0 proposals, 1 active | Active ambient stopped |
| UT-AUD-08 | `toggle_mute` | Unmuted state | All volumes set to 0 |
| UT-AUD-09 | `toggle_mute` | Muted state | Volumes restored from Settings |
| BRIDGE-U-001 | Bridge SFX | `sfx_open="bridge_open"` | `entity.sfx_open == "bridge_open"` |
| BRIDGE-U-002 | Bridge SFX | `sfx_close="bridge_close"` | `entity.sfx_close == "bridge_close"` |
| BRIDGE-U-003 | Bridge SFX | `material="wood"` | `entity.material == "wood"` |
| BRIDGE-U-004 | Bridge SFX | No `sfx_open` provided | `entity.sfx_open == ""` |
| BRIDGE-U-005 | Bridge SFX | No `sfx_close` provided | `entity.sfx_close == ""` |
| BRIDGE-U-006 | Bridge SFX | No `material` provided | `entity.material == ""` |
| BRIDGE-U-007 | Interaction | `is_on=True`, `sfx_open` set | `_resolve_sfx` returns `sfx_open` |
| BRIDGE-U-008 | Interaction | `is_on=False`, `sfx_close` set | `_resolve_sfx` returns `sfx_close` |
| BRIDGE-U-009 | Interaction | `is_on=True`, `sfx_open=""` | `_resolve_sfx` falls back to `sfx` |
| BRIDGE-U-010 | Interaction | `is_on=False`, `sfx_close=""` | `_resolve_sfx` falls back to `sfx` |
| BRIDGE-U-011 | Interaction | `sfx`, `sfx_open`, `sfx_close` empty | `_resolve_sfx` returns `""` |
| BRIDGE-U-012 | Interaction | Legacy entity (no `sfx_open`/`sfx_close` attrs) | `_resolve_sfx` returns `sfx` |
| BRIDGE-U-013 | Player SFX | Override entity with `material="wood"` at player pos | `_resolve_footstep_material` returns `wood` |
| BRIDGE-U-014 | Player SFX | Override entity with `material=""` at player pos | `_resolve_footstep_material` falls back to map terrain |
| BRIDGE-U-015 | Player SFX | No override entities on map | `_resolve_footstep_material` uses map terrain |
| BRIDGE-U-016 | Player SFX | Player not on override entity | `_resolve_footstep_material` uses map terrain |

### 9.2 Integration Tests
| Test ID | Flow | Setup / Verification |
|---------|------|----------------------|
| IT-AUD-01 | Map transition with same BGM | Music continues without restart |
| IT-AUD-02 | Map transition with different BGM | Old BGM fades out, new fades in |
| IT-AUD-03 | Entity propose → flush cycle | Ambient plays with correct volume |
| BRIDGE-I-001 | Lever triggers bridge ON | Lever target is bridge; pull lever -> Bridge toggled ON, plays `sfx_open` |
| BRIDGE-I-002 | Lever triggers bridge OFF | Lever target is bridge; pull lever again -> Bridge toggled OFF, plays `sfx_close` |
| BRIDGE-I-003 | Footsteps on lowered bridge | Bridge lowered (`is_on=True`, `material="wood"`); player walks -> Plays `04-footstep_wood` SFX |

---

## 10. Deep Links
- **`AudioManager`**: [audio.py:17](../../src/engine/audio.py#L17)
- **Propose/flush**: [audio.py:171-235](../../src/engine/audio.py#L171)
- **`Drawbridge` entity class**: [interactive.py L121](../../src/entities/interactive.py#L121)
- **Footstep material resolver**: [player.py L156](../../src/entities/player.py#L156)

---

## 11. Linked Test Functions

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
