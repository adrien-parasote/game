# Research: Asset Creation Tool for Tiled-Native Tilesets

## Context

Build a Python tool for creating pixel art tileset assets (grass, paths, terrain, etc.)
that outputs **Tiled-native files** (PNG + TSX/TSJ with Wang sets) — eliminating the
current RPG Maker XP → Tiled conversion step.

The tool must be usable by both **human** (visual workflow) and **AI** (programmatic/CLI).

## Topic Decomposition

| # | Sub-Question | Why Necessary | Source Types |
|---|-------------|---------------|-------------|
| 1 | What is the Tiled-native autotile format? | Must generate correct output | Tiled official docs, existing .tsx files |
| 2 | What Python libraries handle pixel art + Tiled I/O? | Core dependencies | PyPI, GitHub |
| 3 | What autotiling standard to use (16/47 tiles)? | Determines output quality | Algorithm references, project history |
| 4 | What is the current asset pipeline? | Must integrate seamlessly | Project codebase |
| 5 | What existing tools solve this problem? | Adopt > Adapt > Build | Web search, GitHub |
| 6 | How to generate pixel art programmatically? | Core capability | Libraries, algorithms |

---

## Source Evaluation

| Source | Type | Date | Credibility | Key Findings |
|--------|------|------|-------------|-------------|
| Tiled JSON Map Format docs | Official docs | Current | High | TSX/TSJ format, Wang set structure, wangid 8-element array |
| Project `scripts/autotiles/` | Project code | Current | High | RPG Maker XP (96×128) → 16-tile edge or 47-tile blob Wang sets |
| Project `src/map/tmj_parser.py` | Project code | Current | High | Engine loads .tsx (XML), cuts PNG into tiles, no autotile awareness |
| Pillow docs (v12.2.0) | Official docs | Apr 2026 | High | Full pixel-level editing, palette mode, NEAREST resampling |
| opensimplex (PyPI) | Library | Maintained | High | Pure Python noise for procedural textures, NumPy support |
| Lospec API | API testing | Current | High | Per-palette JSON at `lospec.com/palette-list/[slug].json`, no search API |
| Tilewise.ai | Commercial tool | 2025 | Medium | Generates 47-tile blob tilesets from prompts, validates seams |
| PixelLab | Commercial tool | 2025 | Medium | AI pixel art with Wang-style terrain, Aseprite plugin |
| Slynyrd Pixelblog | Expert blog | 2019-2023 | High | Clustering, layering, palette techniques for natural tilesets |

## Key Findings

### 1. Current Pipeline (Pain Points)

```
RPG Maker XP autotile (96×128 PNG)
    ↓ rpgmaker_autotile_to_tiled.py (16 tiles, edge)
    ↓ rpgmaker_blob_autotile_to_tiled.py (47 tiles, blob)
Tiled Wang tileset (PNG strip + .tsx XML)
    ↓ Manually imported into Tiled
Map editing in Tiled (.tmj)
    ↓ src/map/tmj_parser.py
Game (Pygame)
```

**Problems:**
- Source format is RPG Maker XP — an unnecessary intermediate format
- Must find/draw in RPG Maker format, then convert
- No batch pipeline (manual script runs, no Makefile targets)
- Edge script (16 tiles) has documented bugs with corner cases
- Two separate scripts for two quality levels (edge vs blob)

### 2. Tiled-Native Target Format

**TSX (XML) with Wang set:**
```xml
<tileset name="grass" tilewidth="32" tileheight="32" tilecount="47" columns="47">
  <image source="grass.png" width="1504" height="32"/>
  <wangsets>
    <wangset name="grass" type="mixed" tile="-1">
      <wangcolor name="grass" color="#55aa00" tile="-1" probability="1"/>
      <wangtile tileid="0" wangid="0,0,0,0,0,0,0,0"/>
      <!-- ... 47 wangtiles ... -->
    </wangset>
  </wangsets>
</tileset>
```

**TSJ (JSON) alternative:**
```json
{
  "name": "grass", "tilewidth": 32, "tileheight": 32,
  "tilecount": 47, "columns": 47,
  "image": "grass.png", "imagewidth": 1504, "imageheight": 32,
  "wangsets": [{
    "name": "grass", "type": "mixed", "tile": -1,
    "colors": [{"name": "grass", "color": "#55aa00", "tile": -1, "probability": 1}],
    "wangtiles": [{"tileid": 0, "wangid": [0,0,0,0,0,0,0,0]}]
  }]
}
```

**wangid format:** `[Top, TopRight, Right, BottomRight, Bottom, BottomLeft, Left, TopLeft]`
- `0` = unset, `1` = first wangcolor, `2` = second, etc.

### 3. 47-Tile Blob Standard

