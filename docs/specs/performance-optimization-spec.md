[assumption: "All implicit constants and defaults are documented here – pending detailed entries"] – risk: Low

# Performance Optimization Spec

> Document Type: Implementation
> Version: 2.0 — 2026-05-15
> Audit source: performance_audit

## Scope

**Phase 1** (v1.0, 2026-05-04): 14 optimizations distributed across 6 modules. No architectural changes.
**Phase 2** (v2.0, 2026-05-15): 3 batches of micro-optimizations targeting the rendering hot path.
All modifications are backward-compatible with the existing test suite.

---

## Assumptions

| # | Assumption | Risk | Validation |
|---|------------|------|------------|
| A1 | `rotozoom(surf, 0, scale)` is equivalent to `smoothscale` for angle=0 | Low | Verify visually after implementation. |
| A2 | The 58 halos oscillate in `[0.72, 1.0]` — 10 buckets of 0.03 cover the range | Low | Calculated from min/max constants in `title_screen.py` |
| A3 | `distance_squared_to()` is available on `pygame.math.Vector2` (pygame-ce 2.5.7) | Low | Verified in pygame-ce documentation |
| A4 | `colliderect((x, y, w, h))` accepts a 4-tuple in pygame-ce | Low | Confirmed in SDL/pygame documentation |
| A5 | Y-sort can be cached without impacting visual correctness as long as sprites are sorted at least once per movement frame | Medium | Validate visually — if buggy, revert to systematic sorted() |

---

## Module 1 — `src/ui/title_screen.py` (P1, P2, P3)

### Implementation Decisions

**P1 — Replacing rotozoom with pre-calculated surfaces lookup**

At `__init__`, for each unique radius in `BACKGROUND_LIGHTS` and `MUSHROOM_LIGHTS`:
- Calculate `scale_range = [0.72, 1.0]` with 10 buckets of step `0.028`
- Pre-generate `N_SCALE_BUCKETS = 10` surfaces via `pygame.transform.smoothscale`
- Store: `_light_halos_scaled[radius][bucket_idx] -> Surface`
- Store: `_mushroom_halos_scaled[(color_key, radius)][bucket_idx] -> Surface`

In `draw()`, replace `rotozoom(halo_surf, 0, display_scale)` with:
```python
bucket = min(N_SCALE_BUCKETS - 1, int((display_scale - SCALE_MIN) / SCALE_STEP))
rendered = _light_halos_scaled[hr][bucket]
```

Constants to define in `title_screen.py` (not in `_constants.py`):
```python
_HALO_SCALE_MIN = 0.72   # observed min flicker value
_HALO_SCALE_MAX = 1.00   # observed max flicker value
_HALO_N_BUCKETS = 10
_HALO_SCALE_STEP = (_HALO_SCALE_MAX - _HALO_SCALE_MIN) / (_HALO_N_BUCKETS - 1)
```

**P2 — Cache for gaussian_blur surfaces (title + hover)**

New attributes initialized in `_load_assets()`:
- `_title_surf_cache: pygame.Surface` — composite title surface (blur+text), never re-generated
- `_menu_hover_cache: dict[int, pygame.Surface]` — composite surface per hovered item index

Invalidation: only when `_hovered_item` changes (compared to previous value).
`_prev_hovered_item: int | None = -2` — initial sentinel to force first render.

Logic in `_blit_halo_text()` → becomes `_render_halo_text()` (returns Surface, does not blit).
`draw()` calls `_render_halo_text()` only if the cache is invalid, otherwise blits directly.

**P3 — Pre-render of menu surfaces (idle + hover)**

In `_load_assets()`, after font construction:
```python
self._menu_label_surfaces: list[dict] = []  # [{idle: Surface, hover: Surface}, ...]
for key, default in zip(_MENU_ITEM_KEYS, _MENU_ITEM_DEFAULTS):
    label = self._i18n.get(key, default=default)
    self._menu_label_surfaces.append({
        "idle": self._render_engraved(label),   # 3-pass composite Surface
        "hover": self._render_halo_text(label, ...),  # blur+text composite Surface
    })
```

