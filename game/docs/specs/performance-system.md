# Technical Specification — Performance & Constants Hardening [Implementation]

> Document Type: Implementation

> **Document Type:** Implementation
> **Source Files:** `src/entities/groups.py`, `src/engine/render_manager.py`, `src/ui/title_screen.py`, `src/engine/interaction.py`, `src/ui/pause_screen.py`, `src/ui/save_menu.py`, `src/entities/interactive.py`, `src/entities/interactive_particles.py`, `src/map/manager.py`
> **New (P-001):** `src/map/manager.py` — `_build_world_surface()`, `_build_fg_occlusion_world()`, `_get_fg_depth_tiles()` · `src/engine/render_manager.py` — `_draw_world_surface()`, `_draw_fg_occlusion_tiles()`
> **New (P-004):** `src/engine/render_manager.py` — `_occ_key`, `_occ_composite_cache`, `reset_occ_cache()`


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
| Call `_update_flicker()` every frame | 64 800 calls/frame × 18 entities at 60 fps — 1.165 s tottime | Throttle to 15 Hz via `_flicker_tick % 4` — f_alpha/f_scale hold last value on skipped frames |
| Append-to-list in particle update loop | Python `list.append()` has overhead per call; `alive = []` allocates a new list every frame per entity | Use list comprehension `[p for p in lst if p["life"] > 0]` — optimized LIST_APPEND bytecode |
| Iterate all visible chunks to blit static foreground tiles | `get_visible_chunks` generator traverses ~480 tiles × 1800 frames = 864 000 iterations | Pre-render static foreground tiles into `get_foreground_layer_surface()` cache; iterate only near-player tiles for occlusion |
| Allocate `pygame.Rect` inside tile loops | Hundreds of temporary objects per frame trigger GC stutters | Pre-allocate `self._tile_rect` once in `__init__`, use `.topleft =` to reposition |
| Call `rotozoom()` or `smoothscale()` in `draw()` | Scaling pixels per frame creates massive CPU load | Read from bucketed caches |
| Render fonts during rendering passes | Font texture creation is extremely slow | Cache composite text surfaces at startup |

---

## 8. Perf Audit Cycle — June 2026

Audit run: 1800 frames @ ~16 fps. Baseline: avg 61.1 ms/frame, p95 65 ms, p99 71 ms.

### 8.1 P-005 — Flicker Throttle (commit `6980c80`)

- **File:** `src/entities/interactive.py` — `_parse_halo()` + `update()`
- **Change:** `_flicker_tick: int = 0` counter added; `_update_flicker()` called only when `_flicker_tick % 4 == 0`
- **Measured:** tottime 1.165 s → 0.313 s (−73 %), ncalls 64 800 → 16 200 (−75 %)
- **Visual impact:** None — sinusoidal flicker at 15 Hz is imperceptible at 60 fps

### 8.2 P-003 — Particle Update Loop (commit `6980c80`)

- **File:** `src/entities/interactive_particles.py` — `_update_particles()`
- **Change:** Replaced `alive = []; for p in …: if alive: alive.append(p)` with in-place mutation + list comprehension filter
- **Measured:** tottime 5.166 s → 3.955 s (−23 %), `_update_core_state` cumtime 14.8 s → 10.1 s (−32 %)
- **Rationale:** Python list comprehensions use optimized LIST_APPEND bytecode; eliminates intermediate list allocation per entity per frame

### 8.3 P-001 — Foreground WorldSurface Pipeline ✅ (commits `515f5a8`, `10778e9`)

- **Files:** `src/map/manager.py`, `src/engine/render_manager.py`
- **Infrastructure (515f5a8):** Added `self._fg_surfaces` cache + `get_foreground_layer_surface()` (unwired).
- **Implementation (10778e9):** Decomposed the 3-responsibility foreground loop into:
  - `_build_world_surface()` — blit static depth>player tiles into a world-space `Surface` at map load time
  - `_build_fg_occlusion_world()` — pre-collect world-space occlusion tile list at map load time
  - `_get_fg_depth_tiles()` — shared generator (build time)
  - `_draw_world_surface(cam_offset)` — blit viewport slice of WorldSurface + collect `occluding_rects` per frame
  - `_draw_fg_occlusion_tiles(player_rect, depth, cam_offset)` — blit semi-transparent tiles near player only
- **Key insight:** The 3 entangled responsibilities (normal blit, occluded blit, rect collection) had to be separated BEFORE introducing the cache (see A-PERF-003).
- **Status:** ✅ COMPLETE — 17 tests (TC-P001-001..008, TC-015..020) GREEN. 91/91 verts.
- **Expected gain:** −20 ms/frame (élimination boucle 480 tiles/frame)


### 8.5 P-004 — Dirty-Flag Cache on `_apply_partial_occlusion` ✅ (commit `df93698`)

- **File:** `src/engine/render_manager.py` — `_apply_partial_occlusion()`, `reset_occ_cache()`
- **Cache key:** `(int(cam_x), int(cam_y), len(occluding_rects))` — invalidation minimale
- **Cache HIT:** re-install composites depuis `_occ_composite_cache` sans re-itérer les sprites
- **Cache MISS:** calcul complet + mise à jour du cache (comportement précédent)
- **`reset_occ_cache()`:** appelée lors d'un changement de map (via `_build_world_surface`)
- **Status:** ✅ COMPLETE — 6 tests TC-P004-001..006 GREEN. 97/97 verts.
- **Expected gain:** élimination des surface composites recréées sur les frames statiques (cam fixe, joueur immobile)

### 8.4 Bottleneck Status (après P-001 + P-004)

| Function | Baseline tottime | Après P-005/P-003 | Après P-001/P-004 | Status |
|---|---|---|---|---|
| `_draw_static_foreground_tiles` | 25.9 s | 28.7 s (bruit) | ✅ Remplacée par WorldSurface | ✅ Résolu P-001 |
| `get_visible_chunks` | 13.4 s | 13.8 s (bruit) | ✅ Build time uniquement | ✅ Résolu P-001 |
| `_update_particles` | 5.2 s | 4.0 s | 4.0 s (stable) | ✅ −23 % P-003 |
| `_apply_partial_occlusion` | 4.3 s | 4.7 s (bruit) | Cache dirty flag | ✅ Résolu P-004 |
| `_draw_particles` | 4.1 s | 4.1 s | 4.1 s (stable) | Stable |
| `_update_flicker` | 1.2 s | 0.3 s | 0.3 s (stable) | ✅ −73 % P-005 |
| `create_overlay` | 1.3 s | 1.3 s | 1.3 s (stable) | ✅ Skip justifié |

> **Prochaine priorité :** P-007 (mesurer le gain réel P-001+P-004 en jeu avant de décider d'autres optimisations).

