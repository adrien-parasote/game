# Technical Specification — Dynamic Lighting & Effects Systems [Implementation]

> Document Type: Implementation

> **Document Type:** Implementation
> **Source Files:** `src/engine/lighting.py`, `src/entities/interactive_lighting.py`, `src/entities/interactive_particles.py`, `src/entities/interactive_constants.py`

This specification consolidates the Dynamic Lighting system, including Pygame subtractive night overlays, window beams with astronomical slants, torch halos with candle-like flickers, and visual particle generators.

---

## 1. Darkness Overlay & Subtracting Blends

The engine uses a Pygame-native subtractive overlay for dynamic darkness without shader pipelines:

```
        ┌────────────────────────────────────────────────────────┐
        │                 Original Rendered Scene                │
        └───────────────────────────┬────────────────────────────┘
                                    │
                                    ▼ (Overlay blit)
        ┌────────────────────────────────────────────────────────┐
        │  _night_overlay (Black surface, filled with opacity)   │
        │                                                        │
        │   Subtract Light Masks (via BLEND_RGBA_SUB):           │
        │    - Radial Torches                                    │
        │    - Trapezoid Window Beams                            │
        │    - Magical Entities                                  │
        └───────────────────────────┬────────────────────────────┘
                                    │
                                    ▼
        ┌────────────────────────────────────────────────────────┐
        │                 Final Visual Output                    │
        └────────────────────────────────────────────────────────┘
```

- **`_night_overlay`**: A transparent black surface covering the viewport, initialized with a variable darkness value (`night_alpha` from `0` to `180`).
- **`BLEND_RGBA_SUB`**: Lighting shapes are composed of white and alpha gradients. Subtracting these shapes from the overlay's alpha channel erases the darkness, cleanly revealing the original scene pixels beneath.

---

## 2. Window Lighting & Mathematical Beams

Window light cones originate from window frames and diffuse downwards onto the ground.

### 2.1 Detection & Caching
- **Detection**: Window origins are read from Tiled rectangle objects (`type="18-light"`) on the `00-system` layer, defining exact width and horizontal centers. If missing, tiles tagged with `type="window"` are used as a fallback.
- **Cache**: Coordinates are cached at map load via `MapManager.get_window_positions()` returning a list of `(cx, y, width)` tuples.

### 2.2 Mathematical Beam Modeling
Each window beam is a trapezoid surface computed pixel-by-pixel:
- **Geometry**: Slants outward from `beam_top_width` (24px) to `beam_bottom_width` (52px) over `beam_height` (70px).
- **Horizontal Diffusion**: Uses a Gaussian falloff `exp(-1.65 * dist²)` to blend edges smoothly.
- **Vertical Decay**: Computed as `(1 - t)^0.6` to simulate progressive light scattering.
- **Oval Floor Bottom**: Corner pixels fade inside the bottom 35% height:
  ```python
  corner_fade = max(0, 1 - bp * d_corner * 1.8)
  ```
  This creates a natural, rounded pool of illumination on the floor.
- **Performance**: Pure Python `pygame.Surface.set_at()` with a cache of up to 64 pre-rendered beams.
- **Cache Key Quantization**: Cache key is quantized to `(round(slant_offset, 1), width)` — 0.1 resolution prevents frame-by-frame cache misses from continuous hour changes.

### 2.3 Solar/Lunar Slant Rotation
Beam slant shifts continuously as a function of the time of day:
- **Astronomy Cosines**:
  ```python
  sun_angle = 2 * pi * (hour - 6) / 24
  moon_angle = 2 * pi * (hour - 18) / 24
  ```
- **Interpolation**: Sun slant and moon slant blend smoothly according to active sky brightness, preventing discontinuous jumps at dawn or dusk.

---

## 3. Torch Halos & Flickering Mechanics

Torch and lamp entities (e.g., `lamp`, `lantern`, `torch`, `fire`, `candle`) utilize a dynamic lighting mixin.

### 3.1 Pre-generated Light Masks
- **Setup**: In `__init__()`, entities with `halo_size > 0` compile a base mask (`_create_halo_surf`) with a quadratic gradient falloff `(1 - r/R)²`.
- **Scaling Cache**: Generates 10 pre-scaled variants ranging from `0.97` to `1.03` size:
  ```python
  scale[i] = 0.97 + i * 0.0066
  ```
  Pre-generating scales eliminates runtime frame drops.

