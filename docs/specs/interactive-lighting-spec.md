> **Design tokens** – see [design-tokens.md](./design-tokens.md)
[assumption: "All implicit constants and defaults are documented here – pending detailed entries"] – risk: Low

# Technical Specification — Interactive Entity Lighting & Particles [Implementation]

> Document Type: Implementation
> Sources: `src/entities/interactive_lighting.py` (124 LOC), `src/entities/interactive_particles.py` (75 LOC), `src/entities/interactive_constants.py` (40 LOC)

This document specifies the AS-IS implementation of the lighting halo and particle emission mixins used by `InteractiveEntity` for torches, lamps, and magical objects.

## 1. Goal Description

Provide dynamic light halos with candle-like flicker and optional particle emission for interactive world objects, using pre-generated surface caches to avoid per-frame allocation.

## 2. Component Overview

| Module | File | LOC | Responsibility |
|--------|------|-----|----------------|
| `InteractiveLightingMixin` | `interactive_lighting.py` | 124 | Halo generation, caching, flicker, rendering |
| `InteractiveParticleMixin` | `interactive_particles.py` | 75 | Particle generation and update |
| Constants | `interactive_constants.py` | 40 | Flicker parameters, cache sizes, animation speeds |

### Mixin Wiring

`InteractiveEntity` inherits from both mixins:
```python
class InteractiveEntity(InteractiveLightingMixin, InteractiveParticleMixin, BaseEntity):
```

Both mixins access `self.*` attributes set by `InteractiveEntity.__init__()`:
- `self.halo_size`, `self.halo_color`, `self.halo_alpha` — from Tiled properties
- `self.is_on`, `self.is_light_source`, `self.is_animated` — state flags
- `self.flicker_phase` — per-instance random phase offset for wave desynchronization

## 3. Constants

### Light Mask Cache
| Constant | Value | Purpose |
|----------|-------|---------|
| `LIGHT_MASK_CACHE_COUNT` | `10` | Number of pre-scaled halo surfaces |
| `LIGHT_MASK_SCALE_BASE` | `0.97` | Base scale for smallest bucket |
| `LIGHT_MASK_SCALE_STEP` | `0.0066` | Increment per bucket (range: 0.97–1.03) |

### Flicker — Alpha (Brightness)
| Constant | Value | Purpose |
|----------|-------|---------|
| `FLICKER_ALPHA_AMPLITUDE` | `0.12` | Main brightness swing (±12%) |
| `FLICKER_ALPHA_JITTER_SCALE` | `0.3` | Secondary jitter wave scale |
| `FLICKER_ALPHA_JITTER_AMP` | `0.02` | Random noise for animated entities |
| `FLICKER_ALPHA_NOISE_AMP` | `0.01` | Random noise for static entities |
| `FLICKER_MAIN_FREQ` | `1.5` | Primary flicker freq (×π rad/s) |
| `FLICKER_JITTER_FREQ` | `4.2` | Secondary jitter freq (×π rad/s) |

### Flicker — Scale (Size)
| Constant | Value | Purpose |
|----------|-------|---------|
| `FLICKER_SCALE_AMPLITUDE` | `0.03` | Halo size oscillation (±3%) |
| `FLICKER_SCALE_FREQ` | `1.2` | Scale wave freq (×π rad/s) |
| `FLICKER_SCALE_PHASE_OFFSET` | `0.5` | Phase difference from alpha wave |

### Defaults
| Constant | Value | Purpose |
|----------|-------|---------|
| `HALO_DEFAULT_COLOR` | `(255, 255, 255)` | White fallback when parsing fails |
| `HALO_DEFAULT_ALPHA` | `130` | Default opacity (0–255) |

## 4. InteractiveLightingMixin

### 4.1. `_setup_lighting() -> None`

Called during `InteractiveEntity.__init__()` for entities with `halo_size > 0`.

**Algorithm**:
1. Create base halo surface: `_create_halo_surf(halo_size)`
2. Pre-generate 10 scaled variants:
   - `scale[i] = 0.97 + i * 0.0066` → range `[0.97, 1.03]`
   - `scaled_size = round(halo_size * scale)`
   - Store in `self.light_mask_cache`

### 4.2. `_create_halo_surf(radius: int) -> Surface`

**Generates**: Black `(2r × 2r)` surface with additive radial gradient.

**Algorithm**:
```python
for r in range(radius, 0, -1):
    ratio = r / radius
    intensity = (1.0 - ratio) ** 2     # quadratic falloff
    final = intensity * (halo_alpha / 255.0)
    color = (R * final, G * final, B * final)
    draw_circle(surf, color, center, r)
```

**Gradient**: Quadratic falloff `(1 - r/R)²` — soft center, sharp edge. Modulated by `halo_alpha`.

### 4.3. `_update_flicker(dt: float, ticks_ms: int | None) -> None`

Called every frame. Computes `self.f_alpha` and `self.f_scale` for current frame.

**Two modes**:

| Mode | Condition | Alpha Source | Scale Source |
|------|-----------|-------------|-------------|
| **Animated** | `is_light_source AND is_animated` | Sprite animation phase | Animation phase |
| **Static** | `is_light_source AND NOT animated` | Wall clock (pygame.ticks) | Wall clock |
| **Off** | `NOT is_on OR halo_size == 0` | `1.0` | `1.0` |

