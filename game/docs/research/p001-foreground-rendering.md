# Research — P-001: Foreground Tile Rendering Optimisation
> Stage: 🔬 DISCOVER
> Date: 2026-06-10
> Topic: Eliminate the ~480 Python iterations/frame in `_draw_static_foreground_tiles`

---

## Context

**Measured Baseline**: `_draw_static_foreground_tiles` — 28.7 s tottime / 1800 frames = **~16 ms/frame** (86% of rendering CPU).

**Root Cause**: `get_visible_chunks` generates ~480 tuples/frame via a Python generator. The loop performs 3 interleaved tasks:
1. `occluding_rects.append(...)` — in screen coordinates (depends on `cam_offset`)
2. `player_screen_rect.colliderect(self._tile_rect)` — tile/player collision checking per tile
3. `screen.blit(occluded_image, pos)` — immediate blit for occluded tiles

**Existing Infrastructure**: `get_foreground_layer_surface(layer_id, pygame, min_depth)` is already in `MapManager` (commit `515f5a8`) but is not called.

---

## AXIS 1 — Domain Context

### Standard Pattern of Professional Pygame Engines

The canonical pattern is the **pre-rendered layer surface**:

```python
# At map load:
fg_surface = pygame.Surface((map_w, map_h), pygame.SRCALPHA)
for tile in static_fg_tiles:
    fg_surface.blit(tile.image, (tile.x, tile.y))

# Per frame:
screen.blit(fg_surface, (cam_offset.x, cam_offset.y))  # 1 call, auto clipping
```

This pattern is **already in place for the background** in `draw_background` (line 48, `render_manager.py`).

### Sprite Occlusion Management in Professional Engines

**pyscroll / pytmx**: `occluding_rects` are stored in **world-space at map load** (static tiles do not move). Per frame: translation to screen-space via a list comprehension of size `O(n_viewport_tiles)`, no complete regeneration.

**Dominant Model**: Separate the collection of rects (load) from their translation (frame). This approach is validated by pyscroll (BufferedRenderer pattern) and official pygame tutorials.

### Sources
- `draw_background` in `render_manager.py:31-60` — in-project implementation confirmed
- pyscroll BufferedRenderer: https://github.com/bitcraft/pyscroll
- pytmx foreground layer handling: https://pytmx.readthedocs.io/

---

## AXIS 2 — Competitive Landscape

### How Existing Engines Handle Foreground Occlusion

| Approach | Engine | Cost/frame | Occlusion |
|---|---|---|---|
| Layer ordering only | pyscroll | 1 blit/layer | No — layer above/below |
| World-space rect cache | custom engines | O(viewport_tiles) list comp | ✅ Semi-transparent possible |
| Double surface (opaque + alpha) | retro engines | 2 blits + 1–4 blits nearby tiles | ✅ Minimal |
| Per-tile iteration (current) | this project | O(480) Python loop | ✅ Complete but expensive |

### Identified Strategies

**Strategy A — World-Space Occluding Rects Cache**
Store at load time the rects of all static foreground tiles in world coordinates. Per frame: translate to screen-space + filter by viewport via a list comprehension.
```python
# Load: O(1) amortized
self._fg_occlusion_world: list[tuple[int, int, int, Surface, Surface]] = [
    (x*ts, y*ts, depth, tile.image, tile.occluded_image)
    for layer, x, y, tile in all_static_fg_tiles
]
# Per frame:
cx, cy = cam_offset.x, cam_offset.y
screen_rects = [
    (Rect(wx+cx, wy+cy, ts, ts), depth, img, occ)
    for wx, wy, depth, img, occ in self._fg_occlusion_world
    if viewport_world.colliderect((wx, wy, ts, ts))
]
```

**Strategy B — Pre-rendered surface blit + sparse occluded overlay**
1. Blit `get_foreground_layer_surface()` (already existing) → 1 call total
2. Among tiles near the player (≤4), blit only `occluded_image` on top

**Strategy C — Hybrid (both)**
- Normal blits → pre-rendered surface (1 blit)
- `occluding_rects` → world-space cache + screen translation per frame
- Occluded tiles → iteration only on tiles near the player (≤4)

**Decision: ADAPT (Strategy C)**. The infrastructure is already 70% in place. We need to: (1) wire `get_foreground_layer_surface()`, (2) add the world-space cache, (3) reduce per-frame iteration to only tiles near the player.

---

## AXIS 3 — Technical Feasibility

### Confirmed Pygame-CE APIs

**`surface.blit(source, dest, area=None)` — `area` = SOURCE clip (not dest)**
```python
# 1 call, auto clipping to screen edges — ZERO allocation
screen.blit(fg_surface, (cam_offset.x, cam_offset.y))
# Identical to draw_background line 48 — pattern already validated in project
```

