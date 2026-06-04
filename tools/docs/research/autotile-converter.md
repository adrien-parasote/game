# Research: RPG Maker Autotile → Tiled Converter

**Date:** 2026-06-04  
**Stage:** DISCOVER  
**Decision:** Build-New (no off-the-shelf Python lib covers all three modes + GUI)

---

## 🔬 Axis 1 — Domain Context: RPG Maker Autotile Formats

### RPG Maker XP (RMXP)

**File location:** `Graphics/Autotiles/`  
**Dimensions:** **96 × 128 pixels** (static), 288 × 128 (3-frame animated)  
**Tile unit:** 32 × 32 px (map tile), assembled from **16 × 16 sub-tiles**  
**Sub-tile grid:** 6 columns × 8 rows of 16 × 16 mini-tiles

#### Internal layout (96 × 128):
```
Row 0: [ICON 32x32 preview (2 sub-cols × 2 sub-rows)] [empty/preview col]
Row 1-4: encoded sub-tiles for the 47 transition combinations
```

- The **top-left 32×32 area** (rows 0–1, cols 0–1 in sub-tile grid) is the **editor icon only** — never rendered on the map.
- The engine reads the remaining 16×16 sub-tiles and **assembles them dynamically** based on neighbor bitmask.
- Each 32×32 map tile = 4 quadrants (TL, TR, BL, BR) each 16×16 pulled from specific positions.
- The autotile has **exactly 8 distinct sub-tile "shapes"**: inner fill, 4 edges (N/S/E/W), 4 outer corners (NE/NW/SE/SW), 4 inner corners.
- Animated version = 3 frames side by side → 288 × 128.

**Key sub-tile positions (16×16 grid within 96×128):**

| Sub-tile role | Pixel position (x, y) in file |
|---|---|
| Icon (editor only) | (0,0) to (31,31) |
| Inner fill (center) | (0,32) area |
| N edge | various |
| NW outer corner | various |
| NW inner corner | various |
| … | … |

> Source: RPGMakerWeb tutorials, local HTML extract (Oniromancie), web search

---

### RPG Maker MV / MZ (identical format)

**File location:** `img/tilesets/` (sheet files named A1–A5, B–E)  
**Relevant files for ground autotiles:** **A2** (ground/floor), **A1** (animated water), **A3** (walls), **A4** (mixed walls+floors)

**Dimensions:** A2 = **768 × 576 pixels** (Area mode) or same dimensions (World mode)  
**Tile unit:** **48 × 48 px**, assembled from **24 × 24 sub-tiles**

#### A2 layout (Area mode):
- **16 columns × 12 rows** of 48×48 tiles
- Each autotile occupies a **2-column × 3-row** block = 96×144 px
- The **top-left 48×48** of each block = editor preview tile (not rendered on map)
- Remaining 5 tiles in the block encode the shape pieces for assembly
- The engine assembles tiles from 24×24 quadrants based on neighbor bitmask
- **48 combinations** possible (47 unique + 1 duplicate to fill grid)

#### A2 layout (World mode):
- Same dimensions but different column arrangement (columns 1 & 3 are base, 2 & 4 are embellishments)

#### For static conversion purposes:
We target **A2 (Area mode)** ground autotiles as the primary MV/MZ input.

> Source: RPGMakerWeb forums, Oniromancie MV/MZ guide (local HTML), web search

---

## 🔬 Axis 2 — Competitive Landscape: Existing Tools

| Tool | Platform | Status | Limitation |
|---|---|---|---|
| Remex | Windows app | Abandonware (repo 404) | XP only, no GUI Python |
| Leafo autotile converter | Web/Lua | Web only | MV only |
| Aseprite scripts | Aseprite plugin | Requires Aseprite | Not standalone |
| Tilesetter | Desktop app | Commercial ($) | Not open source |
| Manual conversion | User work | Always available | Error-prone |

**Decision: Build-New** — No Python lib handles all 3 input modes (XP + MV + MZ) with a GUI + Tiled TSX export + canvas preview.