**Animated mode**: Flicker is synchronized to the sprite animation cycle:
```python
animation_phase = (frame_progress / num_frames) * 2π
f_alpha = 1.0 + 0.12 * sin(phase - π/2) + random(±0.02)
f_scale = 1.0 + 0.03 * sin(phase)
```

**Static mode**: Uses wall clock with per-instance `flicker_phase`:
```python
main_wave = sin(t * 1.5π + flicker_phase)
jitter = 0.3 * sin(t * 4.2π + flicker_phase * 0.5)
f_alpha = 1.0 + 0.12 * main_wave + 0.02 * jitter + random(±0.01)
f_scale = 1.0 + 0.03 * sin(t * 1.2π + flicker_phase + 0.5)
```

### 4.4. `_draw_halo(surface, cam_offset, global_darkness) -> None`

**Rendering**:
1. `dark_factor = global_darkness / 180.0` (darkness from lighting system)
2. `global_factor = max(0.15, dark_factor)` — halos always 15%+ visible
3. Select pre-cached surface by scale index: `idx = clamp(round((f_scale - 0.97) / 0.0066))`
4. Set alpha: `min(255, round(255 * global_factor * f_alpha))`
5. Blit with `BLEND_RGB_ADD` centered on entity

**Performance**: No `Surface.copy()` — uses `set_alpha()` on the entity's own cached surfaces (each entity creates its own `light_mask_cache` in `__init__`). Safe because rendering is single-threaded and each entity owns its surfaces.

## 5. InteractiveParticleMixin

### 5.1. Behavior

Generates small particle sprites (sparks/embers) from the entity's position, updated per frame with simple velocity + gravity simulation.

**Consumed by**: Entities with `particles: true` Tiled property (e.g., torches).

### 5.2. Particle Lifecycle

1. **Spawn**: Random velocity, position near entity center
2. **Update**: Apply velocity + gravity, decrement lifetime
3. **Cull**: Remove when `lifetime <= 0`
4. **Draw**: Small colored rectangle or circle at particle position

## 6. Anti-Patterns (DO NOT)

| ❌ Don't | ✅ Do Instead | Why |
|----------|---------------|-----|
| Call `_create_halo_surf()` per frame | Use `light_mask_cache[idx]` | O(n²) circle drawing per frame |
| Use `Surface.copy()` for alpha changes | Use `set_alpha()` on shared surface | Avoids allocation per frame (P9 optimization) |
| Use uniform random for flicker | Use sinusoidal waves + small noise | Candle-like organic feel |
| Same `flicker_phase` for all entities | Randomize in `__init__()` | Prevents synchronized flickering |
| Blit halos without `BLEND_RGB_ADD` | Always use `special_flags=BLEND_RGB_ADD` | Additive blending prevents dark spots |

## 7. Error Handling Matrix

| Error Type | Detection | Response | Fallback |
|------------|-----------|----------|----------|
| `halo_size <= 0` | Check in `_setup_lighting` | Skip cache generation | No halo rendered |
| `scaled_size <= 0` | Check in `_setup_lighting` loop | Use base `light_mask` | Fallback surface |
| Missing `halo_color` attribute | `getattr` with default | Use `HALO_DEFAULT_COLOR` | White halo |
| Missing `halo_alpha` attribute | `getattr` with default | Use `HALO_DEFAULT_ALPHA` | 130/255 opacity |
| Empty `light_mask_cache` | Guard in `_draw_halo` | Early return | No halo drawn |
| `f_scale` out of bucket range | `max(0, min(9, ...))` clamping | Nearest bucket | No crash |

## 8. Test Case Specifications

### Unit Tests
| Test ID | Component | Input | Expected Output |
|---------|-----------|-------|-----------------|
| UT-ILT-01 | `_setup_lighting` | halo_size=50 | 10 cached surfaces, sizes 97–103% |
| UT-ILT-02 | `_create_halo_surf` | radius=30 | 60×60 surface, center brighter |
| UT-ILT-03 | `_update_flicker` (animated) | frame_index=2 of 4 | f_alpha ≈ 1.0±0.14 |
| UT-ILT-04 | `_update_flicker` (static) | ticks=1000 | f_alpha in [0.85, 1.15] |
| UT-ILT-05 | `_update_flicker` (off) | is_on=False | f_alpha=1.0, f_scale=1.0 |
| UT-ILT-06 | `_draw_halo` | darkness=180 | Full brightness blit |
| UT-ILT-07 | `_draw_halo` | darkness=0 | 15% minimum brightness |

## 8. Deep Links
- **InteractiveLightingMixin**: [interactive_lighting.py:29](../../src/entities/interactive_lighting.py#L29)
- **InteractiveParticleMixin**: [interactive_particles.py:1](../../src/entities/interactive_particles.py#L1)
- **Constants**: [interactive_constants.py:1](../../src/entities/interactive_constants.py#L1)
- **Consumer**: [interactive.py:1](../../src/entities/interactive.py#L1)

## 9. Assumptions

| # | Assumption | Risk | Validation |
|---|-----------|------|------------|
| 1 | 10 cache buckets provide sufficient visual resolution | Low | Covers 0.97–1.03 range |
| 2 | `set_alpha()` on shared cache is safe (single-threaded render) | Low | Pygame is single-threaded |
| 3 | Quadratic falloff `(1-r/R)²` matches desired visual | Low | Playtested |
| 4 | `global_darkness / 180.0` normalization is correct | Medium | Depends on lighting system max |
