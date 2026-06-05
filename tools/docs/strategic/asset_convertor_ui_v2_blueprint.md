# Strategic Blueprint — Asset Convertor GUI v2: Dual-Toolbar + Recolor

> **Date:** 2026-06-05
> **Status:** STRATEGY
> **Scope:** GUI refactor of `tools/src/asset_convertor/` + A3/A4 converters + Recolor mode
> **Research:** [UI Redesign Research](../research/asset_convertor_ui_redesign.md)

---

## 1. What exact problem are you solving?

**Persona:** Solo game developer converting RPG Maker MV/MZ/XP tilesets into Tiled-compatible formats.

**Current pain:**
1. The current GUI is a single horizontal toolbar that mixes type-selection, format-selection, and animation options in one cramped row — adding A3/A4 converters and Recolor would make it unworkable.
2. Only A2 (Ground) and A1 (Animated) converters exist. A3 (Building/Roof) and A4 (Wall) are missing.
3. No way to recolor any game asset (tiles, sprites, props) directly in the tool.
4. Export options (PNG vs PNG+TSX) are not selectable — always exports both.

**Measurable outcome:**
- Developer selects asset type in one click, sees only the relevant options (no noise from unrelated modes).
- A3 and A4 conversions work correctly per `Tilemap.WALL_AUTOTILE_TABLE` from rpgtkoolmv/corescript.
- Recolor mode accepts any PNG (autotile, sprite, prop, tileset) and remaps its color palette interactively.
- Export target (PNG only or PNG + TSX) is selectable per conversion.

---

## 2. Success Metrics

| Metric | Target | Timeline |
|--------|--------|----------|
| Type selection | 1-click switch between A1/A2/A3/A4/Recolor, no modal or wizard | V2.0 |
| Contextual options | Secondary toolbar shows 0 irrelevant controls for the selected mode | V2.0 |
| A3 conversion | Correctly produces 16-shape tileset from `WALL_AUTOTILE_TABLE` | V2.0 |
| A4 conversion | Correctly handles hybrid FLOOR+WALL table logic (ty%2) | V2.0 |
| Recolor palette extraction | Auto-detects all unique colors from loaded PNG in < 1s | V2.0 |
| Recolor preview | Live preview updates within < 500ms of any color remap change | V2.0 |
| Lospec presets | ≥ 6 embedded palettes (Endesga 32, Resurrection 64, Dawnbringer 32, GameBoy, Autumn, Winter) | V2.0 |
| Export choice | User can independently toggle PNG and TSX output per session | V2.0 |
| Test coverage | ≥ 80% on new converter logic (A3, A4, recolor engine) | V2.0 |
| Regression | All existing A1 and A2 conversions produce identical output | V2.0 |

---

## 3. Why will we win?

**Structural advantage:** The existing converter core (`converter_mv.py`) is a well-tested pure function pipeline — `convert_mv()` → PIL Image. The GUI is a thin layer that calls these functions. Adding A3/A4 and Recolor follows the same pattern: new converter modules, new GUI mode, no engine rewrite.

**Corescript-sourced truth:** A3/A4 autotile tables are read directly from the official `rpgtkoolmv/corescript` repo (`Tilemap.WALL_AUTOTILE_TABLE`, `Tilemap.FLOOR_AUTOTILE_TABLE`). No reverse-engineering needed.

**Progressive disclosure pattern:** The dual-toolbar architecture (primary = type, secondary = contextual options) means every future mode (Recolor, A5 import, batch processing) can be added as a new primary button with its own secondary toolbar — no layout changes required.

---

## 4. Architecture Decisions

### ADR-UI-001: Dual-Toolbar Layout (ADOPTED)

**Decision:** Replace the current single horizontal toolbar with:
- **Toolbar 1 (Primary):** `[Ouvrir]` | `[Ground A2]` `[Bâtiment A3]` `[Mur A4]` `[Animé A1]` `[Recolor]` | `[Convertir/Appliquer]`
- **Toolbar 2 (Secondary):** Contextual frame that swaps content based on the selected type button.

**Trade-offs:**

| Option | Pro | Con |
|--------|-----|-----|
| **A. Dual Toolbar** ✅ | Zero wasted space. Each mode shows only its controls. Scales to N future modes. | Toolbar 2 must animate/swap cleanly — small implementation complexity. |
| B. Left sidebar | More vertical space for options | Reduces the 3-panel preview width significantly. Preview quality suffers. |
| C. Single toolbar (current) | Simple | Already broken at A2. Would be unusable with 5 modes. |

**Rationale:** Option A. The 3 preview panels are the most valuable part of the UI — they must stay full-width. The contextual secondary toolbar achieves this.

---

### ADR-UI-002: Mode = Primary Axis, Format = Secondary (ADOPTED)

