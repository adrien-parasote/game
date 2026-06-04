# Strategic Blueprint — Autotile Converter: RPG Maker → Tiled

> **Date:** 2026-06-04
> **Status:** STRATEGY — pending SPEC approval
> **Research:** [autotile-converter.md](../research/autotile-converter.md)
> **Replaces:** `autotile-pipeline-strategy.md` (obsolete — 16-tile Edge set, no GUI)

---

## 1. What exact problem are you solving?

**Persona:** Solo game developer with existing RPG Maker XP / MV / MZ asset libraries.

**Current pain:** Autotile assets from RPG Maker cannot be used directly in Tiled. The RPG Maker format uses a proprietary packed sub-tile layout that requires engine-side reassembly. Tiled expects either manually placed tiles or a **47-tile blob spritesheet** with a matching TSX terrain definition.

The developer must:
1. Manually slice and reassemble each autotile into 47 variants → error-prone, hours of work
2. Or discard the entire RPG Maker asset library and redraw from scratch

**Measurable outcome:**
- Drop a RPG Maker autotile PNG into the tool → get a Tiled-ready 47-tile PNG + TSX file in **< 5 seconds**
- Visual canvas confirms the conversion is correct before export
- Zero manual configuration required in Tiled after export

---

## 2. Success Metrics

| Metric | Target | Timeline |
|--------|--------|----------|
| Conversion correctness | All 47 blob tiles correctly assembled from input | V1.0 |
| Mode coverage | XP + MV + MZ inputs all produce valid output | V1.0 |
| Auto-detect tile size | Correctly identifies 32px vs 48px MV blocks | V1.0 |
| Export completeness | PNG + TSX generated in one click | V1.0 |
| Preview validation | Canvas draws 5×5 test pattern using output tiles | V1.0 |
| Speed | < 5s from file load to export ready | V1.0 |
| Tiled compatibility | TSX loads in Tiled 1.10+ without manual edits | V1.0 |
| Static only (no animated) | Animated frames ignored, not crashed | V1.0 |

---

## 3. Structural Advantage

The conversion from RPG Maker → Tiled blob is a **well-defined deterministic mapping**:
- The 47 blob tile configurations are fixed (cr31 specification)
- The RPG Maker sub-tile sampling positions are fixed (engine source lookup tables)
- No ML, no heuristics, no user judgment — just pixel cropping and compositing

We own the full pipeline: load input → extract sub-tiles → assemble 47 tiles → write PNG + TSX. No runtime dependency on RPG Maker or Tiled.

---

## 4. Core Architecture Decisions

### ADR-001: Transform asset_convertor, not a new tool

**Decision:** The existing `tools/src/asset_convertor/` GUI shell (customtkinter) is **replaced in-place**. The new autotile converter reuses the window/layout pattern but entirely replaces the generation logic.

**Rationale:**
- Avoids a second tool entry point
- Reuses existing project infrastructure (pyproject.toml, venv, tests)
- The old procedural tile generation is explicitly deprecated by the user ("on laisse tomber la génération de tiles")

**Trade-off:**

| Option | Pro | Con |
|--------|-----|-----|
| **Replace asset_convertor in-place ✅** | Single tool, no new entry point | Old generator code deleted (user approved) |
| New standalone tool | Zero overlap risk | Doubles tooling overhead |

---

### ADR-002: 47-tile Blob output (not 16-tile Edge)

**Decision:** Output format is the **47-tile Mixed Wang / Blob** tileset, not the older 16-tile Edge set.

**Rationale:**
- Blob handles both edges AND corners → no seam artifacts at diagonal transitions
- The RPG Maker autotile format natively encodes all 4 corner + 4 edge cases → maps cleanly to blob
- Tiled 1.5+ supports Mixed (blob) terrain sets natively
- The old strategy doc used 16-tile Edge — this was wrong for RPG Maker input which has inner corners

**TSX wangset type:** `type="mixed"` (not `type="edge"`)

---

### ADR-003: Mode selection drives the conversion logic

**Decision:** Three distinct converter modes — XP, MV, MZ — are selected by the user. No auto-detect of the *format type* (XP vs MV), but auto-detect of *tile size* within MV/MZ.

**Rationale:**
- XP (96×128) and MV (96×144 or 64×96) have different sub-tile layouts — wrong mode = broken output
- The user knows which RPG Maker they're converting from
- Auto-detecting XP vs MV from image dimensions is possible (96×128 ≠ 96×144 ≠ 64×96) but adds complexity that's unnecessary when the user can just select

**Auto-detect within MV/MZ:**
- `block_width == 64` → tile_size = 32 (community pack)
- `block_width == 96` → tile_size = 48 (official standard)

---

### ADR-004: GUI tech stack — stay on customtkinter

**Decision:** Keep **customtkinter** (already installed, already used in asset_convertor). Do NOT migrate to Dear PyGui.

**Rationale:**
- The asset_convertor V3 blueprint chose Dear PyGui for real-time texture performance (47 tiles × slider callbacks)
- The converter tool has NO sliders — it loads a file and shows a static preview
- customtkinter is sufficient for: file picker, mode selector, image display, export button
- The canvas for validation is a `tkinter.Canvas` widget (built-in, no new dep)

---

## 5. Tech Stack

