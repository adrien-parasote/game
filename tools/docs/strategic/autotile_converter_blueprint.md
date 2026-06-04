# Strategic Blueprint — Autotile Converter: RPG Maker → Tiled

> **Date:** 2026-06-04
> **Status:** STRATEGY — pending SPEC approval
> **Research:** [animated_autotiles.md](../../docs/research/animated_autotiles.md)
> **Replaces:** `autotile-pipeline-strategy.md` (obsolete — 16-tile Edge set, no GUI)

---

## 1. What exact problem are you solving?

**Persona:** Solo game developer with existing RPG Maker XP / MV / MZ asset libraries.

**Current pain:** Autotile assets from RPG Maker (including animated floor/water and waterfalls) cannot be used directly in Tiled. RPG Maker uses a proprietary sub-tile layout and animation loop that requires engine-side processing. Tiled expects either manually placed static tiles or a **47-tile blob spritesheet** with matching TSX terrain and animation frame loop metadata.

The developer must:
1. Manually slice, reassemble, and compile multiple frames for each animated autotile into dozens of animation variants → error-prone, hours of repetitive work.
2. Or discard the entire RPG Maker animated asset library and draw everything from scratch.

**Measurable outcome:**
- Load a RPG Maker static or animated autotile PNG into the tool → get a Tiled-ready multi-frame PNG + TSX file with animation metadata in **< 5 seconds**.
- Visual canvas animates the converted tiles in real-time, confirming correct loop progression before export.
- Zero manual configuration required in Tiled after export.

---

## 2. Success Metrics

| Metric | Target | Timeline | How Measured |
|--------|--------|----------|-------------|
| **Conversion correctness** | All 47 blob tiles correctly assembled from input | V1.0 | Unit tests + Tiled visual check |
| **Mode coverage** | XP + MV + MZ inputs all produce valid output | V1.0 | Pytest pass rate |
| **Auto-detect tile size** | Correctly identifies 32px vs 48px MV blocks | V1.0 | Integration tests |
| **Export completeness** | PNG + TSX generated in one click | V1.0 | GUI export trigger verification |
| **Preview validation** | Canvas draws 5×5 test pattern using output tiles | V1.0 | GUI render |
| **Speed** | < 5s from file load to export ready | V1.0 | Execution timer |
| **Tiled compatibility** | TSX loads in Tiled 1.10+ without manual edits | V1.0 | Manual Tiled loading |
| **Animation support** | Converted horizontal and vertical frames cycle correctly | V2.0 (New) | Pytest + visual verification |
| **Auto-detect frames** | Correctly identifies 3-frame vs 4-frame width/height | V2.0 (New) | Integration tests |
| **Canvas animation** | Canvas preview loops frames smoothly at configured speed | V2.0 (New) | Interactive review |

---

## 3. Structural Advantage

The conversion from RPG Maker → Tiled blob is a **well-defined deterministic mapping**:
- The 47 blob tile configurations are fixed (cr31 specification).
- The RPG Maker sub-tile sampling positions are fixed (engine source lookup tables).
- Animations follow standard frame sequences (ping-pong `0 → 1 → 2 → 1` or linear loop).
- No ML, no heuristics, no user judgment — just pixel cropping, frame stacking, and XML writing.

We own the full pipeline: load input → extract sub-tiles → assemble 47 tiles per frame → stack vertically → write PNG + TSX. No runtime dependency on external programs.

---

## 4. Core Architecture Decisions

### ADR-001: Transform asset_convertor, not a new tool
*Status: Approved* (V1.0)
- The existing `tools/src/asset_convertor/` GUI shell (customtkinter) is replaced in-place. The new autotile converter reuses the window/layout pattern but replaces the generation logic.

### ADR-002: 47-tile Blob output (not 16-tile Edge)
*Status: Approved* (V1.0)
- Output format is the **47-tile Mixed Wang / Blob** tileset, not the older 16-tile Edge set.

### ADR-003: Mode selection drives the conversion logic
*Status: Approved* (V1.0)
- Three distinct converter modes — XP, MV, MZ — are selected by the user. Auto-detect of tile size within MV/MZ is performed based on image dimensions.

### ADR-004: GUI tech stack — stay on customtkinter
*Status: Approved* (V1.0)
- Keep **customtkinter** (already installed). The canvas for validation is a `tkinter.Canvas` widget.

