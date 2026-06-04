# Research: Animated Autotiles Conversion

**Date:** 2026-06-04  
**Stage:** DISCOVER  
**Decision:** Build-New (Extend the existing `asset_convertor` tool to support animated autotiles)

---

## Topic Decomposition

| # | Sub-Question | Why Necessary | Source Types |
|---|---|---|---|
| 1 | What is the layout of RPG Maker A1 (animated) autotiles for MV/MZ and XP? | Understand block partitioning, dimensions, and types of autotiles (water vs. waterfall) in A1 sheets. | RPG Maker official help, corescript code analysis |
| 2 | How does RPG Maker's engine cycle animation frames for animated autotiles vs. waterfalls? | Match frame order and loop structure to create seamless animations in Tiled (e.g. ping-pong 0->1->2->1). | `Tilemap.js` source code analysis |
| 3 | How can Tiled represent animated autotiles using TSX files? | Determine the XML tags required to represent animations in TSX (Wangsets / Terrains). | Tiled official documentation |
| 4 | How should the GUI and output files be structured? | Define the layout of the generated PNG sheet and the GUI inputs needed for configuration. | Tiled documentation, UX best practices |

---

## 🔬 Axis 1: Domain Context

### RPG Maker A1 Autotile Format (MV/MZ)
The standard A1 tileset contains **16 autotile blocks** of 2 columns × 3 rows (in 48px tile units, that is 96×144 px per block).
The A1 sheet is divided into two columns of 8 blocks each (total width = 16 tiles = 768 px, height = 12 tiles = 576 px).

There are three types of A1 autotile blocks:
1. **Animated Floor Autotiles (e.g., Water, Lava):**
   - Consist of **3 frames** arranged horizontally side-by-side.
   - Each frame is a standard 2x3 block.
   - Total block size: 6 columns × 3 rows of tiles (192x96 px for 32px tiles; 288x144 px for 48px tiles).
   - Frame cycle: `0 → 1 → 2 → 1` (ping-pong, 4 steps).
2. **Static Floor Autotiles (e.g., Ground/Floors bordering water):**
   - Consist of a **single 2x3 block** (no animation).
   - Positioned as the 4th block next to kinds 0 and 1.
3. **Waterfall Autotiles:**
   - Consist of **3 frames stacked vertically** within a single 2x3 block.
   - Each frame is 2 tiles wide × 1 tile high.
   - Total block size: 2 columns × 3 rows of tiles.
   - Frame cycle: `0 → 1 → 2` (linear, 3 steps) or offset shifting: `by += animationFrame % 3`.
   - Uses a simplified 4-shape lookup table (`Tilemap.WATERFALL_AUTOTILE_TABLE`) rather than the 48-shape table.

---

## 🔬 Axis 2: Competitive Landscape

| Tool / Solution | Positioning | Strengths | Gaps | Source |
|---|---|---|---|---|
| **Tilesetter** | Commercial desktop app | Full-featured map and tileset editor. | Paid license; closed-source. | [tilesetter.org](https://www.tilesetter.org/) |
| **Leafo Autotile Converter** | Open-source Lua script / Web tool | Clean static A2 conversion. | Does not support animated autotiles (A1) or Tiled TSX animation tags. | [leafo.net](https://leafo.net/) |
| **Aseprite scripts** | Custom editor plugins | Direct image manipulation in Aseprite. | Requires Aseprite; lacks automatic Tiled TSX metadata generation. | GitHub |

---

## 🔬 Axis 3: Technical Feasibility

### Tiled Animation Format (TSX)
Animations are defined inside the `<tile>` element using an `<animation>` container containing `<frame>` tags:
```xml
<tile id="0">
  <animation>
    <frame tileid="0" duration="150"/>
    <frame tileid="48" duration="150"/>
    <frame tileid="96" duration="150"/>
    <frame tileid="48" duration="150"/>
  </animation>
</tile>
```
Each frame requires a local `tileid` and a `duration` in milliseconds.

### Proposed Conversion and Output Strategy
1. **Output PNG Sheet Layout:**
   We will stack the 47 converted tiles of each animation frame vertically.
   - Row 0-5 (indices 0..47): Frame 0 tiles (where slot 47 is transparent padding).
   - Row 6-11 (indices 48..95): Frame 1 tiles (padding at 95).
   - Row 12-17 (indices 96..143): Frame 2 tiles (padding at 143).
   - (For 4-frame animations) Row 18-23 (indices 144..191): Frame 3 tiles (padding at 191).
   
2. **TSX Generation:**
   Define the Tiled Wangset / Terrain on the first 47 tiles (indices 0..46). Add `<animation>` tags to map each of these 47 tiles to their counterparts in other frames:
   - For **3-frame ping-pong** (water): `i` (duration $D$) → `i + 48` ($D$) → `i + 96` ($D$) → `i + 48` ($D$).
   - For **3-frame linear** (waterfall): `i` ($D$) → `i + 48` ($D$) → `i + 96` ($D$).
   - For **4-frame linear**: `i` ($D$) → `i + 48` ($D$) → `i + 96` ($D$) → `i + 144` ($D$).

3. **Waterfall 47-Tile Mapping Strategy:**
   Since waterfalls only connect horizontally, we repeat their 4 shape configurations across the 47-tile blob layout based on horizontal neighbor presence:
   - No horizontal neighbors (isolated): map to shape 3.
   - West neighbor only: map to shape 2.
   - East neighbor only: map to shape 1.
   - Both West and East neighbors: map to shape 0.

---

## Cross-Axis Insights

1. **Terrain Usability:** By mapping waterfall shapes into a standard 47-tile sheet, we allow the user to use the exact same Tiled Terrain brush for water and waterfalls, removing the need for custom scripting in Tiled.
2. **Visual Realism:** Implementing real-time animation tick using Tkinter's `after()` loops in the Canvas preview will directly validate that the converted frames loop seamlessly before export.

---

## Recommendation

- **Chosen Approach:** **Adapt** and extend `asset_convertor` to support animated autotiles.
- **Justification:** Extending the existing layout and lookup structures ensures high code reuse. Supporting animated formats inside the same GUI keeps the tools unified.
- **Impact on Spec:** Add animation modes (Horizontale, Cascade/Verticale), custom dimension validation, and TSX animation tag writers.

---

## Discovered Patterns

- **Waterfall table:** Refer to `Tilemap.WATERFALL_AUTOTILE_TABLE` in `Tilemap.js` for quadrant offsets.
- **Animation speed:** Default speed in RPG Maker is 500ms (30 frames), but Tiled animations often use 150-200ms for smoother loops. We will make this configurable in the GUI.