**Decision:** The user selects **mode first** (what kind of operation: A2 Ground, A3 Building, A4 Wall, A1 Animated, Recolor), then **format** (MV/MZ/XP) appears as a secondary option **only when relevant**.

- A2, A3, A4, A1 → format selector (MV/MZ/XP) in Toolbar 2.
- Recolor → no format selector (format-agnostic operation).

**Rationale:** Confirmed by user preference from DISCOVER session. Format is an output concern, not an identity concern.

---

### ADR-UI-003: Autotile Tables from Official Corescript (VERIFIED)

**Decision:** A3 and A4 conversion logic uses `WALL_AUTOTILE_TABLE` and `FLOOR_AUTOTILE_TABLE` as defined in [`rpgtkoolmv/corescript/js/rpg_core/Tilemap.js`](https://github.com/rpgtkoolmv/corescript/blob/master/js/rpg_core/Tilemap.js).

**Key verified facts from the source:**
- `WALL_AUTOTILE_TABLE` = 16 entries (shapes 0–15). Used for: A3 roof tiles + A4 wall-side tiles.
- `FLOOR_AUTOTILE_TABLE` = 47 entries (shapes 0–46). Used for: A2 ground + A4 wall-top tiles.
- A4 is **hybrid**: `ty % 2 === 1` → `WALL_AUTOTILE_TABLE` (wall sides), else → `FLOOR_AUTOTILE_TABLE` (wall tops).
- A3 always → `WALL_AUTOTILE_TABLE`.
- Tile IDs: A1=2048, A2=2816, A3=4352, A4=5888, MAX=8192.

---

### ADR-UI-004: Recolor Engine — Palette-First (ADOPTED)

**Decision:** Recolor mode operates on the extracted color palette of the loaded PNG, not on individual pixels. The remapping table is (source_color → target_color) where source colors are the unique colors detected in the image.

**Workflow:**
1. Load PNG → extract unique colors (≤ 256, configurable tolerance for near-duplicate merging).
2. Display extracted colors as "PALETTE DE L'ASSET".
3. User selects a Lospec preset → auto-proposes nearest-color mapping per source color.
4. User can override any row manually (click target swatch → system color picker or hex input).
5. Apply = remap all pixels matching each source color to its paired target color.

**Why palette-first, not hue-shift?**
- RPG Maker assets use indexed-like palettes (limited unique colors per tileset block).
- Palette remapping is exact and reversible. Hue shift creates artifacts on pixels that straddle hue boundaries.
- The user asked explicitly for "each element can be changed manually" — this requires per-color control.

---

### ADR-UI-005: Export Options — Independent Checkboxes (ADOPTED)

**Decision:** Two independent checkboxes in the footer or aperçu panel:
- `☑ PNG` — always enabled, cannot be unchecked (the source of truth).
- `☑ TSX` — enabled by default for A1/A2/A3/A4 modes (tileset-producing). **Automatically disabled and unchecked** for Recolor mode (recolored arbitrary PNGs are not Tiled tilesets).

**Rationale:** TSX export is only meaningful when the output is a structured Tiled tileset. A recolored tree sprite is not a tileset. Prevent user error by auto-toggling based on mode.

---

## 5. Feature List

Ordered by implementation dependency:

| # | Feature | Mode | Priority |
|---|---------|------|----------|
| F1 | **Dual-toolbar layout** — primary type selector + contextual secondary frame | All | 🔴 Required |
| F2 | **AppState refactor** — decouple `resource_type` from `format`; add `recolor` mode | All | 🔴 Required |
| F3 | **A3 converter** — `converter_mv_a3.py`: `WALL_AUTOTILE_TABLE`, 16 shapes, 192×96 source | A3 | 🔴 Required |
| F4 | **A4 converter** — `converter_mv_a4.py`: hybrid FLOOR+WALL logic, 192×144 source | A4 | 🔴 Required |
| F5 | **Recolor engine** — `core/recolor.py`: palette extraction + color remapping + tolerance | Recolor | 🔴 Required |
| F6 | **Lospec palette bundle** — 6 embedded palettes (Endesga 32, Resurrection 64, Dawnbringer 32, GameBoy, Autumn, Winter) as Python dicts | Recolor | 🔴 Required |
| F7 | **Recolor UI panel** — palette-of-asset display, preset grid, remapping table with color picker | Recolor | 🔴 Required |
| F8 | **Export checkboxes** — independent PNG/TSX toggles; TSX auto-disabled in Recolor mode | All | 🔴 Required |
| F9 | **Secondary toolbar — A1 context** — format selector + animation type + speed | A1 | 🔴 Required |
| F10 | **Secondary toolbar — A2 context** — format selector + animation checkbox (disabled) | A2 | 🔴 Required |
| F11 | **Secondary toolbar — A3 context** — format selector + expected dimensions hint | A3 | 🔴 Required |
| F12 | **Secondary toolbar — A4 context** — format selector + hybrid mode indicator | A4 | 🔴 Required |
| F13 | **macOS menu bar** — File > Ouvrir, Affichage > Journal on/off | All | 🟡 Should-have |
| F14 | **Recolor preview auto-update** — live aperçu updates on any remap change | Recolor | 🔴 Required |
| F15 | **Nearest-color auto-mapping** — when preset selected, auto-propose mapping per source color | Recolor | 🟡 Should-have |

---

## 6. What are we NOT building?

| Excluded | Rationale |
|----------|-----------|
| **Batch mode** (multiple files) | Out of scope. User extracts one block at a time (stated preference). CLI handles batch if needed. |
| **Undo/redo stack** | YAGNI. Change a slider/color back manually. |
| **Custom palette save to disk** | User manages palettes outside the tool. Lospec presets are embedded. |
| **Animated preview in Recolor mode** | A1 animation preview stays in A1 mode only. |
| **XP format for A3/A4** | RPG Maker XP has different autotile logic (5-part autotile). Out of scope for V2. |
| **A5 import** | A5 is a standard tileset (no autotile). Simple crop/TSX export — future scope. |
| **Recolor TSX export** | A recolored arbitrary PNG is not a Tiled tileset. No TSX for Recolor. |
| **Drag & drop batch queue** | One asset at a time. YAGNI. |
| **Plugin system** | Single-purpose tool. |

---

## 7. Risk Assessment

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| **A4 hybrid logic complexity** — ty%2 switching between FLOOR and WALL tables mid-source-file | High | Medium | Unit-test each A4 row independently against expected tile positions verified from engine source. |
| **Recolor palette extraction quality** — too many "unique" colors if tolerance too low (gradients, anti-aliasing) | Medium | High | Default tolerance = 5 (ΔE), user-adjustable. Merge near-duplicate colors. Show count in UI. |
| **CustomTkinter color picker** — CTk has no native color picker; must use `colorchooser.askcolor()` or implement our own | Medium | High | Use `tkinter.colorchooser.askcolor()` for the initial version. It's native macOS. |
| **WALL_AUTOTILE_TABLE coordinate system** — mini-tile coordinates are in 24px units (half-tile), not 48px | High | Low | Verified directly from corescript. Our existing `converter_mv.py` already uses this system for A2. |
| **Regression on A1/A2** — GUI refactor might break existing convert paths | Medium | Low | Run existing test suite before and after refactor. No logic changes in A1/A2 core functions. |

---

## 8. Assumptions

| # | Assumption | Risk | Status |
|---|-----------|------|--------|
| A1 | CustomTkinter `CTkSegmentedButton` can replace the current toolbar layout | Low | ASSUMED — CTk docs confirm segmented buttons exist |
| A2 | `WALL_AUTOTILE_TABLE` has exactly 16 entries and applies to A3 roof + A4 wall-sides | Low | **VERIFIED** — read directly from corescript blob SHA `9ff2991` |
| A3 | A4 source file is 768×720 px (MV full sheet). Wall-TOP blocks (even ty, FLOOR table 47 shapes) and wall-SIDE blocks (odd ty, WALL table 16 shapes) are **interleaved by row** in the same source file. | Medium | **VERIFIED** — confirmed visually against a real MV A4 file: even rows = shrub/rock tops viewed from above; odd rows = arch/window facades. Matches corescript `ty % 2` formula exactly. |
| A4 | `tkinter.colorchooser.askcolor()` returns an (R,G,B) tuple usable directly with PIL | Low | ASSUMED — standard library, well-documented |
| A5 | Lospec palette data (6 palettes) can be embedded as static Python dicts without license issues | Low | VERIFIED — Lospec palettes are public domain / CC0 |
| A6 | The Recolor engine does not need to handle indexed PNGs (mode 'P') — all RPG Maker assets are RGBA | Medium | ASSUMED — needs validation with a real RPG Maker asset export |

---

## Next Step

→ Proceed to **📋 SPEC** stage. Module specs needed:
1. `gui/app.py` — Dual-toolbar layout refactor
2. `gui/state.py` — AppState refactor (resource_type + format decoupled)
3. `core/converter_mv_a3.py` — A3 Building converter
4. `core/converter_mv_a4.py` — A4 Wall converter (hybrid)
5. `core/recolor.py` — Palette extraction + color remapping engine
6. `core/palettes.py` — Lospec palette bundle (6 presets)
7. `gui/recolor_panel.py` — Recolor UI panel (palette display + remapping table)
