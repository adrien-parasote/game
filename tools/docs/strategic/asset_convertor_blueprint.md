# Strategic Blueprint — Asset Convertor V3: Interactive UI

> **Date:** 2026-05-31
> **Status:** IMPLEMENTED
> **Research:** [Python GUI Frameworks](../research/python_gui_frameworks.md) — Decision: ADOPT Dear PyGui

---

## 1. What exact problem are you solving?

**Persona:** Solo game developer building a top-down 2D RPG with procedural tileset generation.

**Current pain:** The CLI-based workflow requires:
1. Editing YAML files by hand to tweak texture parameters
2. Running `python -m tools.asset_convertor generate --terrain grass --quality v2 --preview` to see results
3. Closing Pygame, editing YAML again, re-running the command
4. No way to compare parameters side-by-side or iterate quickly

**Measurable outcome:** A developer can adjust any texture parameter (scale, octaves, persistence, detail type, etc.) via sliders/dropdowns and see a **single tile preview + minimap** update **in < 1 second**, without leaving the application. The complete workflow — from parameter tweaking to PNG + TSX export — happens entirely within the GUI.

---

## 2. What are your success metrics?

| Metric | Target | Timeline |
|--------|--------|----------|
| Iteration speed | < 1s from parameter change to tile + minimap preview update | V3.0 |
| Parameter coverage | 100% of `TextureParams` + `DetailConfig` + `EdgeConfig` exposed as widgets | V3.0 |
| Complete workflow | Full pipeline in GUI: preset select → tweak params → preview tile + minimap → export PNG + TSX | V3.0 |
| Export workflow | 1-click PNG + TSX export with output path selection | V3.0 |
| Terrain switching | Instant preset switching via dropdown | V3.0 |
| CLI preservation | CLI still works independently (no regression) | V3.0 |
| Test coverage | ≥ 80% on new GUI-adjacent code (state management, callbacks) | V3.0 |

---

## 3. Why will you win?

**Structural advantage:** The V1/V2 generation pipeline is already modular and well-tested (263 tests). The pipeline takes frozen dataclass configs → produces PIL Images. The GUI is a thin interactive layer on top of the same pipeline — no engine rewrite needed.

**Framework fit:** Dear PyGui's raw texture API (PIL → numpy → GPU) eliminates the image conversion bottleneck that plagues other frameworks (Flet=base64, CustomTkinter=CTkImage GC). The 32×32 tiles are tiny — regeneration is fast.

**Existing pipeline is pure functions:** `generate_noise_texture_v2()`, `apply_detail_overlay()`, `generate_subtiles()`, `assemble_tileset()` are all stateless. The UI just calls them with new parameters each time.

---

## 4. What's the core architecture decision?

### ADR-001: GUI replaces Pygame preview, CLI preserved

**Decision:** The Dear PyGui GUI **replaces** `preview/pygame_preview.py` as the interactive visualization tool. The CLI (`cli.py`) is preserved for scripted/automated workflows.

**Trade-off analysis:**

| Option | Pro | Con |
|--------|-----|-----|
| **A. Replace Pygame, keep CLI** ✅ | Clean separation: UI for interactive use, CLI for automation. No breaking change. | Two entry points to maintain. |
| B. Replace both CLI + Pygame | Single entry point. | Breaks scripted workflows. Regression risk on automation. |
| C. Embed CLI in GUI only | Users can still type commands. | UX anti-pattern — defeats the purpose of a GUI. |

**Rationale:** Option A. The CLI is used in automation (e.g., batch generation). The GUI is for interactive design. They share the same core pipeline.

### ADR-002: Thin GUI wrapper pattern

**Decision:** The GUI does NOT contain generation logic. It builds `TextureParams`, `DetailConfig`, `EdgeConfig` dataclasses from widget state and calls existing pipeline functions. All generation logic stays in `core/`.

**Rationale:** This keeps the core testable without GUI dependencies. The GUI module depends on core, never the reverse.

### ADR-003: Minimap logic extraction

**Decision:** Extract minimap rendering logic (`_compute_bitmask_for_cell`, `_find_closest_bitmask_index`, `_generate_minimap_grid`) from `preview/pygame_preview.py` into a shared `core/minimap.py` module. Both the Dear PyGui UI and the Pygame preview (if kept as legacy) can use it.

**Rationale:** The minimap is pure computation — bitmask → tile index mapping. It should not be locked inside a rendering framework.

---

## 5. What's the tech stack rationale?

| Choice | Rationale |
|--------|-----------|
| **Dear PyGui 2.3** | GPU-accelerated raw texture API. Perfect for real-time PIL preview. 2 MB, MIT, macOS ARM native. See [research](../research/python_gui_frameworks.md). |
| **numpy** | Required for Dear PyGui raw texture pipeline (PIL → float32 array). Already used by subtile.py. |
| **Existing stack preserved** | Pillow, opensimplex, PyYAML — no changes. |
| **Pygame-CE** | Demoted from hard dependency to optional (CLI `--preview` flag). GUI replaces it for interactive use. |

---

## 6. What are the features?

