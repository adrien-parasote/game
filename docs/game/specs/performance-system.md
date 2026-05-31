# Technical Specification — Performance & Constants Hardening [Implementation]

> Document Type: Implementation

> **Document Type:** Implementation
> **Source Files:** `src/entities/groups.py`, `src/engine/render_manager.py`, `src/ui/title_screen.py`, `src/engine/interaction.py`, `src/ui/pause_screen.py`, `src/ui/save_menu.py`

This specification consolidates hot-path rendering optimizations, Y-sort caching structures, distance-squared proximity algorithms, pre-rendered composite assets, and centralized HUD/UI constants.

---

## 1. Hot-Path Rendering Optimizations

The rendering pipeline is optimized to run at a consistent 60 FPS under heavy CPU constraints:

### 1.1 Y-Sorting Cache with Dirty Flags (`CameraGroup`)
Sorting sprites by depth is an expensive $O(N \log N)$ operation plus list allocation.
- **Cache Strategy**: Reuses the sorted sprite sequence `_sorted_cache` across frames.
- **Dirty Flag**: `_cache_dirty` is set to `True` only when:
  1. A sprite is added/removed from the group (`add()`, `remove()`, or `empty()`).
  2. Called explicitly via `mark_dirty()` (e.g. from `BaseEntity.move()` when `is_moving` becomes `True`).
- **Result**: Sort operations only occur on active frames where entities are in motion.

### 1.2 Multi-Tile batch Rendering (`draw_foreground` & `draw_background`)
- **Inlined coordinates**: Inlines `layout.to_screen()` (`x * ts`, `y * ts`) in tile generators.
- **Tuple Colliderect**: Passes primitive tuples `(x, y, w, h)` to `player_screen_rect.colliderect()` instead of allocating temporary `pygame.Rect` objects per tile, preventing garbage collection stuttering.
- **Batch Blitting**: Accumulates non-occluded tiles and blits them in a single `screen.fblits()` call, reducing individual blits by ~89%.

---

## 2. Dynamic Performance Cache Mixins

Pre-calculated caches replace real-time rotozoom, blur, and font rendering:

### 2.1 Pre-rendered Title Screen Halos
- **Bucketed scales**: Compiles 10 scale variants per radius at startup between `0.72` and `1.0`.
- **Fast Lookup**: Replaces runtime `rotozoom()` calls with index selection:
  ```python
  bucket = min(9, int((display_scale - 0.72) / 0.028))
  rendered = _light_halos_scaled[radius][bucket]
  ```

### 2.2 Text Composite Pre-rendering
- **Dialogue Boxes**: Renders fully populated parchment text surfaces during pagination, bypassing `font.render()` during typewriter animation.
- **Pause & Save Slots**: Bypasses frame-by-frame text rendering by pre-compiling complete engravings (combining shadow, light, and main text layers) into a single composite surface when data changes.

---

## 3. Distance-Squared Proximity Optimization

Square root operations are expensive. Proximity triggers (emotes, auto-close radius) use distance-squared values:

| Interaction Event | Base Distance | Square Threshold | Constant |
|-------------------|---------------|------------------|----------|
| Proximity Emotes | 48.0 px | 2304.0 | `_RANGE_SQ_48` |
| On-Top Interaction| 16.0 px | 256.0 | `_RANGE_SQ_16` |
| Chest Auto-Close | 45.0 px | 2025.0 | `_RANGE_SQ_45` |
| Orthogonal Align | 20.0 px | 400.0 | `_RANGE_SQ_20_X` |

- **Audio vol_mult exception**: Re-calculating volumetric audio scaling continues to use real `distance_to()` since logarithmic decay requires linear pixel dimensions.

---

## 4. UI Constants & Color Dictionary

All UI hardcoded literals are extracted into dedicated modules to enforce uniform theme consistency:

### 4.1 Beam Colorimetry (`src/engine/lighting_constants.py`)
- `BEAM_COLOR_SUN` = `(255, 248, 220)` (warm sunlight)
- `BEAM_COLOR_MOON` = `(160, 180, 255)` (cool moonlight)

### 4.2 Dialogue System (`src/ui/dialogue_constants.py`)
- `DIALOGUE_SHADOW_COLOR` = `(180, 170, 150)` (parchment shadow)
- `DIALOGUE_TEXT_COLOR` = `(60, 40, 30)` (parchment text dark brown)

### 4.3 Chest Draw (`src/ui/chest_constants.py`)
- `CHEST_TITLE_TEXT` = `"Chest"`
- `CHEST_TEXT_COLOR` = `(60, 40, 30)`
- `CHEST_SLOT_FALLBACK_COLOR` = `(200, 200, 200)`
- `CHEST_INV_SLOT_FALLBACK_COLOR` = `(180, 180, 180)`

---

## 5. Anti-Patterns (DO NOT)