### 3.2 Desynchronized Flicker Waves
Modulates halo alpha and scale to simulate organic candle flicker:
- **Static Mode (Wall Clock)**: Uses standard sinusoids with a unique, randomized `flicker_phase` offset for each entity:
  ```python
  f_alpha = 1.0 + 0.12 * sin(t * 1.5 * pi + phase) + 0.02 * sin(t * 4.2 * pi + phase * 0.5) + noise(0.01)
  f_scale = 1.0 + 0.03 * sin(t * 1.2 * pi + phase + 0.5)
  ```
- **Animated Mode (Sprite Sync)**: Syncs frequency to the active sprite's animation frame sequence:
  ```python
  phase = (frame_index / total_frames) * 2 * pi
  f_alpha = 1.0 + 0.12 * sin(phase - pi / 2) + noise(0.02)
  ```

---

## 4. Sparks & Embers Particle Engine

Interactive entities with `particles: true` emit visual details (e.g. fire sparks, lantern glow).
- **Update loop**: Tracks particles using basic physics (upward vertical velocity offset, horizontal wind sway, and gravity).
- **Alpha decay**: Subtracts life over time, fading the opacity linearly until culling occurs (`lifetime <= 0`).

---

## 5. Anti-Patterns (DO NOT)

| ❌ Don't | ✅ Do Instead | Why |
|----------|---------------|-----|
| Call circle draw or shape APIs per frame | Pre-calculate surfaces and store them in a cache | Per-frame canvas vector math causes major lag |
| Blend shadows on standard surfaces | Write subtractive alphas to the night overlay | Multiplicative blending leads to washed-out or flat scenes |
| Share a single `flicker_phase` | Randomize the offset at entity startup | Uniform flicker looks artificial |
| Re-render scaled images each tick | Select the nearest bucket from `light_mask_cache` | Copying and scaling surfaces during game loops creates memory churn |
| Re-scan map grid for windows during draw | Query map caches created at load time | `O(W*H)` grid queries drop frame rates |

---

## 6. Test Case Specifications

### 6.1 Unit Tests
- **UT-LT-01**: `get_window_positions` correctly parses Tiled rectangle coordinates.
- **UT-LT-02**: Window slant shifts continuously through the day without spikes.
- **UT-LT-03**: Interactive light setup constructs exactly 10 scaling cache surfaces.
- **UT-LT-04**: Torch flicker desynchronizes multiple active lamp sprites.

### 6.2 Integration Tests
- **IT-LT-01**: Dynamic overlay fades opacity matching noon to midnight transition times.
- **IT-LT-02**: Particle spawns are culled and collected when lifetime hits 0.

### Linked Test Functions

| Test ID | Test Function | File |
|---------|---------------|------|
| LT-001 | `test_map_manager_window_cache_lt001` | `../../tests/engine/test_lighting.py` |
| LT-002 | `test_lighting_beam_color_sync_lt003` | `../../tests/engine/test_lighting.py` |
| LT-004 | `test_lighting_night_overlay_lt004` | `../../tests/engine/test_lighting.py` |
| LT-012 | `test_beam_cache_reuses_surface` | `../../tests/engine/test_lighting.py` |

---