---

## 🔬 Axis 3 — Technical Feasibility: Tiled Output Format

### What Tiled expects for autotiles (Terrain / Wangset)

The standard "Tiled-compatible" autotile format is a **47-tile blob tileset** in a flat sprite sheet, with an accompanying **TSX (tileset XML)** that defines the `<wangsets>` terrain rules.

#### The 47-tile Blob Tileset
Defined by the cr31 Wang blob specification. Uses 8-neighbor bitmask:

```
NW=128  N=1   NE=2
W=64   [tile]  E=4
SW=32   S=16  SE=8
```

Index = sum of active neighbor bits. The 47 valid blob indices are:
```
0, 1, 4, 5, 7, 16, 17, 20, 21, 23, 28, 29, 31, 64, 65, 68, 69, 
71, 80, 81, 84, 85, 87, 92, 93, 95, 112, 113, 116, 117, 119, 124, 
125, 127, 193, 197, 199, 209, 213, 215, 221, 223, 241, 245, 247, 253, 255
```

#### Standard 47-tile layout (8 columns × 6 rows, with 1 duplicate)
The conventional layout used by most engines/tools places tiles in bitmask index order across an 8×6 grid. Tiled can also use rotation flags to reduce to 15 tiles, but we target the full 47 for maximum compatibility.

#### TSX output format
```xml
<?xml version="1.0" encoding="UTF-8"?>
<tileset version="1.10" tiledversion="1.10.2" 
         name="my_autotile" 
         tilewidth="32" tileheight="32" 
         tilecount="47" columns="8">
  <image source="my_autotile_tiled.png" 
         width="256" height="192"/>
  <wangsets>
    <wangset name="Terrain" type="mixed" tile="46">
      <wangcolor name="Terrain" color="#ff0000" tile="46" probability="1"/>
      <!-- one <wangtile> per tile: -->
      <wangtile tileid="0"  wangid="0,0,0,0,0,0,0,0"/>  <!-- bitmask 0 -->
      <wangtile tileid="1"  wangid="1,0,0,0,1,0,0,0"/>  <!-- bitmask 1 = N -->
      <!-- ... 47 total entries ... -->
    </wangset>
  </wangsets>
</tileset>
```

**wangid format:** `[top, topRight, right, bottomRight, bottom, bottomLeft, left, topLeft]`  
Values: `0` = no terrain, `1` = terrain color 1

#### Output sprite sheet
- **Static output:** PNG containing 47 tiles in an 8×6 grid (last row partially filled, or 6×8)  
- Tile size matches input: **32×32 for XP**, **48×48 for MV/MZ**

---

## 🔍 Key Technical Decisions

### 1. Input format parsing

#### XP (96×128):
The engine uses a lookup table of 47 configurations. Each configuration specifies which 16×16 sub-tile to copy to each quadrant of the output 32×32 tile. This lookup table is well-documented and can be hardcoded.

**Strategy:** Use Pillow to crop sub-tiles from source image, assemble output tiles via lookup table.

#### MV/MZ (A2 sheet, 768×576):
Each autotile block is a 2-column × 3-row area (96×144 px). The engine uses 24×24 sub-tiles from this block to assemble the 48 transitions. The lookup table for MV is also well-documented.

**Strategy:** Same as XP but with different tile sizes (48 px) and different lookup table.

