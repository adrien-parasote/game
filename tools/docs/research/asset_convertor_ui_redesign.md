# Research: Asset Convertor UI Redesign

> Document type: Research
> Stage: DISCOVER
> Date: 2026-06-05

---

## Axis 1 — Domain Context

### Current Tool Architecture

The `asset_convertor` tool (customtkinter, `tools/src/asset_convertor/gui/app.py`, 864 lines) currently supports:
- **XP format** (96×128 px static, n×96 px animated horizontal)
- **MV/MZ A2 ground autotile** (64×96 or 96×144 static; animated horizontal/vertical)

Implemented resource types: A1 (animated tiles), A2 (ground).
Missing: **A3 (Building Tiles)**, **A4 (Wall Tiles)**.

### Identified UI Pain Points

1. **Flat toolbar** — Format selector + animation controls crammed into one row. Cannot scale to A3/A4 without breaking layout.
2. **`mode` conflates format with resource type** — `Literal["XP", "MV", "MZ"]` doesn't distinguish A2 from A3 from A4. All three are "MV" format but have completely different conversion logic.
3. **Animation options always visible** — A3 buildings have no animation. A4 walls have no blob bitmask autotiling. Showing animation controls for these types creates confusion.
4. **No structural scalability** — Future features (recolorizer, palette swap) would need a completely different set of controls.

---

## Axis 2 — Competitive Landscape / Reference Tools

### TexturePacker
- **Mode selector is the branch root** — Data Format dropdown drives ALL subsequent options
- **Contextual reveal** — Selecting Unity vs Phaser shows completely different export fields
- **Progressive disclosure** — Advanced options grouped under collapsible categories
- **Real-time preview** — Preview panel updates immediately on any change

### Aseprite Export Dialog
- **Single-screen, not wizard** — despite complexity (layers, animation, palette...)
- **Tab-based within a modal** — "Layers" / "Frames" / "Output" tabs inside a single window
- **Contextual enable/disable** — Animation frames field grays out when exporting static images

### Pattern Verdict
- **Single-screen + progressive disclosure** is the established pattern for per-file asset conversion workflows
- **Wizard flow** is appropriate only for first-time project setup — not per-file conversion
- **Mode/type selector = first decision** that determines all subsequent options

---

## Axis 3 — Technical Feasibility

### RPG Maker MV A3/A4 Format Specs (from research)

| Resource Type | Full Sheet Dimensions | Sub-tile size | Structure |
|---|---|---|---|
| A1 (Animated Tiles) | 768×576 | 24×24 | Animated autotile blocks |
| A2 (Ground) | 768×576 | 24×24 | Standard blob autotile |
| **A3 (Buildings)** | **768×384** | **24×24** | 8 autotile blocks, simpler structure |
| **A4 (Walls)** | **768×720** | **24×24** | Wall face + edges/corners, complex |
| A5 (Normal Tiles) | 384×768 | 48×48 | No autotile — simple tileset |

**Key insight**: The tool currently works with individual autotile *blocks* (one block = one conversion), NOT full sheets. For A3/A4, the user will likely input individual blocks extracted from the sheet (same as A2 workflow).

**A3 Block dimensions (single block):** 96×48 px (2 tiles × 1 tile) — simpler than A2
**A4 Block dimensions (single block):** Requires more research with actual files

### What's Different About A3 Autotile Logic
- A3 uses a simpler 16-shape autotile (not the 47-shape blob)
- No diagonal neighbor detection needed
- Used for roof/building tops — terrain blending only on edges, not corners

### What's Different About A4 Autotile Logic
- A4 handles wall height — tiles stack vertically
- Wall top + wall face are separate concepts
- The "shadow" generation is handled by the engine, not the tile

---

## Cross-Axis Insights

1. **The real problem is `AppState.mode` not `AppState.resource_type`** — The current state machine needs a new axis: `resource_type: Literal["A1", "A2", "A3", "A4"]` that is independent of `format: Literal["XP", "MV", "MZ"]`. Not all formats support all resource types (XP only has one autotile type; MV has A1–A5).

2. **The toolbar can't grow — it needs a sidebar** — TexturePacker's insight applies: put the type selector prominently, then let a **contextual options panel** (sidebar or dedicated section below the toolbar) change based on what's selected. This is architecturally much cleaner than adding more items to a horizontal toolbar.

3. **Progressive disclosure is already partially implemented correctly** — The animation checkbox → animation controls reveal is the right pattern. The architectural change needed is at a higher level: the "resource type" selection revealing the right *set* of options panels.

4. **Future recolorizer doesn't need a different screen** — If the UI is redesigned as "type selector → contextual options panel → preview → export", a Recolorizer type just shows a different options panel (palette picker, color mapping). No wizard needed.

---

## Adopt / Adapt / Build Decision

| Option | Description | Decision |
|---|---|---|
| **Adopt** | Keep current 3-panel layout (Source/Output/Canvas) | ✅ ADOPT — panels are correct |
| **Adopt** | Progressive disclosure for contextual options | ✅ ADOPT — already partially done |
| **Adapt** | Toolbar → Left sidebar with type+format selector | ✅ ADAPT — move controls to a structured panel |
| **Build** | `resource_type` concept in AppState | ✅ BUILD — not in current architecture |
| **Build** | A3/A4 converter backends | ✅ BUILD — new converters needed |

---

## Open Questions for STRATEGY

1. **A3/A4 input format**: Does the user input a full A3/A4 sheet (768×384) or individual blocks? Need to test with actual files.
2. **A3 output**: What is the desired Tiled output for A3 buildings — a 47-tile blob tileset or a simpler tileset?
3. **Sidebar vs accordion** for the options panel: sidebar keeps the 3 preview panels wide; accordion collapses less-used options inline.
4. **XP + A3/A4 combinations**: Does XP format have buildings/walls with different autotile logic from MV?