Ordered by implementation dependency:

| # | Feature | Dependencies | Priority |
|---|---------|-------------|----------|
| F1 | **Bitmask engine extraction** — extract `compute_bitmask`, `find_closest_bitmask_index` from `pygame_preview.py` into `core/minimap.py` | None (refactor) | 🔴 Required |
| F2 | **GUI window + layout** | Dear PyGui install | 🔴 Required |
| F3 | **Terrain preset selector** | F2 | 🔴 Required |
| F4 | **Texture parameter sliders** | F2, F3 | 🔴 Required |
| F5 | **Single tile preview** (base texture, 4× zoomed) | F2, F4 (raw texture API) | 🔴 Required |
| F6 | **Paint canvas** — interactive grid, two modes (see below) | F1, F5 | 🔴 Required |
| F6a | ↳ **Autotile mode** — click/drag paints terrain on/off, bitmasks auto-computed, correct Wang tile displayed per cell | F1, F6 | 🔴 Required |
| F6b | ↳ **Standalone mode** — tile palette (47 tiles), click canvas to place selected tile freely | F6 | 🔴 Required |
| F6c | ↳ **Canvas tools** — paint (LMB), erase (RMB), clear all | F6 | 🔴 Required |
| F7 | **Detail overlay controls** | F4 | 🔴 Required |
| F8 | **Edge style controls** | F4 | 🔴 Required |
| F9 | **Seed control** (input + randomize) | F4 | 🔴 Required |
| F10 | **Quality toggle** (V1/V2) | F4 | 🔴 Required |
| F11 | **Output path selection** (file dialog) | F2 | 🔴 Required |
| F12 | **Export button** (PNG + TSX) | F5, F11 | 🔴 Required |
| F13 | **Palette color preview** | F3 | 🟢 Nice-to-have |

### Paint Canvas — Detailed Description