### [ADR-005](../ADRs/ADR-005-animated-autotile-tileset-layout.md): Animated Autotile Tileset Layout & Cycle Rules
*Status: Pending Approval* (V2.0)
- Converted animation frames are stacked vertically (8 columns × `6 * N` rows) in the output PNG.
- TSX file includes `<animation>` tags for the first 47 tiles (indices 0..46), cycling through vertical offsets in the sheet.
- Waterfall autotiles (horizontal tiling only) are mapped to 47-tile sheets by repeating their 4 cardinal shapes.


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
| F9 | **Animation mode selection** — Statique / Horizontale / Verticale dropdown | 🔴 Required (New) |
| F10| **Animation speed selector** — configurable frame duration | 🟡 Preferred (New) |
| F11| **Canvas animation loop** — real-time canvas rendering of animation cycles | 🔴 Required (New) |
| F12| **Multi-frame TSX generator** — writes TSX animation nodes with local offsets | 🔴 Required (New) |
| F13| **Waterfall converter** — translates 4 waterfall shapes into 47-tile blob | 🔴 Required (New) |

---

## 7. UI Layout

```
┌──────────────────────────────────────────────────────────────────┐
│  Convertisseur Autotile — RPG Maker → Tiled          [—][□][×]  │
├─────────────────────────────────────────────────────────────────-┤
│  [📂 Ouvrir un autotile]   Format: ○ XP  ● MV  ○ MZ             │
│  Animation: [Horizontale  v]  Vitesse: [150 ms v]   [⚙ Convertir]│
├────────────────────┬────────────────────┬────────────────────────┤
│  SOURCE            │  SORTIE TILED      │  APERÇU CANVAS         │
│                    │                    │                        │
│  ┌──────────────┐  │  ┌──────────────┐  │  ┌──────────────────┐  │
│  │  PNG source  │  │  │ grille 8×6   │  │  │ motif test 5×5   │  │
│  │ (multi-frame)│  │  │ (Frame 0)    │  │  │                  │  │
│  │              │  │  │              │  │  │  ■■■■■ (Animé!)  │  │
│  └──────────────┘  │  └──────────────┘  │  │ ■■■■■■■          │  │
│                    │                    │  │  ■■■■■           │  │
│  Format: MV/32px   │  Tile: 32px        │  │                  │  │
│                    │  Sortie: 256×576   │  └──────────────────┘  │
├────────────────────┴────────────────────┴────────────────────────┤
│  [Exporter PNG + TSX]  Dossier: [tools/src/output/] [📂]        │
│  État: Prêt.                                                     │
└──────────────────────────────────────────────────────────────────┘
```

---

## 8. What are you NOT building?

| Excluded | Rationale |
|----------|-----------|
| **Custom frame counts > 4** | Standard animations cycle 3 or 4 frames. Complex speeds are out of scope. |
| **A3/A4 wall autotiles** | Complex separate format; ground autotiles first. |
| **Batch conversion** | Single file per session; CLI batch out of scope. |
| **A1/A2 full sheet input** | User provides single animated autotile block (containing all frames of that block). |
| **Auto-detect format type** (XP vs MV) | User selects mode — simpler, less error-prone. |
| **In-tool palette editing** | Out of scope. |

---

## 9. Assumption Audit

| # | Assumption | Risk | Status |
|---|-----------|------|--------|
| A1 | XP input always 96×128 | Low | **VERIFIED** — sample confirmed, standard documented |
| A2 | MV/MZ input = extracted block (not full A2 sheet) | Low | **VERIFIED** — user confirmed |
| A3 | Image unique multi-frames: input is a single image containing all frames side-by-side or stacked | Low | **VERIFIED** — corrected and verified by user |
| A4 | Tiled TSX `<animation>` syntax works on local tile IDs | Low | **VERIFIED** — official Tiled XML specification confirmed |
| A5 | Waterfall autotiles (horizontal only) map correctly to 47-tile blob | Low | **VERIFIED** — direct cardinal mapping math |
| A6 | XP animated autotiles follow the same 3-frame horizontal format | Medium | **ASSUMED** — will configure during SPEC |
| A7 | Customtkinter Canvas can render real-time ticks without lag | Low | **VERIFIED** — simple after() update loop is extremely fast |

---

## 10. Risks

| Risk | Impact | Mitigation |
|------|--------|-----------|
| **Animation loop stutter** | Medium | Use optimized Pillow crops and cache Frame PhotoImages on load rather than cropping on every tick. |
| **Out-of-sync frames** | Medium | Maintain absolute frame indexing using a modulo calculation relative to the detected frame count. |
| **Invalid block dimensions loaded** | High | Strictly validate that width and height match multiples of tile size based on selected format and animation mode. |

---

## Next Step

→ **📋 SPEC** stage. Modules to spec:

1. `src/asset_convertor/core/converter_mv.py` — Update to handle multi-frame horizontal water and vertical waterfalls
2. `src/asset_convertor/core/converter_xp.py` — Update to handle multi-frame horizontal autotiles
3. `src/asset_convertor/exporters/tsx_generator.py` — Update TSX generation to write `<animation>` tags
4. `src/asset_convertor/gui/app.py` — Add animation selector, speed picker, and `Tkinter.after` animation loop