`_blit_engraved()` and `_blit_halo_text()` are decomposed into:
- `_render_engraved(label) -> Surface` (composes without blitting)
- `_render_halo_text(label, ...) -> Surface` (composes without blitting)
- `_draw_engraved(surf, cx, cy)` (blit only)
- `_draw_halo_text(surf, cx, cy)` (blit only)

`_draw_menu_items()` blits from `_menu_label_surfaces[i]["idle"|"hover"]`.

### Anti-Patterns (P1-P3)

| ❌ Don't | ✅ Do Instead | Why |
|----------|---------------|-----|
| Call `rotozoom()` in `draw()` | Lookup in `_light_halos_scaled` | `rotozoom` = O(pixels) per frame |
| Call `gaussian_blur()` in `draw()` | Blit from cache | `gaussian_blur` is CPU intensive |
| Call `font.render()` in `draw()` | Blit from `_menu_label_surfaces` | `render()` creates an SDL Surface on each call |
| Re-create cache if `_hovered_item` has not changed | Compare with `_prev_hovered_item` | Invalidate only on real change |
| Store surfaces in dict without bounded bucket | Use `min(N-1, ...)` on the index | Avoid IndexError on out-of-range values |
| Use `rotozoom` for angle=0 | Use `smoothscale` in pre-calculation | `smoothscale` is optimized for scale without rotation |

### Test Case Specifications (P1-P3)

| TC ID | Component | Input | Expected Output | Edge Case |
|-------|-----------|-------|-----------------|-----------|
| PERF-U-001 | `_load_assets` | init TitleScreen | `_light_halos_scaled` contains 10 surfaces per radius | radius = 0: skip |
| PERF-U-002 | `_load_assets` | init TitleScreen | `_mushroom_halos_scaled` contains 10 surfaces per (color, radius) | empty MUSHROOM_LIGHTS: empty dict |
| PERF-U-003 | `draw()` | `_light_time=0.0` | `rotozoom` is NOT called | flicker min/max boundaries |
| PERF-U-004 | `draw()` | `_hovered_item=None` (no change) | `gaussian_blur` is NOT called | first frame: force render |
| PERF-U-005 | `draw()` | `_hovered_item=0` → `_hovered_item=1` | cache invalidated for items 0 and 1 | `_hovered_item=None` → no cache needed |
| PERF-U-006 | `_render_halo_text` | label str, font, colors | Returns Surface with alpha > 0 | empty label: valid Surface |
| PERF-U-007 | `_render_engraved` | label str | Returns Surface with dimensions > 0 | empty label: valid Surface |
| PERF-U-008 | `_menu_label_surfaces` | post-init | len == len(_MENU_ITEM_KEYS) | items added dynamically |
| PERF-U-009 | bucket calc | `display_scale=_HALO_SCALE_MIN` | bucket_idx = 0 | scale < min → clamp to 0 |
| PERF-U-010 | bucket calc | `display_scale=_HALO_SCALE_MAX` | bucket_idx = N_BUCKETS-1 | scale > max → clamp to N-1 |

### Error Handling Matrix (P1-P3)

| Error | Detection | Response | Logging |
|-------|-----------|----------|---------|
| `BACKGROUND_LIGHTS` empty | `len == 0` | `_light_halos_scaled = {}` | DEBUG |
| `MUSHROOM_LIGHTS` empty | `len == 0` | `_mushroom_halos_scaled = {}` | DEBUG |
| `bucket` out of range | `min(N-1, max(0, bucket))` | Silent clamp | None |
| `gaussian_blur` AttributeError (pygame standard) | `except` AttributeError (existing) | Fallback already implemented | WARNING |

---

## Module 2 — `src/entities/groups.py` (P4)

### Implementation Decisions

Cache of Y-sort with dirty flag:
- `_sorted_cache: list[Sprite] = []`
- `_cache_dirty: bool = True`

`get_sorted_sprites()` returns the cache if `_cache_dirty == False`, otherwise sorts and caches.
The flag is set to `True` when:
1. A sprite is added/removed from the group (`add()` / `remove()` / `empty()`)
2. Called explicitly via `mark_dirty()` — public method

`CameraGroup.mark_dirty()` will be called from `BaseEntity.move()` when `self.is_moving` becomes `True`.

Override `add()` and `remove()` to auto-invalidate the cache.

### Anti-Patterns (P4)

