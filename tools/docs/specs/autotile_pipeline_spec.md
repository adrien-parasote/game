> Document Type: Implementation

# Spec: Blob Autotile Pipeline (47 tiles)

**Script:** `scripts/autotiles/rpgmaker_blob_autotile_to_tiled.py`  
**Replaces:** `scripts/autotiles/rpgmaker_autotile_to_tiled.py` (16 tiles edge-only → corner artifacts)  
**Research:** [devium/tiled-autotile](https://github.com/devium/tiled-autotile)

---

## Context and Decision

The 16-tile edge-only script generates artifacts at **diagonal corners** because it only recognizes 4 neighbors (T/R/B/L). The correct solution is the **47-tile blob** format, which encodes all 8 neighbors (T/R/B/L + 4 diagonals).

**ADR-002:** Adopt `devium/tiled-autotile` sub-tile assembly logic, adapted for our standalone pipeline.

---

## Assumptions

| # | Assumption | Risk | Validation |
|---|-----------|------|------------|
| A1 | The source RPG Maker XP autotile is 96×128 px (static) or N×96×128 (animated) | Low | [SHOW] verified via API call to `PIL` size check |
| A2 | The 47 devium combinations cover all visual edge cases of the blob | Low | [SHOW] verified via CLI call `python3` on reference maps |
| A3 | Tiled `type="mixed"` (corner+edge) supports the 47-tile blob | Low | [SHOW] verified via manual import check |
| A4 | The blob wangid encodes 8 directions: TL, T, TR, R, BR, B, BL, L | Low | [SHOW] verified via CLI call to `tiled` |

## Constants

| Constant | Value | Description |
|-----------|--------|-------------|
| SUBTILE | 16 | Half-tile in px |
| TILE_SIZE | 32 | Tile in px |
| BLOB_COUNT | 47 | Number of active blob tiles (no padding slots) |
| BLOB_BITMASKS | tuple | 47 valid terrain bitmask values (see below) |

---

## Source RPG Maker XP Format (96×128)

```
6 columns × 8 rows of 16×16 sub-tiles
Col 0-5, Row 0-7

Layout (in 32×32 tiles):
  [A][B][C]    A=isolated, B=inner-corners, C=variant
  [D][E][F]    D=left-edge, E=top-edge, F=right-edge
  [G][H][I]    G=left, H=CENTER (full), I=right
  [J][K][L]    J=bot-left, K=bot-edge, L=bot-right
```
The inner-corners (`B`) are located at columns 4-5, rows 0-1, and NOT at columns 2-3 (which are transparent in water tiles).

---

## The 47 Combinations (Sub-tiles)

The implementation does not use the devium 49 list but dynamically reconstructs the 47 terrain bitmasks (`BLOB_BITMASKS`) via modular `_quarter()` logic that maps each corner to its exact 16x16 sub-tile in the source.

> ⚠️ **No transparent padding slots exist in the real implementation.** The spec previously referenced slots 41 and 48 as transparent pads — this was incorrect. The real strip contains exactly 47 active tiles per frame, with no empty/transparent padding.

```python
BLOB_BITMASKS = (
    0, 2, 8, 10, 11, 16, 18, 22, 24, 26, 27, 30, 31, 64, 66, 72,
    74, 75, 80, 82, 86, 88, 90, 91, 94, 95, 104, 106, 107, 120,
    122, 123, 126, 127, 208, 210, 214, 216, 218, 219, 222, 223,
    248, 250, 251, 254, 255
)
```

## Bitmask → Tile Index

The 8-bit bitmask encodes neighbors: `NW=1, N=2, NE=4, W=8, E=16, SW=32, S=64, SE=128`

**Blob Rule:** If a cardinal neighbor (N/E/S/W) is absent, its adjacent diagonals are ignored when constructing the sub-tile to prevent "tearing".
The index is simply the position in `BLOB_BITMASKS`. There are exactly 47 slots per frame, with no transparent padding slots.

### Bitmask Bit-Position Reference

| Direction | Bit Value | Bit Position (shift) |
|-----------|-----------|---------------------|
| NW | 1 | `>> 0` |
| N | 2 | `>> 1` |
| NE | 4 | `>> 2` |
| W | 8 | `>> 3` |
| E | 16 | `>> 4` |
| SW | 32 | `>> 5` |
| S | 64 | `>> 6` |
| SE | 128 | `>> 7` |

> Cross-reference: the `_blob_wang_id()` function (below) uses these exact bit positions. The encoding table and the function must remain in sync.

### `_quarter(corner: str, c1: bool, c2: bool, diag: bool, iso: bool) -> tuple[int, int]`

Returns the `(col, row)` coordinates (in 16×16 sub-tile units) within the 96×128 source image for the given corner.

**Parameters:**
- `corner`: `"tl"` | `"tr"` | `"bl"` | `"br"`
- `c1`: vertical cardinal (N for `tl`/`tr`, S for `bl`/`br`)
- `c2`: horizontal cardinal (W for `tl`/`bl`, E for `tr`/`br`)
- `diag`: diagonal neighbor (NW, NE, SW, SE respectively)
- `iso`: `True` when ALL four cardinals are absent (full isolation)

**Blob Rule enforcement:** Diagonal gating is applied upstream by `_build_blob_tile` before calling `_quarter` — if a cardinal neighbor is absent, its adjacent diagonals are already forced to `False`.

**Full sub-tile mapping table (per corner, (col, row) in the 96×128 source grid):**

| Corner | c1 | c2 | diag | iso | (col, row) | Source piece |
|--------|----|----|------|-----|------------|--------------|
| tl | T | T | T | — | (2, 4) | H-TL (center) |
| tl | T | T | F | — | (4, 0) | B-TL (inner corner) |
| tl | T | F | — | — | (0, 4) | G-TL (left edge) |
| tl | F | T | — | — | (2, 2) | E-TL (top edge) |
| tl | F | F | — | T | (0, 0) | A-TL (isolated) |
| tl | F | F | — | F | (0, 2) | D-TL (corner) |
| tr | T | T | T | — | (3, 4) | H-TR (center) |
| tr | T | T | F | — | (5, 0) | B-TR (inner corner) |
| tr | T | F | — | — | (5, 4) | I-TR (right edge) |
| tr | F | T | — | — | (3, 2) | E-TR (top edge) |
| tr | F | F | — | T | (1, 0) | A-TR (isolated) |
| tr | F | F | — | F | (5, 2) | F-TR (corner) |
| bl | T | T | T | — | (2, 5) | H-BL (center) |
| bl | T | T | F | — | (4, 1) | B-BL (inner corner) |
| bl | T | F | — | — | (0, 5) | G-BL (left edge) |
| bl | F | T | — | — | (2, 7) | K-BL (bot edge) |
| bl | F | F | — | T | (0, 1) | A-BL (isolated) |
| bl | F | F | — | F | (0, 7) | J-BL (corner) |
| br | T | T | T | — | (3, 5) | H-BR (center) |
| br | T | T | F | — | (5, 1) | B-BR (inner corner) |
| br | T | F | — | — | (5, 5) | I-BR (right edge) |
| br | F | T | — | — | (3, 7) | K-BR (bot edge) |
| br | F | F | — | T | (1, 1) | A-BR (isolated) |
| br | F | F | — | F | (5, 7) | L-BR (corner) |

> **Verified:** This table was extracted directly from the `_quarter_tl`, `_quarter_tr`, `_quarter_bl`, or `_quarter_br` implementations in `tools/src/autotiles/rpgmaker_blob_autotile_to_tiled.py` on 2026-06-04.

---

## Output Data

### PNG Strip

Dimensions: `(n_frames × 47) × 32` px wide, `32` px tall.

- **Static (n_frames=1):** `47 × 32 = 1504` px wide.
- **Animated (n_frames=N):** `N × 47 × 32` px wide.

Tiles ordered by `BLOB_BITMASKS` sequence (47 entries, no transparent padding slots).

> ⚠️ **Correction from previous spec version:** Earlier versions stated `1568 × 32` (49 tiles) with two transparent padding slots at 41 and 48. The real implementation uses exactly 47 tiles with no padding. The `BLOB_COUNT = 47` constant in the source is the ground truth.

### TSX XML

The script generates the TSX dynamically using the following XML template, sourcing the Tiled version and Wang color from module-level constants `TILED_VERSION = "1.10.0"` and `WANG_COLOR = "#4488ff"` respectively.

**Variables:** `total = n_frames * BLOB_COUNT` (= `n_frames * 47`).

```xml
<tileset version="1.10" tiledversion="{tiled_version}"
         name="{stem}" tilewidth="32" tileheight="32"
         tilecount="{total}" columns="{total}">
  <image source="{rel_png}" width="{32 * total}" height="32"/>

  <!-- Animations: only present when n_frames > 1 -->
  <!-- slot = 0..46, fi = 0..n_frames-1 -->
  <tile id="{slot}">
    <animation>
      <frame tileid="{fi * 47 + slot}" duration="{ms}"/>
      ...
    </animation>
  </tile>

  <wangsets>
    <wangset name="{stem}" type="mixed" tile="-1">
      <wangcolor name="{stem}" color="{wang_color}" tile="-1" probability="1"/>
      <!-- 47 wangtiles, tileid = 0..46 (frame 0 only — Tiled follows <animation> for rendering) -->
      <wangtile tileid="{slot}" wangid="{_blob_wang_id(bitmask)}"/>
    </wangset>
  </wangsets>
</tileset>
```

> **Animated tileset layout:** For N frames, the PNG contains `N × 47` tiles laid out left-to-right. Frame 0 occupies slots 0–46, frame 1 occupies 47–93, etc. The `<animation>` element for slot `s` references `tileid = fi * 47 + s` for each frame `fi`. `tilecount` and `columns` are ALWAYS `n_frames * 47`.

### wangid blob (type="mixed")

Exact Tiled mixed format: `Top, TopRight, Right, BottomRight, Bottom, BottomLeft, Left, TopLeft`

```python
def _blob_wang_id(bitmask: int) -> str:
    nw = (bitmask >> 0) & 1
    n  = (bitmask >> 1) & 1
    ne = (bitmask >> 2) & 1
    e  = (bitmask >> 4) & 1
    se = (bitmask >> 7) & 1
    s  = (bitmask >> 6) & 1
    sw = (bitmask >> 5) & 1
    w  = (bitmask >> 3) & 1
    # Note: Tiled Wang ID expects exact array order
    return f"{n},{ne},{e},{se},{s},{sw},{w},{nw}"
```

---

## CLI Interface

```
python3 scripts/autotiles/rpgmaker_blob_autotile_to_tiled.py <input.png>
        [--tsx PATH] [--png PATH] [--frame-duration MS]
```

Identique au script animé. Si `width == 96` → static (pas d'animation). Si `width > 96` → animé.

---

## Algorithm

The module exposes a main `convert` function that coordinates the image and XML generation.
- **Image Assembly**: Reconstructs the 47-tile blob strip by cropping and pasting 16x16 sub-tiles from the source image according to predefined corner combinations.
- **XML Generation**: Dynamically writes the TSX Wangset using a standardized XML template.

## Error Handling Matrix

| Error | Response | Message |
|-------|----------|---------|
| Missing file | `sys.exit` | `ERROR: File not found: {path}` |
| Corrupt image | `sys.exit` | `ERROR: Cannot open image: {e}` |
| height ≠ 128 | `sys.exit` | `ERROR: Expected height 128px, got {h}px` |
| width % 96 ≠ 0 | `sys.exit` | `ERROR: Width not a multiple of 96px` |
| frame_duration ≤ 0 | `sys.exit` | `ERROR: --frame-duration must be > 0` |
| N == 1 | warning → **stderr** | `WARNING: Single frame detected — output will be static (no animation).` |
| mkdir fails | `sys.exit` | `ERROR: Could not create output directory: {e}` |
| PNG write fails | `sys.exit` | `ERROR: Cannot write PNG: {e}` |
| TSX write fails | `sys.exit` | `ERROR: Cannot write TSX: {e}` |

---

## Constraints

| Tier | Examples |
|------|----------|
| **Always do** | Run Python unit tests before completing execution; use pathlib.Path for all path manipulations; preserve 100% of horizontal pixel-art alignment (no horizontal scaling). |
| **Ask first** | Adding dependencies outside Pillow (PIL) to requirements.txt or pyproject.toml; changing the CLI argument contract names. |
| **Never do** | Commit raw image assets; use lossy compression (JPEG) for tileset outputs; apply horizontal interpolation or antialiasing (no fuzzy pixels). |

---

## Cross-Spec Contracts

### Produces
| Path / Identifier | Format | Schema location | Consumers |
|---|---|---|---|
| Target PNG strip | PNG (RGBA) | This spec § "PNG Strip" | Tiled Map Editor |
| Target TSX XML | TSX (XML) | This spec § "TSX XML" | Tiled Map Editor |

### Consumes
| Path / Identifier | Format | Schema location | Producer |
|---|---|---|---|
| Source RPG Maker autotile | PNG (RGBA) | This spec § "Source RPG Maker XP Format (96×128)" | RPG Maker XP / Artist |

### Public Interface
| Type | Identifier | Documented at |
|---|---|---|
| CLI Command | `python3 scripts/autotiles/rpgmaker_blob_autotile_to_tiled.py` | This spec § "CLI Interface" |
| Public function | `convert` | This spec § "Algorithm" |

### External Invocations
| Type | Invoked | Defined in |
|---|---|---|
| Python Library | `PIL` | External library (Pillow) |

### Tracked Concepts
| Concept | Status in this spec | Mentioned in |
|---|---|---|
| 47-Tile Blob | Implemented | [asset_creator_spec.md](./asset_creator_spec.md#L1) |

---

## Project File Tree

The following files are managed by this specification:
```
scripts/
  autotiles/
    rpgmaker_blob_autotile_to_tiled.py # [DEV-TOOL] Main blob autotile converter script
assets/
  images/
    autotiles/
      images/                          # [DEV-TOOL] Directory for image assets
  tiled/
    autotiles/
      tilesets/                        # [DEV-TOOL] Directory for tileset TSXs
third_party/
  devium/
    tiled-autotile/                    # [DEV-TOOL] Reference devium autotile repo
```

---

## Anti-patterns

| # | Anti-pattern | Correct |
|---|-------------|---------|
| AP-1 | Reusing `_build_tile` (4-bit edge) | Use `_build_blob_tile` with the 47-bitmask combinations |
| AP-2 | wangset `type="edge"` | `type="mixed"` for corner+edge blob |
| AP-3 | 16 wangtiles | 47 wangtiles |
| AP-4 | wangid format `T,0,R,0,B,0,L,0` | Mixed format `T,TR,R,BR,B,BL,L,TL` |
| AP-5 | Hardcoded `tilecount="49"` or `tilecount="47"` in TSX | `tilecount = n_frames * BLOB_COUNT` (= `n_frames * 47`) — ALWAYS dynamic |
| AP-6 | Adding transparent padding slots (41, 48) | No padding — the real implementation has exactly 47 active tiles per frame |
| AP-7 | Ignoring diagonals in bitmask | Apply blob rule: diagonal=0 if cardinal is absent |
| AP-8 | Hardcoded `columns="47"` or `columns="49"` | `columns = tilecount = n_frames * 47` — columns ALWAYS equals tilecount for single-row strips |

---

## Test Case Specifications

### UT-001 — _build_blob_tile: correct dimensions
**Input:** synthetic 96×128 frame, bitmask=255 (center full)  
**Expected:** 32×32 RGBA tile

### UT-002 — _blob_mask: diagonal rule
**Input:** n=True, nw=True, w=False  
**Expected:** nw forced to False (w absent)

### UT-003 — _blob_wang_id: bitmask 255 (surrounded)
**Input:** bitmask=255  
**Expected:** `"1,1,1,1,1,1,1,1"`

### UT-004 — _blob_wang_id: bitmask 0 (isolated)
**Input:** bitmask=0  
**Expected:** `"0,0,0,0,0,0,0,0"`

### UT-005 — Static strip: dimensions
**Input:** 96×128 image  
**Expected:** strip size == (1504, 32)  ← `47 × 32 = 1504`

### UT-006 — BLOB_COUNT and BLOB_BITMASKS alignment
**Input:** `len(BLOB_BITMASKS)`  
**Expected:** `== BLOB_COUNT == 47`

### UT-007 — Height validation
**Input:** 96×64 image  
**Expected:** SystemExit, message contains "height"

### UT-008 — Width validation
**Input:** 100×128 image  
**Expected:** SystemExit, message contains "multiple"

### UT-009 — _quarter tl mapping: both cardinals present, diag present
**Input:** `_quarter("tl", c1=True, c2=True, diag=True, iso=False)`  
**Expected:** `(2, 4)` (H-TL center sub-tile)

### UT-010 — _quarter tl mapping: both cardinals present, diag absent
**Input:** `_quarter("tl", c1=True, c2=True, diag=False, iso=False)`  
**Expected:** `(4, 0)` (B-TL inner corner sub-tile)

### IT-001 — Complete static pipeline
**Input:** grass.png 96×128  
**Expected:** 1504×32 PNG, TSX `tilecount="47"`, 47 wangtiles, `type="mixed"`

### IT-002 — Animated pipeline N=4
**Input:** water.png 384×128, frame_duration=200  
**Expected:** 5632×32 PNG (`4 × 47 × 32 = 5632`), TSX `tilecount="188"` (`4 × 47`), 47 `<tile><animation>` elements each with 4 frames

### IT-003 — Bitmask 255 → slot 46 (center)
**Input:** bitmask=255  
**Expected:** `BITMASK_TO_IDX[255] == 46`

### IT-004 — Relative image in TSX
**Input:** tsx in `autotiles/tilesets`, png in `autotiles/images`  
**Expected:** `<image source>` is a relative path

### IT-005 — Animated tilecount correct
**Input:** water.png 384×128 (N=4 frames)  
**Expected:** TSX attribute `tilecount == columns == 4 * 47 == 188`

---

## Deep Links

- Tiled mixed Wang: https://doc.mapeditor.org/en/stable/reference/tmx-map-format/#wangset
- devium/tiled-autotile: https://github.com/devium/tiled-autotile
- Blob Script: [rpgmaker_blob_autotile_to_tiled.py](../../autotiles/rpgmaker_blob_autotile_to_tiled.py#L1)
