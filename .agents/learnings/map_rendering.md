## 🗺️ Map & Rendering

### L-MAP-001 · 2026-04-28 · U · Major Rework
**Semantic name-based layer ordering**

Tiled JSON layer order is unstable — nested groups reorder silently. Sort layers by semantic name prefix (`00-`, `01-`) in `MapManager` instead.

```python
# ✅
layer_order = sorted(raw_order, key=lambda lid: self.layer_names.get(lid, ""))
```

**Evidence:** Background (`00-layer`) disappeared due to group nesting. `tests/test_map.py` confirmed fix.

---

### L-REND-001 · 2026-04-28 · U · Perfect
**Additive light overlays applied after darkness**

Apply `BLEND_ADD` light sources after the global darkness surface. Applying before causes darkness to dim the light source.

---

### A-MAP-001 · 2026-04-28 · U · Major Rework
**Index-based layer priority** → See L-MAP-001 (same root cause).

---


### L-REND-002 · 2026-05-01 · U · Minor Rework
**Corner-fade approach for shaped surface bottoms**

Using `effective_t = t * (1 + dist * k)` to make edges fade faster than the center also dims the center column at the bottom, creating a spike/triangle shape instead of an oval.

```python
# ❌ Couples center and edge: center spikes because effective_t > 1 at edges
effective_t = t * (1.0 + dist_x * 0.9)
v_fade = max(0.0, 1.0 - effective_t) ** 0.35

# ✅ Keep v_fade independent, add a separate corner multiplier in the bottom zone only
v_fade = (1.0 - t) ** 0.6  # unchanged for all x
if t > 0.65:
    bp = (t - 0.65) / 0.35
    cf = max(0.0, 1.0 - bp * abs(x - cx) / half_w * 1.8)  # 1.0 at center, fades at edges
else:
    cf = 1.0
alpha = master_alpha * v_fade * h_fade * cf
```

**Rule:** Never modify a per-row decay function based on per-pixel horizontal distance. Add a separate multiplier that's always 1.0 at the center column.
**Evidence:** User screenshot showed spike; corner_fade approach restored trapezoid shape with oval bottom.

---

---

### L-REND-003 · 2026-05-01 · U · Minor Rework
**Continuous cosine blending for cyclic state transitions**

Hard `if brightness < threshold: moon else: sun` switches create visible discontinuities ("tic") at state transitions like dawn/dusk.

```python
# ❌ Binary switch — 42px jump at 18h
if brightness < 0.15:
    return moon_slant   # e.g., +14px
else:
    return sun_slant    # e.g., -28px at 18h

# ✅ Two continuous cosine waves blended by brightness
sun_slant  = max_slant * cos(2π * (hour - 6) / 24)
moon_slant = max_slant * 0.5 * cos(2π * (hour - 18) / 24)
slant = sun_slant * brightness + moon_slant * (1 - brightness)
```

**Rule:** For any cyclic parameter that transitions between two modes (day/night, seasons, tides), model each mode as an independent continuous function and blend by the existing continuous transition weight.
**Evidence:** Slant continuity test — max jump < 5px across 48 half-hour samples vs. 42px jump with if/else.

---

---

### L-MAP-002 · 2026-05-13 · U · Major Rework
**Tiled exact wangid array order**

Tiled's terrain auto-painter relies on an exact order for `wangid` values when generating Mixed Wang Sets.

```python
# ❌ Shifted by 1
wangid = f"{nw},{n},{ne},{e},{se},{s},{sw},{w}"

# ✅ Exact Tiled Order
wangid = f"{n},{ne},{e},{se},{s},{sw},{w},{nw}"
```

**Anti-pattern:** Assuming a standard directional array (e.g., TopLeft first) for Tiled properties without checking the exact API order.
**Evidence:** Terrain painter failed (left checkerboard gaps) because bitmasks shifted by 1 index didn't map to valid tiles. Reordering to `Top, TopRight, Right, BottomRight, Bottom, BottomLeft, Left, TopLeft` fixed it perfectly.

---

### L-MAP-003 · 2026-05-13 · U · Minor Rework
**Visual artifact debugging (transparent tiles vs missing IDs)**

When an auto-generated tile appears as a flat, dark grey block in Tiled, it's easy to assume Tiled rejected the tile and placed a fallback background. 

**Anti-pattern:** Spending time debugging TSX Wang ID mappings when an autotile has a visual artifact in Tiled.
**Rule:** Check the output PNG for transparency first. Tiled's default map background is a dark grey grid. If a crop coordinate is wrong and extracts a transparent section, it looks identical to Tiled "missing" the tile. 
**Evidence:** A script was cropping `(2,0)` instead of `(4,0)` for an RPG Maker XP inner corner, producing a fully transparent 32x32 tile. Tiled successfully placed the tile, but it was invisible.

---

### L-MAP-004 · 2026-05-13 · U · Perfect
**Cache Evasion for Dynamic Tile Overlays**

When introducing dynamic visual elements (like animated autotiles) into a heavily cached static system (tilemaps), attempting to rebuild or invalidate the global static cache kills performance.

```python
# ❌ Draw animated tiles into the global static layer cache
# Requires invalidating and rebuilding the entire 3200x3200 surface every 150ms.
def get_layer_surface(self): ...

# ✅ Explicitly skip dynamic elements during static bake, leaving a transparent hole
if tile.frames is not None:
    continue # Skip animated tiles
    
# Then yield dynamic tiles in a separate pass for RenderManager
for tile in get_visible_animated_chunks():
    screen.blit(anim_manager.get_current_frame(tile.id), pos)
```

**Rule:** Always decouple dynamic elements from static pre-render pipelines by applying "Cache Evasion" — explicitly skip rendering the dynamic element into the cache, and composite it dynamically on top of the static cache during the render loop.
**Evidence:** Animated autotiles integrated flawlessly into the Tiled parser while maintaining constant 60 FPS without invalidating the static layer cache.