| Component | Choice | Rationale |
|-----------|--------|-----------|
| GUI | **customtkinter** (existing) | No new dep, sufficient for file/mode/preview/export |
| Image processing | **Pillow** (existing) | Crop, paste, resize — all standard PIL ops |
| XML generation | **xml.etree.ElementTree** (stdlib) | TSX is simple XML, no lib needed |
| Canvas preview | **tkinter.Canvas** (stdlib) | Draw test pattern from output tiles |

---

## 6. Features

| # | Feature | Priority |
|---|---------|----------|
| F1 | **File picker** — load any PNG, validate format | 🔴 Required |
| F2 | **Mode selector** — XP / MV / MZ radio buttons | 🔴 Required |
| F3 | **Input preview** — display loaded source image | 🔴 Required |
| F4 | **Conversion engine** — XP lookup table, MV lookup table | 🔴 Required |
| F5 | **Output preview** — display generated 47-tile sheet | 🔴 Required |
| F6 | **Canvas validator** — 5×5 test pattern using output tiles | 🔴 Required |
| F7 | **Export** — save PNG + TSX to user-selected output dir | 🔴 Required |
| F8 | **Auto-detect MV tile size** — 32px vs 48px from block dims | 🔴 Required |

---

## 7. UI Layout

```
┌──────────────────────────────────────────────────────────────────┐
│  Autotile Converter — RPG Maker → Tiled              [—][□][×]  │
├─────────────────────────────────────────────────────────────────-┤
│  [📂 Open autotile file]    Mode: ○ XP  ● MV  ○ MZ              │
├───────────────────────┬─────────────────┬────────────────────────┤
│  SOURCE                │  TILED OUTPUT   │  CANVAS PREVIEW        │
│                        │                 │                        │
│  ┌──────────────────┐  │  ┌───────────┐  │  ┌──────────────────┐ │
│  │                  │  │  │ 47 tiles  │  │  │ 5×5 test pattern │ │
│  │  loaded PNG      │  │  │  8×6 grid │  │  │                  │ │
│  │  (original size) │  │  │           │  │  │  ▓▓▓▓▓▓▓         │ │
│  │                  │  │  └───────────┘  │  │ ▓▓▓▓▓▓▓▓▓        │ │
│  └──────────────────┘  │                 │  │  ▓▓▓▓▓▓▓         │ │
│                        │  tile_size: 32  │  │                  │ │
│  Format: MV/32px       │  output: 256×192│  └──────────────────┘ │
│                        │                 │                        │
├───────────────────────┴─────────────────┴────────────────────────┤
│  [Export PNG + TSX]    Output: [assets/images/autotiles/] [📂]   │
│  Status: Ready.                                                   │
└──────────────────────────────────────────────────────────────────┘
```

---

## 8. What are you NOT building?

| Excluded | Rationale |
|----------|-----------|
| **Animated autotiles** | Static only — explicitly scoped out by user |
| **A3/A4 wall autotiles** | Complex separate format; ground autotiles first |
| **Batch conversion** | Single file per session; CLI batch out of scope |
| **A2 full sheet input** | User provides extracted single autotile block |
| **Auto-detect format type** (XP vs MV) | User selects mode — simpler, less error-prone |
| **16-tile Edge set output** | Blob (47-tile) covers all cases including inner corners |
| **In-tool palette editing** | Out of scope |

---

## 9. Assumption Audit

| # | Assumption | Risk | Status |
|---|-----------|------|--------|
| A1 | XP input always 96×128 | Low | **VERIFIED** — sample confirmed, standard documented |
| A2 | MV/MZ input = extracted block (not full A2 sheet) | Low | **VERIFIED** — user confirmed |
| A3 | MV tile size detected from block_width (32 or 48) | Low | **VERIFIED** — sample is 64×96 = 32px |
| A4 | RPG Maker XP sub-tile lookup table is fixed and well-documented | Medium | **ASSUMED** — community verified, will hardcode in SPEC |
| A5 | RPG Maker MV sub-tile lookup table is fixed | Medium | **ASSUMED** — will derive from engine source in SPEC |
| A6 | TSX wangset type="mixed" works for 47-tile blob in Tiled 1.10 | Low | **VERIFIED** — Tiled terrain docs confirm Mixed = blob |
| A7 | customtkinter Canvas widget can render 47 tiles in preview grid | Low | **ASSUMED** — standard tkinter Canvas, no GPU needed |
| A8 | MZ uses identical autotile format to MV | Low | **ASSUMED** — MZ is a superset of MV, same asset format documented |

> **A4 & A5 are MEDIUM risk** — will be fully resolved in SPEC by encoding the exact pixel lookup coordinates for all 47 configurations.

---

## 10. Risks

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Sub-tile lookup table wrong → broken output | High | Validate with real samples (XP + MV files provided) |
| MV lookup differs from XP in undocumented ways | Medium | Cross-reference engine source + community wiki |
| TSX wangid mapping off-by-one | Medium | Test import in Tiled before finalizing |
| Canvas preview misleading (shows wrong test pattern) | Low | Use a known blob pattern for validation |

---

## Next Step

→ **📋 SPEC** stage. Modules to spec:

1. `src/asset_convertor/core/converter_xp.py` — XP lookup table + assembly logic
2. `src/asset_convertor/core/converter_mv.py` — MV/MZ lookup table + assembly logic
3. `src/asset_convertor/exporters/tsx_generator.py` — TSX wangset XML output
4. `src/asset_convertor/gui/app.py` — replaced GUI (file picker, mode, previews, canvas, export)

**Test samples:** `tools/src/input/sample_xp.png`, `tools/src/input/sample_mv_32px.png`  
**Output dir:** `tools/src/output/`