| ❌ Don't | ✅ Do Instead | Why |
|----------|---------------|-----|
| Call `sorted()` every frame | Use the cache and the dirty flag | `sorted()` = O(n log n) + list allocation |
| Mark dirty every frame | Mark dirty only on change | Cancels the cache benefit |
| Override `update()` to invalidate | Override `add()`/`remove()` | Correct invalidation moment |

### Test Case Specifications (P4)

| TC ID | Component | Input | Expected Output | Edge Case |
|-------|-----------|-------|-----------------|-----------|
| PERF-U-011 | `get_sorted_sprites()` | empty group | `[]` | no sprites |
| PERF-U-012 | cache | 2nd call without add/remove | same list object (not re-calculated) | single sprite |
| PERF-U-013 | dirty flag | `add(sprite)` | `_cache_dirty = True` | multiple additions |
| PERF-U-014 | dirty flag | `remove(sprite)` | `_cache_dirty = True` | absent removal |
| PERF-U-015 | `mark_dirty()` | manual call | `_cache_dirty = True` | repeated calls |
| PERF-U-016 | Y-sort | sprites with different Y | returned sorted by increasing `rect.bottom` | identical Y |

### Error Handling Matrix (P4)

| Error | Detection | Response | Logging |
|-------|-----------|----------|---------|
| Empty group on sort | `len(sprites()) == 0` | Return `[]` | None |

---

## Module 3 — `src/engine/render_manager.py` (P5, P6)

### Implementation Decisions

**P5 — Tuple instead of Rect in `draw_foreground()`**

```python
# Before
dest_rect = pygame.Rect(screen_pos[0], screen_pos[1], self.game.tile_size, self.game.tile_size)
if player_screen_rect.colliderect(dest_rect):

# After
if player_screen_rect.colliderect((screen_pos[0], screen_pos[1], ts, ts)):
```
`ts = self.game.tile_size` — read once before the loop.

**P6 — Set `_active_torches` maintained in `Game`**

Added in `Game.__init__()`: `self._active_torches: set = set()`

Method `Game._update_active_torches(entity)` called from:
- `InteractionManager._check_object_interactions()` after `obj.interact()`
- `InteractiveEntity.restore_state()` (via `entity.game._update_active_torches(entity)`)
- `Game._update()` for day_night_driven entities (once per frame, but only day_night_driven entities)

Logic: `entity.is_on and entity.halo_size > 0` → add, otherwise discard.

In `draw_scene()`:
```python
# Before
active_torches = [obj for obj in self.game.interactives if ...]
# After
active_torches = self.game._active_torches
```

### Anti-Patterns (P5-P6)

| ❌ Don't | ✅ Do Instead | Why |
|----------|---------------|-----|
| `pygame.Rect()` in the tile loop | Pass tuple `(x, y, w, h)` to `colliderect()` | Avoids object allocation per tile |
| List comprehension on `interactives` every frame | Maintain `_active_torches: set` | Set lookup O(1), no iteration |
| Call `_update_active_torches` every frame for all entities | Call only on state change | Avoids redundant O(n) |

### Test Case Specifications (P5-P6)

| TC ID | Component | Input | Expected Output | Edge Case |
|-------|-----------|-------|-----------------|-----------|
| PERF-U-017 | `draw_foreground` | player outside foreground | `colliderect` called with tuple | tile at screen edge |
| PERF-U-018 | `_active_torches` | `interact()` torch on | entity added to the set | halo_size=0 → not added |
| PERF-U-019 | `_active_torches` | `interact()` torch off | entity removed from the set | absent entity → no error |
| PERF-U-020 | `draw_scene()` | night active | `create_overlay` receives `_active_torches` | empty set → overlay without holes |
| PERF-U-021 | `restore_state` | is_on=True, halo_size>0 | entity in `_active_torches` | game=None → no-op |

### Error Handling Matrix (P5-P6)

| Error | Detection | Response | Logging |
|-------|-----------|----------|---------|
| `entity.game` absent during `restore_state` | `hasattr(entity, 'game')` | No-op on `_update_active_torches` | None |
| Empty set for `_active_torches` | N/A (empty set = valid) | Overlay without torch masks | None |

---

## Module 4 — `src/engine/interaction.py` (P7)

