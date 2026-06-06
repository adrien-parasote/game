# Strategic Blueprint — Map Lighting Modes

> Status: STRATEGY complete  
> Feature: `lighting_mode` map property support  
> Scope: game engine (sub-project `/game/game/`)

---

## What We're Building

Support for per-map lighting behavior controlled by a Tiled map property.
Three modes drive how the darkness overlay alpha is computed each frame.

---

## 1. Success Metrics

| Metric | Target |
|--------|--------|
| Underground maps immune to day/night cycle | `night_alpha` = `ambient_dark_alpha` (fixed) at all in-game hours |
| Indoor maps have attenuated day/night effect | Overlay alpha capped at `MAX_NIGHT_ALPHA * INDOOR_ATTENUATION` |
| Outdoor maps unchanged | Zero regression — identical behaviour to today |
| Torches/lights still work on all modes | Radial punch-through logic untouched |
| No per-frame allocation added | Alpha computation stays O(1), no new Surface allocation |
| Implementation < 1 sprint (1 dev-day) | Trivial code path switch |

---

## 2. Tiled Map Properties — Schema (decided, locked)

Properties are defined at **map root level** in `.tmj` files (already extracted by `TmjParser` into `map_result["properties"]`).

| Property | Type | Values | Default | Semantics |
|----------|------|--------|---------|-----------|
| `lighting_mode` | enum (string) | `outdoor` · `indoor` · `underground` | `outdoor` | Controls how darkness overlay alpha is computed |
| `ambient_dark_alpha` | int | 0–255 | `0` | Used only in `underground` mode: fixed overlay alpha |
| `bgm` | string | filename | — | Existing; unchanged |
| `name` | string | display name | — | Existing; unchanged |

### Mode Semantics

| Mode | Overlay Alpha Source | Day/Night Cycle | Season Effect | Window Beams |
|------|---------------------|----------------|---------------|--------------|
| `outdoor` | `time_system.night_alpha` (0→180) | **YES** | (via brightness) | YES |
| `indoor` | `min(255, ambient_dark_alpha + int(night_alpha × INDOOR_ATTENUATION))` | **attenuated** | attenuated | YES |
| `underground` | `ambient_dark_alpha` (fixed, from Tiled) | **NO** | **NO** | NO (no sky) |

> **`indoor` — Option B (LOCKED):**
> `ambient_dark_alpha` = plancher d'obscurité permanente (jour).
> La nuit s'ajoute par-dessus, filtrée par `INDOOR_ATTENUATION = 0.35`.
> `ambient_dark_alpha = 0` → comportement dégradé identique à une pure atténuation.
> Valeur conseillée pour une pièce standard : 30–60.

> **`underground` — no sky source:**
> Window beams désactivés (pas de ciel). Torches seules percent l'overlay.
> `ambient_dark_alpha = 0` → map pleinement éclairée (designer fixe consciemment).
> Valeur conseillée pour une cave sombre : 180–220.

---

## 3. Constraint Mapping

| Dimension | Constraint |
|-----------|-----------|
| **Performance** | No new Surface allocation per frame. Alpha value computed as a single integer expression. |
| **Backward compatibility** | Maps with no `lighting_mode` property → fallback to `outdoor`. Zero breaking changes. |
| **Tiled integration** | Properties already defined in Tiled project via custom class. Engine reads them from existing `map_result["properties"]` dict. |
| **TimeSystem** | Must NOT be modified. Time continues advancing on underground maps (saves, HUD, season logic all depend on it). Only the *lighting consumer* changes. |
| **Torch system** | `LightingManager.create_overlay()` torch punch-through logic: untouched. Works on all modes. |
| **Window beams** | Skipped when `lighting_mode == "underground"` (no sky → no window beams make sense). |

---

## 4. Architecture Direction

**Single point of truth: `game._map_lighting_mode` + `game._map_ambient_dark_alpha`**

Set at map load time by `MapLoader`. Read at render time by `RenderManager`.
No changes to `TimeSystem`, `LightingManager`, or `TmjParser`.

```
MapLoader.load()
  → reads map_result["properties"]["lighting_mode"]
  → stores game._map_lighting_mode   (str, default "outdoor")
  → stores game._map_ambient_dark_alpha  (int, default 0)

RenderManager.draw_scene()
  → computes effective_night_alpha from _map_lighting_mode
  → passes to _render_lighting_and_effects()
```

**ADR-LIGHT-001:** Alpha override lives in `RenderManager`, not in `TimeSystem`.
Rationale: `TimeSystem` is a pure clock — it must not know about map topology.
Overriding at the render level keeps all lighting concerns co-located.

---

## 5. Exclusions & Boundaries

| OUT of scope | Reason |
|-------------|--------|
| Per-zone lighting within a single map | Future feature; `ambient_dark_alpha` is map-level only |
| Animated alpha transition on map entry (fade-in to underground darkness) | Follow-up; scope creep for this iteration |
| Seasonal color tinting underground | Out — underground has no sky, seasons don't apply |
| Modifying `TimeSystem` to freeze time | Wrong layer — time must keep advancing |
| New `LightingManager` subclass per mode | Over-engineering; a 3-branch switch in `RenderManager` suffices |

---

## 6. Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Map without `lighting_mode` breaks | Low | High | Default `"outdoor"` → identical current behaviour |
| `ambient_dark_alpha = 0` on underground map → fully bright | Known, intended | None | Designer must set the value consciously; documented |
| Window beams visible underground (sky source absent) | Medium | Medium | Skip `draw_additive_window_beams` when mode == "underground" |
| Torches not visible (overlay too dark, alpha not subtracted) | Low | Medium | Torch logic in `create_overlay` uses BLEND_RGBA_SUB — unchanged, works at any alpha |

---

## Assumption Audit (Behavior #2)

| Assumption | Status | Risk | Evidence |
|-----------|--------|------|----------|
| `map_result["properties"]` is always a dict (never None) | VERIFIED | — | `tmj_parser.py:59` — `{p["name"]: p["value"] for p in data.get("properties", [])}` |
| `TmjParser` already extracts map-level properties | VERIFIED | — | `map_result["properties"]` consumed for `bgm` in `map_loader.py:66` |
| `game._map_lighting_mode` attribute doesn't yet exist | ASSUMED | Low | Not found in `grep` over `game.py`; added at `MapLoader.load()` |
| `lighting_mode` Tiled enum serialises as a plain string in JSON | ASSUMED | Low | Standard Tiled enum-property → JSON `"type":"string"`, `"value":"outdoor"` |
| Indoor ATTENUATION constant = 0.4 is visually correct | ASSUMED | Low | Tunable constant in `lighting_constants.py` — designer adjusts |
