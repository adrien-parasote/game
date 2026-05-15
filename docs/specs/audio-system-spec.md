[assumption: "All implicit constants and defaults are documented here – pending detailed entries"] – risk: Low

# Technical Specification — Audio System [Implementation]

> Document Type: Implementation
> Source: `src/engine/audio.py` (253 LOC)

This document specifies the AS-IS implementation of the `AudioManager` subsystem.

## 1. Goal Description

Manage all game audio: background music (BGM) with cross-map continuum, sound effects (SFX) with preloading, and ambient loops with distance-based volume via a per-frame propose/flush model.

## 2. Component Overview

| Module | File | LOC | Responsibility |
|--------|------|-----|----------------|
| `AudioManager` | `src/engine/audio.py` | 253 | BGM, SFX, ambient loop management |

### Singleton: No
`AudioManager` is instantiated once by `Game.__init__()` and stored as `game.audio`.

### External Dependencies
- `pygame.mixer` — mixer initialization, channels, Sound/Music objects
- `src.config.Settings` — `BGM_VOLUME`, `SFX_VOLUME`

## 3. Constants

| Constant | Value | Definition | Purpose |
|----------|-------|------------|---------|
| `AMBIENT_VOLUME_SCALE` | `0.8` | `audio.py:10` | Max fraction of SFX_VOLUME for ambient sounds |
| `AMBIENT_MAX_DISTANCE` | `300.0` | `audio.py:13` | Distance (px) at which ambient volume reaches minimum |
| `AMBIENT_MIN_FALLOFF` | `0.05` | `audio.py:14` | Floor multiplier — ambient never drops below 5% |
| Mixer channels | `32` | `audio.py:48` | Total pygame mixer channels allocated |

## 4. Interfaces

### 4.1. Initialization

```python
def __init__(self) -> None
```

**Behavior**:
1. Set `bgm_dir = "assets/audio/bgm"`, `sfx_dir = "assets/audio/sfx"`
2. Initialize `pygame.mixer` if not already initialized
3. Set 32 mixer channels via `pygame.mixer.set_num_channels(32)`
4. If mixer init fails → set `is_enabled = False`, return early
5. Call `preload_sfx()` to cache all `.ogg` files from `sfx_dir`

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

### 4.2. BGM

```python
def play_bgm(self, name: str, loop: bool = True, fade_ms: int = 500) -> None
```

**Behavior**:
1. If `name == self.current_bgm` AND music is playing → **no-op** (continuum rule)
2. Load `assets/audio/bgm/{name}.ogg`
3. Set volume to Settings.BGM_VOLUME
4. Play with `loops=-1` (infinite) if `loop=True`, else `loops=0`
5. Apply fade-in of `fade_ms` milliseconds
6. Update `self.current_bgm = name`

**Continuum Rule**: When transitioning between maps that share the same BGM track name, the music is NOT restarted. This is the core BGM design — seamless map transitions.

```python
def stop_bgm(self, fade_ms: int = 500) -> None
```

**Behavior**: Fade out current BGM over `fade_ms` ms, set `current_bgm = None`.

### 4.3. SFX

```python
def preload_sfx(self) -> None
```

**Behavior**: Scan `sfx_dir` for all `.ogg` files, load each as `pygame.mixer.Sound`, cache in `self.sounds` keyed by filename without extension.

```python
def play_sfx(self, name: str, source_id: str | None = None, volume_multiplier: float = 1.0) -> bool
```

**Behavior**:
1. Look up `name` in preloaded `self.sounds`
2. If not found → attempt lazy load from `sfx_dir/{name}.ogg`
3. **Stop** the sound if already playing (prevents flanging from rapid triggers)
4. Set volume to `Settings.SFX_VOLUME * volume_multiplier`
5. Play on first available channel
6. Return `True` on success, `False` on failure

**`source_id`**: Currently unused for channel tracking — reserved for future per-entity channel isolation.

### 4.4. Ambient Audio — Propose/Flush Model

#### Architecture

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

**Behavior**: Record `min(existing_proposal, distance)` for `name` in `_ambient_proposals`. Multiple entities proposing the same sound name → closest wins.

```python
def flush_ambient(self) -> None
```

**Behavior** (called once per frame):
1. For each proposal `(name, min_dist)`:
   - If `name` not in `ambient_sounds` → load `.ogg`, start looping on a new channel
   - Compute volume: `SFX_VOLUME * AMBIENT_VOLUME_SCALE * falloff(min_dist)`
   - Apply volume to the sound object