### Implementation Decisions

Replace `distance_to()` with `distance_squared_to()` in all proximity functions.
Define module-level constants:

```python
_RANGE_SQ_48 = 48.0 ** 2   # 2304.0
_RANGE_SQ_16 = 16.0 ** 2   # 256.0
_RANGE_SQ_45 = 45.0 ** 2   # 2025.0
_RANGE_SQ_20_X = 20.0 ** 2 # 400.0  (for orthogonal alignment)
```

Impacted functions:
- `_check_interactive_emote()` : `dist >= range_dist` → `sq_dist >= _RANGE_SQ_48`
- `_check_pickup_emote()` : ditto
- `_check_npc_emote()` : ditto
- `_check_pickup_interactions()` : `dist >= range_dist` → `sq_dist >= _RANGE_SQ_48` ; `dist < 16` → `sq_dist < _RANGE_SQ_16`
- `_check_object_interactions()` : `dist < 16` → `sq_dist < _RANGE_SQ_16` ; `dist < 48` → `sq_dist < _RANGE_SQ_48` ; `dist < 45` → `sq_dist < _RANGE_SQ_45`
- `_check_chest_auto_close()` : `dist > 45` → `sq_dist > _RANGE_SQ_45`

**IMPORTANT**: `is_on_top = dist < 16.0` → `is_on_top = sq_dist < _RANGE_SQ_16`
The use of `distance_to()` for audio vol_mult REMAINS unchanged (real distance needed).

### Anti-Patterns (P7)

| ❌ Don't | ✅ Do Instead | Why |
|----------|---------------|-----|
| `distance_to()` for range guards | `distance_squared_to()` + constants `_RANGE_SQ_*` | costly sqrt for comparison |
| Recalculating `range ** 2` inline | Module-level constants | Avoids recalculation on every frame |
| Replacing `distance_to()` in audio vol_mult calculation | Keep `distance_to()` for audio | Audio volume requires real distance |
| Naming constants `DIST_48` | Name `_RANGE_SQ_48` | Avoids distance vs distance² confusion |

### Test Case Specifications (P7)

| TC ID | Component | Input | Expected Output | Edge Case |
|-------|-----------|-------|-----------------|-----------|
| PERF-U-022 | `_check_interactive_emote` | obj at dist=47 | emote triggered | dist exactly = 48: no emote |
| PERF-U-023 | `_check_interactive_emote` | obj at dist=49 | no emote | dist=0: is_on_top |
| PERF-U-024 | `_check_pickup_emote` | pickup at dist=15 | emote triggered (is_on_top) | dist=16: alignment required |
| PERF-U-025 | `_check_object_interactions` | obj at dist=44 | valid interaction | dist=45: invalid |
| PERF-U-026 | `_check_chest_auto_close` | dist=46 | chest closed | dist=44: chest remains open |
| PERF-U-027 | audio vol_mult | calculated dist | vol_mult between 0.4 and 1.0 | uses `distance_to()` (not sq) |

### Error Handling Matrix (P7)

| Error | Detection | Response | Logging |
|-------|-----------|----------|---------|
| `distance_squared_to` absent (old pygame) | N/A — pygame-ce 2.5.7 confirmed | N/A | N/A |

---

## Module 5 — `src/entities/interactive.py` (P9, P13, P14)

### Implementation Decisions

**P9 — Eliminating `.copy()` in `draw_effects()`**

Replace the `copy()` + `fill(MULT)` pattern with blit using `set_alpha()`:
```python
# Before
render_surf = self.light_mask_cache[scale_idx].copy()
m = max(0, min(255, int(round(255 * global_factor * self.f_alpha))))
if m < 255: render_surf.fill((m, m, m), special_flags=pygame.BLEND_RGB_MULT)
surface.blit(render_surf, halo_pos, special_flags=pygame.BLEND_RGB_ADD)

# After
render_surf = self.light_mask_cache[scale_idx]
m = max(0, min(255, int(round(255 * global_factor * self.f_alpha))))
render_surf.set_alpha(m)
surface.blit(render_surf, halo_pos, special_flags=pygame.BLEND_RGB_ADD)
```