## 7. Deep Links
- **Dynamic Lighting Manager**: [lighting.py L7](../../src/engine/lighting.py#L7)
- **Interactive Light Mixin**: [interactive_lighting.py L29](../../src/entities/interactive_lighting.py#L29)
- **Particle Mixin**: [interactive_particles.py L1](../../src/entities/interactive_particles.py#L1)
- **Flicker parameters & constants**: [interactive_constants.py L1](../../src/entities/interactive_constants.py#L1)

---

## 8. Map Lighting Modes — Per-Map Ambient Darkness

**Covers:** F-LIGHTMODE-01, F-LIGHTMODE-02, F-LIGHTMODE-03  
**Blueprint:** [`docs/strategic/blueprint-map-lighting-modes.md`](../strategic/blueprint-map-lighting-modes.md)

### 8.1 Overview

Three lighting modes control how the darkness overlay alpha is computed each frame.
The mode is declared at **map root level** in `.tmj` via a Tiled custom property.
`TimeSystem` is **never modified** — the clock always advances.

### 8.2 Tiled Map Properties — Contract

Extracted by `TmjParser` into `map_result["properties"]` (existing pipeline).
Read by `MapLoader.load()` and stored on `game`.

| Property | Tiled type | Default | Constraint |
|----------|-----------|---------|-----------|
| `lighting_mode` | enum (string) | `"outdoor"` | Must be `"outdoor"` · `"indoor"` · `"underground"` |
| `ambient_dark_alpha` | int | `0` | Clamped to [0, 255]. Used as plancher for `indoor`, fixed value for `underground` |

Maps without `lighting_mode` → implicit `"outdoor"` (zero regression).

### 8.3 Effective Alpha Formula per Mode

```python
# outdoor (unchanged — zero regression)
effective_alpha = time_system.night_alpha          # 0 → 180

# indoor (Option B — locked)
effective_alpha = min(255,
    ambient_dark_alpha + int(time_system.night_alpha * INDOOR_ATTENUATION)
)

# underground — fixed, no time dependency
effective_alpha = ambient_dark_alpha               # 0 → 255, set by designer
```

Constants in `lighting_constants.py`:
```python
INDOOR_ATTENUATION: float = 0.35   # Night filtered through walls
```

### 8.4 Window Beams — Mode Rules

| Mode | `draw_additive_window_beams` | Rationale |
|------|------------------------------|-----------|
| `outdoor` | ✅ called | Sun/moon beam through windows |
| `indoor` | ✅ called | Windows exist, exterior light filters in |
| `underground` | ❌ skipped | No sky source — torches are the only light |

### 8.5 Affected Files & Change Summary

| File | Change | Scope |
|------|--------|-------|
| `src/engine/lighting_constants.py` | Add `INDOOR_ATTENUATION = 0.35` | +1 constant |
| `src/engine/map_loader.py` | `_apply_map_lighting(props)` called in `load()` — reads `lighting_mode` + `ambient_dark_alpha`, validates, clamps, stores on `game` | ~25 lines |
| `src/engine/render_manager.py` | `_compute_effective_night_alpha()` (3-mode formula) + underground beam guard in `_render_lighting_and_effects()` | ~20 lines |
| `assets/tiled/maps/**/*.tmj` | Designer sets properties in Tiled (no code change) | Data only |

**No changes to:** `TimeSystem`, `LightingManager`, `TmjParser`, `MapManager`.

### 8.6 game attributes set by MapLoader

```python
game._map_lighting_mode: str       # "outdoor" | "indoor" | "underground"
game._map_ambient_dark_alpha: int  # 0–255
```

Both attributes initialised to defaults in `MapLoader.load()` even if the property
is absent from the map — guarantees `RenderManager` never encounters `AttributeError`.

### 8.7 Constraints

| Tier | Rule |
|------|------|
| **Always do** | Clamp `ambient_dark_alpha` to [0, 255] on read; default `lighting_mode` to `"outdoor"` if absent |
| **Ask first** | Changing `INDOOR_ATTENUATION` constant value (affects all indoor maps globally) |
| **Always do** | Pass `alpha_override=effective_alpha` to `create_overlay()` — never let it read `time_system.night_alpha` directly |
| **Never do** | Modify `TimeSystem` for lighting — it is a pure clock |

### 8.8 Anti-Patterns

| ❌ Don't | ✅ Do Instead | Why |
|----------|---------------|-----|
| Read `lighting_mode` in `LightingManager` | Read in `RenderManager`; pass `effective_alpha` | `LightingManager` must not know map topology (ADR-LIGHT-001) |
| Freeze `TimeSystem` for underground maps | Keep clock running; override alpha in renderer | Time must advance for saves, HUD, season logic |
| Use `if "underground" in map_name` | Use `game._map_lighting_mode` property | Naming convention coupling is fragile and undocumented |
| Call `draw_additive_window_beams` underground | Guard with `if game._map_lighting_mode != "underground"` | No sky source — beams would look absurd |
| Set `ambient_dark_alpha` to non-zero for outdoor maps | Leave it at `0` for `outdoor` (ignored) | The field is only meaningful for `indoor` / `underground` |

### 8.9 Error Handling Matrix

| Condition | Source | Response | Fallback | Logging |
|-----------|--------|----------|----------|---------|
| `lighting_mode` value unknown (e.g. `"cave"`) | Map load | Use `"outdoor"` | ✅ | `logging.warning("Unknown lighting_mode '%s', defaulting to outdoor")` |
| `ambient_dark_alpha` out of [0, 255] | Map load | `max(0, min(255, int(raw_alpha or 0)))` clamp | ✅ | No log (Tiled already constrains int range) |
| `ambient_dark_alpha` is `None` (Tiled null) | Map load | `int(raw_alpha or 0)` guard → clamp to 0 | ✅ | No log |
| `game._map_lighting_mode` missing at render time | Render frame | `getattr(game, "_map_lighting_mode", "outdoor")` | ✅ | None (defensive read) |

All error states: VERIFIED (CITED — defensive patterns enforced by `getattr` + explicit clamp + `or 0` guard).

### 8.10 Test Case Specifications

#### Unit Tests

| TC ID | Function | File | Assertion |
|-------|----------|------|-----------|
| TC-LM-U-01 | `test_outdoor_mode_uses_time_system_alpha` | `../../tests/engine/test_lighting_modes.py` | `effective_alpha == time_system.night_alpha` at any hour |
| TC-LM-U-02 | `test_underground_mode_fixed_alpha` | `../../tests/engine/test_lighting_modes.py` | `effective_alpha == ambient_dark_alpha` regardless of hour (midnight = noon) |
| TC-LM-U-03 | `test_indoor_mode_option_b_formula` | `../../tests/engine/test_lighting_modes.py` | `effective_alpha == min(255, ambient + int(night_alpha * 0.35))` |
| TC-LM-U-04 | `test_indoor_alpha_clamped_at_255` | `../../tests/engine/test_lighting_modes.py` | `ambient=240, night_alpha=180` → result ≤ 255 |
| TC-LM-U-05 | `test_unknown_lighting_mode_defaults_outdoor` | `../../tests/engine/test_lighting_modes.py` | Mode `"cave"` → falls back to `outdoor` formula |
| TC-LM-U-06 | `test_map_loader_stores_lighting_mode_on_game` | `../../tests/engine/test_lighting_modes.py` | After `MapLoader.load()`, `game._map_lighting_mode` and `game._map_ambient_dark_alpha` set |
| TC-LM-U-07 | `test_map_loader_defaults_when_property_absent` | `../../tests/engine/test_lighting_modes.py` | Map with no `lighting_mode` → `game._map_lighting_mode == "outdoor"`, `ambient == 0` |

#### Integration Tests

| TC ID | Function | File | Assertion |
|-------|----------|------|-----------|
| TC-LM-I-01 | `test_underground_alpha_constant_over_full_day` | `../../tests/engine/test_lighting_modes.py` | Step through 24h via `time_system.update()`; `effective_alpha` never changes |
| TC-LM-I-02 | `test_window_beams_skipped_underground` | `../../tests/engine/test_lighting_modes.py` | `draw_additive_window_beams` NOT called when mode = `underground` |
| TC-LM-I-03 | `test_window_beams_called_indoor` | `../../tests/engine/test_lighting_modes.py` | `draw_additive_window_beams` IS called when mode = `indoor` |
| TC-LM-I-04 | `test_create_overlay_called_with_effective_alpha` | `../../tests/engine/test_lighting_modes.py` | **Regression** — `create_overlay` called with `alpha_override=ambient` (not time_system) when underground at midday |

#### Linked Test Functions

| TC ID | Test Function | File |
|-------|---------------|------|
| TC-LM-U-01 | `test_outdoor_mode_uses_time_system_alpha` | `../../tests/engine/test_lighting_modes.py` |
| TC-LM-U-02 | `test_underground_mode_fixed_alpha` | `../../tests/engine/test_lighting_modes.py` |
| TC-LM-U-03 | `test_indoor_mode_option_b_formula` | `../../tests/engine/test_lighting_modes.py` |
| TC-LM-U-04 | `test_indoor_alpha_clamped_at_255` | `../../tests/engine/test_lighting_modes.py` |
| TC-LM-U-05 | `test_unknown_lighting_mode_defaults_outdoor` | `../../tests/engine/test_lighting_modes.py` |
| TC-LM-U-06 | `test_map_loader_stores_lighting_mode_on_game` | `../../tests/engine/test_lighting_modes.py` |
| TC-LM-U-07 | `test_map_loader_defaults_when_property_absent` | `../../tests/engine/test_lighting_modes.py` |
| TC-LM-I-01 | `test_underground_alpha_constant_over_full_day` | `../../tests/engine/test_lighting_modes.py` |
| TC-LM-I-02 | `test_window_beams_skipped_underground` | `../../tests/engine/test_lighting_modes.py` |
| TC-LM-I-03 | `test_window_beams_called_indoor` | `../../tests/engine/test_lighting_modes.py` |
| TC-LM-I-04 | `test_create_overlay_called_with_effective_alpha` | `../../tests/engine/test_lighting_modes.py` |

### 8.11 Cross-Spec Contracts

#### Produces
N/A — this spec produces no file artifacts consumed by other specs.

#### Consumes

| Identifier | Format | Schema location | Producer |
|-----------|--------|----------------|---------|
| `map_result["properties"]["lighting_mode"]` | str | This spec § 8.2 | `map-world-system.md § MapLoader` |
| `map_result["properties"]["ambient_dark_alpha"]` | int | This spec § 8.2 | `map-world-system.md § MapLoader` |
| `time_system.night_alpha` | int 0–180 | `engine-core.md § TimeSystem` | `engine-core.md` |

#### Public Interface

| Type | Identifier | Documented at |
|------|-----------|--------------|
| game attr | `game._map_lighting_mode: str` | This spec § 8.6 |
| game attr | `game._map_ambient_dark_alpha: int` | This spec § 8.6 |
| constant | `INDOOR_ATTENUATION` in `lighting_constants.py` | This spec § 8.3 |

#### External Invocations

| Type | Invoked | Defined in |
|------|---------|-----------|
| method | `LightingManager.draw_additive_window_beams()` | This spec § 8.4 (guarded by mode) |
| method | `LightingManager.create_overlay()` | `lighting-system.md § 1` |

#### Tracked Concepts

| Concept | Status in this spec | Mentioned in |
|---------|--------------------|---------| 
| `lighting_mode` Tiled property | Defined here | `map-world-system.md` |
| `ambient_dark_alpha` Tiled property | Defined here | `map-world-system.md` |

### 8.12 Deep Links

- **`render_manager.py` draw_scene()**: [render_manager.py L468](../../src/engine/render_manager.py#L468)
- **`render_manager.py` _compute_effective_night_alpha()**: [render_manager.py L351](../../src/engine/render_manager.py#L351)
- **`render_manager.py` _render_lighting_and_effects()**: [render_manager.py L371](../../src/engine/render_manager.py#L371)
- **`map_loader.py` _apply_map_lighting()**: [map_loader.py L199](../../src/engine/map_loader.py#L199)
- **`lighting_constants.py`**: [lighting_constants.py L1](../../src/engine/lighting_constants.py#L1)
- **Blueprint**: [`docs/strategic/blueprint-map-lighting-modes.md`](../strategic/blueprint-map-lighting-modes.md)

### 8.13 Assumptions

| Assumption | Status | Risk | Evidence |
|-----------|--------|------|----------|
| `lighting_mode` Tiled enum serialises as plain string in `.tmj` JSON | VERIFIED | Low | Standard Tiled behaviour — enum properties → `"type":"string"` in JSON export |
| `map_result["properties"]` is always a dict, never None | VERIFIED | Low | `tmj_parser.py:59` — `{p["name"]: p["value"] for p in data.get("properties", [])}` |
| `game._map_lighting_mode` does not yet exist on `game` | ASSUMED | Low | Not found in grep of `game.py`; created by `MapLoader.load()` |
| `INDOOR_ATTENUATION = 0.35` is visually correct | ASSUMED | Low | Tunable constant — designer adjusts post-playtest |

### 8.14 Bundling & Native-Module Audit
- BM1: N/A — Python/Pygame project, no bundler
- BM2: N/A — no client/server split
- BM3: N/A — no native modules
- BM4: N/A — no field renames in this spec

## Assumptions

## Light Limits
Maximum 16 dynamic lights per active chunk.

