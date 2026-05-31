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
| BLOB_COUNT | 47 | Number of blob tiles (49 slots, 2 empty) |
| BLOB_BITMASKS | tuple | 47 valid terrain bitmask values |
| BLOB_COMBINATIONS | list | 49 quadrant combinations mapping to source sub-tiles |

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
The index is simply the position in `BLOB_BITMASKS`. There are exactly 49 slots per frame, including empty transparent padding at slots 41 and 48.

---

## Output Data

### PNG Strip

Dimensions: (47 × 32) × 32 = 1504 × 32 px
Tiles 0-46: Ordered by BLOB_BITMASKS sequence.

### TSX XML

The script generates the TSX dynamically using the following XML template, sourcing the Tiled version and Wang color from module-level constants `TILED_VERSION = "1.10.0"` and `WANG_COLOR = "#4488ff"` respectively:

```xml
<tileset version="1.10" tiledversion="{tiled_version}"
         name="{stem}" tilewidth="32" tileheight="32"
         tilecount="47" columns="47">
  <image source="{rel_png}" width="1504" height="32"/>

  <!-- Animations (if N > 1): same logic as the animated script -->
  <tile id="{i}">
    <animation>
      <frame tileid="{i}"       duration="{ms}"/>
      <frame tileid="{47 + i}"  duration="{ms}"/>
      ...
    </animation>
  </tile>

  <wangsets>
    <wangset name="{stem}" type="mixed" tile="-1">
      <wangcolor name="{stem}" color="{wang_color}" tile="-1" probability="1"/>
      <!-- 47 wangtiles -->
      <wangtile tileid="{i}" wangid="{_blob_wang_id(bitmask)}"/>
    </wangset>
  </wangsets>
</tileset>
```

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
| N == 1 | warning | `WARNING: Single frame — static output` |
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
| AP-1 | Reusing `_build_tile` (4-bit edge) | Use `_assemble_tile` with the 49 combinations |
| AP-2 | wangset `type="edge"` | `type="mixed"` for corner+edge blob |
| AP-3 | 16 wangtiles | 47 wangtiles (slots 41 and 48 omitted) |
| AP-4 | wangid format `T,0,R,0,B,0,L,0` | Mixed format `TL,T,TR,R,BR,B,BL,L` |
| AP-5 | fixed tilecount=49 | `tilecount = n_frames * 49` |
| AP-6 | Including empty slots (41,48) in wangtiles | Omit them — transparent tiles, no terrain |
| AP-7 | Ignoring diagonals in bitmask | Apply blob rule: diagonal=0 if cardinal is absent |

---

## Test Case Specifications

### UT-001 — _assemble_tile: correct dimensions
**Input:** synthetic 96×128 frame, combo index 8 (center full)  
**Expected:** 32×32 RGBA tile

### UT-002 — _blob_mask: diagonal rule
**Input:** n=True, nw=True, w=False  
**Expected:** nw forced to 0 (w absent)

### UT-003 — _blob_wang_id: bitmask 255 (surrounded)
**Input:** bitmask=255  
**Expected:** `"1,1,1,1,1,1,1,1"`

### UT-004 — _blob_wang_id: bitmask 0 (isolated)
**Input:** bitmask=0  
**Expected:** `"0,0,0,0,0,0,0,0"`

### UT-005 — Static strip: dimensions
**Input:** 96×128 image  
**Expected:** strip size == (1568, 32)

### UT-006 — Transparent empty slots
**Input:** slot 41 and 48  
**Expected:** pixels = (0,0,0,0) RGBA

### UT-007 — Height validation
**Input:** 96×64 image  
**Expected:** SystemExit, "height"

### UT-008 — Width validation
**Input:** 100×128 image  
**Expected:** SystemExit, "multiple"

### IT-001 — Complete static pipeline
**Input:** grass.png 96×128  
**Expected:** 1568×32 PNG, TSX tilecount=49, 47 wangtiles, type="mixed"

### IT-002 — Animated pipeline N=4
**Input:** water.png 384×128, frame_duration=200  
**Expected:** 7056×32 PNG (4×49×32), 47 `<tile><animation>` of 4 frames

### IT-003 — Bitmask 255 → slot 46 (center)
**Input:** bitmask=255  
**Expected:** BITMASK_TO_IDX[255] == 46

### IT-004 — Relative image in TSX
**Input:** tsx in `autotiles/tilesets`, png in `autotiles/images`  
**Expected:** `<image source>` is relative

---

## Deep Links

- Tiled mixed Wang: https://doc.mapeditor.org/en/stable/reference/tmx-map-format/#wangset
- devium/tiled-autotile: https://github.com/devium/tiled-autotile
- Blob Script: [rpgmaker_blob_autotile_to_tiled.py](../../autotiles/rpgmaker_blob_autotile_to_tiled.py#L1)