**IMPORTANT**: `set_alpha()` on a Surface without SRCALPHA is a global alpha (surface-level), which is functionally equivalent to `BLEND_RGB_MULT` with a uniform value `(m, m, m)`.
The `light_mask_cache` surfaces are created with `pygame.Surface(...)` (without SRCALPHA) → `set_alpha()` is applicable.

**P13 — `pygame.time.get_ticks()` once per frame**

In `Game._update()`, calculate `_ticks_ms = pygame.time.get_ticks()` before the interactives loop.
Pass via `entity.update(dt, ticks_ms=self._ticks_ms)`.

Modify the signature of `InteractiveEntity.update(dt, ticks_ms=None)`.
Fallback: `ticks = ticks_ms if ticks_ms is not None else pygame.time.get_ticks()`.

**P14 — Remove Surface allocation in particle rendering**

```python
# Before (line 405)
surface.blit(pygame.Surface((p['size']*2, p['size']*2)), (int(p['x'] + cam_offset.x), ...))
pygame.draw.circle(surface, color, ...)

# After — remove the blit line, keep only draw.circle
pygame.draw.circle(surface, color, (int(p['x'] + cam_offset.x), int(p['y'] + cam_offset.y)), p['size'])
```

The line `surface.blit(pygame.Surface(...))` blits a black surface without a blend flag → no visual effect.

### Anti-Patterns (P9, P13, P14)

| ❌ Don't | ✅ Do Instead | Why |
|----------|---------------|-----|
| `.copy()` on `light_mask_cache` per frame | `set_alpha()` on existing surface | Avoids Surface allocation |
| `get_ticks()` per entity | Pass `ticks_ms` from `Game._update()` | 1 SDL call vs N calls |
| `blit(Surface(...))` black without blend | Delete the line | Operation with no visual effect |
| Changing the update(dt) signature without fallback | `update(dt, ticks_ms=None)` | Backward-compatible signature |

### Test Case Specifications (P9, P13, P14)

| TC ID | Component | Input | Expected Output | Edge Case |
|-------|-----------|-------|-----------------|-----------|
| PERF-U-028 | `draw_effects` | luminous entity, dark_factor=1.0 | `set_alpha(255)` called, no `.copy()` | m=255: set_alpha(255) |
| PERF-U-029 | `draw_effects` | `global_darkness=0` | `set_alpha` with m=`int(0.15*255)` | dark_factor=0 → 0.15 floor |
| PERF-U-030 | `update(dt, ticks_ms=500)` | luminous non-animated entity | `ticks_ms` used for `time_sec` | ticks_ms=None → get_ticks() |
| PERF-U-031 | `draw_effects` | active particles | `pygame.Surface` not allocated in particle loop | 0 particles: no call |
| PERF-U-032 | `update(dt)` | call without ticks_ms | fallback on `get_ticks()` | backward-compatible signature |

### Error Handling Matrix (P9, P13, P14)

| Error | Detection | Response | Logging |
|-------|-----------|----------|---------|
| Surface without `set_alpha` support | N/A — pygame.Surface always supported | N/A | N/A |
| `ticks_ms=None` passed | Check `if ticks_ms is not None` | Fallback `pygame.time.get_ticks()` | None |

---

## Module 6 — `src/engine/game.py` (P11, P12)

### Implementation Decisions

**P11 — Remove dead code**

The following methods in `game.py` are never called (replaced by `RenderManager`):
- `_draw_background()` (lines 429–460)
- `_draw_foreground()` (lines 462–482)
- `_draw_hud()` (lines 484–486)

Pure deletion. No functional impact.

**P12 — Pre-allocate `_viewport_world_rect`**

In `Game.__init__()` after `self.screen` creation:
```python
self._viewport_world_rect = pygame.Rect(0, 0, Settings.WINDOW_WIDTH, Settings.WINDOW_HEIGHT)
```

In `_update()` — replace the 3 creation lines with in-place update:
```python
offset = self.visible_sprites.offset
self._viewport_world_rect.x = -int(offset.x) - 128
self._viewport_world_rect.y = -int(offset.y) - 128
self._viewport_world_rect.width = self.screen.get_width() + 256
self._viewport_world_rect.height = self.screen.get_height() + 256
```

### Anti-Patterns (P11-P12)

