# Technical Specification — Dynamic Lighting & Effects Systems [Implementation]

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

---

## 7. Deep Links
- **Dynamic Lighting Manager**: [lighting.py L7](../../src/engine/lighting.py#L7)
- **Interactive Light Mixin**: [interactive_lighting.py L29](../../src/entities/interactive_lighting.py#L29)
- **Particle Mixin**: [interactive_particles.py L1](../../src/entities/interactive_particles.py#L1)
- **Flicker parameters & constants**: [interactive_constants.py L1](../../src/entities/interactive_constants.py#L1)