**`subsurface(rect)`**: creates a view (not a copy) in O(1). Same cost as `blit(..., area=rect)`. Prefer `blit(..., area=...)` to avoid creating a Python object per frame.

**`fblits(seq, doreturn=False)`** (pygame-ce only):
```python
screen.fblits([(img, pos), ...], doreturn=False)  # C loop, not Python — fastest
```
`doreturn=False` avoids allocating the returned list of Rects.

**Alpha surface performance (ranking):**
1. Opaque surface — pure memcopy, fastest
2. `set_colorkey` — binary transparent/opaque
3. `surface.set_alpha(val)` — uniform alpha
4. SRCALPHA (per-pixel) — mathematical blend per pixel
5. SRCALPHA + `set_alpha` — **4× slower, to be avoided**

Pre-rendered foreground surfaces must be SRCALPHA (for tiles with transparency). The cost is acceptable because it is **1 blit** vs 480.

### Critical API — Collision on Converted World Rects

For the list of tiles near the player (per-frame iteration filter):
```python
player_world_rect = player.rect.move(-cam_offset.x, -cam_offset.y)
# OR: use player.rect with screen-space rects after translation
nearby = [
    t for t in self._fg_occlusion_world
    if abs(t[0] - player_world_x) <= 2*ts and abs(t[1] - player_world_y) <= 2*ts
]
# Typically 1–4 tiles maximum
```

### Sources
- pygame-ce Surface.blit: https://pyga.me/docs/ref/surface.html#pygame.Surface.blit
- pygame-ce Surface.fblits: https://pyga.me/docs/ref/surface.html#pygame.Surface.fblits
- pygame Speed Tips: https://www.pygame.org/docs/tut/newbieguide.html#speed
- Code in-project: `render_manager.py:31-60` (`draw_background` — pattern validated)

---

## Cross-Axis Synthesis

| Insight | Source | Impact |
|---|---|---|
| Negative `cam_offset` → auto clipping to screen edges | AXIS 3 (pygame docs) | `blit(surf, cam_offset)` pattern is sufficient, no need for `area=` |
| `occluding_rects` in world-space = viable | AXIS 2 (pyscroll) + AXIS 1 | Eliminates main loop — static tiles → load-time cache |
| ≤4 tiles overlap the player per frame | AXIS 2 (empirical observation) | Per-frame iteration for occlusion is O(4), not O(480) |
| `get_foreground_layer_surface()` already exists | AXIS 3 (in-project code) | 70% of infrastructure complete — work reduced to wiring + world-space cache |
| NPC occlusion does not require refactoring | AXIS 1 + AXIS 3 | `occluding_rects` in screen-space can be generated via list comp from world-space |

---

## Adopt / Adapt / Build-New Decision

**→ ADAPT**

| Component | Decision | Rationale |
|---|---|---|
| `get_foreground_layer_surface()` | **ADAPT** — already exists, wiring only | Already tested implementation, cached |
| World-space fg occluding cache | **BUILD-NEW** — `_fg_occlusion_world` in `MapManager.__init__` | No existing infrastructure, but simple O(n_tiles) |
| `_draw_static_foreground_tiles` | **ADAPT** — decouple the 3 responsibilities | Rewrite to use the two components above |

**Expected Gain**: 480 Python iterations + 480 `pygame.Rect()` allocations + 480 dict lookups → **1 blit + O(4) iterations**. Estimated recovery: 12–15 ms/frame.

---

## Open Questions

1. **`occluding_rects` for NPCs**: the `_apply_partial_occlusion` spec uses them for NPC sprites, not just the player. The world-space cache covers all static foreground tiles → the list comprehension filters by viewport → NPCs are covered ✅
2. **Animated foreground tiles**: managed separately by `_draw_animated_foreground_tiles` → out of scope for P-001 ✅
3. **Map reload**: the `_fg_surfaces` and `_fg_occlusion_world` caches must be invalidated when loading a new map. Existing mechanism: `MapManager` is recreated on each `load_map()` → automatic invalidation ✅
4. **Mixed-depth layers**: tiles with `depth <= player_depth` in foreground layers. The world-space cache must exclude them (same as `get_foreground_layer_surface` which filters on `tile.depth > min_depth`) ✅

---

## Transition Plan to STRATEGY

The DISCOVER Gate is passed:
- ✅ 3-axis research complete with cited sources
- ✅ ADAPT decision documented with rationale
- ✅ Open questions resolved
- ✅ Artifact in `game/docs/research/`