| ❌ Don't | ✅ Do Instead | Why |
|----------|---------------|-----|
| Keeping `_draw_background/foreground/hud` in `game.py` | Delete them | Dead code → confusion + maintenance |
| `screen.get_rect().move(...)` every frame | Pre-allocate + in-place update | 2 Rect allocations avoided |
| `inflate_ip` on a Rect created inline | Apply margins in init values | Same result, 0 allocations |

### Test Case Specifications (P11-P12)

| TC ID | Component | Input | Expected Output | Edge Case |
|-------|-----------|-------|-----------------|-----------|
| PERF-U-033 | `Game.__init__` | init without map | `_viewport_world_rect` exists | `skip_map_load=True` |
| PERF-U-034 | `_update()` | offset=(−100, −50) | `_viewport_world_rect.x == -28, y == 22` (−(−100)−128=−28) | offset=0 |
| PERF-U-035 | deleted methods | `hasattr(game, '_draw_background')` | `False` | N/A |
| PERF-U-036 | `_active_torches` | init | empty `set()` | N/A |

### Error Handling Matrix (P11-P12)

| Error | Detection | Response | Logging |
|-------|-----------|----------|---------|
| non-integer offset | `int(offset.x)` | Explicit conversion | None |

---

## Integration Tests

| TC ID | Flow | Setup | Verification | Teardown |
|-------|------|-------|--------------|----------|
| PERF-I-001 | TitleScreen draw loop without transform | Init TitleScreen with non-empty BACKGROUND_LIGHTS, call `draw()` 10× | `pygame.transform.rotozoom` is NOT called; `_light_halos_scaled` used | N/A |
| PERF-I-002 | Interaction distance_squared vs distance_to semantic equivalence | Configure obj at dist=45 and dist=47 from player, call `_check_interactive_emote()` | dist=47 → emote; dist=45+ → no emote (same behavior as before migration) | N/A |
| PERF-I-003 | Game._update NPC visibility with pre-allocated rect | Create mocked Game with 3 NPCs at varied positions, call `_update()` 2× with different offsets | `_viewport_world_rect` reused (same object id), `npc.is_visible` updated correctly | N/A |

---

## Deep Links