### 2. Output tile size
- **XP input → 32×32 output tiles** (matching XP's native tile size)
- **MV/MZ input → 48×48 output tiles** (matching MV/MZ native tile size)

### 3. Lookup table source
The exact sub-tile sampling coordinates for each of the 47 blob configurations are derived from the RGSS/RPGMaker engine source and community-verified documentation. They will be hardcoded as a Python constant.

### 4. Canvas preview for validation
The tool will render a small test map (~5×5 tiles) using the 47 output tiles with typical patterns (center surrounded by borders) to validate the conversion visually.

---

## 📋 Adopt / Adapt / Build Decision

| Component | Decision | Rationale |
|---|---|---|
| XP sub-tile lookup table | **Adapt** | Community-documented, needs Python implementation |
| MV sub-tile lookup table | **Adapt** | Community-documented, needs Python implementation |
| 47-tile blob bitmask system | **Adopt** | Well-proven, cr31 spec |
| TSX wangset XML format | **Adopt** | Official Tiled spec |
| GUI shell | **Adapt** | Reuse customtkinter from existing asset_convertor |
| Canvas/preview | **Build** | tkinter Canvas with pattern drawing |

---

## ⚠️ Assumptions (to verify during SPEC)

1. **XP input tile size is always 32×32** — Risk: Low (documented standard)
2. **MV/MZ input tile size is always 48×48** — Risk: Low (documented standard)
3. **We only handle A2 ground autotiles for MV/MZ** (not A1/A3/A4/walls) — Risk: Low (scope decision)
4. **Static only (no animated frames)** — Risk: None (explicitly scoped out by user)
5. **The entire A2 sheet is not the input** — user provides a **single autotile block** extracted from A2, not the full 768×576 sheet — **Risk: Medium** — must clarify in SPEC whether input is the full A2 sheet or a single extracted autotile
6. **Output grid is always 8 columns × 6 rows** = 256px wide for 32px tiles, 384px wide for 48px tiles

> **⚠️ Assumption 5 is HIGH PRIORITY to clarify**: Does the user provide the full A2 sheet (768×576) and we pick one autotile, OR do they provide a pre-extracted single autotile block (96×144)? The UI should handle both but spec must decide.

---

## 📦 Sample Files — Confirmed Analysis

### XP Sample: [`tools/src/input/sample_xp.png`](file:///Users/adrien.parasote/Documents/perso/game/tools/src/input/sample_xp.png)

**Dimensions:** 96×128 px — **✅ Matches standard RMXP format exactly**

| Tile position (32px grid) | Role |
|---|---|
| (col=0, row=0) — top-left 32×32 | **ICON** shown in editor palette |
| (col=1, row=0) — top-center 32×32 | **EMPTY indicator** (solid teal `#549696`) — not used for map rendering |
| (col=2, row=0) — top-right 32×32 | **Inner fill** (fully surrounded = solid texture) |
| (col=0..2, row=1) — y=32..63 | Shape data row A (outer corner pieces) |
| (col=0..2, row=2) — y=64..95 | Shape data row B (edge pieces) |
| (col=0..2, row=3) — y=96..127 | Shape data row C (inner corner pieces) |

Sub-tile resolution: **16×16 px** (6 cols × 8 rows).  
The 47 blob output tiles are assembled by sampling specific 16×16 quadrants from this file.

---

### MV Sample: [`tools/src/input/sample_mv_32px.png`](file:///Users/adrien.parasote/Documents/perso/game/tools/src/input/sample_mv_32px.png)

**Dimensions:** 64×96 px — **MV/MZ autotile block with 32×32 tiles** (2 cols × 3 rows)

Standard MV uses 48×48 tiles (96×144 block), but this sample uses **32×32 tiles** (community pack format).  
The tool must **auto-detect** tile size from block dimensions:

| Block dimensions | Tile size | Format |
|---|---|---|
| 64×96 px | 32×32 | MV/MZ community pack |
| 96×144 px | 48×48 | MV/MZ standard official |

Detection rule: `tile_size = block_width // 2`

---

## References

- [Tiled Terrain Documentation](https://doc.mapeditor.org/en/stable/manual/terrain/)
- [cr31 Blob Tileset Specification](https://web.archive.org/web/20230101/cr31.co.uk/stagecast/wang/blob.html)
- [RPGMakerWeb Autotile Tutorials](https://rpgmakerweb.com)
- Local HTML: `extract/web/[RPG-MAKER.FR] ... Réaliser un autotile.html` (XP format)
- Local HTML: `extract/web/[RPG-MAKER.FR] ... templates MV et MZ.html` (MV/MZ format)
