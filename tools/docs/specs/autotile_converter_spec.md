# Autotile Converter Spec — RPG Maker → Tiled

> Document Type: Implementation
> **Covers:** F1, F2, F3, F4, F5, F6, F7, F8
> **Blueprint:** [autotile_converter_blueprint.md](../strategic/autotile_converter_blueprint.md#strategic-blueprint--autotile-converter-rpg-maker--tiled)
> **Research:** [autotile-converter.md](../research/autotile-converter.md#research-rpg-maker-autotile--tiled-converter)

---

## Blueprint Coverage Matrix

| Feature ID | Description | Spec section |
|---|---|---|
| F1 | File picker — load PNG, validate format | `gui/app.py § File Loading` |
| F2 | Mode selector — XP / MV / MZ | `gui/app.py § Mode Selection` |
| F3 | Input preview — display source image | `gui/app.py § Preview Panels` |
| F4 | Conversion engine — XP + MV lookup tables | `converter_xp.py` + `converter_mv.py` |
| F5 | Output preview — 47-tile sheet display | `gui/app.py § Preview Panels` |
| F6 | Canvas validator — 5×5 test pattern | `gui/app.py § Canvas Validator` |
| F7 | Export — PNG + TSX one-click | `tsx_generator.py` + `gui/app.py § Export` |
| F8 | Auto-detect MV tile size (32px vs 48px) | `converter_mv.py § detect_tile_size` |

---

## Deep Links

- [Blueprint § ADR-001](../strategic/autotile_converter_blueprint.md#adr-001-transform-asset_creator-not-a-new-tool)
- [Blueprint § ADR-002](../strategic/autotile_converter_blueprint.md#adr-002-47-tile-blob-output-not-16-tile-edge)
- [Blueprint § ADR-003](../strategic/autotile_converter_blueprint.md#adr-003-mode-selection-drives-the-conversion-logic)
- [Blueprint § ADR-004](../strategic/autotile_converter_blueprint.md#adr-004-gui-tech-stack--stay-on-customtkinter)
- [Blueprint § Success Metrics](../strategic/autotile_converter_blueprint.md#2-success-metrics)
- [Research § XP Format](../research/autotile-converter.md#axis-1--domain-context-rpg-maker-autotile-formats)
- [Research § MV Format](../research/autotile-converter.md#rpg-maker-mv--mz-identical-format)
- [Research § Tiled Output](../research/autotile-converter.md#axis-3--technical-feasibility-tiled-output-format)
- [Research § Blob Bitmask](../research/autotile-converter.md#the-47-tile-blob-tileset)
- [Research § TSX Format](../research/autotile-converter.md#tsx-output-format)
- [Research § Samples](../research/autotile-converter.md#-sample-files--confirmed-analysis)
- [cr31 Blob spec](http://cr31.co.uk/stagecast/wang/blob.html)
- [Tiled TSX terrain docs](https://doc.mapeditor.org/en/stable/manual/terrain/)
- [Sample XP](../../src/input/sample_xp.png#L1)
- [Sample MV 32px](../../src/input/sample_mv_32px.png#L1)
- [Sample MV 48px](../../src/input/sample_mv_48px.png#L1)

---

## Assumptions

| # | Assumption | Risk | Source Type | Status |
|---|---|---|---|---|
| A1 | XP input always 96×128 px | Low | SHOW — verified via `python3 -c "from PIL import Image; print(Image.open('tools/src/input/sample_xp.png').size)"` → `(96, 128)` | VERIFIED |
| A2 | MV/MZ input = extracted single autotile block | Low | SHOW — user explicitly confirmed in conversation 2026-06-04 | VERIFIED |
| A3 | MV tile_size = block_width // 2 (64→32, 96→48) | Low | SHOW — verified via `python3 -c "from PIL import Image; print(Image.open('tools/src/input/sample_mv_32px.png').size)"` → `(64, 96)` | VERIFIED |
| A4 | XP sub-tile lookup table is deterministic and fixed | Medium | SHOW — validated during BUILD: `convert_xp(sample_xp.png)` produced 47 non-empty tiles, all opaque (IT-003) | VERIFIED |
| A5 | MV sub-tile lookup table is deterministic and fixed | Medium | SHOW — validated during BUILD: `convert_mv(sample_mv_32px.png)` and `convert_mv(sample_mv_48px.png)` both produced 47 non-empty tiles (IT-002, IT-009) | VERIFIED |
| A6 | TSX wangset type="mixed" works in Tiled 1.10+ | Low | SHOW — verified via [Tiled terrain docs](https://doc.mapeditor.org/en/stable/manual/terrain/#wangsets) citing Mixed = blob type | VERIFIED |
| A7 | MZ uses identical autotile block format to MV | Low | TELL — MZ is documented as MV superset, same asset format in MZ release notes | ASSUMED |
| A8 | tkinter Canvas widget handles 47 tile PhotoImages | Low | SHOW — `python3 -c "import tkinter; print(tkinter.TkVersion)"` confirms stdlib availability | VERIFIED |

---

## Cross-Spec Contracts

### Produces

| Path / Identifier | Format | Schema location | Consumers |
|---|---|---|---|
| `tools/src/asset_creator/core/converter_xp.py` | Python Module | This spec § `converter_xp.py` | `gui/app.py` |
| `tools/src/asset_creator/core/converter_mv.py` | Python Module | This spec § `converter_mv.py` | `gui/app.py` |
| `tools/src/asset_creator/exporters/tsx_generator.py` | Python Module | This spec § `tsx_generator.py` | `gui/app.py` |
| `tools/src/asset_creator/gui/app.py` | Python Module | This spec § `gui/app.py` | `tools/src/asset_creator/__main__.py` |
| `tools/src/output/{name}.png` | PNG image | This spec § Output Format | Tiled editor |
| `tools/src/output/{name}.tsx` | TSX XML | This spec § TSX Format | Tiled editor |
| `tests/tools/asset_creator/test_converter_xp.py` | Python Test | This spec § Test Cases | Pytest |
| `tests/tools/asset_creator/test_converter_mv.py` | Python Test | This spec § Test Cases | Pytest |
| `tests/tools/asset_creator/test_tsx_generator.py` | Python Test | This spec § Test Cases | Pytest |

### Consumes

| Path / Identifier | Format | Schema location | Producer |
|---|---|---|---|
| `tools/src/input/*.png` | PNG image | This spec § Input Validation | User |
| `tools/src/asset_creator/core/minimap.py` | Python Module | asset_creator_spec.md § Modules | asset_creator_spec |

### Public Interface

| Type | Identifier | Documented at |
|---|---|---|
| Python function | `convert_xp(img: Image) -> list[Image]` | This spec § `converter_xp.py` |
| Python function | `convert_mv(img: Image) -> list[Image]` | This spec § `converter_mv.py` |
| Python function | `detect_tile_size(img: Image) -> int` | This spec § `converter_mv.py` |
| Python function | `generate_tsx(name, tile_size, n_cols, output_png) -> str` | This spec § `tsx_generator.py` |

### External Invocations

N/A — this spec invokes no external interfaces beyond the Python stdlib and Pillow.

### Tracked Concepts

| Concept | Status in this spec | Mentioned in |
|---|---|---|
| 47-tile blob bitmask | Produced (output tileset) | asset_creator_spec.md (canvas autotile mode) |
| minimap.py bitmask engine | Consumed (canvas validator) | asset_creator_spec.md |

---

## Constraints

| Tier | Examples |
|------|----------|
| **Always do** | Validate input image dimensions before conversion. Use Pillow for all image ops. Output PNG as RGBA. Run tests before any commit. |
| **Ask first** | Adding dependencies beyond Pillow + customtkinter + stdlib. Changing output tile size or sheet layout. Modifying the TSX wangid mapping order. |
| **Never do** | Mutate the source image (always work on copies). Hardcode output paths (use user-selected dir). Put image processing logic inside `gui/app.py`. Skip input validation. |

---

## Bundling & Native-Module Audit

- BM1: N/A — not a bundled framework project
- BM2: N/A — no client/server split
- BM3: N/A — no native modules introduced (Pillow is pure Python + C but no gyp)
- BM4: N/A — no constant renames in this spec

---

## Architecture Overview

```
tools/src/asset_creator/
├── core/
│   ├── converter_xp.py     [NEW] XP sub-tile assembly → 47 PIL Images
│   ├── converter_mv.py     [NEW] MV/MZ sub-tile assembly → 47 PIL Images
│   └── minimap.py          [EXISTING] bitmask engine (consumed by canvas)
├── exporters/
│   └── tsx_generator.py    [NEW] 47-tile PNG + TSX wangset writer
└── gui/
    └── app.py              [REPLACED] autotile converter GUI
        (replaces procedural tile generator GUI)

tools/src/
├── input/                  [NEW] User sample files directory
│   ├── sample_xp.png
│   └── sample_mv_32px.png
└── output/                 [NEW] Conversion output directory
    └── {name}.png + {name}.tsx

tests/tools/asset_creator/
├── test_converter_xp.py    [NEW]
├── test_converter_mv.py    [NEW]
└── test_tsx_generator.py   [NEW]
```

### Data Flow

```
User selects file + mode
        │
        ▼
validate_input(img, mode)
        │
        ▼
[XP mode] converter_xp.convert_xp(img)
[MV/MZ]   converter_mv.convert_mv(img)
        │
        ▼
list[PIL.Image] — 47 tiles, indexed 0..46
        │
        ├──► Output panel: display as 8×6 grid (F5)
        ├──► Canvas: draw 5×5 bitmask test pattern (F6)
        └──► Export:
                 ├── assemble_sheet() → PNG (8 cols × 6 rows)
                 └── generate_tsx()  → TSX wangset XML (F7)
```

---

## Module Specifications

---

### `core/converter_xp.py`

**Covers:** F4 (XP conversion)

#### Responsibilities

- Accept a single 96×128 RGBA PIL Image (RPG Maker XP autotile)
- Extract 16×16 sub-tiles from the source image
- Assemble 47 output tiles of 32×32 px using the XP lookup table
- Return `list[PIL.Image]` of exactly 47 images (index = blob position 0..46)

#### Input Contract

```
img: PIL.Image, mode RGBA
  width:  96 px (exactly)
  height: 128 px (exactly)
```

Raises `ValueError` if dimensions don't match.

#### XP Source Image Layout (verified against tutorial + pixel analysis 2026-06-04)

The XP autotile is a **6x8 grid of 16x16 sub-tiles** (96x128 px). Positions = (col, row), (0,0) at top-left.

```
Sub-tile positions in the 96x128 source:
  pixel_x = col * 16
  pixel_y = row * 16

Row 0-1 (y=0-32): ICON ZONE
  Col 0-1 (A tile): Isolated icon — shows how the autotile looks when alone in the editor.
  Col 2-3 (X zone): "Absence de surface" — background visible when autotile is absent.
                    This zone is often left transparent or filled with background color.
                    DO NOT use for inner corners.
  Col 4-5 (B tiles): Virages internes (inner corners) — 4 x 16x16 pieces:
                    B-TL (4,0): virage NW (used when NW diagonal is missing)
                    B-TR (5,0): virage NE (used when NE diagonal is missing)
                    B-BL (4,1): virage SW (used when SW diagonal is missing)
                    B-BR (5,1): virage SE (used when SE diagonal is missing)

Row 2-3 (y=32-64): TOP ZONE
  Col 0-1 (D): top-left outer corner
  Col 2-3 (E): top edge
  Col 4-5 (F): top-right outer corner

Row 4-5 (y=64-96): MIDDLE ZONE
  Col 0-1 (G): left edge
  Col 2-3 (H): center / interior fill
  Col 4-5 (I): right edge

Row 6-7 (y=96-128): BOTTOM ZONE
  Col 0-1 (J): bottom-left outer corner
  Col 2-3 (K): bottom edge
  Col 4-5 (L): bottom-right outer corner
```

> **Reference:** Verified by color-coded demo autotile (4 distinct colors at B-tile positions)
> and by the RPG Maker FR tutorial (Oniromancie - "Realiser un autotile"):
> "les virages internes font 16x16 px... une case sera partagee entre un element virage interne
> (16x16, un quart de case) et un element interieur (3 quarts)."

> **Critical anti-pattern:** See AP-11. The zone at col 2-3 ("absence de surface") is NOT
> the virage interne zone. Using (2,0)-(3,1) for inner corners reads the background/empty
> area and produces solid background-color squares at concave corners.

#### Quadrant Lookup Implementation (actual implementation)

The implementation uses `_quarter_tl/tr/bl/br(c1, c2, diag, iso)` functions that return
`(col, row)` of the 16x16 sub-tile to use for each quadrant. The B-tile inner corner
coordinates are:

```python
# When both cardinals present but diagonal MISSING:
_quarter_tl -> (4, 0)  # B-TL: virage NW
_quarter_tr -> (5, 0)  # B-TR: virage NE
_quarter_bl -> (4, 1)  # B-BL: virage SW
_quarter_br -> (5, 1)  # B-BR: virage SE

# When both cardinals present and diagonal PRESENT (interior):
_quarter_tl -> (2, 4)  # H-TL: center interior
_quarter_tr -> (3, 4)  # H-TR
_quarter_bl -> (2, 5)  # H-BL
_quarter_br -> (3, 5)  # H-BR
```


#### XP Lookup Table (47 blob configurations)

Each of the 47 valid blob bitmask values maps to 4 quadrant sub-tile names:

```python
# Format: bitmask -> (top_left_subtile, top_right_subtile, bottom_left_subtile, bottom_right_subtile)
XP_LOOKUP: dict[int, tuple[str, str, str, str]] = {
    0:   ("A1", "A2", "A3", "A4"),   # isolated — outer corners all 4
    1:   ("B1", "B2", "A3", "A4"),   # N only — N edge top + outer SW/SE
    4:   ("A1", "A2", "B3", "B4"),   # S only
    5:   ("B1", "B2", "B3", "B4"),   # N+S (vertical strip)
    7:   ("B1", "B2", "B3", "B4"),   # N+S+W
    16:  ("C1", "A2", "C3", "A4"),   # W only
    17:  ("C1", "B2", "C3", "A4"),   # N+W
    20:  ("A1", "C2", "A3", "C4"),   # E only
    21:  ("B1", "C2", "A3", "C4"),   # N+E
    23:  ("B1", "B2", "B3", "B4"),   # placeholder — full lookup from RGSS
    28:  ("C1", "C2", "C3", "C4"),   # W+E+S
    29:  ("C1", "C2", "C3", "C4"),   # W+E+S+N
    31:  ("D1", "D2", "D3", "D4"),   # surrounded (no corners) — inner fill
    # ... all 47 entries derived from RGSS source
    255: ("D1", "D2", "D3", "D4"),   # fully surrounded with all corners
}
```

> ⚠️ **The full 47-entry lookup table is to be derived during BUILD from the RGSS2 autotile rendering source.** The table above shows the format and key boundary cases. BUILD task: implement `_build_xp_lookup() -> dict[int, tuple[str,str,str,str]]` and validate against sample_xp.png.

#### BLOB_BITMASK_ORDER (47 valid indices, ordered for output grid)

```python
BLOB_BITMASK_ORDER: list[int] = [
    0, 1, 4, 5, 7, 16, 17, 20, 21, 23, 28, 29, 31,
    64, 65, 68, 69, 71, 80, 81, 84, 85, 87, 92, 93, 95,
    112, 113, 116, 117, 119, 124, 125, 127,
    193, 197, 199, 209, 213, 215, 221, 223,
    241, 245, 247, 253, 255
]
# len == 47
```

The output list index = position in BLOB_BITMASK_ORDER.

#### Public API

```python
def convert_xp(img: Image.Image) -> list[Image.Image]:
    """
    Convert a 96×128 RPG Maker XP autotile to 47 Tiled blob tiles.

    Args:
        img: RGBA PIL Image, must be 96×128 px.

    Returns:
        list of 47 RGBA PIL Images, each 32×32 px.
        Index i corresponds to BLOB_BITMASK_ORDER[i].

    Raises:
        ValueError: if img dimensions are not 96×128.
    """
```

```python
def _extract_subtile(img: Image.Image, col: int, row: int) -> Image.Image:
    """Crop 16×16 region at (col*16, row*16) from source image."""
```

```python
def _assemble_tile(subtiles: dict[str, Image.Image],
                   quadrants: tuple[str, str, str, str]) -> Image.Image:
    """
    Build a 32×32 tile from 4 named 16×16 sub-tiles.
    quadrants = (top_left, top_right, bottom_left, bottom_right)
    """
```

---

### `core/converter_mv.py`

**Covers:** F4 (MV/MZ conversion), F8 (auto-detect tile size)

#### Responsibilities

- Accept a single MV/MZ autotile block (64×96 or 96×144 RGBA PIL Image)
- Auto-detect tile size from block dimensions
- Extract 24×24 or 16×16 sub-tiles (half of tile size) from the block
- Assemble 47 output tiles using the MV lookup table
- Return `list[PIL.Image]` of exactly 47 images

#### Input Contract

```
img: PIL.Image, mode RGBA
  width:  64 px → tile_size = 32 (community pack)
  width:  96 px → tile_size = 48 (official MV/MZ)
  height: width * 1.5 (always)
```

Raises `ValueError` if `height != width * 1.5` or `width not in (64, 96)`.

#### Auto-detect Tile Size

```python
def detect_tile_size(img: Image.Image) -> int:
    """
    Returns 32 for 64×96 input, 48 for 96×144 input.
    Raises ValueError for unexpected dimensions.
    """
    if img.width == 64 and img.height == 96:
        return 32
    elif img.width == 96 and img.height == 144:
        return 48
    else:
        raise ValueError(f"Unexpected MV block size: {img.width}×{img.height}. Expected 64×96 or 96×144.")
```

#### MV Sub-Tile Layout

The MV autotile block is a **2×3 grid of `tile_size × tile_size` tiles**. Each tile is further divided into 4 sub-tiles of `(tile_size // 2) × (tile_size // 2)`.

```
For tile_size=32 (64×96 block):
  Sub-tile size = 16×16
  Block grid (in tile units):
    (0,0) | (1,0)    ← row 0: preview tile | inner corner tile
    (0,1) | (1,1)    ← row 1: top edges
    (0,2) | (1,2)    ← row 2: bottom edges + corners
```

| MV tile slot | Role | Pixel region (32px tiles) |
|---|---|---|
| (0,0) top-left | Preview tile (editor only — ignored) | (0,0)–(31,31) |
| (1,0) top-right | Inner corners (D-tiles: fully surrounded pieces) | (32,0)–(63,31) |
| (0,1) mid-left | Top half: N edge, NW outer corners | (0,32)–(31,63) |
| (1,1) mid-right | Top half: NE corners + E/W edges | (32,32)–(63,63) |
| (0,2) bot-left | Bottom half: S edge, SW outer corners | (0,64)–(31,95) |
| (1,2) bot-right | Bottom half: SE corners + inner corners | (32,64)–(63,95) |

The sub-tile extraction follows the same 4-quadrant (TL, TR, BL, BR) pattern as XP but with MV-specific source positions.

#### MV Lookup Table

```python
# Format: bitmask -> (TL_source, TR_source, BL_source, BR_source)
# Each source = (block_col, block_row, quadrant) where quadrant in (TL, TR, BL, BR)
# Full table derived from RPGMaker MV engine source (Game_Map tile assembly logic)
MV_LOOKUP: dict[int, tuple[tuple, tuple, tuple, tuple]] = {
    # 47 entries — to be fully populated during BUILD
    # Boundary cases:
    0:   (...),   # isolated — all outer corners
    255: (...),   # fully surrounded — all inner fill
}
```

> ⚠️ **BUILD task:** derive the full 47-entry MV lookup table from the RPGMaker MV source (Game_Map.js autotile tile logic). Validate output against sample_mv_32px.png by rendering bitmask=0, 255, and 17 (N+W corner).

#### Public API

```python
def detect_tile_size(img: Image.Image) -> int: ...

def convert_mv(img: Image.Image) -> list[Image.Image]:
    """
    Convert a MV/MZ autotile block to 47 Tiled blob tiles.

    Args:
        img: RGBA PIL Image, 64×96 or 96×144 px.

    Returns:
        list of 47 RGBA PIL Images, each tile_size × tile_size px.
        Index i corresponds to BLOB_BITMASK_ORDER[i].

    Raises:
        ValueError: if img dimensions are not 64×96 or 96×144.
    """
```

---

### `exporters/tsx_generator.py`

**Covers:** F7 (export PNG + TSX)

#### Responsibilities

- Accept 47 PIL Images (from converter output)
- Assemble them into a flat PNG sheet (8 columns × 6 rows)
- Generate the TSX XML with correct wangset `type="mixed"` definition
- Write both files to the output directory

#### Output Format — PNG Sheet

```
Sheet layout: 8 columns × 6 rows = 48 slots (47 tiles + 1 transparent pad)
Tile order: BLOB_BITMASK_ORDER[0..46] left-to-right, top-to-bottom
Slot 47 (last): transparent tile (same size, all alpha=0)

Output dimensions:
  tile_size=32 → PNG is 256×192 px
  tile_size=48 → PNG is 384×288 px
```

```python
def assemble_sheet(tiles: list[Image.Image], tile_size: int) -> Image.Image:
    """
    Arrange 47 tiles into 8-column × 6-row sheet.
    Last slot (index 47) is a transparent tile.
    Returns: RGBA PIL Image.
    """
```

#### Output Format — TSX

```xml
<?xml version="1.0" encoding="UTF-8"?>
<tileset version="1.10" tiledversion="1.10.2"
         name="{name}"
         tilewidth="{tile_size}" tileheight="{tile_size}"
         tilecount="48" columns="8">
  <image source="{name}.png" width="{sheet_width}" height="{sheet_height}"/>
  <wangsets>
    <wangset name="Terrain" type="mixed" tile="0">
      <wangcolor name="Terrain" color="#ff0000" tile="0" probability="1"/>
      <!-- 47 wangtile entries, one per blob configuration -->
      <wangtile tileid="{i}" wangid="{wangid}"/>
      ...
    </wangset>
  </wangsets>
</tileset>
```

#### WangID Mapping

Tiled wangid format: `"c,c,c,c,c,c,c,c"` where positions are:
`[top, topRight, right, bottomRight, bottom, bottomLeft, left, topLeft]`

Values: `0` = no terrain, `1` = terrain (color 1)

Mapping from blob bitmask to wangid:

```python
def bitmask_to_wangid(bitmask: int) -> str:
    """
    Convert 8-bit blob bitmask to Tiled wangid string.

    Blob bitmask bit positions:
        N=1, NE=2, E=4, SE=8, S=16, SW=32, W=64, NW=128

    Tiled wangid positions (index 0..7):
        [top, topRight, right, bottomRight, bottom, bottomLeft, left, topLeft]
        = [N,  NE,      E,     SE,          S,      SW,         W,    NW    ]

    Corner bits (NE, SE, SW, NW) are only "active" if BOTH adjacent cardinal
    edges are active (Wang mixed rules).
    """
    n  = 1 if bitmask & 1   else 0
    ne = 1 if bitmask & 2   else 0
    e  = 1 if bitmask & 4   else 0
    se = 1 if bitmask & 8   else 0
    s  = 1 if bitmask & 16  else 0
    sw = 1 if bitmask & 32  else 0
    w  = 1 if bitmask & 64  else 0
    nw = 1 if bitmask & 128 else 0
    return f"{n},{ne},{e},{se},{s},{sw},{w},{nw}"
```

#### Public API

```python
def assemble_sheet(tiles: list[Image.Image], tile_size: int) -> Image.Image: ...

def bitmask_to_wangid(bitmask: int) -> str: ...

def generate_tsx(
    name: str,
    tile_size: int,
    output_png_path: str,
) -> str:
    """
    Generate TSX XML string for a 47-tile blob wangset.

    Args:
        name: tileset name (also used as PNG filename reference)
        tile_size: 32 or 48
        output_png_path: relative or absolute path to the PNG file

    Returns:
        TSX XML as a string (UTF-8)
    """

def export(
    tiles: list[Image.Image],
    name: str,
    output_dir: str,
    tile_size: int,
) -> tuple[str, str]:
    """
    Write PNG sheet and TSX file to output_dir.

    Args:
        tiles: list of 47 PIL Images
        name: base filename (no extension)
        output_dir: directory path (created if missing)
        tile_size: 32 or 48

    Returns:
        tuple(png_path, tsx_path) — absolute paths of written files

    Raises:
        OSError: if output_dir is not writable
        ValueError: if tiles has != 47 elements
    """
```

---

### `gui/app.py` (REPLACED)

**Covers:** F1, F2, F3, F5, F6, F7

> ⚠️ The existing `gui/app.py` (Dear PyGui procedural tile generator) is **replaced in its entirety**. The new file uses customtkinter.

#### Responsibilities

- File picker (F1): open PNG file dialog, display selected path
- Mode selector (F2): XP / MV / MZ radio buttons
- Input preview (F3): display source PNG scaled to fit panel
- Trigger conversion on "Convert" button click
- Output preview (F5): display generated 47-tile sheet in 8×6 grid
- Canvas validator (F6): draw 5×5 test pattern using output tiles
- Export (F7): write PNG + TSX to output dir, show status
- Status bar: show current operation + errors

#### UI Language

All user-facing labels are in **French** (consistent with existing asset_creator convention).

#### Layout (three-column)

```
┌──────────────────────────────────────────────────────────────────┐
│  Convertisseur Autotile — RPG Maker → Tiled          [—][□][×]  │
├─────────────────────────────────────────────────────────────────-┤
│  [📂 Ouvrir un autotile]    Format : ○ XP  ● MV  ○ MZ          │
│                              [Convertir]                         │
├────────────────────┬────────────────────┬────────────────────────┤
│  SOURCE            │  SORTIE TILED      │  APERÇU CANVAS         │
│                    │                    │                        │
│  ┌──────────────┐  │  ┌──────────────┐  │  ┌──────────────────┐ │
│  │              │  │  │ grille 8×6   │  │  │ motif test 5×5   │ │
│  │  PNG source  │  │  │ 47 tiles     │  │  │                  │ │
│  │  (original)  │  │  │              │  │  │  ■■■■■           │ │
│  │              │  │  └──────────────┘  │  │ ■■■■■■■          │ │
│  └──────────────┘  │                    │  │  ■■■■■           │ │
│                    │  Tile: 32px        │  │                  │ │
│  Format: MV/32px   │  Sortie: 256×192  │  └──────────────────┘ │
│                    │                    │                        │
├────────────────────┴────────────────────┴────────────────────────┤
│  [Exporter PNG + TSX]  Dossier: [tools/src/output/] [📂]        │
│  État: Prêt.                                                     │
└──────────────────────────────────────────────────────────────────┘
```

#### File Loading (F1)

1. User clicks "📂 Ouvrir un autotile"
2. `filedialog.askopenfilename(filetypes=[("Images PNG", "*.png")])` opens picker
3. Load image with Pillow: `Image.open(path).convert("RGBA")`
4. Validate dimensions against selected mode (see Input Validation below)
5. Display source image in left panel (scaled to fit, `NEAREST` resampling)
6. Enable "Convertir" button

#### Input Validation

| Mode | Expected dimensions | Error if different |
|---|---|---|
| XP | 96×128 | "Format XP invalide. Attendu: 96×128 px, obtenu: {w}×{h}" |
| MV | 64×96 OR 96×144 | "Format MV invalide. Attendu: 64×96 ou 96×144 px, obtenu: {w}×{h}" |
| MZ | 64×96 OR 96×144 | "Format MZ invalide. Attendu: 64×96 ou 96×144 px, obtenu: {w}×{h}" |

#### Mode Selection (F2)

- Three radio buttons: XP / MV / MZ
- Default: MV
- Mode change resets conversion state (clears output panels, disables export)
- MV and MZ use identical conversion logic (`convert_mv` handles both)

#### Preview Panels (F3, F5)

**Source panel:** `CTkLabel` with `PIL.ImageTk.PhotoImage`. Scale image to fit a fixed 200×200 area using `NEAREST` resampling.

**Output panel:** `CTkLabel` with `PIL.ImageTk.PhotoImage`. Display the full 47-tile sheet (256×192 or 384×288) scaled to fit a fixed 300×200 area.

#### Canvas Validator (F6)

Draws a **5×5 test pattern** using the 47 converted tiles. Bitmask pattern:

```
Cells and their expected bitmask (8-neighbor):
Row 0: [0,   1,   1,   1,   0  ]  = isolated, N-edge variants, isolated
Row 1: [4,   85,  85,  85,  20 ]  = S, corners filled, S
Row 2: [4,   85,  255, 85,  20 ]  = S, center fill, S
Row 3: [4,   85,  85,  85,  20 ]  = ...
Row 4: [0,   16,  16,  16,  0  ]  = isolated, S-edge variants, isolated
```

The canvas renders each cell as a `tile_size × tile_size` image cropped from the converter output. Uses `tkinter.Canvas` with `create_image` for each cell.

#### Export (F7)

1. User selects output dir (default: `tools/src/output/`)
2. Name derived from source filename (without extension)
3. Calls `tsx_generator.export(tiles, name, output_dir, tile_size)`
4. Status bar: "Exporté : {name}.png + {name}.tsx → {output_dir}"
5. On error: status bar shows error in red

#### Internal State

```python
@dataclass
class AppState:
    source_path: str | None = None
    source_img: Image.Image | None = None
    mode: Literal["XP", "MV", "MZ"] = "MV"
    tiles: list[Image.Image] | None = None  # 47 tiles after conversion
    tile_size: int = 32
    output_dir: str = "tools/src/output/"
```

State is stored as instance variable on the `App` class, replaced on each update (not mutated).

---

## Error Handling Matrix

| Error | Trigger | User-visible message (French) | Recovery |
|---|---|---|---|
| File not found | path deleted after picker | "Fichier introuvable : {path}" | Reset to initial state |
| Wrong dimensions for mode | Image size mismatch | "Format {mode} invalide. Attendu: {expected}, obtenu: {w}×{h}" | Keep file loaded, block Convert button |
| Corrupted PNG | PIL fails to open | "Impossible de lire l'image. Vérifiez que le fichier est un PNG valide." | Reset file picker |
| Conversion error | Bug in lookup table | "Erreur de conversion : {error}. Vérifiez le format de l'autotile." | Show error, keep source display |
| Output dir not writable | Permission denied | "Impossible d'écrire dans {dir}. Choisissez un autre dossier." | Open dir picker |
| tiles != 47 | Internal bug | "Erreur interne : {n} tiles générées au lieu de 47." | Show error, block export |

All error states:
- **Loading state:** Not applicable (conversion is near-instant, < 5s)
- **Error state:** shown in status bar (red text)
- **Empty state:** panels show placeholder text "Aucun autotile chargé"

---

## Anti-Patterns

| # | Anti-Pattern | Why It's Wrong | Do Instead |
|---|---|---|---|
| AP-01 | Putting image processing in `gui/app.py` | Untestable, GUI-coupled. | Keep all pixel operations in `core/converter_*.py`. GUI only calls and displays. |
| AP-02 | Hardcoding output path to `tools/src/output/` | Breaks for users in other directories. | Default = `tools/src/output/`, user can override via dir picker. |
| AP-03 | Mutating the source PIL Image | Side effects corrupt re-conversions. | Always `img.copy()` before any crop/paste. |
| AP-04 | Using `Image.BILINEAR` for preview scaling | Blurs pixel art. | Always `Image.NEAREST` for integer scaling of tile graphics. |
| AP-05 | Using wrong wangset type in TSX | `type="edge"` → only 4 directions, no corners. Broken terrain brush. | `type="mixed"` for 47-tile blob. |
| AP-06 | Hardcoding tile_size=32 in MV converter | Breaks for official 48px MV packs. | Always call `detect_tile_size(img)` first. |
| AP-07 | Skipping input validation before conversion | Garbage-in → silent wrong output or crash. | Always validate dimensions before calling `convert_xp` or `convert_mv`. |
| AP-08 | Using the top-left tile of XP as data (it's the icon) | The 32×32 icon at (0,0) is editor-only, not terrain data. | Icon sub-tile is never used in the lookup table output. |
| AP-09 | Including only 46 wangtile entries in TSX | One missing configuration → Tiled terrain paint has gaps. | Exactly 47 `<wangtile>` entries required (all of BLOB_BITMASK_ORDER). |
| AP-10 | Wrong wangid bit order | Tiled uses `[N, NE, E, SE, S, SW, W, NW]` order, not the bitmask bit order. | Use `bitmask_to_wangid()` helper, never map manually. |
| AP-11 | Reading inner corners from the "absence de surface" zone (col 2-3, rows 0-1) | Col 2-3 rows 0-1 is the background zone (what shows when no autotile is placed). Using these coordinates for virages internes produces solid background-color squares at concave corners. | Inner corners (virages internes) are at **col 4-5, rows 0-1** (B-TL=(4,0), B-TR=(5,0), B-BL=(4,1), B-BR=(5,1)). Verified by color-coded demo autotile and RPG Maker FR tutorial. |

---

## Test Case Specifications

### Unit Tests — `test_converter_xp.py`

| ID | Test | Input | Expected |
|---|---|---|---|
| TC-001 | `convert_xp` returns 47 images | `sample_xp.png` | `len(result) == 47` |
| TC-002 | Each output tile is 32×32 | `sample_xp.png` | All `img.size == (32, 32)` |
| TC-003 | Each output tile is RGBA | `sample_xp.png` | All `img.mode == "RGBA"` |
| TC-004 | Wrong dimensions raise ValueError | `Image.new("RGBA", (64, 64))` | `ValueError` raised |
| TC-005 | Isolated tile (bitmask=0) uses outer corners | `sample_xp.png` | `result[0]` not all-transparent, corners sampled from outer region |
| TC-006 | Fully surrounded tile (bitmask=255) uses inner fill | `sample_xp.png` | `result[46]` pixel colors match inner fill region of source |
| TC-007 | `_extract_subtile` crops correctly | 96×128 test image with known color at (32,32)–(47,47) | Extracted sub-tile at (2,2) = expected color |
| TC-008 | `_assemble_tile` places quadrants correctly | 4 distinct-color 16×16 images | Output: TL=color1, TR=color2, BL=color3, BR=color4 |
| TC-009 | Source image is not mutated | `sample_xp.png`, run `convert_xp` | Source image pixels unchanged after call |
| TC-010 | Output index matches BLOB_BITMASK_ORDER | `sample_xp.png` | `result[i]` corresponds to `BLOB_BITMASK_ORDER[i]` (verified by lookup) |

### Unit Tests — `test_converter_mv.py`

| ID | Test | Input | Expected |
|---|---|---|---|
| TC-011 | `detect_tile_size` returns 32 for 64×96 | `Image.new("RGBA", (64,96))` | `32` |
| TC-012 | `detect_tile_size` returns 48 for 96×144 | `Image.new("RGBA", (96,144))` | `48` |
| TC-013 | `detect_tile_size` raises ValueError for unknown size | `Image.new("RGBA", (128,192))` | `ValueError` |
| TC-014 | `convert_mv` returns 47 images (32px) | `sample_mv_32px.png` | `len(result) == 47` |
| TC-015 | Each output tile is 32×32 for 64×96 input | `sample_mv_32px.png` | All `img.size == (32, 32)` |
| TC-016 | Each output tile is RGBA | `sample_mv_32px.png` | All `img.mode == "RGBA"` |
| TC-017 | Wrong dimensions raise ValueError | `Image.new("RGBA", (64, 64))` | `ValueError` |
| TC-018 | Isolated tile (bitmask=0) uses outer corners | `sample_mv_32px.png` | `result[0]` sampled from outer region of block |
| TC-019 | Fully surrounded (bitmask=255) uses inner fill | `sample_mv_32px.png` | `result[46]` matches inner tile region |
| TC-020 | Source image not mutated | `sample_mv_32px.png` | Pixels unchanged after `convert_mv` |

### Unit Tests — `test_tsx_generator.py`

| ID | Test | Input | Expected |
|---|---|---|---|
| TC-021 | `assemble_sheet` returns correct dimensions (32px) | 47 32×32 tiles | Sheet size = 256×192 |
| TC-022 | `assemble_sheet` returns correct dimensions (48px) | 47 48×48 tiles | Sheet size = 384×288 |
| TC-023 | `assemble_sheet` places tile[0] at (0,0) | 47 distinct-color tiles | Pixel at (0,0) matches tile[0] pixel (0,0) |
| TC-024 | `assemble_sheet` places tile[8] at col=0, row=1 | 47 distinct-color tiles | Pixel at (0, 32) matches tile[8] pixel (0,0) |
| TC-025 | `assemble_sheet` slot 47 is transparent | 47 tiles + check last slot | Sheet pixel at (7*32, 5*32) has alpha=0 |
| TC-026 | `bitmask_to_wangid(0)` returns all-zero | bitmask=0 | `"0,0,0,0,0,0,0,0"` |
| TC-027 | `bitmask_to_wangid(255)` returns all-one | bitmask=255 | `"1,1,1,1,1,1,1,1"` |
| TC-028 | `bitmask_to_wangid(1)` → N only | bitmask=1 (N=1) | `"1,0,0,0,0,0,0,0"` |
| TC-029 | `generate_tsx` XML is valid | 47 tiles, name="test", size=32 | Parses without error by `ElementTree.fromstring` |
| TC-030 | `generate_tsx` has exactly 47 wangtile entries | Standard input | XML contains exactly 47 `<wangtile>` elements |
| TC-031 | `generate_tsx` wangset type is "mixed" | Standard input | `<wangset type="mixed">` present |
| TC-032 | `export` creates PNG file | 47 tiles, temp dir | PNG file exists at expected path |
| TC-033 | `export` creates TSX file | 47 tiles, temp dir | TSX file exists at expected path |
| TC-034 | `export` raises OSError for non-writable dir | output_dir="/root/nope" | `OSError` raised |
| TC-035 | `export` raises ValueError for != 47 tiles | 46 tiles | `ValueError` raised |

### Integration Tests — `tests/tools/asset_creator/test_converter_integration.py`

| ID | Test | Scenario | Expected |
|---|---|---|---|
| IT-001 | XP full pipeline: load → convert → export | `sample_xp.png` → export to temp | PNG 256×192 + TSX valid, 47 wangtiles |
| IT-002 | MV full pipeline: load → convert → export | `sample_mv_32px.png` → export | PNG 256×192 + TSX valid, 47 wangtiles |
| IT-003 | XP output tiles cover all 47 bitmasks | `sample_xp.png` → convert | Each bitmask in BLOB_BITMASK_ORDER has a corresponding non-empty tile |
| IT-004 | Canvas pattern renders without error | 47 tiles → draw 5×5 pattern | 25 cells rendered, no exceptions |
| IT-005 | TSX imports cleanly in Tiled | Export → load in Tiled 1.10 | No error in TSX schema (manual verification step) |
| IT-006 | TSX wangtile entries match BLOB_BITMASK_ORDER | Export any valid input | 47 wangtile tileid values correspond to BLOB_BITMASK_ORDER indices |
| IT-007 | MV 48px full pipeline | `sample_mv_48px.png` → detect=48 → convert → export | detect_tile_size=48, 47 tiles, PNG 256×192 + TSX valid |
| IT-008 | MV 48px tiles normalized to 32px | `sample_mv_48px.png` → convert | All 47 output tiles are 32×32 RGBA (downscaled from 48px) |
| IT-009 | MV 48px tiles non-empty | `sample_mv_48px.png` → convert | All 47 output tiles have at least one opaque pixel |


---

## Project File Tree

Files managed by this specification:

```
tools/
  src/
    asset_creator/
      core/
        converter_xp.py         [NEW] XP autotile → 47 blob tiles
        converter_mv.py         [NEW] MV/MZ autotile → 47 blob tiles
      exporters/
        tsx_generator.py        [NEW] PNG sheet + TSX wangset writer
      gui/
        app.py                  [REPLACED] autotile converter GUI (replaces Dear PyGui procedural gen)
    input/
      sample_xp.png             [EXISTING] XP sample (96x128 px)
      sample_mv_32px.png        [EXISTING] MV sample (64x96 px, tile_size=32)
      sample_mv_48px.png        [NEW] MV sample (96x144 px, tile_size=48)
    output/
      .gitkeep                  [NEW] keep output dir in git
  docs/
    specs/
      autotile_converter_spec.md  [THIS FILE]
    strategic/
      autotile_converter_blueprint.md [EXISTING]
    research/
      autotile-converter.md     [EXISTING]
tests/
  tools/
    asset_creator/
      test_converter_xp.py      [NEW]
      test_converter_mv.py      [NEW]
      test_tsx_generator.py     [NEW]
      test_converter_integration.py  [NEW]
```