- **Audit source**: performance_audit.md
- **TitleScreen**: [title_screen.py L1](../../src/ui/title_screen.py#L1)
- **TitleScreen constants**: [title_screen_constants.py L1](../../src/ui/title_screen_constants.py#L1)
- **CameraGroup**: [groups.py L51](../../src/entities/groups.py#L51)
- **RenderManager**: [render_manager.py L1](../../src/engine/render_manager.py#L1)
- **InteractionManager**: [interaction.py L1](../../src/engine/interaction.py#L1)
- **InteractiveEntity.update**: [interactive.py L308](../../src/entities/interactive.py#L308)
- **Game._update**: [game.py L637](../../src/engine/game.py#L637)
- **Title screen tests**: [test_title_screen.py L1](../../tests/ui/test_title_screen.py#L1)
- **Interaction tests**: [test_interaction.py L1](../../tests/engine/test_interaction.py#L1)
- **Render manager tests**: [test_render_manager.py L1](../../tests/engine/test_render_manager.py#L1)
- **Lighting tests**: [test_lighting.py L1](../../tests/engine/test_lighting.py#L1)
- **DialogueManager**: [dialogue.py L1](../../src/ui/dialogue.py#L1)

---

## Absorbed from optimization-spec.md (2026-05-07)

> The specifications below come from `optimization-spec.md` (consolidated here).

### DialogueManager Optimization TCs

| TC ID | Component | Input | Expected Output | Edge Cases |
|-------|-----------|-------|-----------------|------------|
| TC-DLG-01 | Pagination | Very long text | Correct number of pages | Empty string, single word |
| TC-DLG-02 | Typewriter | `dt` updates | `displayed_text` matches index | Speed=0, extreme `dt` |
| TC-DLG-03 | Advancing | Skip input | Page complete immediately | Last page closes |

### Linked Test Functions
| Test ID | Test Function | File |
|---------|---------------|------|
| TC-DLG-01 | `test_dialogue_pagination` | `../../tests/ui/test_inventory.py:L238` |
| IT-INT-01 | `test_handle_interaction_npc` | `../../tests/engine/test_interaction.py:L169` |
### Linked Test Functions
| Test ID | Test Function | File |
|---------|---------------|------|
| PERF-I-001 | `test_title_screen_draw_no_rotozoom` | `../../tests/engine/test_performance_optimizations.py` |
| PERF-I-002 | `test_interaction_distance_sq_semantics_match_original` | `../../tests/engine/test_performance_optimizations.py` |
| PERF-I-003 | `test_game_viewport_rect_reused_across_updates` | `../../tests/engine/test_performance_optimizations.py` |
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
| TC-DLG-01 | `test_dialogue_pagination` | `../../tests/ui/test_inventory.py` |
| IT-INT-01 | `test_handle_interaction_npc` | `../../tests/engine/test_interaction.py` |
| IT-INT-02 | `test_interaction_toggle_entity_by_id` | `../../tests/engine/test_interaction.py` |

---

## Phase 2 — Batch Performance Optimizations (2026-05-15)

> Profiling baseline: 600-frame cProfile run. Commits: `8940440` (Batch 1), `f0aab8c` (Batch 2), `c743c42` (Batch 3).

### Batch 1 — Import & Attribute Lookup Cleanup (✅ DONE)

| File | Change | Impact |
|------|--------|--------|
| `src/entities/groups.py` | `from src.config import Settings` moved to module top | Eliminates per-frame `sys.modules` dict lookup in 120Hz `custom_draw` |
| `src/entities/interactive.py` | Removed `hasattr`/`getattr` guards in `update()` | Direct attr access — attrs always set in `__init__` |
| `src/engine/game.py` | `anim_map_manager = None` in `_init_groups()` | Eliminates 2× `getattr` per frame |
| `src/engine/render_manager.py` | Pre-allocated `_tile_rect`, `_screen_rect`, `_viewport_world` in `__init__` | Eliminated ~54K `Rect()` allocations/sec |
| `src/engine/audio.py` | Early-exit in `flush_ambient()` when no sources; volume guard in `play_sfx` | Avoids set allocation and SDL audio write |

**Measured result**: 8.38ms → 8.25ms avg frame time (600-frame run).

### Batch 2 — `fblits` Batch Rendering + Inline `to_screen` (✅ DONE)

| File | Change | Impact |
|------|--------|--------|
| `src/map/manager.py` | Inlined `layout.to_screen()` (`x * ts, y * ts`) in tile generators | Eliminated 199K method calls/600 frames |
| `src/engine/render_manager.py` | `draw_foreground`: non-occluded tiles → list → `screen.fblits()` | `blit()` calls: 212K → 23K (−89%) |
| `src/engine/render_manager.py` | `draw_background`: animated tiles → `screen.fblits()` | Further blit reduction |
| `src/engine/render_manager.py` | Cache `player_depth`, `tiles`, `screen` as locals | Reduces `self.game.*` chain lookups per tile |

**Measured result**: `blit()` calls −89%; `draw_foreground` cumtime −14%; total calls 3.40M → 3.24M (−4.7%).

> **Rule**: Tiles needing `colliderect` check (occluded) MUST remain individual `blit()`. All others MUST use `fblits()`.

### Batch 3 — Eliminate `getattr` on `TileMapData` (✅ DONE)

`TileMapData` is a `@dataclass` — `depth` (required) and `frames` (default `None`) are always set at parse time. All `getattr(tile, 'depth', 0)` and `getattr(tile, 'frames', None)` replaced with direct `tile.depth` / `tile.frames`.

Affected: `layer_max_depths` init, `get_layer_surface()`, `get_visible_chunks()`, `get_visible_animated_chunks()` in `src/map/manager.py`.

**Measured result**: 3.24M → 2.46M function calls (−24%); `get_visible_chunks` −32% (0.208s → 0.141s).

### Phase 2 Cumulative Results

| Metric | Before Batch 1 | After All Batches | Delta |
|--------|---------------|-------------------|-------|
| Total function calls (600 frames) | ~3.40M | 2.46M | −28% |
| `blit()` calls | 212K | 23K | −89% |
| `get_visible_chunks` tottime | 0.208s | 0.141s | −32% |
| Avg frame time | 8.38ms | ~7.96ms | −5% |