**Autotile mode** (like Tiled's terrain brush):
- Canvas = N×M grid of 32×32 cells (default 16×12)
- Left click / drag = mark cell as "terrain" (filled)
- Right click / drag = erase cell (empty)
- On each change, recalculate 8-direction bitmask for affected cells + neighbors
- Display the correct Wang blob tile (from the 47-tile set) for each filled cell
- Empty cells show a neutral background (checkerboard or transparent)

**Standalone mode** (like Tiled's stamp brush):
- Tile palette panel shows all 47 tiles from current tileset
- Click a tile to select it
- Click canvas cell to place the selected tile
- Right click = erase
- No bitmask computation — free placement

**Canvas interactions:**
- Mode toggle: radio button or tab switch
- Clear button: reset entire canvas
- Canvas auto-updates when texture parameters change (regenerates all placed tiles)

### UI Layout (conceptual)

```
┌──────────────────────────────────────────────────────────────────┐
│  Asset Convertor V3                                       [—][×] │
├───────────────────┬──────────────────────────────────────────────┤
│ ▾ Terrain Preset  │                                              │
│ ┌───────────────┐ │  ┌──────────┐                                │
│ │ grass       ▾ │ │  │  32×32   │  TILE PREVIEW (4× zoom)        │
│ └───────────────┘ │  │  → 128px │                                │
│                   │  └──────────┘                                │
│ ▾ Quality         │                                              │
│ ○ V1  ● V2        │  ┌─ Paint Canvas ────────────────────────┐   │
│                   │  │  Mode: ● Autotile  ○ Standalone       │   │
│ ▾ Texture         │  │  ┌──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┐  │   │
│ scale     ═══●═══ │  │  │  │▓▓│▓▓│▓▓│  │  │▓▓│▓▓│  │  │  │  │   │
│ octaves   ═══●═══ │  │  ├──┼──┼──┼──┼──┼──┼──┼──┼──┼──┼──┤  │   │
│ persist   ═══●═══ │  │  │  │▓▓│▓▓│▓▓│▓▓│  │▓▓│▓▓│▓▓│  │  │  │   │
│ lacunar   ═══●═══ │  │  ├──┼──┼──┼──┼──┼──┼──┼──┼──┼──┼──┤  │   │
│ detail_s  ═══●═══ │  │  │  │  │▓▓│▓▓│▓▓│▓▓│▓▓│▓▓│  │  │  │  │   │
│ detail_str═══●═══ │  │  ├──┼──┼──┼──┼──┼──┼──┼──┼──┼──┼──┤  │   │
│ ☑ dithering       │  │  │  │  │  │▓▓│▓▓│▓▓│▓▓│  │  │  │  │  │   │
│ ☑ smooth ramp     │  │  ├──┼──┼──┼──┼──┼──┼──┼──┼──┼──┼──┤  │   │
│                   │  │  │  │  │  │  │▓▓│▓▓│  │  │  │  │  │  │   │
│ ▾ Detail Overlay  │  │  └──┴──┴──┴──┴──┴──┴──┴──┴──┴──┴──┘  │   │
│ ┌───────────────┐ │  │  LMB=paint  RMB=erase  [Clear]        │   │
│ │grass_blades ▾ │ │  └───────────────────────────────────────┘   │
│ └───────────────┘ │                                              │
│ density   ═══●═══ │  ┌───────────┐ ┌──────────────────┐          │
│ max_height═══●═══ │  │ Regenerate│ │ Export PNG + TSX │          │
│                   │  └───────────┘ └──────────────────┘          │
│ ▾ Edge Style      │                                              │
│ ┌───────────────┐ │  Seed: [42______] [🎲 Random]                │
│ │ organic    ▾  │ │  Output: [assets/images/autotiles] [📂]      │
│ └───────────────┘ │  Name:  [grass_______________]               │
│ width     ═══●═══ │                                              │
│ noise_sc  ═══●═══ │                                              │
└───────────────────┴──────────────────────────────────────────────┘
```

**▓▓ = terrain peint (autotile mode)** — chaque cellule affiche la tile Wang correspondante à son bitmask.
**En standalone mode**, les ▓▓ sont remplacés par la tile sélectionnée dans la palette.

---

## 7. What are you NOT building?

| Excluded | Rationale |
|----------|-----------|
| **Palette editor** (add/remove/reorder colors) | Palettes are managed via YAML files. Out of scope for V3. |
| **Preset YAML editor** in GUI | Use a text editor. GUI reads presets, doesn't write them. |
| **Undo/redo stack** | Overkill for a parameter-tweaking tool. Just change the slider back. |
| **Multi-terrain view** | One terrain at a time. Batch generation stays in CLI. |
| **Animated water preview** | V2 spec notes "V1 = static water only". Not V3 scope. |
| **Custom palette creation** from GUI | Palette YAML is the source of truth. |
| **Plugin system** | Single-purpose tool. YAGNI. |
| **Docking panels / window management** | One fixed layout. Not a full IDE. |

---

## Assumptions

| # | Assumption | Risk | Status |
|---|-----------|------|--------|
| A1 | Dear PyGui 2.3.1 works on Python 3.13 macOS ARM | Low | VERIFIED — `pip install --dry-run` successful, wheel exists |
| A2 | 32×32 tile regeneration is fast enough for slider callbacks (< 200ms) | Low | ASSUMED — single tile gen is ~10ms based on V2 tests. Full tileset (47 tiles) may be ~500ms. |
| A3 | Dear PyGui raw texture API supports RGBA float32 | Low | CITED — [Dear PyGui docs](https://dearpygui.readthedocs.io/en/latest/documentation/textures.html) |
| A4 | numpy is the only new dependency needed | Low | VERIFIED — Dear PyGui has no transitive deps besides numpy |
| A5 | Bitmask engine extraction is non-breaking | Low | ASSUMED — pure computation, no Pygame dependency in the logic itself |
| A6 | Dear PyGui mouse input events (click, drag) work for canvas painting | Low | CITED — [Dear PyGui input handling docs](https://dearpygui.readthedocs.io/en/latest/documentation/input-polling.html) |
| A7 | Canvas with 16×12 = 192 raw textures performs well in Dear PyGui | Medium | ASSUMED — each is 32×32 = tiny. But 192 texture updates on param change could be heavy. |

---

## Gap Discovery

| # | Gap | Impact if unresolved | Owner |
|---|-----|---------------------|-------|
| 1 | **Full tileset regeneration time** — 47 tiles × subtile generation + assembly. Is it < 1s for real-time preview, or do we need debounce/async? | If > 1s, slider interaction feels laggy. Need debounce or background generation. | Research (benchmark) |
| 2 | **Dear PyGui image scaling** — tiles are 32×32 but need to display larger (e.g., 4x zoom = 128×128). Does raw texture support scaling, or do we resize PIL images before feeding? | Blurry or pixelated preview if scaling is wrong. Pixel art needs nearest-neighbor, not bilinear. | Research (DPG docs) |
| 3 | **Canvas click detection** — Dear PyGui's `add_image` + mouse position polling for a grid of textures. Do we use a drawlist, image buttons, or manual hit-testing? | Wrong approach = broken click/drag painting. | Research (DPG docs) |
| 4 | **Canvas performance on param change** — when a slider changes, all 192 canvas cells need their tiles regenerated + textures updated. Is this fast enough? | If too slow, need lazy update (only repaint visible/filled cells). | Research (benchmark) |

---

## Resolved Gaps (user decisions)

| # | Gap | Decision |
|---|-----|----------|
| R1 | Preset modification workflow | **Changes lost on preset switch.** Presets are read-only. No save-to-YAML from GUI. |
| R2 | Pygame-CE dependency fate | **Keep as optional** for CLI `--preview`. GUI replaces it for interactive use. |

---

## Next Step

→ Once gaps are resolved, proceed to **📋 SPEC** stage with module-level specs for:
1. `core/minimap.py` — extracted bitmask engine (compute_bitmask, find_closest_index)
2. `gui/app.py` — Dear PyGui application + layout
3. `gui/canvas.py` — paint canvas (autotile + standalone modes)
4. `gui/state.py` — UI state management (dataclass → widget binding)
5. `gui/preview.py` — PIL → raw texture pipeline