The **47-tile blob** (8-neighbor bitmask with diagonal gating) is THE standard for
quality autotiling. Already implemented in `rpgmaker_blob_autotile_to_tiled.py`.

Key algorithm (already in project):
- 8-neighbor bitmask: NW=1, N=2, NE=4, W=8, E=16, SW=32, S=64, SE=128
- Diagonal gating: if cardinal edge absent, adjacent diagonal = 0
- Reduces 256 → 47 unique visual tiles
- Each tile assembled from 4 sub-tiles (16×16 quarters of a 32×32 tile)

### 4. Python Libraries (Validated)

| Library | Purpose | Install | Status |
|---------|---------|---------|--------|
| **Pillow** | Core image manipulation, pixel editing, palette mode | `pip install Pillow` | ✅ v12.2.0, very active |
| **NumPy** | Fast array-based pixel ops, procedural generation | `pip install numpy` | ✅ Active |
| **opensimplex** | Noise generation for terrain textures | `pip install opensimplex` | ✅ Maintained, no patents |
| **xml.etree** | TSX generation (already used in project) | stdlib | ✅ Built-in |

No additional libraries needed. The existing stack (Pillow + stdlib) is sufficient.

### 5. Existing Solutions Assessment

| Tool | Adopt? | Why |
|------|--------|-----|
| **Tilewise.ai** | No | Commercial, $, cloud-only, no Python API |
| **PixelLab** | No | Commercial, cloud-only, not tileset-focused |
| **Sprite Fusion** | No | Browser-based map editor, not asset generator |
| **Pyxelate** | No | Image-to-pixel-art converter, not generator. Inactive, Python 3.8 |
| **WFC implementations** | Partial | Good for map layout, not for individual tile creation |
| **Existing project scripts** | Adapt | Core blob algorithm is solid, just needs new input pipeline |

### 6. Asset Naming Convention (Project Standard)

```
NN-category[-variant].png
NN: 00=ground, 01=structural, 02=decorative, 03=interactive, 04=nature, 99=debug
```

### 7. Lospec Palette API

```
GET https://lospec.com/palette-list/{slug}.json
→ { "name": "...", "author": "...", "colors": ["574368", "8488d3", ...] }
```

No search API — must cache/bundle palettes locally.

---

## Gaps Identified

| Gap | Why It Matters | Resolution |
|-----|---------------|------------|
| No programmatic tile drawing | Need to generate pixel art without RPG Maker source | Build: Pillow-based tile drawing engine |
| No Tiled-native output (without RPG Maker input) | Current scripts require 96×128 RPG Maker input | Build: direct 47-tile generator |
| No palette management | Color consistency across tilesets | Build: palette system (Lospec integration + custom) |
| No preview system | Human needs to see tiles before committing | Build: HTML preview or Pygame preview |
| No batch pipeline | Manual runs = friction | Build: CLI with batch mode |

---

## Recommendation

- **Chosen approach:** **Build** (with heavy **Adapt** from existing blob algorithm)
- **Justification:**
  - No existing tool generates Tiled-native 47-tile blob tilesets from a programmatic/CLI workflow
  - The core blob algorithm already exists in `rpgmaker_blob_autotile_to_tiled.py` — the sub-tile assembly and Wang ID logic is proven
  - What's missing is the **input side**: instead of reading RPG Maker format, we need to **generate** the sub-tiles programmatically
  - Python stack (Pillow + NumPy + opensimplex) is sufficient, no new dependencies needed beyond opensimplex

## Discovered Patterns

1. **Sub-tile architecture is the key reuse** — the blob converter already knows how to assemble 47 tiles from 16×16 sub-tiles. The new tool needs to **generate** those sub-tiles instead of extracting them from RPG Maker PNGs.

2. **Template-based approach** — a terrain type can be defined as a set of sub-tile templates:
   - Center fill (seamless repeating texture)
   - Edge transitions (4 cardinal edges)
   - Corner transitions (4 outer + 4 inner corners)
   - = 13 unique sub-tile patterns → assembled into 47 tiles

3. **Palette-first workflow** — define colors before drawing. A terrain spec = palette + texture rules.

4. **Tiled uses .tsx (XML)** in this project, not .tsj (JSON) — new tool must output XML to match convention.

---

## DISCOVER Checklist

- [x] Topic decomposed into sub-questions before searching
- [x] Existing codebase search performed
- [x] Package registries consulted
- [x] Official reference documentation read (Tiled format docs)
- [x] At least 3 sources compared
- [x] Source credibility evaluated
- [x] Gaps explicitly identified with impact assessment
- [x] Adopt/Adapt/Build decision taken and justified
- [x] Results documented for spec integration
- [x] No prototyping done during research
- [x] Every conclusion supported by multiple sources