2. For each `name` in `ambient_sounds` NOT in current proposals → stop its channel, remove from tracking
3. Clear `_ambient_proposals`

**Falloff formula**:
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

```python
def stop_ambient(self, source_id: str) -> None
def stop_all_ambients(self) -> None
```

**Behavior**: Explicit stop for a named ambient or all ambients. Used during map transitions.

### 4.5. Volume Control

```python
def toggle_mute(self) -> None
```

**Behavior**:
- Mute: Set all sounds/music to volume 0
- Unmute: Call `update_volumes()` to restore from Settings

```python
def update_volumes(self) -> None
```

**Behavior**: Re-apply Settings.BGM_VOLUME to music, Settings.SFX_VOLUME to all preloaded sounds. Does NOT update ambient volumes (handled by `flush_ambient`).

## 5. Wiring

| Caller | Method | Context |
|--------|--------|---------|
| `Game.__init__()` | Constructor | Created once per game session |
| `Game._update()` | `flush_ambient()` | End of entity update cycle |
| `MapLoader.load_map()` | `play_bgm(name)` | Map transition triggers BGM |
| `MapLoader.load_map()` | `stop_all_ambients()` | Clean ambient state on map change |
| `InteractiveEntity.update()` | `propose_ambient(name, dist)` | Entities with `sfx_ambient` property |
| `InteractionManager` | `play_sfx(name)` | Interaction feedback (chest open, door) |
| `Player._play_footstep()` | `play_sfx(material)` | Terrain-based footstep sounds |
| `GameStateManager` | `stop_bgm()` | Title/pause transitions |

## 6. Anti-Patterns (DO NOT)

| ❌ Don't | ✅ Do Instead | Why |
|----------|---------------|-----|
| Play ambient directly in entity.update() | Use `propose_ambient()` | Only closest source should control volume |
| Create new Sound objects per frame | Preload in `preload_sfx()` or cache in `ambient_sounds` | Avoids I/O in game loop |
| Use `sound.play()` without `sound.stop()` first | Stop then play for SFX | Prevents flanging from rapid triggers |
| Call `flush_ambient()` per entity | Call once per frame in `Game._update()` | Ensures all proposals are collected first |
| Set ambient volume without falloff | Use the `falloff` formula | Abrupt volume changes are jarring |

## 7. Error Handling Matrix

| Error Type | Detection | Response | Fallback |
|------------|-----------|----------|----------|
| Mixer init failure | `pygame.error` in `__init__` | Log warning | `is_enabled = False`, all methods no-op |
| Missing BGM file | `os.path.exists()` check | Log error | No playback, no crash |
| Missing SFX file | `os.path.exists()` in `play_sfx` | Log warning | Return `False` |
| Missing ambient file | `os.path.exists()` in `flush_ambient` | Log warning | Skip sound, continue |
| No free channel | `sound.play()` returns `None` | Log warning | Sound not started |

## 8. Test Case Specifications

### Unit Tests
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

### Integration Tests
| Test ID | Flow | Verification |
|---------|------|--------------|
| IT-AUD-01 | Map transition with same BGM | Music continues without restart |
| IT-AUD-02 | Map transition with different BGM | Old BGM fades out, new fades in |
| IT-AUD-03 | Entity propose → flush cycle | Ambient plays with correct volume |

## 9. Deep Links
- **AudioManager**: [audio.py:17](../../src/engine/audio.py#L17)
- **Propose/flush**: [audio.py:171-235](../../src/engine/audio.py#L171)
- **Caller (Game)**: [game.py:1](../../src/engine/game.py#L1)
- **Caller (MapLoader)**: [map_loader.py:1](../../src/engine/map_loader.py#L1)

## 10. Assumptions

| # | Assumption | Risk | Validation |
|---|-----------|------|------------|
| 1 | 32 mixer channels is sufficient for all concurrent sounds | Low | Playtest with dense maps |
| 2 | `.ogg` is the only audio format used | Low | Asset pipeline check |
| 3 | `AMBIENT_MAX_DISTANCE=300px` provides natural falloff | Medium | Tune via playtesting |
| 4 | `sound.stop()` before `play()` is acceptable for SFX | Low | No overlapping SFX needed |