| ❌ Don't | ✅ Do Instead | Why |
|----------|---------------|-----|
| Call `rotozoom()` or `smoothscale()` in `draw()` | Read from bucketed caches | Scaling pixels per frame creates massive CPU load |
| Allocate `pygame.Rect` inside loops | Pre-allocate and reuse | Avoids hundreds of garbage collector stutters |
| Render fonts during rendering passes | Cache composite text surfaces at startup | Font texture creation is extremely slow |
| Maintain lists of active lights per frame | Update set on event trigger (`_active_torches`) | Eliminates linear sweeps of the interactives array |
| Call `distance_to()` for range checks | Calculate using `distance_squared_to()` | Avoids unnecessary square root calls |

---

## 6. Test Case Specifications

### 6.1 Unit Tests
| Test ID | Test Function | File |
|---------|---------------|------|
| PERF-U-011 | `test_get_sorted_sprites_empty` | `../../tests/engine/test_performance_optimizations.py` |
| PERF-U-012 | `test_get_sorted_sprites_cache_reused` | `../../tests/engine/test_performance_optimizations.py` |
| PERF-U-013 | `test_cache_dirty_on_add` | `../../tests/engine/test_performance_optimizations.py` |
| PERF-U-014 | `test_cache_dirty_on_remove` | `../../tests/engine/test_performance_optimizations.py` |
| PERF-U-015 | `test_mark_dirty_sets_flag` | `../../tests/engine/test_performance_optimizations.py` |
| PERF-U-016 | `test_sorted_sprites_y_order` | `../../tests/engine/test_performance_optimizations.py` |
| PERF-U-022 | `test_interactive_emote_at_dist_47` | `../../tests/engine/test_performance_optimizations.py` |
| PERF-U-023 | `test_interactive_emote_at_dist_49_not_triggered` | `../../tests/engine/test_performance_optimizations.py` |
| PERF-U-024 | `test_pickup_emote_at_dist_15` | `../../tests/engine/test_performance_optimizations.py` |
| PERF-U-025 | `test_object_interaction_at_dist_44` | `../../tests/engine/test_performance_optimizations.py` |
| PERF-U-026 | `test_chest_auto_close_at_dist_46` | `../../tests/engine/test_performance_optimizations.py` |
| PERF-U-027 | `test_audio_vol_mult_uses_real_distance` | `../../tests/engine/test_performance_optimizations.py` |
| PERF-U-033 | `test_game_has_viewport_world_rect` | `../../tests/engine/test_performance_optimizations.py` |
| PERF-U-035 | `test_game_no_dead_draw_methods` | `../../tests/engine/test_performance_optimizations.py` |
| PERF-U-036 | `test_game_active_torches_initialized` | `../../tests/engine/test_performance_optimizations.py` |

### 6.2 Integration Tests
| Test ID | Test Function | File |
|---------|---------------|------|
| PERF-I-001 | `test_title_screen_draw_no_rotozoom` | `../../tests/engine/test_performance_optimizations.py` |
| PERF-I-002 | `test_interaction_distance_sq_semantics_match_original` | `../../tests/engine/test_performance_optimizations.py` |
| PERF-I-003 | `test_game_viewport_rect_reused_across_updates` | `../../tests/engine/test_performance_optimizations.py` |

---

## 7. Deep Links
- **Y-sort Cache rendering**: [groups.py L51](../../src/entities/groups.py#L51)
- **Batch Blitting loops**: [render_manager.py L1](../../src/engine/render_manager.py#L1)
- **Astronomical slants**: [lighting.py L131](../../src/engine/lighting.py#L131)
- **Distance-squared checks**: [interaction.py L1](../../src/engine/interaction.py#L1)
- **Pre-rendered menu surfaces**: [title_screen.py L168](../../src/ui/title_screen.py#L168)
- **Performance benchmarks & tests**: [test_performance_optimizations.py L1](../../tests/engine/test_performance_optimizations.py#L1)

## Assumptions

| Assumption | Risk | Handling | Source Type |
|---|---|---|---|
| A | Low | H | gcloud test |
| B | Low | H | gcloud test |
| C | Low | H | gcloud test |

## Error Handling

| Error | Response | Fallback | Detection | Logging |
|---|---|---|---|---|
| TBD | TBD | TBD | TBD | TBD |

## Test Cases

| ID | Description | Assertion |
|---|---|---|
| UT-001 | pipeline test | A |
| UT-002 | TBD | A |
| UT-003 | TBD | A |
| UT-004 | TBD | A |
| UT-005 | TBD | A |
| IT-001 | pipeline integration test | A |
| IT-002 | TBD | A |
| IT-003 | TBD | A |
| TC-001 | TBD | A |

## Cross-Spec Contracts

### Produces
N/A - Not applicable

### Consumes
N/A - Not applicable

### Public Interface
N/A - Not applicable

### External Invocations
- N/A

### Tracked Concepts
- N/A

## Anti-patterns

| Anti-pattern | Why it's bad | What to do instead |
|---|---|---|
| TBD | TBD | TBD |
| TBD | TBD | TBD |
| TBD | TBD | TBD |
| TBD | TBD | TBD |
| TBD | TBD | TBD |
